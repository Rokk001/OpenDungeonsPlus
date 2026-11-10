"""Regression check for the invisible creatures of build 58. It does not start a game.

The hardware skinned creature programs read their bones from world_matrix_array_3x4. In OGRE 14 that name is an
alias of bone_matrix_array_3x4, and MeshManager::getBonesUseObjectSpace() is true by default, so the uploaded bone
matrices are in OBJECT space: SubEntity::getWorldTransforms passes the entity's world transform separately and
Entity::updateAnimation does not build world space bone matrices. The authored skinning shaders of build 58 treated
the bones as world space and never applied the entity transform, so every creature body, its shadow, its metal part
and its contour were drawn around the map origin instead of at the creature, and only the level badges were left.

This check requires that the game keeps OGRE's object space bones, and that every authored program that reads the
bone array also binds world_matrix and moves the skinned position (and directions) into world space with it.
"""
from pathlib import Path
import os
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def check_pinned_ogre():
    """When the pinned Ogre source is present, confirm that it keeps the bones in object space."""
    deps = Path(os.environ.get('BUILD_DEPS_ROOT', Path(os.environ.get('USERPROFILE', '')) / 'build-deps'))
    src = deps / 'src/ogre/OgreMain/src'
    if not (src / 'OgreMeshManager.cpp').is_file():
        return 'pinned Ogre source absent, shaders only'
    def ogre(name):
        return (src / name).read_text(encoding='utf-8', errors='replace')
    assert 'bool MeshManager::mBonesUseObjectSpace = true;' in ogre('OgreMeshManager.cpp')
    assert 'AutoConstantDefinition(ACT_BONE_MATRIX_ARRAY_3x4,        "world_matrix_array_3x4"' in ogre('OgreGpuProgramParams.cpp')
    params = ogre('OgreAutoParamDataSource.cpp')
    assert 'return mWorldMatrixArray + int(MeshManager::getBonesUseObjectSpace());' in params
    # world_matrix stays the entity transform, the first entry before the bones
    assert 'return mWorldMatrixArray[0];' in params
    sub = ogre('OgreSubEntity.cpp')
    transforms = sub[sub.index('void SubEntity::getWorldTransforms('):sub.index('SubEntity::getNumWorldTransforms(')]
    assert '*xform++ = mParentEntity->_getParentNodeFullTransform();' in transforms
    assert '? mParentEntity->mBoneMatrices' in transforms
    return 'pinned Ogre source confirmed'


# The game must not switch OGRE to world space bones, which the RTSS skinning of the menu models and animated
# objects also depends on; the authored shaders below are written for the default object space bones.
for path in list((repo / 'source').rglob('*.cpp')) + list((repo / 'source').rglob('*.h')):
    assert 'setBonesUseObjectSpace' not in path.read_text(encoding='utf-8', errors='replace'), path

# Every authored program declaring the bone array applies the world matrix to the skinned position.
skinning_shaders = {
    'shaders/Creature.vert': 'P = (worldMatrix * vec4(P, 1.0)).xyz;',
    'shaders/ReflMetalSkinned.vert': 'P = (worldMatrix * vec4(P, 1.0)).xyz;',
    'shaders/CreatureShadowCaster.vert': 'gl_Position = viewProjectionMatrix * (worldMatrix * vec4(P, 1.0));',
    'shaders/Enlarge.vert': 'vec4 clip = viewProjectionMatrix * (worldMatrix * vec4(P, 1.0));',
}
found = set()
for path in (repo / 'shaders').glob('*.vert'):
    if re.search(r'uniform\s+vec4\s+boneMatrices\[', path.read_text(encoding='utf-8')):
        found.add('shaders/' + path.name)
assert found == set(skinning_shaders), sorted(found)
for name, applied in skinning_shaders.items():
    text = read(name)
    assert re.search(r'^uniform\s+mat4\s+worldMatrix;', text, re.M), '%s does not declare worldMatrix' % name
    assert applied in text, '%s does not move the skinned position into world space' % name
    # the position goes to the screen only after the world matrix
    main = text.split('void main')[1]
    assert main.index(applied) <= main.index('viewProjectionMatrix *'), name

# Directions follow the world matrix as well, as the former unskinned shaders did.
creature = read('shaders/Creature.vert')
assert 'vec3 T = normalize(vec3(worldMatrix * vec4(skinTangent, 0.0)));' in creature
assert 'vec3 B = normalize(vec3(worldMatrix * vec4(cross(skinTangent, skinNormal), 0.0)));' in creature
assert 'VertexPos = lightMatrix * vec4(P, 1.0);' in creature
assert creature.index('P = (worldMatrix * vec4(P, 1.0)).xyz;') < creature.index('VertexPos = lightMatrix')
assert 'out_Normal = mat3(worldMatrix) * skinNormal;' in read('shaders/ReflMetalSkinned.vert')
assert 'vec2 dir = (viewMatrix * (worldMatrix * vec4(N, 0.0))).xy;' in read('shaders/Enlarge.vert')

# Every material program that binds the bone array also binds the world matrix.
programs = 0
for path in (repo / 'materials').rglob('*.material'):
    text = path.read_text(encoding='utf-8')
    for name, body in re.findall(r'vertex_program\s+(\S+)\s+glsl\s*\{(.*?)\n\s*\}\s*\n\s*\}', text, re.S):
        if 'world_matrix_array_3x4' not in body:
            continue
        programs += 1
        assert re.search(r'param_named_auto\s+boneMatrices\s+world_matrix_array_3x4\s*$', body, re.M), (path.name, name)
        assert re.search(r'param_named_auto\s+worldMatrix\s+world_matrix\s*$', body, re.M), \
            '%s: %s reads object space bones without the world matrix' % (path.name, name)
# 33 creature material files, the skinning shadow caster and the skinned metal
assert programs >= 35, programs

# The contour pass built in code binds the world matrix next to the bones.
render = read('source/render/RenderManager.cpp')
outliner = render.split('void RenderManager::rrAddOutliner')[1].split('void RenderManager::rrRemoveOutliner')[0]
assert 'setNamedAutoConstant("boneMatrices", Ogre::GpuProgramParameters::ACT_WORLD_MATRIX_ARRAY_3x4)' in outliner
assert 'setNamedAutoConstant("worldMatrix", Ogre::GpuProgramParameters::ACT_WORLD_MATRIX)' in outliner

print('ok: ' + check_pinned_ogre())
