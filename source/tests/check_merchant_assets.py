"""Merchant room assets after owner check 664 finding 6 (build 0.7.3.37): the merchant was a brown shapeless figure inside
an untextured bright orange table next to an untextured orange shelf. Owner check 710 finding 3 (build 0.7.3.41): still a
brown figure at a table with a beige dripping cloth instead of the hunched figure in a ragged layered cloak holding the
scales of D-6-v2 variant 1; in the room light the textures came out near black (a vertical face shows at about 0.7 x its
texture value: robe 49 -> 30-38 in the screenshot). Owner check 836 (build 48): robe and hood came out light beige/pink
(rework 2 had lifted them for that 0.7 x light, but at the front table corner the figure gets about 1.0 x: hood texture
135/109/84 -> 133/106/82 in the screenshot), the hood was a smooth pale sack, the face was not readable from the game
camera, and the belt with pouch and the scales hanging at the belt were missing (he held the scales).

One check per fault
  furniture textures   SalesTable and MerchantShelf use only materials with a texture (the flat ItemWood, ItemWoodLight,
                       MerchantClothTrim and the herb and bag colours turned bright orange under the warm room light);
                       the only flat material left is the dark iron of nails and lantern (diffuse below 0.25)
  table look           the table uses its plank atlas MerchantTableWood and the stained cloth MerchantTableCloth
  figure textures      the merchant's robe, hood, skin, leather and brass are textured; only small face parts
                       (MerchantDark, MerchantEye, MerchantGold, MerchantHair) are flat
  layered cloak        robe, over-cloak (MerchantCloak) and hood cape (MerchantHood) use three different textures
  scales readable      scales, buckle and ring use the self-lit MerchantBrass (not the flat ItemBrass)
  scales at the belt   the Scales bone hangs from the pelvis (the belt), not from a hand (decision 836; rework 2 had
                       them in the hands), and its bind position is at belt height on his left hip in front of the body
  belt and pouch       the mesh has the leather belt and pouch and the brass buckle at belt height (MerchantLeather and
                       MerchantBrass vertices 0.5 to 0.72 above the feet)
  readable face        the face (MerchantHide vertices above the shoulders) reaches forward of the hood, the nose
                       reaches at least 0.12 in front of the head joint, and the gold tooth is at least 15 mm wide
  beside the table     the game puts the merchant on the centre of a sales table: below the table top no vertex of the
                       figure (bind pose) lies inside the table footprint (RoomObjectBounds.h), and the figure stands
                       at the front corner (towards the room camera, -Y) beside the table, so the whole figure is seen
  bright enough        the furniture, leather and skin textures have a minimum mean luminance for the room light
                       (build 41 leather 39, table wood 26 failed), the table cloth is no light beige cloth
  dark brown cloth     robe, over-cloak and hood stay in a dark brown luminance range (build 41 robe 49 near black,
                       build 48 robe 96, cloak 80, hood 114 beige/pink failed) with a brown hue (red clearly above
                       green, blue clearly below green: the build 48 cloak had blue at 0.94 x green and read pink) and
                       enough fold and wear contrast (standard deviation) not to read as a smooth sack
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
MIN_LUMINANCE = {'MerchantLeather': 60,    # (39)
                 'MerchantHide': 110,      # (97)
                 'MerchantTableWood': 50,  # (26)
                 'MerchantWares': 60}      # (50)
# The table cloth stays a dark stained linen, not the light beige cloth of build 41 (73)
MAX_CLOTH_LUMINANCE = 70
# Dark brown cloth (decision 836): mean luminance range, hue and contrast; build 41 / build 48 values in brackets
CLOTH_LUMINANCE = {'MerchantRobe': (52, 72),    # (49 near black / 96 beige)
                   'MerchantCloak': (48, 68),   # (- / 80 pink)
                   'MerchantHood': (54, 76)}    # (52 / 114 beige)
CLOTH_MIN_RED_OVER_GREEN = 1.2
CLOTH_MAX_BLUE_OVER_GREEN = 0.8
CLOTH_MIN_STD = 10.0
# Belt height above the feet for belt, buckle, pouch and the scales hook
BELT_LOW, BELT_HIGH = 0.5, 0.72
SCALES_PARENTS = ('Pelvis',)
# Least vertices at belt height: double belt, pouch and scales strap in leather (build 48: 1247, one belt and a small
# pouch), buckle in brass
BELT_MATERIALS = {'MerchantLeather': 2000, 'MerchantBrass': 30}
# Readable face (decision 836), metres; build 48 values in brackets
FACE_LOW = 1.0                # face, hood and gold tooth parts lie above this height
FACE_OUT_OF_HOOD = 0.04       # the face reaches at least this far forward of the hood opening (0.057)
NOSE_MIN = 0.2                # nose tip in front of the head joint (0.185)
GOLD_TOOTH_MIN = 0.024        # gold tooth width (0.020)
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


# Returns (mean luminance, mean red, mean green, mean blue, luminance standard deviation), 0..255, of an 8-bit grey,
# RGB or RGBA PNG without interlacing.
def png_stats(path):
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
    total2 = 0.0
    rgb = [0.0, 0.0, 0.0]
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
            if channels < 3:
                lum = px[0]
                for c in range(3):
                    rgb[c] += px[0]
            else:
                lum = 0.299 * px[0] + 0.587 * px[1] + 0.114 * px[2]
                for c in range(3):
                    rgb[c] += px[c]
            total += lum
            total2 += lum * lum
        prev = line
    n = width * height
    mean = total / n
    return (mean, rgb[0] / n, rgb[1] / n, rgb[2] / n, max(0.0, total2 / n - mean * mean) ** 0.5)


def png_mean_luminance(path):
    return png_stats(path)[0]


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


def geometry_positions(geometry):
    out = []
    for vb in geometry.iter('vertexbuffer'):
        for v in vb.iter('vertex'):
            p = v.find('position')
            if p is not None:
                out.append((float(p.get('x')), float(p.get('y')), float(p.get('z'))))
    return out


# Positions of the vertices the faces of the submeshes with this material use (shared or own geometry)
def submesh_positions(tree, material):
    shared = None
    out = []
    for sm in tree.iter('submesh'):
        if sm.get('material') != material:
            continue
        if sm.get('usesharedvertices') == 'true':
            if shared is None:
                shared = geometry_positions(tree.find('sharedgeometry'))
            pts = shared
        else:
            pts = geometry_positions(sm.find('geometry'))
        used = set()
        for f in sm.iter('face'):
            used.update(int(f.get(k)) for k in ('v1', 'v2', 'v3'))
        out.extend(pts[i] for i in sorted(used))
    return out


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
skeleton_tree = skeleton_xml('Merchant')
parents = {}
for bp in skeleton_tree.iter('boneparent'):
    parents[bp.get('bone')] = bp.get('parent')
assert parents.get('Scales') in SCALES_PARENTS, \
    'the scales must hang at the belt: Scales hangs from %s, not from the pelvis' % parents.get('Scales')


# Bind position of a bone in model space (positions are relative to the parent; every merchant bone has the identity
# as rest rotation, which is asserted)
def bind_position(name):
    bones = {b.get('name'): b for b in skeleton_tree.iter('bone')}
    out = [0.0, 0.0, 0.0]
    while name:
        b = bones[name]
        p = b.find('position')
        r = b.find('rotation')
        assert r is None or abs(float(r.get('angle'))) < 1e-4, 'bone %s has a rest rotation' % name
        out = [out[0] + float(p.get('x')), out[1] + float(p.get('y')), out[2] + float(p.get('z'))]
        name = parents.get(name)
    return out


scales_at = bind_position('Scales')
pelvis_at = bind_position('Pelvis')
assert BELT_LOW <= scales_at[2] <= BELT_HIGH, 'the scales hook is not at belt height (%.2f)' % scales_at[2]
assert scales_at[0] > pelvis_at[0] + 0.05, 'the scales must hang on his left hip (+x of the pelvis), x %.2f' % scales_at[0]
assert scales_at[1] < pelvis_at[1] - 0.15, 'the scales must hang in front of the body, y %.2f' % scales_at[1]
assert bind_position('Hand_R')[2] - scales_at[2] > 0.2, 'the scales hang at the hands, not at the belt'

# Belt with buckle and pouch at belt height
for mat, least in BELT_MATERIALS.items():
    at_belt = [p for p in submesh_positions(trees['Merchant'], mat) if BELT_LOW <= p[2] <= BELT_HIGH]
    assert len(at_belt) >= least, 'Merchant.mesh has too little %s at belt height (belt, pouch, buckle): %d vertices' % (
        mat, len(at_belt))

# Readable face from the game camera: out of the hood, long nose, large gold tooth (front is -Y)
face = [p for p in submesh_positions(trees['Merchant'], 'MerchantHide') if p[2] > FACE_LOW]
assert face, 'Merchant.mesh has no face'
hood_front = min(p[1] for p in submesh_positions(trees['Merchant'], 'MerchantHood') if p[2] > FACE_LOW)
face_front = min(p[1] for p in face)
assert face_front < hood_front - FACE_OUT_OF_HOOD, \
    'the face sits deep in the hood (face front %.3f, hood front %.3f)' % (face_front, hood_front)
nose = bind_position('Head')[1] - face_front
assert nose >= NOSE_MIN, 'the nose is too short to read from the game camera (%.3f in front of the head joint)' % nose
gold = [p for p in submesh_positions(trees['Merchant'], 'MerchantGold') if p[2] > FACE_LOW]
assert gold, 'Merchant.mesh has no gold tooth'
width = max(p[0] for p in gold) - min(p[0] for p in gold)
assert width >= GOLD_TOOTH_MIN, 'the gold tooth is too small to read from the game camera (%.3f wide)' % width

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

# 10. Bright enough for the room light, no light beige cloth; robe, over-cloak and hood dark brown (decision 836)
for mat, (low_value, high_value) in CLOTH_LUMINANCE.items():
    path = 'materials/textures/' + mat + '.png'
    assert material_texture(mat) == mat + '.png' and texture_exists(mat + '.png'), mat + ' must use its own texture'
    value, red, green, blue, std = png_stats(path)
    assert value >= low_value, '%s.png is near black in the room light (mean %.0f, needs %d)' % (mat, value, low_value)
    assert value <= high_value, '%s.png reads beige in the room light (mean %.0f, at most %d)' % (mat, value, high_value)
    assert red >= CLOTH_MIN_RED_OVER_GREEN * green, '%s.png is not brown (red %.0f, green %.0f)' % (mat, red, green)
    assert blue <= CLOTH_MAX_BLUE_OVER_GREEN * green, '%s.png reads pink or grey (blue %.0f, green %.0f)' % (mat, blue, green)
    assert std >= CLOTH_MIN_STD, '%s.png is a smooth cloth without folds and wear (contrast %.1f)' % (mat, std)
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
