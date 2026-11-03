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

#include "creatureaction/CreatureActionRampage.h"

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <functional>
#include <vector>

//! \brief Tiles the search for a new target tries before it gives up (a path is computed for each).
static const uint32_t RAMPAGE_TARGET_TRIES = 8;

std::function<bool()> CreatureActionRampage::action()
{
    return std::bind(&CreatureActionRampage::handleRampage,
        std::ref(mCreature));
}

//! \brief Walks to the target room tile and stays on it. A target that is gone (destroyed, sold, lost) is replaced; when no
//! room tile can be reached the action ends and the creature wanders around.
bool CreatureActionRampage::handleRampage(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(!creature.isRampaging() || (myTile == nullptr))
    {
        creature.popAction();
        return false;
    }

    Tile* target = creature.getRampageTarget();
    if((target != nullptr) && !isTargetTile(creature, *target))
    {
        creature.clearRampageTarget();
        target = nullptr;
    }

    if(target == nullptr)
    {
        target = findTarget(creature);
        if(target == nullptr)
        {
            creature.popAction();
            return false;
        }

        creature.setRampageTarget(target);
    }

    // On the target tile the creature stays; the hits are counted by the creature itself
    if(myTile == target)
        return false;

    if(creature.isMoving())
        return false;

    if(!creature.setDestination(target))
    {
        creature.clearRampageTarget();
        creature.popAction();
    }
    return false;
}

//! \brief True for a tile of a room of the keeper that can still be attacked, except the dungeon heart and the portals.
bool CreatureActionRampage::isTargetTile(const Creature& creature, const Tile& tile)
{
    Room* room = tile.getCoveringRoom();
    if((room == nullptr) || (room->getSeat() != creature.getSeat()))
        return false;

    if((room->getType() == RoomType::dungeonTemple) || (room->getType() == RoomType::portal))
        return false;

    return room->isAttackable(const_cast<Tile*>(&tile), creature.getSeat());
}

//! \brief Chooses a random room tile of the keeper that the creature may hit and can reach.
Tile* CreatureActionRampage::findTarget(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
        return nullptr;

    std::vector<Tile*> candidates;
    for(Room* room : creature.getGameMap()->getRooms())
    {
        if((room->getSeat() != creature.getSeat()) || (room->getType() == RoomType::dungeonTemple) ||
           (room->getType() == RoomType::portal))
        {
            continue;
        }

        for(Tile* tile : room->getCoveredTiles())
        {
            if(isTargetTile(creature, *tile))
                candidates.push_back(tile);
        }
    }

    for(uint32_t tries = 0; (tries < RAMPAGE_TARGET_TRIES) && !candidates.empty(); ++tries)
    {
        const uint32_t index = Random::Uint(0, candidates.size() - 1);
        Tile* tile = candidates[index];
        if((tile == myTile) || creature.getGameMap()->pathExists(&creature, myTile, tile))
            return tile;

        candidates.erase(candidates.begin() + index);
    }

    return nullptr;
}

//! \brief Hits the room tile with absolute damage, so neither the attack nor the defense of the creature or the room counts.
bool CreatureActionRampage::hitTile(Creature& creature, Tile& tile)
{
    if(!isTargetTile(creature, tile))
        return false;

    Room* room = tile.getCoveringRoom();
    const double damage = ConfigManager::getSingleton().getRampageConfigDouble("RampageTileDamage");
    OD_LOG_INF("creature=" + creature.getName() + " hits the room tile of room=" + room->getName());
    room->takeDamage(&creature, damage, 0.0, 0.0, 0.0, &tile, false);
    return isTargetTile(creature, tile);
}
