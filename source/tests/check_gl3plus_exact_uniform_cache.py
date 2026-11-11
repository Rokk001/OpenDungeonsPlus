"""Check selective uniform caching without compiling Ogre or claiming runtime savings."""
from pathlib import Path
import argparse
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PATCH = ROOT / 'scripts/win32/patches/ogre14-gl3plus-exact-uniform-cache.patch'


def preimages(patch):
    """Reconstruct text fixtures with the old hunk positions for both apply modes."""
    files = {}
    lines = None
    remaining = 0
    for line in patch.splitlines(True):
        if line.startswith('--- a/'):
            name = line[6:].strip()
            lines = files.setdefault(name, [])
        elif line.startswith('@@ '):
            match = re.match(r'@@ -(\d+)(?:,(\d+))? ', line)
            start, count = int(match[1]), int(match[2] or 1)
            while len(lines) < start - 1:
                lines.append('\n')
            remaining = count
        elif remaining and line[0] in ' -':
            lines.append(line[1:])
            remaining -= 1
        elif remaining and line == '\n':
            # git accepts an empty context line without its whitespace prefix.
            lines.append(line)
            remaining -= 1
    return {name: ''.join(lines) for name, lines in files.items()}


def verify(files):
    """Require exact comparison, selective opt-in, full widths and both lifecycle clears."""
    header = files['RenderSystems/GLSupport/include/OgreGLUniformCache.h']
    cache = files['RenderSystems/GLSupport/src/OgreGLUniformCache.cpp']
    shader = files['RenderSystems/GL3Plus/src/GLSL/src/OgreGLSLShader.cpp']
    program = files['RenderSystems/GL3Plus/src/GLSL/src/OgreGLSLSeparableProgram.cpp']
    assert 'std::pair<bool, std::vector<unsigned char> > ExactUniformValue' in header
    exact = cache.split('bool GLUniformCache::updateUniformExact(', 1)[1].split('bool GLUniformCache::updateUniform(', 1)[0]
    assert '#if' not in exact and 'FastHash' not in exact
    for token in ('mExactUniformValueMap[location]', 'cached.second.size() == length',
                  'cached.first == transpose', 'length != 0 && std::memcmp(cached.second.data(), value, length) == 0',
                  'return false;', 'cached.first = transpose;', 'cached.second.resize(length);',
                  'std::memcpy(cached.second.data(), value, length);', 'return true;'):
        assert token in exact
    clear = cache.split('void GLUniformCache::clearCache()', 1)[1].split('//! Suppresses', 1)[0]
    assert clear.index('mExactUniformValueMap.clear();') < clear.index('#ifdef OGRE_ENABLE_STATE_CACHE')
    legacy = cache.split('bool GLUniformCache::updateUniform(', 1)[1]
    assert '#ifdef OGRE_ENABLE_STATE_CACHE' in legacy
    link = shader.split('bool GLSLShader::linkSeparable()', 1)[1].split('return true;', 2)
    # The already-linked fast path must retain its cache; new links must clear before GL calls.
    assert 'if(mLinked)' in link[0] and 'clearCache' not in link[0]
    assert link[1].index('mUniformCache.clearCache();') < link[1].index('glProgramParameteri')
    assert link[1].index('mUniformCache.clearCache();') < link[1].index('getMicrocodeFromCache')
    unload = shader.split('void GLSLShader::unloadHighLevelImpl(void)', 1)[1]
    assert unload.index('mUniformCache.clearCache();') < unload.index('glDeleteShader')
    assert 'uniformCache->updateUniformExact(def->logicalIndex, val,' in program
    assert 'def->elementSize * def->arraySize * (def->isDouble() ? 8 : 4), transpose)' in program


def fixtures():
    """Specify fixed upload decisions for bytes, orientation, programs and resets."""
    caches = [{}, {}]
    cases = [
        (0, 2, b'\x00' * 4, False, True),
        (0, 2, b'\x00' * 4, False, False),
        (0, 2, b'\x00\x00\x00\x80', False, True),  # signed zero
        (0, 2, b'\x00\x00\x00\x80', True, True),
        (0, 2, b'\x00\x00\x00\x80', True, False),
        (1, 2, b'\x00\x00\x00\x80', True, True),  # another program
        (0, 2, b'\x00' * 8, True, True),
        (0, 2, b'\x00' * 7 + b'\x01', True, True),  # double upper bytes
        (0, 3, b'\x00' * 7 + b'\x01', True, True),
        (0, 2, b'\x00' * 7 + b'\x01', True, False),
        (0, 2, b'\x01\x00\xc0\x7f', False, True),  # NaN payload
        (0, 2, b'\x01\x00\xc0\x7f', False, False),
        (0, 2, b'\x02\x00\xc0\x7f', False, True),
        (0, 4, b'array-0-array-1', False, True),
        (0, 4, b'array-0-array-2', False, True),  # another array element
        (0, 4, b'array-0-array-2', False, False),
        (0, 4, b'', False, True),  # no cached-empty sentinel can suppress an upload
        (0, 4, b'', False, True),
    ]
    for program, location, value, transpose, expected in cases:
        current = (transpose, value)
        upload = not value or caches[program].get(location) != current
        assert upload == expected
        caches[program][location] = current
    caches[0].clear()
    assert 2 not in caches[0] and 2 in caches[1]
    assert len(cases) == 18


def native_probe(files):
    """Optionally compile the actual patched method; FINAL alone may invoke --probe."""
    import runpy
    extract = runpy.run_path(str(ROOT / 'source/tests/check_terrain_draw_batch.py'))['body']
    cache = files['RenderSystems/GLSupport/src/OgreGLUniformCache.cpp']
    exact = extract(cache, 'bool GLUniformCache::updateUniformExact(')
    clear = extract(cache, 'void GLUniformCache::clearCache(')
    program = r'''
#include <unordered_map>
#include <vector>
#include <utility>
#include <cstring>
#include <cassert>
//! Exercises the actual patch method without an Ogre or GL runtime.
class GLUniformCache
{
    typedef std::pair<bool, std::vector<unsigned char> > ExactUniformValue;
    std::unordered_map<int, ExactUniformValue> mExactUniformValueMap;
public:
    bool updateUniformExact(int location, const void* value, size_t length, bool transpose);
    void clearCache();
};
bool GLUniformCache::updateUniformExact(int location, const void* value, size_t length, bool transpose)
{ EXACT }
void GLUniformCache::clearCache()
{ CLEAR }
//! Checks actual upload decisions, complete arrays, double tails and cache invalidation.
int main()
{
    GLUniformCache first;
    GLUniformCache second;
    unsigned char value[64] = {};
    assert(first.updateUniformExact(2, value, 64, false));
    assert(!first.updateUniformExact(2, value, 64, false));
    value[63] = 1;
    assert(first.updateUniformExact(2, value, 64, false));
    assert(!first.updateUniformExact(2, value, 64, false));
    assert(first.updateUniformExact(2, value, 64, true));
    assert(second.updateUniformExact(2, value, 64, true));
    assert(first.updateUniformExact(2, value, 8, true));
    value[7] = 1;
    assert(first.updateUniformExact(2, value, 8, true));
    assert(!first.updateUniformExact(2, value, 8, true));
    assert(first.updateUniformExact(3, value, 8, true));
    first.clearCache();
    assert(first.updateUniformExact(2, value, 8, true));
    assert(first.updateUniformExact(2, nullptr, 0, true));
    assert(first.updateUniformExact(2, nullptr, 0, true));
    return 0;
}
'''.replace('EXACT', exact).replace('CLEAR', clear)
    with tempfile.TemporaryDirectory(prefix='exact-uniform-native-') as temporary:
        directory = Path(temporary)
        (directory / 'probe.cpp').write_text(program)
        # cl is provided by the check runner's configured compiler environment.
        subprocess.run(['cl', '/nologo', '/EHsc', '/MD', 'probe.cpp', '/Feprobe.exe'],
                       cwd=directory, check=True)
        subprocess.run([str(directory / 'probe.exe')], cwd=directory, check=True)
    print('exact uniform native probe: 13 fixed assertions passed')


def pinned_source_check(source):
    """Apply all seven installer patches to isolated pinned source files, then reverse them."""
    pinned = 'f906880885f6014ca9b5bd8aaa09b399394d5676'
    subprocess.run(['git', '-C', str(source), 'cat-file', '-e', pinned + '^{commit}'], check=True)
    names = (
        'ogre14-multiwindow-settings.patch', 'ogre14-short-emitter.patch',
        'ogre14-light-position-cache.patch', 'ogre14-discard-lock-unsynchronized.patch',
        'ogre14-gl3plus-program-shutdown.patch', 'ogre14-gl3plus-exact-uniform-cache.patch',
        'ogre14-tower-trace.patch',
    )
    patches = [PATCH.parent / name for name in names]
    install = (ROOT / 'scripts/win32/install-ogre-prereq.ps1').read_text()
    assert [install.index("'patches/" + name + "'") for name in names] == sorted(
        install.index("'patches/" + name + "'") for name in names)
    paths = set()
    for patch in patches:
        paths.update(re.findall(r'^--- a/(.+)$', patch.read_text(), re.MULTILINE))
    # Binary patches have no --- header; bind their preimage to the fixed target.
    binary_target = 'RenderSystems/GL3Plus/src/OgreGL3PlusHardwareBuffer.cpp'
    binary_stats = subprocess.check_output(
        ['git', 'apply', '--numstat', str(patches[3])], text=True).splitlines()
    assert binary_stats == ['-\t-\t' + binary_target], binary_stats
    paths.add(binary_target)
    with tempfile.TemporaryDirectory(prefix='pinned-ogre-patches-') as temporary:
        directory = Path(temporary) / 'src/ogre'
        directory.mkdir(parents=True)
        subprocess.run(['git', 'init', '--quiet'], cwd=directory, check=True)
        subprocess.run(['git', 'config', 'core.autocrlf', 'false'], cwd=directory, check=True)
        before = {}
        for name in paths:
            before[name] = subprocess.check_output(['git', '-C', str(source), 'show', pinned + ':' + name])
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(before[name])
        # Execute the actual patch phase, excluding receipt removal and all build commands.
        phase = install.split("$taskPatch = Join-Path", 1)[1]
        phase = '$taskPatch = Join-Path' + phase.split("$ErrorActionPreference = 'Stop'", 1)[0]
        script = Path(temporary) / 'patch-phase.ps1'
        script.write_text('param($taskRoot, $taskPatchDirectory)\n' +
                          phase.replace('$PSScriptRoot', '$taskPatchDirectory'))
        for repeat in range(2):
            result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                                     '-File', str(script), temporary, str(PATCH.parent.parent)],
                                    capture_output=True, text=True, check=True)
            assert result.stdout.count('Applying OGRE') == (7 if repeat == 0 else 0), result.stdout
            for patch in patches:
                subprocess.run(['git', 'apply', '--recount', '--reverse', '--check', str(patch)],
                               cwd=directory, check=True)
        verify({name: (directory / name).read_text() for name in preimages(PATCH.read_text())})
        for patch in reversed(patches):
            subprocess.run(['git', 'apply', '--recount', '--reverse', '--check', str(patch)],
                           cwd=directory, check=True)
            subprocess.run(['git', 'apply', '--recount', '--reverse', str(patch)], cwd=directory, check=True)
        assert all((directory / name).read_bytes() == data for name, data in before.items())
        assert not (directory / 'OgreMain/src/OgreODTowerTrace.h').exists()
    print('pinned Ogre: seven patches applied, second install skipped all seven, all reversed byte-for-byte')


def main():
    """Check actual installer apply modes and reject thirteen source mutations and old receipts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--ogre-source', type=Path, help='read pinned files from this Git repository without modifying it')
    args = parser.parse_args()
    assert b'\r' not in PATCH.read_bytes(), 'exact uniform patch must retain LF on Windows checkouts'
    attributes = subprocess.check_output(['git', 'check-attr', 'eol', '--', str(PATCH)], cwd=ROOT, text=True)
    assert attributes.strip().endswith(': eol: lf'), 'patch requires an explicit LF checkout attribute'
    patch = PATCH.read_text()
    before = preimages(patch)
    assert len(before) == 4
    with tempfile.TemporaryDirectory(prefix='exact-uniform-') as temporary:
        directory = Path(temporary)
        for name, text in before.items():
            target = directory / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding='utf-8')
        applied = subprocess.run(['git', 'apply', '--recount', '--check', str(PATCH)], cwd=directory,
                                 capture_output=True, text=True)
        assert applied.returncode == 0, applied.stderr
        applied = subprocess.run(['git', 'apply', '--recount', str(PATCH)], cwd=directory, capture_output=True, text=True)
        assert applied.returncode == 0, applied.stderr
        after = {name: (directory / name).read_text() for name in before}
        verify(after)
        if args.probe:
            native_probe(after)
        mutations = [
            ('cached.second.size() == length', 'true'),
            ('cached.first == transpose', 'true'),
            ('std::memcmp(cached.second.data(), value, length) == 0', 'true'),
            ('cached.first = transpose;', ';'),
            ('cached.second.resize(length);', ';'),
            ('std::memcpy(cached.second.data(), value, length);', ';'),
            ('mExactUniformValueMap.clear();', ';'),
            ('mUniformCache.clearCache();', ';'),
            ('def->isDouble() ? 8 : 4', '4'),
            ('uniformCache->updateUniformExact(', 'uniformCache->updateUniform('),
            ('mExactUniformValueMap[location]', 'mExactUniformValueMap[0]'),
        ]
        for old, new in mutations:
            assert any(old in text for text in after.values())
            try:
                verify({name: text.replace(old, new) for name, text in after.items()})
            except (AssertionError, ValueError, IndexError):
                continue
            raise AssertionError('accepted mutation: ' + old)
        shader_name = 'RenderSystems/GL3Plus/src/GLSL/src/OgreGLSLShader.cpp'
        for signature in ('bool GLSLShader::linkSeparable()', 'void GLSLShader::unloadHighLevelImpl(void)'):
            shader = after[shader_name]
            start = shader.index(signature)
            clear = shader.index('mUniformCache.clearCache();', start)
            candidate = dict(after)
            candidate[shader_name] = shader[:clear] + shader[clear:].replace('mUniformCache.clearCache();', ';', 1)
            try:
                verify(candidate)
            except (AssertionError, ValueError):
                continue
            raise AssertionError('accepted missing lifecycle clear: ' + signature)
        reversed_patch = subprocess.run(['git', 'apply', '--recount', '--reverse', '--check', str(PATCH)], cwd=directory,
                                        capture_output=True, text=True)
        assert reversed_patch.returncode == 0, reversed_patch.stderr
        reversed_patch = subprocess.run(['git', 'apply', '--recount', '--reverse', str(PATCH)], cwd=directory,
                                        capture_output=True, text=True)
        assert reversed_patch.returncode == 0, reversed_patch.stderr
        assert all((directory / name).read_text() == text for name, text in before.items())
        # Retain the predecessor's plain-apply coverage alongside the installer path.
        subprocess.run(['git', 'apply', str(PATCH)], cwd=directory, check=True)
        subprocess.run(['git', 'apply', '--reverse', str(PATCH)], cwd=directory, check=True)
        assert all((directory / name).read_text() == text for name, text in before.items())
    if args.ogre_source:
        pinned_source_check(args.ogre_source)
    fixtures()
    install = (ROOT / 'scripts/win32/install-ogre-prereq.ps1').read_text()
    assert PATCH.name in (ROOT / 'scripts/win32/ogre-prereq-provenance.ps1').read_text()
    assert 'apply --recount --reverse --check $taskExactUniformPatch' in install
    assert install.index('apply --recount $taskExactUniformPatch') < install.index('$taskPatchHashes = Get-OgrePrereqPatchHashes')
    print('exact uniform cache: patch apply/reverse, 18 decision fixtures, 13 rejected mutations; runtime gate deferred')


if __name__ == '__main__':
    main()
