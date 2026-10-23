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


# Build a ruined gatehouse with a horned skull crown, iron points and worn hanging chains.
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
                    (1.11+rng.uniform(-0.08,0.03),1.03,0.92+rng.uniform(-0.07,0.02)))
        b.box((side*5.9,-0.52,0.3),(3.0,1.55,0.6))
        for x in (side*5.0,side*6.8):
            b.box((x,-0.42,6.2),(0.28,1.26,12.4))
        for i in range(23):
            t=i/22
            b.link((side*(5.8+3.2*t),-0.75+0.07*math.sin(i*1.7),11.5-(1.35 if side<0 else 0.95)*math.sin(t*math.pi)),0.26+rng.uniform(-0.025,0.015),bool(i%2))
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
    b.oval((0,-1.20,12.25),(0.84,0.48,0.86),"MenuCarvedStone",22,14)
    b.oval((0,-1.48,11.68),(0.58,0.28,0.29),"MenuCarvedStone",18,10)
    for side in (-1,1):
        b.oval((side*0.34,-1.61,12.36),(0.25,0.11,0.24),"MenuBlack",16,10)
        b.segment((side*0.65,-1.15,12.65),(side*1.16,-1.05,13.21),0.27,0.20,"MenuCarvedStone",12)
        b.segment((side*1.16,-1.05,13.21),(side*1.40,-0.88,13.92),0.20,0.11,"MenuCarvedStone",12)
        b.segment((side*1.40,-0.88,13.92),(side*1.14,-0.78,14.33),0.11,0.01,"MenuCarvedStone",10)
    b.prism([(-0.11,12.17),(0.11,12.17),(0,11.93)],-1.69,-1.58,"MenuBlack")
    for x in (-0.36,-0.18,0,0.18,0.36):
        b.box((x,-1.73,11.62),(0.10,0.09,0.17),"MenuDarkStone")
    return b.finish()


# Build damaged buttressed masonry with broken spiked crenels while retaining both menu alcoves.
def wall():
    b=MeshBuilder("MenuWallSegment")
    rng=random.Random(307)
    for row in range(11):
        for col in range(16):
            x=-10.2+col*1.34+(0.22 if row%2 else 0)
            if 6<=col<=8 and row<4:
                continue
            if (row,col) in ((8,2),(6,12),(9,13),(4,4)):
                continue
            b.box((x+rng.uniform(-0.06,0.06),0.5+rng.uniform(-0.08,0.06),row*0.88+0.44),
                (1.30+rng.uniform(-0.10,0.02),2.8,0.83+rng.uniform(-0.08,0.02)))
    b.box((0,0.5,9.83),(22.0,3.45,0.5))
    for x in range(-10,11,2):
        if x in (-6,4):
            b.prism([(x-0.48,10.08),(x+0.48,10.08),(x+0.44,10.42),(x-0.15,10.77)],-1.30,1.6)
        else:
            b.box((x,0.15,10.65+rng.uniform(-0.13,0.10)),(0.96,2.9,1.15))
            b.column((x,-0.92,11.22),0.18,0.80+rng.uniform(-0.14,0.20),0,"MenuIron",7)
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
    for i in range(24):
        b.oval((rng.uniform(-10.7,10.7),rng.uniform(-2.9,-1.2),rng.uniform(0,0.20)),
            (rng.uniform(0.12,0.65),rng.uniform(0.15,0.47),rng.uniform(0.12,0.43)),"MenuRoughStone",10,6)
    return b.finish()


# Build a weathered tower with missing masonry, broken iron-tipped crenels and an accessible platform.
def tower():
    b=MeshBuilder("MenuTower")
    rng=random.Random(407)
    for row in range(13):
        for col in range(4):
            if (row,col) in ((8,0),(10,3),(3,1)):
                continue
            b.box((-1.74+col*1.16+rng.uniform(-0.045,0.045),-0.25+rng.uniform(-0.05,0.04),row*0.94+0.46),
                (1.12+rng.uniform(-0.09,0.025),4.4,0.89+rng.uniform(-0.05,0.02)))
    for z in (0.5,4.4,8.5,12.3):
        b.box((0,-0.25,z),(5.2,4.95,0.32))
    b.box((0,-0.25,12.8),(5.8,5.7,0.65))
    for side in (-1,1):
        for x in (-2.35,0,2.35):
            if side<0 and x==2.35:
                b.prism([(x-0.45,13.07),(x+0.45,13.07),(x+0.18,13.61),(x-0.31,13.37)],side*2.3-0.73,side*2.3+0.23)
            else:
                b.box((x,side*2.3-0.25,13.75+rng.uniform(-0.12,0.07)),(0.9,0.95,1.35))
                b.column((x,side*2.3-0.25,14.42),0.19,0.90+rng.uniform(-0.1,0.20),0,"MenuIron",7)
        b.box((side*2.35,-0.25,13.75),(0.95,0.95,1.35))
    for z in (4.2,7.8,10.7):
        weather_marks(b,0,-2.51,z+1.55,0.98,1.1)
        b.box((0,-2.48,z),(0.4,0.025,1.45),"MenuWindowGlow")
        b.arch(0,-2.58,z+0.73,0.22,0.19,0.2,9)
    weather_marks(b,-1.6,-2.505,6.0,0.55,2.8)
    for i in range(15):
        b.oval((rng.uniform(-3,3),rng.uniform(-3.4,-2.5),rng.uniform(0,0.2)),
            (rng.uniform(0.14,0.58),rng.uniform(0.14,0.44),rng.uniform(0.13,0.41)),"MenuRoughStone",10,6)
    b.column((0,0.9,13.15),0.82,3.4,0,"MenuDarkStone",9)
    return b.finish()


# Carve a weathered winged guardian with a fractured wingtip, fissures and readable anatomy.
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
        tip=(2.88,8.52) if side<0 else (3.20,9.08)
        wing=[(side*0.65,5.8),(side*1.25,7.42),(side*tip[0],tip[1])]
        if side<0:
            wing.extend([(side*2.69,8.41),(side*2.91,8.17)])
        wing.extend([(side*2.95,7.50),(side*3.43,6.88),(side*2.37,6.65),(side*2.22,5.71),(side*1.60,6.05),(side*0.90,5.1)])
        b.prism(wing,0.52,0.72,stone)
        b.segment((side*0.68,0.48,5.76),(side*1.30,0.47,7.42),0.23,0.15)
        b.segment((side*1.30,0.47,7.42),(side*tip[0],0.49,tip[1]),0.15,0.025)
        for x,z in ((2.95,7.50),(3.43,6.88),(2.37,6.65),(2.22,5.71)):
            b.segment((side*1.30,0.45,7.42),(side*x,0.45,z),0.105,0.025)
        b.prism([(side*1.74,7.33),(side*1.80,7.34),(side*1.96,6.91),(side*1.88,6.69),
            (side*2.15,6.49),(side*2.10,6.43),(side*1.81,6.67),(side*1.87,6.91)],0.495,0.51,"MenuBlack")
    b.prism([(-0.28,6.20),(-0.23,6.21),(-0.11,5.87),(-0.20,5.59),(0.04,5.29),
        (-0.02,5.25),(-0.27,5.59),(-0.18,5.87)],-0.98,-0.95,"MenuBlack")
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


# Create a torn, holed cloth banner with an uneven hem and its existing looping wave animation.
def banner():
    b=MeshBuilder("MenuBanner")
    b.box((0,0,0),(2.4,0.13,0.13),"MenuIron")
    for row in range(13):
        for col in range(7):
            x=-1.4+col*(2.8/6)
            z=-row*0.40
            y=0.10*math.sin(x*5)+0.03*row*math.sin(x*4)
            if row>=10:
                z-=0.10*(col%3)+0.13*math.sin(col*2.8+row)
            if row==12:
                z+=0.14+(0.36 if col in (1,5) else -0.12)
            b.vertices.append((x,y,z))
    start=len(b.vertices)-13*7
    for row in range(12):
        for col in range(6):
            if (row,col) in ((6,1),(7,1),(10,5),(11,5),(11,0)):
                continue
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


# Build broken, sunken and uneven flagstones with irregular puddles and scattered rubble.
def courtyard():
    b=MeshBuilder("MenuCourtyard")
    rng=random.Random(71)
    for row in range(30):
        y=-29+row*1.65
        for col in range(30):
            x=-25+col*1.75+(0.82 if row%2 else 0)
            sx,sy=1.67+rng.uniform(-0.10,0.05),1.55+rng.uniform(-0.10,0.05)
            z=-0.10+rng.uniform(-0.13,0.065)
            if rng.random()<0.045:
                continue
            if rng.random()<0.16:
                b.prism([(x-sx/2,z-0.11),(x+0.12,z-0.11),(x-0.08,z+0.07),(x-sx/2+0.025,z+0.11)],
                    y-sy/2,y+sy/2,"MenuWetStone")
                b.prism([(x+0.20,z-0.19),(x+sx/2,z-0.19),(x+sx/2-0.025,z-0.03),(x+0.01,z+0.005)],
                    y-sy/2+0.08,y+sy/2-0.05,"MenuWetStone")
            else:
                poly=[(x-sx/2,z-0.11),(x+sx/2,z-0.11),(x+sx/2-0.025,z+0.07+rng.uniform(-0.04,0.05)),(x-sx/2+0.025,z+0.07)]
                b.prism(poly,y-sy/2,y+sy/2,"MenuWetStone")
    b.box((0,-4,-0.39),(56,58,0.12),"MenuDarkStone")
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
    for i in range(62):
        b.oval((rng.uniform(-18,18),rng.uniform(-22,12),rng.uniform(-0.09,0.05)),
            (rng.uniform(0.06,0.23),rng.uniform(0.07,0.28),rng.uniform(0.05,0.19)),"MenuRoughStone",8,5)
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
COLOURS={"MenuSoot":(0.009,0.007,0.005),"MenuPuddle":(0.05,0.05,0.045),"MenuCarvedStone":(0.22,0.24,0.26),"MenuRoughStone":(0.20,0.22,0.24),"MenuDistantStone":(0.003,0.004,0.006),"MenuStone":(0.30,0.29,0.28),"MenuDarkStone":(0.11,0.12,0.13),"MenuIron":(0.14,0.15,0.16),"MenuWood":(0.18,0.11,0.07),"MenuParchment":(0.42,0.36,0.25),"MenuBlack":(0.012,0.014,0.016),"MenuCloth":(0.25,0.025,0.028),"MenuEmber":(0.9,0.16,0.015),"MenuCrystal":(0.035,0.45,0.055),"MenuMountain":(0.055,0.065,0.07),"MenuCloud":(0.035,0.043,0.049),"MenuSky":(0.012,0.018,0.022),"MenuCampaignMap":(0.7,0.7,0.7),"MenuWindowGlow":(0.8,0.12,0.018),"MenuFlame":(1.0,0.11,0.008),"MenuFlameCore":(1.0,0.42,0.035),"MenuCrystalDark":(0.005,0.12,0.018),"MenuCrystalBright":(0.12,0.8,0.035)}


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
