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

#ifndef TREASURYCREATURERULES_H
#define TREASURYCREATURERULES_H

#include "render/TreasuryGoldMesh.h"

#include <map>

//! \brief Client side rules for creatures walking on the treasury gold: how far they are lifted,
//! when a step splashes coins and how many splashes a room may show at once. Nothing here
//! touches the renderer, the server or the creature position used for pathing.
namespace TreasuryCreatureRules
{
//! From this pile level on the gold is deep enough to splash and clink
static const int deepLevel = 4;
//! Distance walked between two splashes, in tiles
static const float stepDistance = 0.55f;
//! Seconds a splash counts against the budget of its room
static const float splashLifetime = 1.4f;
//! Creatures higher above the floor than this (flying ones) are not lifted
static const float groundHeightLimit = 0.3f;

inline bool isDeep(int level)
{
    return level >= deepLevel;
}

//! Visual lift of a creature standing at the given height above the floor on a pile of the given
//! surface height. Only a render offset: the position of the creature itself is not changed.
inline float liftOnGold(float surfaceHeight, float creatureHeight)
{
    if(surfaceHeight <= 0.0f || creatureHeight > groundHeightLimit)
        return 0.0f;
    return surfaceHeight;
}

//! True when the creature walked far enough since its last splash for the next one
inline bool stepDue(float dx, float dy)
{
    return dx * dx + dy * dy >= stepDistance * stepDistance;
}

//! Particle budget of one room by the "Treasury detail" option
inline int splashBudget(TreasuryGoldMesh::Detail detail)
{
    switch(detail)
    {
        case TreasuryGoldMesh::Detail::full:
            return 6;
        case TreasuryGoldMesh::Detail::reduced:
            return 2;
        default:
            return 0;
    }
}

//! Counts the splashes shown per room (the room is identified by any pointer)
class SplashBudget
{
public:
    //! Takes one place for the room. False when the room already shows limit splashes.
    bool tryAcquire(const void* room, int limit)
    {
        if(limit <= 0)
            return false;
        int& count = mActive[room];
        if(count >= limit)
            return false;
        ++count;
        return true;
    }

    void release(const void* room)
    {
        std::map<const void*, int>::iterator it = mActive.find(room);
        if(it == mActive.end())
            return;
        --it->second;
        if(it->second <= 0)
            mActive.erase(it);
    }

    int active(const void* room) const
    {
        std::map<const void*, int>::const_iterator it = mActive.find(room);
        return it == mActive.end() ? 0 : it->second;
    }

    void clear()
    {
        mActive.clear();
    }

private:
    std::map<const void*, int> mActive;
};
}

#endif // TREASURYCREATURERULES_H
