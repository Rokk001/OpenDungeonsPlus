"""Exercise the source preflight guard with generated and authored material fixtures, without compiling."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
source = (repo / 'source/render/RenderManager.cpp').read_text(encoding='utf-8')
start = source.index('bool RenderManager::useShaderSkinning(Ogre::Entity* entity)')
body = source[start:source.index('Adds a menu point light with its own scene node', start)]


def check(text):
    """Evaluate the actual generated-technique guard and retain the all-or-nothing source-program gate."""
    match = re.search(r'if\((technique->getSchemeName\(\).*?)\)\s*continue;', text, re.S)
    assert match, 'the generated technique must be skipped before inspecting its programs'
    condition = match.group(1)
    replacements = {
        'technique->getSchemeName()': 'scheme',
        'Ogre::RTShader::ShaderGenerator::DEFAULT_SCHEME_NAME': "'rtss'",
        'technique->getNumPasses()': 'passes',
        'technique->getPass(0)->getUserObjectBindings().getUserAny(\n'
        '                    Ogre::RTShader::TargetRenderState::UserKey).has_value()': 'generated',
        '&&': ' and ',
    }
    for before, after in replacements.items():
        condition = condition.replace(before, after)
    condition = ' '.join(condition.split())
    # Same scheme name is insufficient: a manually authored program must remain untouched.
    fixtures = [
        ('rtss', 1, True, True),
        ('rtss', 2, True, True),
        ('rtss', 1, False, False),
        ('default', 1, False, False),
        ('custom', 1, False, False),
        ('custom', 1, True, False),
        ('rtss', 0, True, False),
    ]
    for scheme, passes, generated, expected in fixtures:
        assert eval(condition, {'__builtins__': {}}, dict(scheme=scheme, passes=passes,
                    generated=generated)) == expected, (scheme, passes, generated)
    program_gate = re.search(r'if\(pass->hasVertexProgram\(\).*?return false;', text, re.S)
    assert program_gate and match.end() < program_gate.start()
    for program in ('hasGeometryProgram()', 'hasTessellationHullProgram()', 'hasTessellationDomainProgram()'):
        assert program in program_gate.group()
    assert text.index('for(const Ogre::SubEntity* subEntity : entity->getSubEntities())') < program_gate.start()
    assert program_gate.end() < text.index('Ogre::RTShader::HardwareSkinningFactory* factory')
    assert program_gate.end() < text.index('material->clone(copyName)')
    assert text.index('material->clone(copyName)') < text.index('setMaterial(skinned[index])')
    assert '"ItemBagSealed"' in text and '"ChickenStraw"' in text


check(body)
mutations = [
    body.replace('technique->getSchemeName() ==', 'technique->getSchemeName() !=', 1),
    body.replace('technique->getNumPasses() > 0', 'technique->getNumPasses() == 0', 1),
    body.replace(').has_value()', ').has_value() == false', 1),
    body.replace('                continue;', '                return false;', 1),
    body.replace('if(pass->hasVertexProgram()', 'if(false', 1),
]
for index, mutation in enumerate(mutations):
    try:
        check(mutation)
    except (AssertionError, SyntaxError, NameError):
        continue
    raise AssertionError('surviving mutation %d' % index)
print('ok: 7 technique fixtures, authored-program/all-subentity gate, 5 mutations')
