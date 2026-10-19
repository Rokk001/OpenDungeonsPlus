"""Static checks that unexplored tiles reveal no type and use ordinary earth geometry and lighting.

Run from any directory. It does not start a game.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
game_mode = (root / "source/modes/GameMode.cpp").read_text(encoding="utf-8")
render = (root / "source/render/RenderManager.cpp").read_text(encoding="utf-8")
failures = []


# Record a contract failure while continuing the independent secrecy checks.
def check(condition, message):
    if not condition:
        failures.append(message)


# Unexplored walls use the same hover text and mark action regardless of their actual type.
tile_cpp = (root / "source/entities/Tile.cpp").read_text(encoding="utf-8")
check("mTileVisual == TileVisual::nullTileVisual && !mEverVisible && !getGameMap()->isServerGameMap()" in tile_cpp,
      "unexplored tiles are not markable on the client")
fog_hover = game_mode[game_mode.index("void GameMode::handlePlayerActionNone()"):game_mode.index("void GameMode::handlePlayerActionSelectTile()")]
check(fog_hover.index('"Unexplored. Click or drag to mark for digging."') < fog_hover.index('tile->fillWithEntities('),
      "neutral fog hover must precede entity and type lookup")

# The selection error texts must not describe a fogged tile
select = game_mode[game_mode.index("void GameMode::handlePlayerActionSelectTile()"):]
select = select[:select.index("\n}\n")]
fogged = select.index("!tile->getEverVisible()")
check(fogged < select.index("is already dug out") and fogged < select.index("enemy's claimed wall"),
      "selection error texts describe a fogged tile")

# The old special unlit fog plane is replaced by exact ordinary earth geometry and lighting.
# This strict companion verifies complete common creation/material/overlay blocks and rejects eleven
# independent geometry, material, height, neighbour, server and preview regressions.
import runpy
runpy.run_path(str(root / "source/tests/check_fog_earth_geometry.py"), run_name="__fog_contract__")
check('"FogOfWarDirt.mesh"' not in render and '"FogOfWarMarked.mesh"' not in render,
      "a separate fog plane can conceal or clip known earth walls")
check('createInstancedEntity("DirtInstanced")' not in render,
      "unknown tiles still use the independent unlit fog material")
check("if(tile.getFogOfWarCloud() != nullptr)" in render,
      "revealing cloud-free unknown ground must safely handle its absent cloud")
# Unknown and known earth share DirtWall, including its normals, lighting and colour grade.
material = (root / "materials/scripts/Dirt.material").read_text(encoding="utf-8")
wall_material = material[material.index("material DirtWall"):]
check("vertex_program_ref myDirtTileVertexShader" in wall_material
      and "fragment_program_ref myDirtTileFragmentShader" in wall_material,
      "ordinary earth must retain its common geometry and lighting programs")
check("if(tile.getEverVisible() && tile.shouldColorTileMesh())" in render,
      "unknown earth exposes a hidden owner's colour")

# Discovered tiles out of sight are never darkened: the colourized clone of a tile material must not
# lower its diffuse, specular, ambient or emissive colour for a missing vision.
_colourize = render[render.index("std::string RenderManager::colourizeMaterial("):]
_colourize = _colourize[:_colourize.index("\n}\n")]
_code = re.sub(r"//.*", "", _colourize)
check("current_color.r = 0.1" not in _code and "= 0.1;" not in _code,
      "tiles out of sight are darkened again")
check("if (!markedForDigging && !playerHasVision)" not in _code,
      "a vision-dependent colour change is back in colourizeMaterial")

# The fog cloud rules stay exactly as planned. Enemy territory only, thirty seconds after the last
# own creature sight: the server never marks own, allied or rogue ground as clouded.
seat_cpp = (root / "source/game/Seat.cpp").read_text(encoding="utf-8")
check("const bool enemyFog = knownOwner != nullptr && !knownOwner->isRogueSeat() &&" in seat_cpp
      and "knownOwner != this && !isAlliedSeat(knownOwner) &&" in seat_cpp
      and "p.second.mOwnCreatureSightAgeTurns >= static_cast<int64_t>(std::ceil(30.0 * ODApplication::turnsPerSecond));" in seat_cpp,
      "the enemy territory cloud rule (enemy ground, thirty seconds without own sight) changed")
# Only previously discovered ground with the enemy fog flag gets a cloud, and it is the only cloud source.
check(render.count('createInstancedEntity("Fog")') == 1
      and "if(tile.getEverVisible() && tileMeshNode != nullptr)" in render
      and "if(tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() == nullptr)" in render,
      "a new cloud source appeared or the discovered-enemy-ground cloud condition changed")
# A marked unknown tile hides its cloud so the mark stays visible at any distance.
check("tile.getFogOfWarCloud()->setVisible(!isMarked);" in render,
      "the cloud is no longer hidden over marked unknown tiles")

if failures:
    print("\n".join("FAIL: " + f for f in failures))
    sys.exit(1)
print("OK")
