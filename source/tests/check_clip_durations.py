"""Decision 853: clips play their plan length in game seconds, not in game turns (a turn is 1/1.4 s).

Pure text check, compiles nothing: the ClipSeconds keys with a doc line each, the clip update of MovableGameEntity, the
2 s get-up (arena KO, tavern, render), the innkeeper Pour over DrinkTurns, the shaman and pool attendant overrides."""
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
# Not changed on purpose: slap duel, box arc, combat attacks, doors
for clip in ('Slap', 'Attack1', 'Open', 'Close', 'Lid'):
    assert 'ClipSeconds' + clip not in values, 'ClipSeconds' + clip + ' must not exist'
assert values.get('PoolAttendantClipSeconds') == 2 and re.search(r'^#\s*PoolAttendantClipSeconds', rooms_cfg, re.M)
assert values.get('CreatureGetUpSeconds', 0) >= 2 and re.search(r'^#\s*CreatureGetUpSeconds', rooms_cfg, re.M)
assert values.get('InfirmaryShamanAnimationSeconds') == 2
# The 20 s transfer and CatchTime are untouched
assert values.get('GhostTransferSeconds') == 20

# The clip update: the clip time runs in game seconds for a clip with ClipSeconds
assert 'virtual double getClipSeconds(' in movable_h and '"ClipSeconds" + clip' in movable
assert 'addedTime = clipLength / mClipSeconds' in movable and 'gameSpeedFactor' in movable.split('addedTime = clipLength')[1][:120]
assert 'getAnimationName() == mPrevAnimationState' in movable, 'a fallback clip keeps the normal rate'

# Get-up: at least 2 s in the render, the arena KO and the tavern
assert 'CREATURE_GET_UP_ANIMATION_DURATION' not in render and 'getRoomConfigDouble("CreatureGetUpSeconds")' in render
assert 'GET_UP_TURNS' not in tavern and 'setSpotState(spot, TavernGuestState::getUp, getUpTurns())' in tavern
assert 'getRoomConfigDouble("CreatureGetUpSeconds")' in tavern and 'getRoomConfigDouble("CreatureGetUpSeconds")' in creature

# Innkeeper Pour lasts the whole serving time, the shaman and the attendant clips their configured time
assert re.search(r'clip == InnkeeperPose::pour\)\s*return [^;]*DRINK_TURNS_KEY[^;]*/ ODApplication::turnsPerSecond', innkeeper)
assert 'InfirmaryShamanAnimationSeconds' in shaman.split('InfirmaryShamanEntity::getClipSeconds')[1][:500]
assert 'PoolAttendantClipSeconds' in pool and 'CHAIR_SEAT_HEIGHT = 1.13 + 0.04' in pool
print('clip duration checks passed')
