#include "ai/AiCare.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/KeeperAI.h"
#include "creatureaction/CreatureAction.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/Random.h"

#include <algorithm>
#include <vector>

namespace
{
//! \brief Returns living own fighters the keeper can move without interrupting possession or captivity.
std::vector<Creature*> ownFighters(KeeperAI& ai)
{
    std::vector<Creature*> fighters;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
    {
        if(creature->isAlive() && !creature->isKo() && creature->getIsOnMap() &&
           !creature->isInContainment() && !creature->isPossessed() &&
           !creature->getDefinition()->isWorker() && !creature->getDefinition()->isChampion())
            fighters.push_back(creature);
    }
    return fighters;
}

//! \brief Tests the idle action list specified for hand placement into the training hall.
bool idle(const Creature& creature)
{
    const CreatureActionType busy[] = {CreatureActionType::useRoom, CreatureActionType::sleep,
        CreatureActionType::eatChicken, CreatureActionType::fight, CreatureActionType::flee,
        CreatureActionType::searchFood, CreatureActionType::findHome};
    for(CreatureActionType action : busy)
        if(creature.isActionInList(action))
            return false;
    return true;
}

//! \brief Orders fighters by the current HP times raw damage per second.
bool stronger(const Creature* left, const Creature* right)
{
    return left->getHP() * left->getRawDamagePerSecond() > right->getHP() * right->getRawDamagePerSecond();
}

//! \brief Finds an own room with space for this creature.
Room* availableRoom(KeeperAI& ai, Creature* creature, RoomType type)
{
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(type, ai.getControlledPlayer().getSeat()))
        if(room->hasOpenCreatureSpot(creature) && !room->getCoveredTiles().empty())
            return room;
    return nullptr;
}

//! \brief Schedules the human pickup and drop path onto claimed room ground.
void moveToRoom(KeeperAI& ai, Creature* creature, Room* room)
{
    if(room == nullptr)
        return;
    for(Tile* tile : room->getCoveredTiles())
        if(tile->isClaimedForSeat(ai.getControlledPlayer().getSeat()) && !tile->isFullTile())
        {
            ACTS::moveCreature(ai, creature, tile);
            return;
        }
}
}

//! \brief Handles the idle-fighter part of the hand rally; combat and wounded moves belong to the war rows.
void CARE::idleToHall(KeeperAI& ai)
{
    // AI row D06
    std::vector<Creature*> fighters = ownFighters(ai);
    std::sort(fighters.begin(), fighters.end(), stronger);
    if(ai.getMind().slip("D06"))
    {
        for(size_t count = fighters.size(); count > 1; --count)
        {
            const size_t index = static_cast<size_t>(Random::Int(0, static_cast<int>(count) - 1));
            std::swap(fighters[count - 1], fighters[index]);
        }
    }
    for(Creature* creature : fighters)
        if(idle(*creature))
            moveToRoom(ai, creature, availableRoom(ai, creature, RoomType::trainingHall));
}

//! \brief Handles the creature-list look for capped training and lack of work.
void CARE::levelWatch(KeeperAI& ai)
{
    // AI row D08
    if(ai.getMind().slip("D08"))
        return;
    for(Creature* creature : ownFighters(ai))
    {
        bool capped = false;
        for(Room* hall : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::trainingHall,
                ai.getControlledPlayer().getSeat()))
            if(!hall->hasOpenCreatureSpot(creature))
                capped = true;
        Room* destination = capped ? availableRoom(ai, creature, RoomType::arena) : nullptr;
        if(destination == nullptr && idle(*creature))
        {
            destination = availableRoom(ai, creature, RoomType::casino);
            if(destination == nullptr)
                destination = availableRoom(ai, creature, RoomType::temple);
        }
        moveToRoom(ai, creature, destination);
    }
}

//! \brief Handles one mood event, choosing the highest room affinity among rooms with a free place.
void CARE::moodRelief(KeeperAI& ai)
{
    // AI row D09
    if(ai.getMind().slip("D09"))
        return;
    const RoomType types[] = {RoomType::casino, RoomType::tavern, RoomType::spa, RoomType::temple};
    for(Creature* creature : ownFighters(ai))
    {
        if(creature->getMoodValue() < CreatureMoodLevel::Upset)
            continue;
        Room* best = nullptr;
        double likeness = 0.0;
        for(RoomType type : types)
        {
            Room* room = availableRoom(ai, creature, type);
            if(room == nullptr)
                continue;
            const double value = creature->getDefinition()->getRoomAffinity(type).getLikeness();
            if(best == nullptr || value > likeness)
            {
                best = room;
                likeness = value;
            }
        }
        moveToRoom(ai, creature, best);
    }
}
