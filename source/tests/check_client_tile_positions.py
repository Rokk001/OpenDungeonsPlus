"""Check that tiles of a map built without a level file stand at their own coordinates.

The client builds its map with GameMap::createNewMap, which only constructs the tiles; the level loader
sets the positions afterwards, the client never did. Room effects placed at tile->getPosition() then all
landed on tile 0,0, where the floor glows of the heart room stacked up into a permanent white-red disc.
The soft glow sprite is white with its falloff in the alpha channel, so its blending must weight by alpha.
"""
from pathlib import Path
import argparse
import re
import subprocess

repo = Path(__file__).resolve().parents[2]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source-ref', help='Read production code from a Git revision for a before/after check')
args = parser.parse_args()


def read_source(path):
    if args.source_ref:
        return subprocess.check_output(['git', 'show', f'{args.source_ref}:{path}'], cwd=repo, text=True)
    return (repo / path).read_text(encoding='utf-8')


def block(text, start_marker):
    start = text.index(start_marker)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


failures = []

# The constructor used by createNewMap places the tile at its coordinates
tile = read_source('source/entities/Tile.cpp')
constructor = block(tile, 'Tile::Tile(GameMap* gameMap, int x, int y')
body = constructor[constructor.index('{'):]
if not re.search(r'mPosition\s*=\s*Ogre::Vector3\(\s*static_cast<Ogre::Real>\(\s*m?[xX]\s*\)\s*,\s*'
                 r'static_cast<Ogre::Real>\(\s*m?[yY]\s*\)\s*,\s*0\.0f\s*\)', body):
    failures.append('Tile constructor does not place the tile at its map coordinates')

# The client map is still built by createNewMap, without a separate position pass
client = read_source('source/network/ODClient.cpp')
load = client[client.index('case ServerNotificationType::loadLevel:'):]
load = load[:load.index('case ServerNotificationType::', 10)]
if 'createNewMap(' not in load:
    failures.append('client level loading no longer uses createNewMap; recheck where tile positions come from')
gamemap = read_source('source/gamemap/GameMap.cpp')
create = block(gamemap, 'bool GameMap::createNewMap(')
if 'new Tile(this, ii, jj)' not in create:
    failures.append('createNewMap no longer constructs tiles with their coordinates')

# Room effects of tiles use the tile position
ambience = read_source('source/render/RoomAmbience.cpp')
scan = block(ambience, 'void RoomAmbience::scanTiles(')
if 'tile->getPosition()' not in scan:
    failures.append('scanTiles changed its tile position source; recheck this check')

# The soft glow is white with the falloff in alpha: additive blending has to weight by alpha
material = read_source('materials/scripts/RoomAmbience.material')
glow = material[material.index('material RoomAmbGlow'):]
glow = glow[:glow.index('\n}\n')]
if 'scene_blend src_alpha one' not in glow:
    failures.append('RoomAmbGlow ignores the alpha falloff of its white sprite (hard disc)')
generator = (repo / 'tools/gen_room_ambience_art.py').read_text(encoding='utf-8')
sprite = generator[generator.index('def sprite_glow(path):'):generator.index('def sprite_smoke(path):')]
if 'radial(image, (255, 255, 255, 255)' not in sprite:
    failures.append('RoomAmbGlow sprite is no longer white with an alpha falloff; recheck the blending')

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    raise SystemExit(1)
print('OK: client tiles stand at their coordinates and the room glow keeps its soft alpha falloff')
