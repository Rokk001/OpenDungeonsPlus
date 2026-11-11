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
#include <OgreRoot.h>
#include <OgreGpuProgram.h>
#include <OgreGpuProgramParams.h>
#include <algorithm>
#include <cmath>
#include <functional>
#include <sstream>
#include <utility>

namespace
{
//! One tile shader family whose output is unchanged when StaticGeometry bakes the world transform into vertices.
struct WorldSpaceTileShader
{
    const char* mVertexSource;
    const char* mFragmentSource;
    //! The shadow projection the vertex shader expects: DirtTile.vert projects the world position with
    //! texture_viewproj_matrix; Room.vert and ClaimedTile.vert multiply texture_worldviewproj_matrix by
    //! inverse(worldMatrix), so the world matrix cancels out in both cases.
    Ogre::GpuProgramParameters::AutoConstantType mShadowMatrix;
};

//! The tile shaders that compute position, normals, deformation and lighting in world space only.
const WorldSpaceTileShader WORLD_SPACE_TILE_SHADERS[] = {
    {"DirtTile.vert", "DirtTile.frag", Ogre::GpuProgramParameters::ACT_TEXTURE_VIEWPROJ_MATRIX},
    {"Room.vert", "Room.frag", Ogre::GpuProgramParameters::ACT_TEXTURE_WORLDVIEWPROJ_MATRIX},
    {"ClaimedTile.vert", "ClaimedTile.frag", Ogre::GpuProgramParameters::ACT_TEXTURE_WORLDVIEWPROJ_MATRIX}
};

//! Accepts only automatic constants that do not depend on the object beyond its light list, plus the
//! family's own shadow projection, so a batch cannot change any value the shader reads.
bool hasWorldSpaceAutoConstants(const Ogre::GpuProgramParametersPtr& parameters,
    Ogre::GpuProgramParameters::AutoConstantType shadowMatrix)
{
    if(!parameters)
        return false;
    const Ogre::GpuProgramParameters::AutoConstantList& constants = parameters->getAutoConstants();
    for(const Ogre::GpuProgramParameters::AutoConstantEntry& constant : constants)
    {
        switch(constant.paramType)
        {
            case Ogre::GpuProgramParameters::ACT_WORLD_MATRIX:
            case Ogre::GpuProgramParameters::ACT_VIEW_MATRIX:
            case Ogre::GpuProgramParameters::ACT_PROJECTION_MATRIX:
            case Ogre::GpuProgramParameters::ACT_AMBIENT_LIGHT_COLOUR:
            case Ogre::GpuProgramParameters::ACT_LIGHT_DIFFUSE_COLOUR_ARRAY:
            case Ogre::GpuProgramParameters::ACT_LIGHT_SPECULAR_COLOUR_ARRAY:
            case Ogre::GpuProgramParameters::ACT_LIGHT_POSITION_ARRAY:
            case Ogre::GpuProgramParameters::ACT_LIGHT_ATTENUATION_ARRAY:
            case Ogre::GpuProgramParameters::ACT_LIGHT_COUNT:
            case Ogre::GpuProgramParameters::ACT_LIGHT_CASTS_SHADOWS:
            case Ogre::GpuProgramParameters::ACT_CAMERA_POSITION:
            case Ogre::GpuProgramParameters::ACT_SURFACE_DIFFUSE_COLOUR:
                break;
            default:
                if(constant.paramType != shadowMatrix)
                    return false;
                break;
        }
    }
    return true;
}

//! Returns whether a pass uses one complete world-space tile shader family with batch-safe parameters.
bool isWorldSpaceTilePass(const Ogre::Pass& pass)
{
    if(!pass.hasVertexProgram() || !pass.hasFragmentProgram() ||
        pass.getMaxSimultaneousLights() < TerrainDrawBatch::TILE_SHADER_LIGHTS)
        return false;
    const Ogre::String& vertexSource = pass.getVertexProgram()->getSourceFile();
    const Ogre::String& fragmentSource = pass.getFragmentProgram()->getSourceFile();
    for(const WorldSpaceTileShader& shader : WORLD_SPACE_TILE_SHADERS)
    {
        if(vertexSource != shader.mVertexSource || fragmentSource != shader.mFragmentSource)
            continue;
        return hasWorldSpaceAutoConstants(pass.getVertexProgramParameters(), shader.mShadowMatrix) &&
            hasWorldSpaceAutoConstants(pass.getFragmentProgramParameters(), shader.mShadowMatrix);
    }
    return false;
}
}

//! Creates a cell with no generated scene object.
TerrainDrawBatch::Cell::Cell() : mGeometry(nullptr), mSuppressed(0), mDirty(true), mDecided(false),
    mEnabled(false), mBuildAllowed(false), mVisibilityMask(0)
{
}

//! Defers scene registration until there is eligible terrain.
TerrainDrawBatch::TerrainDrawBatch() : mScene(nullptr), mNumber(0), mLastBuildFrame(0), mHasBuildFrame(false),
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

//! Original entities use Ogre's finder in canonical order, whereas the region reuses the common ordered list.
//! Ogre uploads all light parameters again whenever the ordered list differs from the previous draw's, so
//! neighbouring tiles lit by the same lights now share one upload and can share one batch.
const Ogre::LightList* TerrainDrawBatch::Cell::objectQueryLights(const Ogre::MovableObject* object)
{
    if(object->getMovableType() == "StaticGeometry")
        return &mLights;
    Ogre::SceneNode* node = object->getParentSceneNode();
    // Detached or bone-attached objects keep Ogre's own handling.
    if(node == nullptr || object->isParentTagPoint() || node->getCreator() == nullptr)
        return nullptr;
    // Same refresh rule as MovableObject::queryLights: recompute when Ogre's light dirty counter changes.
    const unsigned long counter = node->getCreator()->_getLightsDirtyCounter();
    CanonicalLights& entry = mCanonicalLights[object];
    if(!entry.mValid || entry.mLightsDirtyCounter != counter)
    {
        node->findLights(entry.mLights, object->getBoundingRadiusScaled(), object->getLightMask());
        canonicalizeLightOrder(entry.mLights);
        entry.mLightsDirtyCounter = counter;
        entry.mValid = true;
    }
    return &entry.mLights;
}

//! The tile shaders apply the single shadow texture to light 0 only and add up every other light the
//! same way, so only light 0 and the set of lights matter. Lists longer than the shader's light slots
//! keep Ogre's order, because reordering them would change which lights the shader receives.
void TerrainDrawBatch::canonicalizeLightOrder(Ogre::LightList& lights)
{
    if(lights.size() < 3 || lights.size() > TILE_SHADER_LIGHTS)
        return;
    std::sort(lights.begin() + 1, lights.end(), std::less<Ogre::Light*>());
}

//! Rejects other shaders, overlays, animation, LOD, scaling and pre-existing listeners. Earth, gold ground,
//! rock, claimed ground, bridges and room floors qualify through their world-space tile shaders.
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
    if(!material || material->getNumTechniques() != 1 || material->getTechnique(0)->getNumPasses() != 1)
        return;
    Ogre::Pass* pass = material->getTechnique(0)->getPass(0);
    if(!isWorldSpaceTilePass(*pass) || pass->isTransparent() || !pass->getDepthWriteEnabled())
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

//! Retains compatible subsets instead of abandoning a whole cell at its first different light list.
void TerrainDrawBatch::partitionByLights(Cell& cell)
{
    if(!cell.mDirty || cell.mGeometry != nullptr)
        return;
    std::vector<Ogre::LightList> lights;
    std::vector<std::vector<Ogre::Entity*> > groups;
    for(Ogre::Entity* entity : cell.mEntities)
    {
        if(!entity->isAttached())
            return;
        const Ogre::LightList& current = entity->queryLights();
        size_t group = 0;
        while(group < lights.size() && lights[group] != current)
            ++group;
        if(group == lights.size())
        {
            lights.push_back(current);
            groups.push_back(std::vector<Ogre::Entity*>());
        }
        groups[group].push_back(entity);
    }
    if(groups.size() < 2)
        return;
    size_t largest = 0;
    for(size_t group = 1; group < groups.size(); ++group)
    {
        if(groups[group].size() > groups[largest].size())
            largest = group;
    }
    // Unique light lists cannot save a submission, so keep the throttled original cell.
    if(groups[largest].size() < 2)
        return;
    for(size_t group = 0; group < groups.size(); ++group)
    {
        if(group == largest)
            continue;
        std::unique_ptr<Cell> subset(new Cell());
        subset->mMaterial = cell.mMaterial;
        subset->mEntities.swap(groups[group]);
        subset->mBuildAllowed = subset->mEntities.size() >= 2;
        for(Ogre::Entity* entity : subset->mEntities)
        {
            subset->mBounds.merge(entity->getWorldBoundingBox(true));
            entity->setListener(subset.get());
            mMembers[entity->getName()] = subset.get();
        }
        std::ostringstream key;
        key << "LightGroup_" << ++mNumber;
        mCells[key.str()] = std::move(subset);
    }
    cell.mEntities.swap(groups[largest]);
    // This is only a construction hint; every group still uses canBatch in each current view.
    cell.mBuildAllowed = true;
}

//! Removes generated geometry, resets construction retry state and forgets cached member lights before a
//! source changes, so a destroyed or re-added entity can never reuse an old light list.
void TerrainDrawBatch::invalidate(Cell& cell)
{
    if(cell.mGeometry != nullptr)
        mScene->destroyStaticGeometry(cell.mGeometry);
    cell.mCanonicalLights.clear();
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

//! Builds one eligible cell per Ogre frame; waiting cells retain their original draws.
void TerrainDrawBatch::preUpdateSceneGraph(Ogre::SceneManager* source, Ogre::Camera* camera)
{
    (void)source;
    const unsigned long frame = Ogre::Root::getSingleton().getNextFrameNumber();
    if(mHasBuildFrame && mLastBuildFrame == frame)
        return;
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
        mLastBuildFrame = frame;
        mHasBuildFrame = true;
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
        return;
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
            if(!cell.mBuildAllowed)
                partitionByLights(cell);
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
