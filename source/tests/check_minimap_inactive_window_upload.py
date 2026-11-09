"""Guard that the drawn minimap uploads no texture while Ogre does not draw the render window.

Measured cause (profiling build 0.7.4.54): while the game window was not
drawn, MiniMapDrawn::update still uploaded its texture in both frame callbacks without any buffer swap.
Every 6.5-13 s the driver then blocked 0.8-1.5 s in glTexSubImage2D (minimap 16.53% of the main loop,
S3 game minute maxima 865-1587 ms). Ogre 14 RenderSystem::_updateAllRenderTargets and
_swapAllRenderTargetBuffers skip every target whose isActive() is false (RenderWindow::isActive() is
mActive && isVisible()), so nothing uploaded in that state can be seen.

The check proves in source and by replay that:
- the upload is skipped only while the render window is inactive;
- colours, animation and overlays still update every call;
- the comparison baseline remains the last uploaded bytes, so every drawn frame shows exactly the
  bytes the former always-upload code would show.
It is noncompiling and cannot establish native speed or parity.
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
GATE = 'if(windowDrawn && (currentBuffer != mPixelBuffer'


def block(source, marker):
    """Extract one balanced C++ block after a unique marker."""
    start = source.index('{', source.index(marker))
    end, depth = start + 1, 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start + 1:end - 1], start, end


def verify(source):
    """Require the inactive-window gate around the upload only, never around map work."""
    assert '#include <OgreRenderWindow.h>' in source
    source = re.sub(r'//[^\n]*|/\*.*?\*/', '', source, flags=re.S)
    body, _, _ = block(source, 'void MiniMapDrawn::update(')
    assert body.count('windowDrawn') == 2, 'windowDrawn must be defined once and used only by the upload gate'
    definition = 'const Ogre::RenderWindow* window = ODFrameListener::getSingleton().getRenderWindow();'
    assert body.count(definition) == 1
    assert 'const bool windowDrawn = window == nullptr || window->isActive();' in body
    gate = body.index(GATE)
    assert body.index(definition) < gate
    upload, opening, closing = block(body, GATE)
    condition = body[gate:opening]
    # All four reuse comparisons stay inside one parenthesised group that windowDrawn guards.
    for text in ('currentBuffer != mPixelBuffer',
                 'mUploadedTextureState != mMiniMapOgreTexture->getStateCount()',
                 'mUploadedTiles.size() != mTiles.size()',
                 'std::memcmp(mUploadedTiles.data(), mTiles.data(), mTiles.size() * sizeof(Color)) != 0'):
        assert text in condition, text
    assert condition.rstrip().endswith('!= 0))'), 'the comparisons must be grouped under windowDrawn'
    assert condition.count('(') == condition.count(')')
    for text in ('currentBuffer->lock(', 'currentBuffer->unlock();', 'mUploadedTiles = mTiles;',
                 'mPixelBuffer = currentBuffer;',
                 'mUploadedTextureState = mMiniMapOgreTexture->getStateCount();'):
        assert body.count(text) == 1 and text in upload, text
    assert body.index('advanceAnimation(timeSinceLastFrame);') < gate
    assert body.index('drawPixel(') < gate
    assert 'updateMapOverlay(' in body[closing:]
    assert 'return;' not in body
    assert 'isVisible()' not in body, 'Ogre skips drawing by isActive(), which also covers deactivation'


def replay():
    """Compare the gated upload against the former always-upload texture in every drawn frame."""
    frames = []
    pixels = bytes(16)
    for index in range(48):
        if index % 3 == 0:
            changed = bytearray(pixels)
            changed[index % 16] = (changed[index % 16] + 37) % 256
            pixels = bytes(changed)
        active = not (12 <= index < 29 or index in (35, 41))
        # Two callbacks per Ogre frame update the minimap with the same bytes.
        frames.append((pixels, active))
        frames.append((pixels, active))
    # previous: byte reuse without the window gate; gated: this source.
    previous_baseline, previous_texture, previous_uploads, previous_inactive = None, None, 0, 0
    baseline, texture, uploads, inactive_uploads = None, None, 0, 0
    for pixels, active in frames:
        if previous_baseline != pixels:
            previous_texture = previous_baseline = pixels
            previous_uploads += 1
            previous_inactive += 0 if active else 1
        if active and baseline != pixels:
            texture = baseline = pixels
            uploads += 1
            inactive_uploads += 0 if active else 1
        if active:
            assert texture == pixels == previous_texture, 'a drawn frame must show the current map'
    assert len(frames) == 96 and inactive_uploads == 0
    assert (previous_uploads, previous_inactive, uploads) == (16, 6, 11), (previous_uploads, previous_inactive, uploads)
    return uploads, previous_inactive


def main():
    """Check the contract, replay the frames and reject eight independent regressions."""
    source = (ROOT / 'source/gamemap/MiniMapDrawn.cpp').read_text()
    verify(source)
    mutations = (
        (GATE, 'if((currentBuffer != mPixelBuffer'),
        ('window == nullptr || window->isActive()', 'true'),
        ('window == nullptr || window->isActive()', 'window == nullptr || !window->isActive()'),
        ('window == nullptr || window->isActive()', 'window == nullptr || window->isVisible()'),
        ((GATE, 'if(windowDrawn && currentBuffer != mPixelBuffer'), ('!= 0))\n', '!= 0)\n')),
        ('mUploadedTiles = mTiles;', ';'),
        ('updateMapOverlay(mMiniMapWindow', 'if(windowDrawn)\n    updateMapOverlay(mMiniMapWindow'),
        ('    advanceAnimation(timeSinceLastFrame);',
         '    if(!ODFrameListener::getSingleton().getRenderWindow()->isActive())\n        return;\n'
         '    advanceAnimation(timeSinceLastFrame);'),
    )
    for mutation in mutations:
        pairs = mutation if isinstance(mutation[0], tuple) else (mutation,)
        mutated = source
        for old, new in pairs:
            assert old in mutated, old
            mutated = mutated.replace(old, new, 1)
        try:
            verify(mutated)
        except (AssertionError, ValueError):
            continue
        raise AssertionError('accepted regression: %r' % (pairs,))
    uploads, skipped = replay()
    print('minimap inactive window: 96 callbacks, %d uploads instead of 16, %d inactive-window uploads '
          'avoided, every drawn frame current, %d rejected mutations' % (uploads, skipped, len(mutations)))


if __name__ == '__main__':
    main()
