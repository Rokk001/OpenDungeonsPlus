"""Decision 853: clips play their plan length in game seconds, not in game turns (a turn is 1/1.4 s).

Pure text check, compiles nothing: the ClipSeconds keys with a doc line each, the clip update of MovableGameEntity, the
6 s get-up of decision 857 (arena KO, tavern, render) after the 30 s lying time, the innkeeper Pour over DrinkTurns, the
shaman and pool attendant overrides, and the slap clips of the slap duel stretched to the slap length the tavern draws
(decision 856, setTimedAnimationState with the playing time sent to the clients)."""
import math
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[2]


def read(name):
    return (root / name).read_text(encoding='utf-8')


rooms_cfg = read('config/rooms.cfg')
global_cfg = read('config/global.cfg')
movable = read('source/entities/MovableGameEntity.cpp')
movable_h = read('source/entities/MovableGameEntity.h')
creature = read('source/entities/Creature.cpp')
tavern = read('source/rooms/RoomTavern.cpp')
render = read('source/render/RenderManager.cpp')
innkeeper = read('source/entities/InnkeeperEntity.cpp')
shaman = read('source/entities/InfirmaryShamanEntity.cpp')
pool = read('source/entities/PoolAttendantEntity.cpp')

block = re.search(r'^\[Rooms\]\s*$(.*?)^\[/Rooms\]', rooms_cfg, re.M | re.S).group(1)
values = {}
for line in block.splitlines():
    words = line.split()
    if len(words) >= 2 and not words[0].startswith('#'):
        try:
            values[words[0]] = float(words[1])
        except ValueError:
            pass

# The plan lengths in seconds
CLIPS = {'Scared': 1, 'Beam': 1, 'Throw': 1, 'Empty': 1, 'RubHands': 2, 'Drink': 2, 'Dice': 2, 'ArmWrestle': 2,
         'KnockedOut': 2, 'Vomit': 2, 'Hangover': 2}
for clip, seconds in CLIPS.items():
    key = 'ClipSeconds' + clip
    assert values.get(key) == seconds, key + ' must be ' + str(seconds)
    assert key in rooms_cfg.split('[Rooms]')[0] or re.search(r'^#.*\b' + key + r'\b', rooms_cfg, re.M), key + ' needs a doc line'
# No fixed key: the slap clips take the slap length drawn per slap; box arc, combat attacks and doors stay as they are
for clip in ('Slap', 'SitSlap', 'SitSlapped', 'Attack1', 'Open', 'Close', 'Lid'):
    assert 'ClipSeconds' + clip not in values, 'ClipSeconds' + clip + ' must not exist'
assert values.get('PoolAttendantClipSeconds') == 2 and re.search(r'^#\s*PoolAttendantClipSeconds', rooms_cfg, re.M)
# Decision 857: the get-up after a knock-out lasts 6 s (tavern and arena alike)
assert values.get('CreatureGetUpSeconds') == 6 and re.search(r'^#\s*CreatureGetUpSeconds.*\b6\b', rooms_cfg, re.M)
assert values.get('InfirmaryShamanAnimationSeconds') == 2
# The 20 s transfer and CatchTime are untouched
assert values.get('GhostTransferSeconds') == 20

# The clip update: the clip time runs in game seconds for a clip with ClipSeconds
assert 'virtual double getClipSeconds(' in movable_h and '"ClipSeconds" + clip' in movable
assert 'addedTime = clipLength / mClipSeconds' in movable and 'gameSpeedFactor' in movable.split('addedTime = clipLength')[1][:120]
assert 'getAnimationName() == mPrevAnimationState' in movable, 'a fallback clip keeps the normal rate'

# A playing time chosen at run time: it wins over ClipSeconds<Clip>, holds for its clip and travels to the clients
odclient = read('source/network/ODClient.cpp')
assert 'void setTimedAnimationState(const std::string& state, double clipSeconds, bool loop,' in movable_h
timed = movable[movable.index('void MovableGameEntity::setTimedAnimationState('):]
timed = timed[:timed.index('\n}') + 2]
assert 'mPendingTimedClipSeconds = std::max(0.0, clipSeconds);' in timed and timed.index('setAnimationState(state') < timed.rindex('mPendingTimedClipSeconds = 0.0;')
set_state = movable[movable.index('void MovableGameEntity::setAnimationState('):movable.index('void MovableGameEntity::startAnimationClip(')]
assert set_state.index('mTimedClipSeconds = mPendingTimedClipSeconds;') < set_state.index('if(getIsOnServerMap())')
assert 'else if(state != mTimedClip)' in set_state and 'mClipSecondsFor.clear();' in set_state
assert '(state == mTimedClip) ? mTimedClipSeconds : 0.0' in set_state, 'the server sends the playing time'
assert re.search(r'mClipSeconds = \(\(mTimedClipSeconds > 0\.0\) && \(mTimedClip == mPrevAnimationState\)\) \?\s*mTimedClipSeconds : getClipSeconds\(mPrevAnimationState\);', movable)
fire = movable[movable.index('void MovableGameEntity::fireObjectAnimationState('):]
fire = fire[:fire.index('queueServerNotification')]
assert 'serverNotification->mPacket << clipSeconds;' in fire
client = odclient[odclient.index('case ServerNotificationType::setObjectAnimationState:'):]
client = client[:client.index('break;\n        }')]
assert 'OD_ASSERT_TRUE(packetReceived >> clipSeconds);' in client and \
    'obj->setTimedAnimationState(animState, clipSeconds, loop, Ogre::Vector3::ZERO, playIdleWhenAnimationEnds);' in client

# The slap duel: the slapper's SitSlap takes the whole slap, the target's SitSlapped the rest of it after the hit
duel = tavern[tavern.index('void RoomTavern::playDuelTurn('):tavern.index('void RoomTavern::cheerSpectators(')]
assert re.search(r'slapper->setTimedAnimationState\(EntityAnimation::sit_slap_anim,\s*static_cast<double>\(clock\.mSlapTurns\) / ODApplication::turnsPerSecond', duel)
assert re.search(r'target->setTimedAnimationState\(EntityAnimation::sit_slapped_anim,\s*static_cast<double>\(std::max\(clock\.mTurnsLeft, 1\)\) / ODApplication::turnsPerSecond', duel)
assert 'setAnimationState(EntityAnimation::sit_slap' not in tavern, 'every slap clip is timed'

# Get-up: 6 s in the render, the arena KO and the tavern, each after its lying time
assert 'CREATURE_GET_UP_ANIMATION_DURATION' not in render and 'getRoomConfigDouble("CreatureGetUpSeconds")' in render
assert 'GET_UP_TURNS' not in tavern and 'setSpotState(spot, TavernGuestState::getUp, getUpTurns())' in tavern
assert 'getRoomConfigDouble("CreatureGetUpSeconds")' in tavern and 'getRoomConfigDouble("CreatureGetUpSeconds")' in creature
arena = creature.split('if(arenaFight)', 1)[1].split('else', 1)[0]
assert re.search(r'mKoTurnCounter = ConfigManager::getSingleton\(\)\.getRoomConfigDouble\("ArenaKnockOutSeconds"\)\s*\*\s*ODApplication::turnsPerSecond\s*'
                 r'\+\s*std::ceil\(ConfigManager::getSingleton\(\)\.getRoomConfigDouble\("CreatureGetUpSeconds"\)\s*\*\s*ODApplication::turnsPerSecond\);', arena), \
    'the arena loser lies ArenaKnockOutSeconds and then gets up'
turns_per_second = float(re.search(r'double ODApplication::turnsPerSecond = ([\d.]+);', read('source/ODApplication.cpp')).group(1))
get_up_turns = math.ceil(values['CreatureGetUpSeconds'] * turns_per_second)
assert get_up_turns == 9 and 6.0 <= get_up_turns / turns_per_second < 6.0 + 1.0 / turns_per_second, 'the get-up lasts 6 s rounded up to whole turns'
arena_counter = values['ArenaKnockOutSeconds'] * turns_per_second + get_up_turns
# The arena loser lies until the counter reaches the get-up turns: 30 s, then 6 s getting up
assert abs((arena_counter - get_up_turns) / turns_per_second - 30.0) < 1e-9 and values['ArenaKnockOutSeconds'] == 30

# Innkeeper Pour lasts the whole serving time, the shaman and the attendant clips their configured time
assert re.search(r'clip == InnkeeperPose::pour\)\s*return [^;]*DRINK_TURNS_KEY[^;]*/ ODApplication::turnsPerSecond', innkeeper)
assert 'InfirmaryShamanAnimationSeconds' in shaman.split('InfirmaryShamanEntity::getClipSeconds')[1][:500]
assert 'PoolAttendantClipSeconds' in pool and 'CHAIR_SEAT_HEIGHT = 1.13 + 0.04' in pool
print('clip duration checks passed')
