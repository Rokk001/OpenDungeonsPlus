#!/usr/bin/env python3
"""Check that the menu scene finds every texture, material and mesh it names.

Textures: every texture named by the material and particle scripts must be found by the engine.
Materials and meshes: every mesh named by the menu scene description must exist under models/, every
material or skeleton named inside the menu meshes must be defined in materials/scripts/*.material (or exist
under models/), and every material used by the menu particle effects must be defined as well.
Lighting off: a material with "lighting off" that has no texture can only take its colour from the
mesh vertex colours. The fixed pipeline otherwise falls back to white, so every menu mesh part that uses
such a material must carry a vertex colour element (Ogre semantic VES_DIFFUSE, read from the binary mesh).

The engine registers each folder of the Graphics section in cmake/config/resources.cfg.in
non-recursively (ResourceManager::setupOgreResources passes recursive=false), so a texture name
is resolvable only if the file lies directly in one of the listed folders. A name with a folder
prefix such as "menu/Name.png" is never found and the layer renders blank.
"""
from pathlib import Path
import re
import struct


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


# Return the set of material names defined by all material scripts (also those derived from a parent).
def defined_materials(root):
    names = set()
    pattern = re.compile(r"^\s*material\s+([^\s:{]+)")
    for script in (root / "materials/scripts").rglob("*.material"):
        for line in script.read_text(encoding="utf-8", errors="replace").splitlines():
            match = pattern.match(line)
            if match:
                names.add(match.group(1))
    return names


# Return the mesh names of every AddEntity command of the menu scene description.
def scene_meshes(root):
    meshes = []
    for line in (root / "config/mainmenuscene.cfg").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "AddEntity":
            meshes.append(parts[2])
    return meshes


# Return the material and skeleton names stored as text inside a binary mesh file.
def mesh_references(mesh_file):
    return sorted(set(name.decode("ascii") for name in re.findall(rb"Menu[A-Za-z0-9_]*(?:\.skeleton)?", mesh_file.read_bytes())))


# Return (chunk id, payload start, chunk end) for each chunk of an Ogre mesh file between start and end.
def mesh_chunks(data, start, end):
    chunks = []
    while start + 6 <= end:
        chunk_id, length = struct.unpack_from("<HI", data, start)
        chunks.append((chunk_id, start + 6, start + length))
        start += length
    return chunks


# Return True when a geometry chunk's vertex declaration contains a vertex colour element (semantic 5).
def geometry_has_vertex_colour(data, geometry_start, geometry_end):
    for chunk_id, start, end in mesh_chunks(data, geometry_start + 4, geometry_end):
        if chunk_id == 0x5100:
            for element_id, element_start, element_end in mesh_chunks(data, start, end):
                if element_id == 0x5110 and struct.unpack_from("<5H", data, element_start)[2] == 5:
                    return True
    return False


# Return {material name: True when every mesh part with it has vertex colours} of a binary v1.100 mesh.
# Layout: header string, mesh chunk 0x3000 (bool, then shared geometry 0x5000 and submeshes 0x4000);
# a submesh holds material string, shared-vertices bool, index count, 32-bit bool, indices, own geometry.
def mesh_vertex_colours(mesh_file):
    data = mesh_file.read_bytes()
    start = data.index(b"\n", 2) + 1
    result = {}
    for chunk_id, mesh_start, mesh_end in mesh_chunks(data, start, len(data)):
        if chunk_id != 0x3000:
            continue
        shared = False
        for sub_id, sub_start, sub_end in mesh_chunks(data, mesh_start + 1, mesh_end):
            if sub_id == 0x5000:
                shared = geometry_has_vertex_colour(data, sub_start, sub_end)
            elif sub_id == 0x4000:
                name_end = data.index(b"\n", sub_start)
                material = data[sub_start:name_end].decode("ascii")
                use_shared = data[name_end + 1] != 0
                count, = struct.unpack_from("<I", data, name_end + 2)
                index_size = 4 if data[name_end + 6] else 2
                geometry = name_end + 7 + count * index_size
                coloured = shared
                if not use_shared:
                    coloured = False
                    for geo_id, geo_start, geo_end in mesh_chunks(data, geometry, sub_end):
                        if geo_id == 0x5000:
                            coloured = geometry_has_vertex_colour(data, geo_start, geo_end)
                            break
                result[material] = result.get(material, True) and coloured
    return result


# Return the names of materials whose block says "lighting off" and names no texture.
def unlit_untextured_materials(root):
    names = set()
    for script in (root / "materials/scripts").rglob("*.material"):
        text = "\n".join(l for l in script.read_text(encoding="utf-8", errors="replace").splitlines()
                         if not l.strip().startswith("//"))
        for match in re.finditer(r"\bmaterial\s+([^\s:{]+)[^{]*\{", text):
            depth, end = 1, match.end()
            while depth and end < len(text):
                depth += (text[end] == "{") - (text[end] == "}")
                end += 1
            block = text[match.end():end]
            if re.search(r"\blighting\s+off\b", block) and not re.search(r"\btexture\s+\S", block):
                names.add(match.group(1))
    return names


# Return the material names that the menu particle script uses.
def particle_materials(root):
    pattern = re.compile(r"^\s*material\s+(\S+)")
    names = set()
    for line in (root / "particles/MenuScene.particle").read_text(encoding="utf-8", errors="replace").splitlines():
        match = pattern.match(line)
        if match:
            names.add(match.group(1))
    return names


# Return the list of missing menu scene materials, meshes and skeletons as readable lines.
def missing_models_and_materials(root):
    problems = []
    defined = defined_materials(root)
    unlit = unlit_untextured_materials(root)
    models = root / "models"
    for mesh in scene_meshes(root):
        mesh_file = models / mesh
        if not mesh_file.is_file():
            problems.append(f"config/mainmenuscene.cfg: mesh {mesh} not found under models/")
            continue
        for material, coloured in sorted(mesh_vertex_colours(mesh_file).items()):
            if material in unlit and not coloured:
                problems.append(f"models/{mesh}: material {material} is lighting off without texture and the mesh part has no vertex colours (renders white)")
        for name in mesh_references(mesh_file):
            if name.endswith(".skeleton"):
                if not (models / name).is_file():
                    problems.append(f"models/{mesh}: skeleton {name} not found under models/")
            elif name not in defined and name + ".mesh" != mesh:
                problems.append(f"models/{mesh}: material {name} is not defined in materials/scripts")
    for name in sorted(particle_materials(root)):
        if name not in defined:
            problems.append(f"particles/MenuScene.particle: material {name} is not defined in materials/scripts")
    return problems


# Fail when a menu scene texture, material, mesh or skeleton cannot be resolved.
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
    problems = missing_models_and_materials(root)
    assert not problems, "menu scene materials or meshes missing:\n  " + "\n  ".join(problems)
    print(f"OK: {menu_count} menu scene texture references resolve through resources.cfg.in; "
          f"{len(scene_meshes(root))} scene meshes with their materials and skeletons are present")


if __name__ == "__main__":
    main()
