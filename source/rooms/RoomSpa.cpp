/*
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "rooms/RoomSpa.h"

#include "creatureaction/CreatureActionUseRoom.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/PoolAttendantEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "gamemap/RoomObjectBounds.h"
#include "network/CosmeticEvent.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomTavern.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <istream>
#include <ostream>
#include <sstream>
#include <string>

const std::string RoomSpaName = "Spa";
const std::string RoomSpaNameDisplay = "Lava spa";
const RoomType RoomSpa::mRoomType = RoomType::spa;
const TileVisual RoomSpa::mRoomVisual = TileVisual::spaRoom;

namespace
{
//! \brief Mesh name of the mud on a pool tile (the name used by the navigation catalog).
const std::string& SPA_POOL_MESH = RoomObjectPath::SPA_POOL_MESH;
//! \brief Mesh name of the stone edge of the pool (the name used by the navigation catalog).
const std::string& SPA_RIM_MESH = RoomObjectPath::SPA_RIM_MESH;
//! \brief Mesh name of the pool attendant's chair.
const std::string SPA_CHAIR_MESH = "SpaChair";
//! \brief Mesh name of the springboard.
const std::string SPA_SPRINGBOARD_MESH = "SpaSpringboard";
//! \brief Particle effect script of the steam above a pool tile.
const std::string SPA_STEAM_EFFECT = "SpaSteam";
//! \brief Particle effect script of the mud splash of a landing.
const std::string SPA_SPLASH_EFFECT = "SpaMudSplash";
//! \brief Turns the steam effect of a pool tile runs before it is renewed.
const uint32_t SPA_STEAM_TURNS = 5040;
//! \brief Turns the mud splash effect of a landing runs (its duration is half a second).
const int32_t SPA_SPLASH_TURNS = 1;
//! \brief Sound family of the splash of a landing.
const std::string SOUND_SPLASH = "Rooms/Spa/Splash";
//! \brief Angles (degrees) of an object whose edge or back is on the side +y, -x, -y and +x of its tile (the same
//! convention as the other rooms with wall furniture: the engine turns counter-clockwise).
const double OBJECT_ANGLE_SIDE_TOP = 0.0;
const double OBJECT_ANGLE_SIDE_LEFT = 90.0;
const double OBJECT_ANGLE_SIDE_BOTTOM = 180.0;
const double OBJECT_ANGLE_SIDE_RIGHT = 270.0;
//! \brief Angle of the chair (it faces the pool, which lies below it) and of the springboard (it faces the pool above it).
const double CHAIR_ANGLE = 180.0;
const double SPRINGBOARD_ANGLE = 0.0;
//! \brief Largest distance (tiles) at which a bather counts as standing in the middle of its block.
const double CENTRE_EPSILON = 0.01;
//! \brief Angle differences smaller than this (degrees) count as the same angle.
const double ANGLE_EPSILON = 0.5;
//! \brief Line of the room stream with who pays for the bath (0 = keeper, 1 = creature).
const std::string STREAM_TAG_PAYER = "SpaPayer";
//! \brief Line of the room stream with the number of bathers; one line per bather follows.
const std::string STREAM_TAG_BATHERS = "SpaBathers";
//! \brief Line of the room stream with the pool attendant: x, y, state, turns left, turns until his next jump, whether
//! he holds a pool tile and its x and y (everything after the turns left is optional).
const std::string STREAM_TAG_ATTENDANT = "PoolAttendant";

//! \brief Reads a value of the [Tavern] block of global.cfg.
//! \param key The key of the value.
double getTavernValue(const std::string& key)
{
    return ConfigManager::getSingleton().getTavernConfigDouble(key);
}

//! \brief The name of a bather state in the room stream.
//! \param state The state.
std::string batherStateToString(SpaBatherState state)
{
    switch(state)
    {
        case SpaBatherState::reserved:
            return "reserved";
        case SpaBatherState::jumping:
            return "jumping";
        case SpaBatherState::bathing:
            return "bathing";
    }
    return "reserved";
}

//! \brief Reads the name of a bather state from the room stream.
//! \param token The name.
//! \param state Set to the state when the name is known.
//! \return False for an unknown name.
bool batherStateFromString(const std::string& token, SpaBatherState& state)
{
    if(token == "reserved")
        state = SpaBatherState::reserved;
    else if(token == "jumping")
        state = SpaBatherState::jumping;
    else if(token == "bathing")
        state = SpaBatherState::bathing;
    else
        return false;

    return true;
}

//! \brief Writes the line of the room stream with the pool attendant.
//! \param os The stream.
//! \param save The state of the attendant.
void writeAttendantLine(std::ostream& os, const PoolAttendantSave& save)
{
    os << STREAM_TAG_ATTENDANT << " " << save.mX << " " << save.mY << " " << PoolAttendantStateNames::toString(save.mState)
       << " " << save.mTurnsLeft << " " << save.mCannonballTurnsLeft << " " << (save.mHasPlace ? 1 : 0) << " "
       << save.mPlaceX << " " << save.mPlaceY << std::endl;
}

//! \brief True when the block contains the tile position.
//! \param block The block.
//! \param x The x of the tile.
//! \param y The y of the tile.
bool blockContains(const SpaBlock& block, int32_t x, int32_t y)
{
    return (x >= block.mX) && (x < block.mX + block.mWidth) && (y >= block.mY) && (y < block.mY + block.mHeight);
}

//! \brief Builds, prices and loads lava spas; registered for RoomType::spa.
class RoomSpaFactory : public RoomFactory
{
    RoomType getRoomType() const override
    { return RoomSpa::mRoomType; }

    TileVisual getVisualType() const override
    { return RoomSpa::mRoomVisual; }

    const std::string& getName() const override
    { return RoomSpaName; }

    const std::string& getNameReadable() const override
    { return RoomSpaNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getRoomConfigInt32("SpaCostPerTile"); }

    void checkBuildRoom(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefault(gameMap, RoomSpa::mRoomType, inputManager, inputCommand);
    }

    //! \brief True when the new tiles together with the spa tiles of the seat they join hold a full block of
    //! SpaMinRoomSide x SpaMinRoomSide tiles.
    //! \param gameMap The map.
    //! \param seat The seat that builds.
    //! \param tiles The new tiles.
    bool hasMinimumSize(GameMap* gameMap, Seat* seat, const std::vector<Tile*>& tiles) const
    {
        SpaTileSet resulting;
        for(Tile* tile : tiles)
            resulting.insert(std::make_pair(tile->getX(), tile->getY()));

        // The own spas that border the new tiles (or each other through the new tiles) are part of the room
        std::vector<Room*> spas = gameMap->getRoomsByTypeAndSeat(RoomType::spa, seat);
        bool grown = true;
        while(grown)
        {
            grown = false;
            for(Room* spa : spas)
            {
                bool joins = false;
                bool alreadyIn = true;
                for(Tile* tile : spa->getCoveredTiles())
                {
                    const std::pair<int32_t, int32_t> position(tile->getX(), tile->getY());
                    if(resulting.find(position) == resulting.end())
                        alreadyIn = false;

                    static const int32_t SIDE_DX[] = { 1, -1, 0, 0 };
                    static const int32_t SIDE_DY[] = { 0, 0, 1, -1 };
                    static const uint32_t NB_SIDES = 4;
                    for(uint32_t i = 0; i < NB_SIDES; ++i)
                    {
                        if(resulting.find(std::make_pair(position.first + SIDE_DX[i], position.second + SIDE_DY[i])) != resulting.end())
                            joins = true;
                    }
                }

                if(alreadyIn || !joins)
                    continue;

                for(Tile* tile : spa->getCoveredTiles())
                    resulting.insert(std::make_pair(tile->getX(), tile->getY()));
                grown = true;
            }
        }

        return SpaLayout::hasSquareBlock(resulting,
            static_cast<int32_t>(ConfigManager::getSingleton().getRoomConfigUInt32("SpaMinRoomSide")));
    }

    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet))
            return false;

        // A spa needs room for a pool: the building is refused (and nothing is paid) when the room that results has no
        // full block of SpaMinRoomSide x SpaMinRoomSide tiles
        if(!hasMinimumSize(gameMap, player->getSeat(), tiles))
        {
            ServerNotification* serverNotification = new ServerNotification(ServerNotificationType::chatServer, player);
            std::string msg = "A lava spa needs at least " +
                Helper::toString(ConfigManager::getSingleton().getRoomConfigUInt32("SpaMinRoomSide")) + "x" +
                Helper::toString(ConfigManager::getSingleton().getRoomConfigUInt32("SpaMinRoomSide")) + " tiles.";
            serverNotification->mPacket << msg << EventShortNoticeType::genericGameInfo;
            ODServer::getSingleton().queueServerNotification(serverNotification);
            return false;
        }

        int32_t pricePerTarget = RoomManager::costPerTile(RoomSpa::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        RoomSpa* room = new RoomSpa(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }

    void checkBuildRoomEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefaultEditor(gameMap, RoomSpa::mRoomType, inputManager, inputCommand);
    }

    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        RoomSpa* room = new RoomSpa(gameMap);
        return buildRoomDefaultEditor(gameMap, room, packet);
    }

    //! \brief Creates an empty room of this type, for a room that has to be split in two.
    Room* createRoom(GameMap* gameMap) const override
    { return new RoomSpa(gameMap); }

    Room* getRoomFromStream(GameMap* gameMap, std::istream& is) const override
    {
        RoomSpa* room = new RoomSpa(gameMap);
        if(!Room::importRoomFromStream(*room, is))
        {
            OD_LOG_ERR("Error while building a room from the stream");
        }
        return room;
    }

    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
        int32_t pricePerTarget = RoomManager::costPerTile(RoomSpa::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
                return false;
        RoomSpa* room = new RoomSpa(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }
};

// Register the factory
static RoomRegister reg(new RoomSpaFactory);
}

RoomSpa::RoomSpa(GameMap* gameMap) :
    Room(gameMap),
    mPayer(SpaPayer::keeper),
    mAttendant(nullptr),
    mPendingAttendant()
{
    setMeshName("Room");
}

bool RoomSpa::isPoolTile(const Tile* tile)
{
    if(tile == nullptr)
        return false;

    const Room* room = tile->getCoveringRoom();
    if((room == nullptr) || (room->getType() != RoomType::spa))
        return false;

    GameMap* gameMap = tile->getGameMap();
    for(int32_t dx = -1; dx <= 1; ++dx)
    {
        for(int32_t dy = -1; dy <= 1; ++dy)
        {
            const Tile* neighbour = gameMap->getTile(tile->getX() + dx, tile->getY() + dy);
            if((neighbour == nullptr) || (neighbour->getCoveringRoom() != room))
                return false;
        }
    }

    return true;
}

void RoomSpa::sendBathFinished(Creature& creature)
{
    // The post "Relaxed" is written on the client of the keeper of the creature: the cosmetic tavern event of the kind
    // relaxed carries it (no thought bubble belongs to this kind)
    RoomTavern::sendTavernEvent(creature, static_cast<int32_t>(CosmeticTavernKind::relaxed), nullptr);
}

SpaTileSet RoomSpa::getCoveredSet() const
{
    SpaTileSet covered;
    for(Tile* tile : mCoveredTiles)
        covered.insert(std::make_pair(tile->getX(), tile->getY()));

    return covered;
}

SpaTileSet RoomSpa::getPoolSet() const
{
    return SpaLayout::poolTiles(getCoveredSet());
}

SpaTileSet RoomSpa::getTakenSet() const
{
    SpaTileSet taken;
    for(const RoomSpaBather& bather : mBathers)
    {
        for(int32_t dx = 0; dx < bather.mBlock.mWidth; ++dx)
        {
            for(int32_t dy = 0; dy < bather.mBlock.mHeight; ++dy)
                taken.insert(std::make_pair(bather.mBlock.mX + dx, bather.mBlock.mY + dy));
        }
    }

    // The pool tile the pool attendant holds for his jump is taken too
    int32_t attendantX = 0;
    int32_t attendantY = 0;
    if((mAttendant != nullptr) && mAttendant->getPlace(attendantX, attendantY))
        taken.insert(std::make_pair(attendantX, attendantY));

    // A place a saved room keeps for a creature is taken too
    for(std::map<std::string, RoomSpaPendingBather>::const_iterator it = mPendingBathers.begin(); it != mPendingBathers.end(); ++it)
    {
        for(int32_t dx = 0; dx < it->second.mBlock.mWidth; ++dx)
        {
            for(int32_t dy = 0; dy < it->second.mBlock.mHeight; ++dy)
                taken.insert(std::make_pair(it->second.mBlock.mX + dx, it->second.mBlock.mY + dy));
        }
    }

    return taken;
}

std::vector<RoomSpaBather>::iterator RoomSpa::findBatherOf(const Creature* creature)
{
    for(std::vector<RoomSpaBather>::iterator it = mBathers.begin(); it != mBathers.end(); ++it)
    {
        if(it->mCreature == creature)
            return it;
    }

    return mBathers.end();
}

bool RoomSpa::canPay(const Creature& creature) const
{
    const int32_t price = static_cast<int32_t>(std::floor(getTavernValue("BeerPrice") + 0.5));
    if(mPayer == SpaPayer::keeper)
        return getSeat()->getGold() >= price;

    return creature.getGoldCarried() >= price;
}

bool RoomSpa::payForBath(Creature& creature)
{
    const int32_t price = static_cast<int32_t>(std::floor(getTavernValue("BeerPrice") + 0.5));
    if(mPayer == SpaPayer::keeper)
        return getGameMap()->withdrawFromTreasuries(price, getSeat());

    if(creature.getGoldCarried() >= price)
    {
        creature.addGoldCarried(-price);
        getGameMap()->addGoldToSeat(price, getSeat()->getId());
        return true;
    }

    return false;
}

bool RoomSpa::canAccept(const Creature& creature) const
{
    if((getSeat() == nullptr) || (creature.getSeat() != getSeat()) || (creature.getDefinition() == nullptr))
        return false;

    if(creature.getDefinition()->isWorker() || mCoveredTiles.empty())
        return false;

    SpaBlock block;
    if(!SpaLayout::findFreeBlock(getPoolSet(), getTakenSet(), creature.getDefinition()->getBedDim1(),
        creature.getDefinition()->getBedDim2(), block))
        return false;

    return canPay(creature);
}

bool RoomSpa::hasOpenCreatureSpot(Creature* c)
{
    if(c == nullptr)
        return false;

    // A creature the saved room waits for has its place, whatever the others do
    if(mPendingBathers.find(c->getName()) != mPendingBathers.end())
        return true;

    return canAccept(*c);
}

bool RoomSpa::addCreatureUsingRoom(Creature* creature)
{
    if(creature == nullptr)
        return false;

    // The place the creature had when the room was saved, or the first free place of its bed size
    RoomSpaBather bather(creature);
    bool fromSave = false;
    std::map<std::string, RoomSpaPendingBather>::iterator pending = mPendingBathers.find(creature->getName());
    if(pending != mPendingBathers.end())
    {
        bather.mBlock = pending->second.mBlock;
        bather.mState = pending->second.mState;
        bather.mTurnsDone = pending->second.mTurnsDone;
        bather.mJump = pending->second.mJump;
        fromSave = true;
    }
    else if(!SpaLayout::findFreeBlock(getPoolSet(), getTakenSet(), creature->getDefinition()->getBedDim1(),
        creature->getDefinition()->getBedDim2(), bather.mBlock))
    {
        return false;
    }

    if(!Room::addCreatureUsingRoom(creature))
        return false;

    if(fromSave)
    {
        mPendingBathers.erase(pending);
    }
    else
    {
        // One bath in SpaCannonballChance starts with a jump from the springboard, when it can be reached
        Tile* springboard = getSpringboardTile();
        Tile* creatureTile = creature->getPositionTile();
        if((springboard != nullptr) && (creatureTile != nullptr) &&
           (Random::Double(0.0, 1.0) < ConfigManager::getSingleton().getRoomConfigDouble("SpaCannonballChance")) &&
           getGameMap()->pathExists(creature, creatureTile, springboard))
        {
            bather.mJump = true;
        }
    }

    // A jump that was running when the room was saved ends at once, in the middle of the place
    if(fromSave && (bather.mState == SpaBatherState::jumping))
        creature->setPosition(getBlockCentre(bather));

    mBathers.push_back(bather);
    if(fromSave && (bather.mState == SpaBatherState::bathing))
    {
        creature->setSpaBathing(true);
        creature->setAnimationState(EntityAnimation::bathe_anim, true, Ogre::Vector3::ZERO, false);
    }

    return true;
}

void RoomSpa::removeCreatureUsingRoom(Creature* creature)
{
    Room::removeCreatureUsingRoom(creature);

    std::vector<RoomSpaBather>::iterator it = findBatherOf(creature);
    if(it == mBathers.end())
        return;

    // The place goes first: the creature may be on its way out of the game (dead, removed), so it is not touched
    // here except for the end of a jump. The mood it gained stays; a bath that is broken off gives no relaxation
    // and no refund.
    if(it->mState == SpaBatherState::jumping)
        creature->cancelJump();

    creature->setSpaBathing(false);
    mBathers.erase(it);
}

bool RoomSpa::shouldStopUseIfHungrySleepy(Creature& creature, bool forced)
{
    std::vector<RoomSpaBather>::iterator it = findBatherOf(&creature);
    if(it == mBathers.end())
        return true;

    return it->mState == SpaBatherState::reserved;
}

bool RoomSpa::shouldNotUseIfBadMood(Creature& creature, bool forced)
{
    return false;
}

Ogre::Vector3 RoomSpa::getBlockCentre(const RoomSpaBather& bather)
{
    return Ogre::Vector3(
        static_cast<Ogre::Real>(bather.mBlock.mX) + static_cast<Ogre::Real>(bather.mBlock.mWidth - 1) * 0.5f,
        static_cast<Ogre::Real>(bather.mBlock.mY) + static_cast<Ogre::Real>(bather.mBlock.mHeight - 1) * 0.5f,
        0.0f);
}

Tile* RoomSpa::getCoveredTileAt(const std::pair<int32_t, int32_t>& position) const
{
    Tile* tile = getGameMap()->getTile(position.first, position.second);
    if((tile == nullptr) || (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), tile) == mCoveredTiles.end()))
        return nullptr;

    return tile;
}

Tile* RoomSpa::getSpringboardTile() const
{
    std::pair<int32_t, int32_t> position;
    if(!SpaLayout::springboardTile(getPoolSet(), position))
        return nullptr;

    return getCoveredTileAt(position);
}

Tile* RoomSpa::getChairTile() const
{
    std::pair<int32_t, int32_t> position;
    if(!SpaLayout::chairTile(getPoolSet(), position))
        return nullptr;

    return getCoveredTileAt(position);
}

bool RoomSpa::hasBatherInPool() const
{
    for(const RoomSpaBather& bather : mBathers)
    {
        if(!bather.mDone && ((bather.mState == SpaBatherState::bathing) || (bather.mState == SpaBatherState::jumping)))
            return true;
    }

    return false;
}

bool RoomSpa::findAttendantPlace(int32_t& x, int32_t& y) const
{
    SpaBlock block;
    if(!SpaLayout::findFreeBlock(getPoolSet(), getTakenSet(), 1, 1, block))
        return false;

    x = block.mX;
    y = block.mY;
    return true;
}

bool RoomSpa::isPoolPosition(int32_t x, int32_t y) const
{
    const SpaTileSet pool = getPoolSet();
    return pool.find(std::make_pair(x, y)) != pool.end();
}

void RoomSpa::playSplashAt(int32_t x, int32_t y)
{
    Tile* tile = getCoveredTileAt(std::make_pair(x, y));
    if(tile == nullptr)
        return;

    // The splash is an effect of the mud piece of the tile, like the steam
    std::map<Tile*, BuildingObject*>::iterator it = mBuildingObjects.find(tile);
    if((it != mBuildingObjects.end()) && (it->second->getMeshName() == SPA_POOL_MESH))
    {
        it->second->addParticleEffect(SPA_SPLASH_EFFECT, SPA_SPLASH_TURNS);
        it->second->fireRefresh();
    }
    playSoundAt(tile, SOUND_SPLASH);
}

bool RoomSpa::isInBlock(const Creature& creature, const SpaBlock& block)
{
    const Tile* tile = creature.getPositionTile();
    if(tile == nullptr)
        return false;

    return blockContains(block, tile->getX(), tile->getY());
}

bool RoomSpa::isBatherDisturbed(const Creature& creature)
{
    if(!creature.getIsOnMap() || !creature.isAlive() || creature.isKo() || creature.isBeingDragged())
        return true;

    return creature.isActionInList(CreatureActionType::fight) ||
        creature.isActionInList(CreatureActionType::fightFriendly) ||
        creature.isActionInList(CreatureActionType::flee);
}

bool RoomSpa::useRoom(Creature& creature, bool forced)
{
    std::vector<RoomSpaBather>::iterator it = findBatherOf(&creature);
    if(it == mBathers.end())
    {
        // The bath was broken off (fight, flight): the use of the room ends
        creature.popAction();
        return true;
    }

    switch(it->mState)
    {
        case SpaBatherState::reserved:
            return walkToPlace(creature, *it);
        case SpaBatherState::bathing:
        {
            // The room counts the bath in doUpkeep; the bather leaves when it is over
            if(!it->mDone)
                return false;

            creature.popAction();
            return true;
        }
        default:
            // jumping is run by doUpkeep
            return false;
    }
}

bool RoomSpa::walkToPlace(Creature& creature, RoomSpaBather& bather)
{
    Tile* springboard = bather.mJump ? getSpringboardTile() : nullptr;
    if(springboard != nullptr)
    {
        // Walk to the springboard. The board is furniture, so the walk may end next to it: a creature that has stopped
        // on the tile of the springboard or on a tile next to it stands there.
        const Tile* here = creature.getPositionTile();
        const bool atBoard = (here != nullptr) && (here == springboard ||
            ((std::abs(here->getX() - springboard->getX()) <= 1) && (std::abs(here->getY() - springboard->getY()) <= 1) &&
             !creature.isMoving()));
        if(!atBoard)
        {
            if(!creature.isMoving() && !creature.setDestination(springboard))
            {
                creature.popAction();
                return true;
            }
            return false;
        }

        // On the springboard the bath is paid, then the creature jumps into the middle of its place
        if(!payForBath(creature))
        {
            creature.popAction();
            return true;
        }

        bather.mState = SpaBatherState::jumping;
        bather.mTurnsDone = 0.0;
        creature.setPosition(Ogre::Vector3(static_cast<Ogre::Real>(springboard->getX()),
            static_cast<Ogre::Real>(springboard->getY()), 0.0f));
        creature.startJump(getBlockCentre(bather));
        return false;
    }

    // Without a reachable springboard the bather simply walks to its place
    bather.mJump = false;
    const Ogre::Vector3 centre = getBlockCentre(bather);
    const Ogre::Vector3 position = creature.getPosition();
    const Ogre::Real distance = Ogre::Vector2(position.x - centre.x, position.y - centre.y).length();
    if(distance > CENTRE_EPSILON)
    {
        if(isInBlock(creature, bather.mBlock))
        {
            // On a tile of the block: the last steps lead to the middle of the block
            if(!creature.isMoving())
            {
                std::vector<Ogre::Vector2> path;
                path.push_back(Ogre::Vector2(centre.x, centre.y));
                creature.setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
                creature.pushAction(Utils::make_unique<CreatureActionWalkToTile>(creature));
            }
            return false;
        }

        Tile* anchor = getGameMap()->getTile(bather.mBlock.mX, bather.mBlock.mY);
        if(!creature.isMoving() && !creature.setDestination(anchor))
        {
            creature.popAction();
            return true;
        }
        return false;
    }

    // In the middle of the place: the bath is paid and starts; a payment that fails now ends the visit
    if(!payForBath(creature))
    {
        creature.popAction();
        return true;
    }

    startBath(bather);
    return false;
}

void RoomSpa::startBath(RoomSpaBather& bather)
{
    bather.mState = SpaBatherState::bathing;
    bather.mTurnsDone = 0.0;
    bather.mCreature->setSpaBathing(true);
    bather.mCreature->setAnimationState(EntityAnimation::bathe_anim, true, Ogre::Vector3::ZERO, false);
}

void RoomSpa::landJump(RoomSpaBather& bather)
{
    Creature* creature = bather.mCreature;
    creature->addParticleEffect(SPA_SPLASH_EFFECT, SPA_SPLASH_TURNS);
    playSoundAt(creature->getPositionTile(), SOUND_SPLASH);
    startBath(bather);
}

void RoomSpa::finishBath(RoomSpaBather& bather)
{
    Creature* creature = bather.mCreature;

    // The relaxation lasts as long as the research level of the keeper allows; a hangover ends at once and the
    // creature carries mud out of the pool. The bath does not clean the creature.
    const ConfigManager& config = ConfigManager::getSingleton();
    creature->setRelaxTurns(SkillManager::getResearchValue(getSeat(), SkillType::roomSpa,
        config.getRoomConfigDouble("SpaRelaxTurns"), ResearchEffect::RelaxTime));
    creature->setHangoverTurns(0.0);
    creature->setSpaMudTilesLeft(static_cast<int32_t>(config.getRoomConfigUInt32("SpaMudTrailTiles")));
    sendBathFinished(*creature);
    bather.mDone = true;
    creature->setSpaBathing(false);
    creature->setAnimationState(EntityAnimation::idle_anim, true);
}

void RoomSpa::playSoundAt(Tile* tile, const std::string& family)
{
    if(tile == nullptr)
        return;

    for(Seat* seat : tile->getSeatsWithVision())
    {
        if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::playSpatialSound, seat->getPlayer());
        serverNotification->mPacket << family << tile->getX() << tile->getY();
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void RoomSpa::doUpkeep()
{
    Room::doUpkeep();

    if(!getIsOnServerMap())
        return;

    resumeLoadedBathers();
    releaseBathersOnLostTiles();
    abortDisturbedBathers();
    upkeepBathers();
    upkeepSteam();
}

void RoomSpa::upkeepBathers()
{
    const double moodPerTurn = ConfigManager::getSingleton().getRoomConfigDouble("SpaMoodPerTurn");
    const double bathTurns = ConfigManager::getSingleton().getRoomConfigDouble("SpaBathTurns");
    for(RoomSpaBather& bather : mBathers)
    {
        switch(bather.mState)
        {
            case SpaBatherState::jumping:
            {
                bather.mCreature->continueJump();
                if(!bather.mCreature->isJumping())
                    landJump(bather);
                break;
            }
            case SpaBatherState::bathing:
            {
                if(bather.mDone)
                    break;

                // The bath ends in the turn in which the counted turns reach SpaBathTurns
                bather.mCreature->addSpaMood(moodPerTurn);
                bather.mTurnsDone += 1.0;
                if(bather.mTurnsDone >= bathTurns)
                    finishBath(bather);
                break;
            }
            default:
                break;
        }
    }
}

void RoomSpa::abortDisturbedBathers()
{
    // A fight, a flight, a knock-out or a hand that takes a bather away ends its bath: the mood it gained stays, it
    // gets no relaxation and no refund
    std::vector<RoomSpaBather>::iterator it = mBathers.begin();
    while(it != mBathers.end())
    {
        if(!it->mDone && isBatherDisturbed(*it->mCreature))
        {
            if(it->mState == SpaBatherState::jumping)
                it->mCreature->cancelJump();

            it->mCreature->setSpaBathing(false);
            it = mBathers.erase(it);
            continue;
        }
        ++it;
    }
}

void RoomSpa::releaseBathersOnLostTiles()
{
    std::vector<Creature*> lost;
    for(const RoomSpaBather& bather : mBathers)
    {
        for(int32_t dx = 0; dx < bather.mBlock.mWidth; ++dx)
        {
            for(int32_t dy = 0; dy < bather.mBlock.mHeight; ++dy)
            {
                if(getCoveredTileAt(std::make_pair(bather.mBlock.mX + dx, bather.mBlock.mY + dy)) == nullptr)
                {
                    if(std::find(lost.begin(), lost.end(), bather.mCreature) == lost.end())
                        lost.push_back(bather.mCreature);
                }
            }
        }
    }

    // Clearing the actions releases the places, so the bathers are handled after the loop
    for(Creature* creature : lost)
        creature->clearActionQueue();
}

void RoomSpa::resumeLoadedBathers()
{
    if(mPendingBathers.empty())
        return;

    // The creatures take their saved places again; the use of the room binds them in addCreatureUsingRoom
    std::vector<std::string> names;
    for(std::map<std::string, RoomSpaPendingBather>::iterator it = mPendingBathers.begin(); it != mPendingBathers.end(); ++it)
        names.push_back(it->first);

    for(const std::string& name : names)
    {
        Creature* creature = getGameMap()->getCreature(name);
        if((creature == nullptr) || !creature->isAlive() || !creature->getIsOnMap() || (creature->getSeat() != getSeat()))
            continue;

        if(!creature->isActionInList(CreatureActionType::useRoom))
            creature->pushAction(Utils::make_unique<CreatureActionUseRoom>(*creature, *this, false));
    }

    // A place whose creature did not come back is free again
    mPendingBathers.clear();
}

void RoomSpa::upkeepSteam()
{
    std::map<Tile*, uint32_t>::iterator it = mSteamTurnsLeft.begin();
    while(it != mSteamTurnsLeft.end())
    {
        std::map<Tile*, BuildingObject*>::iterator object = mBuildingObjects.find(it->first);
        if((object == mBuildingObjects.end()) || (object->second->getMeshName() != SPA_POOL_MESH))
        {
            mSteamTurnsLeft.erase(it++);
            continue;
        }

        if(it->second > 0)
            --it->second;

        if(it->second == 0)
        {
            object->second->addParticleEffect(SPA_STEAM_EFFECT, SPA_STEAM_TURNS);
            object->second->fireRefresh();
            it->second = SPA_STEAM_TURNS;
        }
        ++it;
    }
}

void RoomSpa::setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles)
{
    Room::setupRoom(name, seat, tiles);

    // The computer keepers let their creatures pay for the bath
    if((seat != nullptr) && (seat->getPlayer() != nullptr) && !seat->getPlayer()->getIsHuman())
        mPayer = SpaPayer::creature;
}

void RoomSpa::absorbRoom(Room* r)
{
    if(r->getType() != getType())
    {
        OD_LOG_ERR("Trying to merge incompatible rooms: " + getName() + ", type=" + RoomManager::getRoomNameFromRoomType(getType()) + ", with " + r->getName() + ", type=" + RoomManager::getRoomNameFromRoomType(r->getType()));
        return;
    }

    // The room that already has its pool objects is the older one and keeps its payer setting; the room that is
    // built last has not got any object yet
    RoomSpa* other = static_cast<RoomSpa*>(r);
    if(mBuildingObjects.empty() && !other->mBuildingObjects.empty())
        mPayer = other->mPayer;

    // The rim pieces of the other room go away; updateActiveSpots puts the right ones around the merged pool
    other->removeRimObjects();
    mSteamTurnsLeft.insert(other->mSteamTurnsLeft.begin(), other->mSteamTurnsLeft.end());
    other->mSteamTurnsLeft.clear();

    // The room without an attendant takes the one of the other; two attendants are one too many, so the other's goes.
    // updateActiveSpots puts the attendant on the chair of the merged pool.
    if((mAttendant == nullptr) && (other->mAttendant != nullptr))
    {
        mAttendant = other->mAttendant;
        other->mAttendant = nullptr;
        mAttendant->setRoom(this, mAttendant->getChairTile());
    }
    else
    {
        other->removeAttendant();
    }

    Room::absorbRoom(r);
}

void RoomSpa::splitRoom(Room& newRoom, const std::vector<Tile*>& tiles)
{
    if(newRoom.getType() != getType())
        return;

    // The room that gets the tiles keeps the payer setting of this one, also when the seat changes
    RoomSpa& newSpa = static_cast<RoomSpa&>(newRoom);
    newSpa.mPayer = mPayer;

    // The pool attendant goes with the chair: when its tile changes rooms, he changes owner with it
    if((mAttendant != nullptr) && (std::find(tiles.begin(), tiles.end(), mAttendant->getChairTile()) != tiles.end()))
    {
        newSpa.mAttendant = mAttendant;
        mAttendant = nullptr;
        newSpa.mAttendant->setRoom(&newSpa, newSpa.mAttendant->getChairTile());
    }
}

bool RoomSpa::removeCoveredTile(Tile* t)
{
    if(!Room::removeCoveredTile(t))
        return false;

    // A bather on the tile, or with a place on it, stops. Clearing its actions releases it from the room, so we work
    // on a copy.
    std::vector<Creature*> bathers = mCreaturesUsingRoom;
    for(Creature* bather : bathers)
    {
        std::vector<RoomSpaBather>::iterator place = findBatherOf(bather);
        const bool hasPlaceOnTile = (place != mBathers.end()) && blockContains(place->mBlock, t->getX(), t->getY());
        if((bather->getPositionTile() == t) || hasPlaceOnTile)
            bather->clearActionQueue();
    }

    return true;
}

void RoomSpa::removeFromGameMap(GameMap* gameMap)
{
    removeAttendant();
    removeRimObjects();
    mSteamTurnsLeft.clear();
    Room::removeFromGameMap(gameMap);
}

void RoomSpa::removeRimObjects()
{
    for(RoomSpaRim& rim : mRimObjects)
    {
        rim.mObject->removeFromGameMap();
        rim.mObject->deleteYourself();
    }
    mRimObjects.clear();
}

void RoomSpa::removeAttendant()
{
    if(mAttendant == nullptr)
        return;

    mAttendant->removeFromRoom();
    mAttendant = nullptr;
}

void RoomSpa::placeAttendant()
{
    // A room without a chair has no attendant; when the chair moved, he is spawned again on the new one
    Tile* chair = getChairTile();
    if(chair == nullptr)
    {
        removeAttendant();
        return;
    }

    if((mAttendant != nullptr) && (mAttendant->getChairTile() != chair))
        removeAttendant();

    if(mAttendant != nullptr)
        return;

    mAttendant = PoolAttendantEntity::spawnOnChair(getGameMap(), this, chair, static_cast<Ogre::Real>(CHAIR_ANGLE));
    if((mAttendant != nullptr) && mPendingAttendant.mPresent)
        mAttendant->restoreFromSave(mPendingAttendant.mSave);

    mPendingAttendant = RoomSpaPendingAttendant();
}

void RoomSpa::addPoolObject(Tile* tile, GameMap* gameMap)
{
    BuildingObject* object = new BuildingObject(gameMap, *this, SPA_POOL_MESH, *tile, 0.0, false);
    addBuildingObject(tile, object, gameMap);
    object->createMesh();

    // The steam rises from every pool tile and is renewed when it runs out
    object->addParticleEffect(SPA_STEAM_EFFECT, SPA_STEAM_TURNS);
    object->fireRefresh();
    mSteamTurnsLeft[tile] = SPA_STEAM_TURNS;
}

void RoomSpa::updateTileObject(Tile* tile, const std::string& meshName, double angle, GameMap* gameMap)
{
    std::map<Tile*, BuildingObject*>::iterator it = mBuildingObjects.find(tile);
    if(it != mBuildingObjects.end())
    {
        const bool sameAngle = std::abs(static_cast<double>(it->second->getRotationAngle()) - angle) < ANGLE_EPSILON;
        if((it->second->getMeshName() == meshName) && sameAngle)
        {
            // A pool piece that came over from another room (a takeover) has no steam timer yet
            if((meshName == SPA_POOL_MESH) && (mSteamTurnsLeft.find(tile) == mSteamTurnsLeft.end()))
                mSteamTurnsLeft[tile] = SPA_STEAM_TURNS;
            return;
        }

        removeBuildingObject(tile);
        mSteamTurnsLeft.erase(tile);
    }

    if(meshName.empty())
        return;

    if(meshName == SPA_POOL_MESH)
    {
        addPoolObject(tile, gameMap);
        return;
    }

    BuildingObject* object = new BuildingObject(gameMap, *this, meshName, *tile, angle, false);
    addBuildingObject(tile, object, gameMap);
    object->createMesh();
}

void RoomSpa::updateRimObjects(const SpaTileSet& pool, GameMap* gameMap)
{
    // Every side of a pool tile that borders a tile outside the pool gets a rim piece, turned to that side
    static const int32_t SIDE_DX[] = { 0, -1, 0, 1 };
    static const int32_t SIDE_DY[] = { 1, 0, -1, 0 };
    static const double SIDE_ANGLE[] = { OBJECT_ANGLE_SIDE_TOP, OBJECT_ANGLE_SIDE_LEFT, OBJECT_ANGLE_SIDE_BOTTOM,
        OBJECT_ANGLE_SIDE_RIGHT };
    static const uint32_t NB_SIDES = 4;
    std::vector<std::pair<Tile*, double> > wanted;
    for(SpaTileSet::const_iterator it = pool.begin(); it != pool.end(); ++it)
    {
        Tile* tile = getCoveredTileAt(*it);
        if(tile == nullptr)
            continue;

        for(uint32_t i = 0; i < NB_SIDES; ++i)
        {
            if(pool.find(std::make_pair(it->first + SIDE_DX[i], it->second + SIDE_DY[i])) == pool.end())
                wanted.push_back(std::make_pair(tile, SIDE_ANGLE[i]));
        }
    }

    // Nothing to do when the pieces already stand where they are wanted
    bool same = (wanted.size() == mRimObjects.size());
    for(std::size_t i = 0; same && (i < wanted.size()); ++i)
    {
        if((mRimObjects[i].mTile != wanted[i].first) || (mRimObjects[i].mAngle != wanted[i].second))
            same = false;
    }
    if(same)
        return;

    removeRimObjects();
    for(const std::pair<Tile*, double>& piece : wanted)
    {
        BuildingObject* object = new BuildingObject(gameMap, *this, SPA_RIM_MESH, *piece.first, piece.second, false);
        object->setSeat(getSeat());
        object->addToGameMap(gameMap);
        object->createMesh();
        object->setPosition(object->getPosition());
        mRimObjects.push_back(RoomSpaRim(piece.first, piece.second, object));
    }
}

void RoomSpa::updateActiveSpots(GameMap* gameMap)
{
    Room::updateActiveSpots(gameMap);

    // The objects are created by the server and sent to the clients like every other entity
    if(!getIsOnServerMap())
        return;

    if(gameMap == nullptr)
        gameMap = getGameMap();

    // Objects of tiles the room no longer covers go away
    std::vector<Tile*> objectsToRemove;
    for(const std::pair<Tile* const, BuildingObject*>& entry : mBuildingObjects)
    {
        if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), entry.first) == mCoveredTiles.end())
            objectsToRemove.push_back(entry.first);
    }
    for(Tile* tile : objectsToRemove)
    {
        removeBuildingObject(tile);
        mSteamTurnsLeft.erase(tile);
    }

    // A room without tiles has no pool
    if(mCoveredTiles.empty())
    {
        removeAttendant();
        removeRimObjects();
        return;
    }

    // The mud on the pool tiles, the chair above the pool and the springboard below it; the other tiles are the rim.
    // The object of a tile that has the wrong kind (a room that grew or shrank) is replaced.
    const SpaTileSet pool = getPoolSet();
    std::pair<int32_t, int32_t> chair;
    std::pair<int32_t, int32_t> springboard;
    const bool hasChair = SpaLayout::chairTile(pool, chair);
    const bool hasSpringboard = SpaLayout::springboardTile(pool, springboard);
    for(Tile* tile : mCoveredTiles)
    {
        const std::pair<int32_t, int32_t> position(tile->getX(), tile->getY());
        std::string wantedMesh;
        double angle = 0.0;
        if(pool.find(position) != pool.end())
        {
            wantedMesh = SPA_POOL_MESH;
        }
        else if(hasChair && (position == chair))
        {
            wantedMesh = SPA_CHAIR_MESH;
            angle = CHAIR_ANGLE;
        }
        else if(hasSpringboard && (position == springboard))
        {
            wantedMesh = SPA_SPRINGBOARD_MESH;
            angle = SPRINGBOARD_ANGLE;
        }

        updateTileObject(tile, wantedMesh, angle, gameMap);
    }

    updateRimObjects(pool, gameMap);
    placeAttendant();
}

void RoomSpa::exportToStream(std::ostream& os) const
{
    Room::exportToStream(os);
    os << STREAM_TAG_PAYER << " " << static_cast<uint32_t>(mPayer) << std::endl;

    // <x> <y> <state> <turnsLeft> <cannonballTurnsLeft> <hasPlace> <placeX> <placeY>: the pool attendant. A loaded room
    // that has not spawned him yet writes the line it read.
    if(mAttendant != nullptr)
    {
        PoolAttendantSave save;
        mAttendant->exportSaveData(save);
        writeAttendantLine(os, save);
    }
    else if(mPendingAttendant.mPresent)
    {
        writeAttendantLine(os, mPendingAttendant.mSave);
    }

    // <creature> <x> <y> <width> <height> <state> <turnsDone> <jump>: one line for every bather, the places a loaded
    // room still waits for included. A bath that is over is not written.
    std::vector<std::string> lines;
    for(const RoomSpaBather& bather : mBathers)
    {
        if((bather.mCreature == nullptr) || bather.mDone)
            continue;

        std::ostringstream line;
        line << bather.mCreature->getName() << " " << bather.mBlock.mX << " " << bather.mBlock.mY << " "
             << bather.mBlock.mWidth << " " << bather.mBlock.mHeight << " " << batherStateToString(bather.mState) << " "
             << bather.mTurnsDone << " " << (bather.mJump ? 1 : 0);
        lines.push_back(line.str());
    }
    for(std::map<std::string, RoomSpaPendingBather>::const_iterator it = mPendingBathers.begin(); it != mPendingBathers.end(); ++it)
    {
        std::ostringstream line;
        line << it->first << " " << it->second.mBlock.mX << " " << it->second.mBlock.mY << " " << it->second.mBlock.mWidth
             << " " << it->second.mBlock.mHeight << " " << batherStateToString(it->second.mState) << " "
             << it->second.mTurnsDone << " " << (it->second.mJump ? 1 : 0);
        lines.push_back(line.str());
    }

    if(lines.empty())
        return;

    os << STREAM_TAG_BATHERS << " " << lines.size() << std::endl;
    for(const std::string& line : lines)
        os << line << std::endl;
}

bool RoomSpa::importFromStream(std::istream& is)
{
    if(!Room::importFromStream(is))
        return false;

    // The lines come after the tiles of the room, in any order, and every one of them is optional. The first word that
    // is none of them belongs to what follows in the stream: it is put back.
    while(true)
    {
        std::streampos pos = is.tellg();
        std::string tag;
        if(!(is >> tag))
        {
            is.clear();
            is.seekg(pos);
            break;
        }

        if(tag == STREAM_TAG_PAYER)
        {
            uint32_t payer = 0;
            if(!(is >> payer) || (payer > static_cast<uint32_t>(SpaPayer::creature)))
                return false;

            mPayer = static_cast<SpaPayer>(payer);
        }
        else if(tag == STREAM_TAG_ATTENDANT)
        {
            // The first four values are required, the rest is optional: a line without them gets new jump timers
            // and no pool tile for a jump
            std::string rest;
            std::getline(is, rest);
            std::istringstream line(rest);
            std::string stateToken;
            PoolAttendantSave saved;
            if(!(line >> saved.mX >> saved.mY >> stateToken >> saved.mTurnsLeft) ||
               !PoolAttendantStateNames::fromString(stateToken, saved.mState))
                return false;

            saved.mHasCannonball = static_cast<bool>(line >> saved.mCannonballTurnsLeft);
            int32_t hasPlace = 0;
            if(saved.mHasCannonball && (line >> hasPlace >> saved.mPlaceX >> saved.mPlaceY))
                saved.mHasPlace = (hasPlace != 0);

            mPendingAttendant.mPresent = true;
            mPendingAttendant.mSave = saved;
        }
        else if(tag == STREAM_TAG_BATHERS)
        {
            uint32_t nbBathers = 0;
            if(!(is >> nbBathers))
                return false;

            // The rest of the tag line, then one line for every bather
            std::string rest;
            std::getline(is, rest);
            for(uint32_t i = 0; i < nbBathers; ++i)
            {
                std::getline(is, rest);
                std::istringstream line(rest);
                std::string name;
                std::string stateToken;
                RoomSpaPendingBather saved;
                if(!(line >> name >> saved.mBlock.mX >> saved.mBlock.mY >> saved.mBlock.mWidth >> saved.mBlock.mHeight >>
                     stateToken >> saved.mTurnsDone) || !batherStateFromString(stateToken, saved.mState) ||
                   (saved.mBlock.mWidth < 1) || (saved.mBlock.mHeight < 1))
                    return false;

                // The jump flag is optional
                int32_t jump = 0;
                line >> jump;
                saved.mJump = (jump != 0);
                mPendingBathers[name] = saved;
            }
        }
        else
        {
            is.clear();
            is.seekg(pos);
            break;
        }
    }

    return true;
}
