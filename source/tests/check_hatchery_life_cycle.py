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

# Eggs are laid in a free place of a coop nest (closest coop first), the place rules are the pure pickNestPlace
cycle_cpp = (root / 'source/rooms/HatcheryCycle.cpp').read_text()
coop_h = (root / 'source/rooms/HatcheryCoopHouse.h').read_text()
assert 'pickNestPlace' in cycle_h and 'int32_t HatcheryCycle::pickNestPlace' in cycle_cpp
nest = body(room_cpp, 'bool RoomHatchery::findNestSpot')
assert 'HatcheryCoopHouse::nestEggSpotWorld' in nest and 'HatcheryCycle::pickNestPlace' in nest
assert 'getCoveringRoom() != this' in nest, 'a nest place outside of the hatchery is not used'
assert 'mCentralActiveSpotTiles' in nest and 'squaredDistance' in nest, 'closest coop first'
assert 'HatcheryNestEggs' in nest and 'HatcheryNestSameRadius' in nest
assert 'HatcheryNestEggs' in cfg and 'HatcheryNestSameRadius' in cfg
assert 'nestEggSpot' in coop_h and 'nestCount' in coop_h and 'eggsPerNest' in coop_h
lay = doUpkeep[doUpkeep.index('hen->countDownLay()'):doUpkeep.index('Eggs hatch while there is a rooster')]
assert 'findNestSpot(' in lay and 'spawnAnimal(ChickenKind::egg, eggSpot, settings)' in lay
assert 'eggPositions.push_back' in lay, 'an egg laid this turn takes its place at once'
assert 'HatcheryCycle::canLay(counts, capacity)' in lay, 'capacity still limits the eggs'
assert 'ChickenPose::lay' in lay, 'the hen sits down where she is (robust variant)'
assert 'eggs.erase(eggIt)' in doUpkeep and doUpkeep.index('eggs.erase(eggIt)') < doUpkeep.index('eggPositions.push_back'),     'trampled eggs free their place'
# The chick from a nest stands next to the coop, the nest lies in the footprint of the coop
assert 'leaveNest(egg)' in doUpkeep and 'chick->teleport(' in body(room_cpp, 'void RoomHatchery::leaveNest')
assert 'standingPosition' in body(room_cpp, 'void RoomHatchery::leaveNest')
teleport_pos = chicken_h.index('void teleport(')
assert 'private:' not in chicken_h[chicken_h.index('void hopDown('):teleport_pos], 'teleport is public'
# Egg save/load: the position (with the height) is saved by the entity, nothing new is saved
assert 'mPosition.z' in body(chicken, 'void ChickenEntity::exportToStream') or 'mPosition.z' in chicken
# Client: the egg in a nest has no straw of its own, the coop mesh has the nests
render = (root / 'source/render/RenderManagerChickens.cpp').read_text()
assert 'hideEggStraw' in render and 'mNestEgg' in render and 'ChickenStraw' in render

# Trampling: shell pieces, yolk and feathers, shown by the clients, no new network value
assert 'fireEggTrample(*egg)' in doUpkeep
fx = body(room_cpp, 'void RoomHatchery::fireEggTrample')
assert 'HatcheryFx/EggTrample' in fx and 'ServerNotificationType::playSpatialSound' in fx
assert 'HatcheryFx/EggTrample' in client and 'rrEggTrampled' in client
assert 'void RenderManager::rrEggTrampled' in render and '"ChickenEggTrample"' in render
particles = (root / 'particles/ChickenEggShell.particle').read_text()
trample = particles[particles.index('particle_system ChickenEggTrample'):]
assert trample.count('emitter Point') == 2, 'shell emitter and yolk emitter'
assert 'enum class ServerNotificationType' in notif and notif[notif.index('enum class ServerNotificationType'):notif.index('};')].rstrip().endswith('timeLimit')
print('hatchery nest egg and trample checks passed')
