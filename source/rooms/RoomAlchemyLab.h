#ifndef ROOMALCHEMYLAB_H
#define ROOMALCHEMYLAB_H

#include "rooms/Room.h"
#include <cstdint>
#include <cstddef>
#include <map>
#include <string>
#include <utility>
#include <vector>

class PotionDefinition;
class Player;

//! \brief A cauldron's persistent recipe, elapsed brewing seconds and current brewer.
class AlchemyLabTileData : public TileData
{
public:
    //! \brief Starts a free cauldron with no reserved recipe ingredients.
    AlchemyLabTileData() : mDone(0.0), mReserved(false) {}
    //! \brief Copies a cauldron with its room tile during takeover and splitting.
    explicit AlchemyLabTileData(const AlchemyLabTileData* data) : TileData(data),
        mPotion(data->mPotion), mBrewer(data->mBrewer), mDone(data->mDone), mReserved(data->mReserved) {}
    //! \brief Preserves the cauldron's recipe state when a tile is cloned.
    TileData* cloneTileData() const override { return new AlchemyLabTileData(this); }
    //! \brief Recipe and brewer names; timer is fractional seconds of completed work.
    std::string mPotion, mBrewer;
    double mDone;
    bool mReserved;
};

//! \brief One visible laboratory-window row, sent without exposing foreign seat data.
struct LabCauldronRow
{
    //! \brief Creates an empty display row.
    LabCauldronRow() : mRemaining(0.0) {}
    std::string mPotion, mBrewer;
    double mRemaining;
};

//! \brief Complete owner-seat laboratory-window data, adopted atomically on receipt.
struct LabWindowData
{
    //! \brief Initialises the seat's default Automatic brewing mode.
    LabWindowData() : mMode(0) {}
    int32_t mMode;
    std::map<std::string, uint32_t> mHerbs;
    std::vector<LabCauldronRow> mCauldrons;
};

//! \brief Stores delivered herbs and brews one recipe per centre cauldron.
class RoomAlchemyLab : public Room
{
public:
    //! \brief Creates empty laboratory storage and its first cosmetic timer.
    explicit RoomAlchemyLab(GameMap* map);
    //! \brief Returns the appended laboratory type.
    RoomType getType() const override { return mRoomType; }
    //! \brief Chooses available recipes, pauses unattended work and sends owner-window updates.
    void doUpkeep() override;
    //! \brief Allows permitted brewers to reserve a cauldron with ingredients or paused work.
    bool hasOpenCreatureSpot(Creature* creature) override;
    //! \brief Assigns one available cauldron to a permitted brewer.
    bool addCreatureUsingRoom(Creature* creature) override;
    //! \brief Pauses the departing brewer's timer without refunding or losing reserved herbs.
    void removeCreatureUsingRoom(Creature* creature) override;
    //! \brief Performs one turn of the exact research-adjusted brewing duration.
    bool useRoom(Creature& creature, bool forced) override;
    //! \brief Accepts harvested bundles while herb storage has space.
    bool hasCarryEntitySpot(GameEntity* carried) override;
    //! \brief Returns a laboratory delivery tile without taking ownership prematurely.
    Tile* askSpotForCarriedEntity(GameEntity* carried) override;
    //! \brief Moves delivered recipe units into storage, leaving any excess in the bundle.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* carried) override;
    //! \brief Unions ingredients and paused batches of absorbed laboratories without discarding overflow.
    void absorbRoom(Room* room) override;
    //! \brief Divides stored herbs by transferred tile count, leaving integer remainders here.
    void splitRoom(Room& room, const std::vector<Tile*>& tiles) override;
    //! \brief Uses one stock snapshot for all pieces split off in the same operation.
    void checkForSplit() override;
    //! \brief Preserves a removed tile's reserved batch before its tile data is retired.
    bool removeCoveredTile(Tile* tile) override;
    //! \brief Restores paused batches after the cauldron layout has settled.
    void updateActiveSpots(GameMap* map = nullptr) override;
    //! \brief Sends the owner's combined laboratory state to its human player.
    static void sendWindow(GameMap& map, Player& player);
    //! \brief Counts loose finished potions waiting in this seat's labs and treasuries.
    static uint32_t countWaitingPotion(GameMap& map, const Seat* seat, const std::string& id);
    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;
protected:
    //! \brief Creates a tile's empty cauldron state.
    TileData* createTileData(Tile* tile) override;
    //! \brief Places cauldrons at centres and bottle shelves at wall spots.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Releases a brewer before its physical cauldron is removed.
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Writes per-room herb storage and reserved paused batches after the existing room fields.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Reads optional herb storage and paused batches without consuming a following room.
    bool importFromStream(std::istream& stream) override;
    //! \brief Saves per-cauldron progress and current brewer after the base tile record.
    void exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* data) const override;
    //! \brief Reads an optional cauldron state, preserving compatibility with empty old data.
    bool importTileDataFromStream(std::istream& stream, Tile* tile, TileData* data) override;
private:
    //! \brief Returns the number of stored herb bundles.
    uint32_t herbCount() const;
    //! \brief Checks all ingredient quantities without consuming them.
    bool canBrew(const PotionDefinition& potion) const;
    //! \brief Applies the exact stock, sales, file-order and largest-usable-size choice rules.
    const PotionDefinition* choosePotion() const;
    //! \brief Returns the exact research-adjusted recipe duration.
    double brewSeconds(const PotionDefinition& potion) const;
    //! \brief Returns an unassigned cauldron with ingredients or paused work.
    Tile* findCauldron() const;
    //! \brief Returns finished bags currently waiting on this laboratory's floor.
    uint32_t finishedCount() const;
    //! \brief Emits a harmless busy-cauldron accident at the prescribed interval.
    void showBang();
    //! \brief Moves a reserved tile batch into the room's persistent paused queue exactly once.
    void preserveBatch(Tile* tile);
    //! \brief Assigns paused batches to unoccupied real cauldrons without consuming herbs again.
    void resumeBatches();
    //! \brief Reserved recipe ids and elapsed work remain here while no cauldron is free.
    std::vector<std::pair<std::string, double>> mPausedBatches;
    //! \brief A transient split snapshot keeps all integer remainders in the original room.
    std::map<std::string, uint32_t> mSplitHerbs;
    std::size_t mSplitTiles = 0;
    //! \brief Stored ingredients, working assignments and cosmetic-only seconds to the next bang.
    std::map<std::string, uint32_t> mHerbs;
    std::map<Creature*, Tile*> mBrewers;
    double mBangSeconds;
};

#endif
