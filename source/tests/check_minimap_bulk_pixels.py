"""Check that the drawn minimap's bulk pixel upload writes exactly the bytes of the former per-pixel loop.

Tilda F1 runtime evidence (build 52, P1 Brackenford save, steady minutes): MiniMapDrawn::update was 10.99%
of main-loop samples, 4.45% of them in PixelBox::setColourAt/PixelUtil::packColour. The per-pixel float
round trip is replaced by one PixelUtil::bulkPixelConversion from PF_BYTE_RGBA. This check emulates both
paths with Ogre's own arithmetic (float32 floatToFixed / fixedToFloat, the A8B8G8R8->R8G8B8A8 converter)
for every byte value and proves equal output bytes, then guards the source contract. No compile, no game.
"""
from pathlib import Path
import random
import re
import struct

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'source/gamemap/MiniMapDrawn.cpp'
HEADER = ROOT / 'source/gamemap/MiniMapDrawn.h'


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def float_to_fixed(value, bits):
    """Ogre Bitwise::floatToFixed with float32 arithmetic."""
    value = f32(value)
    if value <= 0.0:
        return 0
    if value >= 1.0:
        return (1 << bits) - 1
    return int(f32(value * float(1 << bits)))


def fixed_to_float(value, bits):
    """Ogre Bitwise::fixedToFloat."""
    return f32(float(value) / float((1 << bits) - 1))


def old_bytes(r, g, b, a):
    """Former loop: setColourAt(ColourValue(c / 255.0)) -> packColour into native-endian PF_R8G8B8A8."""
    value = (float_to_fixed(r / 255.0, 8) << 24) | (float_to_fixed(g / 255.0, 8) << 16) | \
        (float_to_fixed(b / 255.0, 8) << 8) | float_to_fixed(a / 255.0, 8)
    return struct.pack('<I', value)


def new_bytes(r, g, b, a):
    """Bulk path: PF_BYTE_RGBA (= PF_A8B8G8R8 on little endian) through Ogre's A8B8G8R8toR8G8B8A8."""
    inp = struct.unpack('<I', bytes([r, g, b, a]))[0]
    out = ((inp & 0x000000FF) << 24) | ((inp & 0x0000FF00) << 8) | ((inp & 0x00FF0000) >> 8) | ((inp & 0xFF000000) >> 24)
    return struct.pack('<I', out)


def generic_bytes(c):
    """Generic fallback for other locked formats: unpack to float, pack again."""
    return float_to_fixed(fixed_to_float(c, 8), 8)


# Every byte value in every channel, plus random combinations.
checked = 0
for c in range(256):
    for channels in ((c, 0, 0, 255), (0, c, 0, 255), (0, 0, c, 255), (12, 34, 56, c)):
        assert old_bytes(*channels) == new_bytes(*channels), channels
        checked += 1
    assert generic_bytes(c) == c and float_to_fixed(c / 255.0, 8) == c, c
rng = random.Random(4096)
for _ in range(20000):
    px = tuple(rng.randrange(256) for _ in range(4))
    assert old_bytes(*px) == new_bytes(*px), px
    checked += 1
# The old path would differ for a wrong source format: BGRA order must not pass.
assert any(old_bytes(r, 0, b, 255) != new_bytes(b, 0, r, 255) for r, b in ((10, 200), (255, 0)))

# Ogre facts the emulation relies on (pinned source / installed headers).
ogre_src = Path('C:/Users/mario/build-deps/src/ogre/OgreMain')
if ogre_src.exists():
    conv = (ogre_src / 'src/OgrePixelConversions.h').read_text(encoding='utf-8')
    block = conv.split('struct A8B8G8R8toR8G8B8A8', 1)[1].split('};', 1)[0]
    assert 'return ((inp&0x000000FF)<<24)|((inp&0x0000FF00)<<8)|((inp&0x00FF0000)>>8)|((inp&0xFF000000)>>24);' in block
    bitwise = (ogre_src / 'include/OgreBitwise.h').read_text(encoding='utf-8')
    assert 'else return (unsigned int)(value * float(1<<bits));' in bitwise
    assert 'return bits ? (float)value/(float)((1<<bits)-1) : 0.0f;' in bitwise
    fmt = (ogre_src / 'include/OgrePixelFormat.h').read_text(encoding='utf-8')
    little = fmt.split('#if OGRE_ENDIAN == OGRE_ENDIAN_BIG', 1)[1].split('#else', 1)[1].split('#endif', 1)[0]
    assert 'PF_BYTE_RGBA = PF_A8B8G8R8,' in little


def update_body(source):
    start = source.index('{', source.index('void MiniMapDrawn::update('))
    depth, end = 1, start + 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def verify(source, header):
    body = re.sub(r'//[^\n]*|/\*.*?\*/', '', update_body(source), flags=re.S)
    assert 'setColourAt' not in body and 'ColourValue(' not in body
    lock = body.index('Ogre::PixelBox output = mPixelBuffer->lock(mPixelBox, Ogre::HardwareBuffer::HBL_NORMAL);')
    box = body.index('const Ogre::PixelBox source(mWidth, mHeight, 1, Ogre::PF_BYTE_RGBA, mTiles.data());')
    convert = body.index('Ogre::PixelUtil::bulkPixelConversion(source, output);')
    unlock = body.index('mPixelBuffer->unlock();')
    assert body.count('bulkPixelConversion(') == 1
    assert lock < box < convert < unlock
    assert 'static_assert(sizeof(Color) == 4' in body
    # Bytes in R, G, B, A order, tightly packed, one per map pixel.
    color = header.split('struct Color', 1)[1].split('};', 1)[0]
    members = re.findall(r'Ogre::uint8 (\w+);', color)
    assert members == ['RR', 'GG', 'BB', 'AA'], members
    assert 'mTiles(mWidth * mHeight, Color(0,0,0)),' in source
    assert 'mPixelBox(mWidth, mHeight, 1, Ogre::PF_R8G8B8A8),' in source
    assert 'mWidth, mHeight, 0, Ogre::PF_R8G8B8A8,' in source


source = SOURCE.read_text(encoding='utf-8')
header = HEADER.read_text(encoding='utf-8')
verify(source, header)
mutations = [
    (source.replace('Ogre::PF_BYTE_RGBA, mTiles.data()', 'Ogre::PF_BYTE_BGRA, mTiles.data()', 1), header),
    (source.replace('Ogre::PF_BYTE_RGBA, mTiles.data()', 'Ogre::PF_R8G8B8A8, mTiles.data()', 1), header),
    (source.replace('    Ogre::PixelUtil::bulkPixelConversion(source, output);\n\n    mPixelBuffer->unlock();',
                    '    mPixelBuffer->unlock();\n    Ogre::PixelUtil::bulkPixelConversion(source, output);', 1), header),
    (source.replace('const Ogre::PixelBox source(mWidth, mHeight, 1,', 'const Ogre::PixelBox source(mHeight, mWidth, 1,', 1), header),
    (source, header.replace('    Ogre::uint8 BB;\n    Ogre::uint8 AA;', '    Ogre::uint8 AA;\n    Ogre::uint8 BB;', 1)),
    (source.replace('    static_assert(sizeof(Color) == 4, "map pixels must be tightly packed RGBA bytes");\n', '', 1), header),
    (source.replace('    Ogre::PixelUtil::bulkPixelConversion(source, output);\n',
                    '    Ogre::PixelUtil::bulkPixelConversion(source, output);\n    output.setColourAt(Ogre::ColourValue::Black, 0, 0, 0);\n', 1), header),
]
for mutated, mutated_header in mutations:
    assert (mutated, mutated_header) != (source, header)
    try:
        verify(mutated, mutated_header)
    except (AssertionError, ValueError):
        continue
    raise AssertionError('unsafe minimap upload mutation was accepted')
print('minimap bulk upload: %d pixels byte-identical to the former setColourAt loop, generic path exact for 256 values, '
      '%d mutations rejected' % (checked, len(mutations)))
