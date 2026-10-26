"""Author frightened and ghost-hunter gestures on the unchanged native creature rigs.

Convert native mesh/skeleton files to out/ghost-clips/<Name>.mesh.xml and
<Name>.skeleton.xml with the existing Ogre converter before running Blender.
Pass the mesh name and an external output directory after --. Only the new
clip chunks may be spliced into the native binary; never round-trip old clips.
"""
from pathlib import Path
import math
import re
import shutil
import sys
import traceback
import xml.etree.ElementTree as ET
import bpy
from mathutils import Vector, Matrix

REPO=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(REPO/'tools/blender-assets'))
import odp_ogre_io as oo
import odp_fk as fk

# Native deform chains, verified against the original mesh weights and bone hierarchy.
ARMS={
 'Goblin':(('LeftArm','LeftForeArm','LeftHand'),('RightArm','RightForeArm','RightHand')),
 'Elf':(('LeftArm','LeftForeArm','LeftHand'),('RightArm','RightForeArm','RightHand')),
 'Defender':(('LeftArm','LeftForeArm','LeftHand'),('RightArm','RightForeArm','RightHand')),
 'Adventurer':(('Upperarm_L','Forearm_L','Hand_L'),('Upperarm_R','Forearm_R','Hand_R')),
 'Gnome':(('arm_l','forearm_l','hand_l'),('arm_r','forearm_r','hand_r')),
 'Dwarf1':(('arm_l','forearm_l','hand_l'),('arm_r','forearm_r','hand_r')),
 'Dwarf2':(('arm_l','forearm_l','hand_l'),('arm_r','forearm_r','hand_r')),
 'PitDemon':(('Arm_L','Forearm_L','Hand_L'),('Arm_R','Forearm_R','Hand_R')),
 'Knight':(('Arm_L','Forearm_L','Hand_L'),('Arm_R','Forearm_R','Hand_R')),
 'Troll':(('upperhand.L','arm.L','indexf1.L'),('upperhand.R','arm.R','indexf1.R')),
 'skeleton':(('shoulderJointLeft','ellbowLeft','handBoneLeft'),('shoulderJointRight','ellbowRight','handBoneRight')),
 'RunelordDwarf':(('upper_arm.cr.L','forearm.cr.L','hand.cr.L'),('upper_arm.cr.R','forearm.cr.R','hand.cr.R')),
 'Rat':(('FrontLeg_L','FrontLeg_L.001','FrontLeg_L.002'),('FrontLeg_R','FrontLeg_R.001','FrontLeg_R.002')),
 'Roach':(('ArmL','ForearmFrontL','ClawFrontL'),('ArmR','ForearmFrontR','ClawFrontR')),
 'Spider':(('v_B1_L','v_B2_L','v_B3_L'),('v_B1_R','v_B2_R','v_B3_R')),
 'CaveHornet':(('Leg1up_L','Leg1mid_L','Leg1low_L'),('Leg1up_R','Leg1mid_R','Leg1low_R')),
}
TORSO={'Goblin':'Spine','Elf':'Spine','Defender':'Spine','Adventurer':'C2','Gnome':'spine','Dwarf1':'spine','Dwarf2':'spine','PitDemon':'Spine_1','Knight':'Spine_1','Troll':'chest','skeleton':'belly','RunelordDwarf':'spine.cr.01','Rat':'Backbone','Roach':'SpineHigh','Spider':'Body','CaveHornet':'Body'}
HEAD={'Goblin':'Head','Elf':'Head','Defender':'Head','Adventurer':'Head','Gnome':'head','Dwarf1':'head','Dwarf2':'head','PitDemon':'Head','Knight':'Head','Troll':'head','skeleton':'crown','RunelordDwarf':'head.cr','Rat':'Head','Roach':'Head','Spider':'Body2','CaveHornet':'Head'}
BEASTS={'Rat','Roach','Spider','CaveHornet'}
HUNTERS={'PitDemon','Troll','skeleton','RunelordDwarf','Knight','Defender'}

# Reconstruct global joint transforms from the native rest data and authored local keys.
def worlds(rig,keys):
    result={}
    for name in rig.topo:
        loc,rot=rig.rest[name]
        tr,qr=keys[name]
        mat=Matrix.Translation(loc+tr)@(rot@qr).to_matrix().to_4x4()
        parent=rig.parent[name]
        result[name]=result[parent]@mat if parent else mat
    return result

# Add a world-space rotation around a joint already positioned by the preceding body pose.
def turn(spec,name,axis,degrees,pivot=None):
    spec.setdefault(name,{}).setdefault('rot',[]).append((axis,degrees,pivot))

# Bend a real two-segment limb towards a target without stretching or adding any bones.
def reach(spec,world,chain,target,amount):
    upper,lower,hand=chain
    a,b,c=(world[n].translation.copy() for n in chain)
    target=c.lerp(Vector(target),amount)
    ab,bc=(b-a).length,(c-b).length
    direction=target-a
    distance=min(direction.length,(ab+bc)*.985)
    distance=max(distance,abs(ab-bc)+.0001)
    direction.normalize()
    along=(ab*ab-bc*bc+distance*distance)/(2*distance)
    bend=b-a-direction*(b-a).dot(direction)
    if bend.length<.0001:
        bend=Vector((1 if a.x>=0 else -1,0,0))-direction*direction.x
    bend.normalize()
    elbow=a+direction*along+bend*math.sqrt(max(0,ab*ab-along*along))
    wrist=a+direction*distance
    q1=(b-a).rotation_difference(elbow-a)
    q2=(q1@(c-b)).rotation_difference(wrist-elbow)
    axis,angle=q1.to_axis_angle()
    turn(spec,upper,axis,math.degrees(angle),a)
    axis,angle=q2.to_axis_angle()
    turn(spec,lower,axis,math.degrees(angle),elbow)

# Give imported Ogre material slots their existing original diffuse texture for an editable preview.
def original_surfaces(obj):
    files=list((REPO/'materials/scripts').rglob('*.material'))
    definitions='\n'.join(p.read_text(errors='replace') for p in files)
    for material in obj.data.materials:
        pattern=r'(?m)^\s*material\s+'+re.escape(material.name)+r'(?=\s|\{)[^{]*\{'
        match=re.search(pattern,definitions)
        if not match:
            continue
        depth=1
        end=match.end()
        while end<len(definitions) and depth:
            depth+=(definitions[end]=='{')-(definitions[end]=='}')
            end+=1
        textures=re.findall(r'(?m)^\s*texture\s+([^\s]+)',definitions[match.end():end])
        source=next((p for t in textures for p in (REPO/'materials/textures').rglob(Path(t).name) if p.is_file()),None)
        material.use_nodes=True
        bsdf=material.node_tree.nodes.get('Principled BSDF')
        bsdf.inputs['Roughness'].default_value=.80
        if source:
            image=bpy.data.images.load(str(source),check_existing=True)
            image.pack()
            image.filepath='//../../../'+source.relative_to(REPO).as_posix()
            tex=material.node_tree.nodes.new('ShaderNodeTexImage')
            tex.image=image
            material.node_tree.links.new(tex.outputs['Color'],bsdf.inputs['Base Color'])
            if source.suffix.lower()=='.png':
                material.node_tree.links.new(tex.outputs['Alpha'],bsdf.inputs['Alpha'])

# Bake original uniform rest scales into Blender joint positions while retaining native handles and hierarchy.
def bake_native_rest_scales(arm,path):
    bones,parents,animations=oo.read_skeleton(str(path))
    by_name={b['name']:b for b in bones}
    global_rest={}
    total_scale={}
    parent_scale={}
    # Resolve original rest transforms before Blender normalizes edit-bone matrices.
    def resolve(name):
        if name in global_rest:
            return
        b=by_name[name]
        scale=b['scale']
        assert max(scale)-min(scale)<1e-5, 'Nonuniform native rest scale needs a separate exact transform'
        parent=parents.get(name)
        if parent:
            resolve(parent)
        parent_scale[name]=total_scale[parent] if parent else 1.0
        total_scale[name]=parent_scale[name]*scale.x
        local=Matrix.Translation(b['pos'])@b['rot'].to_matrix().to_4x4()@Matrix.Diagonal(Vector((*scale,1)))
        global_rest[name]=global_rest[parent]@local if parent else local
    for name in by_name:
        resolve(name)
    if all(abs(value-1)<1e-6 for value in total_scale.values()):
        return parent_scale
    for ob in bpy.context.view_layer.objects:
        ob.select_set(False)
    arm.select_set(True)
    bpy.context.view_layer.objects.active=arm
    bpy.ops.object.mode_set(mode='EDIT')
    for name,world in global_rest.items():
        bone=arm.data.edit_bones[name]
        bone.matrix=Matrix.Translation(world.translation)@world.to_quaternion().to_matrix().to_4x4()
        bone.length=oo.BONE_LEN*total_scale[name]
    bpy.ops.object.mode_set(mode='OBJECT')
    for action in bpy.data.actions:
        bag=oo._channelbag(action)
        if bag is None:
            continue
        for curve in bag.fcurves:
            match=re.fullmatch(r'pose.bones\["(.+)"\]\.location',curve.data_path)
            if match:
                factor=parent_scale[match.group(1)]
                for key in curve.keyframe_points:
                    key.co.y*=factor
                    key.handle_left.y*=factor
                    key.handle_right.y*=factor
    print('NATIVE_REST_SCALE_BAKED', {n:v for n,v in total_scale.items() if abs(v-1)>1e-6},flush=True)
    return parent_scale

# Convert only new clip translations back to the original native parent-scale convention.
def restore_native_translations(path,parent_scale):
    tree=ET.parse(path)
    for track in tree.findall('./animations/animation/tracks/track'):
        factor=parent_scale[track.get('bone')]
        if abs(factor-1)>1e-6:
            for translation in track.findall('./keyframes/keyframe/translate'):
                for axis in ('x','y','z'):
                    translation.set(axis,format(float(translation.get(axis))/factor,'.9g'))
    tree.write(path,encoding='utf-8',xml_declaration=True)

# Make packed original diffuse references portable relative to the independently editable source file.
def repath_source(name,private):
    source=Path(__file__).parent/(name+'.blend')
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.preferences.filepaths.save_version=0
    for image in bpy.data.images:
        if image.source!='FILE':
            continue
        matches=list((REPO/'materials/textures').rglob(Path(image.filepath).name))
        assert len(matches)==1,(image.name,matches)
        image.filepath='//../../../'+matches[0].relative_to(REPO).as_posix()
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    shutil.copy2(source,private/source.name)
    print('SOURCE_REPATH_DONE',name,flush=True)


# Make the actual one-second body and limb gestures in native model units.
def pose(rig,name,clip,t,height,forward):
    spec={}
    roots=[n for n in rig.order if rig.parent[n] is None]
    up=Vector((0,0,1))
    front=Vector((0,forward,0))
    if clip=='Scared':
        flinch=fk.ease(0,.18,t)*(1-fk.ease(.64,1,t))
        hop=math.sin(math.pi*min(1,max(0,(t-.16)/.44)))
        retreat=fk.ease(.12,.43,t)*(1-fk.ease(.68,1,t))
        shift=-front*(height*.10*retreat)+up*(height*.09*hop)
        for root in roots:
            spec[root]={'move':shift}
        turn(spec,TORSO[name],(1,0,0),forward*14*flinch)
        if HEAD[name]!=TORSO[name]:
            turn(spec,HEAD[name],(1,0,0),-forward*17*flinch)
        world=worlds(rig,rig.solve(spec))
        for chain in ARMS[name]:
            a=world[chain[0]].translation
            side=1 if a.x>=0 else -1
            if name in BEASTS:
                target=a+Vector((side*height*.09,forward*height*.05,height*.18))
            else:
                target=a+Vector((side*height*.16,-forward*height*.01,height*.27))
            reach(spec,world,chain,target,flinch)
        if name=='CaveHornet':
            for side in ('L','R'):
                for wing in ('Wing1_','Wing2_'):
                    turn(spec,wing+side,(0,1,0),(1 if side=='L' else -1)*(22+9*math.sin(t*math.pi*14))*flinch)
        if name=='Rat':
            turn(spec,'Tail',(0,0,1),18*flinch*math.sin(t*math.pi*3))
        if name=='Roach':
            turn(spec,'Tail',(1,0,0),-forward*20*flinch)
        return spec
    if clip=='Beam':
        # A fixed grip with periodic recoil makes the loop endpoints identical.
        # Repeated boundary poses give the sampled linear curves zero velocity on both sides of the wrap.
        envelope=fk.ease(1/24,3/24,t)*(1-fk.ease(21/24,23/24,t))
        recoil=(.5-.5*math.cos(t*math.pi*6))*envelope
        turn(spec,TORSO[name],(1,0,0),forward*(5+2*recoil))
        world=worlds(rig,rig.solve(spec))
        for index,chain in enumerate(ARMS[name]):
            a=world[chain[0]].translation
            side=1 if a.x>=0 else -1
            target=Vector((side*height*.045,a.y+forward*height*(.30-.012*recoil),a.z-height*(.10 if index==0 else .07)))
            reach(spec,world,chain,target,1)
    elif clip=='Throw':
        backswing=fk.ease(0,.23,t)*(1-fk.ease(.23,.48,t))
        release=fk.ease(.23,.57,t)*(1-fk.ease(.78,1,t))
        turn(spec,TORSO[name],(1,0,0),-forward*12*release)
        world=worlds(rig,rig.solve(spec))
        for index,chain in enumerate(ARMS[name]):
            a=world[chain[0]].translation
            side=1 if a.x>=0 else -1
            if index==1:
                target=a+Vector((side*height*.04,forward*height*(-.18*backswing+.29*release),height*(-.24*backswing+.01*release)))
                reach(spec,world,chain,target,min(1,backswing+release))
            else:
                target=a+Vector((side*height*.12,forward*height*.08,-height*.16))
                reach(spec,world,chain,target,.6*release)
    elif clip=='Empty':
        lift=fk.ease(.03,.28,t)*(1-fk.ease(.80,1,t))
        tip=fk.ease(.30,.48,t)*(1-fk.ease(.73,.88,t))
        shake=math.sin(t*math.pi*14)*tip
        turn(spec,TORSO[name],(1,0,0),-forward*19*lift)
        world=worlds(rig,rig.solve(spec))
        for index,chain in enumerate(ARMS[name]):
            a=world[chain[0]].translation
            side=1 if a.x>=0 else -1
            target=Vector((side*height*.07,a.y+forward*height*(.27+.014*shake),a.z-height*.06+height*.035*tip))
            reach(spec,world,chain,target,lift)
            turn(spec,chain[2],(1,0,0),-forward*(78+7*shake)*tip)
    return spec

# Capture a normal Blender still of the real posed mesh for visual review, never an engine claim.
def preview(obj,arm,action,path,t):
    oo.assign_action(arm,action)
    bpy.context.scene.frame_set(int(t*oo.FPS),subframe=t*oo.FPS-int(t*oo.FPS))
    bpy.context.view_layer.update()
    bpy.context.scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)

# Import one actual rig, author only the requested new actions, and retain its editable mesh source.
def main():
    args=sys.argv[sys.argv.index('--')+1:]
    name=args[0]
    out=REPO/'out/ghost-clips'
    private=Path(args[1])
    private.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version=0
    if '--repath' in args:
        repath_source(name,private)
        return
    arm=oo.import_skeleton(str(out/(name+'.skeleton.xml')),name+'NativeRig')
    parent_scale=bake_native_rest_scales(arm,out/(name+'.skeleton.xml'))
    obj=oo.import_mesh(str(out/(name+'.mesh.xml')),arm,name)
    original_surfaces(obj)
    rig=fk.Rig(arm,'Idle',0)
    base=worlds(rig,rig.base)
    height=max(v.co.z for v in obj.data.vertices)-min(v.co.z for v in obj.data.vertices)
    # Original creature meshes face -Y; an idle head lean is not a facing indicator.
    forward=-1
    clips=('Beam','Throw','Empty') if name in HUNTERS else ('Scared',)
    print('NATIVE_RIG',name,'height',height,'forward',forward,'chains',ARMS[name],flush=True)
    actions=[]
    for clip in clips:
        action=fk.build_clip(rig,clip,1.0,lambda t:pose(rig,name,clip,t,height,forward),step=1/24)
        action.use_fake_user=True
        actions.append(action)
    for action in bpy.data.actions:
        action.use_fake_user=True
    export=out/(name+'.authored.skeleton.xml')
    oo.export_skeleton_xml(arm,str(export),only_actions=set(clips))
    restore_native_translations(export,parent_scale)
    oo.assign_action(arm,actions[0])
    scene=bpy.context.scene
    scene.frame_start=0
    scene.frame_end=24
    scene.frame_set(0)
    source=Path(__file__).parent/(name+'.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(source))
    shutil.copy2(source,private/source.name)
    if '--source-only' in args:
        print('GHOST_CLIPS_DONE',name,','.join(clips),flush=True)
        return
    scene.render.engine='BLENDER_EEVEE'
    scene.render.resolution_x=640
    scene.render.resolution_y=640
    scene.render.resolution_percentage=100
    scene.render.film_transparent=True
    scene.world=bpy.data.worlds.new('Rig preview')
    scene.world.color=(.07,.07,.07)
    lo=Vector(tuple(min(v.co[i] for v in obj.data.vertices) for i in range(3)))
    hi=Vector(tuple(max(v.co[i] for v in obj.data.vertices) for i in range(3)))
    centre=(lo+hi)/2
    size=max(hi-lo)
    bpy.ops.object.camera_add(location=centre+Vector((size*1.5,forward*size*2.6,size*1.0)))
    camera=bpy.context.object
    camera.rotation_euler=(centre-camera.location).to_track_quat('-Z','Y').to_euler()
    camera.data.type='ORTHO'
    camera.data.ortho_scale=size*1.8
    scene.camera=camera
    for pos,power in ((centre+Vector((size*2,forward*size*2,size*3)),350),(centre+Vector((-size*2,-forward*size,size)),190)):
        bpy.ops.object.light_add(type='AREA',location=pos)
        light=bpy.context.object
        light.data.energy=power*size*size
        light.data.shape='DISK'
        light.data.size=size*2
        light.rotation_euler=(centre-light.location).to_track_quat('-Z','Y').to_euler()
    scene.view_settings.view_transform='AgX'
    for action in actions:
        preview(obj,arm,action,private/(name+'-'+action.name+'-pose.png'),.40 if action.name=='Scared' else .55)
    if name in {'Goblin','Rat','CaveHornet','PitDemon','RunelordDwarf'}:
        preview(obj,arm,actions[0],private/(name+'-'+actions[0].name+'-start.png'),0)
        preview(obj,arm,actions[0],private/(name+'-'+actions[0].name+'-end.png'),1)
    print('GHOST_CLIPS_DONE',name,','.join(clips),flush=True)

if __name__=='__main__':
    unit=sys.argv[sys.argv.index('--')+1]
    log=REPO/'out/ghost-clips'/(unit+'.author.log')
    with log.open('w',encoding='utf-8',buffering=1) as stream:
        sys.stdout=stream
        sys.stderr=stream
        try:
            main()
        except Exception:
            traceback.print_exc()
            raise
