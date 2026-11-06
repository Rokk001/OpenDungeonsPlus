"""Merchant room assets after owner check 664 finding 6 (build 0.7.3.37): the merchant was a brown shapeless figure inside
an untextured bright orange table next to an untextured orange shelf.

One check per fault
  furniture textures   SalesTable and MerchantShelf use only materials with a texture (the flat ItemWood, ItemWoodLight,
                       MerchantClothTrim and the herb and bag colours turned bright orange under the warm room light);
                       the only flat material left is the dark iron of nails and lantern (diffuse below 0.25)
  table look           the table uses its plank atlas MerchantTableWood and the stained cloth MerchantTableCloth
  figure textures      the merchant's robe, hood, skin, leather and brass are textured; only small face parts
                       (MerchantDark, MerchantEye, MerchantGold, MerchantHair) are flat
  hood separate        hood and mantle use MerchantHood, not the robe material, so hood and hump separate from the robe
  scales readable      scales, buckle and ring use the self-lit MerchantBrass (not the flat ItemBrass)
  not in the table     the game puts the merchant on the centre of a sales table: below the table top every vertex of
                       the figure (bind pose) lies behind the table's back edge (RoomObjectBounds.h, SalesTable maxY)
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
FIGURE_TEXTURED = ('MerchantRobe', 'MerchantHood', 'MerchantHide', 'MerchantLeather', 'MerchantBrass')
FIGURE_FLAT_OK = ('MerchantDark', 'MerchantEye', 'MerchantGold', 'MerchantHair')
MERCHANT_CLIPS = ('Idle', 'Walk', 'CountGold', 'RubHands')
NEW_TEXTURES = ('MerchantRobe', 'MerchantHood', 'MerchantBrass', 'MerchantTableWood', 'MerchantTableCloth', 'MerchantWares')
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


converter = os.environ.get('OGRE_XML_CONVERTER', 'OgreXMLConverter')
work = Path(tempfile.mkdtemp(prefix='merchant_assets_'))


def mesh_xml(name):
    target = work / (name + '.mesh.xml')
    subprocess.run([converter, '-q', '-log', str(target) + '.log', str(root / 'models' / (name + '.mesh')), str(target)],
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
assert material_texture('MerchantHood') != material_texture('MerchantRobe'), 'hood and robe need different textures'

# 6. Not inside the table
table_max_y = object_bounds('SalesTable')[3]
low = [p for p in positions(trees['Merchant']) if p[2] < TABLE_TOP]
assert low, 'Merchant.mesh has no vertices'
front = min(p[1] for p in low)
assert front >= table_max_y, 'the merchant stands inside the sales table (front %.3f < %.3f)' % (front, table_max_y)

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

# 9. Furniture bounds equal RoomObjectBounds.h
for name in FURNITURE:
    pts = positions(trees[name])
    got = (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts))
    want = object_bounds(name)
    assert all(abs(a - b) < BOUNDS_TOLERANCE for a, b in zip(got, want)), name + ' bounds %s differ from %s' % (got, want)

print('merchant assets ok')
