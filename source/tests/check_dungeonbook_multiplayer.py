"""Check that every client gets and shows the same Dungeonbook picture (static check, no game needed).

What is checked here: the server is the only place that rolls an appearance, every path that tells a
client about a creature (add entity, join, load, late assignment) carries the appearance for every seat
alike, and the code that turns appearance and name into pixels and remarks has no input that could differ
between clients (no random numbers, clock, hash of the standard library, seat or local player).

The runtime part (packet round trips of two clients and a late joiner fed from one server state, same
picture key, same selected JPEG, same remarks) is the boost test 00-DungeonbookMultiplayer. A real run with two
game instances is not part of this check; that stays a manual test.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(name):
    return (repo / name).read_text()


def body(source, signature):
    start = source.index(signature)
    brace = source.index('\n{\n', start)
    end = source.index('\n}\n', brace)
    return source[brace:end]


creature = read('source/entities/Creature.cpp')

# The server alone rolls: random picks only inside the server side assign function
assign = body(creature, 'void Creature::assignAppearance(bool firstSpawn)')
assert re.search(r'^\s+if\(!getIsOnServerMap\(\)', assign, re.M), 'assignAppearance must return early off the server map'
assert 'pickRandom(' in assign and 'getAppearanceRandom' in assign
assert 'Random::Uint' in creature[:creature.index('void Creature::assignAppearance(bool firstSpawn)')]
for other in re.finditer(r'pickRandom\(', creature):
    assert other.start() > creature.index('void Creature::assignAppearance(bool firstSpawn)'), 'pickRandom outside assign'
assert creature.count('pickRandom(') == 1, 'only one place may roll an appearance'

# Every way a creature reaches a client goes through exportToPacket, and the token is not seat dependent
fire = body(creature, 'void Creature::fireAddEntity(Seat* seat, bool async, NodeType nt )')
assert fire.count('exportToPacket(') == 2, 'async and sync add entity both use exportToPacket'
export_full = body(creature, 'void Creature::exportToPacket(ODPacket& os, const Seat* seat) const')
line = [l for l in export_full.splitlines() if 'toToken(mAppearance)' in l]
assert len(line) == 1 and line[0].startswith('    os <<'), 'the token is written at top level, for every seat'
assert 'seat' not in line[0]
assert 'getCreatureFromPacket' in read('source/entities/EntityLoading.cpp')
get_from_packet = body(creature, 'Creature* Creature::getCreatureFromPacket(GameMap* gameMap, ODPacket& is)')
assert 'importFromPacket(is)' in get_from_packet

# Late assignment: sent to the seats with vision of the creature, the others get it with the next full data
retry = body(creature, 'void Creature::retryAppearance()')
assert 'mSeatsWithVisionNotified' in retry and 'ServerNotificationType::creatureAppearance' in retry
client = read('source/network/ODClient.cpp')
handler = client[client.index('case ServerNotificationType::creatureAppearance:'):]
handler = handler[:handler.index('break;')]
assert 'setAppearanceFromServer(' in handler

# Join and load send visible creatures the same way: no separate creature path that skips the appearance
server = read('source/network/ODServer.cpp')
assert 'creatureAppearance' not in server, 'the appearance has no join path of its own, it rides on the creature data'
assert not re.search(r'[Cc]reature[^;\n]*exportToPacket\(', server), 'creature data is only sent via fireAddEntity'

# The pixels and remarks are a function of the appearance and the name only
forbidden = (r'\bRandom::', r'\brand\(', r'\bsrand\(', r'std::hash', r'<random>', r'\btime\(', r'std::chrono', r'getLocalPlayer',
             r'getSeat\(', r'ODFrameListener', r'getTurnNumber', r'std::random_device')
for name in ('source/render/DungeonbookQuirks.cpp',
             'source/game/CreatureAppearance.cpp', 'source/render/CreatureAppearancePicture.cpp'):
    text = re.sub(r'//.*', '', read(name))
    # Only the appearance picture code may be checked for the random pick: CreatureAppearance takes the
    # random function as a parameter and never calls the global generator itself
    for pattern in forbidden:
        if pattern == 'std::chrono' and name.endswith('CreatureAppearancePicture.cpp'):
            # The picture code only uses a clock to decide when failed files are tried again, never for pixels
            for line in text.splitlines():
                if 'std::chrono' in line:
                    assert any(word in line for word in ('#include', 'mLastRetry', 'steady_clock', 'RETRY_SECONDS')), line
            continue
        assert not re.search(pattern, text), '%s uses %s' % (name, pattern)

# The remark choice and the stable look use the fixed hash
quirks = read('source/render/DungeonbookQuirks.cpp')
assert 'stableHash(' in quirks

# The profile asks for the picture on every fill and sets it right away
fill = body(creature, 'float Creature::fillProfilePage(CEGUI::Window* page)')
assert 'getCreatureAppearanceImage(getName(), mAppearance)' in fill
assert 'appearanceImage' in fill

# The tests that give the runtime part are part of the build
tests = read('source/tests/CMakeLists.txt')
for test in ('00-DungeonbookMultiplayer', '00-DungeonbookQuirks', '00-CreatureAppearance', '00-PortraitCatalog',
             '00-WholePortraitJpeg'):
    assert 'add_boost_test(%s' % test in tests, test

print('dungeonbook multiplayer wiring ok')

# The book receives the server's complete allied roster, including creatures outside client vision.
roster = server[server.index('    void notifyDungeonbookRoster(GameMap* gameMap, Player* player)'):]
roster = roster[:roster.index('    //! \\brief Sends the current patients')]
assert 'gameMap->getCreatures()' in roster
assert 'owner != nullptr && owner->getPlayer() != nullptr && seat->isAlliedSeat(owner) && creature->isAlive()' in roster
assert roster.index('if(player == nullptr)') < roster.index('player->getSeat()')
for getter in ('getAttackRating()', 'getDefenseRating()', 'getRawDamagePerSecond()', 'getTileSightRadius()',
               'getSkillPointsEarned()', 'getSkillPointsSpent()'):
    assert getter in roster, getter + ' must be included in actual stats'
request = server[server.index('case ClientNotificationType::askDungeonbookRoster:'):]
request = request[:request.index('case ClientNotificationType::askCreatureInfos:')]
assert 'mServerState != ServerState::StateGame' in request
assert request.index('clientSocket->getPlayer() == nullptr') < request.index('clientSocket->getPlayer()->getSeat()')
assert 'mSeatsWithVisionNotified' not in roster and 'getIsOnMap()' not in roster
assert 'keeper->getNick()' in roster and 'getStatsText(owner)' in roster
assert 'stats.erase(debug,' in roster and 'stats.find("\\nMood: ", debug)' in roster, 'keep mood values without developer details'
assert 'owner->getPlayer() != nullptr' in roster, 'non-player seats are excluded'
server_fields = ('creature->getName()', 'creature->getDefinition()->getClassName()', 'keeperName',
                 'CreatureAppearanceLogic::toToken(creature->getAppearance())', '<< stats',
                 'creature->getLevel()', 'creature->getStrength()', 'creature->getDexterity()',
                 'creature->getLife()', 'creature->getMana()', 'creature->getSkillListText()',
                 'creature->getEquipmentText()', 'creature->getSkillPathText()', 'creature->getCritChance()',
                 'creature->getAttackRating()', 'creature->getDefenseRating()',
                 'creature->getPhysicalDefense()', 'creature->getMagicalDefense()', 'creature->getElementDefense()',
                 'creature->getDefinition()->isWorker()', 'creature->getDefinition()->isChampion()', 'unhappy')
wire = roster[roster.index('notification->mPacket << creature->getName()'):]
positions = [wire.index(field) for field in server_fields]
assert positions == sorted(positions), 'server snapshot field order changed'
client_case = client[client.index('case ServerNotificationType::dungeonbookRoster:'):]
client_case = client_case[:client_case.index('break;')]
client_fields = ('entry.name', 'entry.className', 'entry.keeper', 'entry.appearance', 'entry.stats', 'entry.level',
                 'entry.strength', 'entry.dexterity', 'entry.life', 'entry.mana', 'entry.skills',
                 'entry.equipment', 'entry.path', 'entry.critical', 'entry.attackRating', 'entry.defenseRating',
                 'entry.physicalDefense', 'entry.magicalDefense', 'entry.elementDefense',
                 'entry.worker', 'entry.champion', 'entry.unhappy')
positions = [client_case.index(field) for field in client_fields]
assert positions == sorted(positions), 'client snapshot field order differs from server'
assert 'setDungeonbookRoster(entries)' in client_case
assert 'if(!(packetReceived >>' in client_case, 'incomplete snapshots must not replace the roster'
assert 'if(sock->getDungeonbookRosterOpen())' in server
window = read('source/render/SocialWindow.cpp')
assert 'askDungeonbookRoster, true' in window and 'askDungeonbookRoster, false' in window
assert 'getDungeonbookRoster()' in window and '"Keeper: " + entry.keeper' in window
# Roster rendering must not require a visible map entity: every page works with the roster entry alone, a creature
# known on this side only adds its relationships, its mood level and its items
assert 'getCreature(selected->name)' not in window
assert window.count('mGameMap.getCreature(') == 4, 'every use of a map entity in the book is one of the four below'
assert 'const CreatureMoodLevel level = creature == nullptr ? CreatureMoodLevel::Unknown' in window
assert 'holder->setVisible(creature != nullptr);' in window and 'fallback->setVisible(creature == nullptr);' in window
assert 'Creature::fillItemSlotWindows(creature, slots, true)' in window and 'if(creature == nullptr)' in window
assert 'if(creature != nullptr)\n            token = CreatureAppearanceLogic::toToken' in window
print('allied Dungeonbook snapshot field order and subscription wiring ok')

# Roster messages are enabled only after both peers agree; absent optional fields default to false.
socket_h = read('source/network/ODSocketClient.h')
socket_cpp = read('source/network/ODSocketClient.cpp')
assert 'mSupportsDungeonbookRoster(false)' in socket_h and 'mSupportsDungeonbookRoster = false;' in socket_cpp
assert 'bool supportsDungeonbookRoster() const' in socket_h
assert 'if(!supportsDungeonbookRoster())' in client_case
assert '!clientSocket->supportsDungeonbookRoster()' in request
assert 'clientSocket->setSupportsDungeonbookRoster(dungeonbookRoster)' in server
assert 'setSupportsDungeonbookRoster(false)' in client
assert 'setSupportsDungeonbookRoster(dungeonbookRoster)' in client
assert 'if(dungeonbookRoster)\n                packSend << dungeonbookRoster;' in client
assert server.count('packetSend << clientSocket->supportsDungeonbookRoster();') == 1
assert server.count('packetSend << client->supportsDungeonbookRoster();') == 1
assert 'packetSend << ServerNotificationType::pickNick << mServerMode << true << true << true << true << true << true << true;' in server
print('allied roster capability negotiation and null-seat filter verified')
