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

#include "gamemap/TileDirtSync.h"

#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/CosmeticEvent.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"

#include <algorithm>
#include <sstream>

//! \brief The multiplier of x in the key of a tile (the map is never wider than this).
static const int64_t TILE_KEY_FACTOR = 65536;
//! \brief Separator between two entries of the event text.
static const char ENTRY_SEPARATOR = ';';
//! \brief Separator between the tile part and the room part of the event text.
static const char PART_SEPARATOR = '|';
//! \brief Separator between the fields of one entry of the event text.
static const char FIELD_SEPARATOR = ',';
//! \brief The words of the dirt stages 1 to 3 of a room.
static const char* const STAGE_TEXT_CLEAN = "clean";
static const char* const STAGE_TEXT_DIRTY = "dirty";
static const char* const STAGE_TEXT_FILTHY = "filthy";

//! \brief The stage of a room that is clean (stage 1).
static const int32_t STAGE_CLEAN = 1;
//! \brief The stage of a room that is dirty (stage 2).
static const int32_t STAGE_DIRTY = 2;

TileDirtSync::TileDirtSync() :
    mRefreshedTurn(-1)
{
}

void TileDirtSync::addChangedTile(Tile* tile)
{
    if(tile == nullptr)
        return;

    mChanged.push_back(tile);
}

int64_t TileDirtSync::makeKey(int32_t x, int32_t y)
{
    return static_cast<int64_t>(x) * TILE_KEY_FACTOR + y;
}

int32_t TileDirtSync::stageForValue(double dirt)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    if((dirt <= 0.0) || (dirt < config.getDirtConfigDouble("DirtVisibleFrom")))
        return 0;

    if(dirt < config.getDirtConfigDouble("DirtStage2At"))
        return 1;

    if(dirt < config.getDirtConfigDouble("DirtStage3At"))
        return 2;

    return 3;
}

std::string TileDirtSync::stageText(uint32_t stage)
{
    if(stage <= static_cast<uint32_t>(STAGE_CLEAN))
        return STAGE_TEXT_CLEAN;

    if(stage <= static_cast<uint32_t>(STAGE_DIRTY))
        return STAGE_TEXT_DIRTY;

    return STAGE_TEXT_FILTHY;
}

bool TileDirtSync::isStageShown(RoomType type)
{
    switch(type)
    {
        case RoomType::crypt:
        case RoomType::treasury:
        case RoomType::portal:
        case RoomType::portalWave:
        case RoomType::dungeonTemple:
        case RoomType::bridgeWooden:
        case RoomType::bridgeStone:
            return false;
        default:
            break;
    }

    return true;
}

//! \brief Tells whether a seat has vision on a tile.
//! \param tile The tile to check.
//! \param seat The seat of the keeper.
static bool isSeenBySeat(Tile* tile, const Seat* seat)
{
    const std::vector<Seat*>& seats = tile->getSeatsWithVision();
    return std::find(seats.begin(), seats.end(), seat) != seats.end();
}

//! \brief Tells whether a seat has vision on at least one tile of a room.
//! \param tiles The tiles of the room.
//! \param seat The seat of the keeper.
static bool isRoomSeenBySeat(const std::vector<Tile*>& tiles, const Seat* seat)
{
    for(Tile* tile : tiles)
    {
        if(isSeenBySeat(tile, seat))
            return true;
    }

    return false;
}

void TileDirtSync::refresh(GameMap* gameMap)
{
    if((gameMap == nullptr) || (gameMap->getTurnNumber() == mRefreshedTurn))
        return;

    mRefreshedTurn = gameMap->getTurnNumber();
    for(Tile* tile : mChanged)
    {
        tile->clearDirtChanged();
        const int64_t key = makeKey(tile->getX(), tile->getY());
        const int32_t stage = stageForValue(tile->getDirt());
        if(stage > 0)
            mStages[key] = stage;
        else
            mStages.erase(key);
    }
    mChanged.clear();

    // The rooms follow the tiles (and rooms that were built or sold)
    mRoomStages.clear();
    for(Room* room : gameMap->getRooms())
    {
        if(!isStageShown(room->getType()))
            continue;

        mRoomStages[room->getName()] = static_cast<int32_t>(room->getDirtStage());
    }
}

bool TileDirtSync::buildEvent(GameMap* gameMap, Seat* seat, TileDirtClientState& state, CosmeticEvent& event)
{
    if((gameMap == nullptr) || (seat == nullptr))
        return false;

    const ConfigManager& config = ConfigManager::getSingleton();
    const uint32_t syncTurns = static_cast<uint32_t>(config.getDirtConfigDouble("DirtSyncTurns"));
    const uint32_t resyncTurns = static_cast<uint32_t>(config.getDirtConfigDouble("DirtResyncTurns"));
    ++state.mSyncWait;
    ++state.mResyncWait;
    const bool resend = state.mFirst || (state.mResyncWait >= resyncTurns);
    if(!resend && (state.mSyncWait < syncTurns))
        return false;

    state.mFirst = false;
    state.mSyncWait = 0;
    if(resend)
        state.mResyncWait = 0;

    std::ostringstream tiles;
    bool firstTile = true;
    // Dirty tiles in sight: new ones, changed ones, and all of them on a resend
    for(std::map<int64_t, int32_t>::const_iterator it = mStages.begin(); it != mStages.end(); ++it)
    {
        const int32_t x = static_cast<int32_t>(it->first / TILE_KEY_FACTOR);
        const int32_t y = static_cast<int32_t>(it->first % TILE_KEY_FACTOR);
        Tile* tile = gameMap->getTile(x, y);
        if((tile == nullptr) || !isSeenBySeat(tile, seat))
            continue;

        std::map<int64_t, int32_t>::iterator sentIt = state.mTiles.find(it->first);
        if(!resend && (sentIt != state.mTiles.end()) && (sentIt->second == it->second))
            continue;

        state.mTiles[it->first] = it->second;
        if(!firstTile)
            tiles << ENTRY_SEPARATOR;
        firstTile = false;
        tiles << x << FIELD_SEPARATOR << y << FIELD_SEPARATOR << it->second;
    }

    // Tiles the client was told about that are clean now and in sight
    std::map<int64_t, int32_t>::iterator sentIt = state.mTiles.begin();
    while(sentIt != state.mTiles.end())
    {
        if(mStages.find(sentIt->first) != mStages.end())
        {
            ++sentIt;
            continue;
        }

        const int32_t x = static_cast<int32_t>(sentIt->first / TILE_KEY_FACTOR);
        const int32_t y = static_cast<int32_t>(sentIt->first % TILE_KEY_FACTOR);
        Tile* tile = gameMap->getTile(x, y);
        if((tile == nullptr) || !isSeenBySeat(tile, seat))
        {
            ++sentIt;
            continue;
        }

        if(!firstTile)
            tiles << ENTRY_SEPARATOR;
        firstTile = false;
        tiles << x << FIELD_SEPARATOR << y << FIELD_SEPARATOR << 0;
        state.mTiles.erase(sentIt++);
    }

    std::ostringstream rooms;
    bool firstRoom = true;
    for(Room* room : gameMap->getRooms())
    {
        std::map<std::string, int32_t>::const_iterator stageIt = mRoomStages.find(room->getName());
        if(stageIt == mRoomStages.end())
            continue;

        std::map<std::string, int32_t>::iterator sentRoomIt = state.mRooms.find(room->getName());
        if(!resend && (sentRoomIt != state.mRooms.end()) && (sentRoomIt->second == stageIt->second))
            continue;

        if(!isRoomSeenBySeat(room->getCoveredTiles(), seat))
            continue;

        state.mRooms[room->getName()] = stageIt->second;
        if(!firstRoom)
            rooms << ENTRY_SEPARATOR;
        firstRoom = false;
        rooms << room->getName() << FIELD_SEPARATOR << stageIt->second;
    }

    if(firstTile && firstRoom)
        return false;

    event = CosmeticEvent(CosmeticEventType::tileDirt);
    event.mValue = resend ? 1 : 0;
    event.mText = tiles.str();
    if(!firstRoom)
        event.mText += std::string(1, PART_SEPARATOR) + rooms.str();

    return true;
}
