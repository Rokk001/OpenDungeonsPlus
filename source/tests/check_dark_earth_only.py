"""Static check that the whole map uses only the single dark earth material.

The earth walls once got their own warmer, lighter DirtWall material next to the dark Dirt material
of the ground, so two earth looks existed. Run from any directory; it does not start a game.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
failures = []


# Record a failed condition and continue with the other checks.
def check(condition, message):
    if not condition:
        failures.append(message)


tilesets = (root / "config/tilesets.cfg").read_text(encoding="utf-8")
earth_materials = set()
for block in ("dirtGround", "dirtFull"):
    body = tilesets.split("[" + block + "]", 1)[1].split("[/" + block + "]", 1)[0]
    earth_materials.update(m for _, m in re.findall(r"(\S+\.mesh)\s+(\w+)\s+[0-9.-]+\s+[0-9.-]+\s+[0-9.-]+", body))
check(earth_materials == {"Dirt"}, "earth tiles use materials other than Dirt: %s" % sorted(earth_materials))

# No light earth variant may remain in materials, textures, configuration or code.
check("DirtWall" not in (root / "materials/scripts/Dirt.material").read_text(encoding="utf-8"),
      "the light earth material is still defined")
for name in ("DirtWall.png", "DirtWallNormal.png"):
    check(not (root / "materials/textures" / name).exists(), name + " still exists")
for folder in ("config", "materials/scripts", "source/render", "source/entities", "shaders"):
    for path in (root / folder).rglob("*"):
        if path.suffix in (".cfg", ".material", ".cpp", ".h", ".frag", ".vert", ".glsl"):
            check("DirtWall" not in path.read_text(encoding="utf-8", errors="ignore"), "DirtWall referenced in " + str(path))

# The violet dig mark stays unchanged.
tile = (root / "source/entities/Tile.cpp").read_text(encoding="utf-8")
check("DIG_MARK_COLOUR(0.65f, 0.45f, 1.0f, 0.5f)" in tile, "the dig mark colour changed")

# The single earth texture is dark.
try:
    from PIL import Image, ImageStat
    mean = ImageStat.Stat(Image.open(root / "materials/textures/Dirt.png").convert("L")).mean[0]
    check(mean < 45, "Dirt.png is not dark: mean luminance %.1f" % mean)
except ImportError:
    pass

if failures:
    print("\n".join(failures))
    sys.exit(1)
print("OK: only the dark earth material is used")
