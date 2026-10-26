"""Check that the in-game background uses its shipped rock texture."""
from pathlib import Path
import re

from PIL import Image, ImageStat

repo = Path(__file__).resolve().parents[2]
material = (repo / "materials/scripts/Background.material").read_text()
texture = repo / "materials/textures/WorldRock.png"

assert re.search(r"\btexture\s+WorldRock\.png\b", material), "Background must use WorldRock.png"
assert re.search(r"\btex_address_mode\s+wrap\b", material), "Background texture must wrap"
# Keep the background dark independently of ambient light and nearby world lights.
for component in ("ambient", "diffuse", "specular"):
    assert re.search(rf"\b{component}\s+0\.0\s+0\.0\s+0\.0\b", material), \
        f"Background {component} must not add world lighting"
assert re.search(r"\bemissive\s+0\.25\s+0\.25\s+0\.25\s+1\.0\b", material), \
    "Background must retain the dark earth tint at quarter emission"
# Eight by five repeats give square 240px patches at the reference 1920x1200 viewport.
assert re.search(r"\bscale\s+0\.125\s+0\.2\b", material), \
    "Background rock structure must not be minified into the old 26-by-15 repeats"
assert texture.is_file(), "WorldRock.png is missing"
with Image.open(texture) as image:
    assert image.format == "PNG" and image.size == (1024, 1024), "WorldRock.png must be a 1024x1024 PNG"
    # Broad rock relief must survive tile-sized minification instead of averaging to flat brown.
    rock = image.convert("L")
    coarse_rock = rock.resize((32, 32), Image.Resampling.BOX)
    assert ImageStat.Stat(coarse_rock).stddev[0] >= ImageStat.Stat(rock).stddev[0] * 0.25, \
        "WorldRock.png must retain broad rock contrast when fine gravel is filtered out"

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
