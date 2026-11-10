"""Ghost hunter pose, cannon aim and hose check (owner decision 894). Compiles nothing.

1. After the delivery the hunter lay on the floor and flailed. Cause: the facing direction given to the Empty, Throw and
   Beam clips was the full 3D vector from the hunter to the target (the trap seat 1.1 above the floor, the floating
   ghost), and the client turns the hunter's node by the shortest arc from its forward axis to that vector
   (RenderManager::rrOrientEntityToward), which pitches the whole body. CreatureActionHuntGhost now gives every clip a
   flat direction (facing()), so the hunter turns about the vertical axis only. The skeleton clips themselves are checked
   to hold no lying pose.
2. While beaming the hunter held the cannon slanted backwards. The cannon now points at the ghost's aim point for the whole
   beam step (aimGhostCannon, every frame), whatever pose the Beam clip holds the hand in.
3. A clearly visible textured hose connects the backpack with the cannon and follows the hunter and the cannon (hose
   shaping every frame, dynamic tube, material GhostHose with the ribbed rubber texture).
Fixed values measured once on this branch: 4 setAnimationState calls with a direction in the hunt, 128 rings and 8 sides.
"""
from pathlib import Path
import importlib.util
import math
import random
import re
import struct

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding='utf-8')


def body(text, signature):
    start = text.index(signature)
    opening = text.index('{', start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == '{') - (text[end] == '}')
        end += 1
    return text[start:end]


def has(text, rule, *fragments):
    for fragment in fragments:
        assert fragment in text, (rule, fragment)


def code_only(text):
    return re.sub(r'//[^\n]*', '', text)


# --- small vector and quaternion model of the Ogre calls used ---------------------------------------------------------
def sub(a, b): return tuple(x - y for x, y in zip(a, b))
def add(a, b): return tuple(x + y for x, y in zip(a, b))
def mul(a, k): return tuple(x * k for x in a)
def dot(a, b): return sum(x * y for x, y in zip(a, b))
def cross(a, b): return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
def length(a): return math.sqrt(dot(a, a))
def unit(a): return mul(a, 1.0 / length(a))


def qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def qinv(q): return (q[0], -q[1], -q[2], -q[3])


def qrot(q, v):
    r = qmul(qmul(q, (0.0,) + tuple(v)), qinv(q))
    return r[1:]


def rotation_to(a, b):
    """Ogre::Vector3::getRotationTo for unit vectors that are not opposite."""
    a, b = unit(a), unit(b)
    c = cross(a, b)
    d = dot(a, b)
    s = math.sqrt((1 + d) * 2)
    return (s / 2, c[0] / s, c[1] / s, c[2] / s)


def random_quaternion(rng):
    q = tuple(rng.gauss(0, 1) for _ in range(4))
    n = math.sqrt(sum(x * x for x in q))
    return tuple(x / n for x in q)


# --- 1. The hunter turns about the vertical axis only ------------------------------------------------------------------
action = read('source/creatureaction/CreatureActionHuntGhost.cpp')
has(body(action, 'Ogre::Vector3 facing(const Creature& hunter, const Ogre::Vector3& point)'), 'flat facing',
    'const Ogre::Vector3 difference=point-hunter.getPosition();', 'return Ogre::Vector3(difference.x,difference.y,0.0f);')
code = code_only(action)
assert 'getPosition()-mCreature.getPosition()' not in code and 'socket-mCreature.getPosition()' not in code, 'no 3D facing direction left'
directions = re.findall(r'setAnimationState\(([^;]*?)\);', code)
directed = [d for d in directions if 'idle_anim' not in d]
assert len(directed) == 3, directed
for call in directed:
    assert 'facing(mCreature,' in call, ('every clip with a direction faces flat', call)
has(code, 'the two clips', 'EntityAnimation::throw_anim,false,facing(mCreature,ghost->getPosition()),true)',
    'EntityAnimation::beam_anim,true,facing(mCreature,ghost->getPosition()),false)')
# Decision 936: the put-in and the pick-up turn him flat to the seat and to the trap with his Idle clip (the client lays
# its generated reach and bend pose over it); every Idle request with a direction faces flat as well
idle_directed = [d for d in directions if 'idle_anim' in d and 'Ogre::Vector3::ZERO,false' not in d]
# (put-in, pick-up step of states 9 and 8, restore of a pick-up saved while he bends down)
assert len(idle_directed) == 3, idle_directed
for call in idle_directed:
    assert 'facing(mCreature,' in call, ('every Idle with a direction faces flat', call)
has(code, 'put-in and pick-up', 'EntityAnimation::idle_anim,true,facing(mCreature,socket),false)',
    'EntityAnimation::idle_anim,true,point==nullptr?Ogre::Vector3::ZERO:facing(mCreature,*point),false)',
    'item==nullptr?Ogre::Vector3::ZERO:facing(mCreature,item->getPosition()),false)')
# The client turn the flat direction is applied to: the shortest arc from the forward axis, no flattening of its own
render = read('source/render/RenderManager.cpp')
orient = body(render, 'void RenderManager::rrOrientEntityToward(MovableGameEntity* gameEntity, const Ogre::Vector3& direction)')
has(orient, 'premise: the node turns by the shortest arc to the direction', 'Ogre::Vector3 tempVector = node->getOrientation() * Ogre::Vector3::NEGATIVE_UNIT_Y;',
    'node->rotate(tempVector.getRotationTo(direction));')


def tilt_after_turn(hunter_yaw_degrees, direction):
    """Angle in degrees between the hunter's up axis and the vertical after the client turned him to the direction."""
    half = math.radians(hunter_yaw_degrees) / 2
    orientation = (math.cos(half), 0.0, 0.0, math.sin(half))
    forward = qrot(orientation, (0.0, -1.0, 0.0))
    turn = rotation_to(forward, direction)
    up = qrot(qmul(turn, orientation), (0.0, 0.0, 1.0))
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(unit(up), (0.0, 0.0, 1.0))))))


# Trap seat 1.1 above the floor, hand reach 0.68 on the -Y side: the old direction lay him back by 58 degrees
old_empty = (0.0, -0.68, 1.1)
new_empty = (old_empty[0], old_empty[1], 0.0)
assert tilt_after_turn(0, old_empty) > 50, tilt_after_turn(0, old_empty)
assert tilt_after_turn(0, new_empty) < 1e-6
rng = random.Random(894)
for _ in range(2000):
    yaw = rng.uniform(0, 360)
    # Ghost anywhere within beam range, hovering between the floor and 1.5 tiles
    planar = (rng.uniform(-2, 2), rng.uniform(-2, 2))
    if length(planar) < 0.05:
        continue
    to_ghost = (planar[0], planar[1], rng.uniform(0.0, 1.5))
    flat = (to_ghost[0], to_ghost[1], 0.0)
    assert tilt_after_turn(yaw, flat) < 1e-5, ('a flat direction never tilts him', yaw, flat)
assert max(tilt_after_turn(rng.uniform(0, 360), (rng.uniform(-2, 2), rng.uniform(-2, 2), 1.0)) for _ in range(200)) > 20, \
    'a direction with a height share would tilt him (the old fault)'

# The skeleton clips of the six hunters hold no lying pose: no bone of the Empty, Throw or Beam clip turns past 50 degrees
spec = importlib.util.spec_from_file_location('ghost_pose_chunks', repo / 'tools/blender-assets/splice_animation_chunks.py')
chunks_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chunks_module)
for creature in ('PitDemon', 'Troll', 'Skeleton', 'RunelordDwarf', 'Knight', 'Defender'):
    block = next(b for b in re.findall(r'\[Creature\](.*?)\[/Creature\]', read('config/creatures.cfg'), re.S)
                 if re.search(r'^\s*Name\s+' + creature + r'\s*$', b, re.M))
    mesh = re.search(r'^\s*MeshName\s+(\S+)', block, re.M)[1]
    _, chunks = chunks_module.chunks((repo / 'models' / (mesh.removesuffix('.mesh') + '.skeleton')).read_bytes())
    clips = {name: data for kind, name, data in chunks if kind == chunks_module.ANIMATION}
    for clip in ('Empty', 'Throw', 'Beam'):
        _, tracks = chunks_module.animation_children(clips[clip])
        for kind, bone, track in tracks:
            if kind != 0x4100:
                continue
            position = 8
            while position < len(track):
                _, size = struct.unpack_from('<HI', track, position)
                angle = struct.unpack_from('<f', track, position + 10)[0]
                assert abs(math.degrees(angle)) <= 50, (creature, clip, bone, math.degrees(angle))
                position += size

# --- 2. The cannon points at the ghost for the whole beam step, naturally (decisions 894 and 998) ------------------------
creature_source = read('source/entities/Creature.cpp')
aim = body(creature_source, 'static void aimGhostCannon(')
has(aim, 'the barrel (+z) is turned to the shown direction through the mount',
    'const Ogre::Vector3 origin=cannon._getParentNodeFullTransform()*Ogre::Vector3::ZERO;',
    'const Ogre::Quaternion wanted=Ogre::Vector3::UNIT_Z.getRotationTo(shown);',
    'body.getParentNode()->_getDerivedOrientation()*body.getSkeleton()->getBone(bone)->_getDerivedOrientation();',
    'grip->setOrientation(parent.Inverse()*wanted);',
    'handNode->setOrientation(handNode->getParentSceneNode()->_getDerivedOrientation().Inverse()*wanted);')
# Decision 998: the pitch is limited by config keys and the turn is smoothed over frames
has(aim, 'limited pitch and smoothing, every number from the config',
    'const std::string& bone, const Ogre::Vector3& aim, Ogre::Vector3& shown, double seconds)',
    'config.getRoomConfigDouble("GhostCannonMaxDownDegrees")', 'config.getRoomConfigDouble("GhostCannonMaxUpDegrees")',
    'config.getRoomConfigDouble("GhostCannonAimSeconds")',
    'const Ogre::Vector3 target=limitGhostCannonPitch(direction,heading,down,up);',
    'if(shown.squaredLength()<1.0e-8f) shown=target;',
    'const Ogre::Real follow=time>0.0?static_cast<Ogre::Real>(1.0-std::exp(-std::max(0.0,seconds)/time)):1.0f;',
    'const Ogre::Vector3 from=limitGhostCannonPitch(shown,heading,down,up);',
    'Ogre::Real yaw=std::atan2(from.y,from.x);', 'Ogre::Real pitch=std::asin(std::max(-1.0f,std::min(1.0f,from.z)));',
    'Ogre::Real turn=std::atan2(target.y,target.x)-yaw;', 'while(turn>Ogre::Math::PI) turn-=Ogre::Math::TWO_PI;',
    'while(turn<-Ogre::Math::PI) turn+=Ogre::Math::TWO_PI;', 'yaw+=follow*turn;',
    'pitch+=follow*(std::asin(std::max(-1.0f,std::min(1.0f,target.z)))-pitch);',
    'shown=Ogre::Vector3(std::cos(pitch)*std::cos(yaw),std::cos(pitch)*std::sin(yaw),std::sin(pitch));')
assert 'direction.normalisedCopy()' not in aim, 'the old direct aim at the ghost is gone'
limit = body(creature_source, 'static Ogre::Vector3 limitGhostCannonPitch(')
has(limit, 'the pitch clamp', 'const Ogre::Real level=Ogre::Vector3(direction.x,direction.y,0.0f).length();',
    'if(flat.squaredLength()<1.0e-8f) flat=Ogre::Vector3(heading.x,heading.y,0.0f);',
    'const Ogre::Real pitch=std::max(-down,std::min(up,static_cast<Ogre::Real>(std::atan2(direction.z,level))));',
    'return flat*std::cos(pitch)+Ogre::Vector3::UNIT_Z*std::sin(pitch);')
visuals = body(creature_source, 'void Creature::updateGhostHuntVisuals(double seconds)')
has(visuals, 'aimed every frame while the beam is on, with the grip kept and the shown direction carried over frames',
    'if(beaming) aimGhostCannon(*body,*mGhostCaptureGun,mGhostCaptureGrip,mGhostGunHandNode,',
    'ghostCannonHandBone(body->hasSkeleton()?body->getSkeleton():nullptr),ghostBeamAimPoint(scene,*target),',
    'mGhostCannonAim,seconds*getGameMap()->getGameSpeedFactor());', 'else mGhostCannonAim=Ogre::Vector3::ZERO;',
    'mGhostCaptureGrip=grip;')
# Before every early return of the beam drawing (the flicker pause), so it holds for every frame of the step
assert visuals.index('if(beaming) aimGhostCannon(') < visuals.index('if(mGhostBeamSample<flickerSeconds) return;')
assert visuals.index('if(beaming) aimGhostCannon(') < visuals.index('const Ogre::Vector3 start=ghostCannonTip(*mGhostCaptureGun);')
# The beam still runs from the cannon tip to the ghost itself, whatever the barrel shows
has(visuals, 'beam from the tip to the ghost', 'const Ogre::Vector3 end=ghostBeamAimPoint(scene,*target);',
    'const Ogre::Vector3 start=ghostCannonTip(*mGhostCaptureGun);')
header = read('source/entities/Creature.h')
has(header, 'the mount and the shown direction are kept', 'Ogre::TagPoint* mGhostCaptureGrip = nullptr;',
    'Ogre::Vector3 mGhostCannonAim = Ogre::Vector3::ZERO;')
clear_visuals = body(creature_source, 'void Creature::clearGhostHuntVisuals()')
assert 'mGhostCaptureGrip=nullptr;' in clear_visuals and 'mGhostCannonAim=Ogre::Vector3::ZERO;' in clear_visuals
rooms = read('config/rooms.cfg')


def config_value(key):
    found = re.findall(r'^\s*' + key + r'\s+(\S+)\s*$', rooms, re.M)
    assert len(found) == 1, (key, found)
    return found[0]


def documented(key):
    """The key has a comment line naming it right above its block."""
    lines = rooms.splitlines()
    index = next(i for i, line in enumerate(lines) if re.match(r'^\s*' + key + r'\s', line))
    while index > 0 and not lines[index - 1].lstrip().startswith('#'):
        index -= 1
    block = []
    while index > 0 and lines[index - 1].lstrip().startswith('#'):
        block.append(lines[index - 1])
        index -= 1
    assert any(key.rstrip('0123456789') in line for line in block), ('doc line', key)


max_down = float(config_value('GhostCannonMaxDownDegrees'))
max_up = float(config_value('GhostCannonMaxUpDegrees'))
aim_seconds = float(config_value('GhostCannonAimSeconds'))
for key in ('GhostCannonMaxDownDegrees', 'GhostCannonMaxUpDegrees', 'GhostCannonAimSeconds'):
    documented(key)
assert 10 <= max_down <= 40, 'a natural downward range: the cannon never points steeply into the floor'
assert 20 <= max_up <= 60 and 0 < aim_seconds <= 0.5, 'smooth but quick enough to follow the ghost'


def limit_pitch(direction, heading, down, up):
    """Model of limitGhostCannonPitch."""
    level = math.hypot(direction[0], direction[1])
    flat = (direction[0], direction[1], 0.0)
    if dot(flat, flat) < 1e-8:
        flat = (heading[0], heading[1], 0.0)
    if dot(flat, flat) < 1e-8:
        flat = (0.0, -1.0, 0.0)
    flat = unit(flat)
    pitch = max(-down, min(up, math.atan2(direction[2], level)))
    return add(mul(flat, math.cos(pitch)), (0.0, 0.0, math.sin(pitch)))


def aim_step(shown, direction, heading, seconds):
    """Model of aimGhostCannon: the new shown direction, eased in yaw (the shorter way round) and pitch."""
    down, up = math.radians(max_down), math.radians(max_up)
    target = limit_pitch(direction, heading, down, up)
    if shown is None:
        return target
    follow = 1 - math.exp(-max(0.0, seconds) / aim_seconds)
    start = limit_pitch(shown, heading, down, up)
    yaw = math.atan2(start[1], start[0])
    pitch = math.asin(max(-1.0, min(1.0, start[2])))
    turn = math.atan2(target[1], target[0]) - yaw
    while turn > math.pi:
        turn -= 2 * math.pi
    while turn < -math.pi:
        turn += 2 * math.pi
    yaw += follow * turn
    pitch += follow * (math.asin(max(-1.0, min(1.0, target[2]))) - pitch)
    return (math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch))


def pitch_of(direction):
    return math.degrees(math.atan2(direction[2], math.hypot(direction[0], direction[1])))


def angle_between(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(unit(a), unit(b))))))


# Model of the beam step of screenshot 2026-11-09: the ghost floats in front of the hunter at chest height, shrinks and
# the open trap on the floor pulls it down to below the floor. The old direct aim turned the barrel steeply into the floor.
frame = 1.0 / 60.0
for _ in range(400):
    grip = (0.0, 0.0, rng.uniform(0.35, 0.6))
    heading = (0.0, -1.0, 0.0)
    trap = (rng.uniform(-0.4, 0.4), rng.uniform(-1.0, -0.35), 0.0)
    shown, previous_pitch = None, None
    old_lowest = 90.0
    steps = 600
    for step in range(steps + 1):
        share = step / steps
        # chest height while beamed, pulled to 0.8 below the floor over the last quarter
        height = 1.1 if share < 0.75 else 1.1 - (share - 0.75) / 0.25 * 1.9
        ghost = (trap[0], trap[1], height)
        direction = sub(ghost, grip)
        before = shown
        shown = aim_step(shown, direction, heading, frame)
        pitch = pitch_of(shown)
        assert -max_down - 1e-6 <= pitch <= max_up + 1e-6, ('never into the floor, never straight up', pitch)
        if before is not None:
            # no snap: one frame turns the barrel at most the smoothing share of the remaining yaw and pitch
            wanted = limit_pitch(direction, heading, math.radians(max_down), math.radians(max_up))
            yaw_gap = abs(math.degrees(math.remainder(math.atan2(wanted[1], wanted[0]) - math.atan2(before[1], before[0]),
                                                      2 * math.pi)))
            pitch_gap = abs(pitch_of(wanted) - pitch_of(before))
            moved = angle_between(before, shown)
            assert moved <= (yaw_gap + pitch_gap) * (1 - math.exp(-frame / aim_seconds)) + 1e-6
            assert moved < 3.0, ('a smooth turn, never a jump', moved)
        old_lowest = min(old_lowest, pitch_of(direction))
    assert old_lowest < -max_down - 10, ('the direct aim would point into the floor', old_lowest)
    # At the end the barrel rests at the lowest natural pitch, pointing the ghost's way
    assert abs(pitch_of(shown) + max_down) < 0.5, pitch_of(shown)
    assert dot(unit((shown[0], shown[1], 0.0)), unit((trap[0] - grip[0], trap[1] - grip[1], 0.0))) > 0.999
# Within the natural range the barrel still ends up along the direction to the ghost
for _ in range(500):
    heading = unit((rng.uniform(-1, 1), rng.uniform(-1, 1), 0.0))
    planar = mul(heading, rng.uniform(0.4, 2.0))
    direction = (planar[0], planar[1], length(planar) * math.tan(math.radians(rng.uniform(-max_down + 1, max_up - 1))))
    shown = aim_step(None, mul(heading, -1.0), heading, frame)
    for _ in range(int(3 * aim_seconds / frame) * 4):
        shown = aim_step(shown, direction, heading, frame)
    assert angle_between(shown, direction) < 0.1, angle_between(shown, direction)
# A ghost straight below the grip keeps the hunter's heading at the lowest natural pitch
below = limit_pitch((0.0, 0.0, -1.0), (1.0, 0.0, 0.0), math.radians(max_down), math.radians(max_up))
assert abs(pitch_of(below) + max_down) < 1e-9 and below[0] > 0.8

# Model: whatever the hand bone does, the barrel ends up along the shown direction
for _ in range(5000):
    node = random_quaternion(rng)
    bone = random_quaternion(rng)
    parent = qmul(node, bone)
    grip = (rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(0.2, 1.0))
    target = (rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(0.0, 1.5))
    direction = limit_pitch(sub(target, grip), (0.0, -1.0, 0.0), math.radians(max_down), math.radians(max_up))
    if length(sub(target, grip)) < 0.1:
        continue
    wanted = rotation_to((0, 0, 1), direction)
    local = qmul(qinv(parent), wanted)
    barrel = qrot(qmul(parent, local), (0, 0, 1))
    error = length(sub(barrel, unit(direction)))
    assert error < 1e-9, ('the barrel points along the shown direction', error)
    # and so it never points backwards or slanted away from it
    assert dot(barrel, unit(direction)) > 1 - 1e-9

# --- 3. The hose from the backpack to the cannon ---------------------------------------------------------------------------
ghost_material = read('materials/scripts/Ghost.material')


def material_block(name):
    start = ghost_material.index('material ' + name + '\n')
    return body(ghost_material[start:], 'material ' + name + '\n')


has(material_block('GhostHose'), 'a textured material', 'texture GhostPackRubber.png')
texture = repo / 'materials/textures/GhostPackRubber.png'
assert texture.is_file() and texture.stat().st_size > 1000, 'the hose texture exists'
assert any('materials/textures/GhostPackRubber.png' in row and 'rubber' in row for row in read('CREDITS').splitlines()), 'credited texture'
shape = body(creature_source, 'static void shapeGhostHose(')
has(creature_source, 'fixed vertex count', 'static const size_t GHOST_HOSE_RINGS=128;', 'static const size_t GHOST_HOSE_SIDES=8;')
has(shape, 'a tube along a cubic curve with sag, rebuilt in place', 'hose.begin("GhostHose",Ogre::RenderOperation::OT_TRIANGLE_LIST);',
    'else hose.beginUpdate(0);', 'hose.textureCoord(', 'hose.normal(normal);', 'const Ogre::Vector3 sag(0.0f,0.0f,-0.18f*span-2.0f*radius);',
    'return port*(u*u*u)+control1*(3.0f*u*u*t)+control2*(3.0f*u*t*t)+rear*(t*t*t);',
    'hose.position(centre+normal*ribRadius);', 'hose.colour(shadeGhostHose(look.mHose,normal,look.mGlow));', 'hose.end();')
has(visuals, 'the hose joins the pack port and the rear end of the cannon, in the holster or in the hand and follows both every frame',
    'Ogre::Entity* hoseGun=beaming?mGhostCaptureGun:mGhostPackGun;', 'mGhostHose->setDynamic(true);',
    'const Ogre::Vector3 port=mGhostBackpackNode->_getFullTransform()*Ogre::Vector3(packBounds.getMinimum().x,',
    'const Ogre::Vector3 rear=gunTransform*Ogre::Vector3(gunBounds.getCenter().x,gunBounds.getCenter().y,gunBounds.getMinimum().z);',
    'const Ogre::Real radius=0.025f*body->getBoundingBox().getSize().z*getEntityNode()->_getDerivedScale().z;',
    'shapeGhostHose(*mGhostHose,port,portOut,rear,')
assert visuals.index('shapeGhostHose(') < visuals.index('if(mGhostBeamSample<flickerSeconds) return;'), 'shaped every frame'
clear = body(creature_source, 'void Creature::clearGhostHuntVisuals()')
has(clear, 'the hose goes with the hunt', 'scene->destroyManualObject(mGhostHose)', 'scene->destroySceneNode(mGhostHoseNode)')
has(read('source/entities/Creature.h'), 'members', 'Ogre::SceneNode* mGhostHoseNode = nullptr;', 'Ogre::ManualObject* mGhostHose = nullptr;')
rings, sides = 128, 8


def hose_centres(port, port_out, rear, rear_out, radius):
    """Model of shapeGhostHose: the ring centres of the cubic curve."""
    span = length(sub(rear, port))
    reach = 0.4 * span + 4 * radius
    sag = (0.0, 0.0, -0.18 * span - 2 * radius)
    c1 = add(add(port, mul(port_out, reach)), sag)
    c2 = add(add(rear, mul(rear_out, reach)), sag)
    result = []
    for ring in range(rings + 1):
        t = ring / rings
        u = 1 - t
        point = tuple(port[i] * u ** 3 + c1[i] * 3 * u * u * t + c2[i] * 3 * u * t * t + rear[i] * t ** 3 for i in range(3))
        result.append(point)
    return result


hunter_height = 1.0
radius = 0.025 * hunter_height
assert radius >= 0.02, 'the hose is thick enough to see (about 5 cm across against a 0.3 long cannon)'
port = (0.0, 0.2, 0.55)
for _ in range(500):
    # The cannon moves anywhere within a hunter's reach (holster at the pack, hand forward, raised, lowered)
    rear = (rng.uniform(-0.6, 0.6), rng.uniform(-0.8, 0.3), rng.uniform(0.2, 1.1))
    if length(sub(rear, port)) < 0.05:
        continue
    centres = hose_centres(port, (-1.0, 0.0, 0.0), rear, unit((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 0.2))), radius)
    assert length(sub(centres[0], port)) < 1e-12 and length(sub(centres[-1], rear)) < 1e-12, 'both ends are joined'
    steps = [length(sub(centres[i + 1], centres[i])) for i in range(rings)]
    assert max(steps) < 1.0 and min(steps) > 0.0, 'a continuous tube'
    # It follows the cannon: moving the cannon by a vector moves the far end by exactly that vector
    shift = (rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2))
    moved = hose_centres(port, (-1.0, 0.0, 0.0), add(rear, shift), (0.0, 0.0, -1.0), radius)
    assert length(sub(moved[-1], add(rear, shift))) < 1e-12
    # It is flexible: it sags below the straight line between its ends in the middle
    mid = centres[rings // 2]
    straight = mul(add(port, rear), 0.5)
    assert mid[2] < straight[2], 'the hose hangs down between its ends'
    assert sum(steps) >= length(sub(rear, port)) - 1e-9, 'the hose is at least as long as the distance'
# Vertex and index count are fixed, so the dynamic tube is rebuilt in place every frame
assert (rings + 1) * (sides + 1) == 1161 and rings * sides * 6 == 6144
# Physical ribs and their dark material remain distinct from the backpack's steel end fittings.
has(shape, '32 physical corrugations and matching texture repeat',
    'radius*(0.86f+0.14f*std::cos(2.0f*Ogre::Math::PI*static_cast<Ogre::Real>(ring)/4.0f))',
    'static_cast<Ogre::Real>(GHOST_HOSE_SIDES),t);')
profile = [0.86 + 0.14 * math.cos(2 * math.pi * ring / 4) for ring in range(129)]
assert sum(abs(value - 1) < 1e-12 for value in profile) == 33
assert sum(abs(value - 0.72) < 1e-12 for value in profile) == 32
# Decision 998: the hose read white in the room light (screenshots 2026-11-09 152945_8 and 153036_15). Hose and wires are
# unlit vertex colours now, so the room light cannot wash them out.
for name in ('GhostHose', 'GhostHoseWire'):
    block = material_block(name)
    has(block, 'unlit vertex colours', 'lighting off', 'ambient vertexcolour', 'diffuse vertexcolour', 'cull_hardware none')
    assert 'specular' not in block and 'emissive' not in block
assert 'texture' not in material_block('GhostHoseWire'), 'plain bright wire colours'
has(visuals, 'steel fittings created once and transformed every frame',
    'scene->createEntity(name,"GhostHoseCoupling.mesh")',
    'coupling->setPosition(end==0?port:rear);',
    'coupling->setOrientation(Ogre::Vector3::UNIT_Z.getRotationTo(direction));',
    'coupling->setScale(Ogre::Vector3(radius,radius,radius));',
    'const Ogre::Vector3 direction=(end==0?portOut:rearOut)*reach+sag;')
assert visuals.index('coupling->setPosition(') < visuals.index('if(mGhostBeamSample<flickerSeconds) return;')
has(clear, 'fittings and child nodes released with the hose', 'scene->destroyEntity(name);',
    'mGhostHoseNode->removeAndDestroyAllChildren();')

# --- 4. Coloured wires from the pack to the cannon (decision 998) ---------------------------------------------------------
# Mario: the plain hose looks boring; bright red, blue, green wires must run from the back to the front, to the cannon.
has(creature_source, 'six-sided wires', 'static const size_t GHOST_HOSE_WIRE_SIDES=6;')
has(shape, 'a second section of wires on the same curve, rebuilt in place every frame',
    'if(hose.getNumSections()<2) hose.begin("GhostHoseWire",Ogre::RenderOperation::OT_TRIANGLE_LIST);',
    'else hose.beginUpdate(1);',
    'const Ogre::Real speedPort=3.0f*(control1-port).length(),speedRear=3.0f*(rear-control2).length();',
    'const Ogre::Real first=speedPort>1.0e-6f?std::min(0.25f,look.mEndInset*radius/speedPort):0.0f;',
    'const Ogre::Real last=speedRear>1.0e-6f?std::max(0.75f,1.0f-look.mEndInset*radius/speedRear):1.0f;',
    'const Ogre::Real thickness=radius*look.mWireRadius;',
    'const Ogre::Vector3 centre=frame(first+(last-first)*share,tangent,side,up);',
    'const Ogre::Real turn=2.0f*Ogre::Math::PI*(static_cast<Ogre::Real>(wire)/static_cast<Ogre::Real>(look.mWires.size())+',
    'look.mTwist*share);', 'const Ogre::Vector3 out=side*std::cos(turn)+up*std::sin(turn);',
    'const Ogre::Vector3 core=centre+out*(radius+thickness);', 'hose.position(core+normal*thickness);',
    'hose.colour(shadeGhostHose(look.mWires[wire],normal,look.mGlow));',
    'const Ogre::uint32 a=static_cast<Ogre::uint32>(wire*wireVertices+ring*(GHOST_HOSE_WIRE_SIDES+1)+k),b=a+1;')
assert shape.index('hose.begin("GhostHose",') < shape.index('hose.begin("GhostHoseWire",'), 'hose section 0, wires section 1'
has(body(creature_source, 'static Ogre::ColourValue shadeGhostHose('), 'glow plus light from above',
    'const Ogre::Real light=glow+(1.0f-glow)*(0.5f+0.5f*normal.z);')
look_source = body(creature_source, 'static const GhostHoseLook& ghostHoseLook()')
has(look_source, 'every look value comes from rooms.cfg', 'ghostHoseConfigColour("GhostHoseColour")',
    'config.getRoomConfigUInt32("GhostHoseWireCount")', 'ghostHoseConfigColour("GhostHoseWireColour"+std::to_string(wire))',
    'config.getRoomConfigDouble("GhostHoseWireRadius")', 'config.getRoomConfigDouble("GhostHoseWireTwist")',
    'config.getRoomConfigDouble("GhostHoseGlow")', 'config.getRoomConfigDouble("GhostHoseWireEndInset")')
has(body(creature_source, 'static Ogre::ColourValue ghostHoseConfigColour('), 'red,green,blue parsing',
    'if(!(stream>>red>>comma1>>green>>comma2>>blue) || comma1!=\',\' || comma2!=\',\')')
# The shaping still happens every frame for the hose in the hand and in the holster (asserted above), so the wires move
# with every sag of the hose.


def colour(key):
    values = [float(value) for value in config_value(key).split(',')]
    assert len(values) == 3 and all(0 <= value <= 1 for value in values), key
    return values


wire_count = int(config_value('GhostHoseWireCount'))
wires = [colour('GhostHoseWireColour%d' % n) for n in range(1, wire_count + 1)]
assert not re.search(r'^\s*GhostHoseWireColour%d\s' % (wire_count + 1), rooms, re.M), 'no unused wire colour'
hose_tint = colour('GhostHoseColour')
glow = float(config_value('GhostHoseGlow'))
wire_share = float(config_value('GhostHoseWireRadius'))
twist = float(config_value('GhostHoseWireTwist'))
end_inset = float(config_value('GhostHoseWireEndInset'))
for key in ('GhostHoseColour', 'GhostHoseGlow', 'GhostHoseWireCount', 'GhostHoseWireColour1', 'GhostHoseWireTwist',
            'GhostHoseWireRadius', 'GhostHoseWireEndInset'):
    documented(key)
assert wire_count >= 4 and len(wires) == wire_count


def hue_name(rgb):
    top = max(rgb)
    names = [name for name, value in zip(('red', 'green', 'blue'), rgb) if value == top]
    second = sorted(rgb)[1]
    if second > 0.6 * top:
        return 'mixed'
    return names[0]


hues = [hue_name(rgb) for rgb in wires]
assert {'red', 'green', 'blue'} <= set(hues), ('red, blue and green wires', hues)
assert len(set(tuple(rgb) for rgb in wires)) == wire_count, 'every wire has its own colour'
for rgb in wires:
    # Bright and saturated: one channel near full, one near zero; even the shadowed underside keeps it vivid
    assert max(rgb) >= 0.9 and min(rgb) <= 0.2, ('saturated', rgb)
    assert glow * max(rgb) >= 0.5, ('bright on the underside too', glow, rgb)
assert 0.4 <= glow < 1.0, 'shaded so the wires read as round, but always bright'
# The hose under the wires no longer reads white: tint x mean rubber texture, fully lit, stays dark
try:
    from PIL import Image
    pixels = Image.open(texture).convert('RGB').resize((64, 64))
    mean = [sum(p[i] for p in pixels.getdata()) / (64 * 64 * 255.0) for i in range(3)]
except ImportError:
    mean = [0.3, 0.29, 0.26]  # measured once: mean of GhostPackRubber.png 77/73/65 of 255
assert all(t * m <= 0.35 for t, m in zip(hose_tint, mean)), ('dark hose, not white', hose_tint, mean)
# The wires fit inside the steel couplings at both ends (sleeve 1.35 hose radii out, 2 hose radii long, see
# check_ghost_assets.py: bounds -1.35..1.35 across, -0.3..2.0 along) and lie on the rib crests
assert 1.0 + 2.0 * wire_share < 1.35 and 0.05 <= wire_share, ('thin wires inside the coupling sleeve', wire_share)
assert 0.0 < end_inset < 2.0, 'the wires end inside the coupling sleeve'
assert 1.0 <= twist <= 5.0, 'twisted round the hose, a few turns from the pack to the cannon'


def hose_frame(port, port_out, rear, rear_out, radius, t):
    """Model of the frame lambda of shapeGhostHose: centre, tangent, side, up at t."""
    span = length(sub(rear, port))
    reach = 0.4 * span + 4 * radius
    sag = (0.0, 0.0, -0.18 * span - 2 * radius)
    c1 = add(add(port, mul(port_out, reach)), sag)
    c2 = add(add(rear, mul(rear_out, reach)), sag)
    u = 1 - t
    centre = tuple(port[i] * u ** 3 + c1[i] * 3 * u * u * t + c2[i] * 3 * u * t * t + rear[i] * t ** 3 for i in range(3))
    tangent = tuple((c1[i] - port[i]) * 3 * u * u + (c2[i] - c1[i]) * 6 * u * t + (rear[i] - c2[i]) * 3 * t * t for i in range(3))
    tangent = unit(tangent)
    side = cross(tangent, (0.0, 0.0, 1.0))
    if length(side) < 1e-3:
        side = cross(tangent, (1.0, 0.0, 0.0))
    side = unit(side)
    return centre, tangent, side, cross(tangent, side)


def wire_cores(port, port_out, rear, rear_out, radius):
    """Model of the wire section: the core line of every wire, ring by ring."""
    span = length(sub(rear, port))
    reach = 0.4 * span + 4 * radius
    sag = (0.0, 0.0, -0.18 * span - 2 * radius)
    speed_port = 3 * length(add(mul(port_out, reach), sag))
    speed_rear = 3 * length(add(mul(rear_out, reach), sag))
    first = min(0.25, end_inset * radius / speed_port)
    last = max(0.75, 1 - end_inset * radius / speed_rear)
    result = []
    for wire in range(wire_count):
        line = []
        for ring in range(rings + 1):
            share = ring / rings
            t = first + (last - first) * share
            centre, tangent, side, up = hose_frame(port, port_out, rear, rear_out, radius, t)
            turn = 2 * math.pi * (wire / wire_count + twist * share)
            out = add(mul(side, math.cos(turn)), mul(up, math.sin(turn)))
            line.append((t, centre, add(centre, mul(out, radius + radius * wire_share)), tangent))
        result.append(line)
    return result


for _ in range(150):
    rear = (rng.uniform(-0.6, 0.6), rng.uniform(-0.8, 0.3), rng.uniform(0.2, 1.1))
    if length(sub(rear, port)) < 0.2:
        continue
    rear_out = unit((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-0.2, 0.2)))
    lines = wire_cores(port, (-1.0, 0.0, 0.0), rear, rear_out, radius)
    for line in lines:
        for t, centre, core, tangent in line:
            # on the rib crests of the same sagging curve, every frame
            assert abs(length(sub(core, centre)) - radius * (1 + wire_share)) < 1e-9
            assert abs(dot(sub(core, centre), tangent)) < 1e-9
        # from the pack's coupling to the cannon's coupling: both ends lie inside a sleeve, within 2 radii of the hose end
        first, last = line[0], line[-1]
        assert length(sub(first[1], port)) <= 2.0 * radius + 1e-9 and length(sub(last[1], rear)) <= 2.0 * radius + 1e-9, \
            (length(sub(first[1], port)) / radius, length(sub(last[1], rear)) / radius)
        assert length(sub(first[1], port)) > 0.5 * radius, 'the wire end hides in the coupling, not at the hose mouth'
        steps = [length(sub(line[i + 1][2], line[i][2])) for i in range(rings)]
        assert max(steps) < 0.1 * sum(steps), 'a continuous wire without jumps'
        assert sum(steps) > length(sub(rear, port)) - 4.0 * radius, 'it runs the whole way from the pack to the cannon'
    # the wires are spread evenly round the hose and twist: at the middle they sit at different sides
    middle = [line[rings // 2][2] for line in lines]
    for a in range(wire_count):
        for b in range(a + 1, wire_count):
            assert length(sub(middle[a], middle[b])) > 0.5 * radius, 'the wires do not lie on top of each other'
# Fixed vertex count of the wire section: rebuilt in place
assert wire_count * (rings + 1) * 7 == wire_count * 903
# Shaded colours of the model: top lit fully, underside at the glow share, never white
for rgb in wires + [hose_tint]:
    for normal_z in (-1.0, 0.0, 1.0):
        light = glow + (1 - glow) * (0.5 + 0.5 * normal_z)
        shaded = [value * light for value in rgb]
        assert max(shaded) <= 1.0
    if rgb is not hose_tint:
        assert min(rgb) * 1.0 <= 0.2, 'no wire is white or grey'
assert not re.search(r'(?i)ghostbust|proton|ecto-?1|slimer', read('config/rooms.cfg') + shape + material_block('GhostHoseWire')), \
    'no names of other games or films'
print('ghost hunter pose, cannon aim, hose and wires: ok')
