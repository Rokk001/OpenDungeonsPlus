"""Source check: earth tiles at the map edge must link to the earth border, so the edge shows no step. No compile."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
game_map = (ROOT / "source/gamemap/GameMap.cpp").read_text(encoding="utf-8")
render = (ROOT / "source/render/RenderManager.cpp").read_text(encoding="utf-8")
tilesets = (ROOT / "config/tilesets.cfg").read_text(encoding="utf-8")

# The border around the map is built from the fully linked (1111) dirtFull meshes.
assert "getTileValues(TileVisual::dirtFull).at(15)" in game_map
assert "createWorldBorder(gameMap);" in render

# Cause: a missing neighbour used to be skipped, so edge earth tiles got the unlinked edge shape.
start = game_map.index("int GameMap::computeTileSetIndex(")
body = game_map[start:game_map.index("\n}\n", start)]
assert "linksToBorder" in body
assert re.search(r"visual\s*==\s*TileVisual::dirtFull", body)
m = re.search(r"if\(t == nullptr\)\s*\{\s*if\(linksToBorder\)\s*index \|= \(1 << i\);\s*continue;\s*\}", body)
assert m, "outside-map neighbour must set the link bit for earth"

# The earth tileset must have a flat 1111 shape that matches what edge tiles now use.
assert re.search(r"\[dirtFull\].*?1111\s*\[oneOf\].*?Dirt_fl_1111", tilesets, re.S)
print("OK")
