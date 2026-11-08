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
        {
            setAnimationState("Idle");
            mFacedRoom = false;
        }
        return;
    }
    if(isMoving())
        return;
    if(mIdleTurns > 0.0)
    {
        mIdleTurns -= 1.0;
        if(!mFacedRoom)
        {
            // He stands on a free tile beside the table or shelf and turns to it, never to a wall
            Tile* stop = getPositionTile();
            Ogre::Vector3 facing = Ogre::Vector3::ZERO;
            if(stop != nullptr && mStopTile != nullptr && mStopTile != stop)
                facing = Ogre::Vector3(static_cast<Ogre::Real>(mStopTile->getX() - stop->getX()),
                    static_cast<Ogre::Real>(mStopTile->getY() - stop->getY()), 0);
            if(facing != Ogre::Vector3::ZERO)
                setAnimationState(mAtShelf ? "Idle" : "CountGold", true, facing);
            mFacedRoom = true;
        }
        return;
    }
    mFacedRoom = false;
    Tile* start = getPositionTile();
    Room* room = start == nullptr ? nullptr : start->getCoveringRoom();
    if(room == nullptr || room->getType() != RoomType::merchant || room->getSeat() != getSeat())
    {
        // Only when his tile was taken from the room (sold, absorbed): he stands beside the first table again
        RoomMerchant* home = RoomMerchant::getForSeat(*getGameMap(), getSeat());
        if(home != nullptr && !home->getSalesTables().empty())
        {
            Tile* stand = home->getStandTileBeside(home->getSalesTables().front());
            setPosition((stand != nullptr ? stand : home->getSalesTables().front())->getPosition());
        }
        else if(home != nullptr && home->getCentralTile() != nullptr)
            setPosition(home->getCentralTile()->getPosition());
        return;
    }
    // Decision 866: he also walks to the wall shelves of his room, so he moves with a single table too.
    // Decision 901: the figure stands at the tile centre; he walks only over free floor tiles of his room (no table,
    // no shelf, no wall) and stands on a free tile beside the table or shelf and faces it.
    RoomMerchant* merchantRoom = static_cast<RoomMerchant*>(room);
    std::vector<Tile*> stops(merchantRoom->getSalesTables());
    const std::vector<Tile*> shelves = merchantRoom->getShelfTiles();
    stops.insert(stops.end(), shelves.begin(), shelves.end());

    // Free tiles reachable from where he stands (the start tile itself is always left, also when it is furniture)
    std::queue<Tile*> pending;
    std::map<Tile*, Tile*> previous;
    pending.push(start);
    previous[start] = nullptr;
    static const int DIRECTIONS[][2] = {{1,0},{-1,0},{0,1},{0,-1}};
    while(!pending.empty())
    {
        Tile* current = pending.front();
        pending.pop();
        for(const int (&direction)[2] : DIRECTIONS)
        {
            Tile* next = getGameMap()->getTile(current->getX() + direction[0], current->getY() + direction[1]);
            if(next == nullptr || next->getCoveringRoom() != room || next->isFullTile() || merchantRoom->isFurnitureTile(next) ||
               previous.find(next) != previous.end())
                continue;
            previous[next] = current;
            pending.push(next);
        }
    }

    // Stops with a free tile beside them that he can reach, other than the one he stands beside now
    std::vector<std::pair<Tile*, Tile*>> options;
    for(Tile* stop : stops)
    {
        Tile* stand = nullptr;
        for(int dx = -1; dx <= 1 && stand == nullptr; ++dx)
            for(int dy = -1; dy <= 1 && stand == nullptr; ++dy)
            {
                Tile* next = getGameMap()->getTile(stop->getX() + dx, stop->getY() + dy);
                if((dx != 0 || dy != 0) && next != nullptr && previous.find(next) != previous.end() && next != start)
                    stand = next;
            }
        if(stand != nullptr)
            options.push_back(std::make_pair(stop, stand));
    }
    if(options.empty())
    {
        setAnimationState("Idle");
        mStopTile = nullptr;
        mIdleTurns = Random::Double(10.0, 20.0) * ODApplication::turnsPerSecond;
        return;
    }
    const std::pair<Tile*, Tile*>& choice = options[Random::Uint(0, static_cast<uint32_t>(options.size() - 1))];
    Tile* destination = choice.second;
    mStopTile = choice.first;
    mAtShelf = std::find(shelves.begin(), shelves.end(), mStopTile) != shelves.end();
    std::vector<Ogre::Vector2> path;
    for(Tile* cursor = destination; cursor != nullptr && cursor != start; cursor = previous[cursor])
        path.push_back(cursor->getPosition2d());
    std::reverse(path.begin(), path.end());
    setWalkPath("Walk", mAtShelf ? "Idle" : "CountGold", true, false, path, false);
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
