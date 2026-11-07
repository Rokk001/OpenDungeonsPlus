"""Merchant room assets after owner check 664 finding 6 (build 0.7.3.37): the merchant was a brown shapeless figure inside
an untextured bright orange table next to an untextured orange shelf. Owner check 710 finding 3 (build 0.7.3.41): still a
brown figure at a table with a beige dripping cloth instead of the hunched figure in a ragged layered cloak holding the
scales of D-6-v2 variant 1; in the room light the textures came out near black (a vertical face shows at about 0.7 x its
texture value: robe 49 -> 30-38 in the screenshot).

One check per fault
  furniture textures   SalesTable and MerchantShelf use only materials with a texture (the flat ItemWood, ItemWoodLight,
                       MerchantClothTrim and the herb and bag colours turned bright orange under the warm room light);
                       the only flat material left is the dark iron of nails and lantern (diffuse below 0.25)
  table look           the table uses its plank atlas MerchantTableWood and the stained cloth MerchantTableCloth
  figure textures      the merchant's robe, hood, skin, leather and brass are textured; only small face parts
                       (MerchantDark, MerchantEye, MerchantGold, MerchantHair) are flat
  layered cloak        robe, over-cloak (MerchantCloak) and hood cape (MerchantHood) use three different textures
  scales readable      scales, buckle and ring use the self-lit MerchantBrass (not the flat ItemBrass)
  scales held          the Scales bone hangs from a hand bone (he holds the scales), not from the pelvis or belt
  beside the table     the game puts the merchant on the centre of a sales table: below the table top no vertex of the
                       figure (bind pose) lies inside the table footprint (RoomObjectBounds.h), and the figure stands
                       at the front corner (towards the room camera, -Y) beside the table, so the whole figure is seen
  bright enough        the figure and furniture textures have a minimum mean luminance for the room light (build 41
                       robe 49, hood 52, leather 39, table wood 26 failed), the table cloth is no light beige cloth
  clips and skeleton   Merchant.mesh links Merchant.skeleton with Idle, Walk, CountGold and RubHands
  textures and credits every new texture is a 256 x 256 PNG with a CREDITS row
  bounds               SalesTable and MerchantShelf vertex bounds equal their rows in RoomObjectBounds.h

Calls (from the repository root; mesh vertex checks need OgreXMLConverter, set OGRE_XML_CONVERTER to its full path):
  python source/tests/check_merchant_assets.py          file checks, no compiler, no game
"""
from pathlib import Path
import fnmatch
import os
import re
import struct
import subprocess
import sys
import tempfile
import zlib
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]

FURNITURE = ('SalesTable', 'MerchantShelf')
# Flat materials the furniture may still use: small dark iron parts only
FLAT_FURNITURE_OK = ('ItemIron',)
FLAT_DARK_LIMIT = 0.25
# Flat colours that turned orange in build 0.7.3.37
BANNED_FURNITURE = ('ItemWood', 'ItemWoodLight', 'MerchantClothTrim', 'MerchantCloth', 'Bloodroot', 'Moonlily', 'Sunthorn',
                    'ItemBag', 'ItemRope', 'ItemBrass')
TABLE_NEEDS = ('MerchantTableWood', 'MerchantTableCloth')
FIGURE_TEXTURED = ('MerchantRobe', 'MerchantCloak', 'MerchantHood', 'MerchantHide', 'MerchantLeather', 'MerchantBrass')
FIGURE_FLAT_OK = ('MerchantDark', 'MerchantEye', 'MerchantGold', 'MerchantHair')
MERCHANT_CLIPS = ('Idle', 'Walk', 'CountGold', 'RubHands')
NEW_TEXTURES = ('MerchantRobe', 'MerchantCloak', 'MerchantHood', 'MerchantBrass', 'MerchantTableWood', 'MerchantTableCloth',
                'MerchantWares')
# Minimum mean luminance (0..255) per texture for the room light (decision 710); build 41 values in brackets
MIN_LUMINANCE = {'MerchantRobe': 75,       # (49)
                 'MerchantCloak': 65,      # (new)
                 'MerchantHood': 85,       # (52)
                 'MerchantLeather': 60,    # (39)
                 'MerchantHide': 110,      # (97)
                 'MerchantTableWood': 50,  # (26)
                 'MerchantWares': 60}      # (50)
# The table cloth stays a dark stained linen, not the light beige cloth of build 41 (73)
MAX_CLOTH_LUMINANCE = 70
HAND_BONES = ('Hand_R', 'Hand_L')
TEXTURE_SIZE = 256
# Height of the sales table top (cloth) the figure must stay behind
TABLE_TOP = 0.71
BOUNDS_TOLERANCE = 1e-3


def read(path):
    return (root / path).read_text(encoding='utf-8', errors='replace')


def png_size(path):
    data = (root / path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path + ' is not a PNG'
    return struct.unpack('>II', data[16:24])


materials_text = ''.join(p.read_text(encoding='utf-8', errors='replace') for p in (root / 'materials' / 'scripts').glob('*.material'))


def material_block(name):
    m = re.search(r'^material ' + re.escape(name) + r'\b.*?^}', materials_text, re.M | re.S)
    assert m, 'material ' + name + ' missing'
    return m.group(0)


def material_texture(name):
    m = re.search(r'^\s*texture\s+(\S+\.png)', material_block(name), re.M)
    return m.group(1) if m else None


def material_diffuse(name):
    m = re.search(r'^\s*diffuse\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)', material_block(name), re.M)
    return tuple(float(x) for x in m.groups()) if m else None


def texture_exists(tex):
    return any((root / 'materials' / 'textures').rglob(tex))


# Returns the mean luminance (0..255) of an 8-bit grey, RGB or RGBA PNG without interlacing.
def png_mean_luminance(path):
    data = (root / path).read_bytes()
    assert data[:8] == b'\x89PNG\r\n\x1a\n', path + ' is not a PNG'
    at, idat, head = 8, b'', None
    while at < len(data):
        size, kind = struct.unpack('>I4s', data[at:at + 8])
        body = data[at + 8:at + 8 + size]
        if kind == b'IHDR':
            head = struct.unpack('>IIBBBBB', body)
        elif kind == b'IDAT':
            idat += body
        at += 12 + size
    width, height, depth, colour, _, _, interlace = head
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    assert depth == 8 and interlace == 0, path + ' must be an 8-bit PNG without interlacing'
    raw = zlib.decompress(idat)
    stride = width * channels
    prev = bytearray(stride)
    total = 0.0
    for y in range(height):
        kind = raw[y * (stride + 1)]
        line = bytearray(raw[y * (stride + 1) + 1:(y + 1) * (stride + 1)])
        for i in range(stride):
            a = line[i - channels] if i >= channels else 0
            b = prev[i]
            c = prev[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + a) & 255
            elif kind == 2:
                line[i] = (line[i] + b) & 255
            elif kind == 3:
                line[i] = (line[i] + (a + b) // 2) & 255
            elif kind == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        for x in range(width):
            px = line[x * channels:x * channels + channels]
            total += px[0] if channels < 3 else 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]
        prev = line
    return total / (width * height)


converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')
work = Path(tempfile.mkdtemp(prefix='merchant_assets_'))


def mesh_xml(name):
    target = work / (name + '.mesh.xml')
    subprocess.run([converter, '-q', '-log', str(target) + '.log', str(root / 'models' / (name + '.mesh')), str(target)],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=120, check=True)
    return ET.parse(target).getroot()


def skeleton_xml(name):
    target = work / (name + '.skeleton.xml')
    subprocess.run([converter, '-q', '-log', str(target) + '.log', str(root / 'models' / (name + '.skeleton')), str(target)],
                   stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=120, check=True)
    return ET.parse(target).getroot()


def submesh_materials(tree):
    return [s.get('material') for s in tree.iter('submesh')]


def positions(tree):
    out = []
    for vb in tree.iter('vertexbuffer'):
        for v in vb.iter('vertex'):
            p = v.find('position')
            if p is not None:
                out.append((float(p.get('x')), float(p.get('y')), float(p.get('z'))))
    return out


def object_bounds(name):
    text = read('source/gamemap/RoomObjectBounds.h')
    m = re.search(r'\{"' + name + r'",\s*([-.\d]+)f,\s*([-.\d]+)f,\s*([-.\d]+)f,\s*([-.\d]+)f\}', text)
    assert m, name + ' row missing in RoomObjectBounds.h'
    return tuple(float(x) for x in m.groups())


trees = {name: mesh_xml(name) for name in FURNITURE + ('Merchant',)}

# 1. Furniture: only textured materials, no orange flat colours
for name in FURNITURE:
    used = submesh_materials(trees[name])
    for mat in used:
        assert mat not in BANNED_FURNITURE, name + ' still uses the flat material ' + mat
        tex = material_texture(mat)
        if tex is None:
            assert mat in FLAT_FURNITURE_OK, name + ' uses the untextured material ' + mat
            assert max(material_diffuse(mat)) < FLAT_DARK_LIMIT, mat + ' must stay dark'
        else:
            assert texture_exists(tex), mat + ' names the missing texture ' + tex
    for geometry in list(trees[name].iter('sharedgeometry')) + list(trees[name].iter('geometry')):
        assert any(int(vb.get('texture_coords', '0')) > 0 for vb in geometry.iter('vertexbuffer')), name + ' needs texture coordinates'
# 2. Table look
table_used = submesh_materials(trees['SalesTable'])
for mat in TABLE_NEEDS:
    assert mat in table_used, 'SalesTable needs ' + mat

# 3. Figure textures, 4. hood separate, 5. scales readable
figure_used = submesh_materials(trees['Merchant'])
for mat in FIGURE_TEXTURED:
    assert mat in figure_used, 'Merchant.mesh needs ' + mat
    tex = material_texture(mat)
    assert tex and texture_exists(tex), mat + ' needs a texture'
for mat in figure_used:
    assert material_texture(mat) or mat in FIGURE_FLAT_OK, 'Merchant.mesh uses the untextured material ' + mat
assert 'ItemBrass' not in figure_used, 'the scales must use MerchantBrass, not the flat ItemBrass'
assert re.search(r'^\s*emissive\s+0*\.0*[1-9]', material_block('MerchantBrass'), re.M), 'MerchantBrass needs its self-light'
layers = [material_texture(m) for m in ('MerchantRobe', 'MerchantCloak', 'MerchantHood')]
assert len(set(layers)) == 3, 'robe, over-cloak and hood need three different textures (layered cloak)'
parents = {}
for bp in skeleton_xml('Merchant').iter('boneparent'):
    parents[bp.get('bone')] = bp.get('parent')
assert parents.get('Scales') in HAND_BONES, 'the merchant must hold the scales: Scales hangs from %s' % parents.get('Scales')

# 6. Beside the table, not in it and not hidden behind it
t_min_x, t_min_y, t_max_x, t_max_y = object_bounds('SalesTable')
low = [p for p in positions(trees['Merchant']) if p[2] < TABLE_TOP]
assert low, 'Merchant.mesh has no vertices'
inside = [p for p in low if t_min_x < p[0] < t_max_x and t_min_y < p[1] < t_max_y]
assert not inside, 'the merchant stands inside the sales table (%d vertices below the top)' % len(inside)
cx = sum(p[0] for p in low) / len(low)
cy = sum(p[1] for p in low) / len(low)
assert cx > t_max_x and cy < t_min_y,     'the merchant must stand at the front corner beside the table, in view of the room camera (centre %.2f %.2f)' % (cx, cy)

# 7. Skeleton and clips
assert b'Merchant.skeleton' in (root / 'models' / 'Merchant.mesh').read_bytes(), 'Merchant.mesh must link Merchant.skeleton'
skeleton = (root / 'models' / 'Merchant.skeleton').read_bytes()
for clip in MERCHANT_CLIPS:
    assert (clip + '\n').encode('ascii') in skeleton, 'Merchant.skeleton has no clip ' + clip

# 8. Textures and credits
credits = read('CREDITS')
patterns = []
for line in credits.splitlines():
    first = re.split(r'\s{2,}|\t', line.strip())[0]
    if first:
        patterns.append(first)
for tex in NEW_TEXTURES:
    path = 'materials/textures/' + tex + '.png'
    assert png_size(path) == (TEXTURE_SIZE, TEXTURE_SIZE), path + ' size'
    assert any(fnmatch.fnmatchcase(path, p) for p in patterns), 'CREDITS has no row for ' + path
for path in ('models/Merchant.mesh', 'models/Merchant.skeleton', 'models/SalesTable.mesh', 'models/MerchantShelf.mesh'):
    assert any(fnmatch.fnmatchcase(path, p) for p in patterns), 'CREDITS has no row for ' + path

# 10. Bright enough for the room light, no light beige cloth
for tex, low_value in MIN_LUMINANCE.items():
    value = png_mean_luminance('materials/textures/' + tex + '.png')
    assert value >= low_value, '%s.png is too dark for the room light (mean %.0f, needs %d)' % (tex, value, low_value)
value = png_mean_luminance('materials/textures/MerchantTableCloth.png')
assert value <= MAX_CLOTH_LUMINANCE, 'MerchantTableCloth.png is a light beige cloth (mean %.0f, at most %d)' % (value, MAX_CLOTH_LUMINANCE)

# 9. Furniture bounds equal RoomObjectBounds.h
for name in FURNITURE:
    pts = positions(trees[name])
    got = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    want = object_bounds(name)
    assert all(abs(a - b) < BOUNDS_TOLERANCE for a, b in zip(got, want)), name + ' bounds %s differ from %s' % (got, want)

print('merchant assets ok')
