"""The ghost keeps a recognisable figure and leaves no blood (owner decision 998 point 7). Compiles nothing.

Screenshot ODscreenshot_2026-11-09_153144_17 showed a flat spiky green heap on the floor next to a blood stain. Findings:
1. The heap is a ghost: GhostEntity is the only user of Ghost.mesh, and the translucent green GhostGlow material is set
   only on ghost entities.
2. The ghost is authored and animated upright and nothing lays it down: the mesh stands about 1.35 tall in its bind
   pose, no bone of its Idle or Walk clip turns more than 30 degrees, its walk direction is flat and no code pitches the
   ghost's node.
3. Since commit a4050a9d5 (2026-11-07, two days before build 0.7.4.57) every animated rendered object, the ghost
   included, was skinned on the GPU through a prepared copy of its material (useShaderSkinning: RTSS skinning stage plus
   prepareEntityForSkinning). GhostEntity::updateLook calls setMeshOpacity every frame, and every opacity value swaps in
   an "_alpha_" clone of the current material (RenderManager::setEntityOpacity / setMaterialOpacity), made by a plain
   clone without that preparation; while the ghost rises, dissolves or is poured into the cauldron it is a fresh clone
   nearly every frame. Ogre chooses between GPU and CPU skinning when a material is set, so a skinned entity whose
   material copies are swapped outside useShaderSkinning can be drawn with mismatched bone matrices: vertices of most
   bones collapse, which reads as a flat spiky heap. This is the most likely cause found by reading the code; it was not
   reproduced in the game (no build in this package). The fix keeps ghosts on CPU skinning, as before a4050a9d5, so the
   figure no longer depends on which material copy is shown.
4. The blood stain is not from the ghost: the dying creature leaves a blood DirtPile in its death turn (GHOSTS-PLAN 5.2:
   "turn 0 unchanged (items, blood, owner told)"), and its ghost rises from the same spot (GHOSTS-PLAN D1). Undead leave
   neither blood nor a ghost. GhostEntity creates no dirt pile.
"""
from pathlib import Path
import importlib.util
import math
import re
import struct

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def body(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def code_only(text):
    return re.sub(r'//[^\n]*', '', text)


sources = {path.relative_to(repo).as_posix(): code_only(path.read_text(encoding='utf-8', errors='replace'))
           for path in (repo / 'source').rglob('*.cpp') if 'tests' not in path.parts}

# --- 1. The heap is a ghost ------------------------------------------------------------------------------------------------
mesh_users = sorted(path for path, text in sources.items() if re.search(r'"Ghost(\.mesh)?"', text))
assert mesh_users == ['source/entities/GhostEntity.cpp'], mesh_users
glow_users = sorted(path for path, text in sources.items() if '"GhostGlow"' in text)
assert glow_users == ['source/render/RenderManager.cpp'], glow_users
render = sources['source/render/RenderManager.cpp']
generic = render[render.index('ent = mSceneManager->createEntity(tempString, meshPtr);'):]
generic = generic[:generic.index('renderedMovableEntity->setParentSceneNode')]
assert 'if(renderedMovableEntity->getObjectType() == GameEntityType::ghostEntity)\n        {\n            ent->setMaterialName("GhostGlow");' \
    in generic.replace('\r\n', '\n'), 'GhostGlow only on ghosts'

# --- 2. Authored and animated upright, never laid down ---------------------------------------------------------------------
spec = importlib.util.spec_from_file_location('ghost_mesh_reader', repo / 'source/tests/check_ghost_apparatus_visible.py')
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
mesh = reader.read_mesh('Ghost')
low = mesh['bounds'][:3]
high = mesh['bounds'][3:6]
assert high[2] - low[2] > 1.2, 'a standing figure about 1.35 tall'
assert mesh['skeleton'] == 'Ghost.skeleton'
# The hooded body stands above the floor in front (y < 0), the torn hem trails behind it
front = [p for p in mesh['positions'] if p[1] < 0.0]
assert min(p[2] for p in front) > 0.1 and max(p[2] for p in front) > 1.1, 'an upright body, not a heap'
spec = importlib.util.spec_from_file_location('ghost_chunks', repo / 'tools/blender-assets/splice_animation_chunks.py')
chunks_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chunks_module)
_, chunks = chunks_module.chunks((repo / 'models/Ghost.skeleton').read_bytes())
clips = {name: data for kind, name, data in chunks if kind == chunks_module.ANIMATION}
assert {'Idle', 'Walk'} <= set(clips), set(clips)
for clip, data in clips.items():
    _, tracks = chunks_module.animation_children(data)
    for kind, bone, track in tracks:
        if kind != 0x4100:
            continue
        position = 8
        while position < len(track):
            _, size = struct.unpack_from('<HI', track, position)
            # key frame: time, then the rotation quaternion x y z w
            w = struct.unpack_from('<5f', track, position + 6)[4]
            turn = math.degrees(2 * math.acos(min(1.0, abs(w))))
            assert turn <= 30.0, ('no lying pose in the ghost clips', clip, bone, turn)
            position += size
movable = sources['source/entities/MovableGameEntity.cpp']
assert movable.count('setWalkDirection(Ogre::Vector3(walkDirection.x * facing,walkDirection.y * facing,0));') == 2, \
    'the ghost turns flat while it floats'
ghost = sources['source/entities/GhostEntity.cpp']
for turn in ('setOrientation(', 'pitch(', 'roll(', 'rotate(', 'rrOrientEntityToward'):
    assert turn not in ghost, ('nothing tilts the ghost node', turn)
look = body(ghost, 'void GhostEntity::updateLook()')
assert 'node->setScale(Ogre::Vector3::UNIT_SCALE*static_cast<Ogre::Real>(scale));' in look

# --- 3. The figure does not depend on the material copy shown for its opacity --------------------------------------------
assert 'setMeshOpacity(alpha);' in look, 'the opacity is set every frame'
assert 'alpha *= static_cast<float>(progress);' in look and 'alpha *= static_cast<float>(1.0 - progress);' in look, \
    'and it changes every frame while the ghost rises and dissolves'
opacity = body(render, 'void RenderManager::setEntityOpacity(Ogre::Entity* ent, float opacity)')
assert 'subEntity->setMaterialName(setMaterialOpacity(subEntity->getMaterialName(), opacity));' in opacity
material_opacity = body(render, 'std::string RenderManager::setMaterialOpacity(const std::string& materialName, float opacity)')
assert 'newMaterialName << "_alpha_" << static_cast<int>(opacity * 255.0f);' in material_opacity
assert 'oldMaterial->clone(newMaterialName.str());' in material_opacity
assert 'prepareEntityForSkinning' not in material_opacity and 'prepareEntityForSkinning' not in opacity, \
    'the opacity copies are never prepared for GPU skinning'
assert render.count('prepareEntityForSkinning(') == 1
# so the ghost is skinned on the CPU
assert 'if(renderedMovableEntity->getObjectType() != GameEntityType::ghostEntity)\n            useShaderSkinning(ent);' \
    in generic.replace('\r\n', '\n')
assert generic.count('useShaderSkinning(') == 1
assert not any('useShaderSkinning(' in text for path, text in sources.items()
               if path not in ('source/render/RenderManager.cpp', 'source/render/RenderManagerChickens.cpp')), \
    'no other path skins a ghost on the GPU'

# --- 4. The blood stain belongs to the dying creature, never to its ghost ------------------------------------------------
assert 'DirtPile' not in ghost, 'a ghost leaves no dirt or blood'
creature = sources['source/entities/Creature.cpp']
death = creature[creature.index('OD_LOG_INF("Creature=" + getName() + " RIP");'):]
death = death[:death.index('mDeathCounter = 1;')]
blood = death.index('DirtPileEntity::createOnTile(getGameMap(), getPositionTile(), DirtPileKind::blood, getDefinition()->getClassName());')
spawn = death.index('GhostEntity* ghost = new GhostEntity(getGameMap(), *this);')
assert blood < spawn, 'the blood of the death turn comes first, from the creature'
assert 'if(getIsOnServerMap() && (getPositionTile() != nullptr) && !getDefinition()->isUndead())' in death
assert 'if(getIsOnServerMap() && !getDefinition()->isWorker() && !getDefinition()->isUndead())' in death
assert death.count('DirtPileKind::blood') == 1 and death.count('new GhostEntity(') == 1
print('ghost figure: a ghost, upright, CPU-skinned through its opacity changes; the blood belongs to the dead creature: ok')
