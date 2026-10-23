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
from mathutils import Quaternion, Vector


# The authored families remain complete while their placed ruins use separate exported variants.
SOURCE_FAMILIES = {
    "MenuGate", "MenuWallSegment", "MenuTower", "MenuStatue", "MenuBrazier", "MenuBanner",
    "MenuArches", "MenuGreenTower", "MenuCourtyard", "MenuBackdrop", "MenuCampaignHall",
    "MenuMapTable", "MenuSideCave"
}


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
    for filename in re.findall(r"\btexture\s+menu/([^\s}]+)", block):
        values["normal" if filename.endswith("Normal.png") else "texture"] = filename
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



# Translate inherited dark surfaces and transparent title or swarm decals using the exported UVs.
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
        image.extension="EXTEND" if name in ("MenuCampaignMap","MenuTitleLetters","MenuBatSprite","MenuCrowSprite") else "REPEAT"
        multiply=nodes.new("ShaderNodeMixRGB")
        multiply.blend_type="MULTIPLY"
        multiply.inputs[0].default_value=1
        links.new(image.outputs["Color"],multiply.inputs[1])
        links.new(base,multiply.inputs[2])
        base=multiply.outputs[0]
    if name in ("MenuTitleLetters","MenuBatSprite","MenuCrowSprite"):
        transparent=nodes.new("ShaderNodeBsdfTransparent")
        if name=="MenuTitleLetters":
            decal=nodes.new("ShaderNodeBsdfPrincipled")
            links.new(base,decal.inputs["Base Color"])
            links.new(base,decal.inputs["Emission Color"])
            decal.inputs["Emission Strength"].default_value=0.25
            decal.inputs["Metallic"].default_value=0.65
            decal.inputs["Roughness"].default_value=0.46
        else:
            decal=nodes.new("ShaderNodeEmission")
            links.new(base,decal.inputs["Color"])
            decal.inputs["Strength"].default_value=0.55
        alpha=nodes.new("ShaderNodeMixShader")
        links.new(image.outputs["Alpha"],alpha.inputs[0])
        links.new(transparent.outputs[0],alpha.inputs[1])
        links.new(decal.outputs[0],alpha.inputs[2])
        links.new(alpha.outputs[0],output.inputs["Surface"])
        material.surface_render_method="DITHERED"
        return
    if name=="MenuCloud":
        transparent=nodes.new("ShaderNodeBsdfTransparent")
        links.new(transparent.outputs[0],output.inputs["Surface"])
        return
    if name=="MenuSpireBeam":
        transparent=nodes.new("ShaderNodeBsdfTransparent")
        links.new(transparent.outputs[0],output.inputs["Surface"])
        return
    if values.get("unlit"):
        emission=nodes.new("ShaderNodeEmission")
        emission.inputs["Color"].default_value=(*values.get("emissive",colour)[:3],1)
        emission.inputs["Strength"].default_value=1
        if name in ("MenuHorizonGlow","MenuHorizonDark"):
            geometry=nodes.new("ShaderNodeNewGeometry")
            noise=nodes.new("ShaderNodeTexNoise")
            noise.inputs["Scale"].default_value=0.055
            noise.inputs["Detail"].default_value=5
            noise.inputs["Roughness"].default_value=0.78
            noise.inputs["Distortion"].default_value=2.8
            links.new(geometry.outputs["Position"],noise.inputs["Vector"])
            cloud_colour=nodes.new("ShaderNodeValToRGB")
            cloud_colour.color_ramp.elements[0].position=0.28
            cloud_colour.color_ramp.elements[0].color=(0.002,0.0025,0.002,1)
            cloud_colour.color_ramp.elements[1].position=0.78
            cloud_colour.color_ramp.elements[1].color=(*values["emissive"][:3],1)
            links.new(noise.outputs["Fac"],cloud_colour.inputs[0])
            separate=nodes.new("ShaderNodeSeparateXYZ")
            links.new(geometry.outputs["Position"],separate.inputs[0])
            horizon_height=nodes.new("ShaderNodeMapRange")
            horizon_height.inputs["From Min"].default_value=12
            horizon_height.inputs["From Max"].default_value=38
            horizon_height.inputs["To Min"].default_value=1
            horizon_height.inputs["To Max"].default_value=0.03
            links.new(separate.outputs["Z"],horizon_height.inputs["Value"])
            links.new(horizon_height.outputs["Result"],emission.inputs["Strength"])
            links.new(cloud_colour.outputs[0],emission.inputs["Color"])
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
        surface.inputs["Roughness"].default_value=0.045
    elif name=="MenuWetStone":
        surface.inputs["Roughness"].default_value=0.17
    else:
        surface.inputs["Roughness"].default_value=min(1,math.sqrt(2/(specular[4]+2)))
    surface.inputs["Specular IOR Level"].default_value=0.5 if name in ("MenuWetStone","MenuPuddle") else max(0.18,sum(specular[:3])/3)
    if name in ("MenuWetStone","MenuPuddle"):
        surface.inputs["Coat Weight"].default_value=0.85
        surface.inputs["Coat Roughness"].default_value=0.08
    elif name in ("MenuStone","MenuDarkStone","MenuCarvedStone","MenuRoughStone","MenuDemonStone","MenuChippedStone","MenuWetSlime","MenuDriedBlood"):
        surface.inputs["Coat Weight"].default_value=0.35
        surface.inputs["Coat Roughness"].default_value=0.15
    if "emissive" in values and max(values["emissive"][:3])>0:
        surface.inputs["Emission Color"].default_value=(*values["emissive"][:3],1)
        surface.inputs["Emission Strength"].default_value=1
    if name=="MenuBloodMoon":
        coordinates=nodes.new("ShaderNodeTexCoord")
        noise=nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value=8
        noise.inputs["Detail"].default_value=5
        noise.inputs["Roughness"].default_value=0.82
        links.new(coordinates.outputs["Generated"],noise.inputs["Vector"])
        lunar=nodes.new("ShaderNodeValToRGB")
        lunar.color_ramp.elements[0].position=0.23
        lunar.color_ramp.elements[0].color=(0.018,0.0008,0.0003,1)
        lunar.color_ramp.elements[1].position=0.74
        lunar.color_ramp.elements[1].color=(0.42,0.025,0.012,1)
        links.new(noise.outputs["Fac"],lunar.inputs[0])
        links.new(lunar.outputs[0],surface.inputs["Emission Color"])
        surface.inputs["Emission Strength"].default_value=0.75
    if values.get("normal"):
        normal_texture=nodes.new("ShaderNodeTexImage")
        normal_texture.image=texture_image(repo,values["normal"],images)
        normal_texture.extension="REPEAT"
        normal=nodes.new("ShaderNodeNormalMap")
        normal.inputs["Strength"].default_value=0.38 if name=="MenuWetStone" else 0.80
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


# Keep a thin nonuniform veil below the courtyard's ankles, leaving all architecture unobscured.
def add_ground_fog(collection):
    bpy.ops.mesh.primitive_cube_add(size=2,location=(0,0,0.24))
    fog=bpy.context.object
    fog.name="Courtyard drifting volume"
    for parent in list(fog.users_collection):
        parent.objects.unlink(fog)
    collection.objects.link(fog)
    fog.scale=(26,29,0.36)
    fog["engine_particle_script"]="MenuCourtyardFog"
    material=bpy.data.materials.new("Courtyard volume")
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    links=material.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial")
    volume=nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value=(0.30,0.33,0.36,1)
    volume.inputs["Anisotropy"].default_value=0.10
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
    ramp.color_ramp.elements[1].color=(0.085,0.085,0.085,1)
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



# Add bounded, radially soft participating gas with animated turbulent density and no solid surface.
def add_soft_volume(collection, name, position, scale, colour, density, emission, emission_strength, phase):
    bpy.ops.mesh.primitive_cube_add(size=2,location=position)
    obj=bpy.context.object
    obj.name=name
    for parent in list(obj.users_collection):
        parent.objects.unlink(obj)
    collection.objects.link(obj)
    obj.scale=scale
    material=bpy.data.materials.new(name+" gas")
    material.use_nodes=True
    nodes=material.node_tree.nodes
    nodes.clear()
    links=material.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial")
    coordinates=nodes.new("ShaderNodeTexCoord")
    center=nodes.new("ShaderNodeVectorMath")
    center.operation="SUBTRACT"
    center.inputs[1].default_value=(0.5,0.5,0.5)
    links.new(coordinates.outputs["Generated"],center.inputs[0])
    length=nodes.new("ShaderNodeVectorMath")
    length.operation="LENGTH"
    if name=="Tower soft scattered shaft":
        radial=nodes.new("ShaderNodeVectorMath")
        radial.operation="MULTIPLY"
        radial.inputs[1].default_value=(1,1,0)
        links.new(center.outputs["Vector"],radial.inputs[0])
        links.new(radial.outputs["Vector"],length.inputs[0])
    else:
        links.new(center.outputs["Vector"],length.inputs[0])
    envelope=nodes.new("ShaderNodeMapRange")
    envelope.interpolation_type="SMOOTHERSTEP"
    envelope.inputs["From Min"].default_value=0.10
    envelope.inputs["From Max"].default_value=0.51
    envelope.inputs["To Min"].default_value=1
    envelope.inputs["To Max"].default_value=0
    links.new(length.outputs["Value"],envelope.inputs["Value"])
    if name=="Tower soft scattered shaft":
        height=nodes.new("ShaderNodeSeparateXYZ")
        links.new(coordinates.outputs["Generated"],height.inputs[0])
        radius=nodes.new("ShaderNodeMapRange")
        radius.inputs["From Min"].default_value=0
        radius.inputs["From Max"].default_value=0.30
        radius.inputs["To Min"].default_value=0.10
        radius.inputs["To Max"].default_value=0.40
        links.new(height.outputs["Z"],radius.inputs["Value"])
        normalized_radius=nodes.new("ShaderNodeMath")
        normalized_radius.operation="DIVIDE"
        links.new(length.outputs["Value"],normalized_radius.inputs[0])
        links.new(radius.outputs["Result"],normalized_radius.inputs[1])
        links.new(normalized_radius.outputs[0],envelope.inputs["Value"])
        envelope.inputs["From Min"].default_value=0
        envelope.inputs["From Max"].default_value=1
    noise=nodes.new("ShaderNodeTexNoise")
    noise.noise_dimensions="4D"
    noise.inputs["Scale"].default_value=5.5
    noise.inputs["Detail"].default_value=4
    noise.inputs["Roughness"].default_value=0.75
    noise.inputs["Distortion"].default_value=1.2
    links.new(coordinates.outputs["Generated"],noise.inputs["Vector"])
    noise.inputs["W"].driver_add("default_value").driver.expression="frame/24*0.32+%.4f"%phase
    turbulence=nodes.new("ShaderNodeMapRange")
    turbulence.inputs["From Min"].default_value=0.30
    turbulence.inputs["From Max"].default_value=0.75
    if name=="Tower soft scattered shaft":
        turbulence.inputs["From Min"].default_value=0.43
        turbulence.inputs["From Max"].default_value=0.65
    links.new(noise.outputs["Fac"],turbulence.inputs["Value"])
    mask=nodes.new("ShaderNodeMath")
    mask.operation="MULTIPLY"
    links.new(envelope.outputs["Result"],mask.inputs[0])
    links.new(turbulence.outputs["Result"],mask.inputs[1])
    volume=nodes.new("ShaderNodeVolumePrincipled")
    volume.inputs["Color"].default_value=(*colour,1)
    volume.inputs["Anisotropy"].default_value=0.35
    volume.inputs["Emission Color"].default_value=(*emission,1)
    for socket,multiplier in (("Density",density),("Emission Strength",emission_strength)):
        amount=nodes.new("ShaderNodeMath")
        amount.operation="MULTIPLY"
        amount.inputs[1].default_value=multiplier
        links.new(mask.outputs[0],amount.inputs[0])
        links.new(amount.outputs[0],volume.inputs[socket])
    if name=="Tower soft scattered shaft":
        scatter=nodes.new("ShaderNodeVolumeScatter")
        scatter.inputs["Color"].default_value=(*colour,1)
        scatter.inputs["Anisotropy"].default_value=0.45
        links.new(volume.inputs["Density"].links[0].from_socket,scatter.inputs["Density"])
        links.remove(volume.inputs["Density"].links[0])
        volume.inputs["Density"].default_value=0
        fade=nodes.new("ShaderNodeMapRange")
        fade.inputs["From Min"].default_value=0.02
        fade.inputs["From Max"].default_value=0.85
        fade.inputs["To Min"].default_value=1
        fade.inputs["To Max"].default_value=0
        links.new(height.outputs["Z"],fade.inputs["Value"])
        soft_emission=nodes.new("ShaderNodeMath")
        soft_emission.operation="MULTIPLY"
        links.new(volume.inputs["Emission Strength"].links[0].from_socket,soft_emission.inputs[0])
        links.new(fade.outputs["Result"],soft_emission.inputs[1])
        links.new(soft_emission.outputs[0],volume.inputs["Emission Strength"])
        combined=nodes.new("ShaderNodeAddShader")
        links.new(scatter.outputs[0],combined.inputs[0])
        links.new(volume.outputs[0],combined.inputs[1])
        links.new(combined.outputs[0],output.inputs["Volume"])
    else:
        links.new(volume.outputs[0],output.inputs["Volume"])
    obj.data.materials.append(material)
    return obj


# Scatter the toxic tower light in a broad soft shaft and a separate localized crown haze.
def add_spire_scattering(collection,definitions,instances):
    bpy.context.view_layer.update()
    tower=next(words for words in definitions if words[0]=="AddEntity" and words[1]=="GreenTower")
    x,y,z=(float(value) for value in tower[3:6])
    beam_vertices=[]
    for obj in instances.objects:
        if obj.type!="MESH" or obj.parent is None or obj.parent.name!="GreenTower":
            continue
        slots={index for index,slot in enumerate(obj.material_slots) if slot.material.name=="MenuSpireBeam"}
        indices={index for polygon in obj.data.polygons if polygon.material_index in slots for index in polygon.vertices}
        beam_vertices.extend(obj.matrix_world @ obj.data.vertices[index].co for index in indices)
    assert beam_vertices, "The authored tower shaft must identify the exact summit"
    summit=min(vertex.z for vertex in beam_vertices)
    base=[vertex for vertex in beam_vertices if vertex.z< summit+0.2]
    x=sum(vertex.x for vertex in base)/len(base)
    y=sum(vertex.y for vertex in base)/len(base)
    add_soft_volume(collection,"Tower soft scattered shaft",(x,y,summit+50),(8,8,50),(0.012,0.48,0.025),0.085,(0.003,0.65,0.018),0.18,0.7)
    add_soft_volume(collection,"Tower crown toxic haze",(x,y,summit+0.5),(5,4,4),(0.008,0.25,0.018),0.018,(0.002,0.35,0.009),0.055,2.3)


# Keep thick smoke rooted in each bowl while separate low mist banks leave the architecture clear.
def add_smoke_and_fog_patches(collection,definitions):
    positions={words[1]:tuple(float(v) for v in words[3:6]) for words in definitions if words[0]=="AddEntity"}
    for index,words in enumerate(words for words in definitions if words[0]=="AddParticleEffect" and words[2]=="MenuBrazierFire"):
        x,y,z=positions[words[1]]
        add_soft_volume(collection,words[1]+" advecting smoke",(x+0.45,y,z+7.4),(1.4,1.2,4.0),(0.07,0.065,0.058),0.72,(0,0,0),0,index*1.7)
    for index,(position,scale) in enumerate((((-12,-12,0.85),(7,5,0.65)),((11,-5,0.80),(6,6,0.60)),((-5,6,0.85),(8,4,0.65)),((3,-20,0.55),(7,3,0.40)))):
        add_soft_volume(collection,"Low drifting fog bank %d"%index,position,scale,(0.48,0.51,0.49),1.0,(0,0,0),0,index*2.3)


# Root grave vapour in the configured opened soil and broken slabs rather than suspending a scene-wide veil.
def add_grave_vapour(collection,definitions):
    positions={words[1]:tuple(float(v) for v in words[3:6]) for words in definitions if words[0]=="AddEntity"}
    for index,name in enumerate(("OpenGraveLeft","OpenGraveRight","BrokenSlabLeft","BrokenSlabRight","Crypt")):
        x,y,z=positions[name]
        add_soft_volume(collection,name+" cold rising grave vapour",(x,y,z+0.48),(1.7,1.4,0.80),(0.22,0.24,0.19),0.65,(0,0,0),0,index*1.9)


# Carry heat from the configured raised volcanic ruins into their own narrow smoke columns.
def add_volcanic_smoke(collection,definitions):
    origin=next(tuple(float(v) for v in words[3:6]) for words in definitions if words[0]=="AddEntity" and words[1]=="VolcanicRuins")
    for index,(offset,scale) in enumerate((((-24,-1,10),(4.0,3.5,8.0)),((-2,3,12),(3.5,4.0,9.0)),((22,5,9),(4.5,3.5,8.0)))):
        position=tuple(origin[axis]+offset[axis] for axis in range(3))
        add_soft_volume(collection,"Distant burning ruin smoke %d"%index,position,scale,(0.04,0.035,0.03),0.22,(0.22,0.022,0.002),0.035,index*2.1)


# Match the engine's smoke-alpha billboards in front of the moon without adding courtyard haze.
def add_moon_cloud_tatters(collection,definitions,repo,images):
    x,y,z=next(tuple(float(v) for v in words[3:6]) for words in definitions if words[0]=="AddEntity" and words[1]=="BloodMoon")
    image=bpy.data.images.load(str(repo/"materials/textures/RoomAmbSmoke.png"),check_existing=True)
    image.pack()
    images["RoomAmbSmoke.png"]=image
    material=bpy.data.materials.new("Moon dark smoke alpha")
    material.use_nodes=True
    material.surface_render_method="DITHERED"
    nodes=material.node_tree.nodes
    nodes.clear()
    links=material.node_tree.links
    output=nodes.new("ShaderNodeOutputMaterial")
    texture=nodes.new("ShaderNodeTexImage")
    texture.image=image
    coordinates=nodes.new("ShaderNodeTexCoord")
    noise=nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value=7
    noise.inputs["Detail"].default_value=3
    links.new(coordinates.outputs["UV"],noise.inputs["Vector"])
    ragged=nodes.new("ShaderNodeValToRGB")
    ragged.color_ramp.elements[0].position=0.25
    ragged.color_ramp.elements[1].position=0.55
    links.new(noise.outputs["Fac"],ragged.inputs[0])
    opacity=nodes.new("ShaderNodeMath")
    opacity.operation="MULTIPLY"
    links.new(texture.outputs["Alpha"],opacity.inputs[0])
    links.new(ragged.outputs[0],opacity.inputs[1])
    transparent=nodes.new("ShaderNodeBsdfTransparent")
    dark=nodes.new("ShaderNodeEmission")
    dark.inputs["Color"].default_value=(0.003,0.0035,0.003,1)
    mix=nodes.new("ShaderNodeMixShader")
    links.new(opacity.outputs[0],mix.inputs[0])
    links.new(transparent.outputs[0],mix.inputs[1])
    links.new(dark.outputs[0],mix.inputs[2])
    links.new(mix.outputs[0],output.inputs["Surface"])
    for index,(offset,scale) in enumerate((((1.5,-6,2.0),(8.0,1.3,1.5)),((0.7,-8,-3.0),(6.5,1.1,0.95)))):
        position=(x+offset[0],y+offset[1],z+offset[2])
        mesh=bpy.data.meshes.new("Moon cloud billboard %d"%index)
        mesh.from_pydata(((-scale[0],0,-scale[2]),(scale[0],0,-scale[2]),(scale[0],0,scale[2]),(-scale[0],0,scale[2])),[],((0,1,2,3),))
        uv=mesh.uv_layers.new(name="UVMap")
        for loop_index,coordinate in enumerate(((0,0),(1,0),(1,1),(0,1))):
            uv.data[loop_index].uv=coordinate
        mesh.materials.append(material)
        cloud=bpy.data.objects.new("Moon foreground cloud tatter %d"%index,mesh)
        collection.objects.link(cloud)
        cloud.location=position
        cloud["engine_particle_script"]="MenuMoonCloudTatters"


# Place drifting dark ash as tiny native facets corresponding to the capped engine ash particle system.
def add_ash(collection,materials):
    rng=random.Random(991)
    vertices=[]
    faces=[]
    for index in range(112):
        x,y,z=rng.uniform(-26,26),rng.uniform(-20,38),rng.uniform(3,18)
        size=rng.uniform(0.009,0.025)
        start=len(vertices)
        vertices.extend(((x-size,y,z),(x+size,y,z+size*0.4),(x+size*0.3,y+size,z+size*2)))
        faces.append((start,start+1,start+2))
    mesh=bpy.data.meshes.new("Falling ash facets")
    mesh.from_pydata(vertices,[],faces)
    mesh.materials.append(materials["MenuAsh"])
    ash=bpy.data.objects.new("Wind-driven falling ash",mesh)
    collection.objects.link(ash)
    ash["engine_particle_script"]="MenuAshFall"
    ash.driver_add("location",0).driver.expression="sin(frame/24*0.23)*0.9"
    ash.driver_add("location",2).driver.expression="-((frame/24*0.32)%6)"
    return len(faces)


# Use the actual transparent bird bitmaps for moving distant swarm sprites, matching the engine emitters.
def add_flying_swarms(collection,repo,images):
    rng=random.Random(217)
    counts={}
    for name,filename,count,side in (("Bat","MenuBat.png",34,1),("Crow","MenuCrow.png",28,-1)):
        material=bpy.data.materials.new("Menu"+name+"Sprite")
        configure_material(material,{"name":material.name,"texture":filename,"diffuse":(0.035,0.030,0.025)},repo,images)
        vertices=[]
        faces=[]
        for index in range(count):
            x=side*rng.uniform(18,48)+rng.uniform(-9,9)
            y=rng.uniform(48,80)
            z=rng.uniform(16,30)
            size=rng.uniform(0.35,0.80)
            first=len(vertices)
            vertices.extend(((x-size,y,z-size),(x+size,y,z-size),(x+size,y,z+size),(x-size,y,z+size)))
            faces.append((first,first+1,first+2,first+3))
        mesh=bpy.data.meshes.new(name+" swarm billboards")
        mesh.from_pydata(vertices,[],faces)
        uv=mesh.uv_layers.new(name="UVMap")
        for polygon in mesh.polygons:
            for loop_index,coordinate in zip(polygon.loop_indices,((0,0),(1,0),(1,1),(0,1))):
                uv.data[loop_index].uv=coordinate
        mesh.materials.append(material)
        swarm=bpy.data.objects.new(name+" horizon swarm particles",mesh)
        collection.objects.link(swarm)
        swarm["engine_particle_script"]="Menu"+name+"Swarm"
        swarm.driver_add("location",0).driver.expression="sin(frame/24*0.36+%.3f)*2.8"%side
        swarm.driver_add("location",2).driver.expression="sin(frame/24*0.73+%.3f)*0.7"%side
        counts[name]=count
    return counts


# Place turbulent storm volumes behind the mountain layers, above the courtyard and architecture.
def add_storm_clouds(collection):
    layers=[((0,80,35),(84,22,6)),((0,112,49),(102,28,8)),((0,145,64),(118,33,10))]
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
        volume.inputs["Color"].default_value=(0.18,0.17,0.16,1)
        volume.inputs["Anisotropy"].default_value=0.20
        geometry=nodes.new("ShaderNodeNewGeometry")
        coordinates=nodes.new("ShaderNodeTexCoord")
        noise=nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value=0.19
        noise.inputs["Detail"].default_value=6
        noise.inputs["Roughness"].default_value=0.82
        noise.inputs["Distortion"].default_value=2.4
        links.new(geometry.outputs["Position"],noise.inputs["Vector"])
        cloud_colour=nodes.new("ShaderNodeValToRGB")
        cloud_colour.color_ramp.elements[0].position=0.43
        cloud_colour.color_ramp.elements[0].color=(0.004,0.005,0.004,1)
        cloud_colour.color_ramp.elements[1].position=0.59
        cloud_colour.color_ramp.elements[1].color=(0.002,0.003,0.002,1)
        rim=cloud_colour.color_ramp.elements.new(0.51)
        rim.color=(0.045,0.050,0.045,1)
        links.new(noise.outputs["Fac"],cloud_colour.inputs[0])
        world_height=nodes.new("ShaderNodeSeparateXYZ")
        links.new(geometry.outputs["Position"],world_height.inputs[0])
        lower_rim=nodes.new("ShaderNodeMapRange")
        lower_rim.inputs["From Min"].default_value=31
        lower_rim.inputs["From Max"].default_value=37
        lower_rim.inputs["To Min"].default_value=0.75 if index==0 else 0
        lower_rim.inputs["To Max"].default_value=0
        links.new(world_height.outputs["Z"],lower_rim.inputs["Value"])
        lit_colour=nodes.new("ShaderNodeMixRGB")
        lit_colour.blend_type="MIX"
        lit_colour.inputs[2].default_value=(0.26,0.026,0.002,1)
        links.new(lower_rim.outputs["Result"],lit_colour.inputs[0])
        links.new(cloud_colour.outputs[0],lit_colour.inputs[1])
        links.new(lit_colour.outputs[0],volume.inputs["Emission Color"])
        density=nodes.new("ShaderNodeValToRGB")
        density.color_ramp.elements[0].position=0.48
        density.color_ramp.elements[0].color=(0,0,0,1)
        density.color_ramp.elements[1].position=0.64
        density.color_ramp.elements[1].color=(0.22,0.22,0.22,1)
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
        horizon_scatter=nodes.new("ShaderNodeMath")
        horizon_scatter.operation="MULTIPLY"
        horizon_scatter.inputs[1].default_value=1.25 if index==0 else 0.85
        links.new(value,horizon_scatter.inputs[0])
        links.new(horizon_scatter.outputs[0],volume.inputs["Emission Strength"])
        links.new(volume.outputs[0],output.inputs["Volume"])
        cloud.data.materials.append(material)


# Separate existing far silhouettes with thin atmospheric banks entirely behind the menu architecture.
def add_background_depth(collection):
    for index,(position,scale) in enumerate((((-28,62,18),(34,9,12)),((34,78,23),(30,10,15)),((-8,100,28),(45,12,17)))):
        add_soft_volume(collection,"Distant ridge haze %d"%index,position,scale,(0.20,0.21,0.20),0.018,(0.018,0.012,0.009),0.035,index*2.8)


# Build native advecting fire volumes at the same four configured particle-emitter locations.
def add_brazier_fire(collection, definitions):
    positions={words[1]:tuple(float(value) for value in words[3:6]) for words in definitions if words[0]=="AddEntity"}
    fires=[]
    for words in definitions:
        if words[0]!="AddParticleEffect" or words[2]!="MenuBrazierFire":
            continue
        position=positions[words[1]]
        bpy.ops.mesh.primitive_cube_add(size=2,location=(position[0],position[1],position[2]+4.15))
        fire=bpy.context.object
        fire.name=words[1]+" animated fire volume"
        for parent in list(fire.users_collection):
            parent.objects.unlink(fire)
        collection.objects.link(fire)
        fire.scale=(0.88,0.88,1.05)
        fire["engine_particle_script"]="MenuBrazierFire"
        material=bpy.data.materials.new(words[1]+" turbulent flame gas")
        material.use_nodes=True
        nodes=material.node_tree.nodes
        nodes.clear()
        links=material.node_tree.links
        output=nodes.new("ShaderNodeOutputMaterial")
        volume=nodes.new("ShaderNodeVolumePrincipled")
        volume.inputs["Color"].default_value=(0.08,0.012,0.001,1)
        coordinates=nodes.new("ShaderNodeTexCoord")
        separate=nodes.new("ShaderNodeSeparateXYZ")
        links.new(coordinates.outputs["Generated"],separate.inputs[0])
        centered=nodes.new("ShaderNodeVectorMath")
        centered.operation="SUBTRACT"
        centered.inputs[1].default_value=(0.5,0.5,0)
        links.new(coordinates.outputs["Generated"],centered.inputs[0])
        flat=nodes.new("ShaderNodeVectorMath")
        flat.operation="MULTIPLY"
        flat.inputs[1].default_value=(1,1,0)
        links.new(centered.outputs["Vector"],flat.inputs[0])
        radial=nodes.new("ShaderNodeVectorMath")
        radial.operation="LENGTH"
        links.new(flat.outputs["Vector"],radial.inputs[0])
        radius=nodes.new("ShaderNodeMapRange")
        radius.inputs["From Min"].default_value=0
        radius.inputs["From Max"].default_value=1
        radius.inputs["To Min"].default_value=0.45
        radius.inputs["To Max"].default_value=0.07
        links.new(separate.outputs["Z"],radius.inputs["Value"])
        edge=nodes.new("ShaderNodeMath")
        edge.operation="SUBTRACT"
        links.new(radius.outputs["Result"],edge.inputs[0])
        links.new(radial.outputs["Value"],edge.inputs[1])
        envelope=nodes.new("ShaderNodeMapRange")
        envelope.clamp=True
        envelope.inputs["From Min"].default_value=0
        envelope.inputs["From Max"].default_value=0.16
        envelope.inputs["To Min"].default_value=0
        envelope.inputs["To Max"].default_value=1
        links.new(edge.outputs[0],envelope.inputs["Value"])
        noise=nodes.new("ShaderNodeTexNoise")
        noise.name="Animated fire turbulence"
        noise.noise_dimensions="4D"
        noise.inputs["Scale"].default_value=6.5
        noise.inputs["Detail"].default_value=3.2
        noise.inputs["Distortion"].default_value=0.8
        links.new(coordinates.outputs["Generated"],noise.inputs["Vector"])
        driver=noise.inputs["W"].driver_add("default_value").driver
        driver.expression="frame / 24 * 1.7 + %.4f"%(len(fires)*0.83)
        tongues=nodes.new("ShaderNodeMapRange")
        tongues.clamp=True
        tongues.inputs["From Min"].default_value=0.36
        tongues.inputs["From Max"].default_value=0.65
        tongues.inputs["To Min"].default_value=0
        tongues.inputs["To Max"].default_value=1
        links.new(noise.outputs["Fac"],tongues.inputs["Value"])
        gas=nodes.new("ShaderNodeMath")
        gas.operation="MULTIPLY"
        links.new(envelope.outputs["Result"],gas.inputs[0])
        links.new(tongues.outputs["Result"],gas.inputs[1])
        height=nodes.new("ShaderNodeValToRGB")
        height.color_ramp.elements[0].position=0.08
        height.color_ramp.elements[0].color=(0,0,0,1)
        height.color_ramp.elements[1].position=0.20
        height.color_ramp.elements[1].color=(1,1,1,1)
        tip=height.color_ramp.elements.new(0.88)
        tip.color=(0,0,0,1)
        links.new(separate.outputs["Z"],height.inputs[0])
        bounded=nodes.new("ShaderNodeMath")
        bounded.operation="MULTIPLY"
        links.new(gas.outputs[0],bounded.inputs[0])
        links.new(height.outputs[0],bounded.inputs[1])
        density=nodes.new("ShaderNodeMath")
        density.operation="MULTIPLY"
        density.inputs[1].default_value=2.2
        links.new(bounded.outputs[0],density.inputs[0])
        links.new(density.outputs[0],volume.inputs["Density"])
        heat=nodes.new("ShaderNodeValToRGB")
        heat.color_ramp.elements[0].position=0.22
        heat.color_ramp.elements[0].color=(0.28,0.012,0.0005,1)
        heat.color_ramp.elements[1].position=0.82
        heat.color_ramp.elements[1].color=(1,0.42,0.045,1)
        links.new(noise.outputs["Fac"],heat.inputs[0])
        links.new(heat.outputs[0],volume.inputs["Emission Color"])
        emission=nodes.new("ShaderNodeMath")
        emission.operation="MULTIPLY"
        emission.inputs[1].default_value=11
        links.new(bounded.outputs[0],emission.inputs[0])
        links.new(emission.outputs[0],volume.inputs["Emission Strength"])
        links.new(volume.outputs[0],output.inputs["Volume"])
        fire.data.materials.append(material)
        fires.append((fire,noise))
    assert len(fires)==4, "The configured four bowls must have native animated fire"
    return fires


# Drive each configured fire light with the same continuous two-frequency waveform as the engine.
def animate_fire_lights(definitions, collection):
    animated=[]
    for words in definitions:
        if words[0]!="Flicker":
            continue
        name=words[1]
        amplitude,frequency,phase=(float(value) for value in words[2:5])
        assert 0<=amplitude<=1 and frequency>0
        light=collection.objects[name]
        baseline=light.data.energy
        light.data["steady_energy_watts"]=baseline
        light.data["cfg_flicker"]=[amplitude,frequency,phase]
        driver=light.data.driver_add("energy").driver
        driver.expression="%.12g*(1+%.12g*(0.7*sin(%.12g*frame/24+%.12g)+0.3*sin(2.37*%.12g*frame/24+1.73*%.12g)))"%(baseline,amplitude,frequency,phase,frequency,phase)
        animated.append(light)
    assert len(animated)==7, "The configured fire lights must match the native menu runtime"
    return animated


# Sample the actual animated data during the existing assembly run without producing extra images.
def sample_fire_animation(scene, fires, lights):
    samples=[]
    for frame in (1,24,48):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        samples.append({"frame":frame,"time_seconds":frame/24,
            "light_energy_watts":{light.name:light.data.energy for light in lights},
            "fire_noise_w":{fire.name:noise.inputs["W"].default_value for fire,noise in fires}})
    for light in lights:
        assert len({sample["light_energy_watts"][light.name] for sample in samples})>1
    for fire,noise in fires:
        assert len({sample["fire_noise_w"][fire.name] for sample in samples})>1
    scene.frame_set(24)
    return samples


# Instantiate configured ember snapshots and advect them sideways with the courtyard wind.
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
    particles.driver_add("location",0).driver.expression="sin(frame/24*0.47)*0.35"
    particles.driver_add("location",1).driver.expression="sin(frame/24*0.31)*0.12"
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


# Seat explicitly marked feet, report every unsupported foot, and persist only a complete valid engine layout.
def seat_configured_contacts(scene,definitions,collection,configuration):
    scene.frame_set(0)
    bpy.context.view_layer.update()
    entries={words[1]:words for words in definitions if words[0]=="AddEntity"}
    report=[]
    corrected={}
    unsupported=[]
    for mode in ("ground","perch"):
        for name,words in entries.items():
            anchor=collection.objects[name]
            meshes=[obj for obj in anchor.children_recursive if obj.type=="MESH"]
            assert len(meshes)==1,name
            mesh=meshes[0]
            if mesh.get("contact_mode")!=mode:
                continue
            support_name=mesh.get("contact_support")
            assert isinstance(support_name,str) and support_name in entries,(name,support_name)
            support_anchor=collection.objects[support_name]
            supports=[obj for obj in support_anchor.children_recursive if obj.type=="MESH"]
            assert supports,(name,support_name)
            point=mesh.get("contact_point",(0,0,min(vertex.co.z for vertex in mesh.data.vertices)))
            foot=mesh.matrix_world @ Vector(point)
            highest=None
            for support in supports:
                evaluated=support.evaluated_get(bpy.context.evaluated_depsgraph_get())
                inverse=evaluated.matrix_world.inverted()
                origin=inverse @ Vector((foot.x,foot.y,160))
                direction=(inverse.to_3x3() @ Vector((0,0,-1))).normalized()
                hit,local,normal,index=evaluated.ray_cast(origin,direction,distance=400)
                if hit:
                    world=evaluated.matrix_world @ local
                    if highest is None or world.z>highest:
                        highest=world.z
            if highest is None:
                unsupported.append(name+" on "+support_name)
                continue
            before=anchor.location.z
            delta=highest-foot.z
            anchor.location.z+=delta
            words[5]="%.8f"%anchor.location.z
            corrected[name]=words[5]
            bpy.context.view_layer.update()
            final_foot=mesh.matrix_world @ Vector(point)
            assert abs(final_foot.z-highest)<0.0001,(name,final_foot.z,highest)
            report.append({"entity":name,"mode":mode,"support":support_name,"foot_local":list(point),
                "support_height":highest,"anchor_z_before":before,"anchor_z_after":anchor.location.z,
                "final_foot_z":final_foot.z})
    assert not unsupported,"No authored support below the foot of: "+", ".join(unsupported)
    if corrected:
        with configuration.open("r",encoding="utf-8",newline="") as source:
            lines=source.read().splitlines(keepends=True)
        for index,line in enumerate(lines):
            words=line.split()
            if len(words)==6 and words[0]=="AddEntity" and words[1] in corrected:
                newline="\r\n" if line.endswith("\r\n") else "\n" if line.endswith("\n") else ""
                match=re.match(r"(\s*AddEntity\s+\S+\s+\S+\s+\S+\s+\S+\s+)(\S+)(.*)",line.rstrip("\r\n"))
                assert match is not None,words[1]
                lines[index]=match.group(1)+corrected[words[1]]+match.group(3)+newline
        configuration.write_text("".join(lines),encoding="utf-8",newline="")
    return report


# Loop each configured native armature action with the same clip selection used by Ogre.
def configure_rig_loops(definitions,collection):
    from odp_ogre_io import _channelbag
    animated=[]
    for words in definitions:
        if words[0]!="AnimationTime":
            continue
        name,clip=words[1:3]
        anchor=collection.objects[name]
        armatures=[obj for obj in anchor.children_recursive if obj.type=="ARMATURE"]
        assert len(armatures)==1, "Configured animation needs its own exported armature: "+name
        arm=armatures[0]
        assert arm.animation_data is not None and arm.animation_data.action is not None,name
        action=arm.animation_data.action
        assert re.sub(r"\.\d{3}$","",action.name)==clip,(name,clip,action.name)
        channels=_channelbag(action)
        assert channels is not None,name
        for curve in channels.fcurves:
            if not any(modifier.type=="CYCLES" for modifier in curve.modifiers):
                curve.modifiers.new("CYCLES")
        arm["engine_animation_clip"]=clip
        arm["engine_animation_loop"]=float(words[3])<0
        animated.append((name,arm))
    return animated


# Record actual bone matrices across idle, takeoff and landing phases in the existing assembly report.
def sample_rig_animation(scene,animated):
    samples=[]
    for frame in (1,24,48,96,144,216,288):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        poses={}
        for name,arm in animated:
            poses[name]={bone.name:[round(value,6) for row in bone.matrix for value in row] for bone in arm.pose.bones}
        samples.append({"frame":frame,"bone_matrices":poses})
    for name,arm in animated:
        distinct={json.dumps(sample["bone_matrices"][name],sort_keys=True) for sample in samples}
        assert len(distinct)>1,"Configured skeletal loop does not move: "+name
    scene.frame_set(24)
    return samples


# Convert configured light at half range to watts and retain the local rift specular ratio.
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
    if name == "SpireSummitScatter":
        data.shadow_soft_size = 1.25
    elif name in ("BoneGlutLeft","BoneGlutRight","FlankGlutLeft","FlankGlutRight"):
        data.shadow_soft_size = 0.55
        data.specular_factor = max(specular) / magnitude
    elif name in ("LavaLeft","LavaRight","GraveRedLeft","GraveRedRight"):
        data.shadow_soft_size = 0.25
    # Local bounce lights reveal surfaces without becoming luminous floating fog orbs.
    if name in ("SpireGround", "SpireBounce", "NightRim", "BloodMoonRim", "BoneGlutLeft", "BoneGlutRight", "FlankGlutLeft", "FlankGlutRight"):
        data.volume_factor = 0
    elif name in ("LeftFloorFire", "RightFloorFire", "CourtyardFireBounce", "SpireFloorBounce"):
        data.volume_factor = 0.25
    elif name == "CloudBack":
        data.volume_factor = 0.35
    elif name == "GateBacklight":
        data.volume_factor = 0.3
    elif name in ("BoneGlutLeft","BoneGlutRight","FlankGlutLeft","FlankGlutRight"):
        data.volume_factor = 0.12
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


# Assemble every authored source and configured skeletal loop, then save and render the native Eevee overview.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--save-only", action="store_true", help="Update the portable assembly without producing another checkpoint render")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:])
    repo = args.repo.resolve()
    sys.path.insert(0,str(repo/"tools/blender-assets"))
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
    scene.frame_end = 288
    scene.view_settings.view_transform = "AgX"
    scene.view_settings.look = "None"
    scene.view_settings.exposure = 1
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
    assert len(entities) >= 31, "The original fortress entities must remain in the expanded scene"
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
        assert isinstance(family,str) and family, "Missing source family: " + filename
        source_families.add(family)
        for obj in objects:
            sources.objects.link(obj)
        prototypes[Path(filename).stem] = objects
    assert SOURCE_FAMILIES.issubset(source_families), "The complete thirteen-family ruin pass is required"
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
    # Discard only unused source duplicates after all mesh slots share their final materials.
    for material in list(bpy.data.materials):
        if material.users==0:
            bpy.data.materials.remove(material)
    for image in list(bpy.data.images):
        if image.users==0:
            bpy.data.images.remove(image)
    entity_report = []
    for words in entities:
        position = [float(value) for value in words[3:6]]
        instantiate(words[1], position, prototypes[Path(words[2]).stem], instances)
        entity_report.append({"name": words[1], "model": words[2], "position": position})
    contacts=seat_configured_contacts(scene,definitions,instances,repo/"config/mainmenuscene.cfg")
    for entry in entity_report:
        entry["position"]=[float(value) for value in next(words for words in entities if words[1]==entry["name"])[3:6]]
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
    assert len(lights) >= 24
    scene.frame_set(24)
    assert len([obj for obj in instances.objects if obj.type == "MESH"]) == len(entities)
    rigs=configure_rig_loops(definitions,instances)
    rig_animation=sample_rig_animation(scene,rigs)
    atmosphere=bpy.data.collections.new("Configured atmospheric effects")
    scene.collection.children.link(atmosphere)
    # Capture off-screen fire and the internally lit tower in the wet courtyard reflections.
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
    add_smoke_and_fog_patches(atmosphere,definitions)
    add_grave_vapour(atmosphere,definitions)
    add_spire_scattering(atmosphere,definitions,instances)
    add_storm_clouds(atmosphere)
    add_background_depth(atmosphere)
    add_volcanic_smoke(atmosphere,definitions)
    add_moon_cloud_tatters(atmosphere,definitions,repo,images)
    fires=add_brazier_fire(atmosphere,definitions)
    fire_lights=animate_fire_lights(definitions,instances)
    fire_animation=sample_fire_animation(scene,fires,fire_lights)
    ember_count=add_embers(atmosphere,definitions)
    if "MenuAsh" not in materials:
        materials["MenuAsh"]=bpy.data.materials.new("MenuAsh")
        configure_material(materials["MenuAsh"],material_values(engine_materials,"MenuAsh"),repo,images)
    ash_count=add_ash(atmosphere,materials)
    swarm_counts=add_flying_swarms(atmosphere,repo,images)
    expected_images={"MenuCampaignMap.png","MenuTitle.png","MenuBat.png","MenuCrow.png","RoomAmbSmoke.png"}
    for surface in ("MenuFortressStone","MenuWetPaving","MenuDemonStone","MenuRustIron","MenuTornCloth"):
        expected_images.update((surface+".png",surface+"Normal.png"))
    assert set(images)==expected_images and all(image.packed_file for image in images.values())
    used_images={image for image in bpy.data.images if image.users>0 and image.source=="FILE"}
    assert used_images==set(images.values()), "Keep exactly the used packed scene images"
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
    scene["preview_limit"] = "Blender Eevee atmosphere preview. Configured low grave fog, fire and smoke are participating volumes; skeletal clips, fire noise, ash, swarms and point-light energy are driven continuously. Ember snapshots use native points. CLQ falloff is matched at half-range only."
    scene.render.filepath = "//menu-scene-eevee-1920x1080.png"
    bpy.ops.wm.save_as_mainfile(filepath=str(assembly),compress=True)
    report = {"source_models": filenames, "source_families": sorted(source_families), "additional_variant_count": len(filenames) - len(source_families), "entities": entity_report, "contact_placements":contacts,"camera_position_rotation": camera_values, "vertical_fov_degrees": math.degrees(camera_data.angle_y), "resolution": [1920, 1080], "engine": scene.render.engine, "lights": lights, "fire_animation_samples": fire_animation, "skeletal_animation_samples":rig_animation,"native_ash_count":ash_count,"native_swarm_counts":swarm_counts,"packed_images": sorted(images), "sample_seconds": 1, "limits": scene["preview_limit"], "ambient_mapping": "No ambient self-emission on stone or architecture. Faint world, distant ember horizon and configured local rim preserve dark silhouettes.", "light_mapping": "E = max(diffuse) * 4*pi^2*d^2/(c+l*d+q*d^2), d=range/2; colour normalised by its largest channel. This matches unnormalised Ogre Lambert radiance to Blender's normalised Lambert response at the reference distance only.", "colour_management": "AgX, neutral look, exposure +1 EV"}
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
