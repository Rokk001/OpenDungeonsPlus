#include "rooms/RoomMerchant.h"

#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/ItemBagEntity.h"
#include "entities/MerchantEntity.h"
#include "entities/Tile.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "gamemap/RoomObjectNavigation.h"
#include "network/ClientNotification.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"

#include <algorithm>
#include <cmath>
#include <sstream>

const RoomType RoomMerchant::mRoomType = RoomType::merchant;
const TileVisual RoomMerchant::mRoomVisual = TileVisual::merchantRoom;

namespace
{
static const std::string ROOM_NAME = "Merchant";
static const std::string ROOM_DISPLAY = "Merchant room";
static const double PERCENT = 100.0;
static uint32_t nextGoodsIndex = 1;

//! \brief Registers the merchant through the existing room construction and editor paths.
class RoomMerchantFactory : public RoomFactory
{
    //! \brief Returns the merchant enum value.
    RoomType getRoomType() const override { return RoomMerchant::mRoomType; }
    //! \brief Returns the merchant tile visual.
    TileVisual getVisualType() const override { return RoomMerchant::mRoomVisual; }
    //! \brief Returns its configuration name.
    const std::string& getName() const override { return ROOM_NAME; }
    //! \brief Returns the approved player-facing room name.
    const std::string& getNameReadable() const override { return ROOM_DISPLAY; }
    //! \brief Reads the approved build cost.
    int getCostPerTile() const override { return ConfigManager::getSingleton().getRoomConfigInt32("MerchantCostPerTile"); }
    //! \brief Previews ordinary room construction.
    void checkBuildRoom(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefault(map, RoomMerchant::mRoomType, input, command); }
    //! \brief Pays for and builds validated merchant tiles.
    bool buildRoom(GameMap* map, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, map, player, packet)) return false;
        return buildRoomOnTiles(map, player, tiles, false);
    }
    //! \brief Previews editor construction without a fee.
    void checkBuildRoomEditor(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefaultEditor(map, RoomMerchant::mRoomType, input, command); }
    //! \brief Creates merchant tiles through the standard editor path.
    bool buildRoomEditor(GameMap* map, ODPacket& packet) const override
    { return buildRoomDefaultEditor(map, new RoomMerchant(map), packet); }
    //! \brief Creates a room for tile splitting and ownership transfer.
    Room* createRoom(GameMap* map) const override { return new RoomMerchant(map); }
    //! \brief Loads a merchant room with the standard room framing.
    Room* getRoomFromStream(GameMap* map, std::istream& stream) const override
    {
        RoomMerchant* room = new RoomMerchant(map);
        if(!Room::importRoomFromStream(*room, stream)) { delete room; return nullptr; }
        return room;
    }
    //! \brief Builds the requested tiles, optionally using the caller's existing fee waiver.
    bool buildRoomOnTiles(GameMap* map, Player* player, const std::vector<Tile*>& tiles, bool noFee) const override
    {
        const int32_t price = static_cast<int32_t>(tiles.size()) * getCostPerTile();
        if(!noFee && !map->withdrawFromTreasuries(price, player->getSeat())) return false;
        return buildRoomDefault(map, new RoomMerchant(map), player->getSeat(), tiles);
    }
};
static RoomRegister reg(new RoomMerchantFactory);

//! \brief Reads a room configuration amount without changing its prescribed value.
double setting(const std::string& key)
{ return ConfigManager::getSingleton().getRoomConfigDouble(key); }

//! \brief Reads the margin as a fractional share.
double margin(const Seat* seat)
{ return seat->getMerchantMargin() / PERCENT; }

//! \brief Thrift discounts what the creature pays and the keeper's purchase margin equally.
double thrift(const Creature& creature)
{ return std::max(0.0, 1.0 - creature.getItemEffect("Thrift") / PERCENT); }

//! \brief Computes one researched table's capacity, rounded down as specified.
size_t tableCapacity(const Seat* seat)
{
    return static_cast<size_t>(std::floor(SkillManager::getResearchValue(seat, SkillType::roomMerchant,
        setting("MerchantGoodsPerTable"), ResearchEffect::Capacity)));
}
}

//! \brief Initialises a stable stock identity without a reservation.
MerchantGood::MerchantGood() : mIndex(0), mReservedUntil(0) {}
//! \brief Starts a tile with no table or goods.
RoomMerchantTileData::RoomMerchantTileData() : TileData(), mTable(false) {}
//! \brief Copies goods when the normal room code clones a transferred tile.
RoomMerchantTileData::RoomMerchantTileData(const RoomMerchantTileData* other) :
    TileData(other), mTable(other->mTable), mGoods(other->mGoods) {}
//! \brief Preserves the goods in a transferred table tile.
TileData* RoomMerchantTileData::cloneTileData() const { return new RoomMerchantTileData(this); }
//! \brief Initialises an empty room and optional saved figure position.
RoomMerchant::RoomMerchant(GameMap* map) : Room(map), mGoodsChanged(true),
    mSavedMerchantPosition(false), mMerchantPosition(Ogre::Vector3::ZERO)
{ setMeshName(ROOM_NAME); }
//! \brief Releases decorative stock before the normal furniture and room removal.
void RoomMerchant::removeFromGameMap(GameMap* map)
{
    clearDisplayedGoods();
    Room::removeFromGameMap(map);
}

//! \brief Deletes only the visual copies; real goods remain in their table records.
void RoomMerchant::clearDisplayedGoods()
{
    for(BuildingObject* bag : mDisplayedGoods)
    {
        bag->removeFromGameMap();
        bag->deleteYourself();
    }
    mDisplayedGoods.clear();
}

//! \brief Rebinds loaded or transferred crystals to the first table without moving ordinary goods.
void RoomMerchant::moveCrystalsToFirstTable()
{
    const ItemInstance crystal = *ItemInstance::createSoulCrystal();
    Tile* firstTable = getFreeTable(&crystal);
    if(firstTable == nullptr) return;
    RoomMerchantTileData* first = static_cast<RoomMerchantTileData*>(mTileData.at(firstTable));
    for(Tile* tile : mCoveredTiles)
    {
        if(tile == firstTable) continue;
        std::vector<MerchantGood>& goods = static_cast<RoomMerchantTileData*>(mTileData.at(tile))->mGoods;
        for(std::vector<MerchantGood>::iterator it = goods.begin(); it != goods.end();)
        {
            if(!it->mItem.mSoulCrystal) { ++it; continue; }
            first->mGoods.push_back(*it);
            it = goods.erase(it);
        }
    }
}

//! \brief Fits ordinary goods to the existing cloth slots and keeps crystals at the first table centre.
void RoomMerchant::refreshDisplayedGoods()
{
    clearDisplayedGoods();
    if(!getIsOnServerMap()) return;
    moveCrystalsToFirstTable();
    const size_t capacity = tableCapacity(getSeat());
    mDisplayedCapacity = capacity;
    for(Tile* tile : mCoveredTiles)
    {
        const RoomMerchantTileData* data = static_cast<const RoomMerchantTileData*>(mTileData.at(tile));
        if(!data->mTable) continue;
        // Retained stock still fits when its new owner has researched fewer table places.
        size_t ordinary = 0;
        for(const MerchantGood& good : data->mGoods)
            if(!good.mItem.mSoulCrystal) ++ordinary;
        const size_t displayPlaces = std::max(capacity, ordinary);
        const float spacing = 0.63f / static_cast<float>(displayPlaces);
        const float scale = std::min(0.6f, spacing / 0.36f);
        size_t ordinaryIndex = 0;
        for(size_t index = 0; index < data->mGoods.size(); ++index)
        {
            const bool crystal = data->mGoods[index].mItem.mSoulCrystal;
            const float y = crystal ? static_cast<float>(tile->getY()) :
                tile->getY() - 0.315f + spacing * (static_cast<float>(ordinaryIndex++) + 0.5f);
            BuildingObject* bag = new BuildingObject(getGameMap(), *this, data->mGoods[index].mItem.mSoulCrystal ? "SoulCrystal" : "ItemBag", tile,
                tile->getX(), y, 0.712f, 0.0f, false);
            bag->setFurnitureScale(Ogre::Vector2(scale, scale));
            if(!data->mGoods[index].mItem.mSoulCrystal)
                bag->setItemBagAppearance(data->mGoods[index].mItem.mQuality, true);
            bag->addToGameMap();
            bag->setPosition(bag->getPosition());
            mDisplayedGoods.push_back(bag);
        }
    }
}
//! \brief Returns the merchant room's type.
RoomType RoomMerchant::getType() const { return mRoomType; }
//! \brief Creates a merchant tile whose stock follows its ownership.
TileData* RoomMerchant::createTileData(Tile* tile) { return new RoomMerchantTileData; }

//! \brief Builds the normal room before spawning its seat figure.
void RoomMerchant::setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles)
{
    Room::setupRoom(name, seat, tiles);
    ensureMerchant();
}

//! \brief Returns the first nonempty merchant room belonging to a seat.
RoomMerchant* RoomMerchant::getForSeat(GameMap& map, const Seat* seat)
{
    for(Room* room : map.getRoomsByTypeAndSeat(RoomType::merchant, seat))
        if(room->numCoveredTiles() > 0) return static_cast<RoomMerchant*>(room);
    return nullptr;
}

//! \brief Creates the one seat merchant only after a usable centre table exists.
void RoomMerchant::ensureMerchant()
{
    if(!getIsOnServerMap() || getSeat() == nullptr || getSeat()->getMerchant() != nullptr || mCentralActiveSpotTiles.empty())
        return;
    Ogre::Vector3 position = mCentralActiveSpotTiles.front()->getPosition();
    if(mSavedMerchantPosition)
    {
        Tile* saved = getGameMap()->getTile(Helper::round(mMerchantPosition.x), Helper::round(mMerchantPosition.y));
        if(saved != nullptr && saved->getCoveringRoom() == this) position = mMerchantPosition;
    }
    MerchantEntity* merchant = new MerchantEntity(getGameMap(), getSeat(), position);
    merchant->addToGameMap();
    merchant->createMesh();
    merchant->setPosition(position);
    merchant->setAnimationState("Idle");
    mSavedMerchantPosition = false;
}

//! \brief Places a table in every centre spot and shelves on wall spots.
BuildingObject* RoomMerchant::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    const bool centre = place == activeSpotCenter;
    RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(mTileData.at(tile));
    if(centre) data->mTable = true;
    mGoodsChanged = true;
    return new BuildingObject(getGameMap(), *this, centre ? "SalesTable" : "MerchantShelf", *tile, 0.0f, false);
}

//! \brief Leaves stock sealed on the floor when its table disappears.
void RoomMerchant::releaseTableGoods(Tile* tile)
{
    std::map<Tile*, TileData*>::iterator found = mTileData.find(tile);
    if(found == mTileData.end()) return;
    RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(found->second);
    for(const MerchantGood& good : data->mGoods)
    {
        std::unique_ptr<ItemInstance> item(new ItemInstance(good.mItem));
        item->mMerchantGoods = true;
        ItemBagEntity* bag = new ItemBagEntity(getGameMap(), std::move(item));
        bag->setSeat(getSeat());
        bag->addToGameMap(); bag->createMesh(); bag->setPosition(tile->getPosition());
    }
    data->mGoods.clear();
    clearDisplayedGoods();
    mGoodsChanged = true;
}

//! \brief Removes table state and releases its remaining goods.
void RoomMerchant::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    if(place == activeSpotCenter)
    {
        releaseTableGoods(tile);
        static_cast<RoomMerchantTileData*>(mTileData.at(tile))->mTable = false;
    }
    Room::notifyActiveSpotRemoved(place, tile);
}

//! \brief Preserves sold-tile goods as sealed floor bags.
bool RoomMerchant::removeCoveredTile(Tile* tile)
{
    releaseTableGoods(tile);
    return Room::removeCoveredTile(tile);
}

//! \brief Clears only the old copies after the existing handover cloned the stock into the receiving room.
void RoomMerchant::splitRoom(Room& receiver, const std::vector<Tile*>& tiles)
{
    for(Tile* tile : tiles)
    {
        std::map<Tile*, TileData*>::iterator found = mTileData.find(tile);
        if(found != mTileData.end()) static_cast<RoomMerchantTileData*>(found->second)->mGoods.clear();
    }
    mGoodsChanged = true;
    if(receiver.getType() == getType()) static_cast<RoomMerchant&>(receiver).mGoodsChanged = true;
    if(mCoveredTiles.empty() && getForSeat(*getGameMap(), getSeat()) == nullptr &&
        getSeat()->getMerchant() != nullptr && receiver.getSeat()->getMerchant() == nullptr)
    {
        MerchantEntity* merchant = getSeat()->getMerchant();
        merchant->removeFromGameMap();
        merchant->setSeat(receiver.getSeat());
        merchant->addToGameMap();
        merchant->createMesh();
    }
}

//! \brief Lets normal room merging move tile stock, then refreshes the stock display.
void RoomMerchant::absorbRoom(Room* other)
{
    if(other == nullptr || other->getType() != getType()) return;
    Room::absorbRoom(other);
    mGoodsChanged = true;
}

//! \brief Returns the first real table for a crystal or one with ordinary goods capacity.
Tile* RoomMerchant::getFreeTable(const ItemInstance* item) const
{
    const size_t capacity = tableCapacity(getSeat());
    for(Tile* tile : mCoveredTiles)
    {
        const RoomMerchantTileData* data = static_cast<const RoomMerchantTileData*>(mTileData.at(tile));
        if(!data->mTable) continue;
        if(item != nullptr && item->mSoulCrystal) return tile;
        size_t ordinary = 0;
        for(const MerchantGood& good : data->mGoods)
            if(!good.mItem.mSoulCrystal) ++ordinary;
        if(ordinary < capacity) return tile;
    }
    return nullptr;
}

//! \brief Approaches the table through the same furniture-aware routes used by working creatures.
MerchantApproach RoomMerchant::approachTable(Creature& creature, Tile* table)
{
    if(table == nullptr || creature.isActionInList(CreatureActionType::fight)) return MerchantApproach::failed;
    BuildingObject* object = getBuildingObjectFromTile(table);
    if(object == nullptr) return MerchantApproach::failed;
    std::vector<Ogre::Vector2> path;
    const Ogre::Vector2 wanted = table->getPosition2d();
    if(!RoomObjectNavigation::workApproach(creature, *object, wanted, Ogre::Vector2::ZERO, path))
        return MerchantApproach::failed;
    if(path.empty()) return MerchantApproach::ready;
    creature.setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
    creature.pushAction(Utils::make_unique<CreatureActionWalkToTile>(creature));
    return MerchantApproach::walking;
}

//! \brief Accepts ordinary goods at the specified table and crystals at the first actual table.
bool RoomMerchant::addGoods(std::unique_ptr<ItemInstance>& item, Tile* table)
{
    if(item.get() == nullptr) return false;
    if(item->mSoulCrystal) table = getFreeTable(item.get());
    if(table == nullptr || table->getCoveringRoom() != this) return false;
    RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(mTileData.at(table));
    if(!data->mTable) return false;
    size_t ordinary = 0;
    for(const MerchantGood& existing : data->mGoods)
        if(!existing.mItem.mSoulCrystal) ++ordinary;
    if(!item->mSoulCrystal && ordinary >= tableCapacity(getSeat())) return false;
    MerchantGood good;
    good.mIndex = nextGoodsIndex++;
    good.mItem = *item;
    good.mItem.mMerchantGoods = true;
    data->mGoods.push_back(good);
    item.reset();
    mGoodsChanged = true;
    return true;
}

//! \brief Collects the current stable stock entries of every merchant room of the seat.
std::vector<MerchantStockEntry> RoomMerchant::getStock(GameMap& map, const Seat* seat)
{
    std::vector<MerchantStockEntry> stock;
    for(Room* base : map.getRoomsByTypeAndSeat(RoomType::merchant, seat))
    {
        RoomMerchant* room = static_cast<RoomMerchant*>(base);
        for(Tile* tile : room->mCoveredTiles)
            for(const MerchantGood& good : static_cast<RoomMerchantTileData*>(room->mTileData.at(tile))->mGoods)
            {
                MerchantStockEntry entry = {room, tile, &good};
                stock.push_back(entry);
            }
    }
    return stock;
}

//! \brief Finds one entry without treating stale client indices as new goods.
const MerchantGood* RoomMerchant::findGood(uint32_t index, Tile*& table) const
{
    table = nullptr;
    for(Tile* tile : mCoveredTiles)
        for(const MerchantGood& good : static_cast<RoomMerchantTileData*>(mTileData.at(tile))->mGoods)
            if(good.mIndex == index) { table = tile; return &good; }
    return nullptr;
}

//! \brief Transfers ownership of exactly the entry with this stable goods index.
std::unique_ptr<ItemInstance> RoomMerchant::takeGoods(uint32_t index)
{
    for(Tile* tile : mCoveredTiles)
    {
        std::vector<MerchantGood>& goods = static_cast<RoomMerchantTileData*>(mTileData.at(tile))->mGoods;
        for(std::vector<MerchantGood>::iterator it = goods.begin(); it != goods.end(); ++it)
            if(it->mIndex == index)
            {
                std::unique_ptr<ItemInstance> item(new ItemInstance(it->mItem));
                item->mMerchantGoods = false;
                goods.erase(it);
                mGoodsChanged = true;
                return item;
            }
    }
    return std::unique_ptr<ItemInstance>();
}

//! \brief Identifies desired equipment, usable potions and worthwhile crystals with inventory room.
bool RoomMerchant::wantsItem(const Creature& creature, const ItemInstance& item)
{
    if(item.mSoulCrystal)
    {
        bool freeSlot = false;
        for(const std::unique_ptr<ItemInstance>& held : creature.getInventory())
        {
            if(held.get() == nullptr) freeSlot = true;
            else if(held->mSoulCrystal) return false;
        }
        const double price = item.getPrice(creature.getGameMap()) * (1.0 + margin(creature.getSeat())) * thrift(creature);
        return freeSlot && creature.wantsSoulCrystal(price);
    }
    if(item.getLevelMin(creature.getGameMap()) > creature.getLevel()) return false;
    if(!item.mPotionId.empty())
    {
        for(const std::unique_ptr<ItemInstance>& slot : creature.getPotionSlots())
            if(slot.get() == nullptr) return true;
        return false;
    }
    if(!creature.isItemEquippable(item)) return false;
    const int32_t slot = creature.getItemEquipmentSlot(item);
    if(slot < 0) return false;
    const std::unique_ptr<ItemInstance>& worn = creature.getEquipment()[static_cast<size_t>(slot)];
    return creature.rateItem(item) > (worn.get() == nullptr ? 0.0 : creature.rateItem(*worn)) + ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("MerchantEquipMargin", 0.5);
}

//! \brief Keeps level-gated items and potion refills, selling only unwanted carried goods.
int32_t RoomMerchant::findSaleSlot(const Creature& creature)
{
    const std::array<std::unique_ptr<ItemInstance>, 4>& inventory = creature.getInventory();
    for(size_t index = 0; index < inventory.size(); ++index)
        if(inventory[index].get() != nullptr && inventory[index]->getLevelMin(creature.getGameMap()) <= creature.getLevel()
            && !(inventory[index]->mSoulCrystal ? creature.wantsSoulCrystal(inventory[index]->getPrice(creature.getGameMap()))
                : wantsItem(creature, *inventory[index]))) return static_cast<int32_t>(index);
    return -1;
}

//! \brief Reserves goods for the greatest need or the highest-level buyer, with sixty-turn expiry.
void RoomMerchant::reserveGoods()
{
    const int64_t turn = getGameMap()->getTurnNumber();
    for(Tile* tile : mCoveredTiles)
        for(MerchantGood& good : static_cast<RoomMerchantTileData*>(mTileData.at(tile))->mGoods)
        {
            if(!good.mReservedBy.empty() && good.mReservedUntil > turn) continue;
            Creature* best = nullptr;
            for(Creature* creature : getGameMap()->getCreaturesBySeat(getSeat()))
            {
                if(!creature->isAlive() || !wantsItem(*creature, good.mItem)) continue;
                if(best == nullptr) { best = creature; continue; }
                if(getSeat()->getMerchantMode() == "fair")
                {
                    if(creature->rateItem(good.mItem) > best->rateItem(good.mItem)) best = creature;
                }
                else if(creature->getLevel() > best->getLevel() || (creature->getLevel() == best->getLevel()
                    && creature->getDefinition()->getFee(0) > best->getDefinition()->getFee(0))) best = creature;
            }
            good.mReservedBy = best == nullptr ? "" : best->getName();
            good.mReservedUntil = turn + static_cast<int64_t>(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("MerchantReservationTurns", 60.0));
        }
}

//! \brief Records the approved twenty-deal history and plays the merchant's reaction.
void RoomMerchant::recordDeal(const std::string& creature, const ItemInstance& item, double price, bool bought)
{
    std::ostringstream line;
    const Creature* actor = getGameMap()->getCreature(creature);
    line << getGameMap()->getTurnNumber() << '\t' << creature << '\t'
        << (actor == nullptr ? "" : actor->getDefinition()->getClassName()) << '\t'
        << (actor != nullptr && actor->getDefinition()->isWorker()) << '\t'
        << (bought ? "bought" : "sold") << '\t' << item.getDisplayName(getGameMap()) << '\t' << price;
    getSeat()->recordMerchantDeal(line.str(), item.mPotionId, bought);
    if(getSeat()->getMerchant() != nullptr) getSeat()->getMerchant()->onDeal();
    if(getCentralTile() != nullptr) fireRoomSound(*getCentralTile(), "Merchant/Deal");
    Player* player = getSeat()->getPlayer();
    if(player != nullptr && player->getIsHuman() && player->getMerchantWindowOpen()) sendWindow(*getGameMap(), *player);
}

//! \brief Buys an unwanted inventory item and routes its exact fractional proceeds.
bool RoomMerchant::buyFromCreature(Creature& creature, size_t slot)
{
    if(creature.getSeat() != getSeat() || creature.isActionInList(CreatureActionType::fight)
        || slot >= creature.getInventory().size() || creature.getInventory()[slot].get() == nullptr) return false;
    const ItemInstance& offered = *creature.getInventory()[slot];
    Tile* table = getFreeTable(&offered);
    if(table == nullptr || (offered.mSoulCrystal ? creature.wantsSoulCrystal(offered.getPrice(getGameMap()))
        : wantsItem(creature, offered)) || offered.getLevelMin(getGameMap()) > creature.getLevel()) return false;
    const double price = offered.getPrice(getGameMap()) * setting("MerchantBuyShare");
    const ItemInstance copy = offered;
    std::unique_ptr<ItemInstance> item = creature.setInventorySlot(slot, std::unique_ptr<ItemInstance>());
    if(!addGoods(item, table)) { creature.setInventorySlot(slot, std::move(item)); return false; }
    creature.addGoldCarriedFraction(price * (1.0 - margin(getSeat())));
    getSeat()->addMerchantGold(price * margin(getSeat()));
    creature.addMerchantMood((setting("MerchantMoodNeutralMargin") - getSeat()->getMerchantMargin()) * setting("MerchantMoodPerMarginPoint"));
    recordDeal(creature.getName(), copy, price * (1.0 - margin(getSeat())), false);
    return true;
}

//! \brief Sells a still-reserved desired item and pays the keeper only the discounted margin.
bool RoomMerchant::sellToCreature(Creature& creature, uint32_t index)
{
    reserveGoods();
    Tile* table = nullptr;
    const MerchantGood* good = findGood(index, table);
    if(good == nullptr || creature.getSeat() != getSeat() || creature.isActionInList(CreatureActionType::fight)
        || good->mReservedBy != creature.getName() || !wantsItem(creature, good->mItem)) return false;
    const double base = good->mItem.getPrice(getGameMap());
    const double price = base * (1.0 + margin(getSeat())) * thrift(creature);
    if(creature.getGoldCarriedAmount() < price) return false;
    std::unique_ptr<ItemInstance> item = takeGoods(index);
    const ItemInstance copy = *item;
    creature.addGoldCarriedFraction(-price);
    getSeat()->addMerchantGold(base * margin(getSeat()) * thrift(creature));
    if(!item->mPotionId.empty())
    {
        for(size_t slot = 0; slot < creature.getPotionSlots().size(); ++slot)
            if(creature.getPotionSlots()[slot].get() == nullptr)
            { creature.setPotionSlot(slot, std::move(item)); break; }
    }
    else creature.acceptItem(std::move(item), true);
    creature.addMerchantMood((setting("MerchantMoodNeutralMargin") - getSeat()->getMerchantMargin()) * setting("MerchantMoodPerMarginPoint"));
    const int32_t marginPercent = getSeat()->getMerchantMargin();
    uint8_t deal = 1;
    if(marginPercent == 0) deal = 2;
    else if(marginPercent >= 30) deal = 3;
    announceDeal(creature, copy, deal);
    recordDeal(creature.getName(), copy, price, true);
    return true;
}

//! \brief Lets only the keeper buy at base price, creating a gifted hand bag.
bool RoomMerchant::sellToKeeper(Player& player, uint32_t index)
{
    if(player.getSeat() != getSeat()) return false;
    Tile* table = nullptr;
    const MerchantGood* good = findGood(index, table);
    if(good == nullptr) return false;
    const double price = good->mItem.getPrice(getGameMap());
    if(!getGameMap()->withdrawFromTreasuries(static_cast<int32_t>(price), getSeat())) return false;
    std::unique_ptr<ItemInstance> item = takeGoods(index);
    item->mGifted = true;
    const ItemInstance copy = *item;
    ItemBagEntity* bag = new ItemBagEntity(getGameMap(), std::move(item));
    bag->setSeat(getSeat()); bag->addToGameMap(); bag->createMesh(); bag->setPosition(table->getPosition());
    player.pickUpEntity(bag);
    recordDeal("Keeper", copy, price, true);
    return true;
}

//! \brief Accepts carried crystals on the first table regardless of ordinary goods capacity.
bool RoomMerchant::hasCarryEntitySpot(GameEntity* entity)
{
    if(entity == nullptr || entity->getObjectType() != GameEntityType::itemBagEntity) return false;
    const ItemInstance* item = static_cast<ItemBagEntity*>(entity)->getItem();
    return item != nullptr && getFreeTable(item) != nullptr;
}
//! \brief Directs the worker to the crystal table or an ordinary free goods place.
Tile* RoomMerchant::askSpotForCarriedEntity(GameEntity* entity)
{ return hasCarryEntitySpot(entity) ? getFreeTable(static_cast<ItemBagEntity*>(entity)->getItem()) : nullptr; }

//! \brief Restocks sealed goods or purchases the keeper's delivered item without margin.
void RoomMerchant::notifyCarryingStateChanged(Creature* carrier, GameEntity* entity)
{
    if(carrier == nullptr || entity == nullptr || entity->getObjectType() != GameEntityType::itemBagEntity) return;
    Tile* tile = carrier->getPositionTile();
    if(tile == nullptr || tile->getCoveringRoom() != this) return;
    ItemBagEntity* bag = static_cast<ItemBagEntity*>(entity);
    if(bag->getItem() == nullptr) return;
    const ItemInstance copy = *bag->getItem();
    std::unique_ptr<ItemInstance> item(new ItemInstance(copy));
    if(!addGoods(item, getFreeTable(&copy))) return;
    bag->takeItem();
    bag->removeFromGameMap(); bag->deleteYourself();
    if(!copy.mMerchantGoods)
    {
        getSeat()->addMerchantGold(copy.getPrice(getGameMap()) * setting("MerchantBuyShare"));
        recordDeal("Keeper", copy, copy.getPrice(getGameMap()) * setting("MerchantBuyShare"), false);
    }
}

//! \brief Rejects leisure jobs; buying and selling use their dedicated actions.
bool RoomMerchant::hasOpenCreatureSpot(Creature* creature)
{ return false; }
//! \brief Rejects leisure use without changing dedicated buying or selling.
bool RoomMerchant::useRoom(Creature& creature, bool forced)
{ return false; }

//! \brief Counts one potion across the seat's entire merchant stock.
uint32_t RoomMerchant::countPotion(GameMap& map, const Seat* seat, const std::string& id)
{
    uint32_t count = 0;
    for(const MerchantStockEntry& entry : getStock(map, seat))
        if(entry.mGood->mItem.mPotionId == id) ++count;
    return count;
}

//! \brief Counts a potion's sales in the retained merchant history.
uint32_t RoomMerchant::recentPotionSales(GameMap& map, const Seat* seat, const std::string& id)
{
    uint32_t count = 0;
    for(const std::pair<std::string, bool>& sale : seat->getMerchantPotionHistory())
        if(sale.second && sale.first == id) ++count;
    return count;
}

//! \brief Offers enemy table stock to a thief, clearing merchant ownership only on arrival.
std::unique_ptr<ItemInstance> RoomMerchant::stealGoods(Creature& thief, Tile*& target)
{
    target = nullptr;
    Tile* start = thief.getPositionTile();
    if(start == nullptr) return std::unique_ptr<ItemInstance>();
    for(Tile* tile : thief.getVisibleTiles())
    {
        Room* base = tile->getCoveringRoom();
        if(base == nullptr || base->getType() != RoomType::merchant || base->getSeat()->isAlliedSeat(thief.getSeat())) continue;
        RoomMerchant* room = static_cast<RoomMerchant*>(base);
        RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(room->mTileData.at(tile));
        if(data->mGoods.empty() || !thief.getGameMap()->pathExists(&thief, start, tile)) continue;
        const MerchantApproach approach = room->approachTable(thief, tile);
        if(approach == MerchantApproach::failed) continue;
        target = tile;
        if(approach == MerchantApproach::ready)
        {
            room->releaseInteractionPosition(&thief);
            return room->takeGoods(data->mGoods.front().mIndex);
        }
        return std::unique_ptr<ItemInstance>();
    }
    return std::unique_ptr<ItemInstance>();
}

//! \brief Writes goods directly after each tile's normal room data.
void RoomMerchant::exportTileDataToStream(std::ostream& stream, Tile* tile, TileData* base) const
{
    Room::exportTileDataToStream(stream, tile, base);
    if(getGameMap()->isInEditorMode()) stream << '\t' << base->mHP << "\t0";
    const RoomMerchantTileData* data = static_cast<const RoomMerchantTileData*>(base);
    stream << " MerchantGoods " << data->mTable << ' ' << data->mGoods.size();
    for(const MerchantGood& good : data->mGoods)
    { stream << ' ' << good.mIndex << ' '; good.mItem.exportToStream(stream); }
}

//! \brief Restores goods atomically within the tile line and rebuilds their Epic registrations.
bool RoomMerchant::importTileDataFromStream(std::istream& stream, Tile* tile, TileData* base)
{
    if(!Room::importTileDataFromStream(stream, tile, base)) return false;
    const std::streampos position = stream.tellg();
    std::string marker;
    if(!(stream >> marker) || marker != "MerchantGoods") { stream.clear(); stream.seekg(position); return true; }
    RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(base);
    uint32_t count = 0;
    if(!(stream >> data->mTable >> count)) return false;
    for(uint32_t index = 0; index < count; ++index)
    {
        MerchantGood good;
        if(!(stream >> good.mIndex) || !good.mItem.importFromStream(stream)) return false;
        good.mItem.mMerchantGoods = true;
        nextGoodsIndex = std::max(nextGoodsIndex, good.mIndex + 1);
        getGameMap()->registerEpic(good.mItem);
        data->mGoods.push_back(good);
    }
    return true;
}

//! \brief Saves the seat figure position once with the room that currently contains it.
void RoomMerchant::exportToStream(std::ostream& stream) const
{
    Room::exportToStream(stream);
    const MerchantEntity* merchant = getSeat()->getMerchant();
    if(merchant != nullptr && merchant->getPositionTile() != nullptr && merchant->getPositionTile()->getCoveringRoom() == this)
        stream << "Merchant " << merchant->getPosition().x << ' ' << merchant->getPosition().y << '\n';
}

//! \brief Restores crystal table ownership and accepts legacy rooms without a merchant position.
bool RoomMerchant::importFromStream(std::istream& stream)
{
    if(!Room::importFromStream(stream)) return false;
    moveCrystalsToFirstTable();
    const std::streampos position = stream.tellg();
    std::string marker;
    if(!(stream >> marker) || marker != "Merchant") { stream.clear(); stream.seekg(position); return true; }
    if(!(stream >> mMerchantPosition.x >> mMerchantPosition.y)) return false;
    mSavedMerchantPosition = true;
    return true;
}

//! \brief Updates the unique figure, reservations and visible stock after room upkeep.
void RoomMerchant::doUpkeep()
{
    Room::doUpkeep();
    ensureMerchant();
    reserveGoods();
    if(mGoodsChanged || mDisplayedCapacity != tableCapacity(getSeat()))
    {
        mGoodsChanged = false;
        refreshDisplayedGoods();
        Player* player = getSeat()->getPlayer();
        if(player != nullptr && player->getIsHuman() && player->getMerchantWindowOpen()) sendWindow(*getGameMap(), *player);
    }
}

//! \brief Sends a complete owner-only stock and twenty-deal snapshot using stable goods indices.
void RoomMerchant::sendWindow(GameMap& map, Player& player)
{
    Seat* seat = player.getSeat();
    if(seat == nullptr || !player.getIsHuman()) return;
    ServerNotification* notification = new ServerNotification(ServerNotificationType::merchantWindow, &player);
    ODPacket& packet = notification->mPacket;
    packet << seat->getMerchantMargin() << seat->getMerchantMode();
    const std::vector<MerchantStockEntry> stock = getStock(map, seat);
    packet << static_cast<uint32_t>(stock.size());
    for(const MerchantStockEntry& entry : stock)
    { packet << entry.mGood->mIndex; entry.mGood->mItem.exportToPacket(packet); }
    packet << static_cast<uint32_t>(seat->getMerchantHistory().size());
    for(const std::string& entry : seat->getMerchantHistory()) packet << entry;
    ODServer::getSingleton().queueServerNotification(notification);
}

//! \brief Validates owner requests without exposing or purchasing another seat's goods.
bool RoomMerchant::handleRequest(GameMap& map, Player& player, ClientNotificationType type, ODPacket& packet)
{
    Seat* seat = player.getSeat();
    if(seat == nullptr || !player.getIsHuman() || player.getHasLost()) return false;
    if(type == ClientNotificationType::askMerchantWindow)
    {
        bool open = false;
        if(!(packet >> open)) return false;
        player.setMerchantWindowOpen(open);
        if(open) sendWindow(map, player);
        return true;
    }
    if(getForSeat(map, seat) == nullptr) return false;
    if(type == ClientNotificationType::askMerchantSettings)
    {
        int32_t value = 0;
        std::string mode;
        if(!(packet >> value >> mode) || value < 0 || value > setting("MerchantMarginMax")
            || (mode != "fair" && mode != "profit")) return false;
        seat->setMerchantSettings(value, mode);
        for(const MerchantStockEntry& entry : getStock(map, seat))
        {
            RoomMerchantTileData* data = static_cast<RoomMerchantTileData*>(entry.mRoom->mTileData.at(entry.mTile));
            for(MerchantGood& good : data->mGoods) good.mReservedUntil = 0;
        }
        ServerNotification* reply = new ServerNotification(ServerNotificationType::merchantSettings, &player);
        reply->mPacket << value << mode;
        ODServer::getSingleton().queueServerNotification(reply);
        if(player.getMerchantWindowOpen()) sendWindow(map, player);
        return true;
    }
    if(type == ClientNotificationType::askMerchantBuy)
    {
        uint32_t index = 0;
        if(!(packet >> index)) return false;
        for(Room* base : map.getRoomsByTypeAndSeat(RoomType::merchant, seat))
        {
            RoomMerchant* room = static_cast<RoomMerchant*>(base);
            Tile* table = nullptr;
            if(room->findGood(index, table) != nullptr) return room->sellToKeeper(player, index);
        }
    }
    return false;
}

//! \brief Records the owner deal byte and uses the existing profile-resolved Epic notices.
void RoomMerchant::announceDeal(Creature& creature, const ItemInstance& item, uint8_t deal)
{
    const std::string name = item.getDisplayName(creature.getGameMap());
    creature.setLastItemDeal(deal, name);
    Player* player = creature.getSeat() == nullptr ? nullptr : creature.getSeat()->getPlayer();
    if(item.mQuality != Quality::epic || player == nullptr || !player->getIsHuman() || deal == 4) return;
    if(deal == 5) player->notifyCreatureEvent(creature, " found " + name + "!");
    else player->notifyCreatureEvent(creature, " bought " + name);
}
