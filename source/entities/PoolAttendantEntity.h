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

#ifndef POOLATTENDANTENTITY_H
#define POOLATTENDANTENTITY_H

#include "entities/PoolAttendantState.h"
#include "entities/RenderedMovableEntity.h"

#include <cstdint>
#include <string>

class GameMap;
class ODPacket;
class RoomSpa;
class Tile;

//! \brief The clips of the pool attendant (besides the clips every entity has: Walk and Jump are the common names).
namespace PoolAttendantPose
{
    //! The attendant sits on the chair (loop).
    static const std::string sit = "Sit";
    //! The attendant whistles at the bathers.
    static const std::string whistle = "Whistle";
    //! The attendant waves his towel.
    static const std::string towelWave = "TowelWave";
    //! The attendant nods off and nearly falls off the chair.
    static const std::string doze = "Doze";
    //! The attendant climbs the ladder of the chair.
    static const std::string climb = "Climb";
}

//! \brief The figure on the high chair of a lava spa. It is pure entertainment: not a creature, it has no wage, no hit
//! points, cannot be fought, picked up or slapped and blocks nothing. It belongs to the seat of the room and changes
//! owner with it. It sits on the chair, every few seconds whistles at the bathers, waves its towel or dozes off, and
//! now and then climbs down, walks to the springboard, jumps into the pool, walks back and climbs up. The room spawns
//! it on the chair, hands it over when the chair tile changes rooms, removes it with the room and saves it in its
//! stream (the entity itself is not saved).
class PoolAttendantEntity: public RenderedMovableEntity
{
public:
    //! \brief Name of the mesh of the pool attendant.
    static const std::string MESH_NAME;

    //! \brief Creates a pool attendant that is not on the map yet.
    //! \param gameMap The map the figure belongs to.
    //! \param roomName The name of the spa; it is the base of the unique name of the figure.
    //! \param rotationAngle The angle (degrees) the figure is turned by, the same as the chair it sits on.
    PoolAttendantEntity(GameMap* gameMap, const std::string& roomName, Ogre::Real rotationAngle);
    //! \brief Creates an empty entity that is filled from a packet.
    PoolAttendantEntity(GameMap* gameMap);

    //! \brief Returns GameEntityType::poolAttendantEntity.
    virtual GameEntityType getObjectType() const override;

    //! \brief Server side, once per turn. Counts down the acts and the jump of the attendant and moves him on.
    virtual void doUpkeep() override;

    //! \brief Client side, every frame. Moves the attendant along the arc of a jump the server told.
    //! \param timeSinceLastFrame The elapsed time since the last frame in seconds.
    virtual void update(Ogre::Real timeSinceLastFrame) override;

    //! \brief A position the server sets cancels a jump a client is showing.
    //! \param position The new position.
    //! \param gameMap The map, the one of the entity if null.
    virtual void setPosition(const Ogre::Vector3& position, GameMap* gameMap = nullptr) override;

    //! \brief Server side. Puts a new attendant on the seat of the chair, owned by the seat of the room.
    //! \param gameMap The map to put the figure on.
    //! \param room The spa the attendant belongs to.
    //! \param chairTile The tile of the chair; nothing happens if it is null.
    //! \param rotationAngle The angle (degrees) the figure is turned by.
    //! \return The new figure, nullptr if the room or the tile is missing.
    static PoolAttendantEntity* spawnOnChair(GameMap* gameMap, RoomSpa* room, Tile* chairTile, Ogre::Real rotationAngle);

    //! \brief Server side. Takes the figure off the map and deletes it. The caller must not use it afterwards.
    void removeFromRoom();

    //! \brief Server side. Hands the attendant to a room (a takeover or a split of the room moves the chair).
    //! \param room The new room.
    //! \param chairTile The tile of the chair, which the room covers now.
    void setRoom(RoomSpa* room, Tile* chairTile);

    //! \brief Returns the tile of the chair the attendant belongs to (server side).
    inline Tile* getChairTile() const
    { return mChairTile; }

    //! \brief Server side. The pool tile the attendant has reserved for his jump.
    //! \param x Set to the x of the tile.
    //! \param y Set to the y of the tile.
    //! \return False when he holds no tile.
    bool getPlace(int32_t& x, int32_t& y) const;

    //! \brief True while the attendant is in the air, on the server and on a client.
    inline bool isJumping() const
    { return mJumpTurnsLeft > 0; }

    //! \brief Server side. Fills the record that the room stream saves.
    //! \param save Set to the state of the attendant.
    void exportSaveData(PoolAttendantSave& save) const;

    //! \brief Server side. Puts a freshly spawned attendant back to the state of a saved room; the attendant goes on
    //! where he was (the acts and the jump at the turn they were saved at).
    //! \param save The saved state.
    void restoreFromSave(const PoolAttendantSave& save);

    //! \brief Client side. Starts the arc that the server told: the clip Jump and the interpolated position.
    //! \param from The start of the jump.
    //! \param to The landing point of the jump.
    //! \param turns The length of the jump in turns.
    //! \param elapsed The turns of the jump that have passed already.
    void startJumpFromServer(const Ogre::Vector3& from, const Ogre::Vector3& to, uint32_t turns, Ogre::Real elapsed);

    //! \brief Creates the figure on a client from the packet of the server.
    static PoolAttendantEntity* getPoolAttendantEntityFromPacket(GameMap* gameMap, ODPacket& is);

private:
    //! \brief Server side. Counts down while the attendant sits; starts a jump or an act when one is due.
    void upkeepSitting();

    //! \brief Server side. Counts down a short act and sits the attendant down again when it is over.
    void upkeepAct();

    //! \brief Server side. Moves the attendant along the ladder while he climbs down or up.
    void upkeepClimb();

    //! \brief Server side. Starts the jump when the attendant has reached the springboard.
    void upkeepWalkToBoard();

    //! \brief Server side. Moves the attendant along the arc and lands him when the jump is over.
    void upkeepJump();

    //! \brief Server side. Starts the climb up when the attendant is back at the foot of the ladder.
    void upkeepWalkBack();

    //! \brief Server side. Starts a random act (the whistle only while somebody bathes).
    void startAct();

    //! \brief Server side. Starts the jump from the springboard when the spa has a springboard and a free place.
    //! \return False when it cannot start now.
    bool startCannonball();

    //! \brief Server side. Lets the attendant walk to the springboard.
    void startWalkToBoard();

    //! \brief Server side. Starts the arc from the springboard to the reserved pool tile.
    void startJump();

    //! \brief Server side. The attendant has landed: the splash, then the way back.
    void land();

    //! \brief Server side. Lets the attendant walk back to the foot of the ladder.
    void startWalkBack();

    //! \brief Server side. Starts a climb.
    //! \param down True to climb down, false to climb up.
    void startClimb(bool down);

    //! \brief Server side. Sits the attendant down on the chair and counts the next act and jump.
    void sitDown();

    //! \brief Server side. Sets the position of the attendant on the ladder.
    //! \param progress How far the climb is, 0 (start) to 1 (end).
    void placeOnLadder(double progress);

    //! \brief Server side. Sets the position and tells the clients that see the attendant.
    //! \param position The new position.
    void moveTo(const Ogre::Vector3& position);

    //! \brief Server side. Tells the clients that see the attendant about the jump that has just started
    //! (ServerNotificationType::creatureJump with name, from, to, turns and elapsed). The notification type is added
    //! by the interface package; until then this does nothing.
    void sendJumpNotification();

    //! \brief The position on the arc of a jump.
    //! \param from The start of the jump.
    //! \param to The landing point.
    //! \param progress How far the jump is, 0 (start) to 1 (landing).
    static Ogre::Vector3 jumpPosition(const Ogre::Vector3& from, const Ogre::Vector3& to, Ogre::Real progress);

    //! \brief The position where the attendant sits on the chair.
    Ogre::Vector3 getSeatPosition() const;

    //! \brief The position at the foot of the ladder, in front of the chair on the side of the pool.
    Ogre::Vector3 getLadderFootPosition() const;

    //! \brief Gives the turns until the next act (a random time between the configured limits).
    double rollActTurns() const;

    //! \brief Gives the turns until the next jump (a random time between the configured limits).
    double rollCannonballTurns() const;

    //! \brief Stops a jump or a walk that cannot go on (no room, no springboard, the pool changed) and sits the
    //! attendant down again.
    void abortToChair();

    //! \brief The spa the attendant belongs to (server side), not owned.
    RoomSpa* mRoom;
    //! \brief The tile of the chair (server side), not owned.
    Tile* mChairTile;
    //! \brief What the attendant is doing (server side).
    PoolAttendantState mState;
    //! \brief Turns the act or the climb still lasts (server side).
    double mTurnsLeft;
    //! \brief Turns until the next act while the attendant sits (server side).
    double mActTurnsLeft;
    //! \brief Turns until the next jump from the springboard (server side).
    double mCannonballTurnsLeft;
    //! \brief True while the attendant holds a pool tile for his jump (server side).
    bool mHasPlace;
    //! \brief The x of the pool tile he holds.
    int32_t mPlaceX;
    //! \brief The y of the pool tile he holds.
    int32_t mPlaceY;
    //! \brief Start of the running jump (not saved).
    Ogre::Vector3 mJumpFrom;
    //! \brief Landing point of the running jump (not saved).
    Ogre::Vector3 mJumpTo;
    //! \brief Length of the running jump in turns (not saved).
    uint32_t mJumpTurns;
    //! \brief Turns of the running jump that are left, 0 = no jump (not saved).
    uint32_t mJumpTurnsLeft;
    //! \brief Turns of the running jump that have passed, fractions on a client (not saved).
    Ogre::Real mJumpElapsed;
};

#endif // POOLATTENDANTENTITY_H
