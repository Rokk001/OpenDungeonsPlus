"""Check worker job wiring, documentation, and removal of old worker shares."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]

# Read one repository file for the wiring assertions.
def read(path):
    return (root / path).read_text(encoding='utf-8')

old_keys = ('CleaningWorkerSharePercent', 'TrapReloadWorkerSharePercent',
            'WorkerCarryFirstMaxShare', 'WorkerClaimWallFirstMinShare')
for path in ('config/global.cfg', 'config/traps.cfg', 'source/game/Player.cpp',
             'source/utils/ConfigManager.cpp', 'source/utils/ConfigManager.h',
             'docs/development/DIRT.md'):
    text = read(path)
    for key in old_keys:
        assert key not in text, (path, key)

creature = read('source/entities/Creature.cpp')
assert 'getWorkerJob()' in creature
assert 'CreatureActionReloadTrap::tryStart' in creature
assert (root / 'docs/development/WORKER-JOBS.md').is_file()
assert '* Workers: workers spread over the jobs and targets instead of crowding one task, carry knocked-out creatures and corpses first, and the library credits research points directly.' in read('RELEASE-NOTES.md')
allocator = read('source/game/WorkerAllocation.cpp')
for exclusion in ('!creature->isAlive()', 'creature->isInHand()', 'creature->isKo()',
                  'creature->isPossessed()', 'CreatureActionType::fight', 'CreatureActionType::flee',
                  'CreatureActionType::goDefendHeart'):
    assert exclusion in allocator, exclusion
assert 'CreatureSkillTree::passiveSum' in allocator
assert 'fixedQuotas(' in allocator and 'assignFixed(' in allocator and 'freeTargets(' in allocator
collector = read('source/game/WorkerTargets.cpp')
for token in ('territoryAllowed(', 'getTilesWithinSightRadius()', 'pathExists(', 'wallDigPath(',
              'WorkerTargetKind::dig', 'WorkerTargetKind::ground', 'WorkerTargetKind::wall',
              'WorkerTargetKind::carry', 'WorkerTargetKind::pile', 'WorkerTargetKind::room',
              'WorkerTargetKind::corridor', 'WorkerTargetKind::reload', 'getWorkerCleanTilesPerCleaner()',
              'getReloadPrice()', 'hasCarryEntitySpot(', 'getDeliveryTile(', 'reservedByKeeper(',
              'collectActiveCarries(', 'setWorkerJobTargets(', 'setWorkerTargetLists('):
    assert token in collector, token
# Territory uses its owner even during partial claims, matching searches beyond sight.
territory = collector.split('bool territoryAllowed(', 1)[1].split('\n}', 1)[0]
assert 'tile.getSeat()' in territory and 'owner == worker.getSeat()' in territory
assert 'owner == nullptr' in territory and 'owner->isRogueSeat()' in territory
assert 'getTilesWithinSightRadius()' in territory and 'isClaimed()' not in territory

# A reserved destination may have no free capacity; an active transport is kept without a second availability test.
active = collector.split('void collectActiveCarries(', 1)[1].split('\n}', 1)[0]
assert 'carry->isForced()' in active and '(!normalSearch && digSearch)' in active
assert 'hasCarryDestination(' not in active and 'carries.push_back(' in active
prison = read('source/rooms/RoomPrison.cpp')
reservation = prison.split('Tile* RoomPrison::askSpotForCarriedEntity(', 1)[1].split('\n}', 1)[0]
assert 'mPendingPrisoners.push_back(creature)' in reservation
assert 'collectActiveCarries(targets, allWorkers)' in collector
turn = read('source/gamemap/GameMap.cpp').split('unsigned long int GameMap::doMiscUpkeep(', 1)[1]
assert turn.index('refreshWorkerTargets(*seat)') < turn.index('WorkerAllocation::refreshFixed(*seat)')
assert turn.index('WorkerAllocation::refreshFixed(*seat)') < turn.index('ge->doUpkeep()')
for job in ('dig', 'claimGround', 'claimWall', 'carry', 'clean', 'reload'):
    assert 'case WorkerJob::' + job + ':' in creature, job
idle = creature.split('bool Creature::handleIdleAction()', 1)[1].split('// A standing order', 1)[0]
assert 'job != WorkerJob::dig && getGoldCarried() > 0' in idle
assert idle.index('resetGoldCarried();') < idle.index('const uint32_t index = static_cast<uint32_t>(job);')
assert 'gold->setPosition(' in idle
drop = creature.split('void Creature::drop(const Ogre::Vector3& v)', 1)[1].split('// Fighters', 1)[0]
assert 'CreatureActionDigTile>(*this, *tileMarkedDig, *tileMarkedDigPos, true)' in drop
assert 'WorkerAllocation::chooseForIdle(' in creature
print('worker job wiring checks passed')
