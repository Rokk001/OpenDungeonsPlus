// Terrain submission keeps the original entities for light selection and picking.
#ifndef TERRAIN_DRAW_BATCH_H
#define TERRAIN_DRAW_BATCH_H

#include <OgreSceneManager.h>
#include <OgreMovableObject.h>
#include <OgreStaticGeometry.h>
#include <OgreMatrix4.h>
#include <OgreAxisAlignedBox.h>
#include <map>
#include <memory>
#include <string>
#include <vector>
#include <chrono>

//! Batches opaque earth within small cells, falling back when per-object inputs differ.
class TerrainDrawBatch : public Ogre::SceneManager::Listener
{
public:
    //! Starts without a scene; the first eligible entity attaches the listener.
    TerrainDrawBatch();
    //! Removes callbacks and geometry while the scene and original entities still exist.
    ~TerrainDrawBatch();
    //! Registers a finished earth tile or border entity without changing its material.
    void add(Ogre::SceneManager* scene, Ogre::Entity* entity);
    //! Invalidates the old batch before a tile's entity, material or transform changes.
    void remove(const std::string& name);
    //! Releases batches and detaches entity listeners before scene teardown.
    void clear();
    //! Builds at most one eligible dirty cell per Ogre frame across all views.
    void preUpdateSceneGraph(Ogre::SceneManager* source, Ogre::Camera* camera) override;
    //! Resets each view's lighting decision and limits failed construction probes.
    void preFindVisibleObjects(Ogre::SceneManager* source,
        Ogre::SceneManager::IlluminationRenderStage stage, Ogre::Viewport* viewport) override;
    //! Reports observed source suppression after visibility traversal, separately from estimated draw savings.
    void postFindVisibleObjects(Ogre::SceneManager* source,
        Ogre::SceneManager::IlluminationRenderStage stage, Ogre::Viewport* viewport) override;

private:
    //! Owns one cell's geometry and supplies exactly the originals' ordered light list.
    struct Cell : public Ogre::MovableObject::Listener
    {
        //! Creates a dirty cell which renders its originals until a batch is built.
        Cell();
        //! Chooses the batch only when all original per-object inputs still agree.
        bool canBatch();
        //! Queues either the region or its originals, never both.
        bool objectRendering(const Ogre::MovableObject* object, const Ogre::Camera* camera) override;
        //! Overrides region-centre light selection with the identical per-tile list.
        const Ogre::LightList* objectQueryLights(const Ogre::MovableObject* object) override;
        std::vector<Ogre::Entity*> mEntities;
        std::vector<Ogre::Affine3> mTransforms;
        Ogre::MaterialPtr mMaterial;
        Ogre::StaticGeometry* mGeometry;
        Ogre::LightList mLights;
        Ogre::AxisAlignedBox mBounds;
        size_t mSuppressed;
        bool mDirty;
        bool mDecided;
        bool mEnabled;
        //! Previous post-transform light compatibility permits construction, never source suppression.
        bool mBuildAllowed;
        //! A failed construction hint delays only new geometry, never current-view validation.
        std::chrono::steady_clock::time_point mNextBuildProbe;
        Ogre::uint32 mVisibilityMask;
    };
    //! Destroys a cell's geometry immediately, retaining the original entity draws.
    void invalidate(Cell& cell);
    //! Splits a rejected dirty cell by exact ordered lights without changing draw eligibility.
    void partitionByLights(Cell& cell);
    Ogre::SceneManager* mScene;
    std::map<std::string, std::unique_ptr<Cell> > mCells;
    std::map<std::string, Cell*> mMembers;
    size_t mNumber;
    //! Retains the build budget across every view and scene reset in one Ogre frame.
    unsigned long mLastBuildFrame;
    bool mHasBuildFrame;
    std::chrono::steady_clock::time_point mNextReport;
};

#endif
