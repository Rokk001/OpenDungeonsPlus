#include "giftboxes/GiftBoxItem.h"

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/ItemDrops.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "network/ODPacket.h"
#include "render/RenderManager.h"

#include <istream>
#include <ostream>
#include <sstream>

//! \brief Creates a deferred random box or resolves the explicitly supplied item instance.
GiftBoxItem::GiftBoxItem(GameMap* map, const std::string& content) :
    GiftBoxEntity(map, "ItemBox_", "MysteryBox", GiftBoxType::item)
{
    if(content == "RandomEpic" || content == "RandomRare" || content == "RandomCommon")
        mRandomQuality = content;
    else
        mItem = ItemDrops::resolve(*map, content);
}

//! \brief Creates a saved item box while retaining its appended type.
GiftBoxItem::GiftBoxItem(GameMap* map) : GiftBoxEntity(map, GiftBoxType::item) {}

//! \brief Releases only fixed Epics that did not pass to another holder.
GiftBoxItem::~GiftBoxItem()
{
    if(mItem.get() != nullptr && getIsOnServerMap())
        getGameMap()->unregisterEpic(*mItem);
}

//! \brief Treats unresolved random boxes as their requested quality for research gates.
Quality GiftBoxItem::getItemQuality() const
{
    if(!getIsOnServerMap()) return mClientQuality;
    if(mItem.get() != nullptr) return mItem->mQuality;
    if(mRandomQuality == "RandomEpic") return Quality::epic;
    if(mRandomQuality == "RandomRare") return Quality::rare;
    return Quality::common;
}

//! \brief Allows ordinary boxes immediately and requires the specified researched tools for Rare or Epic.
bool GiftBoxItem::canCrack(const Seat& seat) const
{
    const Quality quality = getItemQuality();
    if(quality == Quality::epic) return seat.isSkillDone(SkillType::trapMasterTools);
    if(quality == Quality::rare) return seat.isSkillDone(SkillType::trapFineTools);
    return true;
}

//! \brief Resolves random content only when cracking, respecting map-wide Epic uniqueness.
std::unique_ptr<ItemInstance> GiftBoxItem::crack()
{
    if(mItem.get() == nullptr)
        mItem = ItemDrops::resolve(*getGameMap(), mRandomQuality);
    mRandomQuality.clear();
    return std::move(mItem);
}

//! \brief Leaves stored boxes alone until an eligible own workshop has space for them.
EntityCarryType GiftBoxItem::getEntityCarryType(Creature* carrier)
{
    if(carrier == nullptr || !getIsOnMap())
        return EntityCarryType::notCarryable;
    Tile* tile = getPositionTile();
    Room* storage = tile == nullptr ? nullptr : tile->getCoveringRoom();
    if(storage != nullptr && storage->getType() == RoomType::treasury)
    {
        for(Room* room : getGameMap()->getRoomsByTypeAndSeat(RoomType::workshop, carrier->getSeat()))
            if(room->hasCarryEntitySpot(this) && room->getCoveredTile(0) != nullptr &&
                getGameMap()->pathExists(carrier, tile, room->getCoveredTile(0))) return EntityCarryType::giftBox;
        return EntityCarryType::notCarryable;
    }
    return EntityCarryType::giftBox;
}

//! \brief Writes the fixed instance or deferred token following the standard gift-box placement.
void GiftBoxItem::exportToStream(std::ostream& stream) const
{
    GiftBoxEntity::exportToStream(stream);
    if(mItem.get() != nullptr) mItem->exportToStream(stream);
    else stream << mRandomQuality;
}

//! \brief Reads one saved content record and rebuilds registration for fixed Epics.
bool GiftBoxItem::importFromStream(std::istream& stream)
{
    if(!GiftBoxEntity::importFromStream(stream))
        return false;
    std::string id;
    if(!(stream >> id))
        return false;
    if(id == "RandomEpic" || id == "RandomRare" || id == "RandomCommon")
    {
        mRandomQuality = id;
        return true;
    }
    mItem.reset(new ItemInstance);
    if(!mItem->importFromStream(stream, id))
        return false;
    getGameMap()->registerEpic(*mItem);
    return true;
}

//! \brief Sends the appearance quality without revealing the item to the client.
void GiftBoxItem::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    GiftBoxEntity::exportToPacket(packet, seat);
    packet << getItemQuality();
}

//! \brief Reads the known item-box quality after its normal placement.
void GiftBoxItem::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    Quality quality = Quality::common;
    if((packet >> quality) && static_cast<int32_t>(quality) >= 0 && static_cast<int32_t>(quality) <= static_cast<int32_t>(Quality::epic))
        mClientQuality = quality;
}

//! \brief Reuses the standard quality tint while retaining the box's own materials.
void GiftBoxItem::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(!getIsOnServerMap()) RenderManager::getSingleton().rrRefreshItemBagAppearance(this, mClientQuality, false);
}
