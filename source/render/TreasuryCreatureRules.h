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
#include "rooms/TreasuryGoldLayer.h"

#include <cmath>
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

//! Seconds a worker spends climbing the pile, pouring out the gold and coming back down
static const float pourDuration = 1.4f;

//! Names of the worker clips that replace the procedural climb and tip (skeleton clips, played by the
//! client while the worker delivers gold). Without them the procedural motion is used.
static const char* const pourClimbClip = "ClimbGold";
static const char* const pourTipClip = "PourGold";
//! Share of the pour time (0..1) spent climbing up, and when the descent starts
static const float pourClimbEnd = 0.3f;
static const float pourDescendStart = 0.85f;
//! Clip time kept free at the end of a clip so that it never counts as ended before the phase changes
static const float pourClipMargin = 0.1f;

inline float smoothStep(float edgeStart, float edgeEnd, float t)
{
    if(t <= edgeStart)
        return 0.0f;
    if(t >= edgeEnd)
        return 1.0f;
    const float x = (t - edgeStart) / (edgeEnd - edgeStart);
    return x * x * (3.0f - 2.0f * x);
}

//! Extra height of a pouring worker above the gold surface of its tile at time t (seconds): up to the
//! top of the heap, held while pouring, then down again. Higher piles are climbed higher.
inline float pourRise(float t, int level)
{
    const float amplitude = 0.035f * static_cast<float>(level < 0 ? 0 : level);
    const float progress = t / pourDuration;
    return amplitude * (smoothStep(0.0f, 0.3f, progress) - smoothStep(0.85f, 1.0f, progress));
}

//! Forward lean (radians, negative leans forward) of a pouring worker: tips over the heap, rocks a little
//! while the coins run out, then straightens up.
inline float pourLean(float t)
{
    const float progress = t / pourDuration;
    const float tip = smoothStep(0.3f, 0.5f, progress) - smoothStep(0.85f, 1.0f, progress);
    const float rock = std::sin(progress * 6.2831853f * 3.0f) * 0.07f * smoothStep(0.45f, 0.55f, progress)
        * (1.0f - smoothStep(0.8f, 0.9f, progress));
    return -0.5f * tip + rock;
}

//! Sideways sway (radians) of the climb: the worker wobbles while it scrambles up and down the heap
inline float pourSway(float t)
{
    const float progress = t / pourDuration;
    const float climbing = smoothStep(0.0f, 0.1f, progress) * (1.0f - smoothStep(0.3f, 0.4f, progress))
        + smoothStep(0.85f, 0.9f, progress) * (1.0f - smoothStep(0.97f, 1.0f, progress));
    return std::sin(progress * 6.2831853f * 6.0f) * 0.12f * climbing;
}

//! Phase of the delivery clip at time t (seconds): 0 climb up, 1 pour, 2 climb down (the climb clip backwards)
inline int pourClipPhase(float t)
{
    const float progress = t / pourDuration;
    if(progress < pourClimbEnd)
        return 0;
    return progress < pourDescendStart ? 1 : 2;
}

//! Time position inside the clip of the current phase for the time t (seconds)
inline float pourClipTime(float t, float climbLength, float pourLength)
{
    const float progress = t / pourDuration;
    float time = 0.0f;
    float length = climbLength;
    switch(pourClipPhase(t))
    {
        case 0:
            time = climbLength * progress / pourClimbEnd;
            break;
        case 1:
            time = pourLength * (progress - pourClimbEnd) / (pourDescendStart - pourClimbEnd);
            length = pourLength;
            break;
        default:
            time = climbLength * (1.0f - (progress - pourDescendStart) / (1.0f - pourDescendStart));
            break;
    }
    const float limit = length - pourClipMargin;
    if(time > limit)
        time = limit;
    return time < 0.0f ? 0.0f : time;
}

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

//! Gold dust over completely filled treasuries: seconds between two attempts to start a puff, how long a
//! puff lives and how many puffs a room may show at once by the "Treasury detail" option
static const float dustInterval = 0.7f;
static const float dustLifetime = 3.0f;

inline int dustBudget(TreasuryGoldMesh::Detail detail)
{
    switch(detail)
    {
        case TreasuryGoldMesh::Detail::full:
            return 3;
        case TreasuryGoldMesh::Detail::reduced:
            return 1;
        default:
            return 0;
    }
}

//! Gold dust over the portal of a rich keeper (same puffs and budget per room as the dust over full piles): the
//! keeper is rich when the gold held reaches this share of the treasury capacity and at least the minimum amount.
//! The dust floats this high above the floor of the portal.
static const float portalRichShare = 0.5f;
static const int portalRichMinGold = 500;
static const float portalDustHeight = 0.9f;
//! The dungeon heart of a rich keeper uses the same rule; its dust floats this high above the heart.
static const float heartDustHeight = 1.8f;

inline bool isRichKeeper(int gold, int goldMax)
{
    if(goldMax <= 0 || gold < portalRichMinGold)
        return false;
    return static_cast<float>(gold) >= portalRichShare * static_cast<float>(goldMax);
}

//! Sparkles and sliding coins on the gold of rich treasuries, and the coins that roll away when gold is taken:
//! seconds between two attempts, how long such an effect counts against the budget of its room, and how many
//! a room may show at once by the "Treasury detail" option. They have a budget of their own.
static const float ambientInterval = 0.9f;
static const float ambientLifetime = 2.5f;
static const int ambientBudgetFull = 3;
static const int ambientBudgetReduced = 1;
//! Piles of at least this level slide coins down their slope; the sparkle needs a richer pile
static const int slideLevel = 3;
static const int glintLevel = 5;

inline int ambientBudget(TreasuryGoldMesh::Detail detail)
{
    switch(detail)
    {
        case TreasuryGoldMesh::Detail::full:
            return ambientBudgetFull;
        case TreasuryGoldMesh::Detail::reduced:
            return ambientBudgetReduced;
        default:
            return 0;
    }
}

//! A pile that grows (gold delivered) or sinks (gold taken) is not swapped at once: its height settles over
//! this many seconds. When taking, it dips into a dent first and then smooths out.
static const float pileSettleTime = 0.7f;
static const float dentDepth = 0.88f;
static const float dentShare = 0.35f;

//! Height factor of a settling pile (1 = the new pile) at time t, coming from the factor "from" (the old level
//! over the new one, limited). Growing starts low and rises; taking starts high, dips below 1 and returns.
inline float pileSettleScale(float from, bool taken, float t)
{
    if(t >= pileSettleTime)
        return 1.0f;
    const float progress = t / pileSettleTime;
    if(!taken)
        return from + (1.0f - from) * smoothStep(0.0f, 1.0f, progress);
    if(progress < dentShare)
        return from + (dentDepth - from) * smoothStep(0.0f, dentShare, progress);
    return dentDepth + (1.0f - dentDepth) * smoothStep(dentShare, 1.0f, progress);
}

//! The old level over the new one as a start height factor, kept in a range that looks sane for any change
inline float pileSettleFrom(int oldLevel, int newLevel)
{
    if(oldLevel <= 0 || newLevel <= 0)
        return 1.0f;
    const float ratio = static_cast<float>(oldLevel) / static_cast<float>(newLevel);
    return ratio < 0.4f ? 0.4f : (ratio > 1.6f ? 1.6f : ratio);
}

//! Objects standing in the gold (room objects, gold lying on the floor of a treasury) are drawn partly buried:
//! the deeper the pile of their tile, the larger the share of their height that sinks into the gold. Only a
//! render offset of the object node; position, bounds and paths of the object are not changed.
static const float buryShareFirst = 0.1f;
static const float buryShareFull = 0.5f;
//! The offset settles at this rate (seconds for roughly 95 percent of a change), as fast as the piles themselves
static const float buriedSettleTime = pileSettleTime;
//! A smaller remaining distance is closed at once
static const float buriedSnapDistance = 0.002f;

//! Share of its height (0..1) that an object sinks into a pile of the given level
inline float buryShare(int level)
{
    if(level <= 0)
        return 0.0f;
    const int top = level > TreasuryGoldLayer::maxLevel ? TreasuryGoldLayer::maxLevel : level;
    return buryShareFirst + (buryShareFull - buryShareFirst) * static_cast<float>(top - 1)
        / static_cast<float>(TreasuryGoldLayer::maxLevel - 1);
}

//! Height of the base of an object above the floor, so that the share of its height given by buryShare()
//! is buried below the gold surface. Never below the floor, and always zero where there is no pile.
inline float buriedLift(float surfaceHeight, int level, float objectHeight)
{
    if(level <= 0 || surfaceHeight <= 0.0f)
        return 0.0f;
    const float lift = surfaceHeight - buryShare(level) * (objectHeight > 0.0f ? objectHeight : 0.0f);
    return lift > 0.0f ? lift : 0.0f;
}

//! One step of the smooth move of the offset from current towards target (elapsed seconds)
inline float buriedStep(float current, float target, float elapsed)
{
    const float rate = 1.0f - std::exp(-3.0f * elapsed / buriedSettleTime);
    const float next = current + (target - current) * rate;
    return std::fabs(target - next) < buriedSnapDistance ? target : next;
}

//! The settled piles of a room are drawn as one static batch per room (see TreasuryGoldBatch.h).
//! A changed room is rebuilt at once when it was not rebuilt for this long, otherwise as soon as this time is over
static const float batchRebuildInterval = 0.25f;

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
