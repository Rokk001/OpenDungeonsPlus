/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "creatureaction/CreatureActionSearchJob.h"

#include "creatureaction/CreatureActionGetFee.h"
#include "creatureaction/CreatureActionSearchFood.h"
#include "creatureaction/CreatureActionSearchToilet.h"
#include "creatureaction/CreatureActionSearchDrink.h"
#include "creatureaction/CreatureActionSearchSpa.h"
#include "creatureaction/CreatureActionSleep.h"
#include "creatureaction/CreatureActionUseRoom.h"
#include "creatureaction/CreatureActionCrackBox.h"
#include "creatureaction/CreatureActionHarvestHerbs.h"
#include "creatureaction/CreatureActionBrewPotion.h"
#include "rooms/RoomWorkshop.h"
#include "rooms/RoomCasino.h"
#include "utils/ConfigManager.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/CreatureRelationships.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/RoomObjectNavigation.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

//! \brief Selects the ordinary room action or its item-box workshop specialization.
static std::unique_ptr<CreatureAction> createRoomWorkAction(Creature& creature, Room& room, bool forced, bool moodRoom = false)
{
    if(room.getType() == RoomType::herbGarden)
        return std::unique_ptr<CreatureAction>(new CreatureActionHarvestHerbs(creature, room, forced));
    if(room.getType() == RoomType::alchemyLab)
        return std::unique_ptr<CreatureAction>(new CreatureActionBrewPotion(creature, room, forced));
    if(room.getType() == RoomType::workshop && static_cast<RoomWorkshop&>(room).hasCrackJob())
        return std::unique_ptr<CreatureAction>(new CreatureActionCrackBox(creature, room, forced));
    return std::unique_ptr<CreatureAction>(new CreatureActionUseRoom(creature, room, forced, moodRoom));
}

std::function<bool()> CreatureActionSearchJob::action()
{
    return std::bind(&CreatureActionSearchJob::handleSearchJob,
        std::ref(mCreature), mForced);
}

//! \brief Selects an allowed room job and its corresponding ordinary or specialized work action.
bool CreatureActionSearchJob::handleSearchJob(Creature& creature, bool forced)
{
    // Current creature tile position
    Tile* myTile = creature.getPositionTile();
    if (myTile == nullptr)
    {
        creature.popAction();
        return false;
    }

    const bool moodSearch = creature.getMoodValue() >= CreatureMoodLevel::Upset ||
        creature.getMissedWages() >= ConfigManager::getSingleton().getUnpaidWagesStopWork();

    if(creature.needInterrupt(false))
    {
        creature.popAction();
        if(creature.getUrge() >= ConfigManager::getSingleton().getDirtConfigDouble("UrgeSeek"))
            creature.pushAction(Utils::make_unique<CreatureActionSearchToilet>(creature));
        else if(creature.isHungry())
            creature.pushAction(Utils::make_unique<CreatureActionSearchFood>(creature, false));
        else
            creature.pushAction(Utils::make_unique<CreatureActionSearchDrink>(creature, false));
        return true;
    }

    if(!creature.hasSlapEffect())
    {
        // The creature should look for gold after payday if the keeper is not broke
        if((creature.getGoldFee() > 0) &&
           (!creature.hasActionBeenTried(CreatureActionType::getFee)) &&
           (creature.getSeat()->getGold() > 0))
        {
            creature.pushAction(Utils::make_unique<CreatureActionGetFee>(creature));
            return true;
        }

        // If we are sleepy, we go to bed unless we have been slapped
        if (creature.isTired())
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
            return true;
        }

        // If we are hungry, we try to find food unless we have been slapped
        if (creature.isHungry())
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSearchFood>(creature, false));
            return true;
        }

        // If we are in a bad mood or have a hangover, we go to a lava spa unless we have been slapped (the mood check
        // above lets only the upset creatures through; the others look for the spa when they are idle)
        if(creature.wantsSpaBath() && !creature.hasActionBeenTried(CreatureActionType::searchSpa))
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSearchSpa>(creature));
            return true;
        }
    }

    if(forced && !moodSearch)
    {
        // We check if we can work in the given room
        Room* room = myTile->getCoveringRoom();
        for(const CreatureRoomAffinity& affinity : creature.getDefinition()->getRoomAffinity())
        {
            if(room == nullptr)
                continue;
            if(room->getType() != affinity.getRoomType())
                continue;
            if(affinity.getEfficiency() <= 0)
                continue;
            if(!creature.getSeat()->canOwnedCreatureUseRoomFrom(room->getSeat()))
                continue;

            // It is the room responsibility to test if the creature is suited for working in it
            if(room->hasOpenCreatureSpot(&creature))
            {
                creature.pushAction(createRoomWorkAction(creature, *room, forced));
                return false;
            }
            break;
        }

        // If we couldn't work on the room we were forced to, we stop trying
        creature.popAction();
        return true;
    }

    std::vector<Room*> workRooms;
    std::vector<Room*> pleasureRooms;
    int32_t workLikeness = 0;
    int32_t pleasureLikeness = 0;
    for(const CreatureRoomAffinity& affinity : creature.getDefinition()->getRoomAffinity())
    {
        const RoomType type = affinity.getRoomType();
        const bool pleasure = type == RoomType::casino || type == RoomType::tavern ||
            type == RoomType::spa || type == RoomType::temple;
        if(affinity.getLikeness() <= 0 || affinity.getEfficiency() <= 0 || (moodSearch && !pleasure))
            continue;
        for(Room* room : creature.getGameMap()->getRooms())
        {
            if(room->getSeat() != creature.getSeat() || room->getType() != type ||
               room->numCoveredTiles() <= 0 || !room->hasOpenCreatureSpot(&creature))
                continue;
            if(type == RoomType::casino && static_cast<RoomCasino*>(room)->getPayout() == CasinoPayout::money)
                continue;
            Tile* tile = room->getCoveredTile(0);
            if(tile == nullptr || !creature.getGameMap()->pathExists(&creature, myTile, tile))
                continue;
            std::vector<Room*>& candidates = pleasure ? pleasureRooms : workRooms;
            int32_t& best = pleasure ? pleasureLikeness : workLikeness;
            if(affinity.getLikeness() < best)
                continue;
            if(affinity.getLikeness() > best)
            {
                candidates.clear();
                best = affinity.getLikeness();
            }
            candidates.push_back(room);
        }
    }
    std::vector<Room*>& candidates = workRooms.empty() ? pleasureRooms : workRooms;
    if(!candidates.empty())
    {
        std::vector<Room*> preferred;
        for(Room* room : candidates)
        {
            if(!room->hasHatedCoworker(&creature))
                preferred.push_back(room);
        }
        std::vector<Room*>& choices = preferred.empty() ? candidates : preferred;
        Room* room = choices[Random::Uint(0, choices.size() - 1)];
        creature.pushAction(createRoomWorkAction(creature, *room, forced, moodSearch));
        return true;
    }

    // Keep the existing room wandering behaviour when no work or pleasure room is available.
    Room* currentRoom = myTile->getCoveringRoom();
    if(!moodSearch && currentRoom != nullptr &&
       creature.getSeat()->canOwnedCreatureUseRoomFrom(currentRoom->getSeat()))
    {
        for(const CreatureRoomAffinity& affinity : creature.getDefinition()->getRoomAffinity())
        {
            if(affinity.getRoomType() != currentRoom->getType() || affinity.getLikeness() <= 0 ||
               (affinity.getEfficiency() > 0 && currentRoom->getType() != RoomType::hatchery))
                continue;
            std::vector<Tile*> wanderTiles = currentRoom->getCoveredTiles();
            RoomObjectNavigation::keepTilesWithStandingPosition(creature, wanderTiles);
            if(!wanderTiles.empty())
                creature.setDestination(wanderTiles[Random::Uint(0, wanderTiles.size() - 1)]);
            return false;
        }
    }

    // We found no job. If the creature wanted to work, it gets frustrated
    for(const CreatureRoomAffinity& affinity : creature.getDefinition()->getRoomAffinity())
    {
        if((affinity.getLikeness() > 0) && (affinity.getEfficiency() > 0))
        {
            creature.increaseNbTurnsOutOfWork();
            creature.fireImpatientIfNeeded();
            break;
        }
    }

    // Default action
    creature.popAction();
    return true;
}
