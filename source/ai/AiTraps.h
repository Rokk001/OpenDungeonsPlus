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

#include <string>
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

//! \brief Finds the entrances of the AI's land: own claimed tiles where a door can stand and that touch a known open
//! tile not claimed for the AI, plus the tunnel entrance once the tunnel was fortified.
std::vector<Entrance> findEntrances(KeeperAI& ai);

//! \brief The trap look: plans the traps and doors of the entrances and builds at most one door or one trap tile.
//! Does nothing without a workshop and the minimum number of room types.
void trapLook(KeeperAI& ai);

//! \brief Builds the next trap tile: the basic mix (spike, cannon, gas) up to the planned number of tiles, then one of
//! the special traps (boulder, lightning, fireburst, freeze, alarm, fear trap, watch banner and trigger) per look.
//! \param trapTiles How many trap tiles the AI owns now.
//! \param want The number of trap tiles the plan asks for.
//! \param entrances The entrances of the AI.
//! \return true when a trap was scheduled.
bool placeTrap(KeeperAI& ai, int trapTiles, int want, const std::vector<Entrance>& entrances);

//! \brief Called once after a fight: the AI decides whether it thinks of the empty traps. While it does and an own trap
//! tile is exhausted, every purchase keeps TrapGoldMargin free (reloadMargin).
//! \return true when the AI watches the traps now, false when it forgot them.
bool reloadGate(KeeperAI& ai);

//! \brief The gold every purchase keeps free while the AI watches its exhausted traps; 0 otherwise.
double reloadMargin(KeeperAI& ai);

//! \brief Builds the door of the best researched kind on an entrance without it, or the special doors: the secret door
//! at the treasury entrance and the runed door at the entrance nearest to the heart.
//! \return true when a door was scheduled.
bool placeDoor(KeeperAI& ai, const std::vector<Entrance>& entrances);

//! \brief Fortifies the new tunnel entrance after the reaction time: three more trap tiles, a door and a barricade.
//! \param breakthrough The tile where the tunnel breaks into the AI's land.
//! \return false when the AI forgot it.
bool fortifyTunnel(KeeperAI& ai, Tile* breakthrough);

//! \brief Returns the decisions of this seat that last longer than one trigger as the tokens "rowId name value" of the
//! lines "draw" of the AI state.
std::vector<std::string> exportDraws(int seatId);

//! \brief Restores one decision of the lines "draw" of the AI state; unknown names are ignored.
void importDraw(int seatId, const std::string& rowId, const std::string& name, const std::string& value);
}

#endif // AITRAPS_H
