#!/usr/bin/env python3
# Static checks of the server side chicken life cycle wiring (the rules themselves are covered by
# the 00-HatcheryCycle unit test).
from pathlib import Path

root = Path(__file__).resolve().parents[2]
chicken_h = (root / 'source/entities/ChickenEntity.h').read_text()
chicken = (root / 'source/entities/ChickenEntity.cpp').read_text()
room = (root / 'source/rooms/RoomHatchery.cpp').read_text()
food = (root / 'source/creatureaction/CreatureActionSearchFood.cpp').read_text()
client = (root / 'source/network/ODClient.cpp').read_text()
notif = (root / 'source/network/ServerNotification.h').read_text()
config = (root / 'config/rooms.cfg').read_text()


def body(text, start):
    i = text.index(start)
    return text[i:text.index('\n}\n', i)]


# Only a free hen is food: the rooster, chicks and eggs are skipped everywhere food is chosen.
assert 'isFree() && (mKind == ChickenKind::hen)' in chicken_h
assert '!isEdible()' in body(chicken, 'bool ChickenEntity::eatChicken')
assert '!chicken->isEdible()' in body(room, 'bool RoomHatchery::useRoom')
assert '!chicken->isEdible()' in food

# Old saves have no kind: the chicken stays a hen (the kind is read optionally after the position).
imp = body(chicken, 'bool ChickenEntity::importFromStream')
assert 'mKind = static_cast<ChickenKind>(kind)' in imp and 'is.clear()' in imp
assert 'mKind(ChickenKind::hen)' in chicken

# Clients get the kind with the entity and a small event when it changes.
assert 'chickenKindChanged' in notif and 'chickenKindChanged' in client
assert 'ServerNotificationType::chickenKindChanged' in body(chicken, 'void ChickenEntity::setKind')
assert 'exportToPacket' in chicken_h and 'importFromPacket' in chicken_h

# Nothing appears without a source: coop spawn only for an empty hatchery or a missing rooster.
doUpkeep = body(room, 'void RoomHatchery::doUpkeep')
assert 'needCoopHen' in doUpkeep and 'needCoopRooster' in doUpkeep
assert doUpkeep.count('spawnFromCoop(') == 2
assert 'new ChickenEntity' not in doUpkeep

# Values come from the config.
for key in ('HatcheryLayMin', 'HatcheryLayMax', 'HatcheryHatchTurns', 'HatcheryGrowTurns',
            'HatcheryTilesPerChicken', 'HatcheryChickenSpawnRate'):
    assert key in config and key in room, key

print('hatchery life cycle checks passed')

# Breeding needs care: lay faster when claimed, lit and without enemies; eggs wait while enemies stand in the hatchery
cycle = (root / 'source/rooms/HatcheryCycle.cpp').read_text()
room_cpp = (root / 'source/rooms/RoomHatchery.cpp').read_text()
cfg = (root / 'config/rooms.cfg').read_text()
assert 'wellCared' in cycle and 'canHatch' in cycle
assert 'HatcheryCycle::withCare' in room_cpp and 'HatcheryCycle::canHatch(counts, care.mEnemies)' in room_cpp
assert 'HatcheryCareLayPercent' in cfg and 'HatcheryCareLightRadius' in cfg

# Enemies trample eggs, own creatures never eat them
cycle_h = (root / 'source/rooms/HatcheryCycle.h').read_text()
assert 'tramples' in cycle_h and 'egg->trample(enemy)' in room_cpp
assert 'HatcheryTramplePercent' in cfg and 'HatcheryTrampleRadius' in cfg
assert 'bool ChickenEntity::trample' in chicken and 'ChickenKind::egg' in chicken[chicken.index('bool ChickenEntity::trample'):][:200]
# only enemies are collected for trampling (allied seats are skipped)
assert 'isAlliedSeat' in room_cpp[room_cpp.index('void RoomHatchery::collectEnemies'):][:600]

# The waiting counters of the room are saved (old saves without the line still load), one hen per coop comes out
room_h = (root / 'source/rooms/RoomHatchery.h').read_text()
assert 'exportToStream' in room_h and 'importFromStream' in room_h
exp = room_cpp[room_cpp.index('void RoomHatchery::exportToStream'):][:300]
assert 'HatcheryWaits' in exp and 'mCoopHenWait' in exp and 'mCoopRoosterWait' in exp
imp = room_cpp[room_cpp.index('bool RoomHatchery::importFromStream'):][:900]
assert 'seekg(pos)' in imp and 'HatcheryWaits' in imp
assert 'coopHenCount' in room_cpp and 'HatcheryCoopBatch' in cfg

# The new rooster comes after the same wait as a hen (HatcheryChickenSpawnRate); the own rooster wait is gone,
# the saved counter stays so that old saves still load
assert 'HatcheryRoosterSpawnRate' not in config and 'HatcheryRoosterSpawnRate' not in room_cpp
assert 'mRoosterWait' not in room_cpp and 'mRoosterWait' not in cycle_h
assert 'mCoopRoosterWait >= settings.mCoopWait' in room_cpp
assert 'needCoopRooster(counts, mNumActiveSpots) && !mFightActive' in room_cpp
spawn_rooster = room_cpp[room_cpp.index('needCoopRooster(counts, mNumActiveSpots)'):][:400]
assert 'capacity' not in spawn_rooster

# Only one rooster per hatchery: two fight, the server draws the winner, the clients get a small event
assert 'needFight' in cycle_h and 'fightWinner' in cycle_h and 'fightContinues' in cycle_h
fight = room_cpp[room_cpp.index('void RoomHatchery::updateFight'):room_cpp.index('RoosterSettings RoomHatchery::getRoosterSettings')]
assert 'HatcheryCycle::fightWinner(Random::Uint(' in fight, 'winner is drawn by the server RNG'
assert fight.count('fightWinner(') == 1, 'drawn once per fight, never per client'
assert 'notifyFight(' in fight and 'loseFight()' in fight and 'ChickenPose::fight' in fight and 'ChickenPose::crow' in fight
assert 'climbDown' in fight and 'fightContinues' in fight
assert 'updateFight(roosters, settings, counts)' in room_cpp
assert 'if(!oneRooster->isFighting())' in room_cpp
for key in ('HatcheryFightTurns', 'HatcheryFightApproachTurns', 'HatcheryFightReach', 'HatcheryFightFeatherSeconds'):
    assert key in config, key
for key in ('HatcheryFightTurns', 'HatcheryFightApproachTurns', 'HatcheryFightReach'):
    assert key in room_cpp, key
render = (root / 'source/render/RenderManagerChickens.cpp').read_text()
assert 'HatcheryFightFeatherSeconds' in render and 'rrChickenFight' in render
assert 'bool ChickenEntity::loseFight' in chicken and 'ChickenState::dying' in body(chicken, 'bool ChickenEntity::loseFight')
pick = body(chicken, 'void ChickenEntity::pickup')
assert 'mFighting = false' in pick, 'a picked up rooster leaves the fight'
# the event is inserted before timeLimit (which stays the last value) and after chickenKindChanged
enum_body = notif[notif.index('enum class ServerNotificationType'):notif.index('};')]
assert enum_body.index('chickenKindChanged') < enum_body.index('chickenFight') < enum_body.index('timeLimit')
assert enum_body.rstrip().endswith('timeLimit')
assert 'ServerNotificationType::chickenFight' in chicken and 'ServerNotificationType::chickenFight' in client
assert 'case ServerNotificationType::chickenFight' in (root / 'source/network/ServerNotification.cpp').read_text()
print('hatchery rooster fight checks passed')
