"""Check what batches the draw submission of the main scene today. It does not start a game.

Cause 5 of the slow frames is the submission of the main scene (SceneManager::_renderVisibleObjects: one
renderSingleObject, one GPU parameter update and one draw per tile, room and creature part). No change that keeps the
look exactly was found that is safe to make without a profile and a build (see the result of package F1): merging
tiles into static geometry or instancing them changes the shader inputs of every tile material, and the seat
colour clones (colourizeMaterial) are separate materials by design. So this check only guards the batching that
exists, so that none of it is lost by accident:
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
print('ok')
