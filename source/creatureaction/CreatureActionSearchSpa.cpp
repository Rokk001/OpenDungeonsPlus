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

#include "creatureaction/CreatureActionSearchSpa.h"

#include "creatureaction/CreatureActionUseRoom.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomSpa.h"
#include "rooms/RoomType.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

//! \brief Gets the function that runs this action.
std::function<bool()> CreatureActionSearchSpa::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionSearchSpa::handleSearchSpa, std::ref(mCreature));
}

//! \brief Looks for the nearest spa of the seat that can take the creature and hands the creature over to it.
bool CreatureActionSearchSpa::handleSearchSpa(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    // The creature has no reason to bathe any more (the mood got better, the hangover is over)
    if(!creature.wantsSpaBath())
    {
        creature.popAction();
        return true;
    }

    // Get the spas controlled by our seat that can take us; without one nothing happens here (no queue, the creature
    // tries again at its next search)
    std::vector<Room*> spas = creature.getGameMap()->getRoomsByTypeAndSeat(RoomType::spa, creature.getSeat());
    std::vector<Tile*> spaTiles;
    for(Room* spa : spas)
    {
        if(spa->numCoveredTiles() <= 0)
            continue;

        if(!static_cast<RoomSpa*>(spa)->canAccept(creature))
            continue;

        Tile* tile = spa->getCoveredTile(0);
        if(tile == nullptr)
        {
            OD_LOG_ERR("creature=" + creature.getName() + ", spa=" + spa->getName());
            continue;
        }

        if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
            continue;

        spaTiles.push_back(tile);
    }

    if(spaTiles.empty())
    {
        creature.popAction();
        return true;
    }

    Tile* chosenTile = nullptr;
    std::list<Tile*> pathToSpa = creature.getGameMap()->findBestPath(&creature, myTile, spaTiles, chosenTile);
    if((chosenTile == nullptr) || !chosenTile->checkCoveringRoomType(RoomType::spa))
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    // Now, the spa reserves the bath place and handles the creature
    creature.popAction();
    creature.pushAction(Utils::make_unique<CreatureActionUseRoom>(creature, *chosenTile->getCoveringRoom(), false));
    return true;
}
