/*!
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

#ifndef AITRAPS_H
#define AITRAPS_H

#include <utility>
#include <vector>

class KeeperAI;
class Tile;

//! \brief The trap and door decisions of the keeper AI. Every build goes through the ACTS wrappers, so the AI pays the
//! prices and follows the research and the workshop limits of a human keeper.
namespace TRAP
{
//! \brief A way into the AI's land: the corridor tile where a door can stand and the direction a walker takes through it.
struct Entrance
{
    //! \brief The own tile where the door stands.
    Tile* mDoor;
    //! \brief The step from the outside to the inside at the door (the walker's direction), x part.
    int mDx;
    //! \brief The step from the outside to the inside at the door (the walker's direction), y part.
    int mDy;
};

//! \brief What the trap and door rows remember for one keeper AI. It lives as long as the AI; the decisions that last
//! longer than one trigger are saved as "draw" lines of the AI state.
struct State
{
    //! \brief Starts with nothing drawn, watched or fortified.
    State();
    //! \brief The draw of row F01 (once per game): -1 not drawn yet, 1 half the trap tiles, 0 the full number.
    int mWantDivided;
    //! \brief True while the AI thinks of its empty traps after a fight (row F12).
    bool mWatching;
    //! \brief Game time of the last test for an exhausted own trap tile (row F12).
    double mLastTestSeconds;
    //! \brief The result of that test.
    bool mExhausted;
    //! \brief Every fortified tunnel breakthrough tile (x, y) of the AI's land (row F15).
    std::vector<std::pair<int, int>> mTunnels;
    //! \brief Mind time at which the AI starts watching its empty traps after the F12 mistake, -1 when none is pending.
    double mWatchDue;
    //! \brief Mind time at which the doors are looked at again after the F13 mistake, -1 when none is pending.
    double mDoorDue;
    //! \brief A tunnel fortification that waits for the symptom delay of the F15 mistake.
    struct PendingFortify
    {
        int mX;
        int mY;
        //! \brief Mind time at which the tunnel is fortified.
        double mDue;
    };
    //! \brief The tunnel fortifications delayed by the F15 mistake.
    std::vector<PendingFortify> mFortifyDue;
    //! \brief True once the saved draw lines of the mind were read.
    bool mRestored;
};

//! \brief Connects the trap and door rows to the mind of the AI: the trap look (F01-F11, F13, F14), FightOver (F12),
//! BuildingDestroyed (F13, a broken door), TunnelOpen (F15), the delayed steps of their mistakes and the saved draw lines.
void bindRows(KeeperAI& ai);

//! \brief Finds the entrances of the AI's land: own claimed tiles where a door can stand and that touch a known open
//! tile not claimed for the AI, plus every tunnel entrance that was fortified.
std::vector<Entrance> findEntrances(KeeperAI& ai);

//! \brief The trap look: plans the traps and doors of the entrances and builds at most one door or one trap tile.
//! Does nothing without a workshop and the minimum number of room types.
//! \param specialDoorMistake Optional shared F14 draw, initially -1.
void trapLook(KeeperAI& ai, int* specialDoorMistake = nullptr);

//! \brief Builds the next trap tile: the basic mix (spike, cannon, gas) up to the planned number of tiles, then one of
//! the special traps (boulder, lightning, fireburst, freeze, alarm, fear trap, watch banner and trigger) per look. A
//! special trap that cannot be built at this look does not stop the next one.
//! \param trapTiles How many trap tiles the AI owns now.
//! \param want The number of trap tiles the plan asks for.
//! \param entrances The entrances of the AI.
//! \return true when a trap was scheduled.
bool placeTrap(KeeperAI& ai, int trapTiles, int want, const std::vector<Entrance>& entrances);

//! \brief Called once after a fight, after the symptom delay of FightOver: from then, while an own trap tile is
//! exhausted, every purchase keeps TrapGoldMargin free (reloadMargin). The rule mistake adds another symptom delay
//! before the AI thinks of the empty traps.
//! \return true when the AI watches the traps now, false when the mistake delayed it.
bool reloadGate(KeeperAI& ai);

//! \brief The gold every purchase keeps free while the AI watches its exhausted traps; 0 otherwise.
double reloadMargin(KeeperAI& ai);

//! \brief Tells whether a purchase of the given cost is allowed while the AI watches its exhausted traps (row F12): the
//! gold must cover the cost, RoomGoldMargin, the wage bill and TrapGoldMargin. Always true while it does not watch them;
//! then only the purchase rule of the caller applies.
//! \param cost The gold the purchase costs.
bool reloadAllows(KeeperAI& ai, double cost);

//! \brief Builds the door of the best researched kind on an entrance without it, or the special doors: the secret door
//! at the treasury entrance and the runed door at the entrance nearest to the heart. The rule mistake forgets the
//! upgrade: existing doors stay, an entrance without a door gets a wooden one, and the doors are looked at again after
//! a symptom delay.
//! \param resumed True for the delayed look of a forgotten upgrade: it carries out the upgrade already decided at the
//! look that drew the mistake, without a new draw and without the special doors of that look.
//! \param specialDoorMistake Optional shared F14 draw, initially -1.
//! \return true when a door was scheduled or a door waits for its gold: then the look buys no trap.
bool placeDoor(KeeperAI& ai, const std::vector<Entrance>& entrances, bool resumed = false, int* specialDoorMistake = nullptr);

//! \brief Fortifies the new tunnel entrance after the reaction time: three more trap tiles, a door and a barricade.
//! The rule mistake adds a symptom delay before the fortification.
//! \param breakthrough The tile where the tunnel breaks into the AI's land.
//! \return false when the mistake delayed it.
bool fortifyTunnel(KeeperAI& ai, Tile* breakthrough);

//! \brief The seconds until the earliest tunnel fortification delayed by the F15 mistake, for the fortifyRemaining
//! token of the saved tunnel line.
//! \return -1 when no fortification is pending.
double fortifyRemaining(KeeperAI& ai);
}

#endif // AITRAPS_H
