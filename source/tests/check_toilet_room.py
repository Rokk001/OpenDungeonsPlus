"""Toilet room registration: room type, tile visual, tileset, buttons, research entry and AI order.

Calls (from the repository root):
  python source/tests/check_toilet_room.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]


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


# 1. RoomType: the published toilet identifier stays before the appended equipment rooms, the tavern follows them
# 1. RoomType: published toilet and equipment identifiers stay before the appended infirmary.
room_type = read('source/rooms/RoomType.h')
rooms = enum_names(room_type, 'enum class RoomType')
assert rooms.index('toilet') == 19 and rooms[-1] == 'nbRooms', rooms
assert rooms[19:25] == ['toilet', 'merchant', 'herbGarden', 'alchemyLab', 'tavern', 'infirmary']
assert rooms.count('toilet') == 1

# 2. The room class, factory, names and registration in the build
room_cpp = read('source/rooms/RoomToilet.cpp')
assert 'const std::string RoomToiletName = "Toilet";' in room_cpp
assert 'const std::string RoomToiletNameDisplay = "Toilet room";' in room_cpp
assert 'const RoomType RoomToilet::mRoomType = RoomType::toilet;' in room_cpp
assert 'const TileVisual RoomToilet::mRoomVisual = TileVisual::toiletRoom;' in room_cpp
assert 'class RoomToiletFactory : public RoomFactory' in room_cpp and 'RoomRegister' in room_cpp
cmake = read('CMakeLists.txt')
for name in ('rooms/RoomToilet.cpp', 'creatureaction/CreatureActionSearchToilet.cpp', 'creatureaction/CreatureActionUseToilet.cpp'):
    assert '${SRC}/' + name in cmake, name + ' missing in CMakeLists.txt'
# Every covered tile gets a seat object (one per tile, removed with the tile)
assert 'ToiletSeat' in room_cpp

# 3. TileVisual: the published toilet visual stays before the appended equipment visuals, the tavern visual follows them
# 3. TileVisual: published toilet and equipment visuals stay before the appended infirmary visual.
tile_h = read('source/entities/Tile.h')
visuals = enum_names(tile_h, 'enum class TileVisual')
assert visuals.index('toiletRoom') == 30 and visuals[-1] == 'countTileVisual', visuals
assert visuals[30:36] == ['toiletRoom', 'merchantRoom', 'herbGardenRoom', 'alchemyLabRoom', 'tavernRoom', 'infirmaryRoom']
tile_cpp = read('source/entities/Tile.cpp')
assert tile_cpp.count('case TileVisual::toiletRoom:') >= 4, 'toiletRoom is missing in the Tile switches'
assert 'return "toiletRoom";' in tile_cpp

# 4. Tileset: mapping line and a block with the 16 corner combinations
tilesets = read('config/tilesets.cfg')
assert re.search(r'^\s*toiletRoom toiletRoom\s*$', tilesets, re.M), 'tileset link line missing'
block = re.search(r'\[toiletRoom\](.*?)\[/toiletRoom\]', tilesets, re.S)
assert block is not None, '[toiletRoom] block missing'
lines = [l.split() for l in block.group(1).splitlines() if l.strip()]
assert [l[0] for l in lines] == ['%04d' % int(format(i, 'b')) for i in range(16)], 'the block needs the 16 masks 0000-1111'
for words in lines:
    assert words[1] == 'Room.mesh' and words[2] == 'Toilet' + words[0], words
# Every visual block must be consumed by the sequential loader in the shipped file order.
config_manager = read('source/utils/ConfigManager.cpp')
tileset_loader = config_manager[config_manager.index('bool ConfigManager::loadTilesets('):
                               config_manager.index('bool ConfigManager::loadTilesetValues(')]
loaded_visuals = re.findall(r'loadTilesetValues\(defFile, TileVisual::(\w+),', tileset_loader)
assert len(loaded_visuals) == len(set(loaded_visuals)), 'duplicate tileset loader visual'
assert set(loaded_visuals) == set(visuals[:-1]), 'tileset loader must consume every TileVisual exactly once'
assert loaded_visuals[-6:] == ['toiletRoom', 'merchantRoom', 'herbGardenRoom', 'alchemyLabRoom', 'tavernRoom', 'infirmaryRoom']
for tileset in re.findall(r'\[Tileset\](.*?)\[/Tileset\]', tilesets, re.S):
    block_order = re.findall(r'^\s*\[(\w+)\]\s*$', tileset, re.M)
    block_order = [name for name in block_order if name not in {'TileLink', 'oneOf'}]
    assert block_order == loaded_visuals, 'tileset blocks must match the sequential ConfigManager loader order'
# The materials of the pieces exist
materials = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))
for words in lines:
    assert re.search(r'^material ' + words[2] + r'\b', materials, re.M), 'material ' + words[2] + ' missing'

# 5. Buttons: action bar (hidden by default, positioned like the others) and research tree, same icon
rooms_layout = read('gui/WindowTabRooms.layout')
skill_layout = read('gui/WindowSkillTree.layout')
button = re.search(r'name="ToiletButton" >(.*?)</Window>', rooms_layout, re.S)
assert button is not None, 'ToiletButton missing in WindowTabRooms.layout'
assert 'OpenDungeonsIcons/ToiletButton' in button.group(1) and '"Visible" value="False"' in button.group(1)
research = re.search(r'name="ToiletButton" >(.*?)<Window type="OD/ProgressBar" name="ToiletButtonProgressBar"', skill_layout, re.S)
assert research is not None, 'ToiletButton missing in WindowSkillTree.layout'
assert 'OpenDungeonsIcons/ToiletButton' in research.group(1) and 'Room: Toilet' in research.group(1)
assert 'name="ToiletButton"' in read('gui/ODIcons.imageset') or 'ToiletButton' in read('gui/ODIcons.imageset')
gui_cpp = read('source/render/Gui.cpp')
arrange = gui_cpp[gui_cpp.index('void Gui::arrangeRoomButtons('):]
arrange = arrange[:arrange.index('\n}\n')]
assert '"DormitoryButton", "ToiletButton", "HatcheryButton"' in arrange, 'the toilet button follows the dormitory in the action bar'
# Button names are unique per layout file
assert rooms_layout.count('name="ToiletButton"') == 1 and skill_layout.count('name="ToiletButton"') == 1

# 6. Research: preserve the published toilet skill id before the appended equipment research (tier II).
skill_type = read('source/game/SkillType.h')
skills = enum_names(skill_type, 'enum class SkillType')
assert skills.index('roomToilet') == 55 and skills[-1] == 'countSkill', skills
assert skills[55:65] == ['roomToilet', 'roomMerchant', 'roomHerbGarden', 'roomAlchemyLab',
                         'trapFineTools', 'trapMasterTools', 'spellSunthornCultivation', 'roomTavern', 'tavernBeer', 'roomInfirmary']
assert 'case SkillType::roomToilet:' in read('source/game/SkillType.cpp') and '"roomToilet"' in read('source/game/SkillType.cpp')
manager = read('source/game/SkillManager.cpp')
assert ('createSkill(mSkills, SkillType::roomToilet, std::vector<SkillType>{SkillType::roomDormitory});\n'
        '    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "ToiletButton", skill, 2, RoomType::toilet);') in manager
constructor = manager[manager.index('SkillManager::SkillManager()'):manager.index('SkillManager::~SkillManager()')]
registered = re.findall(r'createSkill\(mSkills, SkillType::(\w+),', constructor)
assert registered.count('roomToilet') == 1
assert len(registered) == 63, 'the combined research tree has 63 entries, found ' + str(len(registered))
skills_cfg = read('config/skills.cfg')
assert re.search(r'^    roomToilet\t250\s*$', skills_cfg, re.M), 'roomToilet costs 250 (tier II)'
# No research effect line for the toilet
effects = re.search(r'\[ResearchEffects\](.*?)\[/ResearchEffects\]', skills_cfg, re.S).group(1)
assert 'roomToilet' not in effects, 'the toilet has no research effect'
# The cost block names every entry; the tab totals are pinned by check_world_balance_tree.py
cost_block = re.search(r'^\[Skills\]\s*$(.*?)^\[/Skills\]', skills_cfg, re.M | re.S).group(1)
assert 'roomToilet' in [line.split()[0] for line in cost_block.splitlines() if line.split() and not line.startswith('#')]

# 7. AI: the keeper AI builds the toilet directly after the dormitory
ai = read('source/ai/KeeperAI.cpp')
wanted = ai[ai.index('static const std::vector<RoomType> wantedBuildings = {'):]
wanted = wanted[:wanted.index('};')]
order = re.findall(r'RoomType::(\w+)', wanted)
assert order[:3] == ['dormitory', 'toilet', 'treasury'], order
assert order.count('toilet') == 1

# 8. Research tree order: the toilet entry follows the casino entry in the tier II row
assert registered.index('roomCasino') + 1 == registered.index('roomToilet'), 'the toilet follows the casino in the tree'

# 9. No clean-once control: the window, its notifications and the room order are gone
assert not (root / 'gui/WindowRoomClean.layout').exists(), 'the clean-once window is removed'
assert 'WindowRoomClean' not in read('gui/ModeGame.layout')
assert 'askCleanRoom' not in read('source/network/ClientNotification.h') and 'roomCleanOrder' not in read('source/network/ServerNotification.h')
game_mode = read('source/modes/GameMode.cpp')
assert 'RoomClean' not in game_mode and 'mCleanRoomName' not in game_mode
pile_hover = game_mode[game_mode.index('static std::string getDirtPileHoverText'):game_mode.index('static std::string getRoomDirtHoverText')]
assert 'social::SocialGenerator::displayClassName(' in pile_hover, 'the pile hover names the creature class readably'

print('toilet room ok')
