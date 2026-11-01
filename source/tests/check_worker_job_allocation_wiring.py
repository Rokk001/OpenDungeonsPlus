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
turn = read('source/gamemap/GameMap.cpp').split('unsigned long int GameMap::doMiscUpkeep(', 1)[1]
assert turn.index('refreshWorkerTargets(*seat)') < turn.index('WorkerAllocation::refreshFixed(*seat)')
assert turn.index('WorkerAllocation::refreshFixed(*seat)') < turn.index('ge->doUpkeep()')
for job in ('dig', 'claimGround', 'claimWall', 'carry', 'clean', 'reload'):
    assert 'case WorkerJob::' + job + ':' in creature, job
assert 'WorkerAllocation::chooseForIdle(' in creature
print('worker job wiring checks passed')
