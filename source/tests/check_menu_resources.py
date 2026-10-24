#!/usr/bin/env python3
"""Check that every texture named by the material and particle scripts can be found by the engine.

The engine registers each folder of the Graphics section in cmake/config/resources.cfg.in
non-recursively (ResourceManager::setupOgreResources passes recursive=false), so a texture name
is resolvable only if the file lies directly in one of the listed folders. A name with a folder
prefix such as "menu/Name.png" is never found and the layer renders blank.
"""
from pathlib import Path
import re


# Return the folders of the Graphics section of the resource list, relative to the repository.
def graphics_folders(root):
    folders = []
    in_graphics = False
    for line in (root / "cmake/config/resources.cfg.in").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("["):
            in_graphics = line == "[Graphics]"
        elif in_graphics and line.startswith("FileSystem="):
            value = line.split("=", 1)[1]
            if not value.startswith("@"):
                folders.append(root / value)
    return folders


# Collect (script, line number, texture name) for every texture reference in the scripts.
def texture_references(root):
    pattern = re.compile(r"^\s*(?:.*\{\s*)?(?:texture|cubic_texture)\s+([^\s}]+\.(?:png|jpg|jpeg|tga|dds|bmp))", re.I)
    references = []
    scripts = sorted((root / "materials/scripts").rglob("*.material")) + sorted((root / "particles").rglob("*.particle"))
    for script in scripts:
        for number, line in enumerate(script.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            if line.strip().startswith("//"):
                continue
            match = pattern.match(line)
            if match:
                references.append((script, number, match.group(1)))
    return references


# Fail when a menu scene texture cannot be resolved; other unresolved names are listed as well.
def main():
    root = Path(__file__).resolve().parents[2]
    folders = graphics_folders(root)
    assert root / "materials/textures/menu" in folders, "menu textures folder must be listed in resources.cfg.in"
    missing = []
    menu_count = 0
    for script, number, name in texture_references(root):
        resolved = any((folder / name).is_file() for folder in folders)
        if script.name.startswith("MenuScene"):
            menu_count += 1
        if not resolved and script.name.startswith("MenuScene"):
            missing.append(f"{script.relative_to(root)}:{number}: {name}")
    assert menu_count > 0, "no menu scene texture references found"
    assert not missing, "menu scene textures not resolvable by the engine:\n  " + "\n  ".join(missing)
    print(f"OK: {menu_count} menu scene texture references resolve through resources.cfg.in")


if __name__ == "__main__":
    main()
