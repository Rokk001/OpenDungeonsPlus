"""Check that the terrain batch accepts exactly the world-space tile shaders, without compiling.

Removed cause: direct draw submission (48.19% of the P1 frame in build 52), where the terrain batch
accepted only the Dirt material. The batch now accepts rock, gold ground, claimed ground and room
floors through their DirtTile, Room and ClaimedTile shaders. This check proves from the shaders and
materials that baking the world transform keeps every value these shaders compute, and rejects
source mutations that would admit an unsafe shader or parameter. Runtime draw savings still need the
release build.
"""
from pathlib import Path
import math
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']

# Fixed once from the branch: shader family -> shadow projection auto constant.
FAMILIES = {
    'DirtTile': 'ACT_TEXTURE_VIEWPROJ_MATRIX',
    'Room': 'ACT_TEXTURE_WORLDVIEWPROJ_MATRIX',
    'ClaimedTile': 'ACT_TEXTURE_WORLDVIEWPROJ_MATRIX',
}
# The world-independent automatic constants the batch accepts (besides the family's shadow projection).
ALLOWED = {
    'ACT_WORLD_MATRIX', 'ACT_VIEW_MATRIX', 'ACT_PROJECTION_MATRIX', 'ACT_AMBIENT_LIGHT_COLOUR',
    'ACT_LIGHT_DIFFUSE_COLOUR_ARRAY', 'ACT_LIGHT_SPECULAR_COLOUR_ARRAY', 'ACT_LIGHT_POSITION_ARRAY',
    'ACT_LIGHT_ATTENUATION_ARRAY', 'ACT_LIGHT_COUNT', 'ACT_LIGHT_CASTS_SHADOWS', 'ACT_CAMERA_POSITION',
    'ACT_SURFACE_DIFFUSE_COLOUR',
}
# Material script names of these constants.
SCRIPT_NAMES = {
    'world_matrix': 'ACT_WORLD_MATRIX', 'view_matrix': 'ACT_VIEW_MATRIX',
    'projection_matrix': 'ACT_PROJECTION_MATRIX', 'ambient_light_colour': 'ACT_AMBIENT_LIGHT_COLOUR',
    'light_diffuse_colour_array': 'ACT_LIGHT_DIFFUSE_COLOUR_ARRAY',
    'light_specular_colour_array': 'ACT_LIGHT_SPECULAR_COLOUR_ARRAY',
    'light_position_array': 'ACT_LIGHT_POSITION_ARRAY',
    'light_attenuation_array': 'ACT_LIGHT_ATTENUATION_ARRAY', 'light_count': 'ACT_LIGHT_COUNT',
    'light_casts_shadows': 'ACT_LIGHT_CASTS_SHADOWS', 'camera_position': 'ACT_CAMERA_POSITION',
    'surface_diffuse_colour': 'ACT_SURFACE_DIFFUSE_COLOUR',
    'texture_viewproj_matrix': 'ACT_TEXTURE_VIEWPROJ_MATRIX',
    'texture_worldviewproj_matrix': 'ACT_TEXTURE_WORLDVIEWPROJ_MATRIX',
}


def verify(source):
    """Require the paired shader test, the parameter whitelist and the unchanged registration gates."""
    registration = body(source, 'void TerrainDrawBatch::add(')
    assert 'if(!isWorldSpaceTilePass(*pass) || pass->isTransparent() || !pass->getDepthWriteEnabled())' in registration
    assert 'getNumPasses() != 1' in registration and 'getCastShadows()' in registration
    table = source[source.index('const WorldSpaceTileShader WORLD_SPACE_TILE_SHADERS[]'):]
    table = table[:table.index('};')]
    rows = re.findall(r'\{"(\w+)\.vert", "(\w+)\.frag", Ogre::GpuProgramParameters::(ACT_\w+)\}', table)
    assert {vert: act for vert, frag, act in rows} == FAMILIES, rows
    assert all(vert == frag for vert, frag, _ in rows) and len(rows) == 3
    constants = body(source, 'bool hasWorldSpaceAutoConstants(')
    accepted = set(re.findall(r'case Ogre::GpuProgramParameters::(ACT_\w+):', constants))
    assert accepted == ALLOWED, accepted ^ ALLOWED
    assert 'if(!parameters)\n        return false;' in constants
    assert 'if(constant.paramType != shadowMatrix)\n                    return false;' in constants
    passes = body(source, 'bool isWorldSpaceTilePass(')
    assert 'pass.getMaxSimultaneousLights() < TerrainDrawBatch::TILE_SHADER_LIGHTS' in passes
    assert 'vertexSource != shader.mVertexSource || fragmentSource != shader.mFragmentSource' in passes
    assert 'getVertexProgram()->getSourceFile()' in passes and 'getFragmentProgram()->getSourceFile()' in passes
    assert 'hasWorldSpaceAutoConstants(pass.getVertexProgramParameters(), shader.mShadowMatrix) &&' in passes
    assert 'hasWorldSpaceAutoConstants(pass.getFragmentProgramParameters(), shader.mShadowMatrix)' in passes
    assert passes.rstrip('}').rstrip().endswith('return false;')


def check_shaders():
    """Each vertex shader works in world space; Room and ClaimedTile cancel the world matrix themselves."""
    shaders = ROOT / 'shaders'
    dirt = (shaders / 'DirtTile.vert').read_text()
    room = (shaders / 'Room.vert').read_text()
    claimed = (shaders / 'ClaimedTile.vert').read_text()
    assert 'vec3 P = (worldMatrix * position).xyz;' in dirt and 'VertexPos = lightMatrix * vec4(P, 1.0);' in dirt
    assert 'vec3 P = (worldMatrix * position).xyz;' in room
    assert 'VertexPos = lightMatrix * inverse(worldMatrix) * vec4(P, 1.0);' in room
    assert 'vec4 P4 = (worldMatrix * position);' in claimed
    assert 'vec4 P_prim = inverse(worldMatrix) * vec4(P, 1.0);' in claimed and 'VertexPos = lightMatrix * P_prim;' in claimed
    for text in (dirt, room, claimed):
        # Normals and tangents only enter through the world matrix; StaticGeometry rotates them the same way.
        assert 'deform(P)' in text and 'normalize(vec3(worldMatrix * vec4(tangent, 0.0)))' in text
    for name in ('DirtTile.frag', 'Room.frag', 'ClaimedTile.frag'):
        fragment = (shaders / name).read_text()
        assert 'worldMatrix' not in fragment and 'tangentOut' not in fragment
        assert 'getLocalLighting(FragPos, Normal, cameraPosition.xyz, shadow.r)' in fragment


def check_materials():
    """Every material of the three families uses only accepted constants and its family's shadow matrix."""
    counts = {family: 0 for family in FAMILIES}
    for path in sorted((ROOT / 'materials').rglob('*.material')):
        text = path.read_text(encoding='utf-8', errors='replace')
        sources = re.findall(r'^\s*source\s+(\w+)\.(vert|frag)\s*$', text, re.M)
        families = {name for name, _ in sources if name in FAMILIES}
        if not families:
            continue
        assert len(families) == 1, path
        family = families.pop()
        counts[family] += 1
        used = {SCRIPT_NAMES[name] for name in re.findall(r'param_named_auto\s+\w+\s+(\w+)', text)}
        assert used <= ALLOWED | {FAMILIES[family]}, (path.name, used - ALLOWED)
        assert FAMILIES[family] in used, path.name
        assert re.findall(r'(light_\w+_array) (\d+)', text) and all(
            size == '8' for _, size in re.findall(r'(light_\w+_array) (\d+)', text)), path.name
    # Fixed once from the branch's material scripts.
    assert counts == {'DirtTile': 2, 'Room': 71, 'ClaimedTile': 5}, counts
    return sum(counts.values())


def mat_mul(a, b):
    """Multiply two 4x4 matrices."""
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def apply(m, p):
    """Apply a 4x4 matrix to a homogeneous point."""
    return [sum(m[r][k] * p[k] for k in range(4)) for r in range(4)]


def rigid(x, y, degrees):
    """World matrix of a tile: rotation about Z by a tileset angle, then translation."""
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return [[c, -s, 0, x], [s, c, 0, y], [0, 0, 1, 0], [0, 0, 0, 1]], [[c, s, 0, -(c * x + s * y)],
            [-s, c, 0, -(-s * x + c * y)], [0, 0, 1, 0], [0, 0, 0, 1]]


def check_shadow_projection():
    """Compare per-object and batched shadow coordinates for each family's shadow matrix."""
    texture_view_proj = [[0.5, 0.1, 0.0, 2.0], [0.0, 0.4, 0.2, -1.0], [0.1, 0.0, 0.3, 0.5], [0.0, 0.05, 0.1, 1.0]]
    identity = [[1.0 if r == c else 0.0 for c in range(4)] for r in range(4)]
    compared = 0
    for x, y, degrees in [(-7, 3, 0), (0, 0, 90), (12, -4, 180), (3, 5, 270)]:
        world, inverse = rigid(x, y, degrees)
        for local in [(0.3, -0.2, 0.0, 1.0), (-0.5, 0.5, 1.2, 1.0), (0.1, 0.4, 0.7, 1.0)]:
            p_world = apply(world, local)
            # DirtTile: texture_viewproj_matrix applied to the world position; the batch passes the baked one.
            assert max(abs(a - b) for a, b in zip(apply(texture_view_proj, p_world),
                                                   apply(texture_view_proj, apply(identity, p_world)))) < 1e-9
            # Room/ClaimedTile: texture_worldviewproj_matrix * inverse(worldMatrix) * P.
            per_object = apply(mat_mul(mat_mul(texture_view_proj, world), inverse), p_world)
            batched = apply(mat_mul(mat_mul(texture_view_proj, identity), identity), p_world)
            assert max(abs(a - b) for a, b in zip(per_object, batched)) < 1e-9
            # Negative control: without the inverse the world matrix does not cancel, so the pairing matters.
            unpaired = apply(mat_mul(texture_view_proj, world), p_world)
            if degrees or x or y:
                assert max(abs(a - b) for a, b in zip(unpaired, batched)) > 1e-3
            compared += 1
    assert compared == 12
    return compared


def main():
    """Run the source, shader, material and projection checks and reject six source regressions."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text(encoding='utf-8')
    header = (ROOT / 'source/render/TerrainDrawBatch.h').read_text(encoding='utf-8')
    assert 'static const unsigned short TILE_SHADER_LIGHTS = 8;' in header
    verify(source)
    check_shaders()
    materials = check_materials()
    projections = check_shadow_projection()
    mutations = [
        ('{"Room.vert", "Room.frag", Ogre::GpuProgramParameters::ACT_TEXTURE_WORLDVIEWPROJ_MATRIX}',
         '{"Room.vert", "Room.frag", Ogre::GpuProgramParameters::ACT_TEXTURE_VIEWPROJ_MATRIX}'),
        ('            case Ogre::GpuProgramParameters::ACT_CAMERA_POSITION:\n',
         '            case Ogre::GpuProgramParameters::ACT_CAMERA_POSITION:\n'
         '            case Ogre::GpuProgramParameters::ACT_WORLDVIEW_MATRIX:\n'),
        ('if(!isWorldSpaceTilePass(*pass) || ', 'if('),
        ('vertexSource != shader.mVertexSource || fragmentSource != shader.mFragmentSource',
         'vertexSource != shader.mVertexSource'),
        ('pass.getMaxSimultaneousLights() < TerrainDrawBatch::TILE_SHADER_LIGHTS', 'false'),
        ('hasWorldSpaceAutoConstants(pass.getVertexProgramParameters(), shader.mShadowMatrix) &&', 'true &&'),
    ]
    for old, new in mutations:
        assert old in source, old
        try:
            verify(source.replace(old, new))
        except (AssertionError, ValueError):
            continue
        raise AssertionError('regression accepted: ' + old)
    assert len(mutations) == 6
    print(f'check_world_space_tile_batching ok: {materials} tile materials, {projections} shadow projections, '
          f'{len(mutations)} rejected mutations; runtime draw savings unverified')


if __name__ == '__main__':
    main()
