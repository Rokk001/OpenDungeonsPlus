"""Check the canonical light order of batch member tiles without compiling or starting a game.

Removed cause: GPU parameters (18.42% of the P1 frame in build 52 for the main view). Ogre uploads all
light parameters again whenever the ordered light list of a draw differs from the previous draw's, and
neighbouring tiles often have the same lights in a different distance order. Batch member tiles now get
Ogre's list with the shadow light first and the other lights in identity order, when the list fits the
8 tile shader light slots. The check proves from the tile shaders that only light 0 is special, models
the shader's light sum and the upload rule on fixed fixtures, and rejects source regressions. Runtime
upload savings still need the release build.
"""
from pathlib import Path
import itertools
import math
import re
import runpy

ROOT = Path(__file__).resolve().parents[2]
body = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']


def verify(source, header):
    """Require the light-0 rule, the 8-slot limit, Ogre's refresh rule and cache invalidation."""
    assert 'static const unsigned short TILE_SHADER_LIGHTS = 8;' in header
    assert 'std::map<const Ogre::MovableObject*, CanonicalLights> mCanonicalLights;' in header
    query = body(source, 'const Ogre::LightList* TerrainDrawBatch::Cell::objectQueryLights(')
    assert query.index('getMovableType() == "StaticGeometry"') < query.index('return &mLights;')
    assert 'if(node == nullptr || object->isParentTagPoint() || node->getCreator() == nullptr)\n        return nullptr;' in query
    assert 'const unsigned long counter = node->getCreator()->_getLightsDirtyCounter();' in query
    refresh = 'if(!entry.mValid || entry.mLightsDirtyCounter != counter)'
    assert refresh in query
    find = 'node->findLights(entry.mLights, object->getBoundingRadiusScaled(), object->getLightMask());'
    assert query.index(refresh) < query.index(find) < query.index('canonicalizeLightOrder(entry.mLights);')
    assert query.index('canonicalizeLightOrder(entry.mLights);') < query.index('entry.mLightsDirtyCounter = counter;')
    assert 'entry.mValid = true;' in query and query.rstrip('}').rstrip().endswith('return &entry.mLights;')
    order = body(source, 'void TerrainDrawBatch::canonicalizeLightOrder(')
    assert 'if(lights.size() < 3 || lights.size() > TILE_SHADER_LIGHTS)\n        return;' in order
    assert 'std::sort(lights.begin() + 1, lights.end(), std::less<Ogre::Light*>());' in order
    reset = body(source, 'void TerrainDrawBatch::invalidate(')
    assert 'cell.mCanonicalLights.clear();' in reset
    # Every cell source change passes through invalidate before the entity list changes.
    add = body(source, 'void TerrainDrawBatch::add(')
    assert add.index('invalidate(*cell);') < add.index('cell->mEntities.push_back(entity);')
    removal = body(source, 'void TerrainDrawBatch::remove(')
    assert removal.index('invalidate(cell);') < removal.index('cell.mEntities.erase(it);')
    # The batch compares canonical lists exactly, so equal light sets can share a batch.
    assert 'const Ogre::LightList& lights = entity->queryLights();' in body(source, 'bool TerrainDrawBatch::Cell::canBatch(')


def check_shaders():
    """Only light 0 differs from the others: it alone receives the single shadow texture."""
    lighting = (ROOT / 'shaders/LocalLighting.glsl').read_text()
    assert '#define MAX_LOCAL_LIGHTS 8' in lighting
    loop = lighting[lighting.index('vec3 getLocalLighting('):]
    loop = loop[:loop.index('return lighting;')]
    assert 'float visibility = i == 0 && firstLightCastsShadows > 0.5 ? shadow : 1.0;' in loop
    assert 'lighting += (diffuse * lightDiffuseColour[i].rgb + specular * lightSpecularColour[i].rgb)' in loop
    # No other index-specific term: every array is read with the loop index only.
    assert not re.search(r'\[(?!i\])[^\]]*\]', loop.replace('[MAX_LOCAL_LIGHTS]', '')), 'index-specific light term'
    for name in ('DirtTile.frag', 'Room.frag', 'ClaimedTile.frag'):
        fragment = (ROOT / 'shaders' / name).read_text()
        assert '#include "LocalLighting.glsl"' in fragment and 'lightPos' not in fragment
    materials = 0
    for path in sorted((ROOT / 'materials').rglob('*.material')):
        text = path.read_text(encoding='utf-8', errors='replace')
        if not re.search(r'^\s*source\s+(DirtTile|Room|ClaimedTile)\.frag\s*$', text, re.M):
            continue
        materials += 1
        assert re.findall(r'param_named_auto\s+\w+\s+light_casts_shadows\s+(\d+)', text) == ['0'], path.name
    assert materials == 78, materials
    return materials


def shade(lights, shadow):
    """Model getLocalLighting's sum for one fragment: light 0 alone gets the shadow factor."""
    total = 0.0
    for index, (diffuse, specular, attenuation, casts) in enumerate(lights[:8]):
        visibility = shadow if index == 0 and casts else 1.0
        total += (diffuse + specular) * attenuation * visibility
    return total


def canonical(lights):
    """Python model of canonicalizeLightOrder on light identities."""
    if len(lights) < 3 or len(lights) > 8:
        return list(lights)
    return [lights[0]] + sorted(lights[1:])


def check_model():
    """Fixed fixtures: canonical lists keep the shading, and equal sets stop repeating light uploads."""
    table = {name: (0.11 * (k + 1), 0.07 * (k + 2), 1.0 / (k + 1.5), k == 0)
             for k, name in enumerate('ABCDEFGHIJ')}
    checked = 0
    for count in range(1, 9):
        names = list('ABCDEFGH'[:count])
        for tail in itertools.permutations(names[1:]):
            ordered = [names[0]] + list(tail)
            original = shade([table[n] for n in ordered], 0.25)
            reordered = shade([table[n] for n in canonical(ordered)], 0.25)
            assert math.isclose(original, reordered, rel_tol=1e-12)
            checked += 1
    # Negative control: moving the shadow light out of slot 0 changes the image, so slot 0 must stay.
    assert not math.isclose(shade([table[n] for n in 'ABC'], 0.25), shade([table[n] for n in 'BAC'], 0.25))
    # Lists longer than the slots keep Ogre's order: reordering would change the lights the shader reads.
    nine = list('AJIHGFEDC')
    assert canonical(nine) == nine
    # Upload model: one upload per change of the ordered list between consecutive draws (Ogre's hash rule).
    draws = [list('ABC'), list('ACB'), list('ABC'), list('ACB'), list('AB'), list('BA'), list('ADCB'), list('ABDC')]

    def uploads(sequence):
        """Count light parameter uploads for consecutive draws."""
        return sum(1 for k, lights in enumerate(sequence) if k == 0 or lights != sequence[k - 1])

    assert uploads(draws) == 8 and uploads([canonical(d) for d in draws]) == 4
    return checked


def main():
    """Run the source, shader and model checks and reject six source regressions."""
    source = (ROOT / 'source/render/TerrainDrawBatch.cpp').read_text(encoding='utf-8')
    header = (ROOT / 'source/render/TerrainDrawBatch.h').read_text(encoding='utf-8')
    verify(source, header)
    materials = check_shaders()
    # Fixed once: sum over n = 1..8 of (n - 1)! tail permutations.
    fixtures = check_model()
    assert fixtures == 5914, fixtures
    mutations = [
        ('std::sort(lights.begin() + 1, lights.end()', 'std::sort(lights.begin(), lights.end()'),
        ('lights.size() < 3 || lights.size() > TILE_SHADER_LIGHTS', 'lights.size() < 3'),
        ('if(!entry.mValid || entry.mLightsDirtyCounter != counter)', 'if(!entry.mValid)'),
        ('    cell.mCanonicalLights.clear();\n', ''),
        ('        entry.mValid = true;\n', ''),
        ('if(node == nullptr || object->isParentTagPoint() || node->getCreator() == nullptr)',
         'if(node == nullptr)'),
    ]
    for old, new in mutations:
        assert old in source, old
        try:
            verify(source.replace(old, new), header)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('regression accepted: ' + old)
    assert len(mutations) == 6
    print(f'check_canonical_tile_lights ok: {materials} tile materials, {fixtures} shading fixtures, '
          f'{len(mutations)} rejected mutations; runtime upload savings unverified')


if __name__ == '__main__':
    main()
