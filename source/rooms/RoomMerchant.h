#ifndef ROOMMERCHANT_H
#define ROOMMERCHANT_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "entities/ItemInstance.h"

#include <deque>
#include <memory>

class MerchantEntity;
class Player;
class RoomMerchant;
enum class ClientNotificationType;

//! \brief Whether a merchant action reached its table, queued a path, or cannot approach it.
enum class MerchantApproach { failed, walking, ready };

//! \brief One merchant-owned item and its expiring creature reservation.
struct MerchantGood
{
    //! \brief Initialises an empty, unreserved stock entry.
    MerchantGood();
    uint32_t mIndex;
    ItemInstance mItem;
    std::string mReservedBy;
    int64_t mReservedUntil;
};

//! \brief Keeps goods with their table tile through room splitting and takeover.
class RoomMerchantTileData : public TileData
{
public:
    //! \brief Creates an empty merchant tile.
    RoomMerchantTileData();
    //! \brief Copies the tile and its goods for the existing room handover mechanism.
    RoomMerchantTileData(const RoomMerchantTileData* other);
    //! \brief Copies the merchant-specific tile state during a room split.
    TileData* cloneTileData() const override;
    bool mTable;
    std::vector<MerchantGood> mGoods;
};

//! \brief Public view of a stable stock index and the table that owns it.
struct MerchantStockEntry
{
    RoomMerchant* mRoom;
    Tile* mTile;
    const MerchantGood* mGood;
};

//! \brief Trades equipment and potions for all creatures of its owner seat.
class RoomMerchant : public Room
{
public:
    //! \brief Creates an empty merchant room.
    RoomMerchant(GameMap* gameMap);
    //! \brief Removes decorative stock before the room leaves its map.
    void removeFromGameMap(GameMap* gameMap = nullptr) override;
    //! \brief Returns the appended merchant room type.
    RoomType getType() const override;
    //! \brief Updates reservations, the single seat merchant, and live stock windows.
    void doUpkeep() override;
    //! \brief Spawns the seat merchant once its first sales table exists.
    void setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles) override;
    //! \brief Leaves goods as sealed ground bags when their tile is sold or destroyed.
    bool removeCoveredTile(Tile* tile) override;
    //! \brief Lets the receiving room's cloned tile data keep goods during takeover.
    void splitRoom(Room& receiver, const std::vector<Tile*>& tiles) override;
    //! \brief Combines existing stock and histories when two merchant rooms join.
    void absorbRoom(Room* other) override;
    //! \brief Accepts bags when a sales table has a free goods place.
    bool hasCarryEntitySpot(GameEntity* entity) override;
    //! \brief Returns a free table for a worker's carried bag.
    Tile* askSpotForCarriedEntity(GameEntity* entity) override;
    //! \brief Buys an owner bag on delivery, or returns sealed goods to stock without a second purchase.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* entity) override;
    //! \brief Rejects leisure jobs; dedicated trading actions still visit the tables.
    bool hasOpenCreatureSpot(Creature* creature) override;
    //! \brief Rejects leisure use without changing dedicated buying or selling.
    bool useRoom(Creature& creature, bool forced) override;
    //! \brief Saves table goods and the merchant's current position.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Reads optional merchant position after the room's tile data.
    bool importFromStream(std::istream& stream) override;
    //! \brief Returns a table with capacity available after research factors.
    Tile* getFreeTable() const;
    //! \brief Returns the current sales table tiles for the merchant's room-only wandering.
    const std::vector<Tile*>& getSalesTables() const { return mCentralActiveSpotTiles; }
    //! \brief Uses the existing furniture-aware work approach for a sales table.
    MerchantApproach approachTable(Creature& creature, Tile* table);
    //! \brief Stores a bag's item; ownership leaves item only on success.
    bool addGoods(std::unique_ptr<ItemInstance>& item, Tile* table);
    //! \brief Removes the entry with a stable goods index and returns its item.
    std::unique_ptr<ItemInstance> takeGoods(uint32_t index);
    //! \brief Returns the table and item for one stable goods index, or null.
    const MerchantGood* findGood(uint32_t index, Tile*& table) const;
    //! \brief Buys one creature's unwanted inventory item at the configured share and margin.
    bool buyFromCreature(Creature& creature, size_t inventorySlot);
    //! \brief Sells a reserved item to a creature that still wants and can afford it.
    bool sellToCreature(Creature& creature, uint32_t index);
    //! \brief Sells an item to the keeper without margin and places its gift bag in the hand.
    bool sellToKeeper(Player& player, uint32_t index);
    //! \brief Returns whether the creature wants this item under the equipment and potion rules.
    static bool wantsItem(const Creature& creature, const ItemInstance& item);
    //! \brief Returns the unwanted inventory slot to sell, or -1 if none exists.
    static int32_t findSaleSlot(const Creature& creature);
    //! \brief Collects stock across all rooms of one seat.
    static std::vector<MerchantStockEntry> getStock(GameMap& map, const Seat* seat);
    //! \brief Returns the first merchant room of the seat, or null.
    static RoomMerchant* getForSeat(GameMap& map, const Seat* seat);
    //! \brief Counts a potion in the seat's merchant stock for laboratory production choice.
    static uint32_t countPotion(GameMap& map, const Seat* seat, const std::string& id);
    //! \brief Counts sales of a potion among the seat's last twenty merchant deals.
    static uint32_t recentPotionSales(GameMap& map, const Seat* seat, const std::string& id);
    //! \brief Returns stolen table goods on arrival, otherwise the visible table to walk toward.
    static std::unique_ptr<ItemInstance> stealGoods(Creature& thief, Tile*& target);
    //! \brief Sends the owner an updated stock window when it is open.
    static void sendWindow(GameMap& map, Player& player);
    //! \brief Handles the owner-only merchant window, settings and keeper purchase requests.
    static bool handleRequest(GameMap& map, Player& player, ClientNotificationType type, ODPacket& packet);
    //! \brief Records an item deal for posts and keeper Epic notices.
    static void announceDeal(Creature& creature, const ItemInstance& item, uint8_t deal);
    //! \brief Returns the configured base cost of the merchant room.
    static const RoomType mRoomType;
    static const TileVisual mRoomVisual;

protected:
    //! \brief Creates a tile whose goods follow the room's normal tile lifecycle.
    TileData* createTileData(Tile* tile) override;
    //! \brief Adds a centre sales table or a wall shelf.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Releases goods if the room shape removes their centre table.
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Appends the goods on this tile to the existing room tile record.
    void exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* data) const override;
    //! \brief Restores the tile goods and registers their unique Epics.
    bool importTileDataFromStream(std::istream& stream, Tile* tile, TileData* data) override;

private:
    //! \brief Removes the transmitted decorative bags without changing the real stock.
    void clearDisplayedGoods();
    //! \brief Places sealed quality bags in evenly spaced positions on each sales table.
    void refreshDisplayedGoods();
    std::vector<BuildingObject*> mDisplayedGoods;
    size_t mDisplayedCapacity = 0;
    //! \brief Creates the seat figure only when at least one centre table exists.
    void ensureMerchant();
    //! \brief Drops every remaining good from a table as a sealed bag.
    void releaseTableGoods(Tile* tile);
    //! \brief Updates reservations according to fair or profit mode.
    void reserveGoods();
    //! \brief Records and announces a deal, retaining exactly the last twenty entries.
    void recordDeal(const std::string& creature, const ItemInstance& item, double price, bool bought);
    bool mGoodsChanged;
    bool mSavedMerchantPosition;
    Ogre::Vector3 mMerchantPosition;
};

#endif // ROOMMERCHANT_H
