"""Check that animated objects other than creatures and menu models are skinned on the GPU. It does not start a game.

Chickens, doors, beds, ghosts, the SmallSpider and the other animated rendered objects use RTSS materials that are
shared with static meshes. They are skinned on the GPU with RenderManager::useShaderSkinning, which works on a copy
of each material. It leaves an entity alone when a material has its own vertex program.
"""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
render = (repo / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')

# The generic rendered object path, after the ghost material is set and before the cauldron flame uses the bones
generic = render[render.index('ent = mSceneManager->createEntity(tempString, meshPtr);'):]
generic = generic[:generic.index('renderedMovableEntity->setParentSceneNode')]
assert 'ent->setMaterialName("GhostGlow");' in generic
assert generic.index('ent->setMaterialName("GhostGlow");') < generic.index('useShaderSkinning(ent);') \
    < generic.index('meshName == "Cauldron"')

# The chicken that is eaten
assert 'useShaderSkinning(feeding.mChickenEntity);' in render

# Parts whose visibility is found by material name keep their material
start = render.index('bool RenderManager::useShaderSkinning(Ogre::Entity* entity)')
body = render[start:render.index('Adds a menu point light with its own scene node', start)]
assert 'material->getName() == "ItemBagSealed"' in body and 'material->getName() == "ChickenStraw"' in body
assert 'part->getMaterialName() == "ChickenStraw"' in (repo / 'source/render/RenderManagerChickens.cpp').read_text(encoding='utf-8')
assert 'materialName == "ItemBagSealed"' in render
# Meshes with vertex animation (poses) cannot be skinned by the stage
assert 'hasVertexAnimation()' in body
print('ok')
