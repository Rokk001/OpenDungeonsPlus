"""Wiring check: the creature highlight is a thin contour only and the creature keeps its normal colours."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


render = read('source/render/RenderManager.cpp')
vert = read('shaders/Enlarge.vert')

body = render.split('void RenderManager::rrAddOutliner')[1].split('void RenderManager::rrRemoveOutliner')[0]
# The extra pass draws only the back faces of a shell behind the model, so the model hides all of it but the rim.
assert 'setCullingMode(Ogre::CULL_ANTICLOCKWISE)' in body
assert 'setDepthBias(-4, -32)' not in body and 'setDepthBias(1.0f, 1.0f)' in body
# The shell is pushed out along the normals by a small width, no longer scaled up as a whole.
assert 'setNamedConstant("width"' in body and 'OutlinerContourWidthFactor' in body
width = float(render.split('OutlinerContourWidthFactor = ')[1].split('f;')[0])
assert 0.0 < width <= 0.02, width
assert 'uniform    float width;' in vert and 'normalize(normal.xyz) * width' in vert and '*1.1' not in vert
# Every sub-entity of every creature gets the pass (no creature type is skipped) and it is added to a clone only.
assert 'getNumSubEntities()' in body and '->clone(ss.str(),"Graphics")' in body
print('ok')
