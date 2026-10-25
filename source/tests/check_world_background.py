"""Check that the in-game background uses its shipped rock texture."""
from pathlib import Path
import re

from PIL import Image

repo = Path(__file__).resolve().parents[2]
material = (repo / "materials/scripts/Background.material").read_text()
texture = repo / "materials/textures/WorldRock.png"

assert re.search(r"\btexture\s+WorldRock\.png\b", material), "Background must use WorldRock.png"
assert re.search(r"\btex_address_mode\s+wrap\b", material), "Background texture must wrap"
assert texture.is_file(), "WorldRock.png is missing"
with Image.open(texture) as image:
    assert image.format == "PNG" and image.size == (1024, 1024), "WorldRock.png must be a 1024x1024 PNG"

assert re.search(r"\bdepth_write\s+off\b", material), "Background must not obscure world geometry"

# An opaque seam-covering plane must end at the map edges, leaving the background visible outside.
renderer = (repo / "source/render/RenderManager.cpp").read_text()
initialization = renderer.split("void RenderManager::initGameRenderer(GameMap* gameMap)", 1)[1]
initialization = initialization.split("void RenderManager::", 1)[0]
for axis in ("X", "Y"):
    assert re.search(
        rf"const Ogre::Real groundSize{axis} = static_cast<Ogre::Real>\(gameMap->getMapSize{axis}\(\)\);",
        initialization,
    ), f"Ground underlay must use the map size on {axis}, without a margin outside the map"
    assert f"(gameMap->getMapSize{axis}() - 1) * 0.5f" in initialization, \
        f"Ground underlay must be centered on the tile centers on {axis}"
assert "groundSizeX, groundSizeY," in initialization, "Ground plane must use its bounded dimensions"
assert re.search(r"GROUND_UNDERLAY_HEIGHT\s*=\s*-4\.0f", renderer), \
    "Seam underlay must remain below the arena pit floor"

print("World background texture, material and unobstructed map-edge coverage: OK")
