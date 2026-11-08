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
Fixed values measured once on this branch: 4 setAnimationState calls with a direction in the hunt, 16 rings and 8 sides.
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

# --- 2. The cannon points at the ghost for the whole beam step ----------------------------------------------------------
creature_source = read('source/entities/Creature.cpp')
aim = body(creature_source, 'static void aimGhostCannon(')
has(aim, 'the barrel (+z) is turned to the aim point through the mount',
    'const Ogre::Vector3 origin=cannon._getParentNodeFullTransform()*Ogre::Vector3::ZERO;',
    'const Ogre::Quaternion wanted=Ogre::Vector3::UNIT_Z.getRotationTo(direction.normalisedCopy());',
    'body.getParentNode()->_getDerivedOrientation()*body.getSkeleton()->getBone(bone)->_getDerivedOrientation();',
    'grip->setOrientation(parent.Inverse()*wanted);',
    'handNode->setOrientation(handNode->getParentSceneNode()->_getDerivedOrientation().Inverse()*wanted);')
visuals = body(creature_source, 'void Creature::updateGhostHuntVisuals(double seconds)')
has(visuals, 'aimed every frame while the beam is on, with the grip kept',
    'if(beaming) aimGhostCannon(*body,*mGhostCaptureGun,mGhostCaptureGrip,mGhostGunHandNode,',
    'ghostCannonHandBone(body->hasSkeleton()?body->getSkeleton():nullptr),ghostBeamAimPoint(scene,*target));',
    'mGhostCaptureGrip=grip;')
# Before every early return of the beam drawing (the flicker pause), so it holds for every frame of the step
assert visuals.index('if(beaming) aimGhostCannon(') < visuals.index('if(mGhostBeamSample<flickerSeconds) return;')
assert visuals.index('if(beaming) aimGhostCannon(') < visuals.index('const Ogre::Vector3 start=ghostCannonTip(*mGhostCaptureGun);')
has(read('source/entities/Creature.h'), 'the mount is kept', 'Ogre::TagPoint* mGhostCaptureGrip = nullptr;')
assert 'mGhostCaptureGrip=nullptr;' in body(creature_source, 'void Creature::clearGhostHuntVisuals()')

# Model: whatever the hand bone does, the barrel ends up along the direction to the ghost
for _ in range(5000):
    node = random_quaternion(rng)
    bone = random_quaternion(rng)
    parent = qmul(node, bone)
    grip = (rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(0.2, 1.0))
    target = (rng.uniform(-3, 3), rng.uniform(-3, 3), rng.uniform(0.0, 1.5))
    direction = sub(target, grip)
    if length(direction) < 0.1 or dot(unit(direction), (0, 0, -1)) > 0.999999 or dot(unit(direction), (0, 0, 1)) < -0.999999:
        continue
    wanted = rotation_to((0, 0, 1), direction)
    local = qmul(qinv(parent), wanted)
    barrel = qrot(qmul(parent, local), (0, 0, 1))
    error = length(sub(barrel, unit(direction)))
    assert error < 1e-9, ('the barrel points at the ghost', error)
    # and so it never points backwards or slanted away from it
    assert dot(barrel, unit(direction)) > 1 - 1e-9

# --- 3. The hose from the backpack to the cannon ---------------------------------------------------------------------------
has(read('materials/scripts/Ghost.material'), 'a textured material', 'material GhostHose', 'texture GhostPackRubber.png')
texture = repo / 'materials/textures/GhostPackRubber.png'
assert texture.is_file() and texture.stat().st_size > 1000, 'the hose texture exists'
assert any('materials/textures/GhostPackRubber.png' in row and 'rubber' in row for row in read('CREDITS').splitlines()), 'credited texture'
shape = body(creature_source, 'static void shapeGhostHose(')
has(creature_source, 'fixed vertex count', 'static const size_t GHOST_HOSE_RINGS=16;', 'static const size_t GHOST_HOSE_SIDES=8;')
has(shape, 'a tube along a cubic curve with sag, rebuilt in place', 'hose.begin("GhostHose",Ogre::RenderOperation::OT_TRIANGLE_LIST);',
    'else hose.beginUpdate(0);', 'hose.textureCoord(', 'hose.normal(normal);', 'const Ogre::Vector3 sag(0.0f,0.0f,-0.18f*span-2.0f*radius);',
    'hose.position(centre+normal*radius);', 'hose.end();')
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
rings, sides = 16, 8


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
assert (rings + 1) * (sides + 1) == 153 and rings * sides * 6 == 768
print('ghost hunter pose, cannon aim and hose: ok')
