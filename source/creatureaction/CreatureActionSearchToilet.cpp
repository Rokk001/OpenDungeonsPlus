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

#include "creatureaction/CreatureActionSearchToilet.h"

#include "creatureaction/CreatureActionUseToilet.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "rooms/RoomToilet.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

std::function<bool()> CreatureActionSearchToilet::action()
{
    return std::bind(&CreatureActionSearchToilet::handleSearchToilet, std::ref(mCreature));
}

bool CreatureActionSearchToilet::handleSearchToilet(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    // The urge is gone (or it was relieved in the meantime)
    if(creature.getUrge() < ConfigManager::getSingleton().getDirtConfigDouble("UrgeSeek"))
    {
        creature.popAction();
        return true;
    }

    // Without a toilet room there is nothing to do, the creature goes on until it cannot hold it any longer
    if(!RoomToilet::hasToiletRoomFor(creature))
    {
        creature.popAction();
        return true;
    }

    // The nearest free seat is reserved at once and used
    Tile* seatTile = RoomToilet::findFreeToiletTile(creature);
    if(seatTile != nullptr)
    {
        creature.popAction();
        creature.pushAction(Utils::make_unique<CreatureActionUseToilet>(creature, seatTile));
        return true;
    }

    // Every seat is busy: the creature waits close to the toilet room until a seat frees up
    bool waiting = false;
    Tile* waitTile = RoomToilet::findWaitTile(creature, waiting);
    if(waiting)
        return false;

    // Nothing reachable to wait at: the creature goes on with its day until it cannot hold it any longer
    if((waitTile == nullptr) || !creature.setDestination(waitTile))
    {
        creature.popAction();
        return true;
    }

    return true;
}
