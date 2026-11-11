"""Check what batches the draw submission of the main scene today. It does not start a game.

Cause 5 is main-scene submission: one renderSingleObject, GPU parameter update and draw per object part.
Earth now shares draws within small cells only when each original has the same ordered light list.
The original entities remain available for picking and fallback; the separate terrain check covers that contract.
This check also guards the existing batches so none are lost by accident:
  - the fog of war clouds are drawn as hardware instanced batches,
  - tile meshes of the tile node are not shadow casters (they add nothing to the shadow pass),
  - the dirt fog instancing material keeps its instancing shader.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
render = (repo / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')

assert 'Ogre::InstanceManager::HWInstancingBasic' in render
assert 'mInstanceManagerCloud->defragmentBatches(true);' in render
assert 'createInstancedEntity("Fog")' in render
assert 'tileMeshEnt->setCastShadows(false);' in render

dirt = (repo / 'materials/scripts/DirtInstanced.material').read_text(encoding='utf-8')
assert 'source DirtTileInstanced.vert' in dirt

terrain = (repo / 'source/render/TerrainDrawBatch.cpp').read_text(encoding='utf-8')
assert 'createStaticGeometry' in terrain and 'lights != mLights' in terrain
assert 'mTerrainDrawBatch.add(mSceneManager, tileMeshEnt);' in render
assert 'mTerrainDrawBatch.add(mSceneManager, entity);' in render
print('ok')
