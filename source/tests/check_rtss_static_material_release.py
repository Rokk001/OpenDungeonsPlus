"""Guard the release of RTSS static skinning shadow materials before Root shutdown, without compiling or launching the game.

Tilda F1 runtime evidence (build 52, 8bb3464ce): --menu-test exits 0xC0000005 in ExitProcess ->
OgreRTShaderSystem.dll exit-time destructors -> Material::~Material -> GpuProgramUsage::~GpuProgramUsage.
RenderManager stores CreatureShadowCaster in HardwareSkinningFactory's static MaterialPtr arrays; they
must be emptied while Root still owns the material and GPU program managers.
"""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
application = (repo / 'source/ODApplication.cpp').read_text(encoding='utf-8')
renderer = (repo / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
SETTERS = ('setCustomShadowCasterMaterials', 'setCustomShadowReceiverMaterials')
TYPES = ('ST_LINEAR', 'ST_DUAL_QUATERNION')


def strip_comments(text):
    return re.sub(r'//[^\n]*|/\*.*?\*/', '', text, flags=re.S)


def start_client(source):
    body = source.split('void ODApplication::startClient()', 1)[1]
    opening = body.index('{')
    depth = 0
    for match in re.finditer(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"|[{}]', body[opening:], re.S):
        if match.group() == '{':
            depth += 1
        elif match.group() == '}':
            depth -= 1
            if depth == 0:
                return body[opening:opening + match.start()]
    raise AssertionError('startClient body not closed')


def check_release(source):
    """Every static caster/receiver slot of both skinning types is reset to an empty pointer in time."""
    assert '#include <RTShaderSystem/OgreShaderExHardwareSkinning.h>' in source
    body = strip_comments(start_client(source))
    root = body.index('Ogre::Root ogreRoot(')
    owners_end = body.index('frameListener.prepareRenderWindowShutdown();')
    destroy = body.index('Ogre::RTShader::ShaderGenerator::destroy();')
    loop = re.search(r'const Ogre::MaterialPtr (\w+);\s*for\s*\(\s*Ogre::RTShader::SkinningType (\w+)\s*:\s*\{([^}]*)\}\s*\)\s*\{(.*?)\n    \}', body, re.S)
    assert loop, 'release loop missing'
    empty, variable, types, calls = loop.groups()
    assert sorted(t.strip().replace('Ogre::RTShader::', '') for t in types.split(',')) == sorted(TYPES)
    for setter in SETTERS:
        call = re.search(r'Ogre::RTShader::HardwareSkinningFactory::' + setter + r'\(\s*(\w+)\s*,([^;]*)\);', calls)
        assert call, setter + ' not reset'
        assert call.group(1) == variable
        assert [a.strip() for a in call.group(2).split(',')] == [empty] * 4, setter + ' must clear all four slots'
    # After the owner scope (no later entity re-registers the caster), before RTSS and Root are destroyed.
    assert root < owners_end < loop.start() < destroy


def check_registration_still_needs_release(source):
    """The release is only meaningful while RenderManager stores a material in the static arrays."""
    assert 'factory->setCustomShadowCasterMaterials(Ogre::RTShader::ST_LINEAR, caster, caster, caster, caster);' in source


check_release(application)
check_registration_still_needs_release(renderer)

# The four arrays released here must be the only static MaterialPtr holders of the pinned RTSS source.
ogre = Path('C:/Users/mario/build-deps/src/ogre/Components/RTShaderSystem/src/OgreShaderExHardwareSkinning.cpp')
if ogre.exists():
    statics = re.findall(r'^static MaterialPtr (\w+)\[', ogre.read_text(encoding='utf-8'), re.M)
    assert sorted(statics) == sorted(['mCustomShadowCasterMaterialsLinear', 'mCustomShadowCasterMaterialsDualQuaternion',
                                      'mCustomShadowReceiverMaterialsLinear', 'mCustomShadowReceiverMaterialsDualQuaternion']), statics

loop_text = application[application.index('    const Ogre::MaterialPtr noMaterial;'):application.index('    Ogre::RTShader::ShaderGenerator::destroy();')]
mutations = [
    application.replace(loop_text, '', 1),
    application.replace(', Ogre::RTShader::ST_DUAL_QUATERNION}', '}', 1),
    application.replace('Ogre::RTShader::HardwareSkinningFactory::setCustomShadowReceiverMaterials(', 'Ogre::RTShader::HardwareSkinningFactory::setCustomShadowCasterMaterials(', 1),
    application.replace('noMaterial, noMaterial, noMaterial, noMaterial);', 'noMaterial, noMaterial, noMaterial, Ogre::MaterialPtr());', 1),
    application.replace('#include <RTShaderSystem/OgreShaderExHardwareSkinning.h>\n', '', 1),
    # moved inside the owner scope, before the frame listener releases its views
    application.replace(loop_text, '', 1).replace('        OD_LOG_INF("Disconnecting client...");\n',
                                                 loop_text + '        OD_LOG_INF("Disconnecting client...");\n', 1),
    # moved after RTSS destruction is still before Root, but RTSS is gone: reject to keep the documented order
    application.replace(loop_text, '', 1).replace('    Ogre::RTShader::ShaderGenerator::destroy();\n', '    Ogre::RTShader::ShaderGenerator::destroy();\n' + loop_text, 1),
]
for mutated in mutations:
    assert mutated != application
    try:
        check_release(mutated)
    except (AssertionError, ValueError):
        continue
    raise AssertionError('unsafe RTSS static material mutation was accepted')
print('ok: RTSS static skinning shadow materials released before ShaderGenerator/Root teardown; %d mutations rejected' % len(mutations))
