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

#ifndef ROOMSPA_H
#define ROOMSPA_H

#include "entities/PoolAttendantState.h"
#include "rooms/Room.h"
#include "rooms/RoomSpaLayout.h"
#include "rooms/RoomType.h"

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <vector>

class BuildingObject;
class Creature;
class PoolAttendantEntity;
class Tile;
enum class TileVisual;

//! \brief Who pays for the bath a lava spa gives. The keeper sets it per spa.
enum class SpaPayer
{
    //! The bath is paid from the treasuries of the keeper.
    keeper = 0,
    //! The bath is paid from the purse of the creature that bathes.
    creature = 1
};

//! \brief What a bather of a lava spa is doing.
enum class SpaBatherState
{
    //! The bather has a bath place reserved and walks there (to the springboard first when it jumps).
    reserved = 0,
    //! The bather is in the air after a jump from the springboard.
    jumping = 1,
    //! The bather sits in the mud and its spa mood rises.
    bathing = 2
};

//! \brief The bath place of one bather in a lava spa: the block of pool tiles it has reserved, what it is doing and how
//! far the bath is.
struct RoomSpaBather
{
    //! \brief Creates a bather place for the given creature.
    //! \param creature The bather, not owned.
    RoomSpaBather(Creature* creature) :
        mCreature(creature),
        mBlock(),
        mState(SpaBatherState::reserved),
        mTurnsDone(0.0),
        mJump(false),
        mDone(false)
    {}

    //! The bather that uses the place, not owned.
    Creature* mCreature;
    //! The block of pool tiles of the place.
    SpaBlock mBlock;
    //! What the bather is doing.
    SpaBatherState mState;
    //! Turns of the bath that are counted already (fractions are kept).
    double mTurnsDone;
    //! True when the bather jumps from the springboard before the bath starts.
    bool mJump;
    //! True when the bath is over (relaxation given); the bather leaves at its next action turn. Not saved.
    bool mDone;
};

//! \brief A bath place that was read from a saved room and waits for its creature (see RoomSpa::doUpkeep).
struct RoomSpaPendingBather
{
    //! \brief Creates an empty saved bather place.
    RoomSpaPendingBather() :
        mBlock(),
        mState(SpaBatherState::reserved),
        mTurnsDone(0.0),
        mJump(false)
    {}

    //! The block of pool tiles of the place.
    SpaBlock mBlock;
    //! What the bather was doing.
    SpaBatherState mState;
    //! Turns of the bath that were counted.
    double mTurnsDone;
    //! True when the bather was to jump before the bath.
    bool mJump;
};

//! \brief The pool attendant read from a saved room; it is spawned again in the first update of the room.
struct RoomSpaPendingAttendant
{
    //! \brief Creates an empty record: the saved room had no attendant line.
    RoomSpaPendingAttendant() :
        mPresent(false),
        mSave()
    {}

    //! True when the room stream had a PoolAttendant line.
    bool mPresent;
    //! The saved state of the attendant.
    PoolAttendantSave mSave;
};

//! \brief A piece of the pool rim: a stone edge on a pool tile, turned to the side where the pool ends. Several can
//! stand on the same tile, so they are kept here and not in the one-object-per-tile map of the building.
struct RoomSpaRim
{
    //! \brief Creates a rim piece.
    //! \param tile The pool tile the piece stands on.
    //! \param angle The angle (degrees) that turns the piece to the side where the pool ends.
    //! \param object The mesh of the piece, owned by the game map.
    RoomSpaRim(Tile* tile, double angle, BuildingObject* object) :
        mTile(tile),
        mAngle(angle),
        mObject(object)
    {}

    //! The pool tile the piece stands on.
    Tile* mTile;
    //! The angle of the piece in degrees.
    double mAngle;
    //! The mesh of the piece.
    BuildingObject* mObject;
};

//! \brief The lava spa: one big hot mud bath that grows with the room, heated by lava below. The covered tiles whose
//! eight neighbours belong to the room are the pool, the others the rim. A creature in a bad mood or with a hangover
//! takes a bath, paid by the keeper or by the creature: its spa mood rises, a hangover ends and the creature is
//! relaxed afterwards (see Creature::getRelaxWorkFactor). The room keeps the pool pieces, the pool attendant's chair
//! and the springboard, the bath places with their bathers, who pays, and saves them all.
class RoomSpa: public Room
{
public:
    //! \brief Creates an empty lava spa on the given map. The bath is paid by the keeper until it is set otherwise.
    RoomSpa(GameMap* gameMap);

    //! \brief Returns the type of this room (RoomType::spa).
    RoomType getType() const override
    { return mRoomType; }

    //! \brief True when the creature can take a bath now (see canAccept), or when the saved room still waits for it.
    bool hasOpenCreatureSpot(Creature* c) override;

    //! \brief True when the creature can take a bath here now: it belongs to the seat of the room, is no worker, a free
    //! bath place of its bed size exists and the payer can pay the price of a bath.
    //! \param creature The creature that wants to bathe.
    bool canAccept(const Creature& creature) const;

    //! \brief Reserves the bath place of the creature (the place it had when the room was saved, or the first free
    //! one of its bed size).
    //! \param creature The bather.
    //! \return False when the creature cannot use the room.
    bool addCreatureUsingRoom(Creature* creature) override;

    //! \brief Frees the bath place of the creature, whatever the creature was doing; a bath that is broken off keeps
    //! the mood already gained and gives no relaxation and no refund.
    //! \param creature The bather that leaves the room.
    void removeCreatureUsingRoom(Creature* creature) override;

    //! \brief Called while a creature uses the room: walks the bather to its place (or to the springboard), pays and
    //! starts the bath, and lets it leave when the bath is over. The jump and the bath run in doUpkeep.
    //! \param creature The bather.
    //! \param forced Not used.
    //! \return True when the bather left the room and may go on in the same turn.
    bool useRoom(Creature& creature, bool forced) override;

    //! \brief Server side. Runs the bathers for one turn: binds the bathers of a loaded room again, ends the baths
    //! that were disturbed, moves the jumpers, lifts the spa mood of the bathers and ends the baths that are over.
    void doUpkeep() override;

    //! \brief A bather in the air or in the mud does not stop because it is hungry or tired.
    bool shouldStopUseIfHungrySleepy(Creature& creature, bool forced) override;

    //! \brief A bather goes into the mud because of its bad mood, so the mood never stops the use of the room.
    bool shouldNotUseIfBadMood(Creature& creature, bool forced) override;

    //! \brief Sets the name, seat and tiles. A spa of a seat that is played by the computer lets the creatures pay.
    void setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles) override;

    //! \brief Joins an adjacent spa of the same seat into this room. The room that already has its pool objects keeps
    //! its payer setting.
    void absorbRoom(Room* r) override;

    //! \brief Called on the room the tiles are leaving. The new room gets the payer setting.
    void splitRoom(Room& newRoom, const std::vector<Tile*>& tiles) override;

    //! \brief Removes a tile from the room. A bather on the tile or with a place on it stops (its action queue is
    //! cleared).
    bool removeCoveredTile(Tile* t) override;

    //! \brief Takes the room off the map together with the rim pieces.
    void removeFromGameMap(GameMap* gameMap = nullptr) override;

    //! \brief Makes sure the pool objects, the rim pieces, the chair and the springboard are right for the tiles the
    //! room covers now. Bath places with a bather or a reservation are never moved.
    void updateActiveSpots(GameMap* gameMap = nullptr) override;

    //! \brief Writes the room, then the lines SpaPayer and, when there are bathers, SpaBathers with one line for every
    //! bather.
    void exportToStream(std::ostream& os) const override;

    //! \brief Reads the room and the lines written by exportToStream. A save without these lines loads with the bath
    //! paid by the keeper (the computer for a seat that the computer plays) and no bather. The bathers read are bound
    //! to their creatures again in the first turn (doUpkeep).
    bool importFromStream(std::istream& is) override;

    //! \brief Returns who pays for the bath.
    inline SpaPayer getPayer() const
    { return mPayer; }

    //! \brief Sets who pays for the bath.
    inline void setPayer(SpaPayer payer)
    { mPayer = payer; }

    //! \brief True when the tile is a pool tile of a lava spa: it is covered by a spa and so are its eight neighbours.
    //! \param tile The tile to test; null is no pool tile.
    static bool isPoolTile(const Tile* tile);

    //! \brief Server side. The bath of a creature is over (relaxation, no hangover, mud). Tells the interface package
    //! to write the post of the creature; until that package is there this does nothing.
    //! \param creature The creature that has bathed.
    static void sendBathFinished(Creature& creature);

    //! \brief The tile of the pool attendant's chair, nullptr when the room has no pool or does not cover that tile.
    Tile* getChairTile() const;

    //! \brief The tile of the springboard, nullptr when the room has no pool or does not cover that tile.
    Tile* getSpringboardTile() const;

    //! \brief True while somebody is in the air or in the mud of the pool (the attendant whistles only then).
    bool hasBatherInPool() const;

    //! \brief Finds a free pool tile for a jump of the pool attendant: the first pool tile in the order of smaller
    //! y, then smaller x that no bather has or has reserved.
    //! \param x Set to the x of the tile.
    //! \param y Set to the y of the tile.
    //! \return False when no pool tile is free.
    bool findAttendantPlace(int32_t& x, int32_t& y) const;

    //! \brief True when the position is a pool tile of this room.
    //! \param x The x of the tile.
    //! \param y The y of the tile.
    bool isPoolPosition(int32_t x, int32_t y) const;

    //! \brief Shows the splash of a landing on a pool tile (mud splash effect and sound) for the keepers that see it.
    //! \param x The x of the pool tile.
    //! \param y The y of the pool tile.
    void playSplashAt(int32_t x, int32_t y);

    //! \brief Returns the pool attendant (server side), nullptr while there is none.
    inline PoolAttendantEntity* getAttendant() const
    { return mAttendant; }

    //! \brief Plays a sound on a tile for the keepers that see it.
    //! \param tile The tile of the sound; nothing happens if it is null.
    //! \param family The sound family.
    static void playSoundAt(Tile* tile, const std::string& family);

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

private:
    //! \brief The tiles the room covers as a set of positions.
    SpaTileSet getCoveredSet() const;

    //! \brief The pool tiles of the room as a set of positions.
    SpaTileSet getPoolSet() const;

    //! \brief The tiles of the places that bathers have or have reserved.
    SpaTileSet getTakenSet() const;

    //! \brief Finds the place of a bather.
    //! \param creature The bather.
    //! \return The place in mBathers, mBathers.end() if the creature has none.
    std::vector<RoomSpaBather>::iterator findBatherOf(const Creature* creature);

    //! \brief True when the price of a bath can be paid now: the treasuries hold it (keeper pays) or the creature
    //! carries it (creature pays).
    //! \param creature The creature that wants to bathe.
    bool canPay(const Creature& creature) const;

    //! \brief Takes the price of a bath (BeerPrice) from the keeper or the creature.
    //! \param creature The bather.
    //! \return True when the bath is paid.
    bool payForBath(Creature& creature);

    //! \brief The point in the middle of the block of a bather.
    //! \param bather The place.
    static Ogre::Vector3 getBlockCentre(const RoomSpaBather& bather);

    //! \brief The covered tile at the position, nullptr when the room does not cover it.
    //! \param position The tile position.
    Tile* getCoveredTileAt(const std::pair<int32_t, int32_t>& position) const;

    //! \brief True when the creature stands on one of the tiles of the block.
    //! \param creature The bather.
    //! \param block The block of its place.
    static bool isInBlock(const Creature& creature, const SpaBlock& block);

    //! \brief True while the bather cannot bathe: it fights, flees, is knocked out, dragged away or not on the map.
    //! \param creature The bather.
    static bool isBatherDisturbed(const Creature& creature);

    //! \brief Walks a bather with a reserved place to the springboard or to the middle of its block; when it is there,
    //! pays and starts the jump or the bath.
    //! \param creature The bather.
    //! \param bather Its place.
    //! \return True when the bather's action ended.
    bool walkToPlace(Creature& creature, RoomSpaBather& bather);

    //! \brief Starts the bath of a bather that stands in the middle of its block.
    //! \param bather The place of the bather.
    void startBath(RoomSpaBather& bather);

    //! \brief The jump of a bather is over: the splash, then the bath starts.
    //! \param bather The place of the bather.
    void landJump(RoomSpaBather& bather);

    //! \brief The bath of a bather is over: relaxation by research level, no hangover, the mud for the next tiles and
    //! the post. The bather leaves at its next action turn.
    //! \param bather The place of the bather.
    void finishBath(RoomSpaBather& bather);

    //! \brief Runs the places for one turn: moves the jumpers and lifts the spa mood of the bathers.
    void upkeepBathers();

    //! \brief Ends the baths of bathers that were disturbed (fight, flight, knocked out, dragged away).
    void abortDisturbedBathers();

    //! \brief Server side. Ends the places whose tiles the room has lost; their bathers stop.
    void releaseBathersOnLostTiles();

    //! \brief Binds the bathers read from a saved room to their creatures again.
    void resumeLoadedBathers();

    //! \brief Server side. Creates a pool piece on a tile and adds the steam to it.
    //! \param tile The tile of the piece.
    //! \param gameMap The map.
    void addPoolObject(Tile* tile, GameMap* gameMap);

    //! \brief Server side. Renews the steam of the pool pieces whose effect has run out.
    void upkeepSteam();

    //! \brief Server side. Removes all the rim pieces.
    void removeRimObjects();

    //! \brief Server side. Takes the pool attendant off the map; does nothing without one.
    void removeAttendant();

    //! \brief Server side. Makes sure there is a pool attendant on the chair: spawns one (the saved one of a loaded
    //! room) or spawns it again when the chair moved; a room without a chair has none.
    void placeAttendant();

    //! \brief Server side. Makes the rim pieces right: one on a pool tile for every side that borders a tile which is
    //! not part of the pool.
    //! \param pool The pool tiles.
    //! \param gameMap The map.
    void updateRimObjects(const SpaTileSet& pool, GameMap* gameMap);

    //! \brief Server side. Makes the furniture of one tile right: the wanted mesh stands on it, a different one is
    //! replaced and a mesh of "" is removed.
    //! \param tile The tile.
    //! \param meshName The wanted mesh, "" for none.
    //! \param angle The angle of the mesh in degrees.
    //! \param gameMap The map.
    void updateTileObject(Tile* tile, const std::string& meshName, double angle, GameMap* gameMap);

    //! \brief Who pays for the bath.
    SpaPayer mPayer;
    //! \brief The bath places, one for every bather and reservation (server side only).
    std::vector<RoomSpaBather> mBathers;
    //! \brief The places read from a saved room, by creature name, until the creatures are bound again.
    std::map<std::string, RoomSpaPendingBather> mPendingBathers;
    //! \brief The rim pieces of the pool (server side only).
    std::vector<RoomSpaRim> mRimObjects;
    //! \brief Turns until the steam of a pool piece has to be renewed, by pool tile (server side only, not saved).
    std::map<Tile*, uint32_t> mSteamTurnsLeft;
    //! \brief The pool attendant on the chair (server side only); the entity is not saved, the room saves it.
    PoolAttendantEntity* mAttendant;
    //! \brief The attendant read from a saved room until the first update spawns it.
    RoomSpaPendingAttendant mPendingAttendant;
};

#endif // ROOMSPA_H
