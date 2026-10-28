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

#include "rooms/RoomTavern.h"

#include "creatureaction/CreatureActionSleep.h"
#include "creatureaction/CreatureActionUseRoom.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/InnkeeperEntity.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "network/CosmeticEvent.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "rooms/RoomManager.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <istream>
#include <limits>
#include <map>
#include <ostream>
#include <sstream>
#include <string>

const std::string RoomTavernName = "Tavern";
const std::string RoomTavernNameDisplay = "Tavern room";
const RoomType RoomTavern::mRoomType = RoomType::tavern;
const TileVisual RoomTavern::mRoomVisual = TileVisual::tavernRoom;

namespace
{
//! \brief Mesh name of the counter on the counter tile of a tavern.
const std::string TAVERN_COUNTER_MESH = "TavernCounter";
//! \brief Mesh name of the keg on a tavern tile that lies next to a wall.
const std::string TAVERN_KEG_MESH = "TavernKeg";
//! \brief Mesh name of the table on a tavern tile that lies inside the room.
const std::string TAVERN_TABLE_MESH = "TavernTable";
//! \brief Object angles (degrees) for a back to the wall at +y, -y, -x and +x (same convention as the other rooms with wall furniture).
const double OBJECT_ANGLE_WALL_TOP = 0.0;
const double OBJECT_ANGLE_WALL_BOTTOM = 180.0;
const double OBJECT_ANGLE_WALL_LEFT = 90.0;
const double OBJECT_ANGLE_WALL_RIGHT = 270.0;
//! \brief Line of the room stream with who pays for the beer (0 = keeper, 1 = creature).
const std::string STREAM_TAG_PAYER = "TavernPayer";
//! \brief Line of the room stream with the tile the innkeeper stands on.
const std::string STREAM_TAG_INNKEEPER = "Innkeeper";
//! \brief Line of the room stream with the counter tile.
const std::string STREAM_TAG_COUNTER = "Counter";
//! \brief Line of the room stream with the place of one guest.
const std::string STREAM_TAG_SPOT = "Spot";
//! \brief Line of the room stream with one running game.
const std::string STREAM_TAG_GAME = "Game";
//! \brief Sound family of a drink that is poured.
const std::string SOUND_POUR = "Rooms/Tavern/Pour";
//! \brief Sound family of a slap in a slap duel.
const std::string SOUND_SLAP = "Creatures/Default/Slap";
//! \brief Sound family of the cheer when a game ends.
const std::string SOUND_CHEER = "Creatures/Default/Cheer";
//! \brief Turns the loser of a slap duel needs to get up from the floor (plan: 2 turns).
const int32_t GET_UP_TURNS = 2;
//! \brief Turns a guest stays in the state done after its last drink, so that a guest finishing its drink in the
//! same or the next turn can still pick it as the partner of a game.
const int32_t DONE_WAIT_TURNS = 2;
//! \brief A slap duel without decision ends after this many times GameTurns turns.
const int32_t DUEL_MAX_TURNS_FACTOR = 4;
//! \brief Scale of the percent values of the [Tavern] block.
const double PERCENT_SCALE = 100.0;
//! \brief Each further drink of the chain halves the chance of the previous one.
const double DRINK_CHAIN_HALVING = 2.0;
//! \brief A squared direction shorter than this has no usable direction.
const double DIRECTION_EPSILON = 0.0001;
//! \brief Number of games a guest can pick when no beer is served (arm wrestling and dice).
const uint32_t NB_GAMES_WITHOUT_BEER = 2;
//! \brief Number of games a guest can pick when beer is served (arm wrestling, dice and the slap duel).
const uint32_t NB_GAMES_WITH_BEER = 3;

//! \brief Reads a value of the [Tavern] block of global.cfg.
//! \param key The key of the value.
double getTavernValue(const std::string& key)
{
    return ConfigManager::getSingleton().getTavernConfigDouble(key);
}

//! \brief The name of a guest state in the room stream.
//! \param state The state.
std::string guestStateToString(TavernGuestState state)
{
    switch(state)
    {
        case TavernGuestState::arriving:
            return "arriving";
        case TavernGuestState::drinking:
            return "drinking";
        case TavernGuestState::done:
            return "done";
        case TavernGuestState::game:
            return "game";
        case TavernGuestState::ko:
            return "ko";
        case TavernGuestState::getUp:
            return "getup";
    }
    return "done";
}

//! \brief Reads the name of a guest state from the room stream.
//! \param token The name.
//! \param state Set to the state when the name is known.
//! \return False for an unknown name.
bool guestStateFromString(const std::string& token, TavernGuestState& state)
{
    if(token == "arriving")
        state = TavernGuestState::arriving;
    else if(token == "drinking")
        state = TavernGuestState::drinking;
    else if(token == "done")
        state = TavernGuestState::done;
    else if(token == "game")
        state = TavernGuestState::game;
    else if(token == "ko")
        state = TavernGuestState::ko;
    else if(token == "getup")
        state = TavernGuestState::getUp;
    else
        return false;

    return true;
}

//! \brief The direction on the ground from a creature to a point; zero when they are on the same spot.
//! \param from The creature.
//! \param target The point.
Ogre::Vector3 directionTo(const Creature& from, const Ogre::Vector3& target)
{
    Ogre::Vector3 direction(target.x - from.getPosition().x, target.y - from.getPosition().y, 0.0f);
    if(direction.squaredLength() < DIRECTION_EPSILON)
        return Ogre::Vector3::ZERO;

    direction.normalise();
    return direction;
}

//! \brief The middle of a tile on the ground.
//! \param tile The tile.
Ogre::Vector3 tileMiddle(const Tile& tile)
{
    return Ogre::Vector3(static_cast<Ogre::Real>(tile.getX()), static_cast<Ogre::Real>(tile.getY()), 0.0f);
}

//! \brief Builds, prices and loads taverns; registered for RoomType::tavern.
class RoomTavernFactory : public RoomFactory
{
    RoomType getRoomType() const override
    { return RoomTavern::mRoomType; }

    TileVisual getVisualType() const override
    { return RoomTavern::mRoomVisual; }

    const std::string& getName() const override
    { return RoomTavernName; }

    const std::string& getNameReadable() const override
    { return RoomTavernNameDisplay; }

    int getCostPerTile() const override
    { return ConfigManager::getSingleton().getRoomConfigInt32("TavernCostPerTile"); }

    void checkBuildRoom(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefault(gameMap, RoomTavern::mRoomType, inputManager, inputCommand);
    }

    bool buildRoom(GameMap* gameMap, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, gameMap, player, packet))
            return false;

        int32_t pricePerTarget = RoomManager::costPerTile(RoomTavern::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
            return false;

        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }

    void checkBuildRoomEditor(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand) const override
    {
        checkBuildRoomDefaultEditor(gameMap, RoomTavern::mRoomType, inputManager, inputCommand);
    }

    bool buildRoomEditor(GameMap* gameMap, ODPacket& packet) const override
    {
        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefaultEditor(gameMap, room, packet);
    }

    //! \brief Creates an empty room of this type, for a room that has to be split in two.
    Room* createRoom(GameMap* gameMap) const override
    { return new RoomTavern(gameMap); }

    Room* getRoomFromStream(GameMap* gameMap, std::istream& is) const override
    {
        RoomTavern* room = new RoomTavern(gameMap);
        if(!Room::importRoomFromStream(*room, is))
        {
            OD_LOG_ERR("Error while building a room from the stream");
        }
        return room;
    }

    bool buildRoomOnTiles(GameMap* gameMap, Player* player, const std::vector<Tile*>& tiles, bool noFee =false) const override
    {
        int32_t pricePerTarget = RoomManager::costPerTile(RoomTavern::mRoomType);
        int32_t price = static_cast<int32_t>(tiles.size()) * pricePerTarget;
        if(!noFee)
            if(!gameMap->withdrawFromTreasuries(price, player->getSeat()))
                return false;
        RoomTavern* room = new RoomTavern(gameMap);
        return buildRoomDefault(gameMap, room, player->getSeat(), tiles);
    }
};

// Register the factory
static RoomRegister reg(new RoomTavernFactory);

//! \brief Reads the x and y of a tile from the stream and looks the tile up on the map.
//! \param gameMap The map the tile belongs to.
//! \param is The stream, positioned behind the tag of the line.
//! \param tile Set to the tile, nullptr when the numbers are fine but the map has no such tile.
//! \return False if the two numbers could not be read.
bool readTileFromStream(GameMap* gameMap, std::istream& is, Tile*& tile)
{
    int32_t x = 0;
    int32_t y = 0;
    if(!(is >> x >> y))
        return false;

    tile = gameMap->getTile(x, y);
    return true;
}
}

RoomTavern::RoomTavern(GameMap* gameMap) :
    Room(gameMap),
    mPayer(TavernPayer::keeper),
    mCounterTile(nullptr),
    mInnkeeper(nullptr)
{
    setMeshName("Room");
}

uint32_t RoomTavern::getNbDrinkingTiles() const
{
    const uint32_t nbTiles = static_cast<uint32_t>(mCoveredTiles.size());
    if((mCounterTile != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), mCounterTile) != mCoveredTiles.end()))
        return nbTiles - 1;

    return nbTiles;
}

bool RoomTavern::hasOpenCreatureSpot(Creature* c)
{
    // A creature the saved room waits for has its place, whatever the other guests do
    if((c != nullptr) && (mPendingSpots.find(c->getName()) != mPendingSpots.end()))
        return true;

    // A leisure visit (the creature is not thirsty) waits until the cooldown since its last tavern visit is over
    if((c != nullptr) && (c->getTavernCooldownTurns() > 0) &&
       (c->getThirst() < getTavernValue("ThirstSeek")))
        return false;

    for(Tile* tile : mCoveredTiles)
    {
        if(isFreeSpotTile(tile))
            return true;
    }

    return false;
}

bool RoomTavern::isFreeSpotTile(Tile* tile) const
{
    if((tile == nullptr) || (tile == mCounterTile))
        return false;

    return mSpots.find(tile) == mSpots.end();
}

Tile* RoomTavern::pickFreeSpotTile(const Creature& creature) const
{
    Tile* creatureTile = creature.getPositionTile();
    Tile* best = nullptr;
    int32_t bestDistance = std::numeric_limits<int32_t>::max();
    bool bestNextToGuest = false;
    for(Tile* tile : mCoveredTiles)
    {
        if(!isFreeSpotTile(tile))
            continue;

        int32_t distance = 0;
        if(creatureTile != nullptr)
        {
            const int32_t dx = tile->getX() - creatureTile->getX();
            const int32_t dy = tile->getY() - creatureTile->getY();
            distance = dx * dx + dy * dy;
        }

        // A place next to a guest comes first, so that two guests can play a game
        bool nextToGuest = false;
        static const int32_t SIDE_DX[] = { 1, -1, 0, 0 };
        static const int32_t SIDE_DY[] = { 0, 0, 1, -1 };
        static const uint32_t NB_SIDES = 4;
        for(uint32_t i = 0; i < NB_SIDES; ++i)
        {
            Tile* side = getGameMap()->getTile(tile->getX() + SIDE_DX[i], tile->getY() + SIDE_DY[i]);
            if((side != nullptr) && (mSpots.find(side) != mSpots.end()))
                nextToGuest = true;
        }

        if((nextToGuest && !bestNextToGuest) || ((nextToGuest == bestNextToGuest) && (distance < bestDistance)))
        {
            bestDistance = distance;
            bestNextToGuest = nextToGuest;
            best = tile;
        }
    }

    return best;
}

std::map<Tile*, RoomTavernSpot>::iterator RoomTavern::findSpotOf(const Creature* creature)
{
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if(it->second.mCreature == creature)
            return it;
    }

    return mSpots.end();
}

bool RoomTavern::addCreatureUsingRoom(Creature* creature)
{
    if(creature == nullptr)
        return false;

    // The place the creature had when the room was saved, if it is still free
    Tile* tile = nullptr;
    std::map<std::string, RoomTavernPendingSpot>::iterator pending = mPendingSpots.find(creature->getName());
    if((pending != mPendingSpots.end()) && isFreeSpotTile(pending->second.mTile) &&
       (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), pending->second.mTile) != mCoveredTiles.end()))
    {
        tile = pending->second.mTile;
    }
    else
    {
        pending = mPendingSpots.end();
        tile = pickFreeSpotTile(*creature);
    }

    if(tile == nullptr)
        return false;

    if(!Room::addCreatureUsingRoom(creature))
        return false;

    std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.insert(std::make_pair(tile, RoomTavernSpot(creature))).first;
    if(pending != mPendingSpots.end())
    {
        it->second.mState = pending->second.mState;
        it->second.mTurnsLeft = pending->second.mTurnsLeft;
        it->second.mDrinks = pending->second.mDrinks;
        it->second.mSleepAfter = pending->second.mSleepAfter;
        mPendingSpots.erase(pending);
        showSpotState(tile, it->second);
    }

    return true;
}

void RoomTavern::removeCreatureUsingRoom(Creature* creature)
{
    Room::removeCreatureUsingRoom(creature);

    std::map<Tile*, RoomTavernSpot>::iterator it = findSpotOf(creature);
    if(it == mSpots.end())
        return;

    // The place goes first: the creature may be on its way out of the game (dead, removed), so its clips are not touched here.
    // Whatever clip it still shows is replaced by the next thing it does. Its leisure cooldown starts, so that the job search
    // does not send it back in at once while it still stands on a tavern tile.
    it->second.mCreature->startTavernCooldown();
    mSpots.erase(it);

    // A game of the guest ends without effects; its partner is done
    std::map<Tile*, RoomTavernGame>::iterator game = mGames.begin();
    while(game != mGames.end())
    {
        if((game->second.mCreatureA == creature) || (game->second.mCreatureB == creature))
        {
            abortGame(game);
            game = mGames.begin();
            continue;
        }
        ++game;
    }
}

bool RoomTavern::shouldStopUseIfHungrySleepy(Creature& creature, bool forced)
{
    std::map<Tile*, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    if(it == mSpots.end())
        return true;

    const TavernGuestState state = it->second.mState;
    return (state != TavernGuestState::game) && (state != TavernGuestState::ko) && (state != TavernGuestState::getUp);
}

bool RoomTavern::shouldNotUseIfBadMood(Creature& creature, bool forced)
{
    return shouldStopUseIfHungrySleepy(creature, forced);
}

bool RoomTavern::useRoom(Creature& creature, bool forced)
{
    std::map<Tile*, RoomTavernSpot>::iterator it = findSpotOf(&creature);
    if(it == mSpots.end())
    {
        OD_LOG_ERR("room=" + getName() + ", creature=" + creature.getName());
        creature.popAction();
        return true;
    }

    Tile* spotTile = it->first;
    RoomTavernSpot& spot = it->second;
    switch(spot.mState)
    {
        case TavernGuestState::arriving:
        {
            // Walk to the place; the walk is an action on top of this one, so we are called again when it is over
            if(creature.getPositionTile() != spotTile)
            {
                if(!creature.isMoving() && !creature.setDestination(spotTile))
                {
                    creature.popAction();
                    return true;
                }
                return false;
            }

            // On the place the first drink starts
            setSpotState(spot, TavernGuestState::drinking, static_cast<int32_t>(getTavernValue("DrinkTurns")));
            showSpotState(spotTile, spot);
            return false;
        }
        case TavernGuestState::done:
        {
            // The guest waits until the room has let the turns of the state pass
            if(spot.mTurnsLeft > 0)
                return false;

            // The visit is over. The loser of a slap duel goes to its bed, whatever its wakefulness
            const bool goToBed = spot.mSleepAfter && (creature.getHomeTile() != nullptr);
            creature.popAction();
            if(goToBed)
                creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
            return true;
        }
        default:
            // drinking, game, ko and getUp are run by doUpkeep
            return false;
    }
}

void RoomTavern::setSpotState(RoomTavernSpot& spot, TavernGuestState state, int32_t turns)
{
    spot.mState = state;
    spot.mTurnsLeft = turns;
}

void RoomTavern::setSpotDone(RoomTavernSpot& spot, int32_t turns)
{
    setSpotState(spot, TavernGuestState::done, turns);
    spot.mWantsGame = false;
    if((spot.mCreature != nullptr) && spot.mCreature->getIsOnMap())
        spot.mCreature->setAnimationState(EntityAnimation::idle_anim, true);
}

void RoomTavern::showSpotState(Tile* tile, RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    if((creature == nullptr) || !creature->getIsOnMap())
        return;

    switch(spot.mState)
    {
        case TavernGuestState::drinking:
        {
            // The guest looks at the counter while it drinks
            Ogre::Vector3 direction = Ogre::Vector3::ZERO;
            if(mCounterTile != nullptr)
                direction = directionTo(*creature, tileMiddle(*mCounterTile));
            creature->setAnimationState(EntityAnimation::drink_anim, true, direction, false);
            break;
        }
        case TavernGuestState::ko:
            creature->setAnimationState(EntityAnimation::knockedout_anim, true, Ogre::Vector3::ZERO, false);
            break;
        case TavernGuestState::getUp:
            creature->setAnimationState(EntityAnimation::getup_anim, false, Ogre::Vector3::ZERO, false);
            break;
        case TavernGuestState::game:
        {
            // The clip of the game, turned towards the opponent
            for(std::map<Tile*, RoomTavernGame>::iterator it = mGames.begin(); it != mGames.end(); ++it)
            {
                RoomTavernGame& game = it->second;
                Creature* opponent = nullptr;
                if(game.mCreatureA == creature)
                    opponent = game.mCreatureB;
                else if(game.mCreatureB == creature)
                    opponent = game.mCreatureA;
                if(opponent == nullptr)
                    continue;

                std::string clip = EntityAnimation::idle_anim;
                if(game.mKind == TavernGameKind::armWrestling)
                    clip = EntityAnimation::armwrestle_anim;
                else if(game.mKind == TavernGameKind::dice)
                    clip = EntityAnimation::dice_anim;
                creature->setAnimationState(clip, true, directionTo(*creature, opponent->getPosition()), false);
                break;
            }
            break;
        }
        default:
            creature->setAnimationState(EntityAnimation::idle_anim, true);
            break;
    }
}

bool RoomTavern::isGuestDisturbed(const Creature& creature)
{
    if(!creature.getIsOnMap() || !creature.isAlive() || creature.isKo() || creature.isBeingDragged())
        return true;

    return creature.isActionInList(CreatureActionType::fight) ||
        creature.isActionInList(CreatureActionType::fightFriendly) ||
        creature.isActionInList(CreatureActionType::flee);
}

void RoomTavern::playSoundAt(Tile* tile, const std::string& family)
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

void RoomTavern::doUpkeep()
{
    Room::doUpkeep();

    if(!getIsOnServerMap())
        return;

    resumeLoadedGuests();
    releaseGuestsOnLostTiles();
    abortDisturbedGuests();
    upkeepGames();
    upkeepSpots();

    // A guest that wants a game and waits for a neighbour looks for a partner again every turn
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if((it->second.mState == TavernGuestState::done) && it->second.mWantsGame && (it->second.mTurnsLeft > 0))
            tryStartGame(it->first);
    }

    // A guest that is done is looked for by a partner during these turns only
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if((it->second.mState == TavernGuestState::done) && (it->second.mTurnsLeft > 0))
            --it->second.mTurnsLeft;
    }
}

void RoomTavern::releaseGuestsOnLostTiles()
{
    std::vector<Creature*> lost;
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if(std::find(mCoveredTiles.begin(), mCoveredTiles.end(), it->first) == mCoveredTiles.end())
            lost.push_back(it->second.mCreature);
    }

    // Clearing the actions releases the places, so the guests are handled after the loop
    for(Creature* creature : lost)
        creature->clearActionQueue();
}

void RoomTavern::abortDisturbedGuests()
{
    // A fight, a flight, a knock-out or a hand that takes a guest away ends its game without effects
    std::map<Tile*, RoomTavernGame>::iterator game = mGames.begin();
    while(game != mGames.end())
    {
        if(isGuestDisturbed(*game->second.mCreatureA) || isGuestDisturbed(*game->second.mCreatureB))
        {
            abortGame(game);
            game = mGames.begin();
            continue;
        }
        ++game;
    }

    // A fight nearby ends the lying at once: the guest gets up and does not go to bed
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        RoomTavernSpot& spot = it->second;
        if((spot.mState != TavernGuestState::ko) && (spot.mState != TavernGuestState::getUp))
            continue;

        if(!isGuestDisturbed(*spot.mCreature))
            continue;

        spot.mSleepAfter = false;
        setSpotDone(spot, 0);
    }
}

void RoomTavern::upkeepSpots()
{
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        RoomTavernSpot& spot = it->second;
        switch(spot.mState)
        {
            case TavernGuestState::drinking:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                    finishDrink(it->first, spot);
                break;
            }
            case TavernGuestState::ko:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                {
                    setSpotState(spot, TavernGuestState::getUp, GET_UP_TURNS);
                    showSpotState(it->first, spot);
                }
                break;
            }
            case TavernGuestState::getUp:
            {
                --spot.mTurnsLeft;
                if(spot.mTurnsLeft <= 0)
                    setSpotDone(spot, 0);
                break;
            }
            default:
                break;
        }
    }
}

bool RoomTavern::payForBeer(Creature& creature, bool& noCoin)
{
    noCoin = false;
    const int32_t price = static_cast<int32_t>(std::floor(getTavernValue("BeerPrice") + 0.5));
    if(mPayer == TavernPayer::keeper)
        return getGameMap()->withdrawFromTreasuries(price, getSeat());

    if(creature.getGoldCarried() >= price)
    {
        creature.addGoldCarried(-price);
        getGameMap()->addGoldToSeat(price, getSeat()->getId());
        return true;
    }

    noCoin = true;
    return false;
}

void RoomTavern::finishDrink(Tile* tile, RoomTavernSpot& spot)
{
    Creature* creature = spot.mCreature;
    DrinkKind kind = DrinkKind::water;
    bool noCoin = false;
    if(servesBeer() && payForBeer(*creature, noCoin))
        kind = DrinkKind::beer;

    creature->drinkTaken(kind);
    if(kind == DrinkKind::beer)
        creature->addTavernMood(getTavernValue("BeerMood"), getTavernValue("BeerMoodTurns"));
    else if(noCoin)
        creature->addTavernMood(getTavernValue("NoCoinMood"), getTavernValue("NoCoinMoodTurns"));

    sendTavernEvent(*creature, static_cast<int32_t>((kind == DrinkKind::beer) ? CosmeticTavernKind::beer : CosmeticTavernKind::water), nullptr);
    addDrinkDirt(tile);
    if(mInnkeeper != nullptr)
        mInnkeeper->onDrink();
    playSoundAt(tile, SOUND_POUR);
    ++spot.mDrinks;

    // The guest decides itself about another drink: 50, 25, 12.5 and 6.25 percent after the 1st to the 4th drink,
    // never more than MaxDrinksPerVisit
    if(spot.mDrinks < static_cast<uint32_t>(getTavernValue("MaxDrinksPerVisit")))
    {
        const double nextDrinkPercent = getTavernValue("NextDrinkPercent") /
            std::pow(DRINK_CHAIN_HALVING, static_cast<double>(spot.mDrinks - 1));
        if(Random::Double(0.0, PERCENT_SCALE) < nextDrinkPercent)
        {
            setSpotState(spot, TavernGuestState::drinking, static_cast<int32_t>(getTavernValue("DrinkTurns")));
            showSpotState(tile, spot);
            return;
        }
    }

    // The visit is over. With GameChancePercent the guest wants a game and waits up to DrinkTurns turns for a neighbour
    setSpotDone(spot, DONE_WAIT_TURNS);
    if(Random::Double(0.0, PERCENT_SCALE) < getTavernValue("GameChancePercent"))
    {
        spot.mWantsGame = true;
        spot.mTurnsLeft = std::max(DONE_WAIT_TURNS, static_cast<int32_t>(getTavernValue("DrinkTurns")));
        tryStartGame(tile);
    }
}

void RoomTavern::tryStartGame(Tile* tile)
{
    std::map<Tile*, RoomTavernSpot>::iterator own = mSpots.find(tile);
    if((own == mSpots.end()) || !own->second.mWantsGame)
        return;

    // A neighbour on one of the four sides that is done too (and waits for the turns to pass) and of the same seat
    static const int32_t NEIGHBOUR_DX[] = { 1, -1, 0, 0 };
    static const int32_t NEIGHBOUR_DY[] = { 0, 0, 1, -1 };
    static const uint32_t NB_NEIGHBOURS = 4;
    std::vector<Tile*> partners;
    for(uint32_t i = 0; i < NB_NEIGHBOURS; ++i)
    {
        Tile* neighbour = getGameMap()->getTile(tile->getX() + NEIGHBOUR_DX[i], tile->getY() + NEIGHBOUR_DY[i]);
        if(neighbour == nullptr)
            continue;

        std::map<Tile*, RoomTavernSpot>::iterator other = mSpots.find(neighbour);
        if(other == mSpots.end())
            continue;

        if((other->second.mState != TavernGuestState::done) || (other->second.mTurnsLeft <= 0))
            continue;

        if(other->second.mCreature->getSeat() != own->second.mCreature->getSeat())
            continue;

        partners.push_back(neighbour);
    }

    if(partners.empty())
        return;

    startGame(tile, partners[Random::Uint(0, static_cast<uint32_t>(partners.size()) - 1)]);
}

void RoomTavern::startGame(Tile* tileA, Tile* tileB)
{
    std::map<Tile*, RoomTavernSpot>::iterator spotA = mSpots.find(tileA);
    std::map<Tile*, RoomTavernSpot>::iterator spotB = mSpots.find(tileB);
    if((spotA == mSpots.end()) || (spotB == mSpots.end()))
        return;

    // Arm wrestling and dice with the same chance; the slap duel joins the draw when beer is served
    const uint32_t nbGames = servesBeer() ? NB_GAMES_WITH_BEER : NB_GAMES_WITHOUT_BEER;
    RoomTavernGame game;
    game.mKind = static_cast<TavernGameKind>(Random::Uint(0, nbGames - 1));
    game.mTileA = tileA;
    game.mTileB = tileB;
    game.mCreatureA = spotA->second.mCreature;
    game.mCreatureB = spotB->second.mCreature;
    game.mTurnIsA = true;
    if(game.mKind == TavernGameKind::slapDuel)
        game.mTurnsLeft = DUEL_MAX_TURNS_FACTOR * static_cast<int32_t>(getTavernValue("GameTurns"));
    else
        game.mTurnsLeft = static_cast<int32_t>(getTavernValue("GameTurns"));
    mGames[tileA] = game;

    spotA->second.mWantsGame = false;
    spotB->second.mWantsGame = false;
    setSpotState(spotA->second, TavernGuestState::game, 0);
    setSpotState(spotB->second, TavernGuestState::game, 0);
    showSpotState(tileA, spotA->second);
    showSpotState(tileB, spotB->second);
}

void RoomTavern::upkeepGames()
{
    std::map<Tile*, RoomTavernGame>::iterator it = mGames.begin();
    while(it != mGames.end())
    {
        // A game that ends erases itself, so the next entry is taken first
        std::map<Tile*, RoomTavernGame>::iterator current = it;
        ++it;
        if(current->second.mKind == TavernGameKind::slapDuel)
            playDuelTurn(current);
        else
            playContestTurn(current);
    }
}

void RoomTavern::playContestTurn(std::map<Tile*, RoomTavernGame>::iterator it)
{
    RoomTavernGame& game = it->second;
    --game.mTurnsLeft;
    if(game.mTurnsLeft > 0)
        return;

    // The weaker creature wins with 50 percent minus 2.5 points per level of difference, never below 5 percent
    Creature* lower = game.mCreatureA;
    Creature* higher = game.mCreatureB;
    if(lower->getLevel() > higher->getLevel())
        std::swap(lower, higher);

    const uint32_t levelDifference = higher->getLevel() - lower->getLevel();
    const double lowerPercent = std::max(getTavernValue("GameUnderdogMinPercent"),
        getTavernValue("GameUnderdogBasePercent") - getTavernValue("GameUnderdogPerLevel") * levelDifference);
    if(Random::Double(0.0, PERCENT_SCALE) < lowerPercent)
        concludeGame(it, lower, levelDifference);
    else
        concludeGame(it, higher, 0);
}

void RoomTavern::playDuelTurn(std::map<Tile*, RoomTavernGame>::iterator it)
{
    RoomTavernGame& game = it->second;
    Creature* slapper = game.mTurnIsA ? game.mCreatureA : game.mCreatureB;
    Creature* target = game.mTurnIsA ? game.mCreatureB : game.mCreatureA;
    uint32_t& targetSlaps = game.mTurnIsA ? game.mSlapsTakenB : game.mSlapsTakenA;

    // The slapper swings; a miss passes the turn
    slapper->setAnimationState(EntityAnimation::slap_anim, false, directionTo(*slapper, target->getPosition()), true);
    playSoundAt(slapper->getPositionTile(), SOUND_SLAP);
    if(target->rollAttackHit(slapper->getAttackRating(), slapper->getLevel(), slapper->isPossessed()))
    {
        // A critical slap (10 percent at equal level, 0.25 points per level of difference) wins the duel at once
        const double levelDifference = static_cast<double>(slapper->getLevel()) - static_cast<double>(target->getLevel());
        const double criticalPercent = getTavernValue("SlapCritBasePercent") +
            getTavernValue("SlapCritPerLevel") * levelDifference;
        if(Random::Double(0.0, PERCENT_SCALE) < criticalPercent)
        {
            concludeGame(it, slapper, 0);
            return;
        }

        // A normal slap takes SlapDamage hit points but never the last one
        const double damage = std::max(0.0, std::min(getTavernValue("SlapDamage"), target->getHP() - 1.0));
        target->takeDamage(slapper, damage, 0.0, 0.0, 0.0, target->getPositionTile(), false);
        ++targetSlaps;
        if(target->getHP() < getTavernValue("SlapDuelLoseBelowHp"))
        {
            concludeGame(it, slapper, 0);
            return;
        }
    }

    game.mTurnIsA = !game.mTurnIsA;
    --game.mTurnsLeft;
    if(game.mTurnsLeft > 0)
        return;

    // No decision: the one with more hit points left wins, a tie is decided by chance
    Creature* winner = game.mCreatureA;
    if(game.mCreatureB->getHP() > game.mCreatureA->getHP())
        winner = game.mCreatureB;
    else if((game.mCreatureB->getHP() == game.mCreatureA->getHP()) && (Random::Uint(0, 1) == 1))
        winner = game.mCreatureB;
    concludeGame(it, winner, 0);
}

void RoomTavern::cheerSpectators(const RoomTavernGame& game)
{
    const int32_t radius = static_cast<int32_t>(getTavernValue("GameSpectatorRadius"));
    for(Creature* creature : getGameMap()->getCreaturesBySeat(getSeat()))
    {
        if((creature == game.mCreatureA) || (creature == game.mCreatureB) || creature->isPossessed() ||
           !creature->getIsOnMap() || !creature->isAlive())
            continue;

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        // Within the radius (Chebyshev distance) of one of the two players
        const int32_t distanceA = std::max(std::abs(tile->getX() - game.mTileA->getX()),
            std::abs(tile->getY() - game.mTileA->getY()));
        const int32_t distanceB = std::max(std::abs(tile->getX() - game.mTileB->getX()),
            std::abs(tile->getY() - game.mTileB->getY()));
        if(std::min(distanceA, distanceB) <= radius)
            creature->addTavernMood(getTavernValue("GameSpectatorMood"), getTavernValue("BeerMoodTurns"));
    }
}

void RoomTavern::concludeGame(std::map<Tile*, RoomTavernGame>::iterator it, Creature* winner, uint32_t underdogLevels)
{
    RoomTavernGame game = it->second;
    mGames.erase(it);

    Creature* loser = (winner == game.mCreatureA) ? game.mCreatureB : game.mCreatureA;
    double winnerMood = getTavernValue("GameWinnerMood");
    double winnerXp = getTavernValue("GameWinnerXp");
    if(underdogLevels > 0)
    {
        // The weaker creature that wins gets more mood and double experience
        winnerMood = std::min(getTavernValue("GameUnderdogMoodMax"),
            winnerMood + getTavernValue("GameUnderdogMoodPerLevel") * underdogLevels);
        winnerXp *= 2.0;
    }
    winner->addTavernMood(winnerMood, getTavernValue("BeerMoodTurns"));
    winner->receiveExp(winnerXp);
    cheerSpectators(game);

    // Only a slap duel is told to the clients (bubbles and posts of the winner and the loser)
    if(game.mKind == TavernGameKind::slapDuel)
    {
        sendTavernEvent(*winner, static_cast<int32_t>(CosmeticTavernKind::duelWon), loser);
        sendTavernEvent(*loser, static_cast<int32_t>(CosmeticTavernKind::duelLost), winner);
    }

    if(mInnkeeper != nullptr)
        mInnkeeper->onCheer();
    playSoundAt(mCounterTile, SOUND_CHEER);

    // Both players are done; the loser of a slap duel goes down
    std::map<Tile*, RoomTavernSpot>::iterator winnerSpot = findSpotOf(winner);
    if(winnerSpot != mSpots.end())
        setSpotDone(winnerSpot->second, 0);

    std::map<Tile*, RoomTavernSpot>::iterator loserSpot = findSpotOf(loser);
    if(loserSpot == mSpots.end())
        return;

    if(game.mKind == TavernGameKind::slapDuel)
    {
        loser->addTavernMood(getTavernValue("GameLoserMood"), getTavernValue("BeerMoodTurns"));
        knockOut(loserSpot->second);
    }
    else
    {
        setSpotDone(loserSpot->second, 0);
    }
}

void RoomTavern::abortGame(std::map<Tile*, RoomTavernGame>::iterator it)
{
    RoomTavernGame game = it->second;
    mGames.erase(it);

    // Both guests are done; one of them may have left the room already
    std::map<Tile*, RoomTavernSpot>::iterator spotA = findSpotOf(game.mCreatureA);
    if(spotA != mSpots.end())
        setSpotDone(spotA->second, 0);

    std::map<Tile*, RoomTavernSpot>::iterator spotB = findSpotOf(game.mCreatureB);
    if(spotB != mSpots.end())
        setSpotDone(spotB->second, 0);
}

void RoomTavern::knockOut(RoomTavernSpot& spot)
{
    spot.mSleepAfter = true;
    setSpotState(spot, TavernGuestState::ko, static_cast<int32_t>(getTavernValue("DuelKoTurns")));
    showSpotState(nullptr, spot);
}

void RoomTavern::resumeLoadedGuests()
{
    if(mPendingSpots.empty() && mPendingGames.empty())
        return;

    // The creatures take their saved places again; the use of the room binds them in addCreatureUsingRoom
    std::vector<std::string> names;
    for(std::map<std::string, RoomTavernPendingSpot>::iterator it = mPendingSpots.begin(); it != mPendingSpots.end(); ++it)
        names.push_back(it->first);

    for(const std::string& name : names)
    {
        Creature* creature = getGameMap()->getCreature(name);
        if((creature == nullptr) || !creature->isAlive() || !creature->getIsOnMap() || (creature->getSeat() != getSeat()))
            continue;

        if(!creature->isActionInList(CreatureActionType::useRoom))
            creature->pushAction(Utils::make_unique<CreatureActionUseRoom>(*creature, *this, false));
    }
    mPendingSpots.clear();

    // A game goes on when both of its guests are back; otherwise it ends without effects
    for(const RoomTavernPendingGame& saved : mPendingGames)
    {
        Creature* creatureA = getGameMap()->getCreature(saved.mNameA);
        Creature* creatureB = getGameMap()->getCreature(saved.mNameB);
        std::map<Tile*, RoomTavernSpot>::iterator spotA = findSpotOf(creatureA);
        std::map<Tile*, RoomTavernSpot>::iterator spotB = findSpotOf(creatureB);
        if((creatureA == nullptr) || (creatureB == nullptr) || (spotA == mSpots.end()) || (spotB == mSpots.end()) ||
           (spotA->second.mState != TavernGuestState::game) || (spotB->second.mState != TavernGuestState::game))
            continue;

        RoomTavernGame game;
        game.mKind = saved.mKind;
        game.mTileA = spotA->first;
        game.mTileB = spotB->first;
        game.mCreatureA = creatureA;
        game.mCreatureB = creatureB;
        game.mTurnsLeft = saved.mTurnsLeft;
        game.mSlapsTakenA = saved.mSlapsTakenA;
        game.mSlapsTakenB = saved.mSlapsTakenB;
        game.mTurnIsA = saved.mTurnIsA;
        mGames[game.mTileA] = game;
        showSpotState(spotA->first, spotA->second);
        showSpotState(spotB->first, spotB->second);
    }
    mPendingGames.clear();

    // A guest in a game whose partner did not come back is done
    for(std::map<Tile*, RoomTavernSpot>::iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        if(it->second.mState != TavernGuestState::game)
            continue;

        bool inGame = false;
        for(std::map<Tile*, RoomTavernGame>::iterator game = mGames.begin(); game != mGames.end(); ++game)
        {
            if((game->second.mCreatureA == it->second.mCreature) || (game->second.mCreatureB == it->second.mCreature))
                inGame = true;
        }
        if(!inGame)
            setSpotDone(it->second, 0);
    }
}

void RoomTavern::addDrinkDirt(Tile* tile)
{
    if(tile == nullptr)
        return;

    tile->addDirt(ConfigManager::getSingleton().getRoomConfigDouble("TavernDirtPerDrink"));
}

void RoomTavern::sendTavernEvent(Creature& creature, int32_t kind, const Creature* opponent)
{
    Tile* tile = creature.getPositionTile();
    if(tile == nullptr)
        return;

    CosmeticEvent event(CosmeticEventType::tavernEvent);
    event.mSubject = creature.getName();
    if(opponent != nullptr)
        event.mObject = opponent->getName();
    event.mValue = kind;
    event.mPosition = creature.getPosition();

    // The keepers that see the tile and the keeper of the creature itself (its post is written on its own client)
    std::vector<Seat*> receivers = tile->getSeatsWithVision();
    if((creature.getSeat() != nullptr) && (std::find(receivers.begin(), receivers.end(), creature.getSeat()) == receivers.end()))
        receivers.push_back(creature.getSeat());

    for(Seat* seat : receivers)
    {
        if((seat->getPlayer() == nullptr) || !seat->getPlayer()->getIsHuman())
            continue;

        ODServer::getSingleton().sendCosmeticEvent(seat->getPlayer(), event);
    }
}

bool RoomTavern::servesBeer() const
{
    return (getSeat() != nullptr) && (getSeat()->getSkillLevel(SkillType::tavernBeer) >= 1);
}

void RoomTavern::setupRoom(const std::string& name, Seat* seat, const std::vector<Tile*>& tiles)
{
    Room::setupRoom(name, seat, tiles);

    if(!tiles.empty())
        mCounterTile = tiles.front();

    // The computer keepers let their creatures pay for the beer
    if((seat != nullptr) && (seat->getPlayer() != nullptr) && !seat->getPlayer()->getIsHuman())
        mPayer = TavernPayer::creature;
}

bool RoomTavern::hasPlacedCounter() const
{
    if(mCounterTile == nullptr)
        return false;

    std::map<Tile*, BuildingObject*>::const_iterator it = mBuildingObjects.find(mCounterTile);
    if(it == mBuildingObjects.end())
        return false;

    return it->second->getMeshName() == TAVERN_COUNTER_MESH;
}

void RoomTavern::absorbRoom(Room* r)
{
    if(r->getType() != getType())
    {
        OD_LOG_ERR("Trying to merge incompatible rooms: " + getName() + ", type=" + RoomManager::getRoomNameFromRoomType(getType()) + ", with " + r->getName() + ", type=" + RoomManager::getRoomNameFromRoomType(r->getType()));
        return;
    }

    // The room that already has its counter and innkeeper is the older one and keeps them with its payer setting. The
    // room that is built last has only picked a counter tile so far; the other room has its objects.
    RoomTavern* other = static_cast<RoomTavern*>(r);
    if(!hasPlacedCounter() && other->hasPlacedCounter())
    {
        mCounterTile = other->mCounterTile;
        mPayer = other->mPayer;
    }

    // The figure of the other room goes away; updateActiveSpots puts one on the counter of the merged room
    other->removeInnkeeper();
    other->mCounterTile = nullptr;

    Room::absorbRoom(r);
}

void RoomTavern::splitRoom(Room& newRoom, const std::vector<Tile*>& tiles)
{
    if(newRoom.getType() != getType())
        return;

    // The room that gets the tiles keeps the payer setting of this one, also when the seat changes
    RoomTavern& newTavern = static_cast<RoomTavern&>(newRoom);
    newTavern.mPayer = mPayer;

    // The counter stays where it was when its tile goes over with the others
    if((mCounterTile != nullptr) && (std::find(tiles.begin(), tiles.end(), mCounterTile) != tiles.end()))
        newTavern.mCounterTile = mCounterTile;
}

bool RoomTavern::removeCoveredTile(Tile* t)
{
    if(!Room::removeCoveredTile(t))
        return false;

    // A guest drinking on the tile, or walking to it, stops: a game it plays ends without winner and without effects.
    // Clearing its actions releases it from the room, so we work on a copy.
    std::vector<Creature*> guests = mCreaturesUsingRoom;
    for(Creature* guest : guests)
    {
        std::map<Tile*, RoomTavernSpot>::iterator spot = findSpotOf(guest);
        const bool hasSpotOnTile = (spot != mSpots.end()) && (spot->first == t);
        if((guest->getPositionTile() == t) || hasSpotOnTile)
            guest->clearActionQueue();
    }

    // The next remaining tile becomes the counter; the innkeeper follows in updateActiveSpots
    if(t == mCounterTile)
    {
        if(mCoveredTiles.empty())
            mCounterTile = nullptr;
        else
            mCounterTile = mCoveredTiles.front();
    }

    return true;
}

void RoomTavern::removeFromGameMap(GameMap* gameMap)
{
    removeInnkeeper();
    Room::removeFromGameMap(gameMap);
}

void RoomTavern::removeInnkeeper()
{
    if(mInnkeeper == nullptr)
        return;

    mInnkeeper->removeFromRoom();
    mInnkeeper = nullptr;
}

double RoomTavern::getBackToWallAngle(const Tile* tile, bool& isNextToWall) const
{
    GameMap* gameMap = getGameMap();
    const int x = tile->getX();
    const int y = tile->getY();
    isNextToWall = true;

    Tile* top = gameMap->getTile(x, y + 1);
    if((top == nullptr) || (top->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_TOP;

    Tile* bottom = gameMap->getTile(x, y - 1);
    if((bottom == nullptr) || (bottom->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_BOTTOM;

    Tile* left = gameMap->getTile(x - 1, y);
    if((left == nullptr) || (left->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_LEFT;

    Tile* right = gameMap->getTile(x + 1, y);
    if((right == nullptr) || (right->getCoveringRoom() != this))
        return OBJECT_ANGLE_WALL_RIGHT;

    // A tile in the middle of the room: all four neighbours are part of it
    isNextToWall = false;
    return OBJECT_ANGLE_WALL_TOP;
}

void RoomTavern::placeInnkeeper()
{
    if(mCounterTile == nullptr)
        return;

    bool isNextToWall = false;
    const Ogre::Real angle = static_cast<Ogre::Real>(getBackToWallAngle(mCounterTile, isNextToWall));

    // The figure is turned like the counter. One that stands elsewhere or looks the wrong way is spawned again, since
    // the angle of an entity cannot be changed.
    if((mInnkeeper != nullptr) && ((mInnkeeper->getPositionTile() != mCounterTile) || (mInnkeeper->getRotationAngle() != angle)))
        removeInnkeeper();

    if(mInnkeeper == nullptr)
        mInnkeeper = InnkeeperEntity::spawnOnTile(getGameMap(), getName(), mCounterTile, angle);
}

//! \brief Updates tavern furniture and the innkeeper for the current room tiles.
void RoomTavern::updateActiveSpots(GameMap* gameMap)
{
    Room::updateActiveSpots(gameMap);

    // The objects and the figure are created by the server and sent to the clients like every other entity
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
        removeBuildingObject(tile);

    // A room without tiles has neither counter nor innkeeper
    if(mCoveredTiles.empty())
    {
        mCounterTile = nullptr;
        removeInnkeeper();
        return;
    }

    // The first tile is the counter tile, also when the old counter tile is gone
    if((mCounterTile == nullptr) || (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), mCounterTile) == mCoveredTiles.end()))
        mCounterTile = mCoveredTiles.front();

    // Select furniture in coordinate order so the same room restores the same placement after loading.
    std::vector<Tile*> orderedTiles = mCoveredTiles;
    std::sort(orderedTiles.begin(), orderedTiles.end(), Room::compareTile);
    std::map<Tile*, std::string> wantedObjects;
    std::map<Tile*, double> kegAngles;
    wantedObjects[mCounterTile] = TAVERN_COUNTER_MESH;
    const size_t kegLimit = orderedTiles.size() / 6;
    const size_t tableLimit = orderedTiles.size() / 4;
    size_t kegs = 0;
    for(Tile* tile : orderedTiles)
    {
        if((tile == mCounterTile) || (kegs >= kegLimit))
            continue;
        const int x = tile->getX();
        const int y = tile->getY();
        Tile* neighbours[] = {gameMap->getTile(x, y + 1), gameMap->getTile(x, y - 1),
                              gameMap->getTile(x - 1, y), gameMap->getTile(x + 1, y)};
        const double angles[] = {OBJECT_ANGLE_WALL_TOP, OBJECT_ANGLE_WALL_BOTTOM,
                                 OBJECT_ANGLE_WALL_LEFT, OBJECT_ANGLE_WALL_RIGHT};
        for(size_t i = 0; i < 4; ++i)
        {
            Tile* neighbour = neighbours[i];
            if((neighbour != nullptr) && neighbour->isFullTile())
            {
                wantedObjects[tile] = TAVERN_KEG_MESH;
                kegAngles[tile] = angles[i];
                ++kegs;
                break;
            }
        }
    }
    size_t tables = 0;
    for(Tile* tile : orderedTiles)
    {
        if((tables >= tableLimit) || (wantedObjects.count(tile) != 0))
            continue;
        wantedObjects[tile] = TAVERN_TABLE_MESH;
        ++tables;
    }

    // Replace obsolete furniture and leave every unselected tile as free floor.
    for(Tile* tile : orderedTiles)
    {
        std::map<Tile*, std::string>::const_iterator wanted = wantedObjects.find(tile);
        std::map<Tile*, BuildingObject*>::iterator existing = mBuildingObjects.find(tile);
        if(existing != mBuildingObjects.end())
        {
            if((wanted != wantedObjects.end()) && (existing->second->getMeshName() == wanted->second))
                continue;
            removeBuildingObject(tile);
        }
        if(wanted == wantedObjects.end())
            continue;
        bool isNextToWall = false;
        const double angle = (wanted->second == TAVERN_KEG_MESH) ? kegAngles[tile] : getBackToWallAngle(tile, isNextToWall);
        BuildingObject* object = new BuildingObject(gameMap, *this, wanted->second, *tile, angle, false);
        addBuildingObject(tile, object, gameMap);
        object->createMesh();
    }

    placeInnkeeper();
}

void RoomTavern::exportToStream(std::ostream& os) const
{
    Room::exportToStream(os);
    os << STREAM_TAG_PAYER << " " << static_cast<uint32_t>(mPayer) << std::endl;
    if(mCounterTile == nullptr)
        return;

    if(mInnkeeper != nullptr)
        os << STREAM_TAG_INNKEEPER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;

    os << STREAM_TAG_COUNTER << " " << mCounterTile->getX() << " " << mCounterTile->getY() << std::endl;

    // Spot <x> <y> <creature> <state> <turnsLeft> <drinks> <sleepAfter>: one line for every guest
    for(std::map<Tile*, RoomTavernSpot>::const_iterator it = mSpots.begin(); it != mSpots.end(); ++it)
    {
        const RoomTavernSpot& spot = it->second;
        if(spot.mCreature == nullptr)
            continue;

        os << STREAM_TAG_SPOT << " " << it->first->getX() << " " << it->first->getY() << " " << spot.mCreature->getName()
           << " " << guestStateToString(spot.mState) << " " << spot.mTurnsLeft << " " << spot.mDrinks << " "
           << (spot.mSleepAfter ? 1 : 0) << std::endl;
    }

    // Game <kind> <xA> <yA> <xB> <yB> <creatureA> <creatureB> <turnsLeft> <slapsA> <slapsB> <turn>: one line for every
    // running game (turn: 0 = the first guest slaps next, 1 = the second)
    for(std::map<Tile*, RoomTavernGame>::const_iterator it = mGames.begin(); it != mGames.end(); ++it)
    {
        const RoomTavernGame& game = it->second;
        os << STREAM_TAG_GAME << " " << static_cast<uint32_t>(game.mKind) << " " << game.mTileA->getX() << " "
           << game.mTileA->getY() << " " << game.mTileB->getX() << " " << game.mTileB->getY() << " "
           << game.mCreatureA->getName() << " " << game.mCreatureB->getName() << " " << game.mTurnsLeft << " "
           << game.mSlapsTakenA << " " << game.mSlapsTakenB << " " << (game.mTurnIsA ? 0 : 1) << std::endl;
    }
}

bool RoomTavern::importFromStream(std::istream& is)
{
    if(!Room::importFromStream(is))
        return false;

    // The lines come after the tiles of the room, in any order, and every one of them is optional. The first word that
    // is none of them belongs to what follows in the stream: it is put back.
    Tile* innkeeperTile = nullptr;
    Tile* counterTile = nullptr;
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
            if(!(is >> payer) || (payer > static_cast<uint32_t>(TavernPayer::creature)))
                return false;

            mPayer = static_cast<TavernPayer>(payer);
        }
        else if(tag == STREAM_TAG_INNKEEPER)
        {
            if(!readTileFromStream(getGameMap(), is, innkeeperTile))
                return false;
        }
        else if(tag == STREAM_TAG_COUNTER)
        {
            if(!readTileFromStream(getGameMap(), is, counterTile))
                return false;
        }
        else if(tag == STREAM_TAG_SPOT)
        {
            // The rest of the line: x y creature state turnsLeft [drinks sleepAfter]
            std::string rest;
            std::getline(is, rest);
            std::istringstream line(rest);
            int32_t x = 0;
            int32_t y = 0;
            std::string name;
            std::string stateToken;
            RoomTavernPendingSpot saved;
            if(!(line >> x >> y >> name >> stateToken >> saved.mTurnsLeft) || !guestStateFromString(stateToken, saved.mState))
                return false;

            int32_t sleepAfter = 0;
            line >> saved.mDrinks >> sleepAfter;
            saved.mSleepAfter = (sleepAfter != 0);
            saved.mTile = getGameMap()->getTile(x, y);
            if(saved.mTile != nullptr)
                mPendingSpots[name] = saved;
        }
        else if(tag == STREAM_TAG_GAME)
        {
            // The rest of the line: kind xA yA xB yB creatureA creatureB turnsLeft slapsA slapsB turn
            std::string rest;
            std::getline(is, rest);
            std::istringstream line(rest);
            uint32_t kind = 0;
            int32_t xA = 0;
            int32_t yA = 0;
            int32_t xB = 0;
            int32_t yB = 0;
            int32_t turn = 0;
            RoomTavernPendingGame saved;
            if(!(line >> kind >> xA >> yA >> xB >> yB >> saved.mNameA >> saved.mNameB >> saved.mTurnsLeft >>
                 saved.mSlapsTakenA >> saved.mSlapsTakenB >> turn) ||
               (kind > static_cast<uint32_t>(TavernGameKind::slapDuel)))
                return false;

            saved.mKind = static_cast<TavernGameKind>(kind);
            saved.mTileA = getGameMap()->getTile(xA, yA);
            saved.mTileB = getGameMap()->getTile(xB, yB);
            saved.mTurnIsA = (turn == 0);
            mPendingGames.push_back(saved);
        }
        else
        {
            is.clear();
            is.seekg(pos);
            break;
        }
    }

    // The innkeeper stands on the counter tile, so its tile tells the counter if the counter line is missing. A tile
    // that is not part of the room is ignored: updateActiveSpots takes the first tile then.
    Tile* wantedCounter = (counterTile != nullptr) ? counterTile : innkeeperTile;
    if((wantedCounter != nullptr) && (std::find(mCoveredTiles.begin(), mCoveredTiles.end(), wantedCounter) != mCoveredTiles.end()))
        mCounterTile = wantedCounter;

    return true;
}
