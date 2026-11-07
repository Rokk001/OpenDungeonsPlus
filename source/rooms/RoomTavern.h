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

#include <OgreVector2.h>

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

//! \brief Number of places of one bench of a tavern table: the table is two tiles long and four guests sit next to each
//! other on each of its two benches.
const uint32_t TAVERN_SEATS_PER_BENCH = 4;
//! \brief Number of places of a tavern table: two benches with four places each.
const uint32_t TAVERN_SEATS_PER_TABLE = 2 * TAVERN_SEATS_PER_BENCH;

//! \brief One seat of a tavern: the tile of the table (the tile its object belongs to) and the number of the place at
//! that table (0 to 3 on the first bench, 4 to 7 on the second). A large guest takes several neighbouring places of one
//! bench and is kept under the first of them.
struct RoomTavernSeat
{
    //! \brief Creates an empty seat without a table.
    RoomTavernSeat() :
        mTable(nullptr),
        mIndex(0)
    {}

    //! \brief Creates the given seat.
    //! \param table The tile of the table.
    //! \param index The number of the seat at the table.
    RoomTavernSeat(Tile* table, uint32_t index) :
        mTable(table),
        mIndex(index)
    {}

    //! \brief Orders seats by table and number, so that a seat can be the key of a map.
    //! \param other The seat to compare with.
    bool operator<(const RoomTavernSeat& other) const
    {
        if(mTable != other.mTable)
            return mTable < other.mTable;

        return mIndex < other.mIndex;
    }

    //! \brief True for the same seat of the same table.
    //! \param other The seat to compare with.
    bool operator==(const RoomTavernSeat& other) const
    { return (mTable == other.mTable) && (mIndex == other.mIndex); }

    //! The tile of the table, not owned.
    Tile* mTable;
    //! The number of the seat at the table.
    uint32_t mIndex;
};

//! \brief The place of one guest in a tavern: the seat it uses, what it is doing and how far it is.
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
        mWantsGame(false),
        mPlaces(1),
        mLeftSeat(false)
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
    //! True while the guest, done with its drinks, waits for a guest of its table to play a game with.
    bool mWantsGame;
    //! Number of neighbouring places the guest takes on its bench: 1, or more for a large guest.
    uint32_t mPlaces;
    //! True once the guest has stepped away from its bench at the end of the visit.
    bool mLeftSeat;
};

//! \brief A game two guests at the same table of a tavern play. It is kept under the seat of the first guest.
struct RoomTavernGame
{
    //! \brief Creates an empty game.
    RoomTavernGame() :
        mKind(TavernGameKind::armWrestling),
        mCreatureA(nullptr),
        mCreatureB(nullptr),
        mTurnsLeft(0),
        mSlapsTakenA(0),
        mSlapsTakenB(0),
        mTurnIsA(true)
    {}

    //! The game that is played.
    TavernGameKind mKind;
    //! The seat of the first guest (the key of the game in the room).
    RoomTavernSeat mSeatA;
    //! The seat of the second guest, at the same table as mSeatA.
    RoomTavernSeat mSeatB;
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
        mState(TavernGuestState::arriving),
        mTurnsLeft(0),
        mDrinks(0),
        mSleepAfter(false),
        mWantsGame(false)
    {}

    //! The seat of the place; without a table in a save made before tavern tables had seats.
    RoomTavernSeat mSeat;
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
        mTurnsLeft(0),
        mSlapsTakenA(0),
        mSlapsTakenB(0),
        mTurnIsA(true)
    {}

    //! The game that was played.
    TavernGameKind mKind;
    //! The seat of the first guest.
    RoomTavernSeat mSeatA;
    //! The seat of the second guest.
    RoomTavernSeat mSeatB;
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
//! stands; kegs stand at the walls and tables are spread over the room. Every table is two tiles long and has two
//! benches with four places each; a large creature takes the places its width needs, up to a whole bench, and a bench with
//! a wall behind it stays empty. A guest sits and drinks water or beer (paid by the keeper or by
//! the guest), may take more drinks and may play a game with a guest of its table: arm wrestling, dice or, with Beer, a
//! slap duel. The room keeps the counter, the furniture, the innkeeper, who pays for the beer, the seats of the guests
//! and the games, and saves them all.
class RoomTavern: public Room
{
public:
    //! \brief Creates an empty tavern on the given map. The beer is paid by the keeper until it is set otherwise.
    RoomTavern(GameMap* gameMap);

    //! \brief Returns the type of this room (RoomType::tavern).
    RoomType getType() const override
    { return mRoomType; }

    //! \brief True when the tavern contains a full three by three block and has a free seat for the creature (as
    //! many free neighbouring places of one bench as its width needs for a large one). A creature the saved room still waits for always has its place.
    bool hasOpenCreatureSpot(Creature* c) override;

    //! \brief Gives the creature a free seat, or the seat it had when the room was saved.
    //! \param creature The guest.
    //! \return False when the creature cannot use the room.
    bool addCreatureUsingRoom(Creature* creature) override;

    //! \brief Frees the place of the creature. A game it played ends without effects.
    //! \param creature The guest that leaves the room.
    void removeCreatureUsingRoom(Creature* creature) override;

    //! \brief Called while a creature uses the room: walks the guest to its seat and lets it step away and leave when
    //! its visit is over. The drinks and the games run in doUpkeep.
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

    //! \brief A guest that sits on its bench ends its visit before it is sent away: no further drink, a game ends without
    //! effects, a slumped duel loser first gets up; then useRoom steps it off the bench (decision 833).
    //! \param creature The guest.
    //! \return True while the guest still sits on its bench.
    bool keepGuestUntilItLeft(Creature& creature) override;

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

    //! \brief Makes sure the counter tile, the furniture and the innkeeper are right for the tiles the room covers now.
    //! Furniture is spread again when the tiles or the counter changed; then all guests stand up, running games end
    //! without a winner and each guest looks for a free seat again. A loaded room gets back its saved furniture.
    void updateActiveSpots(GameMap* gameMap = nullptr) override;

    //! \brief Writes the room, then the lines TavernPayer, Innkeeper, Counter and SeatLayout, one line Furniture for
    //! every keg and table, one line Spot for every guest and one line Game for every running game.
    void exportToStream(std::ostream& os) const override;

    //! \brief Reads the room and the lines written by exportToStream. A save without these lines loads with the beer
    //! paid by the keeper, the counter on the first tile and no guest. A save without the line SeatLayout was made before
    //! tables had seats: its furniture is spread again, its games end and its guests look for a seat. The guests and
    //! games read are bound to their creatures again in the first turn (doUpkeep).
    bool importFromStream(std::istream& is) override;

    //! \brief Returns whether the tavern contains a full three by three block.
    bool hasMinimumBlock() const;

    //! \brief True when a keg, a table or the counter of this room stands on the tile; a table covers two tiles.
    //! \param tile The tile to test; nullptr gives false.
    bool hasFurnitureOn(const Tile* tile) const;

    //! \brief Returns the table tile of the seat of the guest, so that it walks straight to its table.
    //! \param creature The guest.
    Tile* getArrivalTile(const Creature& creature) override;

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
    std::map<RoomTavernSeat, RoomTavernSpot>::iterator findSpotOf(const Creature* creature);

    //! \brief Returns the tiles of the tables of the room in coordinate order.
    std::vector<Tile*> getTableTiles() const;

    //! \brief True when the seat is at a table of the room and can take a guest: its bench has no wall behind it and
    //! all the places the guest needs, starting at the seat, are free on that bench.
    //! \param seat The seat to test; for a large guest the first of its places.
    //! \param places The number of neighbouring places the guest needs.
    bool isFreeSeat(const RoomTavernSeat& seat, uint32_t places) const;

    //! \brief True when a bench has a wall (or the edge of the map) directly behind it, so that nobody sits there.
    //! \param table The tile of the table.
    //! \param bench 0 for the first bench of the table, 1 for the second.
    bool isBenchBlocked(const Tile* table, uint32_t bench) const;

    //! \brief Picks a free seat for the creature; a table with a guest comes first, then the nearest table.
    //! \param creature The guest.
    //! \param seat Set to the seat that was picked.
    //! \return False if the room has no free seat for the creature.
    bool pickFreeSeat(const Creature& creature, RoomTavernSeat& seat) const;

    //! \brief True when the creature is large (a bed of two by two tiles) and takes more than one place.
    //! \param creature The creature to test.
    static bool isLargeGuest(const Creature& creature);

    //! \brief The number of neighbouring places on a bench the creature needs: 1, or for a large creature as many as its
    //! seated width covers (the places are 0.328 tiles wide).
    //! \param creature The creature.
    static uint32_t getPlacesOf(const Creature& creature);

    //! \brief Returns where a guest sits on the ground, from the place and rotation of the table.
    //! \param seat The seat.
    //! \param places The number of places the guest takes (it sits in the middle of them).
    Ogre::Vector2 getSeatPosition(const RoomTavernSeat& seat, uint32_t places) const;

    //! \brief Returns the direction on the ground in which a guest on the seat looks across its table.
    //! \param seat The seat.
    Ogre::Vector3 getAcrossTableDirection(const RoomTavernSeat& seat) const;

    //! \brief True when the guest is at the place of its seat.
    //! \param creature The guest.
    //! \param seat The seat.
    //! \param places The number of places the guest takes.
    bool isOnSeat(const Creature& creature, const RoomTavernSeat& seat, uint32_t places) const;

    //! \brief The direction a guest looks in while it plays a game with another guest or slaps it: across its table
    //! while it is on its seat (the seated clips are made for that direction), otherwise towards the partner.
    //! \param creature The guest.
    //! \param partner The other guest of the game or the duel.
    Ogre::Vector3 getFacingDirection(const Creature& creature, const Creature& partner);

    //! \brief Finds free points next to the seat from where a creature gets onto the bench.
    //! \param creature The guest.
    //! \param seat The seat.
    //! \param places The number of places the guest takes.
    //! \param stagingPoints Set to the usable points, the best first.
    void findSeatStagingPoints(Creature& creature, const RoomTavernSeat& seat, uint32_t places,
        std::vector<Ogre::Vector2>& stagingPoints) const;

    //! \brief Walks the guest around the furniture and onto its seat; the last leg goes straight to the bench.
    //! \param creature The guest.
    //! \param seat The seat.
    //! \param places The number of places the guest takes.
    //! \return False when there is no way to the seat.
    bool walkToSeat(Creature& creature, const RoomTavernSeat& seat, uint32_t places);

    //! \brief Lets a guest at the end of its visit step away from the bench, so it never leaves through the furniture.
    //! \param creature The guest.
    //! \param seat The seat.
    //! \param places The number of places the guest takes.
    //! \return True when the guest walks; false when there is no free point next to the bench.
    bool stepOffSeat(Creature& creature, const RoomTavernSeat& seat, uint32_t places);

    //! \brief Moves a guest whose seat cannot be reached to another free seat it can walk to.
    //! \param creature The guest.
    //! \param seat The seat that cannot be reached.
    //! \return True when the guest walks to another seat.
    bool walkToOtherSeat(Creature& creature, const RoomTavernSeat& seat);

    //! \brief Returns another tavern of the keeper that has a seat for the creature and can be reached.
    //! \param creature The creature that needs a seat.
    //! \return The tavern, or nullptr when there is none.
    Room* findOtherTavern(Creature& creature);

    //! \brief Sends a guest this tavern has no seat for away: to the other tavern, otherwise to its work and the visit cooldown.
    //! \param creature The guest; its action queue must no longer hold a use of this tavern.
    //! \param otherTavern The tavern found by findOtherTavern before the guest left, or nullptr.
    void sendToOtherTavernOrWork(Creature& creature, Room* otherTavern);

    //! \brief All guests stand up: running games end without a winner and without effects, and each guest looks for a
    //! free seat again by the normal rule. A guest without a free seat goes to another tavern of the keeper, otherwise
    //! it leaves and tries again after the visit cooldown.
    void standUpGuests();

    //! \brief Shows what the guest does in its state: the clip of the state, turned towards what it looks at.
    //! \param tile The tile of the table.
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

    //! \brief Server side. Lets the guests stand up and look for a seat again when the table of one of them is gone.
    void reseatGuestsAtLostTables();

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

    //! \brief The turns the next drink of the guest lasts: BeerDrinkTurns for a beer (the tavern serves beer and the
    //! payer has the price), DrinkTurns for water ([Tavern] of global.cfg).
    //! \param creature The guest.
    int32_t nextDrinkTurns(const Creature& creature) const;

    //! \brief True while another guest of the same keeper drinks at the table of the seat.
    //! \param seat The seat of the guest that waits for a game.
    bool hasDrinkingTableMate(const RoomTavernSeat& seat) const;

    //! \brief Lets the guest that wants a game start it with a guest of the same table that is done too; a guest on the
    //! opposite bench comes first. The guest asks again every turn while it waits.
    //! \param seat The seat of the guest.
    void tryStartGame(const RoomTavernSeat& seat);

    //! \brief Starts a game of two guests at the same table.
    //! \param seatA The seat of the guest that starts the game.
    //! \param seatB The seat of the other guest.
    void startGame(const RoomTavernSeat& seatA, const RoomTavernSeat& seatB);

    //! \brief Plays one turn of an arm wrestling or dice game.
    //! \param it The game.
    void playContestTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);

    //! \brief Plays one turn of a slap duel: the guest whose turn it is slaps.
    //! \param it The game.
    void playDuelTurn(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);

    //! \brief Ends a game with a winner: mood and experience, spectators, the innkeeper cheers; the loser of a slap
    //! duel is knocked out.
    //! \param it The game; it is erased.
    //! \param winner The winner of the game.
    //! \param underdogLevels Levels the winner was below the loser (0 if it was not the weaker one); the weaker one
    //! wins more mood and double experience.
    void concludeGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels);

    //! \brief Ends a game without winner and without effects; both guests are done.
    //! \param it The game; it is erased.
    void abortGame(std::map<RoomTavernSeat, RoomTavernGame>::iterator it);

    //! \brief The loser of a slap duel goes down: it lies DuelKoTurns turns, gets up and goes to bed.
    //! \param spot The place of the loser.
    void knockOut(RoomTavernSpot& spot);

    //! \brief The loser of a slap duel falls from its bench onto a free floor tile next to its seat.
    //! \param spot The place of the loser.
    //! \return False when no floor tile is free; the loser then slumps on its seat.
    bool fallNextToBench(RoomTavernSpot& spot);

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
    //! \brief The places of the guests, by seat (server side only). A seat without entry has no guest; a large guest
    //! is kept under the first of its places.
    std::map<RoomTavernSeat, RoomTavernSpot> mSpots;
    //! \brief The running games, by the seat of the first guest (server side only).
    std::map<RoomTavernSeat, RoomTavernGame> mGames;
    //! \brief The places read from a saved room, by creature name, until the creatures are bound again.
    std::map<std::string, RoomTavernPendingSpot> mPendingSpots;
    //! \brief The games read from a saved room until the creatures are bound again.
    std::vector<RoomTavernPendingGame> mPendingGames;
    //! \brief The kegs and tables read from a saved room until updateActiveSpots has placed them again.
    std::vector<RoomTavernSavedFurniture> mSavedFurniture;
    //! \brief The tiles in coordinate order the furniture was last placed for; empty until it was placed once.
    std::vector<Tile*> mLayoutTiles;
    //! \brief The counter tile the furniture was last placed for.
    Tile* mLayoutCounter;
};

#endif // ROOMTAVERN_H
