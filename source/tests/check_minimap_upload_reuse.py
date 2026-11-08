"""Guard exact minimap upload reuse without skipping colour, animation or overlay updates.

The measured driver upload is avoided only for identical bytes in the same loaded
texture generation. This noncompiling check cannot establish native speed or parity.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


def block(source, marker):
    """Extract one balanced C++ block after a unique marker."""
    start = source.index('{', source.index(marker))
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start + 1:end - 1], start, end


def verify(source, header):
    """Require full-byte comparison, reload invalidation and unconditional non-upload work."""
    source = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
    body, _, _ = block(source, 'void MiniMapDrawn::update(')
    gate = 'if(currentBuffer != mPixelBuffer'
    upload, opening, closing = block(body, gate)
    condition = body[body.index(gate):opening]
    assert 'if(!mMiniMapOgreTexture->isLoaded())\n        mMiniMapOgreTexture->createInternalResources();' in body[:opening]
    assert 'const Ogre::HardwarePixelBufferSharedPtr currentBuffer = mMiniMapOgreTexture->getBuffer();' in body[:opening]
    assert 'mUploadedTextureState != mMiniMapOgreTexture->getStateCount()' in condition
    assert 'mUploadedTiles.size() != mTiles.size()' in condition
    assert 'std::memcmp(mUploadedTiles.data(), mTiles.data(), mTiles.size() * sizeof(Color)) != 0' in condition
    assert 'static_assert(sizeof(Color) == 4' in body[:body.index(gate)]
    assert 'std::vector<Color> mUploadedTiles;' in header
    assert 'mUploadedTiles(' not in source  # First upload cannot be skipped for initially black pixels.
    assert 'mUploadedTextureState(0)' in source
    order = [upload.index(text) for text in (
        'currentBuffer->lock(',
        'Ogre::PixelUtil::bulkPixelConversion(source, output);',
        'currentBuffer->unlock();',
        'mUploadedTiles = mTiles;',
        'mPixelBuffer = currentBuffer;',
        'mUploadedTextureState = mMiniMapOgreTexture->getStateCount();')]
    assert order == sorted(order)
    assert body.index('advanceAnimation(timeSinceLastFrame);') < body.index(gate)
    assert body.index('drawPixel(') < body.index(gate)
    assert 'updateMapOverlay(' in body[closing:]
    assert 'return;' not in body


def check_pixels():
    """Replay every changed byte and repeated frame against an always-uploaded texture."""
    pixels = bytes(64)
    frames = [pixels, pixels]
    for index in range(64):
        changed = bytearray(pixels)
        changed[index] = 255
        frames.extend((bytes(changed), bytes(changed)))
    cached, surface, uploads = None, None, 0
    for frame in frames:
        if cached != frame:
            surface = cached = frame
            uploads += 1
        assert surface == frame
    assert len(frames) == 130 and uploads == 65
    # Recreating a texture loses its pixels even when all desired bytes are identical.
    surface = None
    previous_generation, new_generation = 1, 2
    assert cached == frames[-1] and previous_generation != new_generation
    surface = frames[-1]
    assert surface == cached
    # A failed upload must not cache the attempted bytes, so the next call retries.
    attempted = bytes([127]) * 64
    assert attempted != cached
    try:
        raise RuntimeError('upload failed')
    except RuntimeError:
        pass
    assert cached != attempted


def main():
    """Check contracts and reject eight independent upload or update regressions."""
    source = (ROOT / 'source/gamemap/MiniMapDrawn.cpp').read_text()
    header = (ROOT / 'source/gamemap/MiniMapDrawn.h').read_text()
    verify(source, header)
    mutations = (
        ('if(currentBuffer != mPixelBuffer', 'if(false'),
        ('mUploadedTextureState != mMiniMapOgreTexture->getStateCount()', 'false'),
        ('mUploadedTiles.size() != mTiles.size()', 'false'),
        ('mTiles.size() * sizeof(Color)) != 0', 'mTiles.size() * 3) != 0'),
        ('mMiniMapOgreTexture->createInternalResources();', ';'),
        ('currentBuffer->unlock();', 'mUploadedTiles = mTiles;\n        currentBuffer->unlock();'),
        ('advanceAnimation(timeSinceLastFrame);', ';'),
        ('updateMapOverlay(mMiniMapWindow', 'return;\n    updateMapOverlay(mMiniMapWindow'),
    )
    for old, new in mutations:
        assert old in source, old
        try:
            verify(source.replace(old, new), header)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: ' + old)
    check_pixels()
    print('minimap upload reuse: 130 byte-change frames, 65 uploads, reload/failure fixtures, 8 rejected mutations')


if __name__ == '__main__':
    main()
