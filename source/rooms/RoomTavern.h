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

#ifndef ROOMTAVERN_H
#define ROOMTAVERN_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <vector>

class Creature;
class InnkeeperEntity;
class Tile;
enum class TileVisual;

//! \brief Who pays for the beer a tavern serves. The keeper sets it per tavern.
enum class TavernPayer
{
    //! The beer is paid from the treasuries of the keeper.
    keeper = 0,
    //! The beer is paid from the purse of the creature that drinks it.
    creature = 1
};

//! \brief What a guest of a tavern is doing on its place.
enum class TavernGuestState
{
    //! The guest has a place and walks to it.
    arriving = 0,
    //! The guest drinks (DrinkTurns turns for every drink).
    drinking = 1,
    //! The visit is over; the guest leaves, unless a second guest picks it for a game in the next turn.
    done = 2,
    //! The guest takes part in a game (see RoomTavernGame).
    game = 3,
    //! The guest lost a slap duel and lies on the floor (DuelKoTurns turns).
    ko = 4,
    //! The guest of a slap duel gets up again.
    getUp = 5
};

//! \brief The games two guests of a tavern play. They never cost gold.
enum class TavernGameKind
{
    //! The two guests arm-wrestle; the weaker one has a good chance to win.
    armWrestling = 0,
    //! The two guests throw dice; the weaker one has a good chance to win.
    dice = 1,
    //! The two guests slap each other in turns until one goes down (only when Beer is researched).
    slapDuel = 2
};

//! \brief The place of one guest in a tavern: the tile it stands on, what it is doing and how far it is.
struct RoomTavernSpot
{
    //! \brief Creates a place for the given guest.
    //! \param creature The guest, not owned.
    RoomTavernSpot(Creature* creature) :
        mCreature(creature),
        mState(TavernGuestState::arriving),
        mTurnsLeft(0),
        mDrinks(0),
        mSleepAfter(false),
        mWantsGame(false)
    {}

    //! The guest that uses the place, not owned.
    Creature* mCreature;
    //! What the guest is doing.
    TavernGuestState mState;
    //! Turns left of the state (drinking, done, ko, getUp).
    int32_t mTurnsLeft;
    //! Number of drinks the guest took in this visit.
    uint32_t mDrinks;
    //! True when the guest goes to its bed after the visit (the loser of a slap duel).
    bool mSleepAfter;
    //! True while the guest, done with its drinks, waits for a neighbour to play a game with.
    bool mWantsGame;
};

//! \brief A game two guests of a tavern play. It is kept under the tile of the first guest.
struct RoomTavernGame
{
    //! \brief Creates an empty game.
    RoomTavernGame() :
        mKind(TavernGameKind::armWrestling),
        mTileA(nullptr),
        mTileB(nullptr),
        mCreatureA(nullptr),
        mCreatureB(nullptr),
        mTurnsLeft(0),
        mSlapsTakenA(0),
        mSlapsTakenB(0),
        mTurnIsA(true)
    {}

    //! The game that is played.
    TavernGameKind mKind;
    //! The tile of the first guest (the key of the game in the room).
    Tile* mTileA;
    //! The tile of the second guest, a neighbour of mTileA.
    Tile* mTileB;
    //! The first guest, not owned.
    Creature* mCreatureA;
    //! The second guest, not owned.
    Creature* mCreatureB;
    //! Turns until the game is decided (a slap duel: until the one with more hit points left wins).
    int32_t mTurnsLeft;
    //! Number of hits the first guest took in a slap duel.
    uint32_t mSlapsTakenA;
    //! Number of hits the second guest took in a slap duel.
    uint32_t mSlapsTakenB;
    //! True when the first guest slaps in the next turn of a slap duel.
    bool mTurnIsA;
};

//! \brief A guest place that was read from a saved room and waits for its creature (see RoomTavern::doUpkeep).
struct RoomTavernPendingSpot
{
    //! \brief Creates an empty saved place.
    RoomTavernPendingSpot() :
        mTile(nullptr),
        mState(TavernGuestState::arriving),
        mTurnsLeft(0),
        mDrinks(0),
        mSleepAfter(false),
        mWantsGame(false)
    {}

    //! The tile of the place.
    Tile* mTile;
    //! What the guest was doing.
    TavernGuestState mState;
    //! Turns that were left of the state.
    int32_t mTurnsLeft;
    //! Number of drinks the guest had taken.
    uint32_t mDrinks;
    //! True when the guest was on its way to bed after the visit.
    bool mSleepAfter;
    //! True when the guest was waiting for a game.
    bool mWantsGame;
};

//! \brief A keg or table that was read from a saved room and is placed again unchanged (see RoomTavern::updateActiveSpots).
struct RoomTavernSavedFurniture
{
    //! \brief Creates an empty saved piece of furniture.
    RoomTavernSavedFurniture() :
        mTile(nullptr),
        mAngle(0.0)
    {}

    //! The tile the object stood on.
    Tile* mTile;
    //! The mesh name of the object.
    std::string mMesh;
    //! The rotation angle of the object in degrees.
    double mAngle;
};

//! \brief A running game that was read from a saved room and waits for its two guests (see RoomTavern::doUpkeep).
struct RoomTavernPendingGame
{
    //! \brief Creates an empty saved game.
    RoomTavernPendingGame() :
        mKind(TavernGameKind::armWrestling),
        mTileA(nullptr),
        mTileB(nullptr),
        mTurnsLeft(0),
        mSlapsTakenA(0),
        mSlapsTakenB(0),
        mTurnIsA(true)
    {}

    //! The game that was played.
    TavernGameKind mKind;
    //! The tile of the first guest.
    Tile* mTileA;
    //! The tile of the second guest.
    Tile* mTileB;
    //! The name of the first guest.
    std::string mNameA;
    //! The name of the second guest.
    std::string mNameB;
    //! Turns that were left.
    int32_t mTurnsLeft;
    //! Hits the first guest had taken.
    uint32_t mSlapsTakenA;
    //! Hits the second guest had taken.
    uint32_t mSlapsTakenB;
    //! True when the first guest was to slap next.
    bool mTurnIsA;
};

//! \brief A room where creatures quench their thirst. The first tile of the room is the counter, where the innkeeper
//! stands; every other tile is a place to drink (one creature per tile), decorated with a keg when it lies next to a
//! wall and with a table otherwise. A guest drinks water or beer (paid by the keeper or by the guest), may take more
//! drinks and may play a game with a guest next to it: arm wrestling, dice or, with Beer, a slap duel. The room keeps
//! the counter, the decoration, the innkeeper, who pays for the beer, the places of the guests and the games, and
//! saves them all.
class RoomTavern: public Room
{
public:
    //! \brief Creates an empty tavern on the given map. The beer is paid by the keeper until it is set otherwise.
    RoomTavern(GameMap* gameMap);

    //! \brief Returns the type of this room (RoomType::tavern).
    RoomType getType() const override
    { return mRoomType; }

    //! \brief True when at least one place to drink is free: a tile of the room that is not the counter tile and has
    //! no guest. A creature the saved room still waits for always has its place.
    bool hasOpenCreatureSpot(Creature* c) override;

    //! \brief Gives the creature the free place nearest to it, or the place it had when the room was saved.
    //! \param creature The guest.
    //! \return False when the creature cannot use the room.
    bool addCreatureUsingRoom(Creature* creature) override;

    //! \brief Frees the place of the creature. A game it played ends without effects.
    //! \param creature The guest that leaves the room.
    void removeCreatureUsingRoom(Creature* creature) override;

    //! \brief Called while a creature uses the room: walks the guest to its place and lets it leave when its visit
    //! is over. The drinks and the games run in doUpkeep.
    //! \param creature The guest.
    //! \param forced Not used.
    //! \return True when the guest left the room and may go on in the same turn.
    bool useRoom(Creature& creature, bool forced) override;

    //! \brief Server side. Runs the guests of the room for one turn: binds the guests of a loaded room again, ends the
    //! games that were disturbed, plays the games, serves the drinks and counts the states down.
    void doUpkeep() override;

    //! \brief A guest in a game, lying on the floor or getting up does not stop because it is hungry or tired.
    bool shouldStopUseIfHungrySleepy(Creature& creature, bool forced) override;

    //! \brief Returns whether this guest is arriving for a drink or drinking.
    bool isGuestDrinking(const Creature& creature);

    //! \brief A guest in a game, lying on the floor or getting up does not stop because of its mood.
    bool shouldNotUseIfBadMood(Creature& creature, bool forced) override;

    //! \brief Sets the name, seat and tiles. The first tile is the counter tile. A tavern of a seat that is played by
    //! the computer lets the creatures pay for the beer.
    void setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles) override;

    //! \brief Joins an adjacent tavern of the same seat into this room. The room that already has its counter keeps it
    //! (and its payer setting); the innkeeper of the other room goes away.
    void absorbRoom(Room* r) override;

    //! \brief Called on the room the tiles are leaving. The new room gets the payer setting and, when the counter tile
    //! goes over with the tiles, keeps the counter where it was.
    void splitRoom(Room& newRoom, const std::vector<Tile*>& tiles) override;

    //! \brief Removes a tile from the room. A creature drinking on the tile stops (its action queue is cleared); when
    //! the tile was the counter tile, the first remaining tile becomes the counter.
    bool removeCoveredTile(Tile* t) override;

    //! \brief Takes the room off the map together with the innkeeper.
    void removeFromGameMap(GameMap* gameMap = nullptr) override;

    //! \brief Makes sure the counter tile, the decoration of every tile and the innkeeper are right for the tiles the
    //! room covers now: the object of a tile whose kind changed is replaced, the objects of tiles the room lost are
    //! removed and the innkeeper stands on the counter tile (it is spawned again when the counter moved).
    void updateActiveSpots(GameMap* gameMap = nullptr) override;

    //! \brief Writes the room, then the lines TavernPayer, Innkeeper and Counter, one line Spot for every guest and
    //! one line Game for every running game.
    void exportToStream(std::ostream& os) const override;

    //! \brief Reads the room and the lines written by exportToStream. A save without these lines loads with the beer
    //! paid by the keeper, the counter on the first tile and no guest. The guests and games read are bound to their
    //! creatures again in the first turn (doUpkeep).
    bool importFromStream(std::istream& is) override;

    //! \brief Returns who pays for the beer.
    inline TavernPayer getPayer() const
    { return mPayer; }

    //! \brief Sets who pays for the beer.
    inline void setPayer(TavernPayer payer)
    { mPayer = payer; }

    //! \brief Returns the counter tile, nullptr while the room has no tile.
    inline Tile* getCounterTile() const
    { return mCounterTile; }

    //! \brief Returns the innkeeper (server side), nullptr while it is not on the map.
    inline InnkeeperEntity* getInnkeeper() const
    { return mInnkeeper; }

    //! \brief True when the tile is the counter tile of this room.
    //! \param tile The tile to test.
    inline bool isCounterTile(const Tile* tile) const
    { return (tile != nullptr) && (tile == mCounterTile); }

    //! \brief True when this tavern serves beer: the seat that owns it has researched Beer. Without it only water is
    //! served.
    bool servesBeer() const;

    //! \brief Server side. A drink was served on the tile: the tile gets TavernDirtPerDrink of rooms.cfg (the same for
    //! every creature, no DirtFactor), so the tavern is cleaned by the workers like the other rooms.
    //! \param tile The tile the creature drinks on; nothing happens if it is null.
    static void addDrinkDirt(Tile* tile);

    //! \brief Server side. Tells the keepers that see the creature what happened to it, so their clients show the
    //! thought bubble and the dungeon book post (cosmetic event tavernEvent). Nothing is sent for a creature that is not
    //! on a tile, and the game never depends on it.
    //! \param creature The creature the event is about.
    //! \param kind What happened (CosmeticTavernKind as a number, kept as int32_t so that this header needs no network header).
    //! \param opponent The other creature of a slap duel, null for the other kinds.
    static void sendTavernEvent(Creature& creature, int32_t kind, const Creature* opponent);

    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

private:
    //! \brief Number of places to drink: the covered tiles without the counter tile.
    uint32_t getNbDrinkingTiles() const;

    //! \brief Finds the place of a guest.
    //! \param creature The guest.
    //! \return The place in mSpots, mSpots.end() if the creature has none.
    std::map<Tile*, RoomTavernSpot>::iterator findSpotOf(const Creature* creature);

    //! \brief True when the tile can hold a guest: it is part of the room, is not the counter tile and has no guest.
    //! \param tile The tile to test.
    bool isFreeSpotTile(Tile* tile) const;

    //! \brief Picks the free place nearest to the creature; a place next to a guest comes before any other.
    //! \param creature The guest.
    //! \return The tile, nullptr if every place is taken.
    Tile* pickFreeSpotTile(const Creature& creature) const;

    //! \brief Shows what the guest does in its state: the clip of the state, turned towards what it looks at.
    //! \param tile The tile of the place.
    //! \param spot The place of the guest.
    void showSpotState(Tile* tile, RoomTavernSpot& spot);

    //! \brief Puts the guest in the state done: it stands idle and leaves at its next action turn once the turns
    //! are over.
    //! \param spot The place of the guest.
    //! \param turns Turns the state lasts (a guest that is looked for as a partner of a game needs more than 0).
    void setSpotDone(RoomTavernSpot& spot, int32_t turns);

    //! \brief Sets the state of a guest without changing what it shows.
    //! \param spot The place of the guest.
    //! \param state The new state.
    //! \param turns Turns the state lasts.
    void setSpotState(RoomTavernSpot& spot, TavernGuestState state, int32_t turns);

    //! \brief Runs the places for one turn: counts the drinks, the lying and the getting up down.
    void upkeepSpots();

    //! \brief Runs the games for one turn.
    void upkeepGames();

    //! \brief Ends the games and the lying of guests that were disturbed (fight, flight, knocked out, dragged away).
    void abortDisturbedGuests();

    //! \brief Server side. Ends the places whose tile the room has lost; their guests stop.
    void releaseGuestsOnLostTiles();

    //! \brief Binds the guests and games read from a saved room to their creatures again.
    void resumeLoadedGuests();

    //! \brief A guest finished a drink: serves it (water or beer, paid), books the dirt, lets the guest decide about
    //! another drink, a game or leaving.
    //! \param tile The tile of the guest.
    //! \param spot The place of the guest.
    void finishDrink(Tile* tile, RoomTavernSpot& spot);

    //! \brief Takes the price of a beer from the keeper or the guest.
    //! \param creature The guest.
    //! \param noCoin Set to true when the guest had to pay and had not enough gold.
    //! \return True when the beer is paid.
    bool payForBeer(Creature& creature, bool& noCoin);

    //! \brief Lets the guest that wants a game start it with a neighbour that is done too. The guest asks again every
    //! turn while it waits (up to DrinkTurns turns after its last drink).
    //! \param tile The tile of the guest.
    void tryStartGame(Tile* tile);

    //! \brief Starts a game of two guests on neighbouring places.
    //! \param tileA The tile of the guest that starts the game.
    //! \param tileB The tile of the neighbour.
    void startGame(Tile* tileA, Tile* tileB);

    //! \brief Plays one turn of an arm wrestling or dice game.
    //! \param it The game.
    void playContestTurn(std::map<Tile*, RoomTavernGame>::iterator it);

    //! \brief Plays one turn of a slap duel: the guest whose turn it is slaps.
    //! \param it The game.
    void playDuelTurn(std::map<Tile*, RoomTavernGame>::iterator it);

    //! \brief Ends a game with a winner: mood and experience, spectators, the innkeeper cheers; the loser of a slap
    //! duel is knocked out.
    //! \param it The game; it is erased.
    //! \param winner The winner of the game.
    //! \param underdogLevels Levels the winner was below the loser (0 if it was not the weaker one); the weaker one
    //! wins more mood and double experience.
    void concludeGame(std::map<Tile*, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels);

    //! \brief Ends a game without winner and without effects; both guests are done.
    //! \param it The game; it is erased.
    void abortGame(std::map<Tile*, RoomTavernGame>::iterator it);

    //! \brief The loser of a slap duel goes down: it lies DuelKoTurns turns, gets up and goes to bed.
    //! \param spot The place of the loser.
    void knockOut(RoomTavernSpot& spot);

    //! \brief Gives the creatures of the seat near a game the spectator mood.
    //! \param game The game.
    void cheerSpectators(const RoomTavernGame& game);

    //! \brief Plays a sound on a tile for the keepers that see it.
    //! \param tile The tile of the sound; nothing happens if it is null.
    //! \param family The sound family.
    static void playSoundAt(Tile* tile, const std::string& family);

    //! \brief True while the creature cannot play a game or lie on the floor: it fights, flees, is knocked out or is
    //! dragged to its bed.
    //! \param creature The guest.
    static bool isGuestDisturbed(const Creature& creature);

    //! \brief True when the counter object already stands on the counter tile, which tells an older room that has
    //! been through updateActiveSpots from a room that was only just set up.
    bool hasPlacedCounter() const;

    //! \brief The angle (degrees) of an object on the tile that has its back to the wall, and whether the tile lies
    //! next to a wall at all (a neighbour in the four directions that is not part of this room).
    //! \param tile The tile of the object.
    //! \param isNextToWall Set to true when the tile lies next to a wall.
    //! \return The angle; 0 for a tile that lies next to no wall.
    double getBackToWallAngle(const Tile* tile, bool& isNextToWall) const;

    //! \brief Server side. Removes the innkeeper from the map; does nothing without one.
    void removeInnkeeper();

    //! \brief Server side. Makes sure there is an innkeeper on the counter tile, turned like the counter.
    void placeInnkeeper();

    //! \brief Who pays for the beer.
    TavernPayer mPayer;
    //! \brief The tile with the counter and the innkeeper, nullptr while the room has no tile. Not owned.
    Tile* mCounterTile;
    //! \brief The figure behind the counter (server side only), nullptr while it is not on the map. Not owned: the
    //! entity is removed by removeInnkeeper.
    InnkeeperEntity* mInnkeeper;
    //! \brief The places of the guests, by tile (server side only). A tile without entry has no guest.
    std::map<Tile*, RoomTavernSpot> mSpots;
    //! \brief The running games, by the tile of the first guest (server side only).
    std::map<Tile*, RoomTavernGame> mGames;
    //! \brief The places read from a saved room, by creature name, until the creatures are bound again.
    std::map<std::string, RoomTavernPendingSpot> mPendingSpots;
    //! \brief The games read from a saved room until the creatures are bound again.
    std::vector<RoomTavernPendingGame> mPendingGames;
    //! \brief The kegs and tables read from a saved room until updateActiveSpots has placed them again.
    std::vector<RoomTavernSavedFurniture> mSavedFurniture;
};

#endif // ROOMTAVERN_H
