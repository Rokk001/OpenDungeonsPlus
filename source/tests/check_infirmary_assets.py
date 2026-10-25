"""Inspect shipped infirmary assets, their registration and licences without compiling."""
from pathlib import Path
import importlib.util
import re
import struct
import xml.etree.ElementTree as ET

repo = Path(__file__).resolve().parents[2]


# Read one registered text asset with consistent Unicode handling.
def read(path):
    return (repo / path).read_text(encoding="utf-8")


# Verify referenced assets exist and have their own source/licence entry.
def credited(path, credits):
    asset = repo / path
    assert asset.is_file() and asset.stat().st_size > 0, "missing asset: " + path
    rows = [line for line in credits.splitlines() if path in line]
    assert rows and any("GPL" in line or "CC0" in line for line in rows), "missing licence: " + path


# Parse animation chunks with the maintained Ogre chunk reader and check actual clip lengths.
def clips():
    path = repo / "tools/blender-assets/splice_animation_chunks.py"
    spec = importlib.util.spec_from_file_location("infirmary_skeleton_chunks", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    _, chunks = module.chunks((repo / "models/InfirmaryShaman.skeleton").read_bytes())
    animations = {name: data for kind, name, data in chunks if kind == module.ANIMATION}
    expected = {"Idle", "Walk", "Chant", "RattleShake", "HerbSniff", "PotionTaste", "TripOverBucket", "Dance"}
    assert set(animations) == expected, sorted(animations)
    for name, data in animations.items():
        duration = struct.unpack_from("<f", data, data.index(b"\n", 6) + 1)[0]
        assert abs(duration - 2.0) < 1e-6, (name, duration)


# Run the floor generator's actual seam calculation in memory without rewriting any asset.
def floor_seam():
    path = repo / "tools/room-floors/generate_room_floors.py"
    spec = importlib.util.spec_from_file_location("infirmary_floor_check", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result, strength = module.build("infirmary")
    ratio = module.wrap_check(result)
    assert ratio < 2.0, ("infirmary wrap seam ratio", ratio)
    print("infirmary wrap seam ratio: %.2f" % ratio)


# Validate every asset family and reject an uninstalled logical GUI image.
def main():
    credits = read("CREDITS")
    furniture = ("InfirmaryCotSmall", "InfirmaryCotMedium", "InfirmaryCotLarge",
        "MedicineCabinet", "InstrumentTable", "WashBasin", "HerbShelf")
    for name in furniture + ("InfirmaryShaman",):
        credited("models/" + name + ".mesh", credits)
        credited("assets-src/rooms/infirmary/" + name + ".blend", credits)
    credited("models/InfirmaryShaman.skeleton", credits)
    credited("materials/scripts/InfirmaryObjects.material", credits)
    objects = read("materials/scripts/InfirmaryObjects.material")
    textures = set(re.findall(r"^\s*texture\s+(\S+)", objects, re.M))
    assert textures, "object materials have no textures"
    for texture in textures:
        credited("materials/textures/" + texture, credits)
    for path in ("materials/textures/InfirmaryFloor.png", "materials/textures/InfirmaryFloorNormal.png",
            "materials/scripts/InfirmaryFloor.material", "assets-src/gui/icons/tiles/InfirmaryButton.png"):
        credited(path, credits)
    floor = read("materials/scripts/InfirmaryFloor.material")
    assert "InfirmaryFloor.png" in floor and "InfirmaryFloorNormal.png" in floor
    tiles = read("config/tilesets.cfg")
    assert re.search(r"^\s*infirmaryRoom\s+infirmaryRoom\s*$", tiles, re.M)
    block = tiles.split("[infirmaryRoom]", 1)[1].split("[/infirmaryRoom]", 1)[0]
    assert "InfirmaryFloor" in block and "TortureFloor" not in block
    particle = read("particles/CreatureReactions.particle")
    block = particle.split("particle_system InfirmaryHealGlow", 1)[1].split("particle_system", 1)[0]
    for pattern in (r"colour\s+0\.45\s+1\.0\s+0\.55\s+0\.8", r"emission_rate\s+4\b", r"quota\s+6\b"):
        assert re.search(pattern, block), pattern
    assert not re.search(r"^\s*duration\s", block, re.M), "heal glow must stay continuous"
    assert "InfirmaryHealGlow" in credits
    for name in ("Admit", "Discharge", "Chant", "Rattle"):
        path = "sounds/Rooms/Infirmary/" + name + ".ogg"
        credited(path, credits)
        assert (repo / path).read_bytes().startswith(b"OggS"), path
        row = next(line for line in credits.splitlines() if path in line)
        assert "CC0" in row and "https://freesound.org/" in row, path
    ambience = read("config/roomAmbience.cfg")
    entries = re.findall(r"\[Effect\](.*?)\[/Effect\]", ambience, re.S)
    chants = [entry for entry in entries if re.search(r"^\s*Name\s+InfirmaryChant\s*$", entry, re.M)]
    assert len(chants) == 1, "missing or duplicate registered chant loop"
    block = chants[0]
    for pattern in (r"Match\s+InfirmaryShaman", r"Kind\s+Sound", r"Family\s+Rooms/Infirmary/Chant", r"Loop\s+yes"):
        assert re.search(pattern, block), pattern
    clips()
    bounds = read("source/gamemap/RoomObjectBounds.h")
    for name in furniture:
        assert re.search(r'\{"' + name + r'"\s*,', bounds), "missing measured mesh bounds: " + name
    assert re.search(r'if\(name\.compare\(0, 12, "InfirmaryCot"\) == 0\)\s*return \{1\.0f, 1\.0f\};', bounds)
    shaman = read("source/entities/InfirmaryShamanEntity.cpp")
    assert 'setWalkPath("Walk", "Idle", true, true, path, false, true)' in shaman
    assert 'setAnimationState("Idle", true)' in shaman
    generator = read("tools/room-floors/generate_room_floors.py")
    assert "'infirmary': {'field': infirmary_field" in generator
    assert "'infirmary': (48.0, 0.7)" in generator
    seam_block = generator.split("SEAM_CHECK_ROOMS =", 1)[1].split(")", 1)[0]
    assert "'infirmary'" in seam_block
    floor_seam()
    imageset = ET.parse(repo / "gui/ODIcons.imageset").getroot()
    image = imageset.find("Image[@name='InfirmaryButton']")
    assert image is not None, "missing logical atlas image: OpenDungeonsIcons/InfirmaryButton"
    assert int(image.get("width")) == 128 and int(image.get("height")) == 128
    atlas = (repo / "gui" / imageset.get("imagefile")).read_bytes()
    assert atlas[:8] == b"\x89PNG\r\n\x1a\n", "icon atlas must be a PNG"
    width, height = struct.unpack_from(">II", atlas, 16)
    assert int(image.get("xPos")) + 128 <= width and int(image.get("yPos")) + 128 <= height
    print("infirmary assets: ok")


if __name__ == "__main__":
    main()
