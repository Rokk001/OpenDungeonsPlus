"""Check earth batching lifecycle and world-space shader equivalence without compiling or starting a game.

The numerical checks use real exported earth vertices, the shared deformation and the active Dirt vertex
shader. They exercise rotated and translated tiles, including negative cell coordinates. Source contracts
cover Ogre's callback trap: StaticGeometry regions do not call objectRendering, and isVisible includes the
previous view's callback suppression. Release rendering, lighting transitions and submission timing still
require the real engine; this check does not claim to measure those.
"""
from pathlib import Path
import math
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]


# Extract a complete C++ body, including nested conditions, for lifecycle ordering checks.
def body(source, signature):
    start = source.index('{', source.index(signature))
    depth = 1
    end = start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


# Guard every fallback whose omission could change lighting, visibility or editor behaviour.
def verify(source, render):
    gate = body(source, 'bool TerrainDrawBatch::Cell::canBatch(')
    for required in ['mGeometry->getRegions().size() != 1', 'mEntities.size() < 2',
                     'entity->getVisible()', 'isInSceneGraph()', 'getSubEntity(0)->isVisible()',
                     'getSubEntity(0)->getMaterial() != mMaterial', 'getVisibilityFlags() & mVisibilityMask',
                     '_getFullTransform() != mTransforms[i]', 'entity->queryLights()',
                     'mLights = lights', 'lights != mLights']:
        assert required in gate, required
    assert 'entity->isVisible()' not in gate, 'previous-view suppression must not disable the next batch'
    assert gate.index('lights != mLights') < gate.index('mEnabled = true')
    registration = body(source, 'void TerrainDrawBatch::add(')
    for required in ['getListener() != nullptr', 'getCastShadows()', 'getNumSubEntities() != 1',
                     'hasSkeleton()', 'hasVertexAnimation()', 'getNumLodLevels() != 1',
                     'getRenderingDistance() != 0', 'getRenderingMinPixelSize() != 0',
                     'Ogre::Vector3::UNIT_SCALE', 'material->getNumTechniques() != 1',
                     'getNumPasses() != 1', '"myDirtTileVertexShader"',
                     '"myDirtTileFragmentShader"', 'pass->isTransparent()',
                     '!pass->getDepthWriteEnabled()', 'std::floor(position.x / 4.0f)',
                     'std::floor(position.y / 4.0f)']:
        assert required in registration, required
    build = body(source, 'void TerrainDrawBatch::preUpdateSceneGraph(')
    for required in ['cell.mGeometry->addEntity(entity, node->_getDerivedPosition()',
                     'node->_getDerivedOrientation()', 'node->_getDerivedScale()',
                     'cell.mGeometry->setCastShadows(false)', 'region->second->setQueryFlags(0)',
                     'region->second->setListener(&cell)']:
        assert required in build, required
    view = body(source, 'void TerrainDrawBatch::preFindVisibleObjects(')
    assert 'stage != Ogre::SceneManager::IRS_NONE' in view
    assert 'viewport->getVisibilityMask() & mScene->getVisibilityMask()' in view
    assert 'setVisible(enabled)' in view
    assert view.index('cell.mDecided =') < view.index('cell.canBatch()') < view.index('setVisible(enabled)')
    lights = body(source, 'const Ogre::LightList* TerrainDrawBatch::Cell::objectQueryLights(')
    assert 'return nullptr' in lights and 'return &mLights' in lights
    submission = body(source, 'bool TerrainDrawBatch::Cell::objectRendering(')
    assert submission.index('if(!canBatch())') < submission.index('return true;')
    assert submission.index('return true;') < submission.index('++mSuppressed;') < submission.index('return false;')
    removal = body(source, 'void TerrainDrawBatch::remove(')
    assert removal.index('invalidate(cell)') < removal.index('setListener(nullptr)') < removal.index('mEntities.erase')
    refresh = body(render, 'void RenderManager::rrRefreshTile(')
    assert refresh.index('mTerrainDrawBatch.remove(tileMeshName)') < refresh.index('destroyEntity(tileMeshEnt)')
    assert refresh.index('colourizeEntity(tileMeshEnt') < refresh.index('mTerrainDrawBatch.add')
    assert 'if(nt == NodeType::MTILES_NODE && tileMeshEnt != nullptr)' in refresh
    destruction = body(render, 'void RenderManager::rrDestroyTile(')
    assert destruction.index('mTerrainDrawBatch.remove(tileMeshName)') < destruction.index('destroyEntity(ent)')
    shutdown = body(render, 'void RenderManager::stopGameRenderer(')
    assert shutdown.index('mTerrainDrawBatch.clear()') < shutdown.index('destroyWorldBorder()')
    # Original materials, entity visibility, query flags and light masks must remain untouched by the batch.
    assert 'entity->setVisible' not in source and 'entity->setMaterial' not in source
    assert 'entity->setQueryFlags' not in source and 'entity->setLightMask' not in source
    assert 'render/TerrainDrawBatch.cpp' in (ROOT / 'CMakeLists.txt').read_text()


# Multiply a vertex by a world matrix, independently of the batch's CPU position baking.
def transform(matrix, point):
    return tuple(sum(matrix[row][col] * (*point, 1.0)[col] for col in range(4)) for row in range(3))


# Compare the active shader's world-space deformation and planar UVs before/after static batching.
def check_geometry():
    earth = runpy.run_path(str(ROOT / 'source/tests/check_fog_earth_geometry.py'))
    border = runpy.run_path(str(ROOT / 'source/tests/check_unknown_wall_borders.py'))
    shader = (ROOT / 'shaders/DirtTile.vert').read_text()
    shared = (ROOT / 'shaders/PerlinNoise.glsl').read_text()
    assert 'vec3 P = (worldMatrix * position).xyz;' in shader
    assert 'worldUvWeight(normalize(mat3(worldMatrix) * normal))' in shader
    assert 'vec2 worldUV = worldTileUV(P);' in shader
    assert shader.index('worldTileUV(P)') < shader.index('P = deform(P)')
    assert 'VertexPos = lightMatrix * vec4(P, 1.0);' in shader
    # Dirt's shadow transform is world-to-shadow, so a new batch world matrix cannot change it.
    material = (ROOT / 'materials/scripts/Dirt.material').read_text()
    assert 'param_named_auto lightMatrix texture_viewproj_matrix 0' in material
    tileset = (ROOT / 'config/tilesets.cfg').read_text().split('[dirtFull]', 1)[1].split('[/dirtFull]', 1)[0]
    entries = re.findall(r'(Dirt_[^\s]+\.mesh)\s+Dirt\s+[0-9.-]+\s+[0-9.-]+\s+[0-9.-]+', tileset)
    assert entries
    checked = 0
    for name in sorted(set(entries)):
        for point in earth['positions'](ROOT / 'models' / name):
            for x, y, degrees in [(-7, 3, 0), (0, 0, 90), (12, -4, 180), (3, 5, 270)]:
                angle = math.radians(degrees)
                c, s = math.cos(angle), math.sin(angle)
                world = ((c, -s, 0, x), (s, c, 0, y), (0, 0, 1, 0))
                original = transform(world, point)
                # StaticGeometry bakes the same rotation/translation; its region centre is zero.
                baked = (c * point[0] - s * point[1] + x,
                         s * point[0] + c * point[1] + y, point[2])
                assert max(abs(a - b) for a, b in zip(original, baked)) < 1e-12
                assert border['deform'](original, shader, shared) == border['deform'](baked, shader, shared)
                # Identical world position also preserves the active worldTileUV input.
                checked += 1
    # Fixed once from the committed earth meshes: 10,394 vertices, four transforms each.
    assert checked == 41576
    return checked


# Reject independent lighting, callback, lifecycle, culling and overlay regressions.
def main():
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text()
    render = (ROOT / 'source/render/RenderManager.cpp').read_text()
    verify(source, render)
    mutations = [
        ('lights != mLights', 'false'),
        ('entity->getVisible()', 'entity->isVisible()'),
        ('!entity->getParentSceneNode()->isInSceneGraph()', 'false'),
        ('getVisibilityFlags() & mVisibilityMask', 'getVisibilityFlags() & 0xFFFFFFFF'),
        ('material->getTechnique(0)->getNumPasses() != 1', 'false'),
        ('cell.mGeometry->setVisible(enabled)', 'cell.mGeometry->setVisible(true)'),
        ('region->second->setQueryFlags(0)', 'region->second->setQueryFlags(1)'),
    ]
    for old, new in mutations:
        assert old in source
        try:
            verify(source.replace(old, new), render)
        except AssertionError:
            pass
        else:
            raise AssertionError('regression accepted: ' + old)
    assert len(mutations) == 7
    print(f'check_terrain_draw_batch ok: {check_geometry()} real vertex transforms; 7 rejected mutations')


if __name__ == '__main__':
    main()
