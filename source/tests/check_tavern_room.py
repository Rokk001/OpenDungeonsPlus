"""Tavern room registration: room type, tile visual, tileset, buttons, research entries, AI order, the counter tile
rules and the payer default of the AI keepers.

What is checked
  RoomType / TileVisual / SkillType   the tavern entries sit at the end of their enums, with the switch cases of the
                                      tile and skill code
  RoomTavern                          names, factory, registration in the build, cost and hit points keys
  tilesets.cfg                        the mapping line and the 16 masks of [tavernRoom] with existing materials
  buttons                             the build button of the Rooms tab (hidden by default, after the hatchery in the
                                      action bar), the research buttons TavernButton and BeerButton, tooltips and icons
  research                            roomTavern (tier I, no parent) and tavernBeer (tier II, parent roomTavern, a keeper
                                      entry after the casino), 56 entries, six free entries, the portal cooldown wiring
  KeeperAI                            the tavern follows the hatchery in the build list
  counter tile                        the first tile of the room is the counter tile; counter, keg (wall side) and table
                                      (inner tiles) objects; the counter tile is never a drinking spot
  AI payer                            taverns of computer keepers let the creatures pay

Calls (from the repository root):
  python source/tests/check_tavern_room.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]


# Returns the text of a repository file.
def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns the identifiers of an enum (comments and "= value" skipped), in order.
def enum_names(text, header):
    start = text.index(header)
    body = text[text.index('{', start) + 1:text.index('};', start)]
    names = []
    for line in body.splitlines():
        line = line.split('//')[0].strip().rstrip(',')
        if line and not line.startswith('/*'):
            names.append(line.split('=')[0].strip())
    return names


# Returns the text of a function from its header up to its closing brace in column 0.
def extract(text, header):
    start = text.index(header)
    return text[start:text.index('\n}\n', start) + 2]


# 1. RoomType, TileVisual and SkillType: the tavern entries are appended, one each
rooms = enum_names(read('source/rooms/RoomType.h'), 'enum class RoomType')
assert rooms[-2:] == ['tavern', 'nbRooms'] and rooms.count('tavern') == 1, rooms[-3:]
visuals = enum_names(read('source/entities/Tile.h'), 'enum class TileVisual')
assert visuals[-2:] == ['tavernRoom', 'countTileVisual'] and visuals.count('tavernRoom') == 1, visuals[-3:]
tile_cpp = read('source/entities/Tile.cpp')
assert tile_cpp.count('case TileVisual::tavernRoom:') >= 4, 'tavernRoom is missing in the Tile switches'
assert 'return "tavernRoom";' in tile_cpp
skills = enum_names(read('source/game/SkillType.h'), 'enum class SkillType')
assert skills[-3:] == ['roomTavern', 'tavernBeer', 'countSkill'], skills[-4:]
skill_type_cpp = read('source/game/SkillType.cpp')
for name in ('roomTavern', 'tavernBeer'):
    assert 'case SkillType::' + name + ':' in skill_type_cpp and '"' + name + '"' in skill_type_cpp, name + ' in SkillType.cpp'

# 2. The room class, factory, names, registration and the keys of its cost and hit points
room_cpp = read('source/rooms/RoomTavern.cpp')
assert 'const std::string RoomTavernName = "Tavern";' in room_cpp
assert 'const std::string RoomTavernNameDisplay = "Tavern room";' in room_cpp
assert 'const RoomType RoomTavern::mRoomType = RoomType::tavern;' in room_cpp
assert 'const TileVisual RoomTavern::mRoomVisual = TileVisual::tavernRoom;' in room_cpp
assert 'class RoomTavernFactory : public RoomFactory' in room_cpp and 'RoomRegister' in room_cpp
assert '"TavernCostPerTile"' in room_cpp
cmake = read('CMakeLists.txt')
for name in ('rooms/RoomTavern.cpp', 'entities/InnkeeperEntity.cpp', 'creatureaction/CreatureActionSearchDrink.cpp',
             'creatureaction/CreatureActionVomit.cpp', 'creaturemood/CreatureMoodThirst.cpp'):
    assert '${SRC}/' + name in cmake, name + ' missing in CMakeLists.txt'

# 3. Tileset: mapping line and a block with the 16 corner combinations with existing materials
tilesets = read('config/tilesets.cfg')
assert re.search(r'^\s*tavernRoom tavernRoom\s*$', tilesets, re.M), 'tileset link line missing'
block = re.search(r'\[tavernRoom\](.*?)\[/tavernRoom\]', tilesets, re.S)
assert block is not None, '[tavernRoom] block missing'
lines = [l.split() for l in block.group(1).splitlines() if l.strip()]
assert [l[0] for l in lines] == ['%04d' % int(format(i, 'b')) for i in range(16)], 'the block needs the 16 masks 0000-1111'
materials = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))
for words in lines:
    # Floor, wainscot and mug shelf are painted into the 16 floor pieces (one material per mask)
    assert words[1] == 'Room.mesh' and words[2] == 'Tavern' + words[0], words
    assert re.search(r'^material ' + words[2] + r'\b', materials, re.M), 'material ' + words[2] + ' missing'

# 4. Buttons: action bar (hidden by default, after the hatchery) and research tree with the icons of the room and Beer
rooms_layout = read('gui/WindowTabRooms.layout')
skill_layout = read('gui/WindowSkillTree.layout')
button = re.search(r'name="TavernButton" >(.*?)</Window>', rooms_layout, re.S)
assert button is not None, 'TavernButton missing in WindowTabRooms.layout'
assert 'OpenDungeonsIcons/TavernButton' in button.group(1) and '"Visible" value="False"' in button.group(1)
research = re.search(r'name="TavernButton" >(.*?)<Window type="OD/ProgressBar" name="TavernButtonProgressBar"', skill_layout, re.S)
assert research is not None, 'TavernButton missing in WindowSkillTree.layout'
assert 'OpenDungeonsIcons/TavernButton' in research.group(1) and 'Room: Tavern' in research.group(1)
beer = re.search(r'name="BeerButton" >(.*?)<Window type="OD/ProgressBar" name="BeerButtonProgressBar"', skill_layout, re.S)
assert beer is not None, 'BeerButton missing in WindowSkillTree.layout'
assert 'OpenDungeonsIcons/BeerButton' in beer.group(1) and 'Tavern: Beer' in beer.group(1)
for layout, names in ((rooms_layout, ('TavernButton',)), (skill_layout, ('TavernButton', 'BeerButton'))):
    for name in names:
        assert layout.count('name="' + name + '"') == 1, name + ' must exist once per layout'
# The painted sources of the two icons exist (the atlas entries are pinned by check_forged_icons.py)
for icon in ('TavernButton', 'BeerButton'):
    assert (root / 'assets-src' / 'gui' / 'icons' / 'tiles' / (icon + '.png')).exists(), 'icon source ' + icon + ' missing'
gui_cpp = read('source/render/Gui.cpp')
arrange = extract(gui_cpp, 'void Gui::arrangeRoomButtons(')
assert '"HatcheryButton", "TavernButton"' in arrange, 'the tavern button follows the hatchery in the action bar'

# 5. Research: tavern (tier I) and Beer (tier II, keeper entry), 56 entries, tooltip, portal cooldown wiring
manager = read('source/game/SkillManager.cpp')
assert ('createSkill(mSkills, SkillType::roomTavern, NO_PARENTS);\n'
        '    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "TavernButton", skill, 1, RoomType::tavern);') in manager
assert ('createSkill(mSkills, SkillType::tavernBeer, std::vector<SkillType>{SkillType::roomTavern});\n'
        '    def = new SkillDefKeeper(TREE_PREFIX_ROOMS, "BeerButton", skill, 2);') in manager
constructor = manager[manager.index('SkillManager::SkillManager()'):manager.index('SkillManager::~SkillManager()')]
registered = re.findall(r'createSkill\(mSkills, SkillType::(\w+),', constructor)
assert registered.count('roomTavern') == 1 and registered.count('tavernBeer') == 1
assert len(registered) == 56, 'the research tree has 56 entries, found ' + str(len(registered))
assert registered.index('roomCasino') < registered.index('tavernBeer'), 'Beer follows the casino in the tier II row'
assert 'KEEPER_TITLE_BEER = "Beer"' in manager and 'Your taverns serve beer.' in manager
assert 'ResearchEffect::PortalCooldown' in manager or '"PortalCooldown"' in manager
portal = read('source/rooms/RoomPortal.cpp')
assert 'SkillType::tavernBeer' in portal and 'PortalCooldownSpawnMin' in portal and 'PortalCooldownSpawnMax' in portal
assert portal.count('getResearchedCooldown(getSeat(),') == 2, 'both portal bounds use the researched factor'
skirmish_hits = [p for p in (root / 'source').rglob('*.cpp') if 'SkillType::tavernBeer' in p.read_text(encoding='utf-8', errors='replace')
                 and 'itemPageName' in p.read_text(encoding='utf-8', errors='replace')]
assert skirmish_hits, 'the skirmish settings must put tavernBeer on the Rooms page'
skills_cfg = read('config/skills.cfg')
free_block = re.search(r'^\[FreeLevelOne\]\s*$(.*?)^\[/FreeLevelOne\]', skills_cfg, re.M | re.S).group(1)
assert 'roomTavern' in free_block.split(), 'roomTavern is a free entry at the start'

# 6. AI: the keeper AI builds the tavern directly after the hatchery
ai = read('source/ai/KeeperAI.cpp')
wanted = ai[ai.index('static const std::vector<RoomType> wantedBuildings = {'):]
wanted = wanted[:wanted.index('};')]
order = re.findall(r'RoomType::(\w+)', wanted)
assert order.index('tavern') == order.index('hatchery') + 1 and order.count('tavern') == 1, order

# 7. Counter tile rules: the first tile is the counter tile (setup and update), with counter, keg and table objects,
# and it never becomes a drinking or game spot
setup = extract(room_cpp, 'void RoomTavern::setupRoom(')
assert 'mCounterTile = tiles.front();' in setup
update = extract(room_cpp, 'void RoomTavern::updateActiveSpots(')
assert 'mCounterTile = mCoveredTiles.front();' in update, 'the next remaining tile becomes the counter tile'
assert 'TAVERN_COUNTER_MESH' in update and 'TAVERN_KEG_MESH' in update and 'TAVERN_TABLE_MESH' in update
assert 'removeInnkeeper();' in update and 'placeInnkeeper();' in update
for name, mesh in (('TAVERN_COUNTER_MESH', 'TavernCounter'), ('TAVERN_KEG_MESH', 'TavernKeg'), ('TAVERN_TABLE_MESH', 'TavernTable')):
    assert 'const std::string ' + name + ' = "' + mesh + '";' in room_cpp, name
free_spot = extract(room_cpp, 'bool RoomTavern::isFreeSpotTile(')
assert 'tile == mCounterTile' in free_spot, 'the counter tile is never a spot'
drinking_tiles = extract(room_cpp, 'uint32_t RoomTavern::getNbDrinkingTiles()')
assert 'nbTiles - 1' in drinking_tiles
for mesh in ('TavernCounter', 'TavernKeg', 'TavernTable', 'Innkeeper', 'TavernMug', 'Vomit'):
    assert (root / 'models' / (mesh + '.mesh')).exists(), 'models/' + mesh + '.mesh missing'

# 8. AI payer default: the human keeper starts with "keeper pays", computer keepers with "creature pays"
header = read('source/rooms/RoomTavern.h')
payer_enum = header[header.index('enum class TavernPayer'):]
payer_enum = payer_enum[:payer_enum.index('};')]
assert re.search(r'keeper = 0,', payer_enum) and re.search(r'creature = 1', payer_enum), 'TavernPayer: keeper 0, creature 1'
assert 'mPayer(TavernPayer::keeper)' in room_cpp, 'the default payer is the keeper'
assert 'getIsHuman()' in setup and 'mPayer = TavernPayer::creature;' in setup, 'computer keepers let the creatures pay'

print('tavern room ok')
