// Terrain submission keeps the original entities for light selection and picking.
#ifndef TERRAIN_DRAW_BATCH_H
#define TERRAIN_DRAW_BATCH_H

#include <OgreSceneManager.h>
#include <OgreMovableObject.h>
#include <OgreStaticGeometry.h>
#include <OgreMatrix4.h>
#include <map>
#include <memory>
#include <string>
#include <vector>

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
    //! Builds dirty cells before Ogre updates their new scene nodes.
    void preUpdateSceneGraph(Ogre::SceneManager* source, Ogre::Camera* camera) override;
    //! Resets the lighting decision separately for every viewport and shadow pass.
    void preFindVisibleObjects(Ogre::SceneManager* source,
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
        bool mDirty;
        bool mDecided;
        bool mEnabled;
        Ogre::uint32 mVisibilityMask;
    };
    //! Destroys a cell's geometry immediately, retaining the original entity draws.
    void invalidate(Cell& cell);
    Ogre::SceneManager* mScene;
    std::map<std::string, std::unique_ptr<Cell> > mCells;
    std::map<std::string, Cell*> mMembers;
    size_t mNumber;
};

#endif
