"""Heart health steps for every visible heart and the grain reaction of the hatchery.

Pure source wiring checks (no compiler, no game): server authority, configuration with defaults, the two new
cosmetic event kinds appended to the network format, saves of the hatchery that still load, and the client side.
The probe of the pure step rules in HeartHealthRing.h is compiled and run only with --probe (needs the MSVC
compiler on the path)."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


event_h = read('source/network/CosmeticEvent.h')
event_cpp = read('source/network/CosmeticEvent.cpp')
ring_h = read('source/game/HeartHealthRing.h')
server = read('source/network/ODServer.cpp')
socket_h = read('source/network/ODSocketClient.h')
client = read('source/network/ODClient.cpp')
client_h = read('source/network/ODClient.h')
config_h = read('source/utils/ConfigManager.h')
config_cpp = read('source/utils/ConfigManager.cpp')
global_cfg = read('config/global.cfg')
rooms_cfg = read('config/rooms.cfg')
hatchery = read('source/rooms/RoomHatchery.cpp')
hatchery_h = read('source/rooms/RoomHatchery.h')
ambience = read('source/render/RoomAmbience.cpp')
ambience_h = read('source/render/RoomAmbience.h')
extras = read('source/render/RoomAmbienceExtras.cpp')
ambience_cfg = read('config/roomAmbienceProduction.cfg')
deferred_cfg = read('config/roomAmbienceDeferred.cfg')

# Network format: the new kinds are appended after the last one (numbers never change), the range test follows
kinds = re.findall(r'^\s+(\w+) = (\d+),?\s*$', event_h.split('enum class CosmeticEventType')[1].split('};')[0], re.M)
numbers = [int(number) for _, number in kinds]
assert numbers == list(range(len(numbers))), 'cosmetic event kinds must stay numbered without gaps'
names = [name for name, _ in kinds]
assert names[-3:] == ['bedStatus', 'heartHealthStage', 'hatcheryGrain'], names[-3:]
assert dict(kinds)['heartHealthStage'] == '12' and dict(kinds)['hatcheryGrain'] == '13'
assert 'CosmeticEventType::hatcheryGrain));' in event_cpp
for name in ('heartHealthStage', 'hatcheryGrain'):
    assert 'return "' + name + '";' in event_cpp, name

# Heart steps: server decides, only for cosmetic-event clients, own and allied hearts always, others when seen
for key, default in (('HeartHealthStages', '5'), ('HeartHealthStageEvents', '1')):
    assert re.search(r'^# .*\n\s+' + key + r'\t' + default + r'\s*$', global_cfg, re.M), key
    assert 'nextParam == "' + key + '"' in config_cpp, key
assert 'mHeartHealthStages(5)' in config_cpp and 'mHeartHealthStageEvents(true)' in config_cpp
assert 'std::max(2, std::min(20, mHeartHealthStages))' in config_h
notify = function_body(server, 'void notifyHeartStages(')
for needle in ('supportsCosmeticEvents()', 'getHeartHealthStageEvents()', 'getHeartHealthStages()',
               'isAlliedSeat(heartSeat)', 'hasVisionOnTile(heartTile)', 'HeartHealthRing::healthStage(',
               'CosmeticEventType::heartHealthStage', 'sendCosmeticEvent(player, event)', 'sent.erase(it)'):
    assert needle in notify, needle
assert 'notifyHeartStages(gameMap, sock, player);' in server
assert 'getHeartStagesSent()' in socket_h
# The exact health is never in the event (only the step), the old owner message stays as it was
assert 'getHeartHealthFraction' in notify and 'mValue2 = stage' in notify
assert 'serverNotification->mPacket << fraction << underAttack << heartHP << temple->getHeartMaxHP();' in server
# Client: stores the step per seat, other clients (without the agreement) and older servers never get or send it
assert 'event.is(CosmeticEventType::heartHealthStage)' in client
assert 'mHeartStageFractions.clear();' in client
assert 'float getHeartStageFraction(int32_t seatId) const;' in client_h

# Every heart beats on its own: the client gives each heart its factor, effects use the nearest heart
assert 'setHeartRateFactor' not in ambience + ambience_h + extras
assert 'ambience.clearHeartRates();' in extras and 'ambience.addHeartRate(position, factor);' in extras
heart = extras[extras.index('meshName == "DungeonTempleObject"'):]
assert 'getHeartBadge()' in heart and 'getHeartStageFraction(' in heart
assert 'tile->getSeat() == localSeat' in heart and 'attacked = badge.mGlow' in heart
assert 'std::map<int32_t, double> mNextHeartBeat;' in read('source/render/RoomAmbienceExtras.h')
assert ambience.count('getHeartRateFactor(') >= 3
rate = function_body(ambience, 'double RoomAmbience::getHeartRateFactor(')
assert 'HEART_RATE_RADIUS' in rate and 'return best;' in rate

# Grain: values in the configuration, read with a default
grain_keys = {'HatcheryGrainReaction': '1', 'HatcheryGrainLevels': '3', 'HatcheryGrainEatPercent': '30',
              'HatcheryGrainRegrowPermille': '8', 'HatcheryGrainSyncTurns': '2', 'HatcheryGrainResyncTurns': '14'}
for key, value in grain_keys.items():
    assert re.search(r'^# ' + key + r'\s', rooms_cfg, re.M), key + ' not documented'
    assert re.search(r'^    ' + key + r'\t' + value + r'\s*$', rooms_cfg, re.M), key + ' not set'
    assert '"' + key + '", ' + value + '.0)' in hatchery, key + ' needs the same default in the source'

# Server authority: hens take grain when they scratch, it grows back, nothing else about the hens changes
scratch = function_body(hatchery, 'void RoomHatchery::updateFlock(')
assert 'hen->playPose(ChickenPose::scratch, 2);\n            eatGrain(hen->getPositionTile());' in scratch
eat = function_body(hatchery, 'void RoomHatchery::eatGrain(')
for needle in ('getCoveringRoom() != this', 'HatcheryGrainReaction', 'HatcheryGrainEatPercent', 'mGrain[tile] = level - 1;'):
    assert needle in eat, needle
update = function_body(hatchery, 'void RoomHatchery::updateGrain(')
for needle in ('HatcheryGrainRegrowPermille', 'mGrain.erase(it++)', 'HatcheryGrainSyncTurns',
               'HatcheryGrainResyncTurns', 'sendGrain();', 'mGrain.clear();'):
    assert needle in update, needle
assert 'updateGrain();' in function_body(hatchery, 'void RoomHatchery::doUpkeep(')
send = function_body(hatchery, 'void RoomHatchery::sendGrain(')
for needle in ('getSeatsWithVision()', 'getIsHuman()', 'sendCosmeticEvent(', 'CosmeticEventType::hatcheryGrain'):
    assert needle in send, needle

# Saving: one optional line after the waiting counters, appended only when grain is missing; old saves load
export = function_body(hatchery, 'void RoomHatchery::exportToStream(')
assert export.index('HatcheryWaits') < export.index('HatcheryGrain') and 'if(!mGrain.empty())' in export
load = function_body(hatchery, 'bool RoomHatchery::importFromStream(')
assert load.count('is.seekg(pos);') == 2 and 'tag != "HatcheryGrain"' in load
assert load.index('HatcheryWaits') < load.index('"HatcheryGrain"')

# Client: levels from the event, decals by level, a peck shows a small cloud; stale lists are dropped
assert 'event.is(CosmeticEventType::hatcheryGrain)' in client and 'notifyHatcheryGrain(' in client
level = function_body(ambience, 'int32_t RoomAmbience::getGrainLevel(')
assert 'mClock > roomIt->second.mExpire' in level and 'return levels;' in level
assert 'getGrainLevel(tile) < static_cast<int32_t>(effect.mGrainMin)' in ambience
assert 'mGrainRooms.clear();' in ambience
assert 'GrainPecked' in function_body(ambience, 'void RoomAmbience::notifyHatcheryGrain(')
for min_level in (1, 2, 3):
    assert re.search(r'^\s+GrainMin\s+' + str(min_level) + r'\s*$', ambience_cfg, re.M), min_level
assert re.search(r'^\s+Event\s+GrainPecked\s*$', deferred_cfg, re.M)
assert 'key == "GrainMin"' in read('source/render/RoomAmbienceConfig.cpp')

if '--probe' in sys.argv:
    probe = r'''
#include "game/HeartHealthRing.h"
#include <iostream>
static int gFailures = 0;
static void check(bool ok, const char* msg)
{
    if(!ok)
    {
        ++gFailures;
        std::cout << "FAIL: " << msg << '\n';
    }
}
int main()
{
    check(HeartHealthRing::healthStage(1.0f, 5) == 5, "an unhurt heart is the top step");
    check(HeartHealthRing::healthStage(0.81f, 5) == 5, "just under full is still the top step");
    check(HeartHealthRing::healthStage(0.8f, 5) == 4, "exactly four fifths is step 4");
    check(HeartHealthRing::healthStage(0.2f, 5) == 1, "exactly one fifth is step 1");
    check(HeartHealthRing::healthStage(0.001f, 5) == 1, "a heart that lives is never step 0");
    check(HeartHealthRing::healthStage(0.0f, 5) == 0, "a destroyed heart is step 0");
    check(HeartHealthRing::healthStage(0.5f, 0) == 1, "fewer than one step counts as one");
    check(HeartHealthRing::healthStage(2.0f, 10) == 10, "more than full is clamped");
    check(HeartHealthRing::stageFraction(5, 5) == 1.0f, "the top step is a calm heart");
    check(HeartHealthRing::stageFraction(0, 5) == 0.0f, "step 0 is no health");
    check(HeartHealthRing::stageFraction(2, 4) == 0.5f, "step 2 of 4 is half");
    std::cout << "FAILURES=" << gFailures << '\n';
    return gFailures ? 1 : 0;
}
'''
    with tempfile.TemporaryDirectory(prefix='odp-heart-stage-') as directory:
        work = Path(directory)
        (work / 'check.cpp').write_text(probe)
        subprocess.run(['cl', '/nologo', '/EHsc', '/MD', '/std:c++14', '/I', str(root / 'source'), 'check.cpp', '/Fecheck.exe'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([str(work / 'check.exe')], cwd=work, capture_output=True, text=True)
        sys.stdout.write(result.stdout)
        assert result.returncode == 0, 'probe failed'

print('check_heart_stage_grain: ok')
