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

#ifndef TREASURYGOLDBATCH_H
#define TREASURYGOLDBATCH_H

#include <map>
#include <set>
#include <string>
#include <tuple>

namespace Ogre
{
class Entity;
class SceneManager;
class SceneNode;
class StaticGeometry;
}

//! \brief Draws the settled gold piles of a treasury as a few static batches instead of one scene object per
//! tile. The piles stay ordinary entities (so the settle animation, the creature heights and the objects
//! buried in the gold keep working); a pile that is not settling is hidden and drawn by the batch of its
//! room and patch of tiles (TreasuryCreatureRules::batchChunkSize) instead. A change marks only its patch
//! dirty; the patch is rebuilt at most every TreasuryCreatureRules::batchRebuildInterval seconds.
//! Everything here only touches client scene objects.
class TreasuryGoldBatch
{
public:
    //! Takes a pile into the batch of its room and patch of tiles. A settling pile stays a visible entity of
    //! its own until pileSettled() is called.
    void addPile(Ogre::SceneManager* sceneManager, const std::string& entityName, const void* roomKey,
        int tileX, int tileY, Ogre::Entity* entity, Ogre::SceneNode* node, bool settling);

    //! The settle animation of the pile is over: the pile joins the batch with its next rebuild
    void pileSettled(const std::string& entityName);

    //! The pile is gone (its entity may already be destroyed): its patch is rebuilt
    void removePile(const std::string& entityName);

    //! Rebuilds the dirty patches whose interval is over
    void update(float timeSinceLastFrame);

    //! Destroys all batches. The entities are not touched (they may be gone already).
    void clear();

    //! Number of patches that currently have a batch (one pass over the piles per patch and material)
    size_t getBatchCount() const;

private:
    typedef std::tuple<const void*, int, int> ChunkKey;

    struct Member
    {
        ChunkKey mKey;
        Ogre::Entity* mEntity;
        Ogre::SceneNode* mNode;
        bool mSettling;
        bool mBatched;
    };

    struct Chunk
    {
        Ogre::StaticGeometry* mGeometry = nullptr;
        std::set<std::string> mMembers;
        bool mDirty = false;
        float mSinceRebuild = 0.0f;
    };

    void rebuild(ChunkKey key, Chunk& chunk);

    Ogre::SceneManager* mSceneManager = nullptr;
    int mGeometryNumber = 0;
    std::map<std::string, Member> mMembers;
    std::map<ChunkKey, Chunk> mChunks;
};

#endif // TREASURYGOLDBATCH_H
