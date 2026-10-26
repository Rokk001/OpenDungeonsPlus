"""Static wiring check for the later stages of level scripting: the make action, the time limit with
its countdown, the creature event conditions, the story state conditions, the victory statistics and
the region test level.

The parser and the writer are run by check_level_script.py; this script checks that the pieces
that need the running game are connected, so a missing hook is found without playing.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(relative):
    return (repo / relative).read_text(encoding='utf-8')


def function(source, signature):
    start = source.index(signature)
    brace = source.index('{', start)
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == '{':
            depth += 1
        elif source[index] == '}':
            depth -= 1
            if depth == 0:
                return source[start:index + 1]
    raise AssertionError('unterminated ' + signature)


runner = read('source/gamemap/LevelScriptRunner.cpp')
script_h = read('source/gamemap/LevelScript.h')
script_cpp = read('source/gamemap/LevelScript.cpp')
gamemap = read('source/gamemap/GameMap.cpp')
gamemap_h = read('source/gamemap/GameMap.h')
map_handler = read('source/gamemap/MapHandler.cpp')
server_h = read('source/network/ServerNotification.h')
server_cpp = read('source/network/ServerNotification.cpp')
client = read('source/network/ODClient.cpp')
client_h = read('source/network/ODClient.h')
game_mode = read('source/modes/GameMode.cpp')
game_layout = read('gui/ModeGame.layout')

# make: the action unlocks the skill through the seat, as research does
make = function(runner, 'void makeSkillAvailable(')
assert 'Skills::fromString(action.mText)' in make
assert 'seat->addSkill(skillType)' in make
assert 'seat->isSkillDone(skillType)' in make
assert 'case LevelScriptActionType::make:' in runner
assert 'type == "make"' in script_cpp and 'case LevelScriptActionType::make:' in script_cpp

# time limit: action, script state, server check and countdown
assert 'case LevelScriptActionType::timeLimit:' in runner and 'gameMap.setScriptTimeLimit(' in runner
assert 'type == "timelimit"' in script_cpp and 'key == "TimeLimit"' in script_cpp
assert '"TimeLimit\\t"' in script_cpp
check = function(gamemap, 'void GameMap::checkGameDuration()')
assert 'mLevelScript->getTimeLimitSeconds()' in check
assert 'sendTimeLimit(' in check
assert check.index('sendTimeLimit(') < check.index('notifyTimeUp')
assert 'Time is up!' in check
set_limit = function(gamemap, 'void GameMap::setScriptTimeLimit(')
assert 'mGameDurationAnnounced = false' in set_limit
assert 'TIME_LIMIT_REMOVED' in set_limit
send = function(gamemap, 'void GameMap::sendTimeLimit(')
assert 'ServerNotificationType::timeLimit' in send and 'getIsHuman()' in send
assert 'rebaseTimeLimit(' in map_handler
enum_body = server_h.split('enum class ServerNotificationType')[1].split('};')[0]
assert enum_body.rstrip().endswith('tavernPayer') and enum_body.index('tavernWindow') < enum_body.index('tavernPayer')
enum_body = enum_body[:enum_body.index('Answer to askTavernWindow')].rsplit('//!', 1)[0].rstrip().rstrip(',')
assert re.findall(r'^\s*([A-Za-z_]\w*)\s*,?\s*(?://.*)?$', enum_body, re.M)[-5:] == ['campaignVictory', 'merchantWindow', 'merchantSettings', 'labWindow', 'labSettings'], 'campaignVictory must be appended after the existing notifications'
assert 'case ServerNotificationType::timeLimit:' in server_cpp
handler = client[client.index('case ServerNotificationType::timeLimit:'):]
handler = handler[:handler.index('break;')]
assert 'mTimeLimitSeconds' in handler
assert 'getTimeLimitSeconds' in client_h
assert 'mTimeLimitSeconds = -1;' in function(client, 'case ServerNotificationType::clientAccepted:') or 'mTimeLimitSeconds = -1;' in client
assert 'getTimeLimitSeconds()' in game_mode and 'HorizontalPipe/TimeLimitDisplay' in game_mode
assert 'name="TimeLimitDisplay"' in game_layout

# creature event conditions: the counters are filled where the event happens
creature = read('source/entities/Creature.cpp')
stats_h = read('source/game/SeatStatistics.h')
for counter in ('mCreaturesLost', 'mCreaturesPickedUp', 'mCreaturesDropped', 'mCreaturesSlapped'):
    assert counter in stats_h and counter + ' = 0;' in stats_h, counter
assert '++getSeat()->getStatistics().mCreaturesPickedUp' in function(creature, 'void Creature::pickup()')
assert '++getSeat()->getStatistics().mCreaturesDropped' in function(creature, 'void Creature::drop(')
assert '++getSeat()->getStatistics().mCreaturesSlapped' in function(creature, 'void Creature::slap()')
assert '++getSeat()->getStatistics().mCreaturesLost' in function(creature, 'double Creature::takeDamage(') or     '++getSeat()->getStatistics().mCreaturesLost' in creature
for name in ('happy', 'angry', 'atlevel', 'lost', 'pickedup', 'dropped', 'slapped'):
    assert 'type == "%s"' % name in script_cpp, name
for kind in ('happyCreatures', 'angryCreatures', 'creaturesAtLevel', 'creaturesLost', 'creaturesPickedUp',
             'creaturesDropped', 'creaturesSlapped'):
    assert 'case LevelScriptConditionType::%s:' % kind in runner, kind
    assert 'case LevelScriptConditionType::%s:' % kind in script_cpp, kind

# victory statistics: sent at the win, carried to the campaign menu
player = read('source/game/Player.cpp')
send = function(player, 'void Player::sendLevelStatistics(')
assert 'ServerNotificationType::levelStatistics' in send and 'levelWon' in send
assert 'sendLevelStatistics(false)' in function(player, 'void Player::notifyDefeat(')
won = function(gamemap, 'void GameMap::addWinningSeat(')
assert 'player->sendLevelStatistics(true)' in won
assert won.index('sendLevelStatistics(true)') < won.index('Campaign::getSingleton().onLevelWon()')
levels_handler = client[client.index('case ServerNotificationType::levelStatistics:'):]
levels_handler = levels_handler[:levels_handler.index('break;')]
assert 'Campaign::getSingleton().setLevelSummary(' in levels_handler and 'debriefingSeatSummary(' in levels_handler
campaign_h = read('source/game/Campaign.h')
campaign_cpp = read('source/game/Campaign.cpp')
assert 'setLevelSummary' in campaign_h and 'getLevelSummary' in campaign_h
assert 'mLevelSummary.clear()' in function(campaign_cpp, 'void Campaign::startLevel(')
assert 'mLevelSummary.clear()' in function(campaign_cpp, 'void Campaign::clearPlayedLevel(')
menu = read('source/modes/MenuModeCampaign.cpp')
assert 'campaign.getLevelSummary()' in menu
assert menu.index('campaign.getLevelSummary()') < menu.index('campaign.clearPlayedLevel()')

# the region test level: a skirmish with 100 start mana, found by the level list
level = read('levels/skirmish/TestRegionScripting.level')
assert 'Region scripting' in level
assert re.search(r'^mana	100$', level, re.M), 'start mana must be 100'
section = level[level.index('[Triggers]'):level.index('[/Triggers]')]
for word in ('Cond	pickedup', 'Cond	dropped', 'Cond	slapped', 'Cond	happy', 'Cond	lost', 'Cond	kills',
             'Cond	claimed', 'Cond	region', 'Cond	gold', 'Action	make', 'Action	reveal',
             'Action	timelimit', 'Action	win'):
    assert word in section, word

# story state: the conditions are evaluated by the runner and the portal and class state reach the game
for kind in ('seatDefeated', 'ownsCreature', 'creatureHealth', 'spellKnown', 'trapsBuilt', 'roomTiles', 'largestRoom',
             'portalActive', 'creatureAlive', 'creatureReached'):
    assert 'case LevelScriptConditionType::%s:' % kind in runner, kind
    assert 'case LevelScriptConditionType::%s:' % kind in script_cpp, kind
for kind in ('portalStatus', 'creatureAvailable', 'removeCreature'):
    assert 'case LevelScriptActionType::%s:' % kind in runner, kind
    assert 'case LevelScriptActionType::%s:' % kind in script_cpp, kind
for name in ('defeated', 'owns', 'health', 'spell', 'built', 'roomtiles', 'roomsize', 'portal', 'alive', 'reached', 'available', 'remove'):
    assert 'type == "%s"' % name in script_cpp or '(type == "%s")' % name in script_cpp, name
assert 'key == "PortalOff"' in script_cpp and 'key == "Block"' in script_cpp
assert 'mPortalOff' in script_h and 'mBlocked' in script_h
assert 'isPortalOff(getSeat()->getId())' in read('source/rooms/RoomPortal.cpp')
assert 'isCreatureBlocked(getId()' in read('source/game/Seat.cpp')

# the story test level: a skirmish that uses the story state conditions, a portal stone and a terrain change
story = read('levels/skirmish/TestLevelScripting.level')
assert 'Level scripting' in story
story_section = story[story.index('[Triggers]'):story.index('[/Triggers]')]
for word in ('Cond	alive', 'Cond	reached', 'Cond	portal', 'Cond	stone', 'Action	portal', 'Action	stonecreate',
             'Action	terrain', 'Action	spawn'):
    assert word in story_section, word

# scripted possession: the creature is possessed by the human keeper, and a level that starts with one is free of mana costs
assert 'case LevelScriptActionType::possessCreature:' in runner and 'startPossession(' in runner
assert 'case LevelScriptConditionType::possessedInRegion:' in runner
assert 'type == "possess"' in script_cpp and 'type == "possessed"' in script_cpp
assert 'key == "FreePossession"' in script_cpp and 'os << "FreePossession' in script_cpp
assert 'isFreePossession()' in read('source/creatureaction/CreatureActionPossessed.cpp')
assert 'script.setFreePossession(true)' in runner

# kept minion: the strongest fighter is chosen by the keepminion action, saved with the campaign progress and
# given out when the next level of the campaign starts
campaign = read('source/game/Campaign.cpp')
assert 'case LevelScriptActionType::keepMinion:' in runner and 'setKeptMinion(' in runner
assert 'type == "keepminion"' in script_cpp and 'os << "keepminion' in script_cpp
assert 'takeKeptMinion(' in runner and 'KeptMinion' in campaign
assert 'LevelScriptRunner::spawnKeptMinion(*gameMap);' in read('source/network/ODServer.cpp')

print('level script final wiring: ok')
