from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]
# Read a tracked source file relative to the repository.
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
# Worker exclusion applies to corpses only: living knocked-out workers use the ordinary own/enemy paths.
creature_classification = classification[classification.index('if(entity.getObjectType() == GameEntityType::creature)'):classification.index('switch(entity.getObjectType())')]
assert creature_classification.index('if(!patient.isAlive())') < creature_classification.index('!patient.getDefinition()->isWorker()')
assert creature_classification.index('!patient.getDefinition()->isWorker()') < creature_classification.index('patient.getKoTurnCounter() >= 0')
assert creature_classification.count('isWorker()') == 1
assert creature_classification.index('patient.getKoTurnCounter() >= 0') < creature_classification.index('WorkerCarryEntry::ownKnockedOut')
assert creature_classification.index('WorkerCarryEntry::ownKnockedOut') < creature_classification.index('WorkerCarryEntry::enemyKnockedOut')
client_enum = read('source/network/ClientNotification.h').split('enum class ClientNotificationType', 1)[1].split('};', 1)[0]
server_enum = read('source/network/ServerNotification.h').split('enum class ServerNotificationType', 1)[1].split('};', 1)[0]
assert client_enum.rindex('askWorkerSettings') > client_enum.rindex('askSpaPayer')
assert server_enum.rindex('workerSettings') > server_enum.rindex('creatureJump')
assert '${SRC}/game/WorkerJobs.cpp' in read('CMakeLists.txt')
# Extract a C++ body so the checks below cannot pass on an unrelated occurrence.
def body(source, signature):
    start = source.index(signature)
    opening = source.index('{', start)
    depth = 1
    end = opening + 1
    while depth:
        if source[end] == '{':
            depth += 1
        elif source[end] == '}':
            depth -= 1
        end += 1
    return source[opening + 1:end - 1]

# Every record has exactly six fixed counts, six job entries and seven carry entries.
assert re.search(r'std::array<uint32_t,\s*6>\s+fixed', shared)
assert re.search(r'std::array<uint32_t,\s*6>\s+priority', shared)
assert re.search(r'std::array<uint32_t,\s*7>\s+carryOrder', shared)
validation = body(shared, 'inline bool validWorkerJobSettings(')
assert re.search(r'for\s*\(uint32_t job : settings\.priority\)', validation)
assert re.search(r'if\s*\(job >= jobs\.size\(\) \|\| jobs\[job\]\) return false;', validation)
assert re.search(r'for\s*\(uint32_t entry : settings\.carryOrder\)', validation)
assert re.search(r'if\s*\(entry >= entries\.size\(\) \|\| entries\[entry\]\) return false;', validation)
assert 'settings.freeMode > 1 || settings.goldFirst > 1' in validation
# Invalid IDs and duplicates fail in the validator; a missing packet value or extra value fails before mutation.
seat_data = read('source/game/SeatData.cpp')
packet_read = body(seat_data, 'bool SeatData::readWorkerJobSettings(')
packet_write = body(seat_data, 'void SeatData::writeWorkerJobSettings(')
fields = ('fixed', 'freeMode', 'priority', 'carryOrder', 'goldFirst')
for packet_body in (packet_read, packet_write):
    positions = [packet_body.index('settings.' + field) for field in fields]
    assert positions == sorted(positions), positions
for field in ('fixed', 'priority', 'carryOrder'):
    assert re.search(r'for\s*\(uint32_t& value : settings\.' + field + r'\) if\s*\(!\(packet >> value\)\) return false;', packet_read)
assert 'if(!(packet >> settings.freeMode)) return false;' in packet_read
assert 'static_cast<bool>(packet >> settings.goldFirst)' in packet_read
assert handler.index('packetReceived.endOfPacket()') < handler.index('seat->setWorkerJobSettings(requested)')
assert handler.index('!player->getHasLost()') < handler.index('seat->setWorkerJobSettings(requested)')
assert handler.index('!player->getIsHuman()') < handler.index('seat->setWorkerJobSettings(requested)')
assert 'uint64_t total = 0;' in handler and 'total += requested.fixed[i];' in handler
assert 'if(!raised || total <= living) seat->setWorkerJobSettings(requested);' in handler
assert 'SeatData::writeWorkerJobSettings(response->mPacket, seat->getWorkerJobSettings());' in handler
print('settings refusal and stored-response source checks: OK')

# Confirm save and load cover the same fields in the same order and worker state stays with its creature.
seat_load = body(seat, 'bool Seat::importSeatFromStream(')
seat_save = body(seat, 'bool Seat::exportSeatToStream(')
load_block = seat_load[seat_load.index('if(str == "[WorkerJobs]")'):seat_load.index('if(str == "[ResearchRemainder]")')]
save_block = seat_save[seat_save.index('os << "[WorkerJobs]";'):seat_save.index('os << "[Infirmary]')]
load_positions = [load_block.index('settings.' + field) for field in fields]
save_positions = [save_block.index('mWorkerJobSettings.' + field) for field in fields]
assert load_positions == sorted(load_positions) and save_positions == sorted(save_positions)
assert 'validWorkerJobSettings(settings)' in load_block and 'str != "[/WorkerJobs]"' in load_block
assert load_block.index('validWorkerJobSettings(settings)') < load_block.index('mWorkerJobSettings = settings')
assert 'str == "[WorkerJobs]"' in seat_load and 'continue;' in load_block
assert 'mWorkerJobSettings(ConfigManager::getSingleton().getDefaultWorkerJobSettings())' in seat_data
creature_header = read('source/entities/Creature.h')
assert 'WorkerJob mWorkerJob = WorkerJob::none;' in creature_header and 'bool mWorkerJobFixed = false;' in creature_header
creature_load = body(creature, 'bool Creature::importFromStream(')
creature_save = body(creature, 'void Creature::exportToStream(')
assert 'if(mDefinition->isWorker())' in creature_save
assert 'static_cast<uint32_t>(mWorkerJob)' in creature_save and '(mWorkerJobFixed ? 1 : 0)' in creature_save
assert 'if(appearanceToken == "[WorkerJob]")' in creature_load
assert 'mWorkerJob = static_cast<WorkerJob>(job);' in creature_load and 'mWorkerJobFixed = fixed != 0;' in creature_load
assert 'fixed && job == static_cast<uint32_t>(WorkerJob::none)' in creature_load
# A missing creature has no save record to restore; no separate assignment name list can resurrect it.
map_handler = read('source/gamemap/MapHandler.cpp')
assert 'for (Creature* creature : gameMap.getCreatures())' in map_handler
assert 'GameEntity::exportToStream(creature, levelFile);' in map_handler
assert '[WorkerJobs]' not in creature_save and 'mWorkerJobFixed' not in save_block
# The client can request or propose settings and receives the server's authoritative record.
client = read('source/network/ODClient.cpp')
request = body(client, 'void ODClient::requestWorkerJobSettings(')
send = body(client, 'void ODClient::sendWorkerJobSettings(')
assert 'askWorkerSettings' in request and 'static_cast<uint32_t>(0)' in request
assert 'askWorkerSettings' in send and 'static_cast<uint32_t>(1)' in send
assert 'SeatData::writeWorkerJobSettings(notification->mPacket, settings);' in send
assert 'SeatData::readWorkerJobSettings(packetReceived, settings)' in client
assert 'getPlayer()->getSeat()->setWorkerJobSettings(settings)' in client
# The regularly sent owner update carries settings, free-worker count and every job count.
update_write = body(seat_data, 'void SeatData::exportToPacketForUpdate(')
update_read = body(seat_data, 'bool SeatData::importFromPacketForUpdate(')
assert 'writeWorkerJobSettings(os, mWorkerJobSettings);' in update_write
assert 'os << mFreeWorkers;' in update_write and 'for(uint32_t value : mWorkerJobCounts) os << value;' in update_write
assert 'readWorkerJobSettings(is, workerSettings)' in update_read
assert 'is >> freeWorkers' in update_read and 'for(uint32_t& value : counts)' in update_read
print('old-save defaults and worker/keeper save-field source checks: OK')

print('worker settings wiring: OK')
