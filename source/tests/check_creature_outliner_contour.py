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
# X1 rework (E9): the bias must push the shell away from the camera (negative), a positive bias filled the creature red
assert 'setDepthBias(-4.0f, -32.0f)' in body and 'setDepthBias(1.0f, 1.0f)' not in body
# X1 rework 3 (E9, decision 710): the contour is a constant number of SCREEN pixels, not a world-space offset. A world
# offset (0.012 of the mesh size) was as thick as thin parts (skeleton bones, wing membranes, spider legs) and huge in
# close-ups, which drew the creature filled red.
assert 'setNamedConstant("pixelWidth"' in body and 'OutlinerContourPixels' in body
assert 'ACT_VIEWPORT_SIZE' in body and 'ACT_VIEW_MATRIX' in body and 'ACT_VIEWPROJ_MATRIX' in body
assert 'OutlinerContourWidthFactor' not in render and 'getBounds().getSize()' not in body
px = float(render.split('OutlinerContourPixels = ')[1].split('f;')[0])
assert 0.5 <= px <= 2.5, px
assert 'uniform    float pixelWidth;' in vert and 'uniform    vec4 viewportSize;' in vert
assert 'clip.xy += dir * pixelWidth * 2.0 * viewportSize.zw * clip.w' in vert
assert 'normalize(normal.xyz) * width' not in vert and 'position.xyz +' not in vert and 'blendIndices' in vert
# Every sub-entity of every creature gets the pass (no creature type is skipped) and it is added to a clone only.
assert 'getNumSubEntities()' in body and '->clone(ss.str(),"Graphics")' in body
print('ok')
