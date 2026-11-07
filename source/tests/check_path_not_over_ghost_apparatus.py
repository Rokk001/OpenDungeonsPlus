"""Decision 727, case ghost room apparatuses: no path step and no creature goes over the mana still, the ghost press, the
soul forge or the ghost cauldron.

Root cause (found by reading the history): 29d6d434d and 46e2993f4 added body bands for exactly the tops of these
apparatuses (1.289, 1.605, 1.694). A creature that has a band for the height of an object is stepped onto it
(prepareLowStep), so a wide creature walked over them and was lifted to wall height. Stepping is only allowed for beds
and cots now (e0926f9ff, kept); the bands stay harmless because collect() gives every other object the infinite height
that never matches a band, and the route search, blocked() and the client lift all use that rule.
No compiler needed."""
from pathlib import Path
import math
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8').replace('\r\n', '\n')


def between(text, start, end):
    assert start in text, start
    part = text.split(start, 1)[1]
    assert end in part, end
    return part.split(end, 1)[0]


bounds_source = read('source/gamemap/RoomObjectBounds.h')
nav = read('source/gamemap/RoomObjectNavigation.cpp')
render = read('source/render/RenderManager.cpp')
ghost_room = read('source/rooms/RoomGhostRoom.cpp')

rule = between(bounds_source, 'inline bool isSteppableMesh(const std::string& name)', '\n}\n')
names = set(re.findall(r'name == "([^"]+)"', rule))
suffixes = re.findall(r'compare\(name\.size\(\) - \d, \d, "([^"]+)"\) == 0', rule)
prefixes = re.findall(r'compare\(0, \d+, "([^"]+)"\) == 0', rule)


def steppable(name):
    return name in names or any(name.endswith(s) for s in suffixes) or any(name.startswith(p) for p in prefixes)


catalog = {}
for name, rest in re.findall(r'^    \{"([^"]+)",([^}]*)\}', between(bounds_source, 'static const MeshBounds meshBounds[] = {', '\n};'), re.M):
    values = [v.strip() for v in rest.split(',')]
    catalog[name] = float(values[4].rstrip('f')) if len(values) > 4 else math.inf
band_block = between(bounds_source, 'static const BodyBand bodyBands[] = {', '\n};')
bands = [(m, float(h)) for m, h in re.findall(r'\{"([^"]+)",\s*([0-9.]+)f?,', band_block)]


def has_band(mesh, height):
    return height > 0.0 and any(m == mesh and abs(h - height) < 0.0001 for m, h in bands)


apparatus = ('ManaStill', 'GhostPress', 'SoulForge', 'GhostCauldron')
for name in apparatus:
    assert '"' + name + '"' in ghost_room, name  # placed by the ghost room
    assert name in catalog and math.isfinite(catalog[name]), name  # measured, with a top height

# the cause: a band exists for each top of the three apparatuses, so a finite height made them steppable
for name in ('ManaStill', 'GhostPress', 'SoulForge'):
    assert has_band('Troll.mesh', catalog[name]), name
# the fix: no apparatus is steppable, collect() keeps their height infinite and infinity matches no band
for name in apparatus + ('GhostCauldronFill',):
    assert not steppable(name), name
assert not has_band('Troll.mesh', math.inf)
collect = between(nav, 'RoomObjectNavigation::collect(', 'RoomObjectNavigation::bodyObstacles(')
assert 'if(RoomObjectPath::isSteppableMesh(bounds.name))\n                result.back().maximumHeight = ' in collect

# only the wall landmarks are skipped as obstacles; every apparatus is one
skip = between(collect, 'const std::function<void(const BuildingObject*)> append', 'for(const RoomObjectPath::MeshBounds& bounds')
for name in ('GhostBell', 'GhostHook', 'GhostHookEmpty', 'GhostWallGauges', 'GhostRack'):
    assert '"' + name + '"' in skip, name
for name in apparatus:
    assert '"' + name + '"' not in skip, name

# the client lift only touches steppable meshes
step = between(render, 'void RenderManager::updateCreatureStep', 'void RenderManager::cancelCreatureStep')
assert 'if(!RoomObjectPath::isSteppableMesh(bounds.name))' in step
print('ok')
