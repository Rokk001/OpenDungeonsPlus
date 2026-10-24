#!/usr/bin/env python3
"""Check the gold system: gold per seam tile, gold per dig step, tile density, carry capacity, level and network
format, editor, look of the densities. Static text checks of the sources plus the texture generator check; no game
start and no build needed.

The first sections cover the gold system code; the last section runs the gold density rebalance tool of the levels
(--check against its base commit) and compares its per-level summary with the expected table.
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

gold_dig = function_body(tile_source, 'double Tile::digOutGold(double stepFactor)')
assert 'getGoldSeamTotal()' in gold_dig
assert 'getGoldPerDigStep()' in gold_dig and 'mGoldDensity' in gold_dig and 'getGoldDensityPercent()' in gold_dig
assert 'mFullness / 100.0 * total' in gold_dig                       # remaining gold from the fullness share
assert '(remaining - step) / total * 100.0' in gold_dig              # fullness = remaining share in percent
assert 'finishDigOut();' in gold_dig and 'return remaining;' in gold_dig  # the last step pays what is left
assert 'getDigRate' not in gold_dig and 'digRate' not in gold_dig   # not worker dependent
assert 'skirmishPercent / 100.0 * stepFactor;' in gold_dig           # only the factor of the caller (dig%, critical)
seam_total = function_body(tile_source, 'double Tile::getGoldSeamTotal() const')
assert 'getGoldPerSeamTile()' in seam_total and 'mGoldDensity' in seam_total and 'getGoldDensityPercent()' in seam_total
# digOut stays as it is for tunnelling and every other wall
dig_out = function_body(tile_source, 'double Tile::digOut(double digRate)')
assert 'case TileVisual::gemFull:' in dig_out and 'fullnessLost = 0.0;' in dig_out
assert 'digOutGold' not in dig_out

dig_action = read('source/creatureaction/CreatureActionDigTile.cpp')
handle = function_body(dig_action, 'bool CreatureActionDigTile::handleDigTile(')
assert 'if(tileDig.getType() == TileType::gold)' in handle and 'amountDug = tileDig.digOutGold(digFactor * criticalFactor);' in handle
assert 'amountDug = tileDig.digOut(creature.getDigRate() * digFactor * criticalFactor);' in handle
gold_case = handle[handle.index('case TileType::gold:'):handle.index('case TileType::gem:')]
assert 'payMinedGold(creature, tileDig, amountDug);' in gold_case
assert 'receiveExp(creature.getDigRate() / 20.0)' in gold_case          # XP per step stays as it was
assert 'receiveExp(1.5 * creature.getDigRate() / 20.0)' in handle
gem_case = handle[handle.index('case TileType::gem:'):handle.index('default:')]
assert 'getGemGoldPerDigStep()' in gem_case and 'payMinedGold(creature, tileDig, gemGoldPerDigStep * digFactor * criticalFactor);' in gem_case
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
assert 'const int32_t baseCapacity = mDefinition->getMaxGoldCarryable();' in capacity   # plan 4 extends the capacity
assert 'getGoldCarryPerStrength()' in capacity and 'getSkillPassive("carry%")' in capacity
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

# ---------------------------------------------------------------------------------------------------------------------
# Gold in the levels (9): the tool recomputes every level at its base commit and compares the gold lines with the files
# ---------------------------------------------------------------------------------------------------------------------
# Expected result per level of the density rebalance: seats, gold tiles before, gold per seat after,
# tiles per density 50/100/150, gold tiles added.
EXPECTED_LEVELS = {
    'levels/campaign/Ashcombe.level': ('1', '136', '406500', '46/45/45', '0'),
    'levels/campaign/Bellwick.level': ('2', '129', '301500', '0/0/134', '5'),
    'levels/campaign/Bonus1.level': ('4', '198', '300375', '0/0/267', '69'),
    'levels/campaign/BoulderCourse.level': ('1', '188', '562500', '63/63/62', '0'),
    'levels/campaign/Brackenford.level': ('1', '43', '301500', '0/0/67', '24'),
    'levels/campaign/Campaign1.level': ('2', '519', '778500', '173/173/173', '0'),
    'levels/campaign/Campaign2.level': ('2', '651', '976500', '217/217/217', '0'),
    'levels/campaign/Campaign3.level': ('2', '2386', '3578250', '796/795/795', '0'),
    'levels/campaign/Cinderhollow.level': ('2', '145', '300000', '0/35/110', '0'),
    'levels/campaign/Coldwell.level': ('1', '72', '300000', '0/16/56', '0'),
    'levels/campaign/CrowshotGallery.level': ('1', '36', '301500', '0/0/67', '31'),
    'levels/campaign/Dunmarrow.level': ('1', '70', '300000', '0/10/60', '0'),
    'levels/campaign/Ebonrook.level': ('1', '187', '559500', '63/62/62', '0'),
    'levels/campaign/Goldspire.level': ('1', '110', '328500', '37/37/36', '0'),
    'levels/campaign/Greywater.level': ('2', '116', '301500', '0/0/134', '18'),
    'levels/campaign/Highcairn.level': ('1', '114', '342000', '38/38/38', '0'),
    'levels/campaign/HollinFen.level': ('1', '120', '360000', '40/40/40', '0'),
    'levels/campaign/HollowmarkCitadel.level': ('1', '113', '337500', '38/38/37', '0'),
    'levels/campaign/Ironbridge.level': ('2', '116', '301500', '0/0/134', '18'),
    'levels/campaign/Kingsfall.level': ('1', '72', '300000', '0/16/56', '0'),
    'levels/campaign/Lanternhill.level': ('2', '111', '301500', '0/0/134', '23'),
    'levels/campaign/Mirewatch.level': ('1', '225', '675000', '75/75/75', '0'),
    'levels/campaign/Mossgate.level': ('1', '34', '301500', '0/0/67', '33'),
    'levels/campaign/Ravensledge.level': ('1', '116', '346500', '39/39/38', '0'),
    'levels/campaign/Saltmere.level': ('2', '104', '301500', '0/0/134', '30'),
    'levels/campaign/Silverdeep.level': ('4', '169', '300375', '0/0/267', '98'),
    'levels/campaign/SkittleCavern.level': ('1', '53', '301500', '0/0/67', '14'),
    'levels/campaign/Stormhaven.level': ('5', '201', '300600', '0/0/334', '133'),
    'levels/campaign/SwarmNight.level': ('2', '48', '301500', '0/0/134', '86'),
    'levels/campaign/Thornreach.level': ('5', '193', '300600', '0/0/334', '141'),
    'levels/campaign/Tinmoor.level': ('1', '138', '414000', '46/46/46', '0'),
    'levels/campaign/TwistingHalls.level': ('1', '28', '301500', '0/0/67', '39'),
    'levels/campaign/VarnsCrossing.level': ('3', '236', '300000', '0/108/128', '0'),
    'levels/campaign/Wolfscar.level': ('5', '187', '300600', '0/0/334', '147'),
    'levels/campaign/Wraithwood.level': ('3', '134', '300000', '0/0/200', '66'),
    'levels/multiplayer/Angel.level': ('4', '2736', '2052000', '912/912/912', '0'),
    'levels/multiplayer/GreedOrMight.level': ('3', '196', '300000', '0/0/200', '4'),
    'levels/multiplayer/RuinsOfTheConfluent.level': ('4', '171', '300375', '0/0/267', '96'),
    'levels/multiplayer/ScreamInTheDark.level': ('5', '372', '300000', '0/116/256', '0'),
    'levels/multiplayer/TheBridge.level': ('2', '255', '382500', '85/85/85', '0'),
    'levels/skirmish/Barrackdeep.level': ('1', '75', '300000', '0/25/50', '0'),
    'levels/skirmish/DuelToDeath.level': ('2', '2386', '3578250', '796/795/795', '0'),
    'levels/skirmish/Embervault.level': ('1', '79', '300000', '0/37/42', '0'),
    'levels/skirmish/FallingKeeper.level': ('2', '519', '778500', '173/173/173', '0'),
    'levels/skirmish/ForgottenTreasures.level': ('2', '651', '976500', '217/217/217', '0'),
    'levels/skirmish/FourThrones.level': ('4', '384', '300000', '96/160/128', '0'),
    'levels/skirmish/Gloomkeep.level': ('1', '171', '513000', '57/57/57', '0'),
    'levels/skirmish/GrandDelve.level': ('1', '74', '300000', '0/22/52', '0'),
    'levels/skirmish/Lanternreach.level': ('1', '135', '405000', '45/45/45', '0'),
    'levels/skirmish/Quietcrag.level': ('1', '87', '300000', '3/55/29', '0'),
    'levels/skirmish/Splitstone.level': ('1', '157', '469500', '53/52/52', '0'),
    'levels/skirmish/StoneKeep.level': ('3', '698', '697500', '233/233/232', '0'),
    'levels/skirmish/TriadDeeps.level': ('3', '552', '552000', '184/184/184', '0'),
    'levels/skirmish/TwinDelve.level': ('2', '124', '301500', '0/0/134', '10'),
    'levels/skirmish/Wyrmhollow.level': ('1', '508', '1522500', '170/169/169', '0'),
}

tool = read('tools/balance/rebalance_gold_density.py')
assert re.search(r'^BASE_COMMIT = "[0-9a-f]{40}"$', tool, re.M)
assert 'GOLD_TARGET_PER_KEEPER_SEAT = 300000' in tool
result = subprocess.run([sys.executable, str(ROOT / 'tools' / 'balance' / 'rebalance_gold_density.py'), '--check'],
                        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True,
                        timeout=TIMEOUT_SECONDS)
assert result.returncode == 0, result.stdout
assert 'MISMATCH' not in result.stdout, result.stdout
found_levels = {}
for line in result.stdout.splitlines():
    fields = [field.strip() for field in line.split('|')]
    if len(fields) == 6:
        found_levels[fields[0]] = tuple(fields[1:])
assert sorted(found_levels) == sorted(EXPECTED_LEVELS), sorted(set(found_levels) ^ set(EXPECTED_LEVELS))
for level_name, expected in EXPECTED_LEVELS.items():
    assert found_levels[level_name] == expected, (level_name, found_levels[level_name], expected)

print('Gold balance: config, density, mining, fractions, capacity, format, network, editor, look, levels passed')
