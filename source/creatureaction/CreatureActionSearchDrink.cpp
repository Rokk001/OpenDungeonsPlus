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

#include "creatureaction/CreatureActionSearchDrink.h"

#include "creatureaction/CreatureActionUseRoom.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

//! \brief Gets the function that runs this action.
std::function<bool()> CreatureActionSearchDrink::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionSearchDrink::handleSearchDrink,
        std::ref(mCreature), mForced);
}

//! \brief Looks for the nearest tavern of the seat with a free place and hands the creature over to it.
bool CreatureActionSearchDrink::handleSearchDrink(Creature& creature, bool forced)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    // Check if the creature is thirsty enough
    if(!forced && (creature.getThirst() < ConfigManager::getSingleton().getTavernConfigDouble("ThirstSeek")))
    {
        creature.popAction();
        return true;
    }

    // Get the taverns controlled by our seat; without one nothing happens here (the malus of the thirst acts)
    std::vector<Room*> taverns = creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::tavern, creature.getSeat());
    std::vector<Tile*> tavernTiles;
    for(Room* tavern : taverns)
    {
        if(tavern->numCoveredTiles() <= 0)
            continue;

        if(!tavern->hasOpenCreatureSpot(&creature))
            continue;

        Tile* tile = tavern->getCoveredTile(0);
        if(tile == nullptr)
        {
            OD_LOG_ERR("creature=" + creature.getName() + ", tavern=" + tavern->getName());
            continue;
        }

        if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
            continue;

        tavernTiles.push_back(tile);
    }

    if(tavernTiles.empty())
    {
        creature.popAction();
        return true;
    }

    Tile* chosenTile = nullptr;
    std::list<Tile*> pathToTavern = creature.getGameMap()->findBestPath(&creature, myTile, tavernTiles, chosenTile);
    if((chosenTile == nullptr) || !chosenTile->checkCoveringRoomType(RoomType::tavern))
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    // Now, the tavern handles the creature
    creature.popAction();
    creature.pushAction(Utils::make_unique<CreatureActionUseRoom>(creature, *chosenTile->getCoveringRoom(), forced));
    return true;
}
