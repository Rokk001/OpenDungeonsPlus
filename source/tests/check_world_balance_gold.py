#!/usr/bin/env python3
"""Check the gold system: gold per seam tile, gold per dig step, tile density, carry capacity, level and network
format, editor, look of the densities. Static text checks of the sources plus the texture generator check; no game
start and no build needed.

Package A of the gold balance covers everything below. The gold density rebalance of the levels (a later package)
extends this file with its own section.
"""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TIMEOUT_SECONDS = 600


def read(path):
    return (ROOT / path).read_text(encoding='utf-8')


def function_body(text, signature):
    """Returns the text from the signature to the closing brace in column 0 of the function."""
    start = text.index(signature)
    end = text.index('\n}\n', start)
    return text[start:end]


def config_value(text, name):
    return float(re.search(r'^\s*' + re.escape(name) + r'\s+([\d.]+)', text, re.M).group(1))


# ---------------------------------------------------------------------------------------------------------------------
# Config: gold per seam tile and per step, cheer share, worker carry capacity
# ---------------------------------------------------------------------------------------------------------------------
global_cfg = read('config/global.cfg')
assert config_value(global_cfg, 'GoldPerSeamTile') == 3000
assert config_value(global_cfg, 'GoldPerDigStep') == 25
assert config_value(global_cfg, 'GemGoldPerDigStep') == 16.67
assert config_value(global_cfg, 'WorkerCheerGoldShare') == 0.35
assert 'DigCoefGold' not in global_cfg and 'DigCoefGem' not in global_cfg
config_manager = read('source/utils/ConfigManager.cpp')
config_header = read('source/utils/ConfigManager.h')
for key in ('GoldPerSeamTile', 'GoldPerDigStep', 'GemGoldPerDigStep', 'WorkerCheerGoldShare'):
    assert 'nextParam == "%s"' % key in config_manager, key
assert 'DigCoefGold' not in config_manager and 'DigCoefGem' not in config_manager
assert 'DigCoefGold' not in config_header and 'DigCoefGem' not in config_header

creatures_cfg = read('config/creatures.cfg')
for worker in ('Kobold', 'DwarfWorker'):
    block = re.search(r'\[Creature\]\s*\n\s*Name\s+' + worker + r'\b.*?\[/Creature\]', creatures_cfg, re.S)
    assert block is not None, worker
    assert re.search(r'^\s*MaxGoldCarryable\s+100\s*$', block.group(0), re.M), worker + ' must carry 100 gold'
assert not re.search(r'MaxGoldCarryable\s+1500', creatures_cfg)

# ---------------------------------------------------------------------------------------------------------------------
# Tile density and the mining of a gold tile (6.2, 6.3, 6.4)
# ---------------------------------------------------------------------------------------------------------------------
tile_header = read('source/entities/Tile.h')
tile_source = read('source/entities/Tile.cpp')
assert 'uint32_t mGoldDensity;' in tile_header
assert 'mGoldDensity        (GOLD_DENSITY_DEFAULT)' in tile_source
assert 'mGoldDensity = tt->mGoldDensity;' in tile_source
set_type = tile_header[tile_header.index('inline void setType(TileType t)'):]
set_type = set_type[:set_type.index('inline uint32_t getGoldDensity')]
assert 'if(mType != TileType::gold)' in set_type and 'mGoldDensity = GOLD_DENSITY_DEFAULT;' in set_type
assert re.search(r'GOLD_DENSITY_LOW = 50;', tile_source)
assert re.search(r'GOLD_DENSITY_DEFAULT = 100;', tile_source)
assert re.search(r'GOLD_DENSITY_HIGH = 150;', tile_source)

gold_dig = function_body(tile_source, 'double Tile::digOutGold()')
assert 'getGoldSeamTotal()' in gold_dig
assert 'getGoldPerDigStep()' in gold_dig and 'mGoldDensity' in gold_dig and 'getGoldDensityPercent()' in gold_dig
assert 'mFullness / 100.0 * total' in gold_dig                       # remaining gold from the fullness share
assert '(remaining - step) / total * 100.0' in gold_dig              # fullness = remaining share in percent
assert 'finishDigOut();' in gold_dig and 'return remaining;' in gold_dig  # the last step pays what is left
assert 'getDigRate' not in gold_dig and 'digRate' not in gold_dig   # not worker dependent
seam_total = function_body(tile_source, 'double Tile::getGoldSeamTotal() const')
assert 'getGoldPerSeamTile()' in seam_total and 'mGoldDensity' in seam_total and 'getGoldDensityPercent()' in seam_total
# digOut stays as it is for tunnelling and every other wall
dig_out = function_body(tile_source, 'double Tile::digOut(double digRate)')
assert 'case TileVisual::gemFull:' in dig_out and 'fullnessLost = 0.0;' in dig_out
assert 'digOutGold' not in dig_out

dig_action = read('source/creatureaction/CreatureActionDigTile.cpp')
handle = function_body(dig_action, 'bool CreatureActionDigTile::handleDigTile(')
assert 'if(tileDig.getType() == TileType::gold)' in handle and 'amountDug = tileDig.digOutGold();' in handle
assert 'amountDug = tileDig.digOut(creature.getDigRate());' in handle
gold_case = handle[handle.index('case TileType::gold:'):handle.index('case TileType::gem:')]
assert 'payMinedGold(creature, tileDig, amountDug);' in gold_case
assert 'receiveExp(creature.getDigRate() / 20.0)' in gold_case          # XP per step stays as it was
assert 'receiveExp(1.5 * creature.getDigRate() / 20.0)' in handle
gem_case = handle[handle.index('case TileType::gem:'):handle.index('default:')]
assert 'getGemGoldPerDigStep()' in gem_case and 'payMinedGold(creature, tileDig, gemGoldPerDigStep);' in gem_case
assert 'amountDug' not in gem_case and 'getGoldDensityPercent' not in gem_case   # fixed per step, not scaled
assert 'creature.getGoldCarried() >= creature.getGoldCapacity()' in handle
assert 'getMaxGoldCarryable' not in dig_action

# ---------------------------------------------------------------------------------------------------------------------
# Fractions and carry capacity (6.5, 6.6)
# ---------------------------------------------------------------------------------------------------------------------
creature_header = read('source/entities/Creature.h')
creature_source = read('source/entities/Creature.cpp')
fraction = function_body(creature_source, 'int32_t Creature::addGoldCarriedFraction(double gold)')
assert 'mGoldRemainder += gold;' in fraction and 'std::floor(mGoldRemainder)' in fraction
assert 'addGoldCarried(added);' in fraction
assert 'double          mGoldRemainder;' in creature_header
assert creature_source.count('mGoldRemainder           (0.0),') == 2
export = creature_source[creature_source.index('mWakefulness << "\\t" << mHunger'):]
assert 'mGoldRemainder' not in export[:export.index('\n}\n')]             # the remainder is not saved
capacity = function_body(creature_source, 'int32_t Creature::getGoldCapacity() const')
assert 'return mDefinition->getMaxGoldCarryable();' in capacity
readers = [path.name for path in (ROOT / 'source').rglob('*.cpp')
           if 'getMaxGoldCarryable()' in path.read_text(encoding='utf-8', errors='replace')
           and 'tests' not in path.parts]
assert readers == ['Creature.cpp'], readers                                 # no other reader of the definition value
assert creature_source.count('getMaxGoldCarryable()') == 1                 # only getGoldCapacity reads it
assert 'getGoldCapacity(), false);' in creature_source                      # the cosmetic event carries the capacity
drop = function_body(creature_source, 'void Creature::dropExcessGold()')
assert 'capacity <= 0' in drop and 'mGoldCarried <= capacity' in drop       # creatures with capacity 0 are untouched
assert 'new TreasuryObject(getGameMap(), mGoldCarried - capacity)' in drop and 'mGoldCarried = capacity;' in drop
upkeep = function_body(creature_source, 'void Creature::doUpkeep()')
assert 'dropExcessGold();' in upkeep

# ---------------------------------------------------------------------------------------------------------------------
# Worker cheer share (6.7)
# ---------------------------------------------------------------------------------------------------------------------
reactions = read('source/render/WorkerReactions.cpp')
assert 'BIG_FIND_SHARE' not in reactions
assert 'ConfigManager::getSingleton().getWorkerCheerGoldShare()' in reactions

# ---------------------------------------------------------------------------------------------------------------------
# Level and save format (6.8): sixth column; mirror of the line logic
# ---------------------------------------------------------------------------------------------------------------------
writer = function_body(tile_source, 'void Tile::exportToStream(std::ostream& os) const')
assert 'bool writeDensity = (getType() == TileType::gold) && (mGoldDensity != GOLD_DENSITY_DEFAULT);' in writer
assert 'os << "\\t-1\\t" << mGoldDensity;' in writer                       # no seat: -1 as the seat column
assert 'os << "\\t" << mGoldDensity;' in writer
loader = function_body(tile_source, 'void Tile::loadFromLine(const std::string& line, Tile *t)')
assert '(tileType == TileType::gold) && (elems.size() >= 6)' in loader
assert 't->setGoldDensity(static_cast<uint32_t>(Helper::toInt(elems[5])));' in loader
assert loader.index('elems[5]') < loader.index('bool shouldSetSeat = false;')   # read before the early return
assert 'goldDensity(optional' in tile_source


def write_line(x, y, fullness, seat, density):
    """Mirror of Tile::exportToStream for a gold tile."""
    fields = [x, y, 2, fullness]
    if seat is None:
        if density != 100:
            fields += [-1, density]
    else:
        fields.append(seat)
        if density != 100:
            fields.append(density)
    return '\t'.join(str(f) for f in fields)


def load_density(line):
    """Mirror of the density part of Tile::loadFromLine: old files with 4 or 5 columns give 100."""
    fields = line.split('\t')
    return int(fields[5]) if len(fields) >= 6 else 100


assert write_line(3, 4, 100, None, 100) == '3\t4\t2\t100'
assert write_line(3, 4, 100, None, 150) == '3\t4\t2\t100\t-1\t150'
assert write_line(3, 4, 0, 2, 50) == '3\t4\t2\t0\t2\t50'
assert [load_density(l) for l in ('3\t4\t2\t100', '3\t4\t2\t0\t2', '3\t4\t2\t100\t-1\t150', '3\t4\t2\t0\t2\t50')] == \
    [100, 100, 150, 50]

# ---------------------------------------------------------------------------------------------------------------------
# Network (6.9): the density is the last value of the tile refresh packet; the editor packets carry it too
# ---------------------------------------------------------------------------------------------------------------------
seat_source = read('source/game/Seat.cpp')
tile_export = function_body(seat_source, 'void Seat::exportTileToPacket(ODPacket& os, Tile* tile,')
assert tile_export.index('os << tileState.mTileVisual;') < tile_export.index('os << goldDensity;')
assert tile_export.rstrip().endswith('os << goldDensity;')
assert 'tileState.mTileVisual == TileVisual::goldFull' in tile_export
reader = function_body(tile_source, 'void Tile::updateFromPacket(ODPacket& is)')
assert reader.index('is >> mTileVisual') < reader.index('is >> goldDensity')
assert 'uint32_t goldDensity = GOLD_DENSITY_DEFAULT;' in reader     # gold counts as 100 until the packet arrives
server = read('source/network/ODServer.cpp')
assert server.count('>> seatId >> goldDensity') == 2                # single tile and rectangle
assert server.count('setGoldDensity(goldDensity)') == 2
assert 'tile->getTileVisual() << tile->getGoldDensity()' in server  # revealTiles
client = read('source/network/ODClient.cpp')
assert '>> tileType >> tileFullness >> seatId >> tileVisual >> goldDensity' in client
game_map = read('source/gamemap/GameMap.cpp')
paste = game_map[game_map.index('ClientNotificationType::editorAskChangeTile);'):]
paste = paste[:paste.index('queueClientNotification')]
assert paste.index('rhs->getSeat()->getId()') < paste.index('rhs->getGoldDensity()')
editor = read('source/modes/EditorMode.cpp')
send = editor[editor.index('ClientNotificationType::editorAskChangeTiles);'):]
send = send[:send.index('queueClientNotification')]
assert send.index('<< seatId;') < send.index('<< mCurrentGoldDensity;')

# ---------------------------------------------------------------------------------------------------------------------
# Editor (6.10)
# ---------------------------------------------------------------------------------------------------------------------
assert 'case OIS::KC_G:' in editor and 'mCurrentGoldDensity = Tile::nextGoldDensity(mCurrentGoldDensity);' in editor
assert '"Gold density (G): " << mCurrentGoldDensity << "%"' in editor
assert '"    G - gold wall density 50/100/150 %"' in editor
assert editor.index('"    T - switch between full and empty tiles"') < editor.index('"    G - gold wall density 50/100/150 %"')
assert 'mCurrentGoldDensity(Tile::GOLD_DENSITY_DEFAULT)' in editor
assert 'EDITOR_GOLD_DENSITY = "HorizontalPipe/GoldDensityDisplay"' in read('source/render/Gui.cpp')
assert 'static const std::string EDITOR_GOLD_DENSITY;' in read('source/render/Gui.h')
layout = read('gui/ModeEditor.layout')
density_window = layout[layout.index('name="GoldDensityDisplay"'):]
density_window = density_window[:density_window.index('name="PositionDisplay"')]
assert '{{0,210},{0,0},{0,405},{0,25}}' in density_window            # FullnessDisplay x (5) + 205
assert 'Gold density (G): 100%' in density_window
# The three windows right of it are moved by the same 205 px so that nothing overlaps
assert '{{0,415},{0,0},{0,615},{0,25}}' in layout and '{{0,635},{0,0},{0,765},{0,25}}' in layout
assert '{{0,775},{0,0},{0,1005},{0,25}}' in layout


def next_density(density):
    """Mirror of Tile::nextGoldDensity."""
    return {100: 150, 150: 50}.get(density, 100)


assert [next_density(d) for d in (100, 150, 50)] == [150, 50, 100]
next_source = function_body(tile_source, 'uint32_t Tile::nextGoldDensity(uint32_t density)')
assert 'return GOLD_DENSITY_HIGH;' in next_source and 'return GOLD_DENSITY_LOW;' in next_source
assert next_source.rstrip().endswith('return GOLD_DENSITY_DEFAULT;')

# ---------------------------------------------------------------------------------------------------------------------
# Look (6.11): materials, tile refresh, CREDITS, texture generator
# ---------------------------------------------------------------------------------------------------------------------
material = read('materials/scripts/Gold.material')
for name, texture in (('Gold50', 'Gold50'), ('Gold150', 'Gold150')):
    block = material[material.index('material ' + name):]
    block = block[:block.index('texture_unit shadowmap')]
    assert 'texture %s.png' % texture in block and 'texture %sNormal.png' % texture in block
    assert 'vertex_program_ref myVertexShader' in block and 'fragment_program_ref myFragmentShader' in block
for texture in ('Gold50', 'Gold50Normal', 'Gold150', 'Gold150Normal'):
    assert (ROOT / 'materials' / 'textures' / (texture + '.png')).is_file(), texture
render = read('source/render/RenderManager.cpp')
assert 'if((density == Tile::GOLD_DENSITY_LOW) || (density == Tile::GOLD_DENSITY_HIGH))' in render
assert 'tileMeshEnt->setMaterialName(goldWallMaterialName(tile.getGoldDensity(), nt == NodeType::MDTC_NODE));' in render
assert 'createLiftedGoldMaterials();' in render and 'removeLiftedGoldMaterials();' in render
assert 'removeLiftedGoldMaterials();' in editor
assert '"LiftedGold"' not in render and 'remove("LiftedGold"' not in editor
credits = read('CREDITS')
lines = credits.splitlines()
gold_line = [i for i, line in enumerate(lines) if line.startswith('-> Gold{,Normal}.png')]
assert len(gold_line) == 1
assert lines[gold_line[0] + 1].startswith('-> Gold{50,150}{,Normal}.png')
assert 'OD Team' in lines[gold_line[0] + 1] and 'CC0' in lines[gold_line[0] + 1]
assert 'tools/dungeon-palette/generate_claimed_gold.py' in lines[gold_line[0] + 1]

result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'dungeon-palette' / 'generate_claimed_gold.py'), '--check'],
                        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                        timeout=TIMEOUT_SECONDS)
assert result.returncode == 0, result.stdout
assert 'UNCHANGED Gold.png' in result.stdout and 'UNCHANGED GoldNormal.png' in result.stdout, result.stdout
expected_shares = {50: (0.127, 0.0031), 100: (0.262, 0.0067), 150: (0.368, 0.0168)}
SHARE_TOLERANCE = 0.005
for density, (cover, glint) in expected_shares.items():
    found = re.search(r'density %d cover ([\d.]+) glint ([\d.]+)' % density, result.stdout)
    assert found is not None, result.stdout
    assert abs(float(found.group(1)) - cover) <= SHARE_TOLERANCE, (density, found.group(1))
    assert abs(float(found.group(2)) - glint) <= SHARE_TOLERANCE, (density, found.group(2))
status = subprocess.run(['git', '--no-pager', 'status', '--porcelain', '--', 'materials/textures'], cwd=str(ROOT),
                        stdout=subprocess.PIPE, universal_newlines=True)
assert 'materials/textures/Gold.png' not in status.stdout        # the check wrote nothing into the repository folder

print('Gold balance (package A): config, density, mining, fractions, capacity, format, network, editor, look passed')
