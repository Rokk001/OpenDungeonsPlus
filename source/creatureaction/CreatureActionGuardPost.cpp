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

#include "creatureaction/CreatureActionGuardPost.h"

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "traps/Trap.h"
#include "traps/TrapType.h"
#include "utils/MakeUnique.h"

#include <list>
#include <memory>
#include <vector>

std::function<bool()> CreatureActionGuardPost::action()
{
    return std::bind(&CreatureActionGuardPost::handleGuardPost,
        std::ref(mCreature), mPostTile);
}

bool CreatureActionGuardPost::handleGuardPost(Creature& creature, Tile* postTile)
{
    Tile* myTile = creature.getPositionTile();
    if((myTile == nullptr) || (postTile == nullptr))
    {
        creature.popAction();
        return false;
    }

    // The post must still be there, belong to our keeper and be installed
    Trap* trap = postTile->getCoveringTrap();
    if((trap == nullptr) ||
       (trap->getType() != TrapType::guardPost) ||
       (trap->getSeat() != creature.getSeat()) ||
       !trap->isActivated(postTile))
    {
        creature.popAction();
        return true;
    }

    // We leave the post to eat, sleep or get our fee
    if(creature.isTired() || creature.isHungry() ||
       ((creature.getGoldFee() > 0) && (creature.getSeat()->getGold() > 0)))
    {
        creature.popAction();
        return true;
    }

    if(myTile != postTile)
    {
        if(!creature.getGameMap()->pathExists(&creature, myTile, postTile))
        {
            creature.popAction();
            return true;
        }

        creature.setDestination(postTile);
        return false;
    }

    // We stand on the post
    creature.setAnimationState(EntityAnimation::idle_anim);
    return false;
}

bool CreatureActionGuardPost::isPostTaken(const Creature& creature, Tile* postTile)
{
    std::vector<Creature*> creatures = creature.getGameMap()->getCreaturesBySeat(creature.getSeat());
    for(Creature* other : creatures)
    {
        if(other == &creature)
            continue;

        for(const std::unique_ptr<CreatureAction>& act : other->getActions())
        {
            if(act->getType() != CreatureActionType::guardPost)
                continue;

            if(static_cast<CreatureActionGuardPost*>(act.get())->getPostTile() == postTile)
                return true;
        }
    }

    return false;
}

bool CreatureActionGuardPost::tryManPost(Creature& creature)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
        return false;

    std::vector<Tile*> posts;
    for(Trap* trap : creature.getGameMap()->getTraps())
    {
        if(trap->getType() != TrapType::guardPost)
            continue;

        if(trap->getSeat() != creature.getSeat())
            continue;

        for(int i = 0; i < static_cast<int>(trap->numCoveredTiles()); ++i)
        {
            Tile* tile = trap->getCoveredTile(i);
            if(!trap->isActivated(tile))
                continue;

            if(isPostTaken(creature, tile))
                continue;

            if(!creature.getGameMap()->pathExists(&creature, myTile, tile))
                continue;

            posts.push_back(tile);
        }
    }

    if(posts.empty())
        return false;

    Tile* chosenTile = nullptr;
    std::list<Tile*> path = creature.getGameMap()->findBestPath(&creature, myTile, posts, chosenTile);
    if(chosenTile == nullptr)
        return false;

    creature.pushAction(Utils::make_unique<CreatureActionGuardPost>(creature, *chosenTile));
    return true;
}
