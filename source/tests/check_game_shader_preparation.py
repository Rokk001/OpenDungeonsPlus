"""Check that the game does not build shaders or material copies in a frame of play. It does not start a game.

Owner check of build 61 (decisions 1072 and 1079): frames of 368 ms and 780 ms during play. Three causes:

1. Light count of the generated shaders. Leaving the menu switched the shader generator back to following the
   number of lights in view; every time more lights than ever before came into view, Ogre (RTSS
   SGScheme::synchronizeWithLightSettings) invalidated the scheme and rebuilt every generated shader in one frame.
   The count is now fixed at OGRE_MAX_SIMULTANEOUS_LIGHTS: no pass gets more lights (no material sets max_lights or
   iterates per light), so the extra slots of a larger count only ever held black lights and the lighting is the same.
2. Materials first drawn during play (emotes, badges, props, reaction, room and spell particles) loaded their texture
   and compiled their generated shaders in that frame (Ogre.log of build 61: CreatureEmote_Steam, new fragment shader,
   184 ms frame). They are prepared during the map load, after the light count is fixed.
3. The contour copy of a creature material for a seat colour and its brighter copy were made the first time a creature
   of that seat appeared or the hand was over it (18:43:59 Kobold green, 18:45:02 and 18:45:24 Roach red in the owner
   log). The first creature with a material now makes the copies for every seat.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def function_body(source, signature):
    start = source.index(signature)
    end = source.index('\n}\n', start)
    return source[start:end]


render = read('source/render/RenderManager.cpp')
render_h = read('source/render/RenderManager.h')

# Cause 1: the light count stays fixed in the game
pin = function_body(render, 'void RenderManager::pinWorldShaderLights()')
assert 'OGRE_MAX_SIMULTANEOUS_LIGHTS' in pin
assert 'setLightCountAutoUpdate(false)' in pin and 'setLightCount(lightCount)' in pin
# A second call (the menu is freed after the map load) must not rebuild the prepared shaders
assert re.search(r'if\(!renderState->getLightCountAutoUpdate\(\) && renderState->getLightCount\(\) == lightCount\)\s*return;', pin)
assert pin.index('return;\n    renderState->setLightCountAutoUpdate(false)') < pin.index('invalidateScheme')
assert 'getSingletonPtr() != mShaderGenerator' in pin, 'the menu is also freed after the generator is gone'
assert 'pinWorldShaderLights();' in function_body(render, 'void RenderManager::releaseMenuShaderLights()')
sources = list((repo / 'source').rglob('*.cpp')) + list((repo / 'source').rglob('*.h'))
for path in sources:
    text = path.read_text(encoding='utf-8', errors='replace')
    assert 'setLightCountAutoUpdate(true)' not in text, '%s lets the shader light count follow the view again' % path
    # The fixed count equals the lights a pass can get only while nothing raises or splits that limit
    assert 'setMaxSimultaneousLights' not in text and 'setIteratePerLight' not in text, path
for path in list((repo / 'materials').rglob('*.material')) + list((repo / 'particles').rglob('*')):
    if path.is_dir():
        continue
    text = path.read_text(encoding='utf-8', errors='replace')
    assert not re.search(r'^\s*max_lights\b', text, re.M), '%s raises the lights of a pass' % path
    assert not re.search(r'^\s*iteration\b.*\bper_light\b', text, re.M), '%s iterates per light' % path

# Cause 2: the game materials are prepared during the map load, after the count is fixed
init = function_body(render, 'void RenderManager::initGameRenderer(GameMap* gameMap)')
assert init.index('pinWorldShaderLights();') < init.index('prepareGameShaders();')
prepare = function_body(render, 'void RenderManager::prepareGameShaders()')
assert 'getTemplateIterator()' in prepare and 'getMaterialName()' in prepare, 'particle templates must be prepared'
assert 'prepareGeneratedShaders(*material)' in prepare and 'prepareGeneratedShaders(*copy)' in prepare
for setting in ('setLightingEnabled(false)', 'setReceiveShadows(false)', 'setDepthCheckEnabled(false)'):
    assert 'copy->' + setting in prepare, 'an overlay copy must match OverlayElement::setMaterial: ' + setting
generated = function_body(render, 'void RenderManager::prepareGeneratedShaders(Ogre::Material& material)')
assert generated.index('material.load()') < generated.index('createShaderBasedTechnique(material, Ogre::MaterialManager::DEFAULT_SCHEME_NAME, scheme)') \
    < generated.index('validateMaterial(scheme, material)')
material_names = set()
for path in (repo / 'materials').rglob('*.material'):
    material_names.update(re.findall(r'^material\s+(\S+)', path.read_text(encoding='utf-8', errors='replace'), re.M))
for array in ('GAME_OVERLAY_MATERIAL_PREFIXES', 'GAME_EFFECT_MATERIAL_PREFIXES'):
    prefixes = re.findall(r'"([^"]+)"', render.split(array + '[] = {')[1].split('}')[0])
    assert prefixes, array
    for prefix in prefixes:
        assert any(name.startswith(prefix) for name in material_names), 'no material starts with ' + prefix
# The emotes and badges are overlay materials, the others are drawn in the scene
assert set(re.findall(r'"([^"]+)"', render.split('GAME_OVERLAY_MATERIAL_PREFIXES[] = {')[1].split('}')[0])) == \
    {'CreatureEmote_', 'CreatureOverlay'}
assert 'void prepareGameShaders();' in render_h and 'void pinWorldShaderLights();' in render_h

# Cause 3: the contour and brighter copies of every seat are made with the first creature of a material
add = function_body(render, 'void RenderManager::rrAddOutliner(Creature* creature)')
assert 'resourceExists(outlinerMaterialName(materialName, cc), "Graphics")' in add
assert 'prepareOutlinerMaterials(materialName, *creature->getGameMap());' in add
assert add.index('prepareOutlinerMaterials(') < add.index('setMaterial(getOutlinerMaterial(materialName, cc))')
seats = function_body(render, 'void RenderManager::prepareOutlinerMaterials(const std::string& materialName, const GameMap& gameMap)')
assert 'gameMap.getSeats()' in seats and 'seat->getColorValue()' in seats
assert 'outliner->load();' in seats and 'getBrighterMaterial(outliner->getName())->load();' in seats
# The copies keep their names, which rrRemoveOutliner and rrNormalizeAmbient cut at the markers
name = function_body(render, 'static std::string outlinerMaterialName(const std::string& materialName, const Ogre::ColourValue& colour)')
assert 'ss << "##_Outliner";' in name and 'ss << "_" << colour;' in name
assert 'ss << "##_Brighter";' in function_body(render, 'Ogre::MaterialPtr RenderManager::getBrighterMaterial(const std::string& materialName)')
assert 'getBrighterMaterial(materialName)' in function_body(render, 'void RenderManager::rrIncreaseAmbient(Creature* creature)')
print('ok')
