from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Read a project source file for the non-compiling checks.
def read(path):
    return (ROOT / path).read_text(encoding='utf-8')

searches = {
    'CreatureActionSearchTileToDig.cpp': 'WorkerJob::dig',
    'CreatureActionSearchGroundTileToClaim.cpp': 'WorkerJob::claimGround',
    'CreatureActionSearchWallTileToClaim.cpp': 'WorkerJob::claimWall',
    'CreatureActionSearchEntityToCarry.cpp': 'WorkerJob::carry',
    'CreatureActionSearchDirtToClean.cpp': 'WorkerJob::clean',
}
for name, job in searches.items():
    source = read('source/creatureaction/' + name)
    assert ('getWorkerTargetLists()' in source or 'workerSearchTiles(creature, ' + job in source), name + ' uses keeper targets'
    assert 'getWorkerJob() != ' + job in source, name + ' stops on job change'
assert 'getWorkerTargetLists()' in read('source/creatureaction/WorkerSearchTargets.h')
dig = read('source/creatureaction/CreatureActionSearchTileToDig.cpp')
assert 'goldFirst' in dig and 'TileType::gold' in dig and 'TileType::gem' in dig
assert 'hasWorkerDigging()' in dig and 'bestStanding' in dig and 'squaredDistanceTile' in dig
wall = read('source/creatureaction/CreatureActionSearchWallTileToClaim.cpp')
assert 'Random::' in wall
carry = read('source/creatureaction/CreatureActionSearchEntityToCarry.cpp')
assert 'carryOrder' in carry and 'classifyWorkerCarry' in carry
assert 'getEntityFromTypeAndName' in carry and 'getCarryLock(creature)' in carry
assert 'hasCarryEntitySpot(entity)' in carry and 'getDeliveryTile(creature)' in carry
assert 'if(forced)' in carry and 'creature.popAction()' in carry
assert carry.index('if(targetStarted)') < carry.index('std::vector<GameEntity*> candidates')
assert carry.index('targetStarted = true;') < carry.index('CreatureActionGrabEntity>(creature, *entity, forced)')
assert 'mTargetStarted(false)' in carry and 'std::ref(mTargetStarted)' in carry
carry_header = read('source/creatureaction/CreatureActionCarryEntity.h')
grab_header = read('source/creatureaction/CreatureActionGrabEntity.h')
assert 'bool isDigGold() const { return mDigGold; }' in carry_header
assert 'bool isDigGold() const { return mDigGold; }' in grab_header
assert 'bool forced = false, bool digGold = false' in carry_header and 'bool forced = false, bool digGold = false' in grab_header
assert 'bool isForced() const' in grab_header
assert 'mForced, mDigGold' in read('source/creatureaction/CreatureActionGrabEntity.cpp')
assert 'mDigGold(digGold)' in read('source/creatureaction/CreatureActionGrabEntity.cpp')
assert read('source/creatureaction/CreatureActionCarryEntity.cpp').count('mDigGold(digGold)') == 2
for source in (dig, read('source/creatureaction/CreatureActionDigTile.cpp')):
    assert 'CreatureActionGrabEntity>(creature, *obj, forced, true)' in source
clean = read('source/creatureaction/CreatureActionSearchDirtToClean.cpp')
assert 'activeCleaners' in clean and 'getWorkerCleanTilesPerCleaner()' in clean
clean_action = read('source/creatureaction/CreatureActionCleanTile.cpp')
assert 'pileGone = pileTarget' in clean_action and '|| pileGone ||' in clean_action
assert 'WorkerTargetKind::pile' in clean and 'WorkerTargetKind::room' in clean and 'WorkerTargetKind::corridor' in clean
reload = read('source/creatureaction/CreatureActionReloadTrap.cpp')
assert 'TrapReloadSearchRadius' not in reload
assert 'TrapReloadSearchRadius' not in read('config/traps.cfg')
creature = read('source/entities/Creature.cpp')
drop = creature.split('void Creature::drop(const Ogre::Vector3& v)', 1)[1].split('// Fighters', 1)[0]
assert 'CreatureActionSearchEntityToCarry>(*this, true)' in drop
save = creature.split('void Creature::exportToStream(', 1)[1].split('bool Creature::importFromStream(', 1)[0]
assert '[WorkerJob]' in save and 'CreatureActionSearchEntityToCarry' not in save
assert 'mArenaKnockOut || mKoTurnCounter < 0' in save
assert 'mIsCarried && !mCorpseCarrierName.empty()' in save
streams = read('source/rooms/RoomInfirmaryStreams.cpp')
assert 'isForcedTransport(patient.reservedBy)' in streams and 'savedPatients' in streams
assert 'spot.second->isCorpseCarried()' in read('source/rooms/RoomCrypt.cpp')
assert 'getCorpseCarrierName().empty()' in read('source/rooms/RoomCrypt.cpp')
grab = read('source/creatureaction/CreatureActionGrabEntity.cpp')
assert '*entity, forced)' in carry and '*buildingWants, forced, digGold)' in grab
assert 'getWorkerJobSettings().goldFirst' in drop and 'hasWorkerDigging()' in drop
assert 'dropWalls[Random::Uint' in drop
dig_action = read('source/creatureaction/CreatureActionDigTile.cpp')
assert 'if(!forced && creature.getWorkerJob() != WorkerJob::dig)' in dig_action
assert 'std::ref(mTilePos), mForced' in dig_action
assert 'Tile& tilePos, bool forced = false' in read('source/creatureaction/CreatureActionDigTile.h')
for repeat in ('CreatureActionSearchTileToDig>(*this, true)', 'CreatureActionSearchGroundTileToClaim>(*this, true)', 'CreatureActionSearchWallTileToClaim>(*this, true)'):
    assert repeat not in drop
assert 'isWoundedForBedCarry()' not in read('source/rooms/RoomDormitory.cpp')
transport = read('source/creatureaction/CreatureActionCarryEntity.cpp')
assert 'mCorpseDrag' in transport and 'mExternalDrag' in transport
assert 'notifyCorpseDragStart' in transport and 'notifyCorpseDragEnd' in transport
assert 'mDelivered = true' in transport and 'notifyCarryingStateChanged(nullptr' in transport
assert 'hasReservedDelivery(*dragged, mTileDest)' in transport
assert 'mBuildingDest->getSeat() != mCreature.getSeat()' in transport
assert 'if(!reserved)' in transport
assert 'startLaying(*dragged)' in transport and 'dragged->getPositionTile() != mTileDest' in transport
assert 'dragged->setPosition(mCreature.getPosition())' not in transport
assert 'carrier->getPositionTile() != getGateTile()' in read('source/rooms/RoomPrison.cpp')
crypt = read('source/rooms/RoomCrypt.cpp')
prison = read('source/rooms/RoomPrison.cpp')
assert 'if(carrier == nullptr)' in crypt
assert 'spot.second == &body' in crypt and 'getDeliveryTile(spot.first) == delivery' in crypt
assert 'getGateTile() == delivery' in prison and 'mPendingPrisoners.end()' in prison
assert 'if(getIsOnMap() && !mIsBeingDragged)' in creature
assert 'mCorpseCarrierName = forced ? std::string() : carrier.getName()' in creature and 'mCorpseCarrierName.clear()' in creature
print('worker searches and carry rules: OK')
