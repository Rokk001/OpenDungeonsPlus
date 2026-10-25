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

#ifndef TILEDIRTSYNC_H
#define TILEDIRTSYNC_H

#include <cstdint>
#include <map>
#include <string>
#include <vector>

class GameMap;
class Seat;
class Tile;
struct CosmeticEvent;
enum class RoomType;

//! \brief What the server remembers about the dirt it has told one client (cosmetic event tileDirt).
struct TileDirtClientState
{
    TileDirtClientState() :
        mFirst(true),
        mSyncWait(0),
        mResyncWait(0)
    {}

    //! The dirt stage (1 - 3) of a floor tile as last sent, by TileDirtSync::makeKey. A tile that is missing is clean
    //! for the client.
    std::map<int64_t, int32_t> mTiles;
    //! The dirt stage (1 - 3) of a room as last sent, by room name.
    std::map<std::string, int32_t> mRooms;
    //! True until the first message was prepared, so a keeper who joins or loads gets everything in sight at once.
    bool mFirst;
    //! Turns since the last check for changes
    uint32_t mSyncWait;
    //! Turns since the last full resend
    uint32_t mResyncWait;
};

//! \brief Server side. Follows which floor tiles are dirty and in which stage (1 - 3, the thresholds of the room stages
//! applied to the value of the tile) and builds the cosmetic events (tileDirt) that tell the clients. The tiles tell it
//! when their dirt changes (Tile::addDirt, cleanDirt and setDirt), nothing is scanned for it. Cosmetic only.
class TileDirtSync
{
public:
    TileDirtSync();

    //! \brief Called by a tile when its dirt changed; the tile is looked at in the next refresh.
    void addChangedTile(Tile* tile);

    //! \brief Brings the stages of the changed tiles and of the rooms up to date. Does nothing more than once per turn.
    void refresh(GameMap* gameMap);

    //! \brief Prepares the event that tells one client what changed in sight of the seat since the last message, or the
    //! whole state in sight when a full resend is due, the client has just joined or loaded, or the keeper sees tiles
    //! it did not see before. Call once per turn per client after refresh().
    //! \param seat The seat of the keeper (only the tiles it has vision on are told).
    //! \param state The record of what this client was told, updated.
    //! \param event Filled when true is returned.
    //! \return True if there is something to send.
    bool buildEvent(GameMap* gameMap, Seat* seat, TileDirtClientState& state, CosmeticEvent& event);

    //! \brief The dirt stage of a tile value: 0 for a tile without visible dirt (value below DirtVisibleFrom),
    //! else 1 below DirtStage2At, 2 below DirtStage3At and 3 above (global.cfg [Dirt]).
    static int32_t stageForValue(double dirt);

    //! \brief The word shown for a dirt stage of a room: "clean" (1), "dirty" (2) or "filthy" (3).
    static std::string stageText(uint32_t stage);

    //! \brief Tells whether the dirt stage of a room of this type is shown to the keeper (not for rooms that make no
    //! room dirt and have no effect of it: crypt, treasury, portals, dungeon heart and bridges).
    static bool isStageShown(RoomType type);

    //! \brief The key of a tile in the maps of this class and in the client: x * 65536 + y.
    static int64_t makeKey(int32_t x, int32_t y);

private:
    //! The stage (1 - 3) of every dirty tile, by key. A clean tile is not in the map.
    std::map<int64_t, int32_t> mStages;
    //! The stage (1 - 3) of every room whose stage is shown, by room name.
    std::map<std::string, int32_t> mRoomStages;
    //! Tiles whose dirt changed since the last refresh
    std::vector<Tile*> mChanged;
    //! Turn of the last refresh, -1 if none
    int64_t mRefreshedTurn;
};

#endif // TILEDIRTSYNC_H
