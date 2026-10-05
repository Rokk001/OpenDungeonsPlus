"""Chicken gift for a creature that is not hungry and the slower walk of a tired creature.

Pure source wiring checks (no compiler, no game): server authority, configuration, saving with
old saves still loading, no new network message."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]


def read(path):
    return (root / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


rooms_cfg = read('config/rooms.cfg')
global_cfg = read('config/global.cfg')
chicken = read('source/entities/ChickenEntity.cpp')
chicken_h = read('source/entities/ChickenEntity.h')
action = read('source/creatureaction/CreatureActionEatChicken.cpp')
action_h = read('source/creatureaction/CreatureActionEatChicken.h')
creature = read('source/entities/Creature.cpp')
creature_h = read('source/entities/Creature.h')
config_h = read('source/utils/ConfigManager.h')
config_cpp = read('source/utils/ConfigManager.cpp')
movable = read('source/entities/MovableGameEntity.cpp')
render = read('source/render/RenderManager.cpp')

# Every value of the gift is in the configuration (documented, set, read with a default)
gift_keys = ['HatcheryGiftOfferTurns', 'HatcheryGiftOfferRadius', 'HatcheryGiftSniffTurns',
             'HatcheryGiftHungerPerChicken', 'HatcheryGiftHpRecoveredPerChicken',
             'HatcheryGiftCooldownMin', 'HatcheryGiftCooldownMax']
for key in gift_keys:
    assert re.search(r'^# ' + key + r'\s', rooms_cfg, re.M), key + ' not documented'
    assert re.search(r'^    ' + key + r'\t\d+', rooms_cfg, re.M), key + ' not set'
    assert re.search(r'getRoomConfigDoubleOrDefault\(\s*"' + key + '"', chicken + action), key + ' not read'

# The offer: only a hen the keeper dropped outside a hatchery, server side, never in the editor
drop = function_body(chicken, 'void ChickenEntity::drop(')
assert 'getIsOnServerMap()' in drop and 'ChickenKind::hen' in drop and 'isInEditorMode()' in drop
assert 'checkCoveringRoomType(RoomType::hatchery)' in drop and 'mGiftTurns =' in drop
assert 'void drop(const Ogre::Vector3& v) override;' in chicken_h
assert 'mGiftTurns = 0;' in function_body(chicken, 'void ChickenEntity::pickup()')
upkeep = function_body(chicken, 'void ChickenEntity::doUpkeep()')
assert 'if(mGiftTurns > 0)\n        offerGift(*tile);' in upkeep
offer = function_body(chicken, 'void ChickenEntity::offerGift(')
assert 'getCreaturesBySeat(tile.getSeat())' in offer      # only creatures of the keeper whose tile it fell on
assert 'canAcceptGift' in offer and 'CreatureActionEatChicken>(*closest, *this, true)' in offer
assert 'mLockedEat' in offer                               # a chicken somebody is after is not offered

# The creature: idle, not hungry, no worker or champion; the hatchery meal rules stay untouched
accept = function_body(action, 'bool CreatureActionEatChicken::canAcceptGift(')
for token in ('isWorker()', 'isChampion()', 'getActions().empty()', 'isHungry()', 'isKo()', 'isInPrison()', 'isPossessed()'):
    assert token in accept, token
assert 'handleGiftChicken' in action_h and 'bool gift = false' in action_h
assert 'if(mGift)' in action and 'handleGiftChicken, std::ref(mCreature), mChicken' in action
# handleEatChicken stays exactly the meal of the hatchery (a navigation check compiles that very text);
# the new functions come after getListenerName so they are not part of it
listener = 'std::string CreatureActionEatChicken::getListenerName()'
eat = action[action.index('bool CreatureActionEatChicken::handleEatChicken('):action.index('\n' + listener)]
assert 'Gift' not in eat and 'mGift' not in eat
assert action.index('bool CreatureActionEatChicken::canAcceptGift(') > action.index(listener)
assert action.index('bool CreatureActionEatChicken::handleGiftChicken(') > action.index(listener)
gift_meal = function_body(action, 'bool CreatureActionEatChicken::handleGiftChicken(')
assert 'edibleBefore' in gift_meal and 'setHunger(' in gift_meal and 'setJobCooldown(' in gift_meal
assert 'HatcheryHungerPerChicken' not in gift_meal         # not the hatchery value
ctor = action[action.index('CreatureActionEatChicken::CreatureActionEatChicken('):action.index('CreatureActionEatChicken::~')]
assert 'mGift' in ctor and 'HatcheryGiftSniffTurns' in ctor

# Saving: the gift state is appended (after the age) and read as optional, old saves end earlier
export = function_body(chicken, 'void ChickenEntity::exportToStream(')
assert export.index('<< mAge <<') < export.index('mGiftTurns')
importBody = function_body(chicken, 'bool ChickenEntity::importFromStream(')
assert importBody.index('mAge = age;') < importBody.index('is >> giftTurns') < importBody.index('is.clear();')
assert 'Age\\tGiftTurns' in chicken
# The gift is server only: no new packet field, no new message
packet = chicken[chicken.index('void ChickenEntity::exportToPacket('):chicken.index('void ChickenEntity::exportToStream(')]
assert 'mGiftTurns' not in packet
assert 'ServerNotificationType' not in offer + gift_meal + drop

# Slower walk of a tired creature: both sides, same value, from the configuration
for key in ('TiredWakefulness', 'TiredWalkSpeedFactor'):
    assert re.search(r'^    ' + key + r'\t[\d.]+', global_cfg, re.M), key
    assert ('"' + key + '"') in config_cpp
assert 'double getTiredWalkSpeedFactor() const' in config_h
assert 'std::max(0.2, std::min(1.0, mTiredWalkSpeedFactor))' in config_h
assert 'mTiredWakefulness(20.0)' in config_cpp and 'mTiredWalkSpeedFactor(0.8)' in config_cpp
tired = function_body(creature, 'bool Creature::isTired() const')
assert 'mWakefulness <= ConfigManager::getSingleton().getTiredWakefulness()' in tired and '20.0' not in tired
speed = function_body(creature, 'double Creature::getMoveSpeed(Tile* tile) const')
assert 'if(isTired())' in speed and 'getTiredWalkSpeedFactor()' in speed
assert speed.count('* tiredFactor') == 4                     # server and client: building, default, bridge, default
pose = function_body(creature, 'double Creature::getClientPoseSpeedFactor() const')
assert 'CreatureMoodValues::Tired' in pose and 'getTiredWalkSpeedFactor()' in pose
assert 'virtual double getClientPoseSpeedFactor() const override;' in creature_h
# The pose factor stays the only client side scaling of the walk clip (not doubled in the renderer)
assert movable.count('getClientPoseSpeedFactor()') == 1
assert 'getTiredWalkSpeedFactor' not in render

# Batch 13a: a chicken outside a hatchery walks back to one (dies only without a reachable one)
for key in ('HatcheryReturnPathTiles', 'HatcheryReturnSearchTiles', 'HatcheryReturnRetryTurns', 'HatcheryReturnMaxTurns'):
    assert re.search(r'^# ' + key + r'\s', rooms_cfg, re.M), key + ' not documented'
    assert re.search(r'^    ' + key + r'\t\d+', rooms_cfg, re.M), key + ' not set'
    assert re.search(r'getRoomConfigDoubleOrDefault\(\s*"' + key + '"', chicken), key + ' not read'
assert 'const bool henMayReturn = (mKind == ChickenKind::hen) && (mGiftTurns == 0) && !mLockedEat;' in upkeep
assert 'henMayReturn) && (currentHatchery == nullptr) && !mIsSlapped && runBackToHatchery(tile)' in upkeep
# the walk back comes before the death rule, so only a chicken without a way dies (30 turn rule unchanged)
assert upkeep.index('runBackToHatchery(tile)') < upkeep.index('NB_TURNS_OUTSIDE_HATCHERY_BEFORE_DIE))')
assert 'const int32_t NB_TURNS_OUTSIDE_HATCHERY_BEFORE_DIE = 30;' in chicken
# the gift window and a chicken somebody is after are not interrupted; the offer goes first
assert upkeep.index('runBackToHatchery(tile)') < upkeep.index('offerGift(*tile)')
back = function_body(chicken, 'bool ChickenEntity::runBackToHatchery(')
assert 'setWalkPath(' in back and 'getRoomsByTypeAndSeat(RoomType::hatchery, seat)' in back
assert 'getRoomsByType(RoomType::hatchery)' in back and 'seat = tile->getSeat();' in back
assert 'failReturn();' in back and 'mReturnRetryTurns' in chicken and 'mReturnTurns' in back
assert 'getIsOnServerMap' in chicken and 'setWalkPath' not in drop
# arrival: the hatchery counts the chickens on its tiles, so there is no separate registration (no double count)
assert 'mHomeSeat = currentHatchery->getSeat();' in upkeep
hatchery = read('source/rooms/RoomHatchery.cpp')
assert 'tile->fillWithEntities(entities, SelectionEntityWanted::chicken' in hatchery
# nothing saved or sent for it
assert 'mReturnTurns' not in export + importBody + packet and 'mReturnRetryTurns' not in export + importBody + packet

# Batch 13a: own sniffing pose, set by the server action, shown once on the client
movable_h = read('source/entities/MovableGameEntity.h')
assert 'sniff_anim = "Sniff"' in movable_h
sniff_meal = function_body(action, 'bool CreatureActionEatChicken::handleGiftChicken(')
assert 'creature.getJobCooldown() > 0' in sniff_meal and 'EntityAnimation::sniff_anim' in sniff_meal
assert sniff_meal.index('EntityAnimation::sniff_anim') < sniff_meal.index('handleEatChicken(creature, chicken)')
assert 'inline int getJobCooldown() const' in creature_h
assert 'Gift' not in eat and 'sniff' not in eat       # the hatchery meal stays untouched
assert 'if((anim == EntityAnimation::sniff_anim) && (dropCreature != nullptr))' in render
reactions = read('source/render/CreatureReactions.cpp')
assert 'clip == EntityAnimation::sniff_anim' in reactions and '"ChickenSniff"' in reactions
cfg_reactions = read('config/creatureReactions.cfg')
sniff_event = cfg_reactions[cfg_reactions.index('Name        ChickenSniff'):cfg_reactions.index('Name        ChickenGift')]
assert 'Name    SniffAndShrug' in sniff_event
gift_event = cfg_reactions[cfg_reactions.index('Name        ChickenGift'):]
gift_event = gift_event[:gift_event.index('[/Event]')]
assert 'SniffAndShrug' not in gift_event               # the sniffing is shown once, not again after the meal
assert cfg_reactions.count('Name    SniffAndShrug') == 1
assert 'cosmetic' not in sniff_meal.lower()            # no new network message: the clip name is the existing animation message

print('check_gift_chicken_tired_walk: ok')
