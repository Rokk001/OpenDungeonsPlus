"""Static wiring checks for the game mechanics that the converted campaign levels need.

One section per mechanic, in the order they were added.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


# Traps of the neutral and the hero seats fire without mana
seat_h = read('source/game/Seat.h')
assert 'isTrapManaFree' in seat_h and 'getFaction() == "Hero"' in seat_h
trap = read('source/traps/Trap.cpp')
assert 'getSeat()->isTrapManaFree() ? 0.0 : getManaToFire()' in trap
door = read('source/traps/TrapDoor.cpp')
assert 'getSeat()->isTrapManaFree() ? 0.0' in door

# Flag comparisons, timers
script_h = read('source/gamemap/LevelScript.h')
script = read('source/gamemap/LevelScript.cpp')
runner = read('source/gamemap/LevelScriptRunner.cpp')
assert 'enum class LevelScriptCompare' in script_h
assert 'startTimer' in script_h and 'advanceTimers' in script_h
assert 'case LevelScriptConditionType::timer:' in runner
assert 'script.advanceTimers();' in runner
assert 'case LevelScriptActionType::startTimer:' in runner
assert 'if(cond.mAtLeast)' not in runner, 'the runner must use levelScriptCompare for every number'
assert 'key == "Timer"' in script and 'os << "Timer' in script

# Seat, creature, spell, trap and room conditions
for name in ('seatDefeated', 'ownsCreature', 'creatureHealth', 'spellKnown', 'trapsBuilt', 'roomTiles', 'largestRoom'):
    assert 'case LevelScriptConditionType::%s:' % name in runner, name
assert 'player->getHasLost()' in runner
assert 'isClassMatching(creature, cond.mName2)' in runner

# Creature events and parties
creature = read('source/entities/Creature.cpp')
assert 'case LevelScriptConditionType::creatureEvent:' in runner
for event in ('attacked', 'incapacitated', 'killed', 'pickedup', 'slapped'):
    assert 'recordScriptEvent(*this, "%s")' % event in creature, event
assert 'addPartyMember(action.mParty' in runner
game_map_h = read('source/gamemap/GameMap.h')
assert 'LevelScript.h' not in game_map_h, 'GameMap.h must not include the script header'

# Tiles and tags, possession and boulders, creature names, alliances, terrain, portals, availability
for name in ('tileKinds', 'tilesTagged', 'possessedInRegion', 'boulderInRegion'):
    assert 'case LevelScriptConditionType::%s:' % name in runner, name
for name in ('alterTerrain', 'portalStatus', 'creatureAvailable', 'removeCreature', 'alliance', 'generateCreature',
             'possessCreature'):
    assert 'case LevelScriptActionType::%s:' % name in runner, name
assert 'TileType::manaWell' in runner and 'kind == "manawell"' in runner
assert 'case LevelScriptActionType::countdown:' in runner and 'setScriptCountdown(' in runner
assert 'TIME_LIMIT_COUNTDOWN_FLAG' in read('source/modes/GameMode.cpp') and 'TIME_LIMIT_COUNTDOWN_FLAG' in read('source/gamemap/GameMap.cpp')
assert 'type == "countdown"' in script and 'os << "countdown' in script and 'key == "Countdown"' in script
assert 'case LevelScriptActionType::waveCountdown:' in runner and 'setScriptWaveCountdown(' in runner
assert 'type == "wavecountdown"' in script and 'os << "wavecountdown' in script and 'key == "WaveCountdown"' in script
assert 'mWaveCountdownSeconds' in read('source/network/ODClient.cpp') and 'mWaveCountdownToSend' in read('source/gamemap/GameMap.cpp')
assert 'WaveCountdownDisplay' in read('source/modes/GameMode.cpp') and 'WaveCountdownDisplay' in read('gui/ModeGame.layout')
assert 'startPossession(' in runner and 'newCreature->setName(' in runner
assert 'isPortalOff(getSeat()->getId())' in read('source/rooms/RoomPortal.cpp')
assert 'isCreatureBlocked(getId()' in read('source/game/Seat.cpp')
server_h = read('source/network/ServerNotification.h')
assert server_h.index('seatTeam,') < server_h.index('timeLimit')
assert 'case ServerNotificationType::seatTeam:' in read('source/network/ODClient.cpp')
assert 'case ServerNotificationType::seatTeam:' in read('source/network/ServerNotification.cpp')

# A scripted possession is free
assert 'isFreePossession()' in read('source/creatureaction/CreatureActionPossessed.cpp')
assert 'script.setFreePossession(true)' in runner

# Standing orders, run speed, room owner, slap limit and the extra conditions
for name in ('creatureOrder', 'creatureSpeed', 'roomOwner', 'slapLimit'):
    assert 'case LevelScriptActionType::%s:' % name in runner, name
for name in ('playerSlaps', 'roomFurniture', 'dungeonBreached'):
    assert 'case LevelScriptConditionType::%s:' % name in runner, name
assert 'doCreatureOrder(' in read('source/entities/Creature.cpp')
assert 'registerSlap(' in read('source/network/ODServer.cpp')
assert 'RUN_SPEED_FACTOR = 1.5;' in runner

# Portal stone: a stone that lies on a tile and is carried by a creature of the level
stone_h = read('source/entities/MissileStone.h')
assert 'class MissileStone' in stone_h and 'MissileObjectType::stone' in stone_h
assert 'MissileStone.cpp' in read('CMakeLists.txt')
for name in ('stoneCreate', 'stoneAttach'):
    assert 'case LevelScriptActionType::%s:' % name in runner, name
assert 'type == "stonecreate"' in script and 'type == "stoneattach"' in script
assert 'key == "Stone"' in script and 'os << "Stone' in script

# Rolling ball and bridges
assert 'case LevelScriptActionType::golfBall:' in runner
assert 'slapFrom(' in read('source/entities/MissileBoulder.h')
assert 'type == "golfball"' in script and 'isBoulderHole(' in script

# Kept minion: the strongest fighter comes along to the next level of the campaign (script action keepminion)
campaign = read('source/game/Campaign.cpp')
assert 'case LevelScriptActionType::keepMinion:' in runner and 'setKeptMinion(' in runner
assert 'type == "keepminion"' in script and 'os << "keepminion' in script
assert 'takeKeptMinion(' in runner and 'KeptMinion' in campaign

# The campaign pieces are called Heartstone pieces
assert 'isHeartstoneComplete()' in read('source/network/ODServer.cpp')
assert 'getHeartstonePieces()' in read('source/modes/MenuModeCampaign.cpp')

# Failed spawns and named corpses cannot receive a newly attached transport stone.
attach = runner.split('case LevelScriptActionType::stoneAttach:', 1)[1].split('case LevelScriptActionType::alliance:', 1)[0]
assert 'gameMap.getCreature(action.mText)' in attach
assert 'if((creature != nullptr) && creature->isAlive())' in attach
assert attach.index('creature->isAlive()') < attach.index('script.addStoneCarrier(action.mText)')

print('check_campaign_mechanics: all checks passed')

# Picking up a carrier leaves its stone at the actual tile before removing the creature.
creature_source = read('source/entities/Creature.cpp')
pickup = creature_source.split('void Creature::pickup()', 1)[1].split('\n}\n', 1)[0]
assert pickup.index('if(getIsOnServerMap())') < pickup.index('LevelScriptRunner::dropCarriedStone(*this)')
assert pickup.index('LevelScriptRunner::dropCarriedStone(*this)') < pickup.index('removeEntityFromPositionTile();')
drop = runner.split('void LevelScriptRunner::dropCarriedStone(', 1)[1].split('\n}\n', 1)[0]
assert 'Tile* tile = creature.getPositionTile();' in drop
assert 'script.getStoneCarriers().count(creature.getName()) == 0' in drop
assert drop.index('createStone(gameMap, tile->getX(), tile->getY());') < drop.index('script.removeStoneCarrier(creature.getName());')
print('Carrier pickup leaves the stone on the actual floor tile exactly once: static PASS')

# Physical mission delivery must use workers, the existing carry node and the same ground entity.
mission = read('source/entities/MissileStone.cpp')
worker_gate = mission.split('Tile* MissileStone::getDeliveryTile(', 1)[1].split('\n}\n', 1)[0]
assert '!carrier.isAlive()' in worker_gate and '!carrier.getDefinition()->isWorker()' in worker_gate
assert 'carrier.getSeat()->getId() != mDeliverySeat' in worker_gate
carry_on = mission.split('void MissileStone::notifyEntityCarryOn(', 1)[1].split('\n}\n', 1)[0]
carry_off = mission.split('void MissileStone::notifyEntityCarryOff(', 1)[1].split('\n}\n', 1)[0]
assert 'removeEntityFromPositionTile();' in carry_on and 'mCarried = true;' in carry_on
assert 'mPosition = position;' in carry_off and 'addEntityToPositionTile();' in carry_off
assert 'tile->getX() == mDeliveryX && tile->getY() == mDeliveryY' in carry_off
assert 'new MissileStone' not in carry_off, 'interruption must release the original item, not create a duplicate'
search = read('source/creatureaction/CreatureActionSearchEntityToCarry.cpp')
grab = read('source/creatureaction/CreatureActionGrabEntity.cpp')
carry = read('source/creatureaction/CreatureActionCarryEntity.cpp')
assert 'getDeliveryTile(creature)' in search and 'pathExists(&creature, myTile, destination)' in search
assert 'getDeliveryTile(creature)' in grab and '*entityToCarry, *destination' in grab
mission_action = carry.split('GameEntity& entityToCarry, Tile& tileDest)', 1)[1].split('\n}\n', 1)[0]
assert 'mBuildingDest(nullptr)' in mission_action
assert 'mCreature.carryEntity(mEntityToCarry);' in mission_action
assert 'mEntityToCarry->notifyEntityCarryOff(pos);' in carry and 'mCreature.releaseCarriedEntity();' in carry
assert '"MissionTransport\\t"' in mission and 'mCarried = false;' in mission
actual_delivery = runner.split('case LevelScriptConditionType::deliveredStone:', 1)[1].split('case LevelScriptConditionType::carryingStone:', 1)[0]
assert 'stone->getMissionIdentity() == cond.mName && stone->isDelivered()' in actual_delivery
assert 'gameMap.getCreature' not in actual_delivery, 'marked creature arrival cannot substitute for delivery'
print('Physical worker mission transport: static PASS (runtime verification remains separate)')

# A mission drop requires an observed actual death; recovery cannot mint another copy of the same item.
mission_drop = runner.split('case LevelScriptActionType::stoneDrop:', 1)[1].split('case LevelScriptActionType::stoneAttach:', 1)[0]
assert 'script.getCreatureDeathTile(action.mText, x, y)' in mission_drop
assert 'createStone(gameMap, x, y, &delivery)' in mission_drop
assert 'getStoneCarrierTile' not in mission_drop
create_stone = runner.split('void createStone(', 1)[1].split('\n}\n', 1)[0]
assert create_stone.index('getMissionIdentity() == delivery->mText') < create_stone.index('new MissileStone')
actual_event = creature_source.rsplit('void recordScriptEvent(', 1)[1].split('\n}\n', 1)[0]
assert actual_event.index('if(eventName == "killed")') < actual_event.index('observeCreatureDeath(')
assert 'tile->getX(), tile->getY()' in actual_event
assert 'action.mType == LevelScriptActionType::stoneDrop && action.mText == creatureName' in script
print('Mission drops require exact recorded death coordinates and keep unique identities: static PASS')
