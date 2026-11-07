#include "render/TerrainDrawBatch.h"
#include <OgreEntity.h>
#include <OgreSubEntity.h>
#include <OgreMesh.h>
#include <OgreMaterial.h>
#include <OgreTechnique.h>
#include <OgrePass.h>
#include <OgreSceneNode.h>
#include <OgreViewport.h>
#include <OgreCamera.h>
#include <algorithm>
#include <cmath>
#include <sstream>

//! Creates a cell with no generated scene object.
TerrainDrawBatch::Cell::Cell() : mGeometry(nullptr), mDirty(true), mDecided(false),
    mEnabled(false), mVisibilityMask(0)
{
}

//! Defers scene registration until there is eligible terrain.
TerrainDrawBatch::TerrainDrawBatch() : mScene(nullptr), mNumber(0)
{
}

//! Clears callbacks before the containing renderer is destroyed.
TerrainDrawBatch::~TerrainDrawBatch()
{
    clear();
}

//! Tests current visibility, transforms and ordered light identities, including shadow-light order.
bool TerrainDrawBatch::Cell::canBatch()
{
    if(mDecided)
        return mEnabled;
    mDecided = true;
    mEnabled = false;
    if(mDirty || mGeometry == nullptr || mGeometry->getRegions().size() != 1 || mEntities.size() < 2)
        return false;
    for(size_t i = 0; i < mEntities.size(); ++i)
    {
        Ogre::Entity* entity = mEntities[i];
        if(!entity->isAttached() || !entity->getVisible() ||
            !entity->getParentSceneNode()->isInSceneGraph() || !entity->getSubEntity(0)->isVisible() ||
            entity->getSubEntity(0)->getMaterial() != mMaterial ||
            (entity->getVisibilityFlags() & mVisibilityMask) == 0 ||
            entity->getParentSceneNode()->_getFullTransform() != mTransforms[i])
            return false;
        const Ogre::LightList& lights = entity->queryLights();
        if(i == 0)
            mLights = lights;
        else if(lights != mLights)
            return false;
    }
    mEnabled = true;
    return true;
}

//! Leaves original entities queryable and visible; only their render-queue submission is suppressed.
bool TerrainDrawBatch::Cell::objectRendering(const Ogre::MovableObject* object, const Ogre::Camera* camera)
{
    (void)camera;
    (void)object;
    return !canBatch();
}

//! Original entities use Ogre's finder, whereas the region reuses the common ordered list.
const Ogre::LightList* TerrainDrawBatch::Cell::objectQueryLights(const Ogre::MovableObject* object)
{
    if(object->getMovableType() != "StaticGeometry")
        return nullptr;
    return &mLights;
}

//! Rejects shader variants, overlays, animation, LOD, scaling and pre-existing listeners.
void TerrainDrawBatch::add(Ogre::SceneManager* scene, Ogre::Entity* entity)
{
    if(mMembers.count(entity->getName()) != 0 || entity->getListener() != nullptr ||
        !entity->isAttached() || entity->getCastShadows() || entity->getNumSubEntities() != 1 ||
        entity->getMesh()->hasSkeleton() || entity->getMesh()->hasVertexAnimation() ||
        entity->getMesh()->getNumLodLevels() != 1 || entity->getRenderingDistance() != 0 ||
        entity->getRenderingMinPixelSize() != 0 ||
        entity->getParentSceneNode()->_getDerivedScale() != Ogre::Vector3::UNIT_SCALE)
        return;
    Ogre::MaterialPtr material = entity->getSubEntity(0)->getMaterial();
    if(!material || (material->getName() != "Dirt" && material->getName().find("Dirt@@") != 0) ||
        material->getNumTechniques() != 1 || material->getTechnique(0)->getNumPasses() != 1)
        return;
    Ogre::Pass* pass = material->getTechnique(0)->getPass(0);
    if(pass->getVertexProgramName() != "myDirtTileVertexShader" ||
        pass->getFragmentProgramName() != "myDirtTileFragmentShader" ||
        pass->isTransparent() || !pass->getDepthWriteEnabled())
        return;
    if(mScene == nullptr)
    {
        mScene = scene;
        mScene->addListener(this);
    }
    const Ogre::Vector3& position = entity->getParentSceneNode()->_getDerivedPosition();
    std::ostringstream key;
    key << std::floor(position.x / 4.0f) << ':' << std::floor(position.y / 4.0f)
        << ':' << material->getName() << ':' << static_cast<unsigned int>(entity->getRenderQueueGroup());
    std::unique_ptr<Cell>& cell = mCells[key.str()];
    if(!cell)
    {
        cell.reset(new Cell());
        cell->mMaterial = material;
    }
    invalidate(*cell);
    cell->mEntities.push_back(entity);
    entity->setListener(cell.get());
    mMembers[entity->getName()] = cell.get();
}

//! Removes generated geometry before an original can be changed or destroyed.
void TerrainDrawBatch::invalidate(Cell& cell)
{
    if(cell.mGeometry != nullptr)
        mScene->destroyStaticGeometry(cell.mGeometry);
    cell.mGeometry = nullptr;
    cell.mDirty = true;
    cell.mDecided = false;
    cell.mEnabled = false;
}

//! Detaches the callback before the caller destroys or recolours the original.
void TerrainDrawBatch::remove(const std::string& name)
{
    std::map<std::string, Cell*>::iterator member = mMembers.find(name);
    if(member == mMembers.end())
        return;
    Cell& cell = *member->second;
    invalidate(cell);
    for(std::vector<Ogre::Entity*>::iterator it = cell.mEntities.begin(); it != cell.mEntities.end(); ++it)
    {
        if((*it)->getName() != name)
            continue;
        (*it)->setListener(nullptr);
        cell.mEntities.erase(it);
        break;
    }
    mMembers.erase(member);
}

//! Builds immutable world-space earth geometry while retaining the original UVs and material.
void TerrainDrawBatch::preUpdateSceneGraph(Ogre::SceneManager* source, Ogre::Camera* camera)
{
    (void)source;
    (void)camera;
    for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        Cell& cell = *it->second;
        if(!cell.mDirty)
            continue;
        cell.mDirty = false;
        if(cell.mEntities.size() < 2)
            continue;
        std::ostringstream name;
        name << "TerrainDrawBatch_" << ++mNumber;
        cell.mGeometry = mScene->createStaticGeometry(name.str());
        cell.mGeometry->setOrigin(Ogre::Vector3(-500.0f, -500.0f, -500.0f));
        cell.mGeometry->setRegionDimensions(Ogre::Vector3(1000.0f, 1000.0f, 1000.0f));
        cell.mGeometry->setCastShadows(false);
        cell.mGeometry->setRenderQueueGroup(cell.mEntities.front()->getRenderQueueGroup());
        cell.mTransforms.clear();
        for(Ogre::Entity* entity : cell.mEntities)
        {
            Ogre::SceneNode* node = entity->getParentSceneNode();
            cell.mGeometry->addEntity(entity, node->_getDerivedPosition(), node->_getDerivedOrientation(),
                node->_getDerivedScale());
            cell.mTransforms.push_back(node->_getFullTransform());
        }
        cell.mGeometry->build();
        const Ogre::StaticGeometry::RegionMap& regions = cell.mGeometry->getRegions();
        for(Ogre::StaticGeometry::RegionMap::const_iterator region = regions.begin(); region != regions.end(); ++region)
        {
            region->second->setQueryFlags(0);
            region->second->setListener(&cell);
        }
    }
}

//! Makes each view recheck culling masks and current lights; shadow passes always keep originals.
void TerrainDrawBatch::preFindVisibleObjects(Ogre::SceneManager* source,
    Ogre::SceneManager::IlluminationRenderStage stage, Ogre::Viewport* viewport)
{
    (void)source;
    for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        Cell& cell = *it->second;
        cell.mDecided = stage != Ogre::SceneManager::IRS_NONE;
        cell.mEnabled = false;
        cell.mVisibilityMask = viewport->getVisibilityMask() & mScene->getVisibilityMask();
        // Region overrides _notifyCurrentCamera without calling MovableObject's rendering
        // listener, so choose its visibility explicitly before Ogre visits the scene.
        const bool enabled = cell.canBatch();
        if(cell.mGeometry != nullptr)
            cell.mGeometry->setVisible(enabled);
    }
}

//! Clears the scene listener, region geometry and original callbacks in that order.
void TerrainDrawBatch::clear()
{
    if(mScene == nullptr)
        return;
    mScene->removeListener(this);
    for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        Cell& cell = *it->second;
        invalidate(cell);
        for(Ogre::Entity* entity : cell.mEntities)
            entity->setListener(nullptr);
    }
    mMembers.clear();
    mCells.clear();
    mScene = nullptr;
}
