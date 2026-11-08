#include "render/TerrainDrawBatch.h"
#include "utils/LogManager.h"
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
TerrainDrawBatch::Cell::Cell() : mGeometry(nullptr), mSuppressed(0), mDirty(true), mDecided(false),
    mEnabled(false), mBuildAllowed(false), mVisibilityMask(0)
{
}

//! Defers scene registration until there is eligible terrain.
TerrainDrawBatch::TerrainDrawBatch() : mScene(nullptr), mNumber(0),
    mNextReport(std::chrono::steady_clock::now())
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

//! Counts actual suppressed original submissions while keeping their visibility and picking state.
bool TerrainDrawBatch::Cell::objectRendering(const Ogre::MovableObject* object, const Ogre::Camera* camera)
{
    (void)camera;
    (void)object;
    if(!canBatch())
        return true;
    ++mSuppressed;
    return false;
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
    cell->mBounds.merge(entity->getWorldBoundingBox(true));
    entity->setListener(cell.get());
    mMembers[entity->getName()] = cell.get();
}

//! Removes generated geometry and resets construction retry state before a source changes.
void TerrainDrawBatch::invalidate(Cell& cell)
{
    if(cell.mGeometry != nullptr)
        mScene->destroyStaticGeometry(cell.mGeometry);
    cell.mGeometry = nullptr;
    cell.mDirty = true;
    cell.mBuildAllowed = false;
    cell.mNextBuildProbe = std::chrono::steady_clock::time_point();
    cell.mDecided = false;
    cell.mEnabled = false;
}

//! Detaches the callback before source changes and drops exhausted cells from per-view traversal.
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
    if(cell.mEntities.empty())
    {
        for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
        {
            if(it->second.get() != &cell)
                continue;
            mCells.erase(it);
            break;
        }
    }
}

//! Builds visible dirty cells after a light-compatible view; current-view validation keeps rejected originals.
void TerrainDrawBatch::preUpdateSceneGraph(Ogre::SceneManager* source, Ogre::Camera* camera)
{
    (void)source;
    for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        Cell& cell = *it->second;
        if(!cell.mDirty)
            continue;
        if(!camera->isVisible(cell.mBounds))
            continue;
        if(cell.mEntities.size() < 2)
            continue;
        // preFindVisibleObjects records this hint after scene transforms have been updated.
        // A previous compatible view only permits construction; canBatch validates the current view.
        if(!cell.mBuildAllowed)
            continue;
        cell.mDirty = false;
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

//! Culls cells, limits failed construction probes and validates every built batch in each view.
void TerrainDrawBatch::preFindVisibleObjects(Ogre::SceneManager* source,
    Ogre::SceneManager::IlluminationRenderStage stage, Ogre::Viewport* viewport)
{
    (void)source;
    const std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
    for(std::map<std::string, std::unique_ptr<Cell> >::iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        Cell& cell = *it->second;
        cell.mSuppressed = 0;
        cell.mDecided = stage != Ogre::SceneManager::IRS_NONE;
        cell.mEnabled = false;
        cell.mVisibilityMask = viewport->getVisibilityMask() & mScene->getVisibilityMask();
        // Region overrides _notifyCurrentCamera without calling MovableObject's rendering
        // listener, so choose its visibility explicitly before Ogre visits the scene.
        // Rejecting a batch here never culls its originals: their normal Ogre traversal remains active.
        if(!cell.mDecided && !viewport->getCamera()->isVisible(cell.mBounds))
            cell.mDecided = true;
        // Do not query lights during preUpdateSceneGraph: Ogre has not updated transforms yet.
        // Dirty cells keep ordinary draws while learning whether construction could help next frame.
        if(!cell.mDecided && cell.mDirty && cell.mEntities.size() >= 2)
        {
            // Incompatible cells keep their ordinary draws during the retry interval.
            // The hint only enables construction; canBatch still validates every current view.
            if(now < cell.mNextBuildProbe)
                continue;
            cell.mBuildAllowed = true;
            Ogre::LightList firstLights;
            for(size_t i = 0; i < cell.mEntities.size(); ++i)
            {
                Ogre::Entity* entity = cell.mEntities[i];
                if(!entity->isAttached())
                {
                    cell.mBuildAllowed = false;
                    break;
                }
                const Ogre::LightList& lights = entity->queryLights();
                if(i == 0)
                    firstLights = lights;
                else if(lights != firstLights)
                {
                    cell.mBuildAllowed = false;
                    break;
                }
            }
            if(!cell.mBuildAllowed)
                cell.mNextBuildProbe = now + std::chrono::milliseconds(250);
        }
        const bool enabled = cell.canBatch();
        if(cell.mGeometry != nullptr)
            cell.mGeometry->setVisible(enabled);
    }
}

//! Logs current-view coverage once per minute without treating enabled cells as measured GPU draws.
void TerrainDrawBatch::postFindVisibleObjects(Ogre::SceneManager* source,
    Ogre::SceneManager::IlluminationRenderStage stage, Ogre::Viewport* viewport)
{
    (void)source;
    if(stage != Ogre::SceneManager::IRS_NONE || !viewport->getOverlaysEnabled())
        return;
    const std::chrono::steady_clock::time_point now = std::chrono::steady_clock::now();
    if(now < mNextReport)
        return;
    mNextReport = now + std::chrono::seconds(60);
    size_t enabled = 0;
    size_t suppressed = 0;
    size_t dirty = 0;
    size_t culled = 0;
    size_t fallback = 0;
    for(std::map<std::string, std::unique_ptr<Cell> >::const_iterator it = mCells.begin(); it != mCells.end(); ++it)
    {
        const Cell& cell = *it->second;
        enabled += cell.mEnabled ? 1 : 0;
        suppressed += cell.mSuppressed;
        dirty += cell.mDirty ? 1 : 0;
        if(!viewport->getCamera()->isVisible(cell.mBounds))
            ++culled;
        else if(!cell.mEnabled)
            ++fallback;
    }
    std::ostringstream report;
    report << "Terrain batch view cells=" << mCells.size() << " enabled=" << enabled
        << " dirty=" << dirty << " culled=" << culled << " fallback=" << fallback
        << " candidateSources=" << mMembers.size() << " suppressedSourceCallbacks=" << suppressed;
    OD_LOG_INF(report.str());
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
