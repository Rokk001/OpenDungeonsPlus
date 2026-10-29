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

#ifndef AIKNOWLEDGE_H
#define AIKNOWLEDGE_H

#include "ai/AiMath.h"
#include "ai/AiSettings.h"

#include <map>
#include <string>
#include <vector>

class Creature;
class GameMap;
class KeeperAI;
class Mind;
class Seat;
class Tile;

//! rief What the AI saw of one enemy fighter: its hit points and its raw damage per second at the sighting.
struct EnemyRecord
{
    double hp;
    double rawDps;
    //! rief The tile the creature stood on when it was seen (runtime only, not saved).
    Tile* tile;
};

//! rief The last sighting of one enemy seat: the noise factors drawn at that sighting (the estimate multiplies the
//! sums of the records by them), the ready flag of the traps and the records of the enemy fighters seen.
struct SeatSighting
{
    bool valid = false;
    //! rief Game seconds of the sighting.
    double time = 0.0;
    double fHp = 1.0, fDps = 1.0, fGold = 1.0, fMana = 1.0, fTrap = 1.0;
    //! rief The trap potential seen, before the noise factor, and whether it is the own trap set.
    double trapBase = 0.0;
    bool ownTraps = true;
    bool ready = true;
    //! rief Game seconds of the last cast of this seat that the AI saw, -1 when none.
    double lastSpellTime = -1.0;
    //! rief Records by creature name.
    std::map<std::string, EnemyRecord> records;
};

//! rief The sightings of all enemy seats by seat id.
struct SightingState
{
    std::map<int, SeatSighting> seats;
};

//! rief The enemy as the AI believes it to be at a plan step.
struct EnemyEstimate
{
    double hp, dps, gold, mana, trap;
    bool ready;
    //! rief True while the trap set is the AI's own (before the first contact of an own assault).
    bool ownTraps;
};

//! \brief What one AI seat knows of the map. An AI may only read the type, fullness, owner and
//! rooms of a tile (and of the enemy buildings on it) when this class reports the tile as known.
class AiKnowledge
{
public:
    //! \brief Creates the knowledge view of the given seat on the given map. Neither pointer is owned.
    AiKnowledge(GameMap& gameMap, Seat* seat);

    //! \brief True if the seat knows the tile. With fog of war off every tile is known; otherwise
    //! a tile is known when it is owned by the seat or when it was ever in the seat's vision.
    //! \param tile The tile to test. A null tile is never known.
    bool isKnown(Tile* tile) const;

    //! rief The known tile with the smallest straight-line distance from the own heart tile that is owned by a
    //! non-allied seat or on which an enemy creature of a record was seen.
    //! 
eturn nullptr when no enemy tile is known.
    Tile* nearestKnownEnemyTile(const SightingState& sighting) const;

    //! rief Plans the tunnel to the target and marks it for digging: draws the detour of the route once (twice,
    //! taking the longer, on the complex mistake of row I02), builds the polyline start - waypoint - target of
    //! length (1 + detour) x distance and marks it in at most DigActions drags.
    //! \param detour Receives the detour that was drawn.
    //! 
eturn false when no tile could be marked.
    bool planRoute(KeeperAI& ai, Mind& mind, const AiSettings& settings, Tile* start, Tile* target, double& detour) const;

    //! rief Looks at the enemy before an attack (row I03): unless the rule mistake is drawn, every enemy fighter in
    //! the seat's vision gets a record, the five noise factors and the ready flag are drawn for each enemy seat
    //! with a sighting, and ScoutCameraActions camera actions are charged.
    //! \param trapPotential The potential of the trap set the estimate uses (the own set before the first contact of
    //! an own assault, the revealed enemy set after it), with the ready flag of that set.
    //! \param ownTraps True when the trap set is the own one (the trap noise factor is then not applied).
    void scout(KeeperAI& ai, Mind& mind, const AiSettings& settings, SightingState& sighting, double now,
               double trapPotential, bool trapReady, bool ownTraps) const;

    //! rief The enemy as the AI believes it to be (row I04): the last sighting unchanged, or, with no record
    //! at all, the own army scaled by one noise factor. No aging, no decay.
    //! \param ownHp Current hit points of the own fighters.
    //! \param ownDps Raw damage per second of the own fighters.
    //! \param ownMana The own mana.
    //! \param ownTrap The own trap potential.
    //! \param seatId The enemy seat the plan step aims at.
    //! \param now Game seconds.
    //! \param ownIncome The own gross mana income per second (mode observed of EnemyManaEstimate).
    EnemyEstimate estimateEnemy(const AiSettings& settings, const SightingState& sighting, int seatId, double now,
                                double ownHp, double ownDps, double ownMana, double ownTrap, double ownIncome) const;

    //! rief Marks the exploration tunnels (row I05): ExploreTunnelsPerDirection tunnels for each of the four map
    //! directions from the own heart, once; later calls mark nothing.
    //! \param marked In/out: true once the tunnels are marked.
    //! 
eturn true when tunnels were marked by this call.
    bool exploreTunnels(KeeperAI& ai, Mind& mind, bool& marked) const;

    //! rief The enemy fighters standing on a tile the seat has vision of.
    std::vector<Creature*> visibleEnemyFighters() const;

private:
    GameMap& mGameMap;
    Seat* mSeat;
};

#endif // AIKNOWLEDGE_H
