#include "entities/ItemBagEntity.h"

#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/ItemDrops.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "render/RenderManager.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <istream>
#include <ostream>

namespace
{
// Meshes of the ghost room goods. Placeholders until the own models exist: the cauldron fill for ectoplasm and the
// soul crystal for the mana crystal; the research book keeps the look of today's Grimoire.
const std::string ECTOPLASM_MESH = "GhostCauldronFill";
const std::string MANA_CRYSTAL_MESH = "SoulCrystal";
const std::string RESEARCH_BOOK_MESH = "Grimoire";
const std::string LEVEL_CRYSTAL_MESH = "SoulCrystal";
}

//! \brief Names the own mesh of crystals and ghost room goods; ordinary items use the tinted bag.
std::string ItemBagEntity::getSpecialMesh(const ItemInstance& item)
{
    if(item.mSoulCrystal) return LEVEL_CRYSTAL_MESH;
    switch(item.mGhostItem)
    {
        case GhostItem::ectoplasm: return ECTOPLASM_MESH;
        case GhostItem::manaCrystal: return MANA_CRYSTAL_MESH;
        case GhostItem::researchBook: return RESEARCH_BOOK_MESH;
        default: return std::string();
    }
}

//! \brief Ectoplasm goes to a ghost room, a mana crystal to the heart, a book to a library, all else to the merchant.
RoomType ItemBagEntity::getUseRoomType(const ItemInstance& item)
{
    switch(item.mGhostItem)
    {
        case GhostItem::ectoplasm: return RoomType::ghostRoom;
        case GhostItem::manaCrystal: return RoomType::dungeonTemple;
        case GhostItem::researchBook: return RoomType::library;
        default: return RoomType::merchant;
    }
}

//! \brief Checks the rooms of the use type of the carrier's keeper that take the bag now and can be reached.
bool ItemBagEntity::isWantedByUseRoom(Creature& carrier)
{
    Tile* tile = getPositionTile();
    if(mItem.get() == nullptr || tile == nullptr)
        return false;
    for(Room* room : getGameMap()->getRoomsByTypeAndSeat(getUseRoomType(*mItem), carrier.getSeat()))
    {
        if(room->hasCarryEntitySpot(this) && room->getCoveredTile(0) != nullptr &&
            getGameMap()->pathExists(&carrier, tile, room->getCoveredTile(0)))
            return true;
    }
    return false;
}

//! \brief Creates a crystal or ghost good mesh, or the common two-material bag for the owned instance.
ItemBagEntity::ItemBagEntity(GameMap* map, std::unique_ptr<ItemInstance> item) :
    RenderedMovableEntity(map, "ItemBag_", "ItemBag", 0.0f, false),
    mItem(std::move(item)), mIdleTurns(0)
{
    if(mItem.get() != nullptr)
    {
        if(!getSpecialMesh(*mItem).empty()) setMeshName(getSpecialMesh(*mItem));
        map->registerEpic(*mItem);
    }
}

//! \brief Creates an empty bag for a complete saved or network record.
ItemBagEntity::ItemBagEntity(GameMap* map) : RenderedMovableEntity(map), mIdleTurns(0) {}

//! \brief Unregisters only items that were not transferred to another holder.
ItemBagEntity::~ItemBagEntity()
{
    if(mItem.get() != nullptr && getIsOnServerMap())
        getGameMap()->unregisterEpic(*mItem);
}

//! \brief Returns the appended entity type.
GameEntityType ItemBagEntity::getObjectType() const { return GameEntityType::itemBagEntity; }

//! \brief Transfers the live instance to another holder on the same map.
std::unique_ptr<ItemInstance> ItemBagEntity::takeItem() { return std::move(mItem); }

//! \brief Ages ground bags and claims treasury ownership; item transfers own consumed-bag removal.
void ItemBagEntity::doUpkeep()
{
    if(!getIsOnMap())
        return;
    ++mIdleTurns;
    Tile* tile = getPositionTile();
    Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
    if(room != nullptr && room->getType() == RoomType::treasury)
        setSeat(room->getSeat());
}

//! \brief Sealed goods cannot enter the keeper's hand; an owned bag must be visible.
bool ItemBagEntity::tryPickup(Seat* seat)
{
    if(mItem.get() == nullptr || mItem->mMerchantGoods || !getIsOnMap() || seat == nullptr)
        return false;
    Tile* tile = getPositionTile();
    return tile != nullptr && (getGameMap()->isInEditorMode() ||
        (getSeat() == seat && seat->hasVisionOnTile(tile)));
}

//! \brief Tests the same visible, non-solid ground rule for every bag drop.
bool ItemBagEntity::tryDrop(Seat* seat, Tile* tile)
{
    return seat != nullptr && tile != nullptr && !tile->isFullTile() &&
        (getGameMap()->isInEditorMode() || seat->hasVisionOnTile(tile));
}

//! \brief Places the bag before Player sends its drop notification and offers any keeper gift.
void ItemBagEntity::drop(const Ogre::Vector3& position)
{
    RenderedMovableEntity::drop(position);
    mIdleTurns = 0;
}

//! \brief Workers move old bags to their use room first and otherwise leave treasury storage undisturbed.
//! Ectoplasm, mana crystals and research books, and every ghost good in a ghost room, are carried at once.
EntityCarryType ItemBagEntity::getEntityCarryType(Creature* carrier)
{
    if(carrier == nullptr || mItem.get() == nullptr || !getIsOnMap() || getCarryLock(*carrier))
        return EntityCarryType::notCarryable;
    Tile* tile = getPositionTile();
    Room* storage = tile == nullptr ? nullptr : tile->getCoveringRoom();
    const bool inGhostRoom = storage != nullptr && storage->getType() == RoomType::ghostRoom;
    const uint32_t idleLimit = static_cast<uint32_t>(ConfigManager::getSingleton().getItemSetting("ItemDrops", "ItemBagIdleTurns"));
    if(mIdleTurns < idleLimit && mItem->mGhostItem == GhostItem::none && !(mItem->mSoulCrystal && inGhostRoom))
        return EntityCarryType::notCarryable;
    // A research book on a library shelf stays there until a researcher opens it
    if(mItem->mGhostItem == GhostItem::researchBook && storage != nullptr && storage->getType() == RoomType::library)
        return EntityCarryType::notCarryable;
    if((mItem->mMerchantGoods || (storage != nullptr && storage->getType() == RoomType::treasury)) && !isWantedByUseRoom(*carrier))
        return EntityCarryType::notCarryable;
    return EntityCarryType::itemBag;
}

//! \brief Removes ground occupancy while a worker carries this bag.
void ItemBagEntity::notifyEntityCarryOn(Creature* carrier) { removeEntityFromPositionTile(); }
//! \brief Restores ground occupancy at the delivered position.
void ItemBagEntity::notifyEntityCarryOff(const Ogre::Vector3& position) { setPosition(position); addEntityToPositionTile(); }

//! \brief Reads and registers a bag only after a complete level record was parsed.
ItemBagEntity* ItemBagEntity::loadFromStream(GameMap* map, std::istream& stream)
{
    std::unique_ptr<ItemBagEntity> bag(new ItemBagEntity(map));
    if(!bag->importFromStream(stream))
        return nullptr;
    return bag.release();
}

//! \brief Creates the client's representation from the authoritative instance payload.
ItemBagEntity* ItemBagEntity::loadFromPacket(GameMap* map, ODPacket& packet)
{
    ItemBagEntity* bag = new ItemBagEntity(map);
    bag->importFromPacket(packet);
    return bag;
}

//! \brief Writes the base placement and the unstacked contained instance.
void ItemBagEntity::exportToStream(std::ostream& stream) const
{
    RenderedMovableEntity::exportToStream(stream);
    mItem->exportToStream(stream);
}

//! \brief Reads either a rolled instance or one of the three random-quality level tokens.
bool ItemBagEntity::importFromStream(std::istream& stream)
{
    if(!RenderedMovableEntity::importFromStream(stream))
        return false;
    std::string id;
    if(!(stream >> id))
        return false;
    const bool randomBag = id == "RandomEpic" || id == "RandomRare" || id == "RandomCommon";
    // A random item bag of a map holds one of the three ghost products instead of its item with GhostProductBoxChance
    if(randomBag && !getGameMap()->isInEditorMode() &&
        Random::Double(0.0, 1.0) < ConfigManager::getSingleton().getRoomConfigDouble("GhostProductBoxChance"))
        mItem = ItemDrops::randomGhostProduct(Random::Double(0.0, 1.0));
    else if(id == "RandomEpic") mItem = getGameMap()->rollItem(Quality::epic);
    else if(id == "RandomRare") mItem = getGameMap()->rollItem(Quality::rare);
    else if(id == "RandomCommon") mItem = getGameMap()->rollItem(Quality::common);
    else
    {
        mItem.reset(new ItemInstance);
        if(!mItem->importFromStream(stream, id))
            return false;
    }
    if(mItem.get() == nullptr)
        return false;
    if(!getSpecialMesh(*mItem).empty()) setMeshName(getSpecialMesh(*mItem));
    getGameMap()->registerEpic(*mItem);
    return true;
}

//! \brief Sends the complete contained item after normal movable-entity placement.
void ItemBagEntity::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(packet, seat);
    mItem->exportToPacket(packet);
}

//! \brief Reads the client copy's contained instance transactionally.
void ItemBagEntity::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    std::unique_ptr<ItemInstance> item(new ItemInstance);
    if(item->importFromPacket(packet))
    {
        mItem = std::move(item);
        if(!getSpecialMesh(*mItem).empty()) setMeshName(getSpecialMesh(*mItem));
    }
}

//! \brief Creates the contained item mesh and applies tint and seals only to ordinary bags.
void ItemBagEntity::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(!getIsOnServerMap() && mItem.get() != nullptr && getSpecialMesh(*mItem).empty())
        RenderManager::getSingleton().rrRefreshItemBag(this);
}
