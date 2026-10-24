#include "entities/ItemBagEntity.h"

#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "render/RenderManager.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"

#include <istream>
#include <ostream>

//! \brief Creates an owned bag using the common two-material mesh.
ItemBagEntity::ItemBagEntity(GameMap* map, std::unique_ptr<ItemInstance> item) :
    RenderedMovableEntity(map, "ItemBag_", "ItemBag", 0.0f, false),
    mItem(std::move(item)), mIdleTurns(0)
{
    if(mItem.get() != nullptr)
        map->registerEpic(*mItem);
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

//! \brief Keeps bags indefinitely and transfers treasury-floor ownership to that treasury's seat.
void ItemBagEntity::doUpkeep()
{
    if(mItem.get() == nullptr)
    {
        removeFromGameMap();
        deleteYourself();
        return;
    }
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

//! \brief Workers move old bags to merchants first and otherwise leave treasury storage undisturbed.
EntityCarryType ItemBagEntity::getEntityCarryType(Creature* carrier)
{
    if(carrier == nullptr || mItem.get() == nullptr || !getIsOnMap() || getCarryLock(*carrier))
        return EntityCarryType::notCarryable;
    const uint32_t idleLimit = static_cast<uint32_t>(ConfigManager::getSingleton().getItemSetting("ItemDrops", "ItemBagIdleTurns"));
    if(mIdleTurns < idleLimit)
        return EntityCarryType::notCarryable;
    Tile* tile = getPositionTile();
    Room* storage = tile == nullptr ? nullptr : tile->getCoveringRoom();
    bool merchantWantsBag = false;
    for(Room* room : getGameMap()->getRoomsByTypeAndSeat(RoomType::merchant, carrier->getSeat()))
    {
        if(room->hasCarryEntitySpot(this) && tile != nullptr && room->getCoveredTile(0) != nullptr &&
            getGameMap()->pathExists(carrier, tile, room->getCoveredTile(0)))
            merchantWantsBag = true;
    }
    if((mItem->mMerchantGoods || (storage != nullptr && storage->getType() == RoomType::treasury)) && !merchantWantsBag)
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
    if(id == "RandomEpic") mItem = getGameMap()->rollItem(Quality::epic);
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
        mItem = std::move(item);
}

//! \brief Creates the usual bag and refreshes its tint and merchant seal.
void ItemBagEntity::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(!getIsOnServerMap())
        RenderManager::getSingleton().rrRefreshItemBag(this);
}
