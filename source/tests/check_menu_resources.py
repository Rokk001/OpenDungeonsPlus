#!/usr/bin/env python3
"""Check that the menu scene finds every texture, material and mesh it names.

Textures: every texture named by the material and particle scripts must be found by the engine.
Materials and meshes: every mesh named by the menu scene description must exist under models/, every
material or skeleton named inside the menu meshes must be defined in materials/scripts/*.material (or exist
under models/), and every material used by the menu particle effects must be defined as well.
Generated shared geometry must retain every referenced vertex without truncated index buffers.
Lighting off: a material with "lighting off" that has no texture can only take its colour from the
mesh vertex colours unless it supplies both explicit shader programs. The fixed pipeline otherwise falls
back to white, so every fixed-function menu mesh part that uses such a material must carry a vertex
colour element (Ogre semantic VES_DIFFUSE, read from the binary mesh).

The engine registers each folder of the Graphics section in cmake/config/resources.cfg.in
non-recursively (ResourceManager::setupOgreResources passes recursive=false), so a texture name
is resolvable only if the file lies directly in one of the listed folders. A name with a folder
prefix such as "menu/Name.png" is never found and the layer renders blank.
"""
from pathlib import Path
import math
import re
import struct

from PIL import Image


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


# Validate each index against its vertex buffer and detect truncated indices in generated shared geometry.
def mesh_index_problems(mesh_file):
    data = mesh_file.read_bytes()
    problems = []
    start = data.index(b"\n", 2) + 1
    for chunk_id, mesh_start, mesh_end in mesh_chunks(data, start, len(data)):
        if chunk_id != 0x3000:
            continue
        shared_count = 0
        shared_used = set()
        has_shared_submesh = False
        for sub_id, sub_start, sub_end in mesh_chunks(data, mesh_start + 1, mesh_end):
            if sub_id == 0x5000:
                shared_count, = struct.unpack_from("<I", data, sub_start)
            elif sub_id == 0x4000:
                name_end = data.index(b"\n", sub_start)
                material = data[sub_start:name_end].decode("ascii")
                use_shared = data[name_end + 1] != 0
                count, = struct.unpack_from("<I", data, name_end + 2)
                index_size = 4 if data[name_end + 6] else 2
                index_start = name_end + 7
                index_end = index_start + count * index_size
                used = {index[0] for index in struct.iter_unpack("<I" if index_size == 4 else "<H", data[index_start:index_end])}
                vertex_count = shared_count
                if use_shared:
                    has_shared_submesh = True
                    shared_used.update(used)
                else:
                    for geometry_id, geometry_start, geometry_end in mesh_chunks(data, index_end, sub_end):
                        if geometry_id == 0x5000:
                            vertex_count, = struct.unpack_from("<I", data, geometry_start)
                            break
                if used and max(used) >= vertex_count:
                    problems.append(f"models/{mesh_file.name}: {material} index exceeds its vertex buffer")
        # The menu exporter appends only referenced vertices; wrapped 16-bit indices orphan the high vertices.
        if has_shared_submesh and len(shared_used) != shared_count:
            problems.append(f"models/{mesh_file.name}: {shared_count - len(shared_used)} shared vertices are unreferenced; check index width before conversion")
    return problems


# Return fixed-function materials whose block says "lighting off" and names no texture.
# pattern selects the material scripts to scan (default: all of them).
def unlit_untextured_materials(root, pattern="*.material"):
    names = set()
    for script in (root / "materials/scripts").rglob(pattern):
        text = "\n".join(l for l in script.read_text(encoding="utf-8", errors="replace").splitlines()
                         if not l.strip().startswith("//"))
        for match in re.finditer(r"\bmaterial\s+([^\s:{]+)[^{]*\{", text):
            depth, end = 1, match.end()
            while depth and end < len(text):
                depth += (text[end] == "{") - (text[end] == "}")
                end += 1
            block = text[match.end():end]
            if (re.search(r"\blighting\s+off\b", block) and not re.search(r"\btexture\s+\S", block)
                    and not (re.search(r"\bvertex_program_ref\s+\S+", block)
                             and re.search(r"\bfragment_program_ref\s+\S+", block))):
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
        problems.extend(mesh_index_problems(mesh_file))
        for material, coloured in sorted(mesh_vertex_colours(mesh_file).items()):
            if material in unlit and not coloured:
                problems.append(f"models/{mesh}: material {material} is lighting off without texture and the mesh part has no vertex colours (renders white)")
        for name in mesh_references(mesh_file):
            if name.endswith(".skeleton"):
                if not (models / name).is_file():
                    problems.append(f"models/{mesh}: skeleton {name} not found under models/")
            elif name not in defined and name + ".mesh" != mesh:
                problems.append(f"models/{mesh}: material {name} is not defined in materials/scripts")
    # A material of MenuScene.material that no menu mesh uses has no vertex colour information, so it
    # counts as without vertex colours and turns red when it is lighting off without a texture.
    used = set()
    for mesh in scene_meshes(root):
        if (models / mesh).is_file():
            used.update(mesh_vertex_colours(models / mesh).keys())
    for material in sorted(unlit_untextured_materials(root, "MenuScene.material")):
        if material not in used:
            problems.append(f"materials/scripts/MenuScene.material: material {material} is lighting off without texture and is not used by a mesh with vertex colours (renders red)")
    for name in sorted(particle_materials(root)):
        if name not in defined:
            problems.append(f"particles/MenuScene.particle: material {name} is not defined in materials/scripts")
    return problems


# Check that self-lit atmosphere bypasses fixed lighting and that its shader files are resolvable.
def check_sky_programs(root, folders):
    text = (root / "materials/scripts/MenuScene.material").read_text(encoding="utf-8")
    for program, filename in (("MenuSkyVertex", "MenuSky.vert"), ("MenuSkyFragment", "MenuSky.frag")):
        assert re.search(r"\b(?:vertex|fragment)_program\s+" + program + r"\s+glsl\s*\{[^}]*\bsource\s+" + re.escape(filename), text), program + " must name its shader source"
        assert any((folder / filename).is_file() for folder in folders), filename + " must resolve through Graphics resources"
    for name, kind in (("MenuSky", 0), ("MenuHorizonGlow", 1), ("MenuHorizonDark", 1), ("MenuCloud", 2), ("MenuBloodMoon", 3)):
        match = re.search(r"\bmaterial\s+" + name + r"\s*\{", text)
        assert match, name + " must have a standalone atmosphere pass"
        depth, end = 1, match.end()
        while depth and end < len(text):
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        block = text[match.end():end]
        for requirement in (r"\breceive_shadows\s+off", r"\blighting\s+off", r"\bvertex_program_ref\s+MenuSkyVertex", r"\bfragment_program_ref\s+MenuSkyFragment", r"\bparam_named\s+atmosphereKind\s+int\s+" + str(kind) + r"\b"):
            assert re.search(requirement, block), name + " lacks atmosphere setting " + requirement
    shader = (root / "shaders/MenuSky.frag").read_text(encoding="utf-8")
    assert "cloudDensity(point)" in shader and "skyPosition.z - 12.0" in shader, "atmosphere needs cloud structure and horizon height fade"
    assert "1.0 / 2.2" in shader, "linear atmosphere colours need their display transfer"


# Read named script blocks while retaining nested emitter, affector and material settings.
def script_blocks(text, declaration):
    blocks = {}
    for match in re.finditer(r"(?m)^" + declaration + r"\s+([^\s:{]+)[^{]*\{", text):
        depth, end = 1, match.end()
        while depth and end < len(text):
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        assert depth == 0, "unclosed " + declaration + " " + match.group(1)
        blocks[match.group(1)] = text[match.end():end - 1]
    return blocks


# Keep textured menu surfaces and inherited colour overrides in their normal-mapped lighting pass.
def check_menu_surface_passes(root):
    text = (root / "materials/scripts/MenuScene.material").read_text(encoding="utf-8")
    materials = script_blocks(text, "material")
    bases = {
        "MenuStone": "MenuFortressStoneNormal.png", "MenuIron": "MenuRustIronNormal.png",
        "MenuCloth": "MenuTornClothNormal.png", "MenuWetStone": "MenuWetPavingNormal.png",
        "MenuDemonStone": "MenuDemonStoneNormal.png",
    }
    parents = dict(re.findall(r"(?m)^material\s+(\w+)\s*:\s*(\w+)", text))
    for name, normal in bases.items():
        block = materials[name]
        assert re.findall(r"\bpass\s+(\w+)\s*\{", block) == ["lighting"], name + " must not overwrite its normal map with a second surface pass"
        assert normal in block and "normal_map tangent_space" in block, name + " must retain its authored tangent-space normal map"
    for name, parent in parents.items():
        if parent in bases:
            assert re.findall(r"\bpass\s+(\w+)\s*\{", materials[name]) == ["lighting"], name + " must override the inherited normal-mapped pass"
    print("OK: menu surface colours and normal maps share one lighting pass, including inherited overrides")


# Validate every configured menu effect and prevent dense bowl smoke from replacing sparks.
def check_menu_particles(root, folders):
    systems = script_blocks((root / "particles/MenuScene.particle").read_text(encoding="utf-8"), "particle_system")
    config = (root / "config/mainmenuscene.cfg").read_text(encoding="utf-8")
    configured = re.findall(r"(?m)^AddParticleEffect\s+(\S+)\s+(\S+)", config)
    materials = {}
    for path in (root / "materials/scripts").rglob("*.material"):
        materials.update(script_blocks(path.read_text(encoding="utf-8", errors="replace"), "material"))
    for name in sorted({system for entity, system in configured}):
        assert name in systems, name + " has no particle definition"
        block = systems[name]
        material_name = re.search(r"\bmaterial\s+(\S+)", block).group(1)
        assert material_name in materials, name + " has no material " + material_name
        material = materials[material_name]
        for setting in (r"\blighting\s+off", r"\bdepth_write\s+off", r"\bscene_blend\s+(?:add|alpha_blend|src_alpha\s+one)\b"):
            assert re.search(setting, material), name + " lacks transparent particle setting " + setting
        textures = re.findall(r"\btexture\s+(\S+)", material)
        assert textures, name + " needs a textured sprite"
        for texture in textures:
            assert any((folder / texture).is_file() for folder in folders), name + " cannot resolve " + texture
        for setting in ("particle_width", "particle_height", "quota", "emission_rate", "time_to_live_min", "time_to_live_max"):
            assert float(re.search(r"\b" + setting + r"\s+([0-9.]+)", block).group(1)) > 0, name + " has invalid " + setting
        for colour in re.findall(r"\bcolour_range_(?:start|end)\s+([^\n]+)", block):
            assert len(colour.split()) == 4 and 0 <= float(colour.split()[3]) <= 1, name + " has invalid particle alpha"
    smoke_texture = next(folder / "RoomAmbSmoke.png" for folder in folders if (folder / "RoomAmbSmoke.png").is_file())
    with Image.open(smoke_texture) as image:
        assert "A" in image.getbands(), "smoke must keep its transparent texture mask"
        alpha = image.getchannel("A")
        assert alpha.getextrema()[0] == 0 and alpha.getextrema()[1] > 0, "smoke mask must contain transparent and visible pixels"
        assert alpha.getpixel((0, image.height // 2)) == 0, "smoke texture edge must fade into transparency"
    smoke = systems["MenuBrazierSmoke"]
    quota = float(re.search(r"\bquota\s+([0-9.]+)", smoke).group(1))
    rate = float(re.search(r"\bemission_rate\s+([0-9.]+)", smoke).group(1))
    lifetime = float(re.search(r"\btime_to_live_max\s+([0-9.]+)", smoke).group(1))
    assert quota <= 6 and rate * lifetime <= 6, "bowl smoke must remain sparse instead of stacking opaque puffs"
    assert all(float(colour.split()[3]) <= 0.18 for colour in re.findall(r"\bcolour_range_(?:start|end)\s+([^\n]+)", smoke)), "bowl smoke must retain a thin alpha profile"
    assert float(re.search(r"\bparticle_height\s+([0-9.]+)", smoke).group(1)) <= 2.5, "bowl smoke must not start as a facade-sized billboard"
    fire_bowls = {entity for entity, system in configured if system == "MenuBrazierFire"}
    ember_bowls = {entity for entity, system in configured if system == "MenuBrazierEmbers"}
    assert len(fire_bowls) == 4 and ember_bowls == fire_bowls, "all four bowls need separate small rising sparks"
    assert "material CombatSparks" in systems["MenuBrazierEmbers"], "bowl embers must use the existing additive spark sprite"
    assert "material RoomAmbGlow" in systems["MenuSpireGlow"], "spire light needs alpha-weighted additive glow instead of opaque smoke"
    assert "scene_blend src_alpha one" in materials["RoomAmbGlow"], "spire glow must weight its soft texture by alpha"
    print(f"OK: {len(set(system for entity, system in configured))} configured menu particle systems use transparent textured sprites; sparse bowl smoke and rising sparks")


# Keep the authored light falloff/exposure and local ambient loading separate from the game lighting.
def check_menu_lighting(root):
    config = (root / "config/mainmenuscene.cfg").read_text(encoding="utf-8")
    preview = (root / "tools/blender-assets/menu_scene_assembly.py").read_text(encoding="utf-8")
    exposure = float(re.search(r"view_settings\.exposure = ([0-9.]+)", preview).group(1))
    gain = 2 ** exposure
    world = preview.split('world = bpy.data.worlds.new("Black exterior")', 1)[1].split("scene.world = world", 1)[0]
    colour = [float(value) for value in re.search(r'inputs\["Color"\]\.default_value = \(([^)]+)\)', world).group(1).split(",")[:3]]
    strength = float(re.search(r'inputs\["Strength"\]\.default_value = ([0-9.]+)', world).group(1))
    ambient_block = config.split("[MenuLighting]", 1)[1].split("[/MenuLighting]", 1)[0]
    ambient = [float(value) for value in re.search(r"(?m)^Ambient\s+([^\n]+)", ambient_block).group(1).split()]
    assert len(ambient) == 3 and all(math.isclose(actual, value * strength * gain, rel_tol=1e-10)
                                    for actual, value in zip(ambient, colour)), "menu ambient must retain the authored warm sky and exposure"
    lights = {words[1]: [float(value) for value in words[2:]] for words in
              (line.split() for line in config.splitlines()) if words and words[0] == "AddPointLight"}
    assert len(lights) == 48, "the existing menu lights must remain, without substitute lights"
    for name, values in lights.items():
        assert len(values) == 13 and all(math.isfinite(value) for value in values), name + " has invalid light values"
        assert values[9] > 0 and values[10] == values[11] == 0 and values[12] > 0, name + " must follow the authored inverse-square falloff"
    # Original warm bowl, gate and green spire samples cover both colour families and distinct ranges.
    authored = {
        "LeftFire": ((1.7, 0.48, 0.065), (0.51, 0.144, 0.0195), 19, 0.045, 0.028, 26),
        "GateFire": ((1, 0.19, 0.018), (0.30, 0.057, 0.0054), 14, 0.065, 0.055, 18),
        "SpireLight": ((0.025, 0.95, 0.07), (0.0075, 0.285, 0.021), 35, 0.035, 0.012, 28),
    }
    for name, (diffuse, specular, light_range, linear, quadratic, cutoff) in authored.items():
        actual = lights[name]
        reference = light_range / 2
        attenuation = 1 + linear * reference + quadratic * reference ** 2
        assert actual[9] == cutoff, name + " changed its tuned range"
        assert all(math.isclose(value, original * gain, rel_tol=1e-10)
                   for value, original in zip(actual[3:9], diffuse + specular)), name + " changed its authored colour or exposure"
        for distance in (reference / 4, reference, reference * 1.5):
            for channel, original in enumerate(diffuse):
                expected = original * gain * reference ** 2 / (attenuation * distance ** 2)
                received = actual[3 + channel] / (actual[12] * distance ** 2)
                assert math.isclose(received, expected, rel_tol=1e-10), name + " lost the calibrated near/far light profile"
    scene = (root / "source/renderscene/RenderSceneMenu.cpp").read_text(encoding="utf-8")
    parser = scene.split("void RenderSceneMenu::readSceneMenu", 1)[1]
    assert '"[MenuLighting]"' in scene and '"[/MenuLighting]"' in scene and "if(lightingSection)" in parser, "menu ambient section must be parsed outside native groups"
    assert "command >> kind >> ambient.r >> ambient.g >> ambient.b" in parser and "mMenuAmbient = ambient;" in parser, "configured ambient must reach the menu scene"
    reset = scene.split("void RenderSceneMenu::resetMenu", 1)[1].split("void RenderSceneMenu::freeMenu", 1)[0]
    assert "mSavedAmbient = renderManager.getSceneManager()->getAmbientLight();" in reset and "setAmbientLight(mMenuAmbient)" in reset, "menu must save world ambient and apply its configured fill"
    release = scene.split("void RenderSceneMenu::freeMenu", 1)[1].split("void RenderSceneMenu::updateMenu", 1)[0]
    assert "setAmbientLight(mSavedAmbient)" in release, "leaving the menu must restore game ambient"
    print("OK: 48 authored menu lights retain calibrated falloff/exposure; menu ambient loads, applies and restores")


# Fail when a menu scene texture, material, mesh or skeleton cannot be resolved.
def main():
    root = Path(__file__).resolve().parents[2]
    folders = graphics_folders(root)
    assert root / "materials/textures/menu" in folders, "menu textures folder must be listed in resources.cfg.in"
    check_sky_programs(root, folders)
    check_menu_surface_passes(root)
    check_menu_particles(root, folders)
    check_menu_lighting(root)
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
