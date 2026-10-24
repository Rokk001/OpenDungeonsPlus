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

print("World background material and 1024x1024 texture: OK")
