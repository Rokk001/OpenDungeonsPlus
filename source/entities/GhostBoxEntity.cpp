#include "entities/GhostBoxEntity.h"
#include "entities/GameEntityType.h"
#include "entities/GhostEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "ODApplication.h"
#include <iomanip>
#include <limits>
#include <memory>
#include <utility>

//! \brief Initializes an empty capture box using the original box mesh.
GhostBoxEntity::GhostBoxEntity(GameMap* map) :
    RenderedMovableEntity(map, "GhostBox", "GhostBox", 0.0f, false), mOpenTurns(0.0)
{
}

//! \brief Takes ownership of the supplied boxed spirit identities.
GhostBoxEntity::GhostBoxEntity(GameMap* map, const std::vector<std::string>& ghosts) : GhostBoxEntity(map)
{
    mGhostNames = ghosts;
}

//! \brief Identifies boxes in the common movable-entity registry.
GameEntityType GhostBoxEntity::getObjectType() const { return GameEntityType::ghostBoxEntity; }

//! \brief Transfers box contents without resuming any contained ghost lifetime.
std::vector<std::string> GhostBoxEntity::takeGhostNames()
{
    std::vector<std::string> ghosts;
    ghosts.swap(mGhostNames);
    mAssignedHunter.clear();
    return ghosts;
}

//! \brief Synchronizes the hunter reservation with observing clients.
void GhostBoxEntity::setAssignedHunter(const std::string& hunter)
{
    mAssignedHunter = hunter;
    refresh();
}

//! \brief Sends the current continuation through the existing entity-refresh packet.
void GhostBoxEntity::refresh()
{
    if(!getIsOnServerMap())
        return;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;
        ServerNotification* notice = new ServerNotification(ServerNotificationType::entitiesRefresh, seat->getPlayer());
        notice->mPacket << uint32_t(1) << getObjectType() << getName();
        exportToPacketForUpdate(notice->mPacket, seat);
        ODServer::getSingleton().queueServerNotification(notice);
    }
}

//! \brief Opens an expired lying box and resumes every contained ghost at its last box position.
void GhostBoxEntity::doUpkeep()
{
    if(!getIsOnServerMap() || !getIsOnMap())
        return;
    mOpenTurns += 1.0;
    if(mOpenTurns < ConfigManager::getSingleton().getRoomConfigDouble("GhostBoxOpenSeconds") * ODApplication::turnsPerSecond)
        return;
    Tile* tile = getPositionTile();
    if(tile != nullptr)
        for(Seat* seat : tile->getSeatsWithVision())
        {
            if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
                continue;
            ServerNotification* notice = new ServerNotification(ServerNotificationType::playSpatialSound, seat->getPlayer());
            notice->mPacket << std::string("Rooms/GhostRoom/BoxSnap") << tile->getX() << tile->getY();
            ODServer::getSingleton().queueServerNotification(notice);
        }
    for(const std::string& name : mGhostNames)
    {
        GhostEntity* ghost = static_cast<GhostEntity*>(getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity, name));
        if(ghost == nullptr)
            continue;
        ghost->teleport(getPosition());
        ghost->setAssignedHunter("");
        ghost->setState(GhostState::floating);
    }
    mGhostNames.clear();
    removeFromGameMap();
    deleteYourself();
}

//! \brief Resolves saved spirit identities only after the complete map exists.
void GhostBoxEntity::restoreInitialEntityState()
{
    RenderedMovableEntity::restoreInitialEntityState();
    if(!getIsOnServerMap())
        return;
    for(const std::string& name : mGhostNames)
    {
        GhostEntity* ghost = static_cast<GhostEntity*>(getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity, name));
        if(ghost != nullptr)
        {
            ghost->setState(GhostState::boxed);
            ghost->setAssignedHunter(mAssignedHunter);
        }
    }
}

//! \brief Writes the exact planned columns followed by optional reservation data.
void GhostBoxEntity::exportToStream(std::ostream& stream) const
{
    const std::streamsize precision = stream.precision();
    stream << std::setprecision(std::numeric_limits<double>::max_digits10);
    stream << getName() << '\t' << mPosition.x << '\t' << mPosition.y << '\t' << mOpenTurns << '\t' << mGhostNames.size();
    for(const std::string& name : mGhostNames)
        stream << '\t' << name;
    stream << " [BoxRuntime] " << (getSeat() == nullptr ? -1 : getSeat()->getId()) << ' '
        << (mAssignedHunter.empty() ? "none" : mAssignedHunter) << " [/BoxRuntime]";
    stream.precision(precision);
}

//! \brief Reads box contents and preserves their fractional opening counter.
bool GhostBoxEntity::importFromStream(std::istream& stream)
{
    uint32_t count;
    if(!(stream >> mName >> mPosition.x >> mPosition.y >> mOpenTurns >> count))
        return false;
    mPosition.z = 0.0f;
    mGhostNames.clear();
    for(uint32_t index = 0; index < count; ++index)
    {
        std::string name;
        if(!(stream >> name))
            return false;
        mGhostNames.push_back(name);
    }
    std::string tag;
    if(stream >> tag)
    {
        int32_t seatId;
        if(tag != "[BoxRuntime]" || !(stream >> seatId >> mAssignedHunter >> tag) || tag != "[/BoxRuntime]")
            return false;
        setSeat(getGameMap()->getSeatById(seatId));
        if(mAssignedHunter == "none")
            mAssignedHunter.clear();
    }
    else
        stream.clear();
    return true;
}

//! \brief Sends normal movable placement followed by all box continuation fields.
void GhostBoxEntity::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(packet, seat);
    packet << mOpenTurns << mAssignedHunter << static_cast<uint32_t>(mGhostNames.size());
    for(const std::string& name : mGhostNames)
        packet << name;
}

//! \brief Reads placement and the complete box continuation on a client.
void GhostBoxEntity::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    uint32_t count;
    OD_ASSERT_TRUE(packet >> mOpenTurns >> mAssignedHunter >> count);
    mGhostNames.clear();
    for(uint32_t index = 0; index < count; ++index)
    {
        std::string name;
        OD_ASSERT_TRUE(packet >> name);
        mGhostNames.push_back(name);
    }
}

//! \brief Appends current opening time and reservation to the common entity update.
void GhostBoxEntity::exportToPacketForUpdate(ODPacket& packet, Seat* seat)
{
    RenderedMovableEntity::exportToPacketForUpdate(packet, seat);
    packet << mOpenTurns << mAssignedHunter;
}

//! \brief Applies the current opening time and reservation from the server.
void GhostBoxEntity::updateFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::updateFromPacket(packet);
    OD_ASSERT_TRUE(packet >> mOpenTurns >> mAssignedHunter);
}

//! \brief Returns a completely parsed box or releases the failed partial record.
GhostBoxEntity* GhostBoxEntity::loadFromStream(GameMap* map, std::istream& stream)
{
    std::unique_ptr<GhostBoxEntity> box(new GhostBoxEntity(map));
    if(!box->importFromStream(stream))
        return nullptr;
    return box.release();
}

//! \brief Creates the client box from its complete creation packet.
GhostBoxEntity* GhostBoxEntity::loadFromPacket(GameMap* map, ODPacket& packet)
{
    GhostBoxEntity* box = new GhostBoxEntity(map);
    box->importFromPacket(packet);
    return box;
}
