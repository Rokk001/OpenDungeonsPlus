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

#ifndef TRAPDOOR_H
#define TRAPDOOR_H

#include "Trap.h"
#include "traps/TrapType.h"

class DoorEntity;

//! \brief A door with ordinary combat rules or a persistent mission key lock.
class TrapDoor : public Trap
{
public:
    //! \brief Creates an ordinary door; mission locks are restored from level data.
    //! \param doorType One of the door trap types (wooden, ironbound, steel, barricade, secret or runed).
    TrapDoor(GameMap* gameMap, TrapType doorType);

    static const std::string ANIMATION_OPEN;
    static const std::string ANIMATION_CLOSE;

    //! \brief The type of this door.
    const TrapType getType() const override
    { return mDoorType; }

    //! \brief Health given to each tile of a newly built door, depending on the door type.
    double getDefaultTileHP() const override;

    bool isDoor() const override
    { return true; }

    // We return true to make sure every creature with vision on the door tile can see it.
    // A secret door is only seen when a creature of its owner stands on it
    //! \brief Updates door visibility and rolls the configured runed-door damage when it fires.
    bool shoot(Tile* tile) override;

    // The runed door pays its mana itself when it fires (see shoot), not on every upkeep
    double getManaToFire() const override
    { return 0.0; }

    void doUpkeep() override;

    double getHP(Tile* tile) const override;
    //! \brief Preserves mission-locked doors and otherwise applies ordinary door damage.
    double takeDamage(GameEntity* attacker, double absoluteDamage, double physicalDamage, double magicalDamage,
        double elementDamage, Tile* tileTakingDamage, bool ko) override;

    bool displayTileMesh() const override
    { return true; }

    //! \brief The trap object covers the whole tile under
    //! but while it built, the ground tile still must be shown.
    bool shouldDisplayGroundTile() const override
    { return true; }

    //! \brief Ignores hand toggles while a mission key is required.
    void notifyDoorSlapped(DoorEntity* doorEntity, Tile* tile);

    //! \brief Applies the persistent mission lock; only script delivery may release it.
    void setKeyLocked(bool locked);

    //! \brief Creates the door model closed when a mission key is still required.
    TrapEntity* getTrapEntity(Tile* tile) override;

    //! \brief Blocks every creature while mission-locked; otherwise keeps ordinary door rules.
    double getCreatureSpeed(const Creature* creature, Tile* tile) const override;

    //! \brief True only when ordinary ground passage needs no door destruction; attack-path exceptions are excluded.
    bool isGroundPassageOpen(Tile* tile) const
    { return !mKeyLocked && (!isActivated(tile) || (!mIsLocked && !mIsLockedState)); }

    //! \brief Mission locks cannot be removed by claiming the door tile.
    bool isClaimable(Seat* seat) const override;

    //! \brief Keeps mission doors intact until delivery, otherwise applies ordinary capture.
    void claimForSeat(Seat* seat, Tile* tile, double danceRate) override;

    bool permitsVision(Tile* tile) override;

    //! \brief A secret door looks like a wall to every seat that has not seen a creature of the owner
    //! (or of an ally) pass through it. All other doors are always seen as doors.
    bool appearsAsWallForSeat(Tile* tile, Seat* seat) const override;

    //! Returns true if tiles North and South (or east and west) are suitable to have a door on the
    //! given tile
    static bool canDoorBeOnTile(GameMap* gameMap, Tile* tile);

    static bool buildTrapOnTile(GameMap* gameMap, Player* player, Tile* tile);

protected:
    //! \brief Saves ordinary and optional mission lock state on the door data line.
    void exportToStream(std::ostream& os) const override;
    //! \brief Loads old door data or its optional persistent mission lock.
    bool importFromStream(std::istream& is) override;

private:
    //! \brief Type of this door (wooden, ironbound, steel, barricade, secret or runed)
    TrapType mDoorType;
    //! \brief Wanted state for the door (changes when the player slaps the door)
    bool mIsLocked;
    //! \brief Current state of the door
    bool mIsLockedState;
    //! \brief Blocks damage, passage and hand toggles until key delivery.
    bool mKeyLocked;
    //! \brief Turns left before a runed door can fire again
    uint32_t mFireCooldownTurns;

    void changeDoorState(DoorEntity* doorEntity, Tile* tile, bool locked);
};

#endif // TRAPDOOR_H
