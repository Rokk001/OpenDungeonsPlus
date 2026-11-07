"""Decision 727, case gravestones/crypt furniture: no path step and no creature goes over the furniture of the crypt.

Root cause (found by reading the history): since 3cfe1b1da a creature steps onto every object whose top height has a
measured body band for the creature, and the coffins of the crypt (KnightCoffin 0.84, StoneCoffin 0.77) were in the
steppable list although nobody sleeps in a grave. So the route search of RoomObjectNavigation::refine took the route
over the coffin and blocked() ignored it, and the client lifted the creature onto the lid. isSteppableMesh now names
beds and cots only; every other object keeps the infinite maximumHeight of a solid obstacle.
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

# the rule of RoomObjectPath::isSteppableMesh, read from its source text
rule = between(bounds_source, 'inline bool isSteppableMesh(const std::string& name)', '\n}\n')
names = set(re.findall(r'name == "([^"]+)"', rule))
suffixes = re.findall(r'compare\(name\.size\(\) - \d, \d, "([^"]+)"\) == 0', rule)
prefixes = re.findall(r'compare\(0, \d+, "([^"]+)"\) == 0', rule)


def steppable(name):
    return name in names or any(name.endswith(s) for s in suffixes) or any(name.startswith(p) for p in prefixes)


# the pieces of the crypt: graves, cross and statues, all measured obstacles of the catalog
crypt = set(re.findall(r'new BuildingObject\(getGameMap\(\), \*this, "([^"]+)"', read('source/rooms/RoomCrypt.cpp')))
assert {'KnightCoffin', 'StoneCoffin', 'CelticCross', 'KnightStatue', 'KnightStatue2'} <= crypt, crypt
catalog = set(re.findall(r'^    \{"([^"]+)",', between(bounds_source, 'static const MeshBounds meshBounds[] = {', '\n};'), re.M))
for name in sorted(crypt):
    assert name in catalog, name
    assert not steppable(name), name + ' must stay a solid obstacle'
# beds and cots stay steppable (the dormitory and the infirmary are not part of this decision)
for name in ('Bed', 'TrollBed', 'DragonBed', 'WorkerBed', 'InfirmaryCotSmall', 'InfirmaryCotLarge'):
    assert steppable(name), name

# collect() gives a finite height to steppable meshes only: a grave keeps the infinite height of an obstacle
collect = between(nav, 'RoomObjectNavigation::collect(', 'RoomObjectNavigation::bodyObstacles(')
assert 'if(RoomObjectPath::isSteppableMesh(bounds.name))\n                result.back().maximumHeight = ' in collect

# model of prepareLowStep: a step needs a measured body band for height = maximumHeight - ground; infinity has none,
# so the route search keeps the grave in `solid` (refine) and removeLowStepObstacles removes nothing of it (blocked)
band_block = between(bounds_source, 'static const BodyBand bodyBands[] = {', '\n};')
bands = [(m, float(h)) for m, h in re.findall(r'\{"([^"]+)",\s*([0-9.]+)f?,', band_block)]
assert len(bands) > 500


def has_band(mesh, height):
    return height > 0.0 and any(m == mesh and abs(h - height) < 0.0001 for m, h in bands)


for mesh in ('Troll.mesh', 'Dragon.mesh', 'Kobold.mesh', 'skeleton.mesh', 'lich.mesh', 'PitDemon.mesh'):
    assert not has_band(mesh, math.inf), mesh
# contrast, the old behaviour: with the finite lid heights of the coffins the big bodies had a band
for height in (0.841464, 0.767922):
    assert has_band('Troll.mesh', height), height

# the client lifts a creature only over steppable meshes
step = between(render, 'void RenderManager::updateCreatureStep', 'void RenderManager::cancelCreatureStep')
assert 'if(!RoomObjectPath::isSteppableMesh(bounds.name))' in step
print('ok')
