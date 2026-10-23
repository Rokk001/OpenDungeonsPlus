"""Assemble the existing menu models from their configuration and render an Eevee overview."""
from pathlib import Path
import argparse
import json
import math
import random
import re
import shutil
import sys

import bpy
from mathutils import Quaternion


# The authored families remain complete while their placed ruins use separate exported variants.
SOURCE_FAMILIES = {
    "MenuGate", "MenuWallSegment", "MenuTower", "MenuStatue", "MenuBrazier", "MenuBanner",
    "MenuArches", "MenuCrystalSpire", "MenuCourtyard", "MenuBackdrop", "MenuCampaignHall",
    "MenuMapTable", "MenuSideCave"
}
EXPECTED_CONFIGURED_ENTITY_COUNT = 31


# Return one existing material definition, including its inherited scalar properties.
def material_values(text, name):
    match = re.search(r"\bmaterial\s+" + re.escape(name) + r"\s*(?::\s*([\w/]+))?\s*\{", text)
    if match is None:
        raise ValueError("Missing menu material: " + name)
    start = match.end()
    depth = 1
    end = start
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    block = text[start:end - 1]
    parent = match.group(1)
    values = material_values(text, parent) if parent and parent.startswith("Menu") else {}
    values = dict(values)
    for field in ("diffuse", "ambient", "emissive", "specular"):
        field_match = re.search(r"\b" + field + r"[ \t]+([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?(?:[ \t]+[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?){2,4})", block)
        if field_match:
            values[field] = tuple(float(value) for value in field_match.group(1).split())
    if re.search(r"\blighting\s+off\b", block):
        values["unlit"] = True
    values["name"] = name
    if name == "MenuStone":
        values["normal"] = "MenuStoneNormal.png"
        values["texture"] = "MenuStone.png"
    elif name == "MenuCampaignMap":
        values["texture"] = "MenuCampaignMap.png"
    # Child stone materials retain their parent's texture and the source mesh's varied UVs.
    return values


# Load each existing texture once and pack it for the portable assembly file.
def texture_image(repo, filename, images):
    if filename not in images:
        image = bpy.data.images.load(str(repo / "materials/textures/menu" / filename), check_existing=True)
        image.colorspace_settings.name = "Non-Color" if filename.endswith("Normal.png") else "sRGB"
        image.pack()
        images[filename] = image
    return images[filename]



# Translate inherited dark surfaces using their exported UVs, without ambient self-lighting.
def configure_material(material, values, repo, images):
    material.use_nodes = True
    nodes=material.node_tree.nodes
    nodes.clear()
    links=material.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial")
    name=values["name"]
    colour=tuple(values.get("diffuse",values.get("ambient",tuple(material.diffuse_color[:3])))[:3])
    rgb=nodes.new("ShaderNodeRGB")
    rgb.outputs[0].default_value=(*colour,1)
    base=rgb.outputs[0]
    if values.get("texture"):
        image=nodes.new("ShaderNodeTexImage")
        image.image=texture_image(repo,values["texture"],images)
        image.extension="EXTEND" if name=="MenuCampaignMap" else "REPEAT"
        multiply=nodes.new("ShaderNodeMixRGB")
        multiply.blend_type="MULTIPLY"
        multiply.inputs[0].default_value=1
        links.new(image.outputs["Color"],multiply.inputs[1])
        links.new(base,multiply.inputs[2])
        base=multiply.outputs[0]
    if name=="MenuCloud":
        transparent=nodes.new("ShaderNodeBsdfTransparent")
        links.new(transparent.outputs[0],output.inputs["Surface"])
        return
    if values.get("unlit"):
        emission=nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value=(*values.get("emissive",colour)[:3],1)
        emission.inputs["Strength"].default_value=1
        if name in ("MenuFlame","MenuFlameCore"):
            geometry=nodes.new("ShaderNodeNewGeometry")
            noise=nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value=7
            noise.inputs["Detail"].default_value=2.5
            links.new(geometry.outputs["Position"],noise.inputs["Vector"])
            heat=nodes.new("ShaderNodeValToRGB")
            heat.color_ramp.elements[0].position=0.2
            heat.color_ramp.elements[0].color=(0.12,0.002,0.0001,1)
            heat.color_ramp.elements[1].position=0.8
            heat.color_ramp.elements[1].color=(1.0,0.3,0.015,1)
            links.new(noise.outputs["Fac"],heat.inputs[0])
            links.new(heat.outputs[0],emission.inputs["Color"])
            transparent=nodes.new("ShaderNodeBsdfTransparent")
            alpha=nodes.new("ShaderNodeValToRGB")
            alpha.color_ramp.elements[0].position=0.28
            alpha.color_ramp.elements[1].position=0.62
            links.new(noise.outputs["Fac"],alpha.inputs[0])
            flicker=nodes.new("ShaderNodeMixShader")
            links.new(alpha.outputs[0],flicker.inputs[0])
            links.new(transparent.outputs[0],flicker.inputs[1])
            links.new(emission.outputs[0],flicker.inputs[2])
            path=nodes.new("ShaderNodeLightPath")
            shadow=nodes.new("ShaderNodeMixShader")
            links.new(path.outputs["Is Shadow Ray"],shadow.inputs[0])
            links.new(flicker.outputs[0],shadow.inputs[1])
            links.new(transparent.outputs[0],shadow.inputs[2])
            links.new(shadow.outputs[0],output.inputs["Surface"])
            material.surface_render_method="DITHERED"
        else:
            links.new(emission.outputs[0],output.inputs["Surface"])
        return
    surface=nodes.new("ShaderNodeBsdfPrincipled")
    links.new(base,surface.inputs["Base Color"])
    specular=values.get("specular",(0,0,0,1,0))
    if name=="MenuPuddle":
        surface.inputs["Roughness"].default_value=0.07
    elif name=="MenuWetStone":
        surface.inputs["Roughness"].default_value=0.16
    else:
        surface.inputs["Roughness"].default_value=min(1,math.sqrt(2/(specular[4]+2)))
    surface.inputs["Specular IOR Level"].default_value=0.5 if name in ("MenuWetStone","MenuPuddle") else max(0.18,sum(specular[:3])/3)
    if name in ("MenuWetStone","MenuPuddle"):
        surface.inputs["Coat Weight"].default_value=0.85
        surface.inputs["Coat Roughness"].default_value=0.08
    if "emissive" in values and max(values["emissive"][:3])>0:
        surface.inputs["Emission Color"].default_value=(*values["emissive"][:3],1)
        surface.inputs["Emission Strength"].default_value=1
    if values.get("normal"):
        normal_texture=nodes.new("ShaderNodeTexImage")
        normal_texture.image=texture_image(repo,values["normal"],images)
        normal_texture.extension="REPEAT"
        normal=nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value=0.25 if name=="MenuWetStone" else 0.65
        links.new(normal_texture.outputs["Color"],normal.inputs["Color"])
        links.new(normal.outputs["Normal"],surface.inputs["Normal"])
    if name in ("MenuCloud","MenuMountain"):
        noise=nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value=0.16
        noise.inputs["Detail"].default_value=4
        bump=nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value=0.6
        bump.inputs["Distance"].default_value=0.6
        links.new(noise.outputs["Fac"],bump.inputs["Height"])
        links.new(bump.outputs["Normal"],surface.inputs["Normal"])
    links.new(surface.outputs[0],output.inputs["Surface"])


# Create low nonuniform participating fog that catches the existing orange and green light.
def add_ground_fog(collection):
    bpy.ops.mesh.primitive_cube_add(size=2,location=(0,3,1.15))
    fog=bpy.context.object
    fog.name="Courtyard drifting volume"
    for parent in list(fog.users_collection):
        parent.objects.unlink(fog)
    collection.objects.link(fog)
    fog.scale=(27,35,1.65)
    fog["engine_particle_script"]="MenuCourtyardFog"
    material=bpy.data.materials.new("Courtyard volume")
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    links=material.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial")
    volume=nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value=(0.50,0.55,0.60,1)
    volume.inputs["Anisotropy"].default_value=0.35
    coordinates=nodes.new("ShaderNodeTexCoord")
    noise=nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=0.24
    noise.inputs["Detail"].default_value=3.4
    noise.inputs["Roughness"].default_value=0.7
    geometry=nodes.new("ShaderNodeNewGeometry")
    links.new(geometry.outputs["Position"],noise.inputs["Vector"])
    ramp=nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position=0.3
    ramp.color_ramp.elements[0].color=(0,0,0,1)
    ramp.color_ramp.elements[1].position=0.75
    ramp.color_ramp.elements[1].color=(0.34,0.34,0.34,1)
    links.new(noise.outputs["Fac"],ramp.inputs[0])
    separate=nodes.new("ShaderNodeSeparateXYZ")
    links.new(coordinates.outputs["Generated"],separate.inputs[0])
    height=nodes.new("ShaderNodeMath")
    height.operation="SUBTRACT"
    height.inputs[0].default_value=1
    links.new(separate.outputs["Z"],height.inputs[1])
    density=nodes.new("ShaderNodeMath")
    density.operation="MULTIPLY"
    links.new(height.outputs[0],density.inputs[0])
    links.new(ramp.outputs[0],density.inputs[1])
    links.new(density.outputs[0],volume.inputs["Density"])
    links.new(volume.outputs[0],output.inputs["Volume"])
    fog.data.materials.append(material)
    return fog



# Fill native spatial storm layers with turbulent density, soft bounds and dark participating smoke.
def add_storm_clouds(collection):
    layers=[((0,57,31),(75,24,7)),((0,90,43),(95,31,10)),((0,124,56),(115,38,12))]
    for index,(position,scale) in enumerate(layers):
        bpy.ops.mesh.primitive_cube_add(size=2,location=position)
        cloud=bpy.context.object
        cloud.name="Storm volume layer %d"%index
        for parent in list(cloud.users_collection):
            parent.objects.unlink(cloud)
        collection.objects.link(cloud)
        cloud.scale=scale
        cloud["engine_particle_script"]="MenuStormClouds"
        material=bpy.data.materials.new("Dark storm participating smoke %d"%index)
        material.use_nodes=True
        nodes=material.node_tree.nodes
        nodes.clear()
        links=material.node_tree.links
        output=nodes.new("ShaderNodeOutputMaterial")
        volume=nodes.new("ShaderNodeVolumePrincipled")
        volume.inputs["Color"].default_value=(0.18,0.21,0.25,1)
        volume.inputs["Anisotropy"].default_value=0.35
        geometry=nodes.new("ShaderNodeNewGeometry")
        coordinates=nodes.new("ShaderNodeTexCoord")
        noise=nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value=0.065
        noise.inputs["Detail"].default_value=4
        noise.inputs["Roughness"].default_value=0.72
        noise.inputs["Distortion"].default_value=0.6
        links.new(geometry.outputs["Position"],noise.inputs["Vector"])
        density=nodes.new("ShaderNodeValToRGB")
        density.color_ramp.elements[0].position=0.42
        density.color_ramp.elements[0].color=(0,0,0,1)
        density.color_ramp.elements[1].position=0.7
        density.color_ramp.elements[1].color=(0.16,0.16,0.16,1)
        links.new(noise.outputs["Fac"],density.inputs[0])
        separate=nodes.new("ShaderNodeSeparateXYZ")
        links.new(coordinates.outputs["Generated"],separate.inputs[0])
        value=density.outputs[0]
        for axis in ("X","Y","Z"):
            inverse=nodes.new("ShaderNodeMath")
            inverse.operation="SUBTRACT"
            inverse.inputs[0].default_value=1
            links.new(separate.outputs[axis],inverse.inputs[1])
            product=nodes.new("ShaderNodeMath")
            product.operation="MULTIPLY"
            links.new(separate.outputs[axis],product.inputs[0])
            links.new(inverse.outputs[0],product.inputs[1])
            boost=nodes.new("ShaderNodeMath")
            boost.operation="MULTIPLY"
            boost.inputs[1].default_value=4
            links.new(product.outputs[0],boost.inputs[0])
            mask=nodes.new("ShaderNodeMath")
            mask.operation="MULTIPLY"
            links.new(value,mask.inputs[0])
            links.new(boost.outputs[0],mask.inputs[1])
            value=mask.outputs[0]
        links.new(value,volume.inputs["Density"])
        links.new(volume.outputs[0],output.inputs["Volume"])
        cloud.data.materials.append(material)


# Instantiate a deterministic particle snapshot from the configured fire and courtyard emitters.
def add_embers(collection,definitions):
    rng=random.Random(427)
    origins=[]
    positions={words[1]:tuple(float(v) for v in words[3:6]) for words in definitions if words[0]=="AddEntity"}
    for words in definitions:
        if words[0]=="AddParticleEffect" and words[2]=="MenuBrazierFire":
            origin=positions[words[1]]
            origins.extend((origin[0]+rng.uniform(-1.2,1.2),origin[1]+rng.uniform(-0.9,0.9),origin[2]+rng.uniform(3.7,7.0)) for unused in range(75))
    origins.extend((rng.choice((-1,1))*rng.uniform(7.2,15.5),rng.uniform(-18,6),rng.uniform(0.4,2.5)) for unused in range(130))
    mesh=bpy.data.meshes.new("Ember source points")
    mesh.from_pydata(origins,[],[])
    particles=bpy.data.objects.new("Fire and courtyard ember particles",mesh)
    collection.objects.link(particles)
    particles["engine_particle_scripts"]="MenuBrazierFire,MenuCourtyardEmbers"
    material=bpy.data.materials.new("Warm ember emission")
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    emission=nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value=(1,0.14,0.008,1)
    emission.inputs["Strength"].default_value=5
    output=nodes.new("ShaderNodeOutputMaterial")
    material.node_tree.links.new(emission.outputs[0],output.inputs["Surface"])
    group=bpy.data.node_groups.new("Configured ember point instances","GeometryNodeTree")
    group.interface.new_socket(name="Geometry",in_out="INPUT",socket_type="NodeSocketGeometry")
    group.interface.new_socket(name="Geometry",in_out="OUTPUT",socket_type="NodeSocketGeometry")
    n=group.nodes
    links=group.links
    input_node=n.new("NodeGroupInput")
    output_node=n.new("NodeGroupOutput")
    points=n.new("GeometryNodeMeshToPoints")
    points.mode="VERTICES"
    links.new(input_node.outputs["Geometry"],points.inputs["Mesh"])
    ico=n.new("GeometryNodeMeshIcoSphere")
    ico.inputs["Radius"].default_value=1
    ico.inputs["Subdivisions"].default_value=1
    set_material=n.new("GeometryNodeSetMaterial")
    set_material.inputs["Material"].default_value=material
    links.new(ico.outputs["Mesh"],set_material.inputs["Geometry"])
    instances=n.new("GeometryNodeInstanceOnPoints")
    links.new(points.outputs["Points"],instances.inputs["Points"])
    links.new(set_material.outputs["Geometry"],instances.inputs["Instance"])
    random_size=n.new("FunctionNodeRandomValue")
    random_size.data_type="FLOAT_VECTOR"
    random_size.inputs["Min"].default_value=(0.006,0.006,0.018)
    random_size.inputs["Max"].default_value=(0.023,0.023,0.07)
    links.new(random_size.outputs["Value"],instances.inputs["Scale"])
    links.new(instances.outputs["Instances"],output_node.inputs["Geometry"])
    modifier=particles.modifiers.new("Ember particle instances","NODES")
    modifier.node_group=group
    return len(origins)


# Copy the source mesh and armature objects while retaining their local parenting and animation.
def instantiate(name, position, prototypes, collection):
    anchor = bpy.data.objects.new(name, None)
    collection.objects.link(anchor)
    anchor.location = position
    copies = {}
    for original in prototypes:
        instance = original.copy()
        instance.name = name + "_" + original.name
        collection.objects.link(instance)
        copies[original] = instance
    for original, instance in copies.items():
        instance.parent = copies.get(original.parent, anchor)
        instance.matrix_parent_inverse = original.matrix_parent_inverse.copy()
        for modifier in instance.modifiers:
            if modifier.type == "ARMATURE" and modifier.object in copies:
                modifier.object = copies[modifier.object]
    return anchor


# Convert the configured unnormalised Lambert light at half its range to Blender watts.
def add_light(words, collection):
    name = words[1]
    numbers = [float(value) for value in words[2:]]
    position, diffuse, specular = numbers[:3], numbers[3:6], numbers[6:9]
    distance_range, constant, linear, quadratic = numbers[9:]
    reference_distance = distance_range / 2
    attenuation = constant + linear * reference_distance + quadratic * reference_distance ** 2
    magnitude = max(diffuse)
    data = bpy.data.lights.new(name, "POINT")
    data.color = tuple(component / magnitude for component in diffuse)
    data.energy = magnitude * 4 * math.pi ** 2 * reference_distance ** 2 / attenuation
    data.shadow_soft_size = 0
    # The indirect crystal bounce illuminates surfaces without becoming a luminous fog orb.
    if name == "SpireGround":
        data.volume_factor = 0
    data.use_custom_distance = True
    data.cutoff_distance = distance_range
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    obj.location = position
    obj["cfg_diffuse"] = diffuse
    obj["cfg_specular"] = specular
    obj["cfg_attenuation"] = [distance_range, constant, linear, quadratic]
    obj["conversion_reference_distance"] = reference_distance
    return {"name": name, "position": position, "diffuse": diffuse, "specular": specular, "attenuation": [distance_range, constant, linear, quadratic], "eevee_energy_watts": data.energy, "reference_distance": reference_distance}


# Assemble the configured overview, save it privately and optionally render it with Eevee.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-only", action="store_true", help="Update the portable assembly without producing another checkpoint render")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    repo = args.repo.resolve()
    output = args.output.resolve()
    assembly = output / "MenuSceneAssembly.blend"
    rendered = output / "menu-scene-eevee-1920x1080.png"
    if assembly.exists() or rendered.exists():
        raise FileExistsError("Use a fresh assembly destination")
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.render.resolution_x = 1920
    scene.render.resolution_y = 1080
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGB"
    scene.render.fps = 24
    scene.frame_start = 0
    scene.frame_end = 96
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 0
    scene.view_settings.gamma = 1
    world = bpy.data.worlds.new("Black exterior")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.012, 0.008, 0.004, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.03
    scene.eevee.use_raytracing = True
    scene.eevee.shadow_pool_size = "1024"
    scene.world = world
    sources = bpy.data.collections.new("Source models")
    scene.collection.children.link(sources)
    sources.hide_render = True
    sources.hide_viewport = True
    instances = bpy.data.collections.new("Configured scene")
    scene.collection.children.link(instances)
    definitions = [line.split() for line in (repo / "config/mainmenuscene.cfg").read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    entities = [words for words in definitions if words[0] == "AddEntity"]
    filenames = sorted({Path(words[2]).stem + ".blend" for words in entities})
    assert len(entities) == EXPECTED_CONFIGURED_ENTITY_COUNT
    assert len({words[1] for words in entities}) == len(entities)
    assert len(filenames) == len(entities), "Every placed ruin must have its own exported model"
    prototypes = {}
    source_families = set()
    for filename in filenames:
        with bpy.data.libraries.load(str(repo / "assets-src/menu-scene" / filename), link=False) as (available, loaded):
            loaded.objects = list(available.objects)
        objects = [obj for obj in loaded.objects if obj is not None]
        meshes = [obj for obj in objects if obj.type == "MESH"]
        assert len(meshes) == 1, "Each ruin source must contain one complete exported mesh: " + filename
        family = meshes[0].get("menu_source_family")
        assert family in SOURCE_FAMILIES, "Missing original source family: " + filename
        source_families.add(family)
        for obj in objects:
            sources.objects.link(obj)
        prototypes[Path(filename).stem] = objects
    assert source_families == SOURCE_FAMILIES, "The complete thirteen-family ruin pass is required"
    materials = {}
    engine_materials = (repo / "materials/scripts/MenuScene.material").read_text()
    images = {}
    for objects in prototypes.values():
        for obj in objects:
            if obj.type != "MESH":
                continue
            for slot in obj.material_slots:
                material = slot.material
                base_name = re.sub(r"\.\d{3}$", "", material.name)
                if base_name not in materials:
                    materials[base_name] = material
                    configure_material(material, material_values(engine_materials, base_name), repo, images)
                slot.material = materials[base_name]
    entity_report = []
    for words in entities:
        position = [float(value) for value in words[3:6]]
        instantiate(words[1], position, prototypes[Path(words[2]).stem], instances)
        entity_report.append({"name": words[1], "model": words[2], "position": position})
    camera_commands = [words for words in definitions if words[0] == "CameraMove"]
    assert len(camera_commands) == 1
    camera_values = [float(value) for value in camera_commands[0][1:]]
    camera_data = bpy.data.cameras.new("Overview")
    camera_data.sensor_fit = "VERTICAL"
    camera_data.sensor_height = 24
    camera_data.lens = camera_data.sensor_height / (2 * math.tan(math.radians(45) / 2))
    camera_data.clip_start = 0.02
    camera_data.clip_end = 300
    camera = bpy.data.objects.new("Overview", camera_data)
    instances.objects.link(camera)
    camera.location = camera_values[:3]
    camera.rotation_mode = "QUATERNION"
    camera.rotation_quaternion = Quaternion((1, 0, 0), math.radians(camera_values[3])) @ Quaternion((0, 1, 0), math.radians(camera_values[4])) @ Quaternion((0, 0, 1), math.radians(camera_values[5]))
    scene.camera = camera
    lights = [add_light(words, instances) for words in definitions if words[0] == "AddPointLight"]
    assert len(lights) == 17
    scene.frame_set(24)
    assert len([obj for obj in instances.objects if obj.type == "MESH"]) == len(entities)
    assert len(images) == 3 and all(image.packed_file for image in images.values())
    atmosphere=bpy.data.collections.new("Configured atmospheric effects")
    scene.collection.children.link(atmosphere)
    # Capture off-screen fire and crystal geometry in the wet courtyard reflections.
    planar_data=bpy.data.lightprobes.new("Wet courtyard planar reflection","PLANE")
    planar_data.influence_distance=0.4
    planar_data.clip_start=0.02
    planar_data.parallax_distance=25
    planar=bpy.data.objects.new("Courtyard reflection plane",planar_data)
    atmosphere.objects.link(planar)
    planar.location=(0,0,-0.025)
    planar.scale=(27,35,1)
    planar["preview_limit"]="Native Eevee planar reflection; engine reflection support remains a later runtime check."
    add_ground_fog(atmosphere)
    add_storm_clouds(atmosphere)
    ember_count=add_embers(atmosphere,definitions)
    compositor=bpy.data.node_groups.new("Fortress fire glow","CompositorNodeTree")
    compositor.interface.new_socket(name="Image",in_out="OUTPUT",socket_type="NodeSocketColor")
    scene.compositing_node_group=compositor
    layers=compositor.nodes.new("CompositorNodeRLayers")
    glow=compositor.nodes.new("CompositorNodeGlare")
    glow.inputs["Type"].default_value="Fog Glow"
    glow.inputs["Quality"].default_value="High"
    glow.inputs["Threshold"].default_value=0.15
    glow.inputs["Size"].default_value=0.06
    glow.inputs["Strength"].default_value=0.3
    final=compositor.nodes.new("NodeGroupOutput")
    compositor.links.new(layers.outputs["Image"],glow.inputs["Image"])
    compositor.links.new(glow.outputs["Image"],final.inputs["Image"])
    scene["ember_particles"]=ember_count
    scene["configuration"] = "config/mainmenuscene.cfg"
    scene["source_model_count"] = len(filenames)
    scene["source_family_count"] = len(source_families)
    scene["configured_entity_count"] = len(entities)
    scene["preview_limit"] = "Blender Eevee atmosphere preview. Configured ground fog and ember emitters are represented as participating volume and instanced points. CLQ falloff is matched at half-range only."
    scene.render.filepath = "//menu-scene-eevee-1920x1080.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(assembly))
    report = {"source_models": filenames, "source_families": sorted(source_families), "additional_variant_count": len(filenames) - len(source_families), "entities": entity_report, "camera_position_rotation": camera_values, "vertical_fov_degrees": math.degrees(camera_data.angle_y), "resolution": [1920, 1080], "engine": scene.render.engine, "lights": lights, "packed_images": sorted(images), "sample_seconds": 1, "limits": scene["preview_limit"], "ambient_mapping": "No ambient self-emission on stone or architecture. Faint world and configured distant night rim preserve dark silhouettes.", "light_mapping": "E = max(diffuse) * 4*pi^2*d^2/(c+l*d+q*d^2), d=range/2; colour normalised by its largest channel. This matches unnormalised Ogre Lambert radiance to Blender's normalised Lambert response at the reference distance only.", "colour_management": "AgX, neutral look, zero exposure adjustment"}
    (output / "assembly-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    scene.render.filepath = str(rendered)
    if not args.save_only:
        bpy.ops.render.render(write_still=True)
    destination = repo / "assets-src/menu-scene/MenuSceneAssembly.blend"
    if destination.exists():
        assert (repo / "assets-src/menu-scene/MenuSceneAssembly.blend").stat().st_size > 0
    shutil.copyfile(assembly, destination)
    assert assembly.read_bytes() == destination.read_bytes()
    print("ASSEMBLY_DONE", json.dumps({"models": len(filenames), "families": len(source_families), "entities": len(entities), "lights": len(lights), "render": str(rendered)}), flush=True)


if __name__ == "__main__":
    main()
