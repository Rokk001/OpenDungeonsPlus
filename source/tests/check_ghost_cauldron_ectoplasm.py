"""Ectoplasm in the ghost cauldron (owner decision 998 point 6, screenshot 15 of build 0.7.4.57).

The liquid in the cauldron mouth was one flat mint-green GhostEctoplasm disc without texture, shine or movement. Now:
- texture: the mouth surface of models/GhostCauldron.mesh and the window fill models/GhostCauldronFill.mesh use
  GhostCauldronEctoplasm with the painted swirl GhostCauldronEctoplasm.png and planar UVs centred on the mouth (the
  mouth spans the inscribed circle of the texture, so turning it round the centre never shows its corners);
- shine and glow: a tight bright specular highlight and an emissive green glow;
- motion: the swirl turns (rotate_anim), two additive layers of GhostCauldronEctoGlint.png (wisps, bubble rings,
  sparkles) drift in other directions and scales, one of them also bobs (wave_xform);
- unchanged: the trap seat glow stays GhostEctoplasm (and every other apparatus keeps GhostEctoplasm), all positions,
  normals, bones and bounds, and the fill level path in BuildingObject.cpp (child node behind the window, height
  scaled by the fill fraction).
Pure file inspection, nothing is compiled or rendered.
"""
from pathlib import Path
import re
import struct

from PIL import Image

repo = Path(__file__).resolve().parents[2]
MATERIAL = 'GhostCauldronEctoplasm'


def read(path):
    return (repo/path).read_text(encoding='utf-8')


# Shared vertex positions, normals and first UV set plus (material, indices) per submesh of a binary OGRE mesh.
def mesh(name):
    data = (repo/'models'/(name+'.mesh')).read_bytes()
    start = data.index(b'\n', 2)+1
    kind, size = struct.unpack_from('<HI', data, start)
    assert kind == 0x3000 and start+size <= len(data), name
    result = {'submeshes': [], 'vertices': None}
    at = start+7
    while at < start+size:
        kind, length = struct.unpack_from('<HI', data, at)
        assert length >= 6 and at+length <= start+size, (name, at)
        if kind == 0x4000:
            end = data.index(b'\n', at+6)
            shared, count, wide = struct.unpack_from('<?IB', data, end+1)
            assert shared, name
            indices = struct.unpack_from(('<%dI' if wide else '<%dH') % count, data, end+7)
            result['submeshes'].append((data[at+6:end].decode(), indices))
        elif kind == 0x5000:
            count = struct.unpack_from('<I', data, at+6)[0]
            elements, buffers, inner = [], {}, at+10
            while inner < at+length:
                child, child_size = struct.unpack_from('<HI', data, inner)
                if child == 0x5100:
                    element = inner+6
                    while element < inner+child_size:
                        _, element_size = struct.unpack_from('<HI', data, element)
                        elements.append(struct.unpack_from('<5H', data, element+6))
                        element += element_size
                elif child == 0x5200:
                    binding, stride = struct.unpack_from('<HH', data, inner+6)
                    buffers[binding] = (stride, inner+16)
                inner += child_size
            def column(semantic, width):
                source, _, _, offset, _ = next(e for e in elements if e[2] == semantic and e[4] == 0)
                stride, first = buffers[source]
                return [struct.unpack_from('<%df' % width, data, first+i*stride+offset) for i in range(count)]
            result['vertices'] = (column(1, 3), column(4, 3), column(7, 2))
        at += length
    return result


# The block of one material in a material script, split into its passes.
def passes(script, name):
    block = re.search(r'^material\s+'+name+r'\s*\n\{(.*?)^\}', script, re.M | re.S)
    assert block, name
    return [part for part in re.split(r'^\s*pass\b', block[1], flags=re.M)[1:]]


def numbers(text, key):
    found = re.search(r'^\s*'+key+r'((?:\s+-?[0-9.]+)+)\s*$', text, re.M)
    assert found, key
    return [float(value) for value in found[1].split()]


def textures():
    credits = read('CREDITS')
    for name, size in (('GhostCauldronEctoplasm.png', 512), ('GhostCauldronEctoGlint.png', 256)):
        path = repo/'materials/textures'/name
        assert path.is_file(), name
        assert any('materials/textures/'+name in row and 'GPLv3+' in row and '998' in row for row in credits.splitlines()), \
            ('CREDITS', name)
        image = Image.open(path).convert('RGB')
        assert image.size == (size, size), (name, image.size)
        pixels = list(image.getdata())
        greens = [g for r, g, b in pixels]
        # texture, not a flat colour: a wide spread of brightness
        assert max(greens)-min(greens) > 150, (name, 'flat')
        if name == 'GhostCauldronEctoplasm.png':
            # green ectoplasm (green leads every channel on average), bright highlights and darker veins/meniscus
            mean = [sum(channel)/len(pixels) for channel in zip(*pixels)]
            assert mean[1] > mean[0]*1.5 and mean[1] > mean[2]*1.5, mean
            assert sum(g > 200 for g in greens) > len(greens)//100, 'no bright swirls or bubbles'
            assert sum(g < 80 for g in greens) > len(greens)//100, 'no dark depths'
        else:
            # mostly black (it is added on top) and seamless (it scrolls): opposite edges match
            assert sum(g < 40 for g in greens) > len(greens)//2, 'glint layer not mostly black'
            left = [image.getpixel((0, y))[1] for y in range(size)]
            right = [image.getpixel((size-1, y))[1] for y in range(size)]
            top = [image.getpixel((x, 0))[1] for x in range(size)]
            bottom = [image.getpixel((x, size-1))[1] for x in range(size)]
            assert sum(abs(a-b) for a, b in zip(left, right))/size < 24, 'glint seam left/right'
            assert sum(abs(a-b) for a, b in zip(top, bottom))/size < 24, 'glint seam top/bottom'
    assert 'materials/textures/GhostCauldronEctoplasm.png' in read('tools/gen_ghost_cauldron_ectoplasm.py')


def material():
    script = read('materials/scripts/Ghost.material')
    base, glint, shimmer = passes(script, MATERIAL)
    # texture and swirl motion on the opaque base
    assert re.search(r'^\s*texture\s+GhostCauldronEctoplasm\.png\s*$', base, re.M), 'swirl texture'
    assert 'scene_blend' not in base and 'depth_write off' not in base, 'base pass is the solid liquid'
    assert 0.005 <= abs(numbers(base, 'rotate_anim')[0]) <= 0.05, 'slow visible swirl'
    # shine: bright, tight specular; glow: emissive green
    specular = numbers(base, 'specular')
    assert min(specular[:3]) >= 0.8 and specular[-1] >= 48, ('wet highlight', specular)
    emissive = numbers(base, 'emissive')
    assert emissive[1] >= 0.6 and emissive[1] > emissive[0] and emissive[1] > emissive[2], ('green glow', emissive)
    # two additive moving glint layers with different speeds and scales
    motions = []
    for layer in (glint, shimmer):
        assert re.search(r'^\s*scene_blend\s+add\s*$', layer, re.M) and 'depth_write off' in layer, 'additive layer'
        assert re.search(r'^\s*texture\s+GhostCauldronEctoGlint\.png\s*$', layer, re.M), 'glint texture'
        assert re.search(r'^\s*tex_address_mode\s+wrap\s*$', layer, re.M), 'glints tile'
        scroll = numbers(layer, 'scroll_anim')
        assert any(abs(value) >= 0.01 for value in scroll), ('glints drift', scroll)
        tint = numbers(layer, 'emissive')
        assert tint[1] > tint[0] and tint[1] > tint[2] and numbers(layer, 'diffuse') == [0, 0, 0], 'green tint only'
        motions.append((tuple(scroll), tuple(numbers(layer, 'scale'))))
    assert motions[0] != motions[1], 'both glint layers move the same way'
    assert re.search(r'^\s*wave_xform\s+scroll_[xy]\s+sine(\s+-?[0-9.]+){4}\s*$', shimmer, re.M), 'bobbing layer'
    # the old flat material is kept untouched for the trap seat glow and the other apparatuses
    old = passes(script, 'GhostEctoplasm')
    assert len(old) == 1 and 'texture' not in old[0] and numbers(old[0], 'diffuse') == [0.25, 0.95, 0.38, 0.90]


def meshes():
    cauldron = mesh('GhostCauldron')
    positions, normals, uvs = cauldron['vertices']
    materials = [name for name, _ in cauldron['submeshes']]
    assert materials == ['GhostIron', 'GhostEctoplasm', MATERIAL, 'GhostBrass', 'GhostCoal', 'GhostEmbers',
                         'GhostWindow'], materials
    submeshes = dict(cauldron['submeshes'])
    mouth, seat = set(submeshes[MATERIAL]), set(submeshes['GhostEctoplasm'])
    assert len(mouth) == 664 and len(submeshes[MATERIAL]) == 380*3, 'measured mouth surface'
    assert len(seat) == 280 and len(submeshes['GhostEctoplasm']) == 108*3, 'measured trap seat glow'
    assert not mouth & seat
    assert all(1.0 < positions[i][2] < 1.06 and (positions[i][0]**2+positions[i][1]**2)**0.5 < 0.57 for i in mouth)
    assert all(abs(positions[i][0]-0.5) < 0.08 and abs(positions[i][1]-0.82) < 0.08 and positions[i][2] > 1.09
               for i in seat), 'seat glow stays on the corner seat'
    assert sum(normals[i][2] > 0.8 for i in mouth) >= 200, 'mouth faces up'
    span = 2*0.565
    for i in mouth:
        u, v = uvs[i]
        assert abs(u-(0.5+positions[i][0]/span)) < 1e-5 and abs(v-(0.5-positions[i][1]/span)) < 1e-5, 'planar mouth UVs'
        assert (u-0.5)**2+(v-0.5)**2 <= 0.5**2+1e-4, 'mouth inside the inscribed circle of the swirl texture'
    fill = mesh('GhostCauldronFill')
    assert [name for name, _ in fill['submeshes']] == [MATERIAL], 'window fill uses the cauldron ectoplasm'
    positions, _, uvs = fill['vertices']
    assert len(positions) == 264
    assert min(p[2] for p in positions) == 0.0 and abs(max(p[2] for p in positions)-0.6) < 1e-6, 'floor origin, 0.6 high'
    for (x, y, z), (u, v) in zip(positions, uvs):
        assert abs(u-(0.5+x/span)) < 1e-5 and abs(v-(0.5-(z-0.3)/span)) < 1e-5, 'planar fill UVs at the mouth scale'
    # credits name the change in the same commit as the meshes
    credits = read('CREDITS')
    for path in ('models/GhostCauldron.mesh', 'models/GhostCauldronFill.mesh'):
        assert any(row.startswith(path+' ') and '998 point 6' in row and MATERIAL in row for row in credits.splitlines()), path


def fill_path():
    building = read('source/entities/BuildingObject.cpp')
    assert 'createEntity(getName()+"_GhostFill","GhostCauldronFill.mesh")' in building, 'fill entity'
    assert 'createChildSceneNode(getName()+"_GhostFillNode",Ogre::Vector3(0.0f,0.74f,0.40f));' in building
    assert 'mGhostFillNode->setScale(1.0f,1.0f,static_cast<float>(std::max(0.0,mGhostFill)));' in building
    assert 'mGhostFillNode->setScale(1.0f,1.0f,static_cast<float>(std::max(0.0,std::min(1.0,mGhostFill))));' in building
    assert 'setMaterial' not in building.split('"GhostCauldronFill.mesh"')[1].split('}')[0], 'mesh material is used'


textures()
material()
meshes()
fill_path()
print('ghost cauldron ectoplasm: ok')
