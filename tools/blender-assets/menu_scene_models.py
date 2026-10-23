"""Create the editable fortress models and export their Ogre XML meshes sequentially."""
from pathlib import Path
import math
import random
import shutil
import sys

import bpy
from mathutils import Vector


# Build disconnected closed surfaces with material slots and world-sized planar UVs.
class MeshBuilder:
    # Start one independently editable menu model.
    def __init__(self, name):
        self.name = name
        self.vertices = []
        self.faces = []
        self.face_materials = []

    # Append a solid polygon extruded along Y.
    def prism(self, polygon, front, back, material="MenuStone"):
        start = len(self.vertices)
        count = len(polygon)
        self.vertices.extend((x, front, z) for x, z in polygon)
        self.vertices.extend((x, back, z) for x, z in polygon)
        self.faces.append(tuple(start + i for i in range(count)))
        self.faces.append(tuple(start + count + i for i in reversed(range(count))))
        for i in range(count):
            j = (i + 1) % count
            self.faces.append((start+i, start+count+i, start+count+j, start+j))
        self.face_materials.extend([material] * (count+2))

    # Add an axis-aligned block whose supplied position is its centre.
    def box(self, centre, size, material="MenuStone"):
        x, y, z = centre
        a, b, c = (v/2 for v in size)
        self.prism([(x-a,z-c),(x+a,z-c),(x+a,z+c),(x-a,z+c)],y-b,y+b,material)

    # Add a tapered vertical polygonal column or pointed spire.
    def column(self, centre, radius, height, top=None, material="MenuStone", sides=12):
        x, y, z = centre
        top = radius if top is None else top
        start = len(self.vertices)
        if top == 0:
            self.vertices.extend((x+radius*math.cos(i*2*math.pi/sides),y+radius*math.sin(i*2*math.pi/sides),z) for i in range(sides))
            self.vertices.append((x,y,z+height))
            self.faces.append(tuple(start+i for i in reversed(range(sides))))
            for i in range(sides):
                self.faces.append((start+i,start+(i+1)%sides,start+sides))
            self.face_materials.extend([material]*(sides+1))
            return
        for level, r in ((z,radius),(z+height,top)):
            self.vertices.extend((x+r*math.cos(i*2*math.pi/sides),y+r*math.sin(i*2*math.pi/sides),level) for i in range(sides))
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
            a=math.pi*i/count+0.012
            b=math.pi*(i+1)/count-0.012
            poly=[(x+radius*math.cos(a),spring+radius*math.sin(a)),(x+(radius+thickness)*math.cos(a),spring+(radius+thickness)*math.sin(a)),(x+(radius+thickness)*math.cos(b),spring+(radius+thickness)*math.sin(b)),(x+radius*math.cos(b),spring+radius*math.sin(b))]
            self.prism(poly,y-depth/2,y+depth/2)

    # Add one elliptical iron chain link in the vertical XZ plane.
    def link(self, centre, radius, alternate=False):
        cx,cy,cz=centre
        sides=12
        ring=6
        start=len(self.vertices)
        for i in range(sides):
            a=i*2*math.pi/sides
            for j in range(ring):
                b=j*2*math.pi/ring
                x=(radius+0.045*math.cos(b))*math.cos(a)
                z=(radius*0.65+0.045*math.cos(b))*math.sin(a)
                y=0.045*math.sin(b)
                self.vertices.append((cx+(y if alternate else x),cy+(x if alternate else y),cz+z))
        for i in range(sides):
            for j in range(ring):
                self.faces.append((start+i*ring+j,start+((i+1)%sides)*ring+j,start+((i+1)%sides)*ring+(j+1)%ring,start+i*ring+(j+1)%ring))
                self.face_materials.append("MenuIron")

    # Produce the Blender mesh with per-face materials and a planar UV layer.
    def finish(self):
        mesh=bpy.data.meshes.new(self.name)
        mesh.from_pydata(self.vertices,[],self.faces)
        mesh.update()
        obj=bpy.data.objects.new(self.name,mesh)
        bpy.context.scene.collection.objects.link(obj)
        names=list(dict.fromkeys(self.face_materials))
        for name in names:
            mesh.materials.append(bpy.data.materials[name])
        uv=mesh.uv_layers.new(name="UVMap")
        for face, name in zip(mesh.polygons,self.face_materials):
            face.material_index=names.index(name)
            if name in ("MenuCarvedStone","MenuRoughStone"):
                face.use_smooth=True
            dominant=max(range(3),key=lambda i:abs(face.normal[i]))
            axes=((1,2),(0,2),(0,1))[dominant]
            for loop_index in face.loop_indices:
                point=mesh.vertices[mesh.loops[loop_index].vertex_index].co
                uv.data[loop_index].uv=(point[axes[0]]*0.5,point[axes[1]]*0.5)
        bpy.context.view_layer.objects.active=obj
        obj.select_set(True)
        if self.name not in ("MenuBanner", "MenuBackdrop", "MenuCrystalSpire"):
            bevel=obj.modifiers.new("Stone edge wear", "BEVEL")
            bevel.width=0.025
            bevel.segments=1
        return obj



# Build a tall, backed gatehouse with deep masonry, full-height grille and hanging chains.
def gate():
    b=MeshBuilder("MenuGate")
    spring,radius,outer=6.0,4.5,6.2
    poly=[(radius,0),(outer,0),(outer,spring)]
    poly.extend((outer*math.cos(i*math.pi/32),spring+outer*math.sin(i*math.pi/32)) for i in range(1,33))
    poly.extend([(-outer,0),(-radius,0),(-radius,spring)])
    poly.extend((radius*math.cos(math.pi-i*math.pi/28),spring+radius*math.sin(math.pi-i*math.pi/28)) for i in range(1,29))
    b.prism(poly,0.0,3.5,"MenuDarkStone")
    for side in (-1,1):
        for row in range(12):
            for col in range(2):
                b.box((side*(5.14+col*1.15),-0.38,row*0.97+0.48),(1.11,1.03,0.92))
        b.box((side*5.9,-0.52,0.3),(3.0,1.55,0.6))
        for x in (side*5.0,side*6.8):
            b.box((x,-0.42,6.2),(0.28,1.26,12.4))
        for i in range(23):
            t=i/22
            b.link((side*(5.8+3.2*t),-0.75,11.5-1.2*math.sin(t*math.pi)),0.26,bool(i%2))
    b.arch(0,-0.48,spring,radius,1.20,1.2,30)
    b.arch(0,-0.57,spring,radius+1.28,0.22,1.3,34)
    for x in (-5.4,-4.1,-2.7,-1.35,0,1.35,2.7,4.1,5.4):
        z=spring+math.sqrt(max(0,outer*outer-x*x))
        b.box((x,0.2,z+0.38),(0.72,2.5,0.75))
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
    return b.finish()


# Build tall buttressed masonry retaining the left archive and right workshop alcoves.
def wall():
    b=MeshBuilder("MenuWallSegment")
    for row in range(11):
        for col in range(16):
            x=-10.2+col*1.34+(0.22 if row%2 else 0)
            if 6<=col<=8 and row<4:
                continue
            b.box((x,0.5,row*0.88+0.44),(1.30,2.8,0.83))
    b.box((0,0.5,9.83),(22.0,3.45,0.5))
    for x in range(-10,11,2):
        b.box((x,0.15,10.65),(0.96,2.9,1.15))
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
        b.box((x,-0.94,7.2),(0.42,0.03,1.8),"MenuWindowGlow")
        b.arch(x,-1.04,8.1,0.23,0.18,0.25,9)
    return b.finish()


# Build a massive masonry tower with slit windows and an accessible battlement platform.
def tower():
    b=MeshBuilder("MenuTower")
    for row in range(13):
        for col in range(4):
            b.box((-1.74+col*1.16,-0.25,row*0.94+0.46),(1.12,4.4,0.89))
    for z in (0.5,4.4,8.5,12.3):
        b.box((0,-0.25,z),(5.2,4.95,0.32))
    b.box((0,-0.25,12.8),(5.8,5.7,0.65))
    for side in (-1,1):
        for x in (-2.35,0,2.35):
            b.box((x,side*2.3-0.25,13.75),(0.9,0.95,1.35))
        b.box((side*2.35,-0.25,13.75),(0.95,0.95,1.35))
    for z in (4.2,7.8,10.7):
        b.box((0,-2.48,z),(0.4,0.025,1.45),"MenuWindowGlow")
        b.arch(0,-2.58,z+0.73,0.22,0.19,0.2,9)
    b.column((0,0.9,13.15),0.82,3.4,0,"MenuDarkStone",9)
    return b.finish()


# Carve a readable crouched winged guardian with separate head, chest, bent limbs and hooked claws.
def statue():
    b=MeshBuilder("MenuStatue")
    b.box((0,0,0.30),(3.4,3.0,0.60))
    b.box((0,0,0.82),(3.0,2.7,0.42))
    b.box((0,0,2.0),(2.55,2.2,2.0))
    for side in (-1,1):
        b.box((side*1.13,-0.9,2.0),(0.28,0.32,1.75),"MenuDarkStone")
    b.box((0,0,3.18),(3.2,2.8,0.40))
    b.box((0,0,3.50),(2.8,2.5,0.26))
    stone="MenuCarvedStone"
    b.oval((0,0.15,5.10),(0.88,0.72,1.28),stone,24,14)
    b.oval((0,-0.24,5.75),(1.03,0.69,0.85),stone,24,14)
    b.segment((0,-0.12,5.9),(0,-0.52,6.85),0.55,0.43)
    b.oval((0,-0.65,7.08),(0.67,0.63,0.76),stone,24,14)
    b.oval((0,-1.23,6.97),(0.48,0.57,0.30),stone,24,12)
    b.oval((0,-1.27,6.65),(0.46,0.45,0.16),stone,20,10)
    b.box((0,-1.57,6.79),(0.64,0.09,0.075),"MenuBlack")
    for side in (-1,1):
        b.oval((side*0.37,-1.12,7.33),(0.26,0.16,0.10),"MenuDarkStone",16,8)
        b.segment((side*0.10,-1.09,7.48),(side*0.60,-0.98,7.51),0.12,0.07)
        b.segment((side*0.49,-0.45,7.54),(side*0.81,-0.20,8.28),0.18,0.015)
        b.oval((side*0.78,0.05,4.42),(0.59,0.81,0.81),stone,22,14)
        b.segment((side*0.83,-0.15,4.55),(side*0.72,-0.98,3.97),0.34,0.24)
        b.oval((side*0.78,-1.03,3.88),(0.48,0.61,0.22),stone,20,10)
        b.segment((side*0.92,-0.18,5.77),(side*1.15,-0.60,4.90),0.34,0.23)
        b.segment((side*1.15,-0.60,4.90),(side*0.94,-1.15,4.05),0.23,0.15)
        b.oval((side*0.94,-1.16,4.03),(0.29,0.30,0.18),stone,18,10)
        for i in range(3):
            x=side*(0.56+i*0.22)
            b.segment((x,-1.27,3.94),(x,-1.72,3.78),0.105,0.035)
            b.segment((x,-1.72,3.78),(x,-1.83,3.58),0.035,0.004)
        wing=[(side*0.65,5.8),(side*1.25,7.42),(side*3.20,9.08),(side*2.95,7.50),(side*3.43,6.88),(side*2.37,6.65),(side*2.22,5.71),(side*1.60,6.05),(side*0.90,5.1)]
        b.prism(wing,0.52,0.72,stone)
        b.segment((side*0.68,0.48,5.76),(side*1.30,0.47,7.42),0.23,0.15)
        b.segment((side*1.30,0.47,7.42),(side*3.20,0.49,9.08),0.15,0.025)
        for x,z in ((2.95,7.50),(3.43,6.88),(2.37,6.65),(2.22,5.71)):
            b.segment((side*1.30,0.45,7.42),(side*x,0.45,z),0.105,0.025)
    return b.finish()


# Build a heavy coal bowl with original sculpted flame tongues on its low pedestal.
def brazier():
    b=MeshBuilder("MenuBrazier")
    b.box((0,0,0.18),(1.65,1.65,0.36))
    b.column((0,0,0.36),0.50,2.35,0.34,sides=12)
    b.column((0,0,2.71),0.35,0.48,0.94,"MenuIron",18)
    b.column((0,0,3.19),0.94,0.12,material="MenuIron",sides=18)
    b.column((0,0,3.31),0.78,0.10,material="MenuEmber",sides=16)
    for i in range(10):
        a=i*math.pi/5
        b.column((0.84*math.cos(a),0.84*math.sin(a),3.13),0.065,0.44,material="MenuIron",sides=6)
    for i in range(9):
        a=i*2.399
        x,y=0.46*math.cos(a),0.46*math.sin(a)
        h=0.95+0.38*math.sin(i*1.8)
        poly=[(x-0.22,3.38),(x+0.24,3.38),(x+0.15,3.75),(x-0.09,3.38+h)]
        b.prism(poly,y-0.16,y+0.16,"MenuFlame")
        b.column((x*0.55,y*0.55,3.35),0.18,0.62+0.1*(i%3),0,"MenuFlameCore",7)
    return b.finish()


# Create an irregular cloth banner with a skeletal looping wave animation.
def banner():
    b=MeshBuilder("MenuBanner")
    b.box((0,0,0),(2.4,0.13,0.13),"MenuIron")
    for row in range(13):
        for col in range(7):
            x=-1.4+col*(2.8/6)
            z=-row*0.40
            y=0.10*math.sin(x*5)+0.03*row*math.sin(x*4)
            if row==12:
                z-=0.22*(col%2)
            b.vertices.append((x,y,z))
    start=len(b.vertices)-13*7
    for row in range(12):
        for col in range(6):
            i=start+row*7+col
            b.faces.append((i,i+1,i+8,i+7))
            b.face_materials.append("MenuCloth")
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
        obj.vertex_groups[lo].add([vertex.index],1.0-blend,"REPLACE")
        if blend>0 and hi!=lo:
            obj.vertex_groups[hi].add([vertex.index],blend,"REPLACE")
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
    b.box((0,0,4.1),(15.7,4.0,8.2),"MenuDarkStone")
    for x in (-7,-2.34,2.34,7):
        b.box((x,0,12.1),(1.15,3.1,7.8))
        b.box((x,0,0.35),(1.65,3.65,0.70))
    for x in (-4.67,0,4.67):
        b.arch(x,0,16.0,1.75,0.60,3.1,18)
    b.box((0,0,18.6),(15.7,3.7,0.55))
    for x in (-6,-3,0,3,6):
        b.box((x,0,19.25),(0.85,3.4,0.8))
    return b.finish()


# Build a rough dark outcrop carrying separate faceted green crystals with visible side faces.
def crystal():
    b=MeshBuilder("MenuCrystalSpire")
    rng=random.Random(64)
    for i in range(20):
        a=i*2.399
        r=rng.uniform(0.2,4.0)
        b.oval((r*math.cos(a),r*math.sin(a),rng.uniform(0.4,4.0)),(rng.uniform(1.3,3.5),rng.uniform(1.3,3.5),rng.uniform(2.0,5.3)),"MenuDarkStone",9,6)
    for i in range(11):
        a=i*2.399
        r=0 if i==0 else rng.uniform(0.7,2.8)
        x,y=r*math.cos(a),r*math.sin(a)
        h=19.0 if i==0 else rng.uniform(9.0,16.5)
        z=5.0+rng.uniform(0,1.5)
        sides=5
        start=len(b.vertices)
        radius=1.25 if i==0 else rng.uniform(0.55,0.95)
        for level,rr in ((z,radius*0.8),(z+h*0.77,radius)):
            b.vertices.extend((x+rr*math.cos(j*2*math.pi/sides),y+rr*math.sin(j*2*math.pi/sides),level) for j in range(sides))
        b.vertices.append((x+0.3*math.sin(a),y+0.2*math.cos(a),z+h))
        b.faces.append(tuple(start+j for j in reversed(range(sides))))
        b.face_materials.append("MenuCrystal")
        for j in range(sides):
            k=(j+1)%sides
            b.faces.append((start+j,start+k,start+sides+k,start+sides+j))
            b.face_materials.append("MenuCrystalDark" if j%3==0 else "MenuCrystal")
            b.faces.append((start+sides+j,start+sides+k,start+sides*2))
            b.face_materials.append("MenuCrystalBright" if j%2 else "MenuCrystal")
    return b.finish()


# Build irregular wet flagstones, broken fissures and layered rubble along both foreground edges.
def courtyard():
    b=MeshBuilder("MenuCourtyard")
    rng=random.Random(71)
    for row in range(30):
        y=-29+row*1.65
        for col in range(30):
            x=-25+col*1.75+(0.82 if row%2 else 0)
            sx,sy=1.67+rng.uniform(-0.10,0.05),1.55+rng.uniform(-0.10,0.05)
            z=-0.10+rng.uniform(-0.04,0.025)
            poly=[(x-sx/2,z-0.11),(x+sx/2,z-0.11),(x+sx/2-0.025,z+0.07),(x-sx/2+0.025,z+0.07)]
            b.prism(poly,y-sy/2,y+sy/2,"MenuWetStone")
    for side in (-1,1):
        for i in range(48):
            position=(side*rng.uniform(8.8,23),rng.uniform(-23,-3),rng.uniform(-0.05,0.9))
            scale=(rng.uniform(0.25,1.65),rng.uniform(0.3,1.5),rng.uniform(0.25,1.4))
            if i<3:
                x,y,z,size=((5.5,-10.2,0.45,(1.3,0.9,0.7)),(6.7,-8.7,0.65,(1.0,0.9,1.0)),(8.6,-5.5,0.35,(1.5,1.1,0.6)))[i]
                position=(side*x,y,z)
                scale=size
            start=len(b.vertices)
            b.oval(position,scale,"MenuRoughStone",18,11)
            for vertex in range(start,len(b.vertices)):
                point=b.vertices[vertex]
                shift=1+rng.uniform(-0.14,0.14)
                b.vertices[vertex]=tuple(position[k]+(point[k]-position[k])*shift for k in range(3))
    return b.finish()


# Build far sculpted mountain ridges, needle towers and low-reflectance storm clouds.
def backdrop():
    b=MeshBuilder("MenuBackdrop")
    rng=random.Random(31)
    b.oval((0,45,0),(190,190,115),"MenuSky",48,24)
    for layer in range(3):
        y=67+layer*20
        points=[(-120,-6)]
        for i in range(32):
            x=-120+i*7.75
            points.extend([(x,rng.uniform(13,23)+layer*3),(x+3.5,rng.uniform(25,42)+layer*3)])
        points.append((124,-6))
        b.prism(points,y,y+12,"MenuMountain")
        for i in range(20):
            x=rng.uniform(-100,100)
            b.oval((x,y-2,rng.uniform(8,22)),(rng.uniform(6,12),rng.uniform(4,9),rng.uniform(7,14)),"MenuMountain",9,6)
    for x,y,h in ((-42,50,28),(-34,57,36),(-28,62,25),(28,60,31),(37,57,39),(47,64,28)):
        b.column((x,y,0),1.8,h,material="MenuDistantStone",sides=10)
        b.column((x,y,h),2.3,7.5,0,"MenuDistantStone",8)
        for j in range(4):
            a=j*math.pi/2
            b.column((x+2.2*math.cos(a),y+2.2*math.sin(a),h-2),0.55,5.5,0,"MenuDistantStone",7)
    for i in range(35):
        b.oval((rng.uniform(-100,100),rng.uniform(38,125),rng.uniform(35,58)),(rng.uniform(13,29),rng.uniform(7,18),rng.uniform(2.5,6)),"MenuCloud",16,7)
    return b.finish()



# Build the vaulted hall beyond the gate without obstructing the entry flight.
def hall():
    b=MeshBuilder("MenuCampaignHall")
    b.box((0,0,-0.15),(13,16,0.3))
    for side in (-1,1):
        b.box((side*6.4,0,3.8),(0.7,16,7.6))
    b.box((0,7.8,3.8),(13,0.7,7.6))
    for y in (-6,-2,2,6):
        b.arch(0,y,5.0,5.8,0.45,0.5,18)
        for side in (-1,1):
            b.column((side*5.8,y,0),0.35,5.1,material="MenuStone",sides=10)
    return b.finish()


# Build the campaign table with a separate plane for the existing map image.
def table():
    b=MeshBuilder("MenuMapTable")
    b.box((0,0,1.55),(4.4,3.2,0.24),"MenuWood")
    for x in (-1.75,1.75):
        for y in (-1.15,1.15):
            b.box((x,y,0.75),(0.24,0.24,1.5),"MenuWood")
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
    return b.finish()


MODELS=(gate,wall,tower,statue,brazier,banner,arches,crystal,courtyard,backdrop,hall,table,cave)
COLOURS={"MenuCarvedStone":(0.22,0.24,0.26),"MenuRoughStone":(0.20,0.22,0.24),"MenuDistantStone":(0.003,0.004,0.006),"MenuStone":(0.30,0.29,0.28),"MenuDarkStone":(0.11,0.12,0.13),"MenuIron":(0.14,0.15,0.16),"MenuWood":(0.18,0.11,0.07),"MenuParchment":(0.42,0.36,0.25),"MenuBlack":(0.012,0.014,0.016),"MenuCloth":(0.25,0.025,0.028),"MenuEmber":(0.9,0.16,0.015),"MenuCrystal":(0.035,0.45,0.055),"MenuMountain":(0.055,0.065,0.07),"MenuCloud":(0.035,0.043,0.049),"MenuSky":(0.012,0.018,0.022),"MenuCampaignMap":(0.7,0.7,0.7),"MenuWindowGlow":(0.8,0.12,0.018),"MenuFlame":(1.0,0.11,0.008),"MenuFlameCore":(1.0,0.42,0.035),"MenuCrystalDark":(0.005,0.12,0.018),"MenuCrystalBright":(0.12,0.8,0.035)}


# Save every model privately first, copy it into the source tree and export its mesh.
def main():
    arguments=sys.argv[sys.argv.index("--")+1:]
    repo,private=map(Path,arguments[:2])
    sys.path.insert(0,str(repo/"tools/blender-assets"))
    import odp_ogre_io as exporter
    source=repo/"assets-src/menu-scene"
    work=repo/"out/menu-scene/xml"
    for folder in (source,work,private):
        folder.mkdir(parents=True,exist_ok=True)
    bpy.context.preferences.filepaths.save_version=0
    report=[]
    for build in MODELS:
        if len(arguments)>2 and build.__name__ not in arguments[2:]:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        for name,colour in COLOURS.items():
            mat=bpy.data.materials.new(name)
            mat.diffuse_color=(*colour,1)
        wet=bpy.data.materials.new("MenuWetStone")
        wet.diffuse_color=(0.30,0.29,0.28,1)
        result=build()
        obj,arm=result if isinstance(result,tuple) else (result,None)
        name=obj.name
        bpy.context.scene.render.fps=24
        bpy.context.scene.frame_start=0
        bpy.context.scene.frame_end=96
        bpy.ops.wm.save_as_mainfile(filepath=str(private/(name+".blend")))
        shutil.copyfile(private/(name+".blend"),source/(name+".blend"))
        stats=exporter.export_mesh_xml(obj,arm,str(private/(name+".mesh.xml")),name+".skeleton" if arm else None,smooth=False)
        shutil.copyfile(private/(name+".mesh.xml"),work/(name+".mesh.xml"))
        if arm:
            exporter.export_skeleton_xml(arm,str(private/(name+".skeleton.xml")))
            shutil.copyfile(private/(name+".skeleton.xml"),work/(name+".skeleton.xml"))
        report.append(name+" "+str(stats))
        print(report[-1],flush=True)
    (work.parent/"models.txt").write_text("\n".join(report)+"\n",encoding="utf-8")


if __name__=="__main__":
    main()
