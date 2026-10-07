#!/usr/bin/env python3
# Checks the rooster on the coop roof: after a random time he jumps on the roof of a coop of his own hatchery, sits
# there and crows (pose and sound) and jumps down again; he never stays up there (time limit, loading, pick up).
import re
from pathlib import Path

root = Path(__file__).resolve().parents[2]
chicken = (root / 'source/entities/ChickenEntity.cpp').read_text()
room = (root / 'source/rooms/RoomHatchery.cpp').read_text()
rooster_h = (root / 'source/rooms/HatcheryRooster.h').read_text()
rooster_cpp = (root / 'source/rooms/HatcheryRooster.cpp').read_text()
config = (root / 'config/rooms.cfg').read_text()


def body(text, signature):
    start = text.index(signature)
    return text[start:text.index('\n}\n', start)]


# Random time from the config (with defaults), a crow lasts a limited number of turns
assert 'static_cast<uint32_t>' in body(room, 'RoosterSettings RoomHatchery::getRoosterSettings(') or 'mCrowMin' in room
for key in ('HatcheryRoosterCrowMin', 'HatcheryRoosterCrowMax', 'HatcheryRoosterCrowTurns', 'HatcheryCoopRoofHeight',
            'HatcheryCoopPerchOffset'):
    assert re.search(r'^# ' + key + r'\s', config, re.M) and re.search(r'^\s+' + key + r'\s', config, re.M), key
assert 'Random::Uint(0, 1000)' in body(room, 'void RoomHatchery::beginRoosterMood(')
assert 'mSinceCrow >= context.mCrowInterval' in rooster_cpp and 'settings.mCrowTurns' in rooster_cpp

# The server computes the roof place, the client only shows the position it gets
roost = body(room, 'void RoomHatchery::roostOnRoof(')
assert 'getNearestCoop(' in roost and 'getPerchSpot(' in roost and 'getRoofHeight(' in roost and 'hopToRoof(' in roost
assert 'if(coopTile == nullptr)' in roost, 'a hatchery without a coop does not crash'
nearest = body(room, 'Tile* RoomHatchery::getNearestCoop(')
assert 'mCentralActiveSpotTiles' in nearest, 'only a coop of the own hatchery'
assert 'RoosterMood::crow' in room and 'ChickenPose::crow' in room and 'Hatchery/Crow' in room

# Down again: free ground spot at the coop, with and without a coop
down = body(room, 'void RoomHatchery::climbDown(')
assert 'if(!rooster->isOnRoof())' in down and 'getGroundSpot(' in down and 'hopDown(' in down
assert 'if(coopTile != nullptr)' in down, 'no crash when the coop is gone'
begin = body(room, 'void RoomHatchery::beginRoosterMood(')
assert 'climbDown(rooster)' in begin

# He never stays on the roof: not after the mood, not after loading (the mood is not saved), not when picked up
update = body(room, 'void RoomHatchery::updateRooster(')
guard = 'if(rooster->isOnRoof() && (rooster->getMood() != RoosterMood::crow))'
assert guard in update and 'climbDown(rooster);' in update[update.index(guard):update.index(guard) + 200]
assert update.index(guard) < update.index('HatcheryRooster::decide('), 'checked before the rooster decides'
assert 'mOnRoof = (mPosition.z > 0.3);' in chicken, 'the roof state is rebuilt after loading'
assert chicken.count('mOnRoof = false;') >= 3, 'picked up, lost a fight and jumped down reset the roof state'

# Not wanted any more: night, sleep, crow at a new day
for text in (rooster_h, rooster_cpp, room):
    for needle in ('isNight', 'newDayCrowOwed', 'RoosterMood::sleep', 'RoosterMood::call', 'RoosterMood::lead'):
        assert needle not in text, needle

print('rooster roof checks passed')
