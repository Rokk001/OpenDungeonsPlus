"""Foreign hearts beat harder for a moment when their health step falls.

Pure source wiring checks (no compiler, no game): the rule in HeartHealthRing.h, the glow time kept per seat on the
client, the frame update and the beat of a foreign heart. No new network data: the step event of the hearts is reused."""
from pathlib import Path

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


ring = read('source/game/HeartHealthRing.h')
client_h = read('source/network/ODClient.h')
client = read('source/network/ODClient.cpp')
game_mode = read('source/modes/GameMode.cpp')
extras = read('source/render/RoomAmbienceExtras.cpp')
event_h = read('source/network/CosmeticEvent.h')

# The rule: only a lower step than the one before is a hit; the first step and healing are not
assert 'inline bool isStageHit(float previousFraction, float newFraction)' in ring
assert 'return previousFraction >= 0.0f && newFraction < previousFraction;' in ring

# The client keeps the glow time per seat, starts it with the step event, clears it with the steps
assert 'std::map<int32_t, float> mHeartStageHitRemaining;' in client_h
assert 'bool isHeartStageHit(int32_t seatId) const;' in client_h
assert 'void updateHeartStageHits(float timeSinceLastFrame);' in client_h
event_block = client[client.index('event.is(CosmeticEventType::heartHealthStage)'):]
event_block = event_block[:event_block.index('break;')]
assert 'float previous = getHeartStageFraction(event.mValue);' in event_block
assert event_block.index('float previous') < event_block.index('mHeartStageFractions[event.mValue]')
assert 'HeartHealthRing::isStageHit(previous, fraction)' in event_block
assert 'mHeartStageHitRemaining[event.mValue] = HeartHealthRing::ATTACK_GLOW_SECONDS;' in event_block
assert client.count('mHeartStageHitRemaining.clear();') == 1
assert client.index('mHeartStageFractions.clear();') < client.index('mHeartStageHitRemaining.clear();')
update = function_body(client, 'void ODClient::updateHeartStageHits(')
assert 'it->second -= timeSinceLastFrame;' in update and 'mHeartStageHitRemaining.erase(it++);' in update

# Every frame of the game mode runs the update
assert 'ODClient::getSingleton().updateHeartStageHits(evt.timeSinceLastFrame);' in game_mode

# A foreign heart takes its hit from the client, the beat factor is the one of the own heart
beat = extras[extras.index('DungeonTempleObject'):]
beat = beat[:beat.index('// The rooster crows')]
assert 'attacked = ODClient::getSingleton().isHeartStageHit(tile->getSeat()->getId());' in beat
assert 'double factor = 1.0 + 1.6 * (1.0 - fraction) + (attacked ? 0.3 : 0.0);' in beat

# Nothing new on the wire: no new cosmetic event kind
assert 'heartHealthStage = 12,' in event_h

print('FOREIGN HEART HIT OK')
