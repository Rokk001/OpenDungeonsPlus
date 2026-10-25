#include "entities/InfirmaryShamanEntity.h"

#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "game/Seat.h"
#include "game/Player.h"
#include "rooms/RoomInfirmary.h"
#include "rooms/RoomType.h"
#include "ODApplication.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <deque>
#include <map>
#include <vector>

//! \brief Creates an original room figure with independent walking and pose timers.
InfirmaryShamanEntity::InfirmaryShamanEntity(GameMap* map, const std::string& roomName) :
    RenderedMovableEntity(map, roomName, "InfirmaryShaman", 0.0f, false),
    mRoomName(roomName),
    mWalkTurns(interval("InfirmaryShamanWalkMinSeconds", "InfirmaryShamanWalkMaxSeconds")),
    mPoseTurns(interval("InfirmaryShamanPoseMinSeconds", "InfirmaryShamanPoseMaxSeconds")),
    mPoseRemaining(0.0)
{
}

//! \brief Creates the decorative model before receiving its authoritative packet.
InfirmaryShamanEntity::InfirmaryShamanEntity(GameMap* map) :
    RenderedMovableEntity(map), mWalkTurns(0.0), mPoseTurns(0.0), mPoseRemaining(0.0)
{
    setMeshName("InfirmaryShaman");
}

//! \brief Returns the separately routed decorative entity type.
GameEntityType InfirmaryShamanEntity::getObjectType() const
{
    return GameEntityType::infirmaryShamanEntity;
}

//! \brief Samples a configured interval in seconds and retains fractional turns.
double InfirmaryShamanEntity::interval(const std::string& minimumKey, const std::string& maximumKey)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    return Random::Double(config.getRoomConfigDouble(minimumKey), config.getRoomConfigDouble(maximumKey))
        * ODApplication::turnsPerSecond;
}

//! \brief Finds a connected floor path entirely within the owning room.
bool InfirmaryShamanEntity::walkToCot(RoomInfirmary& room)
{
    const std::vector<Tile*> destinations = room.getShamanWalkTargets();
    Tile* start = getPositionTile();
    if(destinations.empty() || start == nullptr)
        return false;
    Tile* destination = destinations[Random::Uint(0, static_cast<uint32_t>(destinations.size() - 1))];
    std::deque<Tile*> pending;
    std::map<Tile*, Tile*> previous;
    pending.push_back(start);
    previous[start] = nullptr;
    while(!pending.empty() && previous.find(destination) == previous.end())
    {
        Tile* tile = pending.front();
        pending.pop_front();
        const int dx[] = {-1, 1, 0, 0};
        const int dy[] = {0, 0, -1, 1};
        for(size_t i = 0; i < sizeof(dx) / sizeof(dx[0]); ++i)
        {
            Tile* next = getGameMap()->getTile(tile->getX() + dx[i], tile->getY() + dy[i]);
            if(next == nullptr || next->isFullTile() || next->getCoveringRoom() != &room
                || previous.find(next) != previous.end())
                continue;
            previous[next] = tile;
            pending.push_back(next);
        }
    }
    if(previous.find(destination) == previous.end())
        return false;
    std::vector<Ogre::Vector2> path;
    for(Tile* tile = destination; tile != start; tile = previous[tile])
        path.push_back(Ogre::Vector2(tile->getX(), tile->getY()));
    std::reverse(path.begin(), path.end());
    if(path.empty())
        return false;
    setWalkPath("Walk", "Idle", true, true, path, false, true);
    return true;
}

//! \brief Entertains the keeper without changing health, mana, movement blockers or targeting.
void InfirmaryShamanEntity::doUpkeep()
{
    if(!getIsOnServerMap())
        return;
    Room* base = getGameMap()->getRoomByName(mRoomName);
    if(base == nullptr || base->getType() != RoomType::infirmary)
    {
        removeFromGameMap();
        deleteYourself();
        return;
    }
    RoomInfirmary& room = *static_cast<RoomInfirmary*>(base);
    setRoomOwner(room.getSeat());
    mWalkTurns -= 1.0;
    mPoseTurns -= 1.0;
    if(mPoseRemaining > 0.0)
    {
        mPoseRemaining -= 1.0;
        if(mPoseRemaining <= 0.0)
            setAnimationState("Idle", true);
        return;
    }
    if(isMoving())
        return;
    if(mPoseTurns <= 0.0)
    {
        const std::vector<Tile*> patients = room.getPatientPositions();
        if(std::find(patients.begin(), patients.end(), getPositionTile()) != patients.end())
        {
            static const char* const poses[] = {
                "Chant", "RattleShake", "HerbSniff", "PotionTaste", "TripOverBucket", "Dance"};
            const std::string pose = poses[Random::Uint(0, sizeof(poses) / sizeof(poses[0]) - 1)];
            setAnimationState(pose, false);
            mPoseRemaining = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryShamanAnimationSeconds")
                * ODApplication::turnsPerSecond;
            if(pose == "RattleShake" && getPositionTile() != nullptr)
                room.playShamanRattle(*getPositionTile());
            mPoseTurns = interval("InfirmaryShamanPoseMinSeconds", "InfirmaryShamanPoseMaxSeconds");
            return;
        }
    }
    if(mWalkTurns <= 0.0)
    {
        if(!walkToCot(room))
            setAnimationState("Idle", true);
        mWalkTurns = interval("InfirmaryShamanWalkMinSeconds", "InfirmaryShamanWalkMaxSeconds");
    }
}

//! \brief Sends the owning room after the ordinary movable state.
void InfirmaryShamanEntity::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(packet, seat);
    packet << mRoomName;
}

//! \brief Reads the room association used by the infirmary window click handler.
void InfirmaryShamanEntity::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    OD_ASSERT_TRUE(packet >> mRoomName);
}

//! \brief Creates the client copy through the same factory path as other room figures.
InfirmaryShamanEntity* InfirmaryShamanEntity::getFromPacket(GameMap* map, ODPacket& packet)
{
    InfirmaryShamanEntity* shaman = new InfirmaryShamanEntity(map);
    shaman->importFromPacket(packet);
    return shaman;
}

//! \brief Keeps clicks on a surviving figure attached to the room after joining rooms.
void InfirmaryShamanEntity::setRoomName(const std::string& roomName)
{
    if(mRoomName == roomName)
        return;
    mRoomName = roomName;
    notifyRoomChanged();
}

//! \brief Keeps the same figure while its room changes owner.
void InfirmaryShamanEntity::setRoomOwner(Seat* seat)
{
    if(getSeat() == seat)
        return;
    setSeat(seat);
    notifyRoomChanged();
}

//! \brief Refreshes the existing figure rather than replacing it on room takeover.
void InfirmaryShamanEntity::notifyRoomChanged()
{
    if(!getIsOnServerMap())
        return;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;
        ServerNotification* notification = new ServerNotification(ServerNotificationType::entitiesRefresh, seat->getPlayer());
        notification->mPacket << static_cast<uint32_t>(1) << getObjectType() << getName();
        exportToPacketForUpdate(notification->mPacket, seat);
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

//! \brief Appends room ownership and the merged room name to the standard refresh.
void InfirmaryShamanEntity::exportToPacketForUpdate(ODPacket& packet, Seat* seat)
{
    RenderedMovableEntity::exportToPacketForUpdate(packet, seat);
    packet << mRoomName << static_cast<int32_t>(getSeat() == nullptr ? -1 : getSeat()->getId());
}

//! \brief Rebinds a visible figure after a room merge or takeover.
void InfirmaryShamanEntity::updateFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::updateFromPacket(packet);
    int32_t seatId;
    OD_ASSERT_TRUE(packet >> mRoomName >> seatId);
    setSeat(seatId < 0 ? nullptr : getGameMap()->getSeatById(seatId));
}
