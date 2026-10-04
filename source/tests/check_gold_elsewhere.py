"""Check the gold shown outside the treasury: a coin heap for gold on the floor, a sack for gold carried
by a worker, brighter veins in the walls, and the wiring of these into the renderer. Also runs the render
budget count (no game start needed)."""
from pathlib import Path
import subprocess
import sys

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


render = read('source/render/RenderManager.cpp')
loose = read('source/render/LooseGoldMesh.cpp')
header = read('source/render/LooseGoldMesh.h')

# Floor gold becomes a heap, carried gold a sack, both only while the treasury detail is not off.
assert 'LooseGoldMesh::prepareHeap(mSceneManager, meshName)' in render
assert 'GameEntityType::treasuryObject' in render
assert 'LooseGoldMesh::prepareSack(mSceneManager, carried->getMeshName())' in render
assert loose.count('TreasuryGoldMesh::Detail::off') == 2
# The sack and its visibility swap are undone when the gold is put down and when the object goes away.
assert '_sack' in render and render.count('"_sack"') >= 3
assert 'carriedEnt->setVisible(true)' in render
# Four sizes follow the four classic stack names the server already sends; nothing else is replicated.
assert 'sizeCount = 4' in header
assert 'GoldstackLv' in loose
assert 'GoldstackLv1' in read('source/entities/TreasuryObject.cpp')
# Assets: material, texture, generator, credits, build.
assert 'material GoldSack' in read('materials/scripts/GoldSack.material')
assert (repo / 'materials/textures/GoldSack.png').exists()
assert (repo / 'tools/treasury-gold/generate_gold_sack.py').exists()
assert 'GoldSack.png' in read('CREDITS')
assert 'LooseGoldMesh.cpp' in read('CMakeLists.txt')
# Veins: brighter gold wall shader with a glint, brighter gem material.
frag = read('shaders/GoldDistortion.frag')
assert 'veinGain' in frag and 'veinTime' in frag
gold_material = read('materials/scripts/Gold.material')
assert 'veinGain' in gold_material and 'veinTime time_0_x' in gold_material
assert 'emissive 0.22' in read('materials/scripts/GemFull.material')

result = subprocess.run([sys.executable, str(repo / 'tools/treasury-gold/check_gold_budget.py')])
assert result.returncode == 0, 'render budget exceeded'

print('check_gold_elsewhere ok')
