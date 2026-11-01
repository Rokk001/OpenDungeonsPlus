#!/usr/bin/env python3
"""Check that urgent needs interrupt room use and sleep without interrupting fights."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
source = (ROOT / 'source/entities/Creature.cpp').read_text(encoding='utf-8')
hungry = source.split('bool Creature::isHungry() const', 1)[1].split('\n}', 1)[0]
assert 'getHungerSeek()' in hungry
need = source.split('bool Creature::needInterrupt(bool servingNeed) const', 1)[1].split('\n}', 1)[0]
for key in ('UrgeSeek', 'ThirstSeek', 'isHungry()', 'servingNeed', 'CreatureActionType::fight', 'CreatureActionType::fightFriendly'):
    assert key in need, key
for key in ('RoomType::hatchery', 'RoomType::tavern', 'numCoveredTiles()', 'RoomToilet::hasToiletRoomFor(*this)',
            'CreatureActionType::searchFood', 'CreatureActionType::searchDrink', 'CreatureActionType::searchToilet'):
    assert key in need, key
room = (ROOT / 'source/creatureaction/CreatureActionUseRoom.cpp').read_text(encoding='utf-8')
assert 'needInterrupt(' in room
assert room.index('if(room == nullptr)') < room.index('if(creature.needInterrupt(servingNeed))')
assert room.index('if(creature.needInterrupt(servingNeed))') < room.index('shouldNotUseIfBadMood')
assert room.index('if(creature.needInterrupt(servingNeed))') < room.index('shouldStopUseIfHungrySleepy')
assert room.index('if(creature.needInterrupt(servingNeed))') < room.index('hasSlapEffect()')
assert 'room->getType() == RoomType::hatchery && creature.isHungry()' in room
assert 'room->getType() == RoomType::tavern' in room and 'getTavernConfigDouble("ThirstSeek")' in room
assert room.index('if(moodRoom && !fighting') < room.index('if(!creature.decreaseJobCooldown())')
assert 'roomType == RoomType::arena || room->shouldNotUseIfBadMood' in room
assert not re.search(r'Random::Int\(\s*0\s*,\s*100\s*\)\s*<\s*20', room)
sleep = (ROOT / 'source/creatureaction/CreatureActionSleep.cpp').read_text(encoding='utf-8')
assert 'needInterrupt(' in sleep
job = (ROOT / 'source/creatureaction/CreatureActionSearchJob.cpp').read_text(encoding='utf-8')
for action in (room, sleep, job):
    interrupt = action.split('if(creature.needInterrupt(', 1)[1].split('return true;', 1)[0]
    for token in ('CreatureActionType::searchFood', 'CreatureActionType::searchDrink',
                  'RoomType::hatchery', 'RoomType::tavern', 'numCoveredTiles()',
                  'if(foodAvailable)', 'else if(drinkAvailable)', 'CreatureActionSearchToilet'):
        assert token in interrupt, token
    assert interrupt.index('if(foodAvailable)') < interrupt.index('else if(drinkAvailable)') < interrupt.index('CreatureActionSearchToilet')
assert '!servingNeed && creature.isHungry()' in room
assert '!servingNeed && creature.getDefinition()->hasThirst()' in room
for action in ('CreatureActionFight.cpp', 'CreatureActionFightFriendly.cpp'):
    assert 'needInterrupt(' not in (ROOT / 'source/creatureaction' / action).read_text(encoding='utf-8')
print('need interrupts ok')
