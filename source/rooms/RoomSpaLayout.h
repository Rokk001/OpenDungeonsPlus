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

#ifndef ROOMSPALAYOUT_H
#define ROOMSPALAYOUT_H

#include <cstdint>
#include <set>
#include <utility>

//! \brief A set of tile positions (x, y) of a lava spa. The pure layout rules of the spa work on such sets so that
//! they do not need a map; the room maps its tiles to a set and back.
typedef std::set<std::pair<int32_t, int32_t> > SpaTileSet;

//! \brief A block of tiles in a pool: the smallest x and y and the size in tiles.
struct SpaBlock
{
    //! \brief Creates an empty block of 1 x 1 tiles at the origin.
    SpaBlock() :
        mX(0),
        mY(0),
        mWidth(1),
        mHeight(1)
    {}

    //! Smallest x of the block.
    int32_t mX;
    //! Smallest y of the block.
    int32_t mY;
    //! Number of tiles along x.
    int32_t mWidth;
    //! Number of tiles along y.
    int32_t mHeight;
};

//! \brief The layout rules of the lava spa: which tiles are pool, where a bather finds a place, where the pool
//! attendant's chair and the springboard stand and how large the room has to be. All of them are deterministic, so
//! the server and the checks get the same result.
namespace SpaLayout
{
    //! \brief The pool tiles of a spa: the covered tiles whose eight neighbours are covered tiles too. The other
    //! covered tiles are the rim.
    //! \param covered All the tiles the room covers.
    inline SpaTileSet poolTiles(const SpaTileSet& covered)
    {
        SpaTileSet pool;
        for(SpaTileSet::const_iterator it = covered.begin(); it != covered.end(); ++it)
        {
            bool allNeighbours = true;
            for(int32_t dx = -1; dx <= 1; ++dx)
            {
                for(int32_t dy = -1; dy <= 1; ++dy)
                {
                    if(covered.find(std::make_pair(it->first + dx, it->second + dy)) == covered.end())
                        allNeighbours = false;
                }
            }
            if(allNeighbours)
                pool.insert(*it);
        }
        return pool;
    }

    //! \brief True when the tiles contain a full block of side x side tiles.
    //! \param tiles The tiles to look in.
    //! \param side The side of the block in tiles.
    inline bool hasSquareBlock(const SpaTileSet& tiles, int32_t side)
    {
        for(SpaTileSet::const_iterator it = tiles.begin(); it != tiles.end(); ++it)
        {
            bool full = true;
            for(int32_t dx = 0; dx < side; ++dx)
            {
                for(int32_t dy = 0; dy < side; ++dy)
                {
                    if(tiles.find(std::make_pair(it->first + dx, it->second + dy)) == tiles.end())
                        full = false;
                }
            }
            if(full)
                return true;
        }
        return false;
    }

    //! \brief True when every tile of the block is a pool tile that is not taken.
    //! \param pool The pool tiles.
    //! \param taken The tiles of the blocks that bathers have or have reserved.
    //! \param block The block to test.
    inline bool isBlockFree(const SpaTileSet& pool, const SpaTileSet& taken, const SpaBlock& block)
    {
        for(int32_t dx = 0; dx < block.mWidth; ++dx)
        {
            for(int32_t dy = 0; dy < block.mHeight; ++dy)
            {
                const std::pair<int32_t, int32_t> tile(block.mX + dx, block.mY + dy);
                if((pool.find(tile) == pool.end()) || (taken.find(tile) != taken.end()))
                    return false;
            }
        }
        return true;
    }

    //! \brief Finds the bath place of a creature: the first free block of its bed size among the pool tiles, in the
    //! order of smaller y, then smaller x. A bed of 1 x 2 tiles tries both orientations, the unrotated one
    //! (width dim1, height dim2) first.
    //! \param pool The pool tiles.
    //! \param taken The tiles of the blocks that bathers have or have reserved.
    //! \param dim1 First bed dimension of the creature (BedDim).
    //! \param dim2 Second bed dimension of the creature (BedDim).
    //! \param block Set to the block that was found.
    //! \return False when no free block exists.
    inline bool findFreeBlock(const SpaTileSet& pool, const SpaTileSet& taken, int32_t dim1, int32_t dim2, SpaBlock& block)
    {
        // The tiles are walked in the order of smaller y, then smaller x
        std::set<std::pair<int32_t, int32_t> > anchors;
        for(SpaTileSet::const_iterator it = pool.begin(); it != pool.end(); ++it)
            anchors.insert(std::make_pair(it->second, it->first));

        for(SpaTileSet::const_iterator it = anchors.begin(); it != anchors.end(); ++it)
        {
            SpaBlock candidate;
            candidate.mX = it->second;
            candidate.mY = it->first;
            candidate.mWidth = dim1;
            candidate.mHeight = dim2;
            if(isBlockFree(pool, taken, candidate))
            {
                block = candidate;
                return true;
            }

            if(dim1 == dim2)
                continue;

            candidate.mWidth = dim2;
            candidate.mHeight = dim1;
            if(isBlockFree(pool, taken, candidate))
            {
                block = candidate;
                return true;
            }
        }
        return false;
    }

    //! \brief The tile of the pool attendant's chair: directly above (y - 1) the pool tile with the smallest y, then
    //! the smallest x.
    //! \param pool The pool tiles.
    //! \param tile Set to the position of the chair tile.
    //! \return False when the pool has no tile.
    inline bool chairTile(const SpaTileSet& pool, std::pair<int32_t, int32_t>& tile)
    {
        if(pool.empty())
            return false;

        std::pair<int32_t, int32_t> best = *pool.begin();
        for(SpaTileSet::const_iterator it = pool.begin(); it != pool.end(); ++it)
        {
            if((it->second < best.second) || ((it->second == best.second) && (it->first < best.first)))
                best = *it;
        }
        tile = std::make_pair(best.first, best.second - 1);
        return true;
    }

    //! \brief The tile of the springboard: directly below (y + 1) the pool tile with the largest y, then the largest x.
    //! \param pool The pool tiles.
    //! \param tile Set to the position of the springboard tile.
    //! \return False when the pool has no tile.
    inline bool springboardTile(const SpaTileSet& pool, std::pair<int32_t, int32_t>& tile)
    {
        if(pool.empty())
            return false;

        std::pair<int32_t, int32_t> best = *pool.begin();
        for(SpaTileSet::const_iterator it = pool.begin(); it != pool.end(); ++it)
        {
            if((it->second > best.second) || ((it->second == best.second) && (it->first > best.first)))
                best = *it;
        }
        tile = std::make_pair(best.first, best.second + 1);
        return true;
    }
}

#endif // ROOMSPALAYOUT_H
