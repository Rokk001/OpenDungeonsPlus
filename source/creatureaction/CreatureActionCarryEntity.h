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

#ifndef CREATUREACTIONCARRYENTITY_H
#define CREATUREACTIONCARRYENTITY_H

#include "creatureaction/CreatureAction.h"
#include "entities/GameEntity.h"

#include <OgreVector2.h>

#include <string>
#include <vector>

class Building;
class GameEntity;
class Tile;

//! \brief Carries one entity to its reserved delivery place, retaining destination changes.
class CreatureActionCarryEntity : public CreatureAction, public GameEntityListener
{
public:
    //! \brief Reserves a fitting cot when starting a carry to an infirmary.
    //! \param forced Whether a hand drop forced this one transport.
    CreatureActionCarryEntity(Creature& creature, GameEntity& entityToCarry, Building& buildingDest, bool forced = false);
    //! \brief Carries a mission item visibly to its exact script destination without inventing a building.
    //! \param forced Whether a hand drop forced this one transport.
    CreatureActionCarryEntity(Creature& creature, GameEntity& entityToCarry, Tile& tileDest, bool forced = false);

    virtual ~CreatureActionCarryEntity();

    CreatureActionType getType() const override
    { return CreatureActionType::carryEntity; }

    std::function<bool()> action() override;

    std::string getListenerName() const override;
    bool notifyDead(GameEntity* entity) override;
    bool notifyRemovedFromGameMap(GameEntity* entity) override;
    bool notifyPickedUp(GameEntity* entity) override;
    bool notifyDropped(GameEntity* entity) override;

    //! \brief Walks cargo to its destination, using a furniture-aware stand position for merchant tables.
    static bool handleCarryEntity(Creature& creature, GameEntity* entityToCarry, Tile* tileDest);

    //! \brief Returns whether a knocked-out creature or body is pulled rather than carried.
    static bool isPulledOverGround(const Creature& carrier, GameEntity& entity);

    //! \brief Advances a ground transport until delivery or interruption.
    bool handleDragCreature();

    //! \brief Returns the entity currently being carried or pulled by this action.
    GameEntity* getCarriedTarget() const { return mEntityToCarry; }
    //! \brief Returns whether a hand drop forced this single transport.
    bool isForced() const { return mForced; }
    //! \brief Keeps a running carry attached when its destination room is absorbed.
    void replaceDestination(Building& oldRoom, Building& newRoom);

private:
    //! \brief Releases cargo and its cot reservation when interrupted.
    //! \brief Releases interrupted cargo and any treasury capacity booked for it.
    void releaseEntity(const std::string& reason);
    void startDrag();
    //! \brief Moves a pulled creature onto its cot or own bed.
    void startLaying(Creature& dragged);
    void followTrail(Creature& dragged, double targetArc);
    bool stopDragging(bool standUp);

    GameEntity* mEntityToCarry;
    Tile* mTileDest;
    Building* mBuildingDest;

    //! True if the entity is pulled instead of carried
    bool mIsDrag;
    //! Whether this ground transport began with an intact corpse.
    bool mCorpseDrag;
    //! Whether the destination is a prison or a crypt rather than an own bed.
    bool mExternalDrag;
    //! Whether the worker completed delivery at the reserved destination.
    bool mDelivered;
    //! Whether the transport is the single task forced by a hand drop.
    bool mForced;
    //! Pulling: 0 while the worker walks, 1 while the creature is moved the last steps into the bed
    int32_t mDragPhase;
    //! Pulling: turns spent in phase 1
    int32_t mDragLayTurns;
    //! Pulling: the way of the worker so far (the first point is where the creature lay) and, for each point, the
    //! length of the way up to it
    std::vector<Ogre::Vector2> mDragTrail;
    std::vector<double> mDragTrailArc;
    //! Pulling: the length of the way up to the point the creature has been sent to
    double mDragFollowArc;
};

#endif // CREATUREACTIONCARRYENTITY_H
