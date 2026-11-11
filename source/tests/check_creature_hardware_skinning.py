"""Check that the animated creatures are skinned on the GPU and not on the CPU. It does not start a game.

Cause 1 of the slow frames: no material declared hardware skinning, so Ogre skinned every visible animated
creature on the CPU (Mesh::softwareVertexBlend), in the main pass and again in the shadow texture pass.

An entity is skinned on the GPU only when the first pass of ALL its sub entity materials uses a vertex program that
includes skeletal animation, and a hardware skinned entity needs a skinning shadow caster, otherwise its shadow
would show the bind pose. This check follows that chain: shader, material scripts, the shadow caster, the meshes
that use the creature materials, the contour pass and the Wyvern metal part.
"""
from pathlib import Path
import re
import struct
import sys

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


# The bone matrices are 3 vec4 per bone
vert = read('shaders/Creature.vert')
match = re.search(r'uniform\s+vec4\s+boneMatrices\[(\d+)\]', vert)
assert match, 'Creature.vert has no bone matrix array'
max_bones = int(match.group(1)) // 3
assert 'layout (location = 1) in vec4 blendWeights;' in vert and 'layout (location = 7) in vec4 blendIndices;' in vert
assert 'viewProjectionMatrix' in vert and 'uniform    mat4 projectionMatrix' not in vert, 'the former projection and view pair is still used'
# OGRE 14 keeps bone matrices in object space (MeshManager::getBonesUseObjectSpace() is true by default and
# world_matrix_array_3x4 is an alias of bone_matrix_array_3x4), so the skinned position must still be moved into
# world space with the entity's world matrix; without it every creature is drawn around the map origin (build 58).
assert 'uniform    mat4 worldMatrix' in vert and 'P = (worldMatrix * vec4(P, 1.0)).xyz;' in vert, 'the skinned position is not moved into world space'
assert 'uniform    mat4 lightMatrix' in vert and 'lightMatrix * vec4(P, 1.0)' in vert, 'the shadow coordinate must use the skinned position'

materials = sorted((repo / 'materials/scripts/Creatures').glob('*.material'))
assert len(materials) >= 33
creature_material_names = set()
for path in materials:
    text = path.read_text(encoding='utf-8')
    names = re.findall(r'^material\s+(\S+)', text, re.M)
    creature_material_names.update(names)
    programs = re.findall(r'vertex_program\s+(\S+)\s+glsl\s*\{(.*?)\n\s*\}\s*\n', text, re.S)
    assert programs, path.name
    for name, body in programs:
        if 'source Creature.vert' not in body:
            continue
        assert re.search(r'includes_skeletal_animation\s+true', body), '%s: %s does not declare hardware skinning' % (path.name, name)
        assert 'param_named_auto boneMatrices world_matrix_array_3x4' in body, path.name
        assert 'param_named_auto viewProjectionMatrix viewproj_matrix' in body, path.name
        assert 'param_named_auto lightMatrix texture_viewproj_matrix 0' in body, path.name
        assert re.search(r'param_named_auto\s+worldMatrix\s+world_matrix\s*$', body, re.M), '%s: the object space bones need the world matrix' % path.name
        assert 'projectionMatrix projection_matrix' not in body and 'texture_worldviewproj_matrix' not in body, '%s still has CPU skinning params' % path.name
    techniques = len(re.findall(r'^\s*technique\b', text, re.M))
    casters = len(re.findall(r'^\s*shadow_caster_material\s+CreatureShadowCaster\s*$', text, re.M))
    assert techniques == casters == len(names), '%s: every technique needs the skinning shadow caster' % path.name

# The skinning shadow caster
skinning = read('materials/scripts/CreatureSkinning.material')
caster_program = re.search(r'vertex_program\s+CreatureShadowCasterVertexShader\s+glsl\s*\{(.*?)\n\}', skinning, re.S).group(1)
assert 'includes_skeletal_animation true' in caster_program and 'world_matrix_array_3x4' in caster_program
assert 'shadow_caster_material' not in skinning.split('material CreatureShadowCaster')[1], 'the caster must not point to itself'
caster = read('shaders/CreatureShadowCaster.vert')
assert 'blendWeights' in caster and 'blendIndices' in caster and 'boneMatrices[768]' in caster
assert 'boneMatrices[768]' in vert

# Every skinned mesh of a creature material must use creature materials only (plus the Wyvern metal), because one
# unskinned sub entity material makes Ogre skin the whole entity on the CPU again.
reflmetal = read('materials/scripts/ReflMetal.material')
skinned_metal = reflmetal.split('material ReflMetalSkinned')[1]
assert 'myReflMetalSkinnedVertexShader' in skinned_metal and 'shadow_caster_material CreatureShadowCaster' in skinned_metal
assert 'includes_skeletal_animation' not in reflmetal.split('vertex_program myReflMetalSkinnedVertexShader')[0], 'ReflMetal of the weapons must stay unskinned'
rm_vert = read('shaders/ReflMetalSkinned.vert')
assert 'blendIndices' in rm_vert and 'boneMatrices[768]' in rm_vert
render = read('source/render/RenderManager.cpp')
assert render.count('useSkinnedMetalMaterial(ent);') == 2, 'creature entities (create and mesh change) need the skinned metal'
assert 'part->setMaterialName("ReflMetalSkinned")' in render


def submesh_materials(path):
    data = path.read_bytes()
    pos = data.index(b'\n') + 1
    chunk_id, length = struct.unpack_from('<HI', data, pos)
    assert chunk_id == 0x3000
    end = pos + length
    skeletal = data[pos + 6]
    cur = pos + 7
    mats = []
    while cur + 6 <= end:
        chunk_id, length = struct.unpack_from('<HI', data, cur)
        if chunk_id == 0x4000:
            start = cur + 6
            mats.append(data[start:data.index(b'\n', start)].decode('latin1'))
        if length < 6:
            break
        cur += length
    return skeletal, mats


checked = 0
for mesh in sorted((repo / 'models').glob('*.mesh')):
    skeletal, mats = submesh_materials(mesh)
    if not skeletal or not any(m in creature_material_names for m in mats):
        continue
    checked += 1
    others = [m for m in mats if m not in creature_material_names]
    if mesh.name == 'Wyvern.mesh':
        assert others == ['ReflMetal'], (mesh.name, others)
    else:
        assert not others, '%s has sub entity materials without hardware skinning: %s' % (mesh.name, others)
assert checked >= 30, checked

# The bone matrices of the largest skeleton must fit in the uniform array (3 vec4 per bone, 1 index per used bone)
for skeleton in (repo / 'models').glob('*.skeleton'):
    if skeleton.stem + '.mesh' not in [m.name for m in (repo / 'models').glob('*.mesh')]:
        continue
    bones = skeleton.read_bytes().count(b'\x00\x30\x0a\x00\x00\x00') + 1
    if skeleton.stem in ('RunelordDwarf', 'NatureMonster', 'Cultist', 'Monk'):
        assert bones <= max_bones, (skeleton.name, bones, max_bones)

# The contour pass of a highlighted creature skins like the creature, or it would show the bind pose
enlarge = read('shaders/Enlarge.vert')
assert 'blendIndices' in enlarge and 'boneMatrices[768]' in enlarge and 'worldViewProj' not in enlarge
assert 'uniform    float pixelWidth;' in enlarge and 'clip.xy += dir * pixelWidth' in enlarge and 'N += weights[i]' in enlarge
assert 'vertex_program->setSkeletalAnimationIncluded(true);' in render
assert 'setNamedAutoConstant("boneMatrices", Ogre::GpuProgramParameters::ACT_WORLD_MATRIX_ARRAY_3x4)' in render
assert 'setNamedAutoConstant("worldViewProj"' not in render

print('ok')
