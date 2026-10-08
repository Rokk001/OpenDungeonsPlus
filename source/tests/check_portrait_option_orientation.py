"""Non-compiling checks of the targeted portrait reflection contract."""
from pathlib import Path
import importlib.util

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('manifests', ROOT/'scripts/check_portrait_manifests.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
expected = {('Goblin.mesh','ears',1), ('Goblin.mesh','ears',2), ('Elf.mesh-male','ears',1)}
actual = set()
count = 0
for manifest in sorted((ROOT/'materials/portraits/variants').glob('*/manifest.cfg')):
    validator.check(manifest)
    count += 1
    for line in manifest.read_text().splitlines():
        row = line.split('\t')
        if row[0]=='Option' and len(row)==6:
            assert row[5]=='flip-x'
            actual.add((manifest.parent.name,row[1],int(row[2])))
assert actual == expected, (actual, expected)

# Reflection is measured across the entire source slot before destination clipping.
source = [10, 20, 30]
assert [source[len(source)-1-x] for x in range(2)] == [30, 20]
assert source == [10, 20, 30]
composer = (ROOT/'source/render/AppearanceCompose.cpp').read_text()
assert 'part.mFlipX ? part.mImage.mWidth - 1 - x : x' in composer
assert 'part.mImage.mWidth + sourceX' in composer
picture = (ROOT/'source/render/CreatureAppearancePicture.cpp').read_text()
assert 'part.mFlipX = option->mFlipX;' in picture
parser = (ROOT/'source/render/PortraitManifest.cpp').read_text()
assert 'raw.mOption.mFlipX = false;' in parser
assert 'columns[5] != "flip-x"' in parser
assert 'columns.size() > 6' in parser
# Invalid extra transformations must also be rejected by the non-compiling validator.
original = ROOT/'materials/portraits/variants/Goblin.mesh/manifest.cfg'
class InvalidManifest:
    parent = original.parent

    def read_text(self, **kwargs):
        return original.read_text().replace('flip-x', 'rotate')

try:
    validator.check(InvalidManifest())
except AssertionError:
    pass
else:
    raise AssertionError('unknown transformation accepted')
print(f'Portrait orientation contract: {count} catalogs valid; 3 targeted options; uncompiled C++ source wiring checked')
