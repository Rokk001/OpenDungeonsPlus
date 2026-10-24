"""Static check that fog and mark surfaces never stay on tiles whose state does not call for them.

Known tiles (seen at least once) show their real mesh. Fog surfaces, dig-mark surfaces and clouds may only
exist for a tile when its state asks for them:
  - never-seen tiles use ordinary earth in the shared terrain entity, with no separate fog surface,
  - the shared terrain mark only while the local player has the tile marked,
  - the cloud only on a seen tile of enemy territory that is currently fogged,
  - all of them are removed again as soon as the tile state no longer asks for them.
Every cloud instance is also placed at zero offset from the tile's own scene node, which already sits at the
tile coordinates: a tile position there is added a second time and moves the fog onto other tiles, which
shows as large black or brown patches on known ground. Run from any directory; no build, no game start.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
render = (root / "source/render/RenderManager.cpp").read_text(encoding="utf-8")
failures = []


# Collect every independent fog-state contract failure.
def check(condition, message):
    if not condition:
        failures.append(message)


def between(text, start, end):
    """Return the part of text from the first start marker up to the following end marker."""
    first = text.index(start)
    return text[first:text.index(end, first)]


# 1. Placement: one helper sets the zero offset, no other code positions a fog instance.
helper = between(render, "static void rrPlaceFogInstance(", "\n}\n")
check("setPosition(Ogre::Vector3::ZERO)" in helper, "fog placement helper must use the zero offset")
refresh = between(render, "void RenderManager::rrRefreshTile(", "\nvoid RenderManager::rrCreateTile(")
for match in re.finditer(r"getFogOfWar(Mesh|Cloud)\(\)\s*->\s*setPosition\(", render):
    failures.append("fog instance positioned directly at offset " + str(match.start()) + ", use rrPlaceFogInstance")
# The three obsolete earth instances are gone; the one delayed cloud remains instanced.
check(len(re.findall(r"rrPlaceFogInstance\(", refresh)) == 1, "every fog attach must call rrPlaceFogInstance")
check(len(re.findall(r"attachObject\(tile\.getFogOfWar(Mesh|Cloud)\(\)\)", refresh)) == 1,
      "the fog attach count changed, update this check together with the placement calls")
check("getPosition()" not in "".join(re.findall(r"[^\n]*FogOfWar[^\n]*", refresh)),
      "a fog line in the tile refresh uses a tile position")
create = between(render, "void RenderManager::rrCreateTile(", "\nvoid RenderManager::rrDestroyTile(")
check("node->setPosition(static_cast<Ogre::Real>(tile.getX()), static_cast<Ogre::Real>(tile.getY())" in create,
      "the tile scene node must sit at the tile coordinates, otherwise fog needs an offset")

# 2. A separate neutral or marked fog surface is prohibited everywhere, rather than only on known tiles.
# Exact common earth selection, creation, appearance and copied mark passes are checked in full,
# with real mesh-neighbour tests and eleven negative mutations; no condition can leak a hidden type.
import runpy
runpy.run_path(str(root / 'source/tests/check_fog_earth_geometry.py'), run_name='__fog_contract__')
check('createInstancedEntity("DirtInstanced")' not in render and 'createMarkedFogMesh' not in render,
      'a separate neutral or marked fog surface still exists')
check('mInstanceManagerMarkedFog' not in render and 'mInstanceManagerDirt' not in render,
      'an obsolete fog manager can recreate a stale surface')
check('colourizeEntity(tileMeshEnt, seatColor, isMarked, vision)' in refresh,
      'the common terrain mark must follow the local mark state')

# 3. Revealing now replaces the ordinary earth entity, not a separate fog instance.
# The former fog handle cannot exist (section 2); every changed mesh still detaches and destroys.
replacement = between(refresh, 'if(mSceneManager->hasEntity(tileMeshName))', 'Ogre::SceneNode* tileMeshNode')
for needle in ['getMesh()->getName().compare(meshName) != 0', 'detachObject(tileMeshEnt)',
               'destroyEntity(tileMeshEnt)', 'tileMeshEnt = nullptr']:
    check(needle in replacement, 'revealing a tile does not replace its earth mesh: missing ' + needle)
check('tile.setHasFogOfWar(false)' in refresh and 'tile.setHasFogOfWar(true)' not in refresh,
      'the obsolete fog surface flag can survive reveal')
# The independently valid cloud cleanup assertions remain strict: no cloud can exist before
# discovery, and ending enemy fog must detach, destroy and null its handle in that order.
cleanup = between(refresh, 'else if(!tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() != nullptr)',
                  '\n    if(tile.getFogOfWarCloud() != nullptr)')
for needle in ['detachObject(tile.getFogOfWarCloud())', 'destroyInstancedEntity(tile.getFogOfWarCloud())',
               'tile.setFogOfWarCloud(nullptr)']:
    check(needle in cleanup, 'cloud state cleanup is missing ' + needle)
check(cleanup.index('detachObject') < cleanup.index('destroyInstancedEntity') < cleanup.index('setFogOfWarCloud(nullptr)'),
      'cloud cleanup must detach and destroy before nulling its handle')

# 4. The cloud exists only on seen tiles with the enemy fog state and goes away with that state.
cloud = refresh[refresh.index("// Only previously discovered enemy territory"):]
cloud = cloud[:cloud.index("// We rescale and set the orientation")]
check("if(tile.getEverVisible() && tileMeshNode != nullptr)" in cloud, "cloud creation must require a seen tile")
check("if(tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() == nullptr)" in cloud,
      "cloud creation must require the enemy fog state")
check("else if(!tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() != nullptr)" in cloud,
      "the cloud must be removed when the enemy fog state ends")
check(refresh.count('createInstancedEntity("Fog")') == 1, "the cloud must have exactly one creation site")
check(render.count('createInstancedEntity("Fog")') == 1, "the cloud is created somewhere outside the tile refresh")
destroy = between(render, "void RenderManager::rrDestroyTile(", "\n}\n")
check("destroyInstancedEntity(tile.getFogOfWarMesh())" in destroy and "destroyInstancedEntity(tile.getFogOfWarCloud())" in destroy,
      "destroying a tile must remove its fog instances")

if failures:
    print("\n".join("FAIL: " + f for f in failures))
    sys.exit(1)
print("OK")
