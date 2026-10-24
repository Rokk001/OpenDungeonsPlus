#include "entities/MerchantEntity.h"

#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "rooms/RoomMerchant.h"
#include "utils/Random.h"
#include "ODApplication.h"

#include <algorithm>
#include <map>
#include <queue>

//! \brief Creates one hooded merchant for the seat at a valid table position.
MerchantEntity::MerchantEntity(GameMap* map, Seat* seat, const Ogre::Vector3& position) :
    RenderedMovableEntity(map, "Merchant", "Merchant", 0.0f, false),
    mIdleTurns(0.0), mDealTurns(0.0)
{
    setSeat(seat);
    mPosition = position;
}

//! \brief Initialises an empty figure for the existing rendered entity packet loader.
MerchantEntity::MerchantEntity(GameMap* map) :
    RenderedMovableEntity(map), mIdleTurns(0.0), mDealTurns(0.0)
{}

//! \brief Drops only this figure's weak reference on its seat.
MerchantEntity::~MerchantEntity()
{
    if(getSeat() != nullptr && getSeat()->getMerchant() == this)
        getSeat()->setMerchant(nullptr);
}

//! \brief Uses the appended merchant entity packet type.
GameEntityType MerchantEntity::getObjectType() const
{ return GameEntityType::merchantEntity; }

//! \brief Registers normal movement and establishes the single figure of the seat.
void MerchantEntity::addToGameMap(GameMap* map)
{
    RenderedMovableEntity::addToGameMap(map);
    if(getIsOnServerMap() && getSeat() != nullptr)
        getSeat()->setMerchant(this);
}

//! \brief Removes the figure and its weak seat reference.
void MerchantEntity::removeFromGameMap(GameMap* map)
{
    if(getSeat() != nullptr && getSeat()->getMerchant() == this)
        getSeat()->setMerchant(nullptr);
    RenderedMovableEntity::removeFromGameMap(map);
}

//! \brief Reuses the standard rendered-entity walking speed.
double MerchantEntity::getMoveSpeed() const
{ return RenderedMovableEntity::getMoveSpeed(); }

//! \brief Marks the figure as scenery rather than a combat target.
bool MerchantEntity::isAttackable(Tile* tile, Seat* seat) const
{ return false; }

//! \brief Keeps the non-creature merchant out of the keeper hand.
bool MerchantEntity::tryPickup(Seat* seat)
{ return false; }

//! \brief Interrupts walking to play the fixed two-second deal pose.
void MerchantEntity::onDeal()
{
    static const double DEAL_SECONDS = 2.0;
    mDealTurns = DEAL_SECONDS * ODApplication::turnsPerSecond;
    clearDestinations("RubHands", true, false);
}

//! \brief Walks along a room-only route and counts gold for ten to twenty seconds at a table.
void MerchantEntity::doUpkeep()
{
    if(!getIsOnServerMap())
        return;
    if(RoomMerchant::getForSeat(*getGameMap(), getSeat()) == nullptr)
    {
        removeFromGameMap();
        deleteYourself();
        return;
    }
    if(mDealTurns > 0.0)
    {
        mDealTurns -= 1.0;
        if(mDealTurns <= 0.0)
            setAnimationState("Idle");
        return;
    }
    if(isMoving())
        return;
    if(mIdleTurns > 0.0)
    {
        mIdleTurns -= 1.0;
        return;
    }
    Tile* start = getPositionTile();
    Room* room = start == nullptr ? nullptr : start->getCoveringRoom();
    if(room == nullptr || room->getType() != RoomType::merchant || room->getSeat() != getSeat())
    {
        RoomMerchant* home = RoomMerchant::getForSeat(*getGameMap(), getSeat());
        if(home != nullptr && home->getCentralTile() != nullptr)
            setPosition(home->getCentralTile()->getPosition());
        return;
    }
    const std::vector<Tile*>& tables = static_cast<RoomMerchant*>(room)->getSalesTables();
    if(tables.empty()) { setAnimationState("Idle"); return; }
    Tile* destination = tables[Random::Uint(0, static_cast<uint32_t>(tables.size() - 1))];
    std::queue<Tile*> pending;
    std::map<Tile*, Tile*> previous;
    pending.push(start);
    previous[start] = nullptr;
    static const int DIRECTIONS[][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    while(!pending.empty() && previous.find(destination) == previous.end())
    {
        Tile* current = pending.front();
        pending.pop();
        for(const int (&direction)[2] : DIRECTIONS)
        {
            Tile* next = getGameMap()->getTile(current->getX() + direction[0], current->getY() + direction[1]);
            if(next == nullptr || next->getCoveringRoom() != room || next->isFullTile() || previous.find(next) != previous.end())
                continue;
            previous[next] = current;
            pending.push(next);
        }
    }
    if(previous.find(destination) != previous.end())
    {
        std::vector<Ogre::Vector2> path;
        for(Tile* cursor = destination; cursor != nullptr && cursor != start; cursor = previous[cursor])
            path.push_back(cursor->getPosition2d());
        std::reverse(path.begin(), path.end());
        setWalkPath("Walk", "CountGold", true, false, path, false);
    }
    static const double IDLE_SECONDS_MIN = 10.0;
    static const double IDLE_SECONDS_MAX = 20.0;
    mIdleTurns = Random::Double(IDLE_SECONDS_MIN, IDLE_SECONDS_MAX) * ODApplication::turnsPerSecond;
}

//! \brief Loads the ordinary rendered packet fields of a client merchant.
MerchantEntity* MerchantEntity::loadFromPacket(GameMap* map, ODPacket& packet)
{
    MerchantEntity* merchant = new MerchantEntity(map);
    merchant->importFromPacket(packet);
    return merchant;
}
