"""Create the editable fortress models and export their Ogre XML meshes sequentially."""
from pathlib import Path
import math
import json
import random
import shutil
import sys

import bpy
from mathutils import Vector, Quaternion
from mathutils.bvhtree import BVHTree

VARIANT_SEED = 0
VARIANT_DAMAGE = 1.0
VARIANT_NAME = ""


# Build disconnected closed surfaces with material slots and world-sized planar UVs.
class MeshBuilder:
    # Start one independently editable menu model.
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.face_materials = []
        self.rng = random.Random(1901 + VARIANT_SEED + sum(ord(value) for value in name))
        self.contact_corrections = []

    # Append a solid polygon extruded along Y.
    def prism(self, polygon, front, back, material="MenuStone"):
        start = len(self.vertices)
        count = len(polygon)
        self.vertices.extend((x, front, z) for x, z in polygon)
        self.vertices.extend((x, back, z) for x, z in polygon)
        if material in ("MenuStone", "MenuDarkStone", "MenuCarvedStone", "MenuRoughStone", "MenuWetStone", "MenuWood", "MenuIron", "MenuDistantStone", "MenuMountain"):
            strength = 0.045 * VARIANT_DAMAGE
            for index in range(start, len(self.vertices)):
                point = self.vertices[index]
                self.vertices[index] = tuple(point[axis] + self.rng.uniform(-strength, strength) for axis in range(3))
        self.faces.append(tuple(start + i for i in range(count)))
        self.faces.append(tuple(start + count + i for i in reversed(range(count))))
        for i in range(count):
            j = (i + 1) % count
            self.faces.append((start+i, start+count+i, start+count+j, start+j))
        self.face_materials.extend([material] * (count+2))

    # Add a chipped, tilted masonry block with genuinely clipped irregular corners.
    def box(self, centre, size, material="MenuStone"):
        x, y, z = centre
        a, b, c = (v/2 for v in size)
        if material in ("MenuWindowGlow", "MenuFlame", "MenuFlameCore", "MenuEmber", "MenuParchment", "MenuCampaignMap"):
            self.prism([(x-a,z-c),(x+a,z-c),(x+a,z+c),(x-a,z+c)],y-b,y+b,material)
            return
        chip = min(a, c) * self.rng.uniform(0.14, 0.43)
        polygon = [(-a+chip,-c),(a-chip*0.6,-c),(a,-c+chip*1.3),(a,c-chip),
            (a-chip*1.2,c),(-a+chip*0.7,c),(-a,c-chip*0.6),(-a,-c+chip)]
        lean = self.rng.uniform(-0.045,0.045) * VARIANT_DAMAGE
        polygon = [(x+px*math.cos(lean)-pz*math.sin(lean), z+px*math.sin(lean)+pz*math.cos(lean)) for px,pz in polygon]
        self.prism(polygon,y-b,y+b,material)
        if material in ("MenuStone", "MenuDarkStone", "MenuCarvedStone", "MenuRoughStone") and self.rng.random()<0.32:
            seam_x=x+self.rng.uniform(-a*0.55,a*0.55)
            seam_z=z+self.rng.uniform(-c*0.30,c*0.30)
            self.prism([(seam_x-0.022,seam_z-c*0.65),(seam_x+0.09,seam_z-c*0.16),
                (seam_x-0.03,seam_z+c*0.32),(seam_x+0.11,seam_z+c*0.73),
                (seam_x+0.075,seam_z+c*0.76),(seam_x-0.075,seam_z+c*0.32),
                (seam_x+0.045,seam_z-c*0.16)],y-b-0.015,y-b-0.009,"MenuBlack")
        if material in ("MenuStone", "MenuDarkStone", "MenuCarvedStone", "MenuRoughStone") and z<8 and self.rng.random()<0.17:
            seam = "MenuMoss" if z<4 else "MenuLichen"
            self.prism([(x-a+chip,z-c+0.015),(x+a*0.45,z-c+0.028),
                (x+a*0.28,z-c+0.072),(x-a*0.2,z-c+0.046),(x-a+chip*1.2,z-c+0.10)],
                y-b-0.018,y-b-0.010,seam)

    # Add a visibly worn, off-axis tapered column or pointed spire.
    def column(self, centre, radius, height, top=None, material="MenuStone", sides=12):
        x, y, z = centre
        top = radius if top is None else top
        irregular = material not in ("MenuFlame", "MenuFlameCore", "MenuEmber", "MenuSpireGlow", "MenuSpireBeam", "MenuEmberCrack")
        lean_x = self.rng.uniform(-0.13,0.13) * VARIANT_DAMAGE if irregular else 0
        lean_y = self.rng.uniform(-0.09,0.09) * VARIANT_DAMAGE if irregular else 0
        start = len(self.vertices)
        if top == 0:
            self.vertices.extend((x+radius*math.cos(i*2*math.pi/sides),y+radius*math.sin(i*2*math.pi/sides),z) for i in range(sides))
            self.vertices.append((x+lean_x,y+lean_y,z+height))
            self.faces.append(tuple(start+i for i in reversed(range(sides))))
            for i in range(sides):
                self.faces.append((start+i,start+(i+1)%sides,start+sides))
            self.face_materials.extend([material]*(sides+1))
            return
        for level, r in ((z,radius),(z+height,top)):
            for i in range(sides):
                wear = self.rng.uniform(0.82,1.11) if irregular else 1
                shift = 1 if level != z else 0
                jitter=self.rng.uniform(-0.055,0.055)*shift if irregular else 0
                self.vertices.append((x+r*wear*math.cos(i*2*math.pi/sides)+lean_x*shift,
                    y+r*wear*math.sin(i*2*math.pi/sides)+lean_y*shift,level+jitter))
        self.faces.extend([tuple(start+i for i in reversed(range(sides))),tuple(start+sides+i for i in range(sides))])
        for i in range(sides):
            j = (i+1)%sides
            self.faces.append((start+i,start+j,start+sides+j,start+sides+i))
        self.face_materials.extend([material]*(sides+2))

    # Add a faceted oval used for carved anatomy, rocks and distant clouds.
    def oval(self, centre, radius, material="MenuStone", sides=12, rings=7):
        start = len(self.vertices)
        self.vertices.append((centre[0],centre[1],centre[2]-radius[2]))
        for row in range(1,rings):
            latitude = -math.pi/2 + math.pi*row/rings
            for i in range(sides):
                a=i*2*math.pi/sides
                self.vertices.append(tuple(centre[k]+radius[k]*v for k,v in enumerate((math.cos(latitude)*math.cos(a),math.cos(latitude)*math.sin(a),math.sin(latitude)))))
        top=len(self.vertices)
        self.vertices.append((centre[0],centre[1],centre[2]+radius[2]))
        for i in range(sides):
            j=(i+1)%sides
            self.faces.append((start,start+1+j,start+1+i))
            self.face_materials.append(material)
        for row in range(rings-2):
            for i in range(sides):
                j=(i+1)%sides
                self.faces.append((start+1+row*sides+i,start+1+row*sides+j,start+1+(row+1)*sides+j,start+1+(row+1)*sides+i))
                self.face_materials.append(material)
        last=start+1+(rings-2)*sides
        for i in range(sides):
            self.faces.append((last+i,last+(i+1)%sides,top))
            self.face_materials.append(material)

    # Connect two anatomical points with a tapering carved stone limb or wing rib.
    def segment(self, start, end, radius, top, material="MenuCarvedStone", sides=12):
        axis=Vector(end)-Vector(start)
        direction=axis.normalized()
        across=direction.cross(Vector((0,1,0)))
        if across.length<0.01:
            across=direction.cross(Vector((1,0,0)))
        across.normalize()
        up=direction.cross(across).normalized()
        first=len(self.vertices)
        for centre,width in ((Vector(start),radius),(Vector(end),top)):
            for i in range(sides):
                point=centre+width*(across*math.cos(i*2*math.pi/sides)+up*math.sin(i*2*math.pi/sides))
                self.vertices.append(tuple(point))
        self.faces.extend([tuple(first+i for i in reversed(range(sides))),tuple(first+sides+i for i in range(sides))])
        for i in range(sides):
            j=(i+1)%sides
            self.faces.append((first+i,first+j,first+sides+j,first+sides+i))
        self.face_materials.extend([material]*(sides+2))

    # Add a curved row of separate wedge-shaped masonry blocks.
    def arch(self, x, y, spring, radius, thickness, depth, count=18):
        for i in range(count):
            gap = int(count * (0.24 + (VARIANT_SEED % 4)*0.10))
            if radius > 1.4 and i in (gap, gap+1) and self.name != "MenuGate":
                continue
            a=math.pi*i/count+0.012
            b=math.pi*(i+1)/count-0.012
            poly=[(x+radius*math.cos(a),spring+radius*math.sin(a)),(x+(radius+thickness)*math.cos(a),spring+(radius+thickness)*math.sin(a)),(x+(radius+thickness)*math.cos(b),spring+(radius+thickness)*math.sin(b)),(x+radius*math.cos(b),spring+radius*math.sin(b))]
            sag = self.rng.uniform(-0.12,0.08)*VARIANT_DAMAGE
            self.prism([(px,pz+sag) for px,pz in poly],y-depth/2,y+depth/2)

    # Add a worn elliptical chain link, with occasional broken sections closed by fracture caps.
    def link(self, centre, radius, alternate=False):
        cx,cy,cz=centre
        sides=12
        ring=6
        start=len(self.vertices)
        broken=int(abs(cx)*13+abs(cz)*7)%7==0
        for i in range(sides):
            a=i*2*math.pi/sides
            for j in range(ring):
                b=j*2*math.pi/ring
                wear=0.045*(0.76+0.18*math.sin(i*1.9+j*0.8))
                x=(radius+wear*math.cos(b))*math.cos(a)
                z=(radius*0.65+wear*math.cos(b))*math.sin(a)
                y=wear*math.sin(b)
                self.vertices.append((cx+(y if alternate else x),cy+(x if alternate else y),cz+z))
        for i in range(sides):
            if broken and i==2:
                continue
            for j in range(ring):
                self.faces.append((start+i*ring+j,start+((i+1)%sides)*ring+j,start+((i+1)%sides)*ring+(j+1)%ring,start+i*ring+(j+1)%ring))
                self.face_materials.append("MenuIron")
        if broken:
            self.faces.append(tuple(start+2*ring+j for j in range(ring)))
            self.faces.append(tuple(start+3*ring+j for j in reversed(range(ring))))
            self.face_materials.extend(["MenuIron","MenuIron"])

    # Produce worn surfaces with baked per-object texture rotation and non-repeating local UV offsets.
    def finish(self):
        settle_rubble(self)
        mesh=bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices,[],self.faces)
        mesh.update()
        obj=bpy.data.objects.new(self.name,mesh)
        bpy.context.scene.collection.objects.link(obj)
        for index, material in enumerate(self.face_materials):
            if material not in ("MenuStone", "MenuDarkStone", "MenuCarvedStone", "MenuRoughStone"):
                continue
            face = mesh.polygons[index]
            center = face.center
            patch = math.sin(center.x*1.71+VARIANT_SEED)+math.sin(center.z*0.73+center.y*0.91)
            if center.z < 3.8 and patch > 0.75:
                self.face_materials[index] = "MenuMoss"
            elif patch < -1.50:
                self.face_materials[index] = "MenuLichen"
            elif math.sin(center.x*7.9+center.y*4.1+VARIANT_SEED) > 0.93:
                self.face_materials[index] = "MenuWaterStain"
            elif self.rng.random() < 0.06:
                self.face_materials[index] = "MenuChippedStone"
        names=list(dict.fromkeys(self.face_materials))
        for name in names:
            mesh.materials.append(bpy.data.materials[name])
        uv=mesh.uv_layers.new(name="UVMap")
        for face, name in zip(mesh.polygons,self.face_materials):
            face.material_index=names.index(name)
            if name=="MenuCarvedStone" and self.name!="MenuGate":
                face.use_smooth=True
            dominant=max(range(3),key=lambda i:abs(face.normal[i]))
            axes=((1,2),(0,2),(0,1))[dominant]
            for loop_index in face.loop_indices:
                point=mesh.vertices[mesh.loops[loop_index].vertex_index].co
                angle = 0.317 * (VARIANT_SEED % 19) + 0.19*int(face.center.x*1.8+face.center.z*0.7)
                u,v=point[axes[0]]*0.5,point[axes[1]]*0.5
                uv.data[loop_index].uv=(u*math.cos(angle)-v*math.sin(angle)+VARIANT_SEED*0.173,
                    u*math.sin(angle)+v*math.cos(angle)+VARIANT_SEED*0.219)
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        if self.name not in ("MenuBanner", "MenuBackdrop", "MenuGreenTower"):
            bevel=obj.modifiers.new("Stone edge wear", "BEVEL")
            bevel.width=0.012 if self.name=="MenuStatue" else 0.025
            bevel.segments=1
        # Native noise displacement stays editable and is evaluated by both Eevee and the Ogre exporter.
        worn = obj.vertex_groups.new(name="Weathered surface")
        deform = set()
        for face in mesh.polygons:
            material = mesh.materials[face.material_index].name
            if material not in ("MenuFlame", "MenuFlameCore", "MenuEmber", "MenuSpireGlow", "MenuSpireBeam", "MenuEmberCrack", "MenuWindowGlow", "MenuCampaignMap", "MenuPuddle", "MenuSky", "MenuCloud", "MenuHorizonGlow", "MenuHorizonDark", "MenuTitleLetters", "MenuTitleCrest", "MenuGateEyes", "MenuLavaCrack", "MenuWeb", "MenuCrowBlack", "MenuBone", "MenuDriedBlood"):
                deform.update(face.vertices)
        if deform:
            worn.add(sorted(deform), 1.0, "REPLACE")
            delicate=set()
            for face in mesh.polygons:
                if mesh.materials[face.material_index].name in ("MenuDemonStone","MenuIron","MenuCorrodedIron"):
                    delicate.update(face.vertices)
            if delicate:
                worn.add(sorted(delicate),0.18,"REPLACE")
            texture = bpy.data.textures.new(self.name+" fracture noise",type="CLOUDS")
            texture.noise_scale = 0.46
            texture.noise_depth = 2
            displacement = obj.modifiers.new("Eroded stone noise", "DISPLACE")
            displacement.texture = texture
            displacement.vertex_group = worn.name
            displacement.strength = 0.11*VARIANT_DAMAGE
            displacement.mid_level = 0.52
        obj["contact_corrections"] = json.dumps(self.contact_corrections)
        return obj



# Add branching soot-dark fissures and an irregular scorched patch to a masonry face.
def weather_marks(builder, x, y, z, width, height):
    builder.prism([(x-width*0.48,z-height*0.48),(x+width*0.40,z-height*0.37),
        (x+width*0.29,z+height*0.22),(x+width*0.10,z+height*0.55),
        (x-width*0.18,z+height*0.39),(x-width*0.40,z-height*0.07)],y-0.012,y,"MenuSoot")
    for side in (-1,1):
        points=[(x+side*width*0.55,z+height*0.7),(x+side*width*0.24,z+height*0.33),
            (x+side*width*0.31,z+height*0.03),(x+side*width*0.11,z-height*0.37)]
        for first,last in zip(points,points[1:]):
            builder.prism([(first[0]-0.025,first[1]),(first[0]+0.025,first[1]),
                (last[0]+0.018,last[1]),(last[0]-0.018,last[1])],y-0.025,y-0.018,"MenuBlack")


# Suspend an empty corroded cage from a visibly sagging, partly broken chain.
def hanging_cage(builder, x, y, z, damage):
    for i in range(9):
        builder.link((x+0.10*math.sin(i*0.7),y,z+1.65+i*0.18),0.12,bool(i%2))
    for level,radius in ((0,0.55),(0.18,0.58),(1.26,0.52)):
        for i in range(9):
            angle=i*2*math.pi/9
            next_angle=(i+1)*2*math.pi/9
            builder.segment((x+radius*math.cos(angle),y+radius*math.sin(angle),z+level),
                (x+radius*math.cos(next_angle),y+radius*math.sin(next_angle),z+level),0.035,0.035,"MenuCorrodedIron",5)
    for i in range(9):
        angle=i*2*math.pi/9
        bottom=(x+0.55*math.cos(angle),y+0.55*math.sin(angle),z)
        top=(x+0.52*math.cos(angle),y+0.52*math.sin(angle),z+1.26)
        if i==damage:
            builder.segment(bottom,(top[0]+0.18,top[1]-0.11,z+0.73),0.033,0.024,"MenuCorrodedIron",5)
        else:
            builder.segment(bottom,top,0.033,0.033,"MenuCorrodedIron",5)
        builder.segment(top,(x,y,z+1.65),0.030,0.020,"MenuCorrodedIron",5)
        builder.segment(bottom,(x,y,z-0.12),0.027,0.020,"MenuCorrodedIron",5)


# Build a ruined gatehouse with a horned skull crown, iron points and worn hanging chains.
# Give the fractured gate arch a rusty spike grille and a chained bestial crown.
def gate():
    b=MeshBuilder("MenuGate")
    rng=random.Random(207)
    spring,radius,outer=6.0,4.5,6.2
    poly=[(radius,0),(outer,0),(outer,spring)]
    poly.extend((outer*math.cos(i*math.pi/32),spring+outer*math.sin(i*math.pi/32)) for i in range(1,33))
    poly.extend([(-outer,0),(-radius,0),(-radius,spring)])
    poly.extend((radius*math.cos(math.pi-i*math.pi/28),spring+radius*math.sin(math.pi-i*math.pi/28)) for i in range(1,29))
    b.prism(poly,0.0,3.5,"MenuDarkStone")
    for side in (-1,1):
        for row in range(12):
            for col in range(2):
                if (side,row,col) in ((-1,8,1),(1,3,0),(1,10,1)):
                    continue
                b.box((side*(5.14+col*1.15)+rng.uniform(-0.035,0.035),-0.38+rng.uniform(-0.055,0.045),row*0.97+0.48),
                    (1.11+rng.uniform(-0.08,0.03),1.03,1.03+rng.uniform(-0.03,0.02)))
        b.box((side*5.9,-0.52,0.3),(3.0,1.55,0.6))
        for x in (side*5.0,side*6.8):
            b.box((x,-0.42,6.2),(0.28,1.26,12.4))
        for i in range(18):
            t=i/17
            b.link((side*(5.4+3.5*t),-1.15-1.45*t+0.05*math.sin(i*1.7),
                11.8+1.15*t-(1.6 if side<0 else 1.15)*math.sin(t*math.pi)),0.26+rng.uniform(-0.025,0.015),bool(i%2))
    b.arch(0,-0.48,spring,radius,1.20,1.2,30)
    b.arch(0,-0.57,spring,radius+1.28,0.22,1.3,34)
    for x in (-5.4,-4.1,-2.7,-1.35,0,1.35,2.7,4.1,5.4):
        z=spring+math.sqrt(max(0,outer*outer-x*x))
        if x in (-2.7,4.1):
            b.prism([(x-0.36,z),(x+0.36,z),(x+0.24,z+0.31),(x-0.18,z+0.62)],-1.05,1.45)
        else:
            b.box((x,0.2,z+0.38),(0.72,2.5,0.75))
            b.column((x,-0.70,z+0.75),0.17,0.75+rng.uniform(-0.13,0.20),0,"MenuIron",7)
    for i in range(23):
        x=-4.4+i*0.4
        top=spring+math.sqrt(max(0,radius*radius-x*x))-0.14
        b.box((x,0.42,(0.4+top)/2),(0.11,0.18,top-0.4),"MenuIron")
        b.column((x,0.42,0.18),0.13,0.38,0,"MenuIron",5)
    for z in (0.9,2.8,4.8,6.6,8.3):
        width=2*radius if z<=spring else 2*math.sqrt(radius*radius-(z-spring)**2)
        b.box((0,0.35,z),(width,0.22,0.15),"MenuIron")
    for side in (-1,1):
        b.box((side*3.8,2.6,4.1),(0.3,0.15,3.2),"MenuWindowGlow")
        weather_marks(b,side*5.7,-0.915,4.4,0.88,2.1)
        for i in range(7):
            b.oval((side*rng.uniform(4.8,7.1),rng.uniform(-2.4,-0.6),rng.uniform(0.05,0.22)),
                (rng.uniform(0.18,0.48),rng.uniform(0.18,0.43),rng.uniform(0.15,0.36)),"MenuRoughStone",10,6)
    crown_start=len(b.vertices)
    b.prism([(-0.39,11.46),(-0.80,12.32),(-0.70,13.32),(-0.36,13.83),
        (0.13,13.96),(0.61,13.61),(0.82,12.57),(0.49,11.55),(0,11.16)],-1.71,-0.76,"MenuCarvedStone")
    b.segment((0,-1.33,13.36),(-0.08,-1.90,12.43),0.30,0.25,"MenuCarvedStone",5)
    b.segment((-0.08,-1.90,12.43),(-0.05,-2.66,11.56),0.26,0.20,"MenuCarvedStone",5)
    b.prism([(-0.18,11.75),(0.10,11.68),(0.15,11.48),(-0.07,11.32),
        (-0.21,11.52)],-2.86,-2.65,"MenuBlack")
    for side in (-1,1):
        b.prism([(side*0.15,12.89),(side*0.65,13.14),(side*0.71,12.88),
            (side*0.54,12.51),(side*0.27,12.42)],-1.77,-1.70,"MenuBlack")
        b.prism([(side*0.29,12.78),(side*0.48,12.89),(side*0.43,12.72),
            (side*0.33,12.64)],-1.775,-1.77,"MenuGateEyes")
        b.segment((side*0.10,-1.90,13.08),(side*0.83,-1.65,13.25),0.14,0.10,"MenuCarvedStone",5)
        b.segment((side*0.72,-1.64,12.48),(side*0.49,-2.30,11.43),0.17,0.09,"MenuCarvedStone",5)
        b.segment((side*0.49,-2.30,11.43),(side*0.25,-2.65,11.07),0.10,0.06,"MenuCarvedStone",5)
        horn=[(side*0.56,-1.17,13.43),(side*1.13,-1.09,13.75),
            (side*1.51,-1.04,14.31),(side*1.60,-0.98,14.91),(side*1.37,-1.0,15.28)]
        if side<0:
            horn=horn[:4]
        for index in range(len(horn)-1):
            b.segment(horn[index],horn[index+1],0.32-index*0.070,
                0.25-index*0.070 if index<len(horn)-2 else (0.10 if side<0 else 0.006),"MenuCarvedStone",7)
            if index>0:
                x,y,z=horn[index]
                b.prism([(x-side*0.15,z-0.11),(x+side*0.24,z+0.20),
                    (x+side*0.19,z-0.14)],y-0.20,y+0.11,"MenuCarvedStone")
        b.segment((side*0.32,-2.51,11.70),(side*0.35,-2.65,10.77 if side<0 else 11.01),0.13,0.003,"MenuBone",5)
        for i in range(6):
            b.link((side*(0.83+i*0.18),-1.28+i*0.05,12.48-i*0.11),0.13,bool(i%2))
        b.segment((side*0.63,-1.85,12.08),(side*1.28,-0.68,11.67),0.075,0.075,"MenuCorrodedIron",4)
        b.box((side*1.25,-0.76,11.75),(0.27,0.22,0.48),"MenuCorrodedIron")
    b.segment((-0.49,-2.30,11.43),(-0.04,-2.55,10.63),0.12,0.055,"MenuBone",5)
    b.segment((-0.04,-2.55,10.63),(0.25,-2.62,10.81),0.055,0.025,"MenuBone",5)
    for x in (-0.16,0.04):
        b.segment((x,-2.65,11.33),(x-0.02,-2.69,11.03),0.065,0.003,"MenuCarvedStone",5)
    b.prism([(-0.06,13.89),(0.0,13.79),(-0.11,13.28),(0.06,12.99),
        (0.03,12.95),(-0.17,13.27),(-0.05,13.77)],-1.745,-1.73,"MenuBlack")
    b.segment((-0.56,-1.80,13.58),(0.51,-1.80,13.48),0.062,0.062,"MenuCorrodedIron",4)
    for x in (-1.1,-0.75,-0.43,0.49,0.84,1.16):
        b.segment((x,-1.15,11.48),(x*1.07,-1.20,10.82),0.11,0.003,"MenuCorrodedIron",5)
    for i in range(5):
        x=-0.50+i*0.23
        b.prism([(x,11.12),(x+0.08,10.71),(x+0.04,10.20),(x-0.03,10.61)],0.21,0.23,"MenuDriedBlood")
    for index in range(crown_start,len(b.vertices)):
        x,y,z=b.vertices[index]
        b.vertices[index]=(x*1.12,y-0.18,14.5+(z-12.2)*1.12)
    # A fractured crown pier carries the raised skull; its clamps penetrate actual masonry.
    b.box((0,0.65,13.0),(2.20,1.2,4.0),"MenuDarkStone")
    b.box((0,0.30,14.00),(4.00,1.10,0.62),"MenuDarkStone")
    for side in (-1,1):
        b.segment((side*1.4,-0.96,14.0),(side*1.4,0.46,14.0),0.105,0.105,"MenuCorrodedIron",6)
    return b.finish()


# Build damaged buttressed masonry with broken spiked crenels while retaining both menu alcoves.
def wall():
    b=MeshBuilder("MenuWallSegment")
    rng=random.Random(307+VARIANT_SEED)
    for row in range(11):
        for col in range(16):
            x=-10.2+col*1.34+(0.22 if row%2 else 0)
            if 6<=col<=8 and row<4:
                continue
            fracture_x = -3.5+math.sin(row*1.21+VARIANT_SEED)*0.7
            crown = 9.3 - 2.5*math.exp(-((x-(4.5 if VARIANT_SEED%2 else -5.7))/3.1)**2)
            if (row,col) in ((8,2),(6,12),(9,13),(4,4)) or row*0.88 > crown or (row>2 and abs(x-fracture_x)<0.70):
                continue
            b.box((x+rng.uniform(-0.06,0.06),0.5+rng.uniform(-0.08,0.06),row*0.88+0.44),
                (1.30+rng.uniform(-0.10,0.02),2.8,0.97+rng.uniform(-0.03,0.02)))
    for x in range(-10,11):
        top = 9.6 - 2.5*math.exp(-((x-(4.5 if VARIANT_SEED%2 else -5.7))/3.1)**2)
        b.box((x,0.5,top),(0.94,3.45,rng.uniform(0.24,0.60)))
        if x%2 == 0 and rng.random()>0.35:
            b.prism([(x-0.48,top),(x+0.48,top),(x+0.24,top+rng.uniform(0.25,1.1)),(x-0.22,top+rng.uniform(0.3,1.3))],-1.30,1.6)
            b.column((x,-0.92,top+0.8),0.18,rng.uniform(0.20,1.0),0,"MenuCorrodedIron",7)
    for x in (-9.7,-5.0,4.5,9.7):
        b.box((x,-0.65,4.8),(1.05,4.1,9.6))
        b.box((x,-1.4,0.5),(1.5,4.4,1.0))
    b.arch(-1.2,-0.8,2.0,1.9,0.62,2.5,18)
    for z in (0.55,1.25,1.95):
        b.box((-1.2,1.0,z),(3.3,0.9,0.12),"MenuWood")
        for x in (-2.4,-1.85,-1.3,-0.75,-0.2):
            b.column((x,0.9,z+0.08),0.10,0.36,material="MenuParchment",sides=8)
    b.box((4.0,-1.35,1.15),(3.0,1.0,0.20),"MenuWood")
    for x in (2.8,5.2):
        b.box((x,-1.35,0.55),(0.16,0.75,1.1),"MenuWood")
    for x in (3.3,4.0,4.7):
        b.box((x,-1.15,1.45),(0.08,0.08,0.6),"MenuWood")
        b.box((x,-1.15,1.77),(0.4,0.12,0.15),"MenuIron")
    for x in (-7,7):
        weather_marks(b,x,-0.99,9.0,0.8,1.7)
        b.box((x,-0.94,7.2),(0.42,0.03,1.8),"MenuWindowGlow")
        b.arch(x,-1.04,8.1,0.23,0.18,0.25,9)
    for x in (-4.8,2.4,9.1):
        weather_marks(b,x,-0.925,4.5,0.68,2.0)
    for x in (-9.6,-8.7,-4.3,-2.0,0.8,3.6,5.4,9.4):
        weather_marks(b,x,-0.925,1.25,0.65,2.2)
    for i in range(24):
        b.oval((rng.uniform(-10.7,10.7),rng.uniform(-2.9,-1.2),rng.uniform(0,0.20)),
            (rng.uniform(0.12,0.65),rng.uniform(0.15,0.47),rng.uniform(0.12,0.43)),"MenuRoughStone",10,6)
    return b.finish()


# Build a weathered tower with missing masonry, broken iron-tipped crenels and an accessible platform.
def tower():
    b=MeshBuilder("MenuTower")
    rng=random.Random(407+VARIANT_SEED)
    collapsed = VARIANT_DAMAGE > 1.3
    for row in range(13):
        for col in range(4):
            if (row,col) in ((8,0),(10,3),(3,1)) or (collapsed and row>=8 and col<2) or (row>=11 and col==0):
                continue
            b.box((-1.74+col*1.16+rng.uniform(-0.045,0.045),-0.25+rng.uniform(-0.05,0.04),row*0.94+0.46),
                (1.12+rng.uniform(-0.09,0.025),4.4,1.02+rng.uniform(-0.03,0.02)))
    for z in (0.5,4.4,8.5,12.3):
        if collapsed and z>8:
            b.box((1.40,-0.25,z),(2.4,4.95,0.32))
        else:
            b.box((0,-0.25,z),(5.2,4.95,0.32))
    if collapsed:
        b.box((1.35,0.35,12.8),(2.8,4.4,0.65))
        b.box((-0.4,0.4,10.1),(1.1,2.3,0.65))
    else:
        b.box((0,-0.25,12.8),(5.8,5.7,0.65))
    for side in (-1,1):
        for x in (-2.35,0,2.35):
            if collapsed and x<=0:
                continue
            if side<0 and x==2.35:
                b.prism([(x-0.45,13.07),(x+0.45,13.07),(x+0.18,13.61),(x-0.31,13.37)],side*2.3-0.73,side*2.3+0.23)
            else:
                b.box((x,side*2.3-0.25,13.75+rng.uniform(-0.12,0.07)),(0.9,0.95,1.35))
                b.column((x,side*2.3-0.25,14.42),0.19,0.90+rng.uniform(-0.1,0.20),0,"MenuIron",7)
        if not collapsed or side>0:
            b.box((side*2.35,-0.25,13.75),(0.95,0.95,1.35))
    for z in (4.2,7.8,10.7):
        weather_marks(b,0,-2.51,z+1.55,0.98,1.1)
        b.box((0,-2.48,z),(0.4,0.025,1.45),"MenuWindowGlow")
        b.arch(0,-2.58,z+0.73,0.22,0.19,0.2,9)
    weather_marks(b,-1.6,-2.505,6.0,0.55,2.8)
    for x in (-1.72,-0.85,0.78,1.65):
        weather_marks(b,x,-2.505,1.4,0.55,2.35)
    for i in range(15):
        b.oval((rng.uniform(-3,3),rng.uniform(-3.4,-2.5),rng.uniform(0,0.2)),
            (rng.uniform(0.14,0.58),rng.uniform(0.14,0.44),rng.uniform(0.13,0.41)),"MenuRoughStone",10,6)
    if collapsed:
        b.column((1.4,0.9,13.15),0.55,1.25,0,"MenuDarkStone",9)
        for i in range(18):
            b.oval((rng.uniform(-4.2,-1),rng.uniform(-3.5,0),rng.uniform(0.1,0.6)),
                (rng.uniform(0.3,0.8),rng.uniform(0.3,0.9),rng.uniform(0.2,0.65)),"MenuRoughStone",9,6)
    else:
        b.column((0.15,0.9,13.15),0.82,2.8,0,"MenuDarkStone",9)
    return b.finish()


# Carve an angular, crouching skeletal guardian with open jaws and torn bat membranes.
def statue():
    b=MeshBuilder("MenuStatue")
    b.box((0,0,0.30),(3.4,3.0,0.60))
    b.box((0,0,0.82),(3.0,2.7,0.42))
    b.box((0,0,2.0),(2.55,2.2,2.0))
    for side in (-1,1):
        b.box((side*1.13,-0.9,2.0),(0.28,0.32,1.75),"MenuDarkStone")
    b.box((0,0,3.18),(3.2,2.8,0.40))
    b.box((0,0,3.50),(2.8,2.5,0.26))
    stone="MenuDemonStone"
    damaged=VARIANT_DAMAGE>1.3
    lean=-0.17 if damaged else 0.13
    b.prism([(-0.42,4.35),(0.43,4.30),(0.27,5.06),(0.42,5.64),
        (0.86,6.27),(0.61,6.72),(-0.56,6.78),(-0.88,6.29),(-0.38,5.61),(-0.23,5.05)],-0.39,0.38,stone)
    b.segment((lean,0.29,4.57),(lean,0.40,6.71),0.16,0.20,stone,6)
    for row in range(5):
        z=5.52+row*0.19
        width=0.45+row*0.065
        for side in (-1,1):
            b.segment((side*0.06,-0.47,z-0.13),(side*width,-0.51,z+0.08),0.065,0.075,stone,5)
            b.segment((side*width,-0.51,z+0.08),(side*(width+0.09),0.06,z+0.16),0.075,0.045,stone,5)
    b.segment((0,-0.52,5.68),(lean,-0.60,6.62),0.065,0.09,stone,5)
    b.segment((lean,0.03,6.44),(lean,-0.91,7.02),0.32,0.25,stone,7)
    b.prism([(lean-0.36,7.02),(lean-0.42,7.48),(lean-0.19,7.79),
        (lean+0.16,7.75),(lean+0.40,7.46),(lean+0.31,7.03),(lean,6.87)],-1.08,-0.33,stone)
    b.segment((lean,-0.55,7.63),(lean,-1.49,7.32),0.29,0.21,stone,5)
    b.segment((lean,-1.04,7.30),(lean,-1.95,7.13),0.27,0.20,stone,5)
    for side in (-1,1):
        b.prism([(lean+side*0.07,7.20),(lean+side*0.19,7.13),
            (lean+side*0.13,7.04),(lean+side*0.04,7.09)],-2.16,-2.13,"MenuBlack")
    b.prism([(lean-0.37,7.03),(lean+0.34,7.03),(lean+0.26,6.58),
        (lean-0.04,6.43),(lean-0.31,6.58)],-1.99,-1.73,"MenuBlack")
    b.segment((lean-0.37,-1.21,6.93),(lean-0.25,-2.01,6.47),0.10,0.095,stone,5)
    b.segment((lean+0.34,-1.21,6.93),(lean+0.21,-2.01,6.47),0.10,0.075,stone,5)
    b.segment((lean-0.25,-2.01,6.47),(lean+0.21,-2.01,6.47),0.095,0.075,stone,5)
    for i in range(7):
        x=lean-0.27+i*0.083
        if not (damaged and i in (1,5)):
            b.segment((x,-2.05,7.10),(x+0.025,-2.08,6.81-(0.09 if i in (0,6) else 0)),0.045,0.003,stone,5)
        if i%2==0:
            b.segment((x,-2.03,6.50),(x-0.01,-2.08,6.69),0.035,0.002,stone,5)
    for side in (-1,1):
        b.prism([(lean+side*0.12,7.43),(lean+side*0.39,7.62),
            (lean+side*0.42,7.43),(lean+side*0.28,7.28),(lean+side*0.17,7.29)],-1.105,-1.07,"MenuBlack")
        b.segment((lean+side*0.09,-1.16,7.49),(lean+side*0.43,-1.04,7.70),0.105,0.055,stone,5)
        b.segment((lean+side*0.48,-0.90,7.20),(lean+side*0.34,-1.47,7.04),0.12,0.045,stone,5)
        horn=[(lean+side*0.34,-0.48,7.70),(lean+side*0.69,-0.22,8.13),
            (lean+side*0.91,-0.10,8.65),(lean+side*0.80,-0.24,9.02),(lean+side*0.57,-0.44,9.20)]
        if side==(-1 if damaged else 1):
            horn=horn[:3]
        for index in range(len(horn)-1):
            b.segment(horn[index],horn[index+1],0.19-index*0.042,
                0.15-index*0.042 if index<len(horn)-2 else (0.075 if len(horn)==3 else 0.002),stone,6)
        b.segment((side*0.79,0.04,6.38),(side*1.26,-0.18,5.33),0.24,0.15,stone,6)
        b.segment((side*1.26,-0.18,5.33),(side*1.03,-1.03,4.03),0.15,0.105,stone,6)
        b.segment((side*1.03,-1.03,4.03),(side*0.91,-1.33,3.86),0.13,0.10,stone,5)
        b.segment((side*0.38,0.13,4.66),(side*1.10,0.19,4.98),0.28,0.20,stone,6)
        b.segment((side*1.10,0.19,4.98),(side*0.91,-0.90,3.88),0.20,0.13,stone,6)
        b.segment((side*0.91,-0.90,3.88),(side*0.89,-1.52,3.70),0.15,0.09,stone,6)
        for i in range(4):
            x=side*(0.64+i*0.18)
            y=-1.42-0.16*math.sin(i*0.9)
            b.segment((x,y,3.92),(x+side*0.045,y-0.45,3.74),0.060,0.038,stone,5)
            b.segment((x+side*0.045,y-0.45,3.74),(x+side*0.035,y-0.64,3.46),0.038,0.002,stone,5)
        b.prism([(side*0.33,6.70),(side*1.05,6.36),(side*0.88,5.99)],0.36,0.64,stone)
        for i in range(4):
            b.segment((side*0.58,0.47,6.48-i*0.17),(side*(0.89+i*0.07),0.57,6.71-i*0.10),0.075,0.002,stone,5)
        broken_side = -1 if VARIANT_SEED%2==0 else 1
        root=(side*0.79,0.55,6.15)
        knuckle=(side*1.42,0.65,8.13)
        tips=[(side*2.18,0.77,9.10),(side*3.10,0.83,8.12),
            (side*3.38,0.78,6.90),(side*2.83,0.70,5.70),(side*1.88,0.60,5.11)]
        if side==broken_side:
            tips[0]=(side*1.79,0.70,8.43)
            tips[2]=(side*2.76,0.78,6.94)
        b.segment(root,knuckle,0.17,0.12,stone,6)
        for tip in tips:
            b.segment(knuckle,tip,0.11,0.012,stone,5)
        for index in range(len(tips)-1):
            tip_a,tip_b=Vector(tips[index]),Vector(tips[index+1])
            middle=(tip_a+tip_b)*0.5
            notch=middle+(Vector(knuckle)-middle)*(0.28 if damaged else 0.20)
            vertices=[Vector(knuckle),tip_a,tip_a.lerp(notch,0.82),
                notch+Vector((side*0.11,-0.02,0.05)),tip_b.lerp(notch,0.74),tip_b]
            centre=sum(vertices,Vector())/len(vertices)
            inner=[centre+(v-centre)*(0.23 if damaged else 0.15) for v in vertices]
            for edge in range(len(vertices)):
                next_edge=(edge+1)%len(vertices)
                if damaged and index==2 and edge in (2,3):
                    continue
                first=len(b.vertices)
                b.vertices.extend(tuple(v) for v in (vertices[edge],vertices[next_edge],inner[next_edge],inner[edge]))
                b.faces.extend([(first,first+1,first+2),(first,first+2,first+3)])
                b.face_materials.extend([stone,stone])
            mid=(vertices[1]+vertices[2])*0.5
            inward=mid+(Vector(knuckle)-mid)*0.23
            b.segment(tuple(mid),tuple(inward),0.025,0.012,stone,5)
    for z in (4.66,5.0,5.36,5.73,6.09,6.45):
        b.segment((lean,0.51,z),(lean+0.08,0.91,z+0.27),0.10,0.003,stone,5)
    b.prism([(-0.28,6.20),(-0.23,6.21),(-0.11,5.87),(-0.20,5.59),(0.04,5.29),
        (-0.02,5.25),(-0.27,5.59),(-0.18,5.87)],-0.545,-0.53,"MenuBlack")
    for i in range(7):
        x=-1.25+((i*0.51+VARIANT_SEED*0.17)%2.5)
        b.oval((x,-1.15,3.68),(0.12,0.13,0.07),"MenuChippedStone",7,4)
    return b.finish()


# Build a worn coal bowl without rigid flame geometry; animated fire is supplied by particles or volume.
def brazier():
    b=MeshBuilder("MenuBrazier")
    b.box((0,0,0.18),(1.65,1.65,0.36))
    b.column((0,0,0.36),0.50,2.35,0.34,sides=12)
    b.column((0,0,2.71),0.35,0.48,0.94,"MenuIron",18)
    b.column((0,0,3.19),0.94,0.12,material="MenuIron",sides=18)
    b.column((0,0,3.31),0.78,0.10,material="MenuEmber",sides=16)
    for i in range(10):
        if i in ((VARIANT_SEED%7),((VARIANT_SEED%7)+3)%10):
            continue
        a=i*math.pi/5
        b.column((0.84*math.cos(a),0.84*math.sin(a),3.13),0.065,0.24+0.2*abs(math.sin(i+VARIANT_SEED)),material="MenuCorrodedIron",sides=6)
    return b.finish()


# Create scorched, dirty red cloth and a fractured horned-skull three-blade iron crest on the existing cloth rig.
def banner():
    b=MeshBuilder("MenuBanner")
    b.box((0,0,0),(2.4,0.13,0.13),"MenuIron")
    for row in range(13):
        for col in range(7):
            x=-1.4+col*(2.8/6)
            length=0.34 if VARIANT_SEED%2 else 0.43
            z=-row*length
            y=0.10*math.sin(x*5)+0.03*row*math.sin(x*4)
            if row>=10:
                z-=0.10*(col%3)+0.13*math.sin(col*2.8+row)
            if row==12:
                z+=0.14+(0.36 if col in (1,5) else -0.12)
            b.vertices.append((x,y,z))
    start=len(b.vertices)-13*7
    for row in range(12):
        for col in range(6):
            if (row,col) in ((6,1),(7,1),(10,5),(11,5),(11,0)) or (VARIANT_SEED%2 and (row,col) in ((4,4),(5,4),(8,2),(9,2),(10,2),(11,2))):
                continue
            i=start+row*7+col
            b.faces.append((i,i+1,i+8,i+7))
            b.face_materials.append("MenuClothFadedB" if VARIANT_SEED%2 else "MenuClothFadedA")
    symbols=[
        [(-0.55,-1.12),(-0.12,-0.88),(0.42,-1.02),(0.58,-1.49),(0.29,-1.88),(-0.22,-1.95),(-0.57,-1.54)],
        [(-0.44,-1.07),(-0.95,-0.63),(-0.82,-1.20),(-0.54,-1.45)],
        [(0.32,-1.01),(0.78,-0.51),(0.73,-1.10),(0.44,-1.39)],
        [(-0.37,-1.81),(-0.53,-2.82),(-0.30,-2.60),(-0.15,-1.90)],
        [(-0.08,-1.89),(-0.11,-3.29),(0.15,-2.87),(0.11,-1.87)],
        [(0.18,-1.81),(0.37,-2.76),(0.62,-2.97),(0.42,-1.74)]
    ]
    for polygon in symbols:
        first=len(b.vertices)
        for x,z in polygon:
            y=0.10*math.sin(x*5)+0.03*(-z/length)*math.sin(x*4)-0.16
            b.vertices.append((x,y,z))
        b.faces.append(tuple(first+i for i in range(len(polygon))))
        b.face_materials.append("MenuBannerSymbol")
    obj=b.finish()
    arm_data=bpy.data.armatures.new("BannerArmature")
    arm=bpy.data.objects.new("BannerArmature",arm_data)
    bpy.context.scene.collection.objects.link(arm)
    obj.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="EDIT")
    for i in range(3):
        bone=arm.data.edit_bones.new("Cloth%d"%i)
        bone.head=(0,0,-i*1.1)
        bone.tail=(0,0,-(i+1)*1.1)
        if i:
            bone.parent=arm.data.edit_bones["Cloth%d"%(i-1)]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm["ogre_bone_order"]=["Cloth0","Cloth1","Cloth2"]
    for i in range(3):
        obj.vertex_groups.new(name="Cloth%d"%i)
    for vertex in obj.data.vertices:
        depth=min(2.0,max(0.0,-vertex.co.z/1.1))
        lo=int(depth)
        hi=min(2,lo+1)
        blend=depth-lo
        obj.vertex_groups["Cloth%d"%lo].add([vertex.index],1.0-blend,"REPLACE")
        if blend>0 and hi!=lo:
            obj.vertex_groups["Cloth%d"%hi].add([vertex.index],blend,"REPLACE")
    modifier=obj.modifiers.new("Cloth wave","ARMATURE")
    modifier.object=arm
    obj.parent=arm
    for frame in (0,12,24,36,48,60,72,84,96):
        for i in range(3):
            bone=arm.pose.bones["Cloth%d"%i]
            bone.rotation_mode="QUATERNION"
            from mathutils import Quaternion
            angle=math.sin(frame/96*2*math.pi+i*0.65)*0.06*i
            bone.rotation_quaternion=Quaternion((0,0,1),angle)
            bone.keyframe_insert("rotation_quaternion",frame=frame,group=bone.name)
    arm.animation_data.action.name="Wave"
    arm.animation_data.action["ogre_length"]=4.0
    bpy.context.scene.frame_set(0)
    return obj,arm



# Build the left gathering arcade as a deep stone structure with dark recesses.
def arches():
    b=MeshBuilder("MenuArches")
    for row in range(8):
        for col in range(8):
            if (row,col) in ((6,2),(7,2),(3,6)):
                continue
            b.box((-6.9+col*1.95,0,row+0.5),(1.84,4.0,1.08),"MenuDarkStone")
    for x in (-7,-2.34,2.34,7):
        b.box((x,0,11.85),(1.15,3.1,8.4))
        b.box((x,0,0.35),(1.65,3.65,0.70))
    for x in (-6.8,-4.1,-1.4,2.2,4.9,7.1):
        b.box((x,0,17.9+0.13*math.sin(x)),(1.8+0.4*math.sin(x),3.7,0.48))
    b.box((0,0,18.04),(15.6,3.35,0.30))
    for x in (-6,-3,0,3,6):
        b.box((x,0,18.43),(0.85,3.4,0.8))
    return b.finish()


# Build a dark many-spired tower with internal green windows, fractured light and a vertical summit beam.
def green_tower():
    b=MeshBuilder("MenuGreenTower")
    rng=random.Random(64)
    for i in range(15):
        a=i*2.399
        r=rng.uniform(0.2,4.0)
        b.oval((r*math.cos(a),r*math.sin(a),rng.uniform(0.4,2.3)),
            (rng.uniform(1.0,2.3),rng.uniform(1.0,2.3),rng.uniform(1.0,2.2)),"MenuDarkStone",15,10)
    for row in range(12):
        z=3.5+row*1.22
        for col in range(5):
            if col==2 and row in (3,4,7,8,10,11):
                continue
            b.box((-1.76+col*0.88,-2.12,z),(0.83,0.90,1.15),"MenuDarkStone")
            if not (row==9 and col==0):
                b.box((-1.76+col*0.88,2.03,z),(0.83,0.90,1.15),"MenuDarkStone")
        b.box((-2.18,0,z),(0.78,4.35,1.15),"MenuDarkStone")
        b.box((2.15,0,z),(0.78,4.35,1.15),"MenuDarkStone")
    for z in (7.7,12.5,16.2):
        b.box((0,-2.10,z),(0.28,0.04,1.7),"MenuSpireGlow")
        b.arch(0,-2.48,z+0.85,0.22,0.17,0.30,9)
        b.box((-2.59,-0.65,z+0.25),(0.025,0.26,1.45),"MenuSpireGlow")
    b.box((0,0,18.0),(5.2,5.3,0.42),"MenuDarkStone")
    b.column((0,0,18.2),1.03,3.1,0.78,"MenuDarkStone",9)
    b.column((0.04,-0.02,21.3),0.80,2.8,0.42,"MenuDarkStone",7)
    b.column((0.06,-0.03,24.1),0.44,1.7,0,"MenuCorrodedIron",7)
    summit=b.vertices[-1]
    for index in range(7):
        angle=index*2*math.pi/7
        x,y=1.80*math.cos(angle),1.82*math.sin(angle)
        height=(5.5,3.8,4.8,2.7,5.9,4.2,5.1)[index]
        b.column((x,y,18.2),0.39,height-1.8,0.23,"MenuDarkStone",6)
        b.column((x+0.07,y-0.05,16.4+height),0.25,1.8,0,"MenuCorrodedIron",6)
        b.segment((x*1.15,y*1.15,17.4),(x*0.43,y*0.43,22.7),0.18,0.075,"MenuDarkStone",5)
        if index%2:
            b.box((x,y-0.38,19.3),(0.09,0.025,1.65),"MenuSpireGlow")
    for x,y,z,height in ((-3.4,-0.2,10.8,8.8),(3.2,0.6,13.2,8.6),(-1.2,3.0,14.4,8.7),(2.5,-2.4,10.5,7.4)):
        b.column((x,y,3.0),0.86,z-3.0,0.75,"MenuDarkStone",12)
        b.column((x,y,z),0.77,height-2.5,0.42,"MenuDarkStone",7)
        b.column((x+0.09,y-0.04,z+height-2.5),0.44,2.5,0,"MenuCorrodedIron",6)
        for side in (-1,1):
            b.segment((x+side*0.73,y,z-0.7),(x+side*0.29,y,z+height-1.7),0.13,0.05,"MenuDarkStone",5)
        b.box((x,y-0.87,z-1.6),(0.18,0.035,1.2),"MenuSpireGlow")
    for x,z in ((-1.3,5.0),(0.9,10.2),(-1.1,14.8)):
        b.prism([(x-0.035,z-1.3),(x+0.10,z-0.4),(x-0.03,z+0.4),(x+0.22,z+1.25),
            (x+0.29,z+1.26),(x+0.04,z+0.4),(x+0.17,z-0.4),(x+0.035,z-1.3)],-2.64,-2.61,"MenuSpireGlow")
    for radius in (0.10,0.24):
        b.column((summit[0],summit[1],summit[2]-0.04),radius,110-summit[2],radius,"MenuSpireBeam",20)
    return b.finish()


# Build broken, sunken and uneven flagstones with irregular puddles and scattered rubble.
def courtyard():
    b=MeshBuilder("MenuCourtyard")
    rng=random.Random(71)
    for row in range(30):
        y=-29+row*1.65
        for col in range(30):
            x=-25+col*1.75+(0.82 if row%2 else 0)+rng.uniform(-0.15,0.15)
            sx,sy=1.57+rng.uniform(-0.21,0.11),1.47+rng.uniform(-0.20,0.10)
            z=-0.10+rng.uniform(-0.24,0.12)
            if any(abs(x-gx)<sx/2+1.02 and abs(y-gy)<sy/2+1.62 for gx,gy in ((-12.6,-9.7),(12.5,-8.3))):
                continue
            b.box((x,y,-0.56),(sx+0.23,sy+0.22,0.46),"MenuDarkStone")
            if rng.random()<0.075:
                continue
            if rng.random()<0.33:
                b.prism([(x-sx/2,-0.55),(x+0.12,-0.55),(x-0.08,z+0.07),(x-sx/2+0.025,z+0.11)],
                    y-sy/2,y+sy/2,"MenuWetStone")
                b.prism([(x+0.20,-0.55),(x+sx/2,-0.55),(x+sx/2-0.025,z-0.03),(x+0.01,z+0.005)],
                    y-sy/2+0.08,y+sy/2-0.05,"MenuWetStone")
            else:
                poly=[(x-sx/2,-0.55),(x+sx/2,-0.55),(x+sx/2-0.025,z+0.07+rng.uniform(-0.04,0.05)),(x-sx/2+0.025,z+0.07)]
                b.prism(poly,y-sy/2,y+sy/2,"MenuWetStone")
            if -24<y<11 and rng.random()<0.24:
                edge=x+sx/2+0.03
                path=[(edge+rng.uniform(-0.014,0.014),y-sy*0.46+j*sy*0.23,z-0.025) for j in range(5)]
                if rng.random()<0.55:
                    path.extend([(edge+0.03,y+sy*0.48,z-0.025),
                        (x+sx*0.20,y+sy*0.5+0.045,z-0.025),
                        (x-sx*0.21,y+sy*0.5+0.03,z-0.025)])
                for a,c in zip(path,path[1:]):
                    direction=Vector(c)-Vector(a)
                    normal=Vector((-direction.y,direction.x,0)).normalized()*rng.uniform(0.012,0.028)
                    first=len(b.vertices)
                    b.vertices.extend(tuple(point) for point in (Vector(a)-normal,Vector(c)-normal,Vector(c)+normal,Vector(a)+normal))
                    b.faces.append(tuple(first+i for i in range(4)))
                    b.face_materials.append("MenuEmberCrack")
    # Individual substrate cells leave both excavated graves genuinely open to depth.
    b.contact_corrections.append("grave cutouts: two physical floor/substrate omissions")
    for i in range(23):
        x,y=rng.uniform(-20,20),rng.uniform(-24,13)
        rx,ry=rng.uniform(0.40,1.8),rng.uniform(0.26,1.1)
        start=len(b.vertices)
        for j in range(9):
            angle=j*2*math.pi/9
            rough=rng.uniform(0.75,1.15)
            b.vertices.append((x+rx*math.cos(angle)*rough,y+ry*math.sin(angle)*rough,-0.19))
        b.faces.append(tuple(start+j for j in range(9)))
        b.face_materials.append("MenuPuddle")
    # Large foreground rocks have separate unique source files and are configured individually.
    for i in range(76):
        x,y=rng.uniform(-22,22),rng.uniform(-20,13)
        b.box((x,y,rng.uniform(-0.03,0.11)),(rng.uniform(0.12,0.65),rng.uniform(0.15,0.58),rng.uniform(0.12,0.40)),"MenuRoughStone")
    for i in range(109):
        b.oval((rng.uniform(-18,18),rng.uniform(-22,12),rng.uniform(-0.09,0.05)),
            (rng.uniform(0.06,0.23),rng.uniform(0.07,0.28),rng.uniform(0.05,0.19)),"MenuRoughStone",8,5)
    for i in range(23):
        x,y=rng.uniform(-15,15),rng.uniform(-19,10)
        if i%2:
            b.segment((x,y,0.01),(x+0.39,y+0.17,0.07),0.06,0.055,"MenuBone",8)
            for dx in (0,0.39):
                b.oval((x+dx,y+(0.17 if dx else 0),0.06),(0.09,0.12,0.08),"MenuBone",8,5)
        else:
            b.prism([(x,0.07),(x+0.17,0.12),(x+0.58,0.04),(x+0.47,-0.01)],y,y+0.07,"MenuCorrodedIron")
            b.segment((x-0.2,y,0.04),(x,y,0.07),0.055,0.05,"MenuAgedWood",7)
            b.segment((x-0.02,y-0.19,0.06),(x+0.06,y+0.23,0.06),0.035,0.02,"MenuCorrodedIron",6)
    return b.finish()


# Build layered fractured ridges, distant fortress needles and a far left ruined arcade bridge.
def backdrop():
    b=MeshBuilder("MenuBackdrop")
    rng=random.Random(31)
    b.oval((0,45,0),(190,190,115),"MenuSky",48,24)
    for index,face in enumerate(b.faces):
        centre=tuple(sum(b.vertices[vertex][axis] for vertex in face)/len(face) for axis in range(3))
        if centre[1]>40 and -15<centre[2]<28:
            b.face_materials[index]="MenuHorizonGlow"
        elif centre[1]>40 and 28<=centre[2]<55:
            b.face_materials[index]="MenuHorizonDark"
    for layer in range(3):
        y=67+layer*20
        points=[(-120,-6)]
        for i in range(97):
            x=-120+i*2.55
            ridge=18+7*math.sin(i*0.11+layer*1.3)+4*math.sin(i*0.28+layer)
            ridge-=10*math.exp(-(x/23)**2)
            points.append((x,ridge+rng.uniform(-1.6,2.1)+layer*2))
        points.append((124,-6))
        b.prism(points,y,y+12,"MenuMountain")
        for i in range(27):
            x=rng.uniform(-100,100)
            height=rng.uniform(12,27)*(0.45 if abs(x)<20 else 1)
            width=rng.uniform(3.5,7)
            b.prism([(x-width,1),(x-width*0.65,height*0.39),
                (x-width*0.60,height*0.68),(x-width*0.29,height*0.64),
                (x-width*0.20,height*0.85),(x+width*0.13,height),
                (x+width*0.23,height*0.74),(x+width*0.44,height*0.77),
                (x+width*0.58,height*0.46),(x+width,2)],y-3,y+rng.uniform(2,6),"MenuMountain")
    for cluster,(cx,cy,base_height) in enumerate(((-42,64,28),(-28,76,25),(31,73,29),(47,85,23))):
        for index in range(13):
            x=cx+rng.uniform(-8,8)
            y=cy+rng.uniform(-4,5)
            h=base_height+rng.uniform(-13,4)
            radius=rng.uniform(0.42,1.05)
            b.column((x,y,0),radius*1.25,h*0.67,top=radius,material="MenuDistantStone",sides=7)
            b.column((x+0.11,y,h*0.67),radius*1.12,h*0.33,top=radius*0.72,material="MenuDistantStone",sides=7)
            b.column((x+0.14,y,h),radius*0.86,rng.uniform(2.5,5.0),0,"MenuDistantStone",6)
            for j in range(3):
                a=j*2*math.pi/3+cluster*0.7
                dx,dy=radius*math.cos(a),radius*math.sin(a)
                b.column((x+dx,y+dy,h-1.6),radius*0.23,rng.uniform(2,4),0,"MenuDistantStone",5)
            if index%3==0:
                b.prism([(x-radius*1.4,h*0.20),(x+radius*1.2,h*0.20),
                    (x+radius*1.3,h*0.37),(x+radius*0.7,h*0.34),
                    (x,h*0.40),(x-radius*1.4,h*0.36)],y-0.8,y+0.8,"MenuDistantStone")
    # This remote broken bridge is scenery behind the existing, unchanged gathering arches.
    for index in range(6):
        x=-60+index*6.5
        y=48+index*1.9
        spring=13.3+index*0.31
        radius=2.62
        for side in (-1,1):
            pier_x=x+side*3.04
            b.prism([(pier_x-0.47,0),(pier_x+0.53,0),(pier_x+0.43,spring+0.12),
                (pier_x-0.36,spring+0.28),(pier_x-0.52,spring*0.53)],y-0.82,y+0.82,"MenuDistantStone")
        for wedge in range(16):
            if index==1 and wedge in (3,4):
                continue
            a=math.pi*wedge/16+0.014
            c=math.pi*(wedge+1)/16-0.014
            b.prism([(x+radius*math.cos(a),spring+radius*math.sin(a)),
                (x+(radius+0.43)*math.cos(a),spring+(radius+0.43)*math.sin(a)),
                (x+(radius+0.43)*math.cos(c),spring+(radius+0.43)*math.sin(c)),
                (x+radius*math.cos(c),spring+radius*math.sin(c))],y-0.80,y+0.80,"MenuDistantStone")
        deck=spring+radius+0.61
        b.prism([(x-3.25,deck-0.27),(x+3.25,deck-0.27),
            (x+3.21,deck+0.17),(x+1.09,deck+0.07),(x-1.20,deck+0.23),
            (x-3.25,deck+0.16)],y-0.92,y+0.92,"MenuDistantStone")
        for post in range(4):
            if (index+post)%5==0:
                continue
            b.column((x-2.85+post*1.73,y-0.87,deck+0.12),0.10,
                0.45+(post%2)*0.30,0,"MenuDistantStone",5)
    for index in range(9):
        x=35+index*3.9+rng.uniform(-1.5,1.5)
        y=61+index*3.4+rng.uniform(-3,3)
        peak=rng.uniform(22,33)
        # Each crag has three spatially offset fractured needles, never a flat extruded profile.
        for spur in range(3):
            cx=x+(spur-1)*rng.uniform(1.1,2.0)
            cy=y+rng.uniform(-2.3,2.3)
            height=peak*(1 if spur==1 else rng.uniform(0.58,0.84))
            width=rng.uniform(1.3,2.5)*(1 if spur==1 else 0.63)
            depth=width*rng.uniform(0.61,1.25)
            lean_x=rng.uniform(-1.6,1.6)
            lean_y=rng.uniform(-1.2,1.2)
            first=len(b.vertices)
            sides=7
            for row,(level,spread) in enumerate(((0.0,1.0),(0.34,0.87),(0.60,0.56),(0.79,0.49),(0.93,0.21))):
                for edge in range(sides):
                    angle=edge*2*math.pi/sides+row*0.11
                    fracture=rng.uniform(0.72,1.19)
                    notch=0.49 if (edge+row+index+spur)%6==0 else 1
                    b.vertices.append((cx+width*spread*fracture*notch*math.cos(angle)+lean_x*level,
                        cy+depth*spread*fracture*math.sin(angle)+lean_y*level,
                        2+height*level+rng.uniform(-0.65,0.65)))
            b.faces.append(tuple(first+edge for edge in reversed(range(sides))))
            b.face_materials.append("MenuMountain")
            for row in range(4):
                for edge in range(sides):
                    a=first+row*sides+edge
                    c=first+row*sides+(edge+1)%sides
                    d=first+(row+1)*sides+(edge+1)%sides
                    e=first+(row+1)*sides+edge
                    b.faces.extend(((a,c,d),(a,d,e)))
                    b.face_materials.extend(("MenuMountain","MenuMountain"))
            tip=len(b.vertices)
            b.vertices.append((cx+lean_x+rng.uniform(-0.3,0.3),cy+lean_y,2+height))
            for edge in range(sides):
                b.faces.append((first+4*sides+edge,first+4*sides+(edge+1)%sides,tip))
                b.face_materials.append("MenuMountain")
    for i in range(35):
        b.oval((rng.uniform(-100,100),rng.uniform(38,125),rng.uniform(35,58)),(rng.uniform(13,29),rng.uniform(7,18),rng.uniform(2.5,6)),"MenuCloud",16,7)
    return b.finish()



# Build the vaulted hall beyond the gate without obstructing the entry flight.
def hall():
    b=MeshBuilder("MenuCampaignHall")
    b.box((0,0,-0.15),(13,16,0.3))
    for side in (-1,1):
        for row in range(7):
            for col in range(9):
                if (row,col,side) in ((5,3,-1),(6,3,-1),(4,7,1)):
                    continue
                b.box((side*6.4,-7+col*1.75,row+0.5),(0.7,1.64,1.07))
    for row in range(7):
        for col in range(8):
            if row>3 and col in (2,3):
                continue
            b.box((-5.7+col*1.6,7.8,row+0.5),(1.5,0.7,1.07))
    for y in (-6,-2,2,6):
        b.arch(0,y,5.0,5.8,0.45,0.5,18)
        for side in (-1,1):
            b.column((side*5.8,y,0),0.35,5.1,material="MenuStone",sides=10)
    return b.finish()


# Build the campaign table with a separate plane for the existing map image.
def table():
    b=MeshBuilder("MenuMapTable")
    b.box((0,0,1.55),(4.4,3.2,0.24),"MenuAgedWood")
    for x in (-1.75,1.75):
        for y in (-1.15,1.15):
            b.box((x,y,0.75),(0.24,0.24,1.5),"MenuAgedWood")
    b.segment((-1.8,-1.20,0.08),(-1.1,-1.7,0.05),0.10,0.06,"MenuAgedWood",7)
    b.box((0,0,1.68),(4.05,2.85,0.03),"MenuParchment")
    start=len(b.vertices)
    b.vertices.extend([(-1.9,-1.3,1.705),(1.9,-1.3,1.705),(1.9,1.3,1.705),(-1.9,1.3,1.705)])
    b.faces.append(tuple(start+i for i in range(4)))
    b.face_materials.append("MenuCampaignMap")
    obj=b.finish()
    polygon=obj.data.polygons[-1]
    for index,uv in zip(polygon.loop_indices,((0,0),(1,0),(1,1),(0,1))):
        obj.data.uv_layers.active.data[index].uv=uv
    return obj


# Build the side-cave mouth as an irregular rocky arch with a clear interior.
def cave():
    b=MeshBuilder("MenuSideCave")
    for side in (-1,1):
        for z in range(5):
            b.oval((side*(2.25+0.16*math.sin(z)),0,z*0.9),(0.90,2.3,0.75),"MenuDarkStone",8,5)
    b.arch(0,0,3.4,1.8,1.1,4.2,11)
    b.box((0,1.2,-0.15),(5.8,7.0,0.3))
    for i in range(13):
        b.oval((-3.8+(i*1.31)%7.5,-1.3+(i*0.67)%4.0,-0.07+(i%3)*0.08),
            (0.16+(i%3)*0.11,0.28,0.19),"MenuRoughStone",8,5)
    return b.finish()


# Build one rounded weathered stone boulder, retaining independent damage without coarse polygon spikes.
def rock():
    b=MeshBuilder("MenuRuinRock")
    rng=random.Random(VARIANT_SEED)
    b.oval((0,0,0.65),(rng.uniform(1.0,1.6),rng.uniform(0.8,1.35),rng.uniform(0.75,1.35)),"MenuRoughStone",11,7)
    for index, point in enumerate(b.vertices):
        scale=1+0.16*math.sin(point[0]*3.7+VARIANT_SEED)*math.sin(point[1]*4.3+point[2]*2.1)
        b.vertices[index]=tuple(value*scale for value in point)
    return b.finish()


# Build one separately exported damaged arcade arch with a unique missing-keystone pattern.
def arcade_arch():
    b=MeshBuilder("MenuArcadeArch")
    index=(VARIANT_SEED-801)%3
    x=(-4.67,0,4.67)[index]
    b.arch(x,0,15.75+0.13*index,1.75,0.63,3.1,19+index)
    if index==1:
        b.box((x+1.1,-0.4,16.8),(0.43,1.8,0.5))
    b.box((x-0.5,-1.8,0.25),(0.68,0.9,0.44),"MenuRoughStone")
    return b.finish()


# Put each loose rubble island onto an actual lower mesh surface, with a small weathering inset.
def settle_rubble(builder):
    if not builder.vertices:
        return
    parent=list(range(len(builder.vertices)))
    # Resolve the connected component of a vertex without merging separate rubble stones.
    def find(index):
        while parent[index]!=index:
            parent[index]=parent[parent[index]]
            index=parent[index]
        return index
    for face in builder.faces:
        root=find(face[0])
        for vertex in face[1:]:
            parent[find(vertex)]=root
    groups={}
    materials={}
    for face,material in zip(builder.faces,builder.face_materials):
        root=find(face[0])
        groups.setdefault(root,set()).update(face)
        materials.setdefault(root,set()).add(material)
    support_faces=[face for face,material in zip(builder.faces,builder.face_materials) if material!="MenuRoughStone"]
    tree=BVHTree.FromPolygons([Vector(v) for v in builder.vertices],support_faces,all_triangles=False) if support_faces else None
    for root,indices in groups.items():
        if materials[root]!={"MenuRoughStone"}:
            continue
        points=[Vector(builder.vertices[index]) for index in indices]
        lowest=min(point.z for point in points)
        centre=sum(points,Vector())/len(points)
        supports=[]
        probes=[point for point in points if point.z<lowest+0.025]
        probes.append(Vector((centre.x,centre.y,lowest)))
        for point in probes:
            hit=tree.ray_cast(Vector((point.x,point.y,lowest-0.065)),Vector((0,0,-1)),80) if tree else (None,None,None,None)
            if hit[0] is not None:
                supports.append(hit[0].z)
        support=max(supports) if supports else -0.22
        # A buried lower edge stays in contact after the editable erosion modifier is evaluated.
        shift=support-0.075-lowest
        if abs(shift)>0.035:
            for index in indices:
                x,y,z=builder.vertices[index]
                builder.vertices[index]=(x,y,z+shift)
            builder.contact_corrections.append(round(shift,4))


# Add a fractured dry skull with deep sockets, an uneven jaw and missing teeth.
def bone_skull(b, position, scale=1, material="MenuBone"):
    x,y,z=position
    first=len(b.vertices)
    b.oval((x,y,z+0.28*scale),(0.25*scale,0.22*scale,0.31*scale),material,9,5)
    b.prism([(x-0.18*scale,z+0.20*scale),(x+0.17*scale,z+0.19*scale),
        (x+0.15*scale,z-0.04*scale),(x-0.10*scale,z-0.10*scale)],y-0.28*scale,y-0.12*scale,material)
    for side in (-1,1):
        b.prism([(x+side*0.045*scale,z+0.35*scale),(x+side*0.20*scale,z+0.40*scale),
            (x+side*0.19*scale,z+0.20*scale),(x+side*0.065*scale,z+0.18*scale)],
            y-0.246*scale,y-0.23*scale,"MenuBlack")
    b.prism([(x-0.04*scale,z+0.18*scale),(x+0.055*scale,z+0.17*scale),(x,z+0.06*scale)],
        y-0.295*scale,y-0.28*scale,"MenuBlack")
    for i in range(6):
        if (i+VARIANT_SEED)%5==0:
            continue
        tx=x+(-0.13+i*0.052)*scale
        b.segment((tx,y-0.28*scale,z+0.045*scale),(tx+0.01*scale,y-0.30*scale,z-0.055*scale),0.022*scale,0.012*scale,material,5)
    b.prism([(x-0.04*scale,z+0.57*scale),(x-0.025*scale,z+0.43*scale),
        (x+0.06*scale,z+0.34*scale),(x+0.045*scale,z+0.32*scale),(x-0.05*scale,z+0.43*scale)],
        y-0.205*scale,y-0.198*scale,"MenuBlack")
    return first


# Add a readable articulated skeleton in a standing, crawling or partly buried pose.
def dead_skeleton(b, position=(0,0,0), scale=1, pose="standing"):
    origin=Vector(position)
    if pose=="crawling":
        hips=Vector((0,0.45,0.40)); neck=Vector((0,-0.70,0.78)); head=Vector((0,-1.01,0.77))
        arms=[((-0.40,-0.50,0.70),(-0.72,-0.99,0.18),(-0.84,-1.50,0.06)),
            ((0.40,-0.50,0.70),(0.80,-0.35,0.24),(1.03,-0.72,0.06))]
        legs=[((-0.20,0.46,0.40),(-0.45,1.07,0.13),(-0.72,1.72,0.05)),
            ((0.20,0.46,0.40),(0.67,0.99,0.32),(0.35,1.58,0.07))]
    else:
        hips=Vector((0,0,0.92)); neck=Vector((0,-0.10,1.92)); head=Vector((0,-0.12,2.02))
        arms=[((-0.35,-0.04,1.72),(-0.64,-0.18,1.20),(-0.55,-0.35,0.74)),
            ((0.35,-0.04,1.72),(0.72,0.02,1.24),(0.64,-0.24,0.81))]
        legs=[((-0.16,0,0.92),(-0.22,-0.02,0.47),(-0.28,-0.13,0.06)),
            ((0.16,0,0.92),(0.29,0.03,0.45),(0.34,-0.10,0.06))]
        if pose=="chained":
            arms=[((-0.35,-0.04,1.72),(-0.67,0,2.02),(-0.80,0,2.44)),
                ((0.35,-0.04,1.72),(0.71,-0.03,2.05),(0.96,-0.01,2.35))]
    neck.x+=0.12*math.sin(VARIANT_SEED*0.53)
    head.x=neck.x+0.06*math.cos(VARIANT_SEED)
    # Transform every joint in the same local frame to keep limbs and ribs physically connected.
    # Apply the shared local skeleton frame to one anatomical joint.
    def point(value):
        return tuple(origin+Vector(value)*scale)
    b.segment(point(hips),point(neck),0.060*scale,0.045*scale,"MenuBone",6)
    for index in range(8):
        center=hips.lerp(neck,index/8)
        b.box(point(center),(0.14*scale,0.12*scale,0.09*scale),"MenuBone")
    b.segment(point(hips+Vector((-0.22,0,0))),point(hips+Vector((0.21,0,0))),0.10*scale,0.095*scale,"MenuBone",6)
    chest_axis=(neck-hips).normalized()
    for row in range(6):
        center=hips.lerp(neck,0.48+row*0.074)
        width=(0.29+0.055*math.sin(row*0.64))*scale
        for side in (-1,1):
            if pose=="rising" and side<0 and row==2:
                continue
            a=origin+center*scale+Vector((side*width,0.015*scale,0))
            c=origin+center*scale+Vector((side*width*0.78,-0.17*scale,-0.065*scale))
            d=origin+center*scale+Vector((side*0.045*scale,-0.22*scale,-0.095*scale))
            b.segment(tuple(a),tuple(c),0.028*scale,0.025*scale,"MenuBone",5)
            b.segment(tuple(c),tuple(d),0.025*scale,0.021*scale,"MenuBone",5)
    bone_skull(b,point(head),0.91*scale)
    for joints in arms+([] if pose=="rising" else legs):
        b.segment(point(joints[0]),point(joints[1]),0.050*scale,0.037*scale,"MenuBone",6)
        b.segment(point(joints[1]),point(joints[2]),0.040*scale,0.027*scale,"MenuBone",6)
        for finger in range(4):
            p=Vector(joints[2])+Vector(((finger-1.5)*0.045,-0.01,0))
            q=p+Vector((0.012,-0.16,-0.035))
            b.segment(point(p),point(q),0.015*scale,0.009*scale,"MenuBone",5)


# Skin authored vertex ranges to rigid bones and create a genuinely looping native Ogre action.
def rigid_loop(obj, bones, clip, seconds, animation, pinned=()):
    if clip=="Sway":
        top=max(vertex.co.z for vertex in obj.data.vertices)
        bones=[("Fixed",(0,0,top),range(0),None)]+[(name,pivot,indices,"Fixed") for name,pivot,indices,parent in bones]
    arm_data=bpy.data.armatures.new(obj.name+"Rig")
    arm=bpy.data.objects.new(obj.name+"Rig",arm_data)
    bpy.context.scene.collection.objects.link(arm)
    obj.select_set(False); arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode="EDIT")
    for name,pivot,indices,parent in bones:
        bone=arm.data.edit_bones.new(name)
        bone.head=pivot; bone.tail=Vector(pivot)+Vector((0,0,0.25))
        if parent:
            bone.parent=arm.data.edit_bones[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm["ogre_bone_order"]=[bone[0] for bone in bones]
    for name,pivot,indices,parent in bones:
        group=obj.vertex_groups.new(name=name)
        if indices:
            group.add(list(indices),1,"REPLACE")
    if clip=="Sway":
        # Upper chain endpoints are bolted in place while lower links and the load can swing.
        for vertex in obj.data.vertices:
            fixed=max(0.0,min(1.0,(vertex.co.z-(top-1.25))/1.25))
            if fixed>0:
                obj.vertex_groups["Fixed"].add([vertex.index],fixed,"REPLACE")
                obj.vertex_groups["Swing"].add([vertex.index],1-fixed,"REPLACE")
    if pinned:
        obj.vertex_groups["Fixed"].add(list(pinned),1.0,"REPLACE")
        obj.vertex_groups["Swing"].add(list(pinned),0.0,"REPLACE")
    modifier=obj.modifiers.new(clip+" skeletal loop","ARMATURE"); modifier.object=arm; obj.parent=arm
    frame_count=int(seconds*24)
    for frame in range(0,frame_count+1,12):
        t=frame/frame_count
        for name,pivot,indices,parent in bones:
            bone=arm.pose.bones[name]; bone.rotation_mode="QUATERNION"
            rotation,translation=animation(name,t)
            # Convert authored scene-axis movement into the bone bind frame.
            basis=bone.bone.matrix_local.to_quaternion()
            authored=Quaternion((0,1,0),rotation[1]) @ Quaternion((1,0,0),rotation[0]) @ Quaternion((0,0,1),rotation[2])
            bone.rotation_quaternion=basis.inverted() @ authored @ basis
            if max(abs(value) for value in rotation)>1e-6:
                assert max(abs(value) for value in bone.rotation_quaternion[1:])>1e-7,"Authored rotation lost its quaternion vector"
            bone.location=basis.inverted() @ Vector(translation)
            bone.keyframe_insert("rotation_quaternion",frame=frame,group=name)
            bone.keyframe_insert("location",frame=frame,group=name)
    arm.animation_data.action.name=clip
    arm.animation_data.action["ogre_length"]=seconds
    bpy.context.scene.frame_set(0)
    return obj,arm


# Return small unsynchronized pendulum motion about the actual chain attachment.
def sway_motion(name,t):
    if name=="Fixed":
        return ((0,0,0),(0,0,0))
    phase=(VARIANT_SEED%23)/23*2*math.pi
    amplitude=0.018+(VARIANT_SEED%7)*0.0015
    angle=math.sin(t*2*math.pi+phase)*amplitude
    return ((angle*0.25,angle,angle*0.15),(0,0,0))


# Pose the crow's idle head and wings, with a brief complete takeoff and landing every twelve seconds.
def crow_motion(name,t):
    t=(t+(VARIANT_SEED%17)/17)%1.0
    flight=max(0,math.sin((t-0.5)*math.pi/0.30)) if 0.5<t<0.8 else 0
    if name=="Root":
        return ((0,0,0),(0,0,flight*1.6))
    if name=="Head":
        return ((0.05*math.sin(t*4*math.pi),0,0.48*math.sin(t*6*math.pi)),(0,0,0))
    side=-1 if name=="WingL" else 1
    return ((0,side*(0.10*math.sin(t*8*math.pi)+flight*0.75*math.sin(t*32*math.pi)),0),(0,0,0))


# Build one new separately editable horror prop; every placed variant has its own seeded source file.
def polish_prop():
    name=VARIANT_NAME
    b=MeshBuilder(name)
    rng=random.Random(VARIANT_SEED)
    kind=next(spec[2] for spec in POLISH_SPECS if spec[0]==name)
    armature=None; bones=None; clip="Sway"; seconds=6; pinned=[]
    if kind=="SkullHeap":
        for index in range(4 if name.endswith("A") else 6):
            bone_skull(b,(rng.uniform(-0.65,0.65),rng.uniform(-0.5,0.5),rng.uniform(0.04,0.18)),rng.uniform(0.7,1.2))
        for index in range(12):
            x,y=rng.uniform(-0.9,0.9),rng.uniform(-0.6,0.6)
            b.segment((x,y,0.07),(x+rng.uniform(-0.4,0.4),y+0.42,0.08),0.035,0.025,"MenuBone",6)
    elif kind in ("GraspingHands","RisingRibcage","CrawlingDead","ChainedDead","CagedDead","EmptyCage","ImpaledBones"):
        if kind=="GraspingHands":
            for x,h in ((-0.29,0.54),(0.42,0.79)):
                b.segment((x,0,-0.20),(x+0.04,-0.12,h),0.055,0.043,"MenuBone",6)
                b.box((x+0.03,-0.10,h),(0.21,0.11,0.18),"MenuBone")
                for finger in range(5):
                    a=(x-0.09+finger*0.045,-0.13,h+0.06)
                    c=(a[0]+0.01,-0.17,h+0.30-abs(finger-2)*0.04)
                    b.segment(a,c,0.019,0.014,"MenuBone",5)
                    b.segment(c,(c[0],c[1]-0.12,c[2]-0.045),0.014,0.005,"MenuBone",5)
        elif kind=="RisingRibcage":
            dead_skeleton(b,(0,0,-0.68),0.95,"rising")
        elif kind=="CrawlingDead":
            dead_skeleton(b,(0,0,0),1.02,"crawling")
        elif kind=="ImpaledBones":
            b.column((0,0,-0.2),0.11,2.9,0,"MenuCorrodedIron",7)
            dead_skeleton(b,(0,-0.10,1.0),0.64,"rising")
        elif kind=="ChainedDead":
            dead_skeleton(b,(0,-0.28,0),0.96,"chained")
            for side in (-1,1):
                for index in range(9):
                    b.link((side*(0.88+index*0.025),0.05,2.28+index*0.12),0.10,bool(index%2))
                b.segment((side*1.08,0.14,3.18),(side*1.08,1.70,3.18),0.065,0.065,"MenuCorrodedIron",6)
                b.box((side*1.08,1.70,3.18),(0.24,0.18,0.20),"MenuCorrodedIron")
            bones=[("Swing",(0,0,3.2),range(len(b.vertices)),None)]
        else:
            hanging_cage(b,0,0,0.0,VARIANT_SEED%9)
            b.segment((0,0,3.16),(0,2.40,3.16),0.085,0.085,"MenuCorrodedIron",6)
            b.box((0,2.40,3.16),(0.32,0.22,0.35),"MenuCorrodedIron")
            if kind=="CagedDead":
                dead_skeleton(b,(0,-0.10,0.04),0.54,"standing")
            bones=[("Swing",(0,0,3.16),range(len(b.vertices)),None)]
    elif kind=="Gravestone":
        lean=rng.uniform(-0.25,0.25)
        b.prism([(-0.61,-0.17),(0.58,-0.17),(0.47+lean,1.40),
            (0.16+lean,1.70),(-0.07+lean,1.39),(-0.48+lean,1.56)],-0.20,0.24,"MenuCarvedStone")
        for row in range(5):
            z=0.30+row*0.18
            b.segment((-0.31,-0.22,z),(0.22-rng.random()*0.12,-0.22,z+0.025),0.018,0.012,"MenuBlack",4)
        b.prism([(-0.11,1.42),(-0.08,1.02),(0.14,0.80),(0.11,0.76),(-0.14,1.0)],-0.225,-0.21,"MenuBlack")
        bone_skull(b,(-0.23,-0.45,0.08),0.55)
    elif kind=="OpenGrave":
        b.box((0,0,-0.45),(1.65,2.7,0.12),"MenuBlack")
        for side in (-1,1):
            b.box((side*0.94,0,-0.15),(0.20,3.1,0.6),"MenuDarkStone")
            b.box((0,side*1.55,-0.15),(2.05,0.20,0.6),"MenuDarkStone")
        dead_skeleton(b,(0,0.10,-0.40),0.73,"crawling")
    elif kind=="Crypt":
        b.box((0,1.30,0.03),(3.4,3.0,0.28))
        for side in (-1,1):
            for row in range(5):
                b.box((side*1.32,1.3,0.40+row*0.58),(0.48,2.7,0.59))
        b.arch(0,0.0,2.1,1.08,0.40,0.50,16)
        b.box((0,1.65,2.98),(3.15,2.5,0.35))
        b.box((0,2.58,1.15),(2.6,0.26,2.3))
        b.box((0,2.40,1.35),(1.4,0.035,1.7),"MenuWindowGlow")
        # The opened iron door is rotated as solid geometry about its left-hand hinge.
        first=len(b.vertices)
        b.box((-0.98,-0.05,1.11),(1.9,0.16,2.20),"MenuCorrodedIron")
        pivot=Vector((-1.0,0.0,0))
        for index in range(first,len(b.vertices)):
            p=Vector(b.vertices[index])-pivot
            b.vertices[index]=tuple(pivot+Vector((p.x*0.34-p.y*0.94,p.x*0.94+p.y*0.34,p.z)))
    elif kind=="Coffin":
        outline=[(-0.31,-1.15),(0.32,-1.15),(0.56,-0.63),(0.44,1.15),(-0.43,1.15),(-0.57,-0.61)]
        first=len(b.vertices)
        b.vertices.extend((x,y,0.02) for x,y in outline)
        b.faces.append(tuple(first+i for i in reversed(range(6)))); b.face_materials.append("MenuAgedWood")
        for i in range(6):
            x,y=outline[i]; u,v=outline[(i+1)%6]
            first=len(b.vertices)
            b.vertices.extend(((x,y,0.02),(u,v,0.02),(u,v,0.42),(x,y,0.42)))
            b.faces.extend(((first,first+1,first+2,first+3),(first+3,first+2,first+1,first)))
            b.face_materials.extend(("MenuAgedWood","MenuAgedWood"))
            b.segment((x,y,0.42),(u,v,0.42),0.045,0.040,"MenuCorrodedIron",5)
        first=len(b.vertices)
        b.vertices.extend((x+1.11,y+0.12,0.055+0.04*x) for x,y in outline)
        b.faces.append(tuple(first+i for i in range(6))); b.face_materials.append("MenuAgedWood")
    elif kind=="EarthBones":
        for index in range(11):
            x,y=rng.uniform(-1.1,1.1),rng.uniform(-0.9,0.9)
            b.oval((x,y,0.02),(rng.uniform(0.35,0.6),rng.uniform(0.3,0.6),rng.uniform(0.1,0.35)),"MenuAsh",7,4)
        bone_skull(b,(0.34,-0.55,0.09),0.85)
        for index in range(7):
            x,y=rng.uniform(-0.8,0.8),rng.uniform(-0.6,0.6)
            b.segment((x,y,0.09),(x+0.3,y+0.2,0.14),0.04,0.035,"MenuBone",6)
    elif kind in ("BrokenSword","BrokenAxe","TatteredSpear"):
        if kind=="BrokenSword":
            b.segment((0.16,0.04,1.04),(0.22,0.08,1.50),0.055,0.038,"MenuAgedWood",7)
        else:
            b.segment((0,0,-0.25),(0.22,0.08,1.5 if kind!="TatteredSpear" else 3.3),0.045,0.028,"MenuAgedWood",7)
        if kind=="BrokenSword":
            b.prism([(-0.16,0.12),(0.10,0.08),(0.27,1.02),(0.10,0.88),(0.02,1.14)],-0.045,0.05,"MenuCorrodedIron")
            b.segment((-0.35,0,1.1),(0.40,0,1.22),0.055,0.04,"MenuCorrodedIron",6)
        elif kind=="BrokenAxe":
            b.prism([(0.02,0.9),(0.70,0.82),(0.81,1.32),(0.60,1.65),(0.51,1.38),(0.06,1.30)],-0.06,0.07,"MenuCorrodedIron")
        else:
            b.column((0.22,0.08,3.0),0.14,0.66,0,"MenuCorrodedIron",5)
            b.prism([(0.15,2.9),(1.0,2.80),(0.54,2.51),(0.81,2.35),(0.27,2.08)],-0.02,0.03,"MenuClothFadedA")
    elif kind=="ArmourHeap":
        for index in range(4):
            x,y=rng.uniform(-0.8,0.8),rng.uniform(-0.6,0.6)
            b.oval((x,y,0.24),(0.34,0.31,0.29),"MenuCorrodedIron",7,4)
            b.prism([(x-0.20,0.25),(x+0.19,0.28),(x+0.13,0.17),(x-0.14,0.16)],y-0.32,y-0.30,"MenuBlack")
        b.prism([(-0.8,0.1),(-0.16,0.08),(0.11,0.52),(-0.21,0.93),(-0.60,0.77)],0.22,0.36,"MenuCorrodedIron")
        for index in range(4):
            b.box((-0.52+index*0.14,0.29,0.37),(0.065,0.20,0.61),"MenuAgedWood")
    elif kind=="BrokenRam":
        for side in (-1,1):
            b.segment((side*1.25,-1.55,0.02),(side*0.88,0.75,1.50),0.17,0.13,"MenuAgedWood",7)
            b.segment((side*1.25,1.60,0.02),(side*0.88,0.75,1.50),0.15,0.12,"MenuAgedWood",7)
        b.segment((-1.9,0,0.52),(0.36,0.12,0.89),0.35,0.28,"MenuAgedWood",9)
        b.segment((0.68,0.15,0.43),(2.1,0.27,0.08),0.29,0.15,"MenuAgedWood",8)
        b.oval((-1.9,0,0.52),(0.39,0.40,0.34),"MenuCorrodedIron",8,5)
        for x in (-0.65,0.34):
            for index in range(6):
                b.link((x,0,1.72-index*0.16),0.13,bool(index%2))
    elif kind in ("Pillory","Gallows","HeadStake","WallHooks"):
        if kind=="Pillory":
            for side in (-1,1):
                b.box((side*0.83,0,1.10),(0.19,0.24,2.4),"MenuAgedWood")
                b.box((side*0.54,0,1.66),(0.64,0.18,0.46),"MenuAgedWood")
            b.box((0,0,2.05),(1.8,0.21,0.20),"MenuAgedWood")
            b.box((0,0,1.30),(1.8,0.21,0.20),"MenuAgedWood")
        elif kind=="Gallows":
            b.box((0,0,1.80),(0.32,0.38,3.7),"MenuAgedWood")
            b.box((0.89,0,3.47),(2.1,0.28,0.28),"MenuAgedWood")
            b.segment((0.04,0,2.49),(1.31,0,3.44),0.10,0.09,"MenuAgedWood",6)
            for index in range(8):
                b.link((1.45,0,3.3-index*0.17),0.10,bool(index%2))
            b.link((1.45,0,1.85),0.28,False)
        elif kind=="HeadStake":
            b.column((0,0,-0.2),0.10,2.4,0,"MenuAgedWood",7)
            bone_skull(b,(0,-0.04,1.48),1.08,"MenuDeadSkin")
            for index in range(3):
                b.segment((rng.uniform(-0.11,0.11),-0.04,1.35),(rng.uniform(-0.15,0.15),-0.02,0.93),0.02,0.005,"MenuDriedBlood",5)
        else:
            for side in (-1,1):
                b.box((side*0.38,1.6,1.8),(0.19,0.24,0.36),"MenuCorrodedIron")
                b.segment((side*0.38,-0.09,1.8),(side*0.38,1.6,1.8),0.065,0.065,"MenuCorrodedIron",5)
                for index in range(12):
                    b.link((side*0.38,-0.09,1.70-index*0.125),0.09,bool(index%2))
                b.segment((side*0.38,-0.09,0.25),(side*0.55,-0.20,0.10),0.05,0.025,"MenuCorrodedIron",5)
            bones=[("Swing",(0,0,2.0),range(len(b.vertices)),None)]
    elif kind=="Crow":
        ranges={}
        first=len(b.vertices)
        b.oval((0,0.0,0.30),(0.16,0.30,0.22),"MenuCrowBlack",9,5)
        b.prism([(-0.15,0.23),(0.14,0.24),(0.11,0.05),(-0.10,0.04)],0.14,0.54,"MenuCrowBlack")
        for side in (-1,1):
            b.segment((side*0.08,0.04,0.15),(side*0.10,-0.02,-0.01),0.018,0.015,"MenuCorrodedIron",5)
            for toe in range(3):
                b.segment((side*0.10,-0.02,-0.01),(side*0.10+(toe-1)*0.045,-0.17,-0.015),0.012,0.005,"MenuCrowBlack",5)
        ranges["Root"]=range(first,len(b.vertices))
        first=len(b.vertices)
        b.oval((0,-0.18,0.57),(0.115+(VARIANT_SEED%5)*0.008,0.15,0.135+(VARIANT_SEED%3)*0.012),"MenuCrowBlack",8,5)
        b.prism([(-0.07,0.56),(0.07,0.56),(0,0.46)],-0.47,-0.24,"MenuCrowBlack")
        for side in (-1,1):
            b.oval((side*0.105,-0.28,0.60),(0.016,0.025,0.018),"MenuGateEyes",6,4)
        ranges["Head"]=range(first,len(b.vertices))
        for side,label in ((-1,"WingL"),(1,"WingR")):
            first=len(b.vertices)
            b.prism([(side*0.07,0.40),(side*0.32,0.31),(side*0.25,0.13),
                (side*0.19,0.10),(side*0.14,0.03),(side*0.10,0.21)],-0.02,0.28,"MenuCrowBlack")
            ranges[label]=range(first,len(b.vertices))
        bones=[("Root",(0,0,0),ranges["Root"],None),("Head",(0,-0.15,0.48),ranges["Head"],"Root"),
            ("WingL",(-0.08,0,0.35),ranges["WingL"],"Root"),("WingR",(0.08,0,0.35),ranges["WingR"],"Root")]
        clip="Watch"; seconds=12
    elif kind=="Rat":
        b.oval((0,0,0.13),(0.15,0.32,0.14),"MenuRatHide",9,5)
        b.oval((0,-0.29,0.15),(0.10,0.16,0.11),"MenuRatHide",8,4)
        b.segment((0,0.23,0.11),(0.14,0.65,0.015),0.025,0.005,"MenuRatHide",6)
        for side in (-1,1):
            b.oval((side*0.08,-0.20,0.24),(0.05,0.04,0.06),"MenuRatHide",6,4)
            for y in (-0.13,0.18):
                b.segment((side*0.11,y,0.10),(side*0.18,y-0.04,0.0),0.025,0.015,"MenuRatHide",5)
    elif kind=="WebVictim":
        center=Vector((0,0,1.25))
        for spoke in range(13):
            angle=spoke*2*math.pi/13
            end=center+Vector((1.2*math.cos(angle),0,1.2*math.sin(angle)))
            b.segment(tuple(center),tuple(end),0.008,0.004,"MenuWeb",4)
        for ring in range(1,5):
            radius=ring*0.25
            for spoke in range(13):
                a=spoke*2*math.pi/13; c=(spoke+1)*2*math.pi/13
                b.segment(tuple(center+Vector((radius*math.cos(a),0,radius*math.sin(a)))),
                    tuple(center+Vector((radius*math.cos(c),0,radius*math.sin(c)))),0.006,0.005,"MenuWeb",4)
        dead_skeleton(b,(0,0.08,0.0),0.54,"chained")
        for z in (0.35,0.56,0.75,0.94):
            b.segment((-0.27,-0.10,z),(0.31,-0.10,z+0.06),0.020,0.010,"MenuWeb",5)
    elif kind in ("BloodTrail","DragTrail"):
        for index in range(11):
            x=rng.uniform(-0.5,0.5); y=index*0.55
            width=rng.uniform(0.10,0.38)
            first=len(b.vertices)
            b.vertices.extend(((x-width,y,0.0),(x+width,y+0.12,0.0),(x+width*0.45,y+0.66,0.0),(x-width*0.40,y+0.49,0.0)))
            b.faces.append(tuple(first+i for i in range(4))); b.face_materials.append("MenuDriedBlood" if kind=="BloodTrail" else "MenuSoot")
    elif kind in ("BurntTorch","CharredRemains","BrokenSlab"):
        if kind=="BurntTorch":
            b.segment((-0.45,0,0.02),(0.49,0.13,0.05),0.06,0.09,"MenuAgedWood",7)
            b.oval((0.45,0.12,0.06),(0.16,0.14,0.12),"MenuSoot",7,4)
        elif kind=="CharredRemains":
            dead_skeleton(b,(0,0,0),0.63,"crawling")
            for index in range(9):
                b.oval((rng.uniform(-0.6,0.6),rng.uniform(-0.6,0.9),0.05),(0.20,0.17,0.10),"MenuAsh",6,4)
        else:
            b.prism([(-0.8,0.0),(0.1,-0.12),(-0.15,0.28),(-0.63,0.46)],-0.70,0.72,"MenuWetStone")
            b.prism([(0.2,-0.12),(0.85,-0.03),(0.63,0.51),(0.34,0.23)],-0.68,0.68,"MenuWetStone")
    elif kind=="GateBeast":
        b.prism([(-2.7,0),(-2.8,2),(-1.9,4.2),(-0.7,6.6),(0.30,6.9),(1.5,4.8),(2.5,3.5),(3.0,0)],-0.02,0.02,"MenuBlack")
        for x in (-0.52,0.52,-1.64,1.39):
            b.oval((x,-0.05,5.0 if abs(x)<1 else 2.9),(0.10,0.035,0.055),"MenuGateEyes",8,4)
    elif kind=="LavaWall":
        for index in range(8):
            z=0.2+index*0.50
            x=0.18*math.sin(index*1.9+VARIANT_SEED)
            b.prism([(x-0.035,z),(x+0.035,z),(x+0.20,z+0.32),(x+0.12,z+0.55),
                (x+0.075,z+0.54),(x+0.14,z+0.31)],-0.02,0.01,"MenuLavaCrack")
    elif kind=="VolcanicRuins":
        # The raised ruins have a real broken mountain foot embedded below the existing distant ridge.
        b.prism([(-44,-30),(44,-30),(44,0),(40,1),(30,2),(20,3),(10,1),
            (0,2),(-10,4),(-20,1),(-30,3),(-39,2),(-44,0)],-5,15,"MenuMountain")
        for index in range(11):
            x=-32+index*6+rng.uniform(-2,2); h=rng.uniform(4,13)
            b.prism([(x-1.6,0),(x+1.5,0),(x+1.1,h),(x+0.3,h+2.4),
                (x-0.3,h-0.9),(x-1.4,h+0.3)],0,3,"MenuDistantStone")
            for slit in range(3):
                b.box((x-0.7+slit*0.6,-0.04,h*0.55),(0.22,0.04,1.5),"MenuLavaCrack")
        b.prism([(-13,-1),(-7,5),(-4,10),(-2,13),(0,11),(3,5),(9,0)],4,8,"MenuMountain")
        for index in range(7):
            b.segment((-2+index*0.12,3.94,12-index*1.3),(-2.4+index*0.22,3.94,10.7-index*1.3),0.05,0.025,"MenuLavaCrack",5)
    elif kind=="HorizonCrows":
        for index in range(24):
            x,y,z=rng.uniform(-17,17),rng.uniform(-3,3),rng.uniform(0,7)
            b.segment((x,y,z),(x-0.28,y+0.05,z+0.16),0.035,0.008,"MenuCrowBlack",4)
            b.segment((x,y,z),(x+0.23,y+0.04,z+0.19),0.035,0.008,"MenuCrowBlack",4)
    elif kind=="TitlePlaque":
        b.prism([(-7.2,-1.70),(6.9,-1.70),(7.25,-1.2),(7.05,1.63),
            (5.0,1.76),(-6.9,1.65),(-7.3,1.1)],-0.05,0.33,"MenuTitleIron")
        for side in (-1,1):
            for index in range(18):
                t=index/17
                tx=side*(5.7+(1.8 if side<0 else 3.0)*t)
                first_link=len(b.vertices)
                b.link((tx,0.14+3.85*t,1.65+1.53*t-0.35*math.sin(t*math.pi)),0.16,bool(index%2))
                if index>=16:
                    pinned.extend(range(first_link,len(b.vertices)))
            anchor_x=side*(7.5 if side<0 else 8.7)
            first_anchor=len(b.vertices)
            b.segment((anchor_x,3.99,3.18),(anchor_x,5.25,3.18),0.10,0.10,"MenuCorrodedIron",7)
            b.box((anchor_x,5.25,3.18),(0.29,0.25,0.32),"MenuCorrodedIron")
            pinned.extend(range(first_anchor,len(b.vertices)))
            for z in (-0.88,0.88):
                b.oval((side*6.60,-0.08,z),(0.12,0.07,0.12),"MenuCorrodedIron",7,4)
        # The title canvas is a single replaceable 3:1 texture, separate from its physical backing.
        start=len(b.vertices)
        b.vertices.extend(((-5.8,-0.085,-1.94),(5.8,-0.085,-1.94),(5.8,-0.085,1.9267),(-5.8,-0.085,1.9267)))
        b.faces.append((start,start+1,start+2,start+3)); b.face_materials.append("MenuTitleLetters")
        bones=[("Swing",(0,0.14,3.05),range(len(b.vertices)),None)]
    elif kind=="TitleCrest":
        b.prism([(-0.95,0.15),(0,0.75),(0.92,0.10),(0.35,-0.65),(0,-1.10),(-0.39,-0.57)],-0.12,0.14,"MenuCorrodedIron")
        for side in (-1,1):
            b.segment((side*0.15,-0.16,0.28),(side*0.45,-0.16,-0.07),0.06,0.035,"MenuTitleCrest",5)
            b.segment((side*0.45,-0.16,-0.07),(side*0.12,-0.16,-0.48),0.035,0.008,"MenuTitleCrest",5)
        b.segment((0,-0.17,0.43),(0,-0.17,-0.75),0.065,0.025,"MenuTitleCrest",5)
    elif kind=="BloodMoon":
        b.oval((0,0,0),(7.0,0.9,7.0),"MenuBloodMoon",72,40)
        craters=[]
        for index in range(11):
            x,z=rng.uniform(-5.7,5.7),rng.uniform(-5.7,5.7)
            if x*x+z*z<32:
                craters.append((x,z,rng.uniform(0.45,1.35),rng.uniform(0.07,0.17)))
        # Basins and broken raised rims deform the actual lunar shell; there are no dark overlay discs.
        for index,(x,y,z) in enumerate(b.vertices):
            if y>=0:
                continue
            displacement=0
            for cx,cz,radius,depth in craters:
                d=math.sqrt((x-cx)**2+(z-cz)**2)/radius
                rim=math.exp(-((d-1)*5.5)**2)*(0.65+0.35*math.sin(x*7+z*3))
                displacement+=depth*math.exp(-d*d*3)-depth*0.47*rim
            b.vertices[index]=(x,y+displacement,z)
    else:
        raise ValueError(kind)
    obj=b.finish()
    mounted=("ChainedDead","CagedDead","EmptyCage","ImpaledBones","WallHooks","WebVictim","GateBeast","LavaWall","TitlePlaque","TitleCrest","BloodMoon","VolcanicRuins","HorizonCrows")
    obj["contact_mode"]="perch" if kind=="Crow" else "embedded" if kind in ("GraspingHands","RisingRibcage","OpenGrave","BloodTrail","DragTrail") else "mounted" if kind in mounted else "ground"
    obj["prop_kind"]=kind
    obj["fixed_anchor_vertex_count"]=len(pinned)
    obj["contact_support"]=("GravestoneA" if name=="MenuCrowA" else "GravestoneC" if name=="MenuCrowB" else "LeftWall" if name=="MenuCrowC" else "RightTower" if name=="MenuCrowD" else "Courtyard")
    obj["contact_point"]=(-0.25,0,0.18) if name=="MenuGravestoneC" else (1.03,-0.72,0.03) if kind=="CrawlingDead" else (0,0,0.18) if kind in ("BrokenSword","BrokenAxe","TatteredSpear","HeadStake","Gravestone") else (0,0,min(v.co.z for v in obj.data.vertices))
    if kind=="TitlePlaque":
        face=obj.data.polygons[-1]
        for loop,uv in zip(face.loop_indices,((0,0),(1,0),(1,1),(0,1))):
            obj.data.uv_layers.active.data[loop].uv=uv
    if bones:
        return rigid_loop(obj,bones,clip,seconds,crow_motion if kind=="Crow" else sway_motion,pinned)
    return obj


# Give every new placed prop its own source, mesh, position and distinct deterministic damage.
POLISH_SPECS=[
    ("MenuSkullHeapA",(-4.5,-8.0,-0.16),"SkullHeap"),("MenuSkullHeapB",(4.5,-12.0,-0.16),"SkullHeap"),
    ("MenuGraspingHands",(-3.4,-13.5,-0.16),"GraspingHands"),("MenuRisingRibcage",(5.1,-15.3,-0.16),"RisingRibcage"),
    ("MenuCrawlingDead",(-11.5,-11.6,-0.16),"CrawlingDead"),
    ("MenuChainedDeadLeft",(-6.7,4.5,1.5),"ChainedDead"),("MenuChainedDeadRight",(6.4,4.6,2.1),"ChainedDead"),
    ("MenuCagedDead",(-5.5,4.8,5.2),"CagedDead"),
    ("MenuEmptyCageLeft",(-13.0,6.0,4.2),"EmptyCage"),("MenuEmptyCageRight",(17.8,5.8,3.5),"EmptyCage"),
    ("MenuImpaledBonesLeft",(-7.3,7.2,13.12),"ImpaledBones"),("MenuImpaledBonesRight",(10.6,6.5,12.5),"ImpaledBones"),
    ("MenuGravestoneA",(-11.5,-12.4,-0.16),"Gravestone"),("MenuGravestoneB",(-15.0,-6.1,-0.16),"Gravestone"),
    ("MenuGravestoneC",(11.6,-10.9,-0.16),"Gravestone"),("MenuGravestoneD",(15.8,-4.3,-0.16),"Gravestone"),
    ("MenuOpenGraveLeft",(-12.6,-9.7,-0.10),"OpenGrave"),("MenuOpenGraveRight",(12.5,-8.3,-0.10),"OpenGrave"),
    ("MenuCrypt",(-16.6,-0.8,-0.16),"Crypt"),("MenuCoffinLeft",(-10.6,-13.4,-0.16),"Coffin"),
    ("MenuCoffinRight",(11.3,-11.6,-0.16),"Coffin"),("MenuEarthBonesLeft",(-15.7,-8.0,-0.16),"EarthBones"),
    ("MenuEarthBonesRight",(14.2,-6.9,-0.16),"EarthBones"),
    ("MenuBrokenSwordA",(-5.0,-10.7,-0.16),"BrokenSword"),("MenuBrokenSwordB",(4.0,-17.3,-0.16),"BrokenSword"),
    ("MenuBrokenAxe",(6.6,-8.9,-0.16),"BrokenAxe"),("MenuArmourHeapLeft",(-13.3,-5.8,-0.16),"ArmourHeap"),
    ("MenuArmourHeapRight",(10.0,-9.2,-0.16),"ArmourHeap"),("MenuTatteredSpear",(13.1,-4.1,-0.16),"TatteredSpear"),
    ("MenuBrokenRam",(3.2,2.3,-0.16),"BrokenRam"),("MenuPillory",(-15.0,3.7,-0.16),"Pillory"),
    ("MenuHeadStakeA",(-12.5,-2.4,-0.16),"HeadStake"),("MenuHeadStakeB",(14.7,-3.0,-0.16),"HeadStake"),
    ("MenuGallows",(17.0,-0.3,-0.16),"Gallows"),("MenuWallHooksLeft",(-24.5,5.5,3.1),"WallHooks"),
    ("MenuWallHooksRight",(22.3,5.4,2.5),"WallHooks"),
    ("MenuCrowA",(-11.5,-12.4,1.47),"Crow"),("MenuCrowB",(11.6,-10.9,1.50),"Crow"),
    ("MenuCrowC",(-12.1,8.4,10.0),"Crow"),("MenuCrowD",(10.4,6.9,14.3),"Crow"),
    ("MenuRatA",(-6.8,-13.4,-0.10),"Rat"),("MenuRatB",(8.7,-11.2,-0.10),"Rat"),("MenuRatC",(-13.0,1.6,-0.10),"Rat"),
    ("MenuWebVictimLeft",(-20.5,8.05,0.30),"WebVictim"),("MenuWebVictimRight",(23.2,6.15,0.24),"WebVictim"),
    ("MenuBloodTrail",(-0.8,-10.6,0.045),"BloodTrail"),("MenuDragTrail",(1.0,-7.4,0.055),"DragTrail"),
    ("MenuBurntTorchA",(-8.0,-6.2,-0.15),"BurntTorch"),("MenuBurntTorchB",(8.7,-6.8,-0.15),"BurntTorch"),
    ("MenuCharredRemains",(6.9,-7.5,-0.16),"CharredRemains"),
    ("MenuBrokenSlabLeft",(-4.6,-16.8,-0.16),"BrokenSlab"),("MenuBrokenSlabRight",(4.5,-11.1,-0.16),"BrokenSlab"),
    ("MenuGateBeast",(0,29.2,-0.18),"GateBeast"),("MenuLavaWallLeft",(-14.1,5.89,0),"LavaWall"),
    ("MenuLavaWallRight",(15.0,5.79,0),"LavaWall"),("MenuVolcanicRuins",(0,95,23.0),"VolcanicRuins"),
    ("MenuHorizonCrows",(-12,65,24),"HorizonCrows"),("MenuTitlePlaque",(0,2.95,10.9),"TitlePlaque"),
    ("MenuTitleCrest",(0,2.9,8.5),"TitleCrest"),("MenuBloodMoon",(-33,83,35),"BloodMoon")]


MODELS=(gate,wall,tower,statue,brazier,banner,arches,green_tower,courtyard,backdrop,hall,table,cave)
COLOURS={"MenuSoot":(0.009,0.007,0.005),"MenuPuddle":(0.05,0.05,0.045),"MenuCarvedStone":(0.22,0.24,0.26),"MenuRoughStone":(0.20,0.22,0.24),"MenuDistantStone":(0.003,0.004,0.006),"MenuStone":(0.30,0.29,0.28),"MenuDarkStone":(0.11,0.12,0.13),"MenuIron":(0.14,0.15,0.16),"MenuWood":(0.18,0.11,0.07),"MenuParchment":(0.42,0.36,0.25),"MenuBlack":(0.012,0.014,0.016),"MenuCloth":(0.25,0.025,0.028),"MenuEmber":(0.9,0.16,0.015),"MenuCrystal":(0.035,0.45,0.055),"MenuMountain":(0.055,0.065,0.07),"MenuCloud":(0.035,0.043,0.049),"MenuSky":(0.012,0.018,0.022),"MenuCampaignMap":(0.7,0.7,0.7),"MenuWindowGlow":(0.8,0.12,0.018),"MenuFlame":(1.0,0.11,0.008),"MenuFlameCore":(1.0,0.42,0.035),"MenuCrystalDark":(0.005,0.12,0.018),"MenuCrystalBright":(0.12,0.8,0.035)}
COLOURS.update({"MenuMoss":(0.035,0.055,0.022),"MenuLichen":(0.065,0.070,0.045),
    "MenuWaterStain":(0.035,0.031,0.026),"MenuChippedStone":(0.14,0.13,0.11),
    "MenuAgedWood":(0.075,0.046,0.026),"MenuClothFadedA":(0.12,0.018,0.014),
    "MenuClothFadedB":(0.085,0.025,0.020),"MenuBone":(0.12,0.105,0.075),"MenuCorrodedIron":(0.075,0.048,0.028)})
COLOURS["MenuDemonStone"]=(0.14,0.15,0.15)
COLOURS.update({"MenuSpireGlow":(0.025,0.8,0.055),"MenuSpireBeam":(0.04,0.95,0.09),
    "MenuEmberCrack":(0.65,0.055,0.004),"MenuBannerSymbol":(0.32,0.21,0.085),
    "MenuHorizonGlow":(0.08,0.012,0.002),"MenuHorizonDark":(0.018,0.007,0.004)})


COLOURS.update({'MenuDriedBlood': (0.05, 0.002, 0.001), 'MenuWetSlime': (0.02, 0.028, 0.009), 'MenuAsh': (0.035, 0.031, 0.026), 'MenuWeb': (0.19, 0.18, 0.15), 'MenuCrowBlack': (0.008, 0.009, 0.008), 'MenuRatHide': (0.05, 0.04, 0.027), 'MenuDeadSkin': (0.08, 0.055, 0.035), 'MenuTitleLetters': (0.5, 0.5, 0.5), 'MenuTitleIron': (0.06, 0.045, 0.03), 'MenuTitleCrest': (0.005, 0.45, 0.015), 'MenuBloodMoon': (0.25, 0.012, 0.002), 'MenuGateEyes': (0.25, 0.035, 0.003), 'MenuLavaCrack': (0.65, 0.03, 0.001)})


# Enumerate the thirteen base families and every independently authored visible instance variant.
def model_specs():
    specs=[]
    for index,build in enumerate(MODELS):
        family=("MenuGate","MenuWallSegment","MenuTower","MenuStatue","MenuBrazier","MenuBanner","MenuArches", "MenuGreenTower","MenuCourtyard","MenuBackdrop","MenuCampaignHall","MenuMapTable","MenuSideCave")[index]
        damage=1.8 if build in (tower,statue) else 1.15
        specs.append((build,family,family,1000+index*10,damage))
    variants=((wall,"MenuWallSegmentRight","MenuWallSegment"),(tower,"MenuTowerRight","MenuTower"),
        (statue,"MenuStatueRight","MenuStatue"),(banner,"MenuBannerRight","MenuBanner"),
        (brazier,"MenuBrazierRight","MenuBrazier"),(brazier,"MenuBrazierGateLeft","MenuBrazier"),
        (brazier,"MenuBrazierGateRight","MenuBrazier"))
    for index,(build,name,family) in enumerate(variants):
        specs.append((build,name,family,2001+index*10,0.85+index*0.045))
    for index in range(8):
        specs.append((rock,"MenuRuinRock%02d"%(index+1),"MenuCourtyard",701+index,1.35))
    for index in range(3):
        specs.append((arcade_arch,"MenuArcadeArch%02d"%(index+1),"MenuArches",801+index,1.1+index*0.23))
    for index,(name,position,family) in enumerate(POLISH_SPECS):
        specs.append((polish_prop,name,family,3001+index*13,0.65))
    return specs


# Save every model privately first, copy it into the source tree and export its mesh.
def main():
    global VARIANT_SEED, VARIANT_DAMAGE, VARIANT_NAME
    arguments=sys.argv[sys.argv.index("--")+1:]
    repo,private=map(Path,arguments[:2])
    sys.path.insert(0,str(repo/"tools/blender-assets"))
    import odp_ogre_io as exporter
    from menu_scene_assembly import configure_material, material_values
    material_text=(repo/"materials/scripts/MenuScene.material").read_text(encoding="utf-8")
    source=repo/"assets-src/menu-scene"
    work=repo/"out/menu-scene/xml"
    for folder in (source,work,private):
        folder.mkdir(parents=True,exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    report=[]
    for build,name,family,seed,damage in model_specs():
        if len(arguments)>2 and build.__name__ not in arguments[2:] and name not in arguments[2:]:
            continue
        VARIANT_SEED,VARIANT_DAMAGE,VARIANT_NAME=seed,damage,name
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for material_name,colour in COLOURS.items():
            mat=bpy.data.materials.new(material_name)
            mat.diffuse_color=(*colour,1)
        wet=bpy.data.materials.new("MenuWetStone")
        wet.diffuse_color=(0.30,0.29,0.28,1)
        result=build()
        obj,arm=result if isinstance(result,tuple) else (result,None)
        images={}
        for material in obj.data.materials:
            configure_material(material,material_values(material_text,material.name),repo,images)
        obj.name=name
        obj.data.name=name
        obj["menu_source_family"]=family
        obj["menu_variant_seed"]=seed
        obj["menu_damage_strength"]=damage
        if arm:
            arm.name=name+"Armature"
        bpy.context.scene.render.fps=24
        bpy.context.scene.frame_start=0
        bpy.context.scene.frame_end=int(24*arm.animation_data.action.get("ogre_length",4)) if arm else 96
        assert obj.name==name
        if (private/(name+".blend")).exists() or (private/(name+".mesh.xml")).exists():
            raise FileExistsError("Use a fresh model destination: "+name)
        bpy.ops.wm.save_as_mainfile(filepath=str(private/(name+".blend")))
        shutil.copyfile(private/(name+".blend"),source/(name+".blend"))
        stats=exporter.export_mesh_xml(obj,arm,str(private/(name+".mesh.xml")),name+".skeleton" if arm else None,smooth=False)
        shutil.copyfile(private/(name+".mesh.xml"),work/(name+".mesh.xml"))
        if arm:
            exporter.export_skeleton_xml(arm,str(private/(name+".skeleton.xml")))
            shutil.copyfile(private/(name+".skeleton.xml"),work/(name+".skeleton.xml"))
        report.append(name+" "+str(stats)+" contact_corrections="+str(len(json.loads(obj.get("contact_corrections","[]")))))
        print(report[-1],flush=True)
    (work.parent/"models.txt").write_text("\n".join(report)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
