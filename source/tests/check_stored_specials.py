"""Static checks of the special boxes: every box type has an editor button and a game button, a delivered
special is kept for the player (not applied at once), the stored specials travel to the client and are saved
with the seat. It does not start a game."""
from pathlib import Path
import re
import sys

repo = Path(__file__).resolve().parents[2]


def read(relative):
    return (repo / relative).read_text(encoding='utf-8')


def function(text, signature):
    start = text.index(signature)
    end = text.index('{', start) + 1
    depth = 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


entity = read('source/entities/GiftBoxEntity.h')
types = re.findall(r'(\w+),', entity[entity.index('enum class GiftBoxType'):entity.index('nbTypes')])
check(types[0] == 'skill' and len(types) == 13, 'GiftBoxType starts with skill and holds the twelve specials: %s' % types)
specials = types[1:]

bonus = read('source/giftboxes/GiftBoxBonus.cpp')
for name in ('getDisplayName', 'getDescription'):
    body = function(bonus, 'std::string GiftBoxBonus::%s(' % name)
    for special in specials:
        check('GiftBoxType::%s:' % special in body, '%s names %s' % (name, special))

editor = read('source/modes/EditorMode.cpp')
editor_layout = read('gui/ModeEditor.layout')
gui = read('source/render/Gui.cpp')
for special in specials:
    check('askCreateGiftBox(GiftBoxType::%s)' % special in editor, 'the editor has a button action for %s' % special)
check(editor_layout.count('BoxButton" >') == len(specials), 'the editor layout holds one box button per special')
check(len(re.findall(r'EDITOR_BOX_\w+_BUTTON = ', gui)) == len(specials), 'one editor box button path per special')
check(len(re.findall(r'connectGuiAction\(Gui::EDITOR_BOX_', editor)) == len(specials), 'every editor box button is connected')

server = read('source/network/ODServer.cpp')
create = server[server.index('case ClientNotificationType::editorCreateGiftBox:'):server.index('case ClientNotificationType::editorCreateGiftBox:') + 1200]
check('GiftBoxType::skill' in create and 'GiftBoxType::nbTypes' in create, 'the server accepts every special box type of the editor')

game_layout = read('gui/ModeGame.layout')
buttons = re.findall(r'name="Special(\d+)"', game_layout)
check(buttons == [str(i) for i in range(1, len(specials) + 1)], 'the game layout holds one special button per type, numbered by type: %s' % buttons)
game_mode = read('source/modes/GameMode.cpp')
check('askUseSpecial' in function(game_mode, 'bool GameMode::useSpecial('), 'a pressed special button asks the server to use it')
check('refreshSpecialButtons();' in function(game_mode, 'void GameMode::onFrameStarted('), 'the special buttons follow the stored count every frame')
check('ClientNotificationType::askUseSpecial:' in server and 'useStoredSpecial(' in server, 'the server uses a stored special for its owner')

temple = function(read('source/rooms/RoomDungeonTemple.cpp'), 'void RoomDungeonTemple::notifyCarryingStateChanged(')
check('addStoredSpecial(' in temple and 'GiftBoxType::skill' in temple and 'applyEffect()' in temple,
      'a human keeper keeps the delivered special, the research box and other seats apply it at once')

seat = read('source/game/Seat.cpp')
seat_data = read('source/game/SeatData.cpp')
check(function(seat_data, 'bool SeatData::importFromPacketForUpdate(').count('mStoredSpecials') >= 2
      and function(seat_data, 'void SeatData::exportToPacketForUpdate(').count('mStoredSpecials') >= 2,
      'the stored specials travel with the changing seat data')
check('[StoredSpecials]' in function(seat, 'bool Seat::exportSeatToStream(')
      and 'str == "[StoredSpecials]"' in function(seat, 'bool Seat::importSeatFromStream('),
      'the stored specials are saved and loaded with the seat (the block is optional, old savegames still load)')
use = function(seat, 'bool Seat::useStoredSpecial(')
check('GiftBoxBonus::applyBonus(' in use and 'erase(' in use, 'using a special applies it once and removes it')

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    sys.exit(1)
print('check_stored_specials: OK')
