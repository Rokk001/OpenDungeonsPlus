from pathlib import Path

root = Path(__file__).resolve().parents[2]
def read(path):
    return (root / path).read_text(encoding='utf-8')

config = read('config/global.cfg')
for line in ('WorkerPriorityParts\t6 5 4 3 2 1', 'WorkerDefaultFixed\t0 0 0 0 0 0',
             'WorkerDefaultFreeMode\tautomatic', 'WorkerDefaultPriority\tcarry dig claimGround claimWall clean reload',
             'WorkerDefaultCarryOrder\townKnockedOut enemyKnockedOut corpse gold items giftBoxes trapsDoors',
             'WorkerDefaultGoldFirst\t0', 'WorkerCleanTilesPerCleaner\t15'):
    assert line in config, line
for key in ('WorkerPriorityParts', 'WorkerDefaultFixed', 'WorkerDefaultFreeMode', 'WorkerDefaultPriority',
            'WorkerDefaultCarryOrder', 'WorkerDefaultGoldFirst', 'WorkerCleanTilesPerCleaner'):
    assert key in read('source/utils/ConfigManager.cpp'), key
seat = read('source/game/Seat.cpp')
assert '[WorkerJobs]' in seat and '[/WorkerJobs]' in seat
creature = read('source/entities/Creature.cpp')
assert '[WorkerJob]' in creature and '[/WorkerJob]' in creature
assert 'askWorkerSettings' in read('source/network/ClientNotification.h')
assert 'workerSettings' in read('source/network/ServerNotification.h')
assert 'askWorkerSettings' in read('source/network/ODServer.cpp')
assert 'workerSettings' in read('source/network/ODClient.cpp')
# Check that every wire value is validated before the current record is replaced.
shared = read('source/game/WorkerJobs.h')
assert 'settings.freeMode > 1 || settings.goldFirst > 1' in shared
assert 'job >= jobs.size() || jobs[job]' in shared
assert 'entry >= entries.size() || entries[entry]' in shared
server = read('source/network/ODServer.cpp')
handler = server[server.index('case ClientNotificationType::askWorkerSettings:'):server.index('case ClientNotificationType::askInfirmaryWindow:')]
for condition in ('!player->getIsHuman()', '!player->getHasLost()', 'validWorkerJobSettings(requested)',
                  'packetReceived.endOfPacket()', 'requested.fixed[i] > seat->getWorkerJobSettings().fixed[i]',
                  '!raised || total <= living', 'seat->setWorkerJobSettings(requested)',
                  'seat->getWorkerJobSettings()'):
    assert condition in handler, condition
assert handler.index('validWorkerJobSettings(requested)') < handler.index('seat->setWorkerJobSettings(requested)')
assert handler.index('seat->setWorkerJobSettings(requested)') < handler.index('ServerNotificationType::workerSettings')
# Optional save blocks allow old saves to retain constructor defaults, and save both fields per worker.
assert 'mWorkerJobSettings(ConfigManager::getSingleton().getDefaultWorkerJobSettings())' in read('source/game/SeatData.cpp')
assert 'str == "[WorkerJobs]"' in seat and 'mWorkerJobSettings = settings' in seat
assert 'mWorkerJobFixed = fixed != 0' in creature and 'static_cast<uint32_t>(mWorkerJob)' in creature
classification = read('source/game/WorkerJobs.cpp')
for entry in ('ownKnockedOut', 'enemyKnockedOut', 'corpse', 'gold', 'items', 'giftBoxes', 'trapsDoors', 'none'):
    assert 'WorkerCarryEntry::' + entry in classification
for guard in ('isWorker()', 'isUndead()', 'getKoTurnCounter() >= 0', 'isAlliedSeat', 'EntityCarryType::corpse', 'dynamic_cast<MissileStone*>'):
    assert guard in classification
client_enum = read('source/network/ClientNotification.h').split('enum class ClientNotificationType', 1)[1].split('};', 1)[0]
server_enum = read('source/network/ServerNotification.h').split('enum class ServerNotificationType', 1)[1].split('};', 1)[0]
assert client_enum.rindex('askWorkerSettings') > client_enum.rindex('askSpaPayer')
assert server_enum.rindex('workerSettings') > server_enum.rindex('creatureJump')
assert '${SRC}/game/WorkerJobs.cpp' in read('CMakeLists.txt')
print('worker settings wiring: OK')
