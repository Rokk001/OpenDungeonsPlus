"""Owner decision 936 points 2 and 3: visible pick-up of the trap from the floor and hand placement onto the seat.

Compiles nothing. Point 2: after the catch the hunter walks to GhostPickUpReach (0.3) in front of the shut trap, turns
to it flat on the floor and holds still for GhostPickUpSeconds (2 s, box mode 7); the client lays a generated pose over
his Idle clip (Creature.cpp buildGhostPose, cumulative blend): a 70 degree bow at the waist towards the trap, knees bent
by 50 degrees with the hips lowered so that the feet keep their place, the head looking at the trap and both arms
stretched to it. The trap lies on the floor until the hands are down at it, comes off the floor into the hand and ends
exactly at the trap in the hand (mode 2), so nothing jumps. Point 3: at the cauldron he turns to the seat with his Idle
clip (no more one-second Empty clip); over GhostPutInSeconds (2 s) a reach pose (15 degree bow, the arm with the trap
stretched to the seat) is laid over it and the trap leaves his hand on one eased curve over a point just above the
seat down onto it (bottom of the trap on the seat). These parts fail on ceef28852 (no mode 7, the trap jumps into the
hand, the Empty clip and a linear one-second put-in from the moving hand). A previously dropped lying box (GhostBoxEntity,
state 8, an interrupted hunt) is picked up with the same walk, turn and bend instead of vanishing at once (fails on
5391b3dce); its own mesh is hidden while the hunter's trap shows the lift from where it lay. A save taken while he
bends down keeps the pick-up record (walked, bending) next to its clock mTurns, so a loaded hunter only runs the
remaining time and the client starts the lift at the server's share; saves without the record repeat the pick-up.
"""
from pathlib import Path
import math
import random
import re

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


def ordered(text, rule, *fragments):
    position = -1
    for fragment in fragments:
        found = text.find(fragment, position + 1)
        assert found > position, (rule, fragment)
        position = found


# --- quaternions (w, x, y, z) -----------------------------------------------------------------------------------------
def qmul(a, b):
    return (a[0] * b[0] - a[1] * b[1] - a[2] * b[2] - a[3] * b[3],
            a[0] * b[1] + a[1] * b[0] + a[2] * b[3] - a[3] * b[2],
            a[0] * b[2] - a[1] * b[3] + a[2] * b[0] + a[3] * b[1],
            a[0] * b[3] + a[1] * b[2] - a[2] * b[1] + a[3] * b[0])


def qinv(q):
    return (q[0], -q[1], -q[2], -q[3])


def axis_angle(axis, degrees):
    n = math.sqrt(sum(c * c for c in axis))
    half = math.radians(degrees) / 2
    return (math.cos(half),) + tuple(math.sin(half) * c / n for c in axis)


def rot(q, v):
    return qmul(qmul(q, (0.0,) + tuple(v)), qinv(q))[1:]


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def scale(a, s):
    return tuple(x * s for x in a)


def unit(a):
    n = math.sqrt(sum(c * c for c in a))
    return tuple(c / n for c in a)


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def rotation_to(a, b):
    a, b = unit(a), unit(b)
    c = cross(a, b)
    d = dot(a, b)
    if d < -0.999999:
        return axis_angle((1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0), 180.0)
    s = math.sqrt((1 + d) * 2)
    return (s / 2,) + tuple(x / s for x in c)


# --- 1. The server: walk in front of the trap, turn to it, hold for the pick-up time -------------------------------------
rooms = read('config/rooms.cfg')
values = dict(re.findall(r'^(Ghost\w+)\s+([-\d.]+)\s*$', rooms, re.M))
assert values['GhostPickUpSeconds'] == '2' and values['GhostPickUpReach'] == '0.3' and values['GhostPutInSeconds'] == '2'
action = read('source/creatureaction/CreatureActionHuntGhost.cpp')
header = read('source/creatureaction/CreatureActionHuntGhost.h')
hunt = body(action, 'bool CreatureActionHuntGhost::handleHunt()')
step = body(action, 'bool CreatureActionHuntGhost::pickUpStep(const Ogre::Vector3* point)')
ordered(step, 'walk in front, turn flat to the trap, hold for the pick-up time',
        'if(!mPickUpWalked)', 'mPickUpWalked=true;', 'if(point!=nullptr && walkInFrontOf(*point)) return false;',
        'if(mCreature.isMoving()) mCreature.clearDestinations(EntityAnimation::idle_anim,true,true);',
        'if(mCreature.isMoving()) return false;',
        'EntityAnimation::idle_anim,true,point==nullptr?Ogre::Vector3::ZERO:facing(mCreature,*point),false',
        'mPickingUp=true;mTurns=0.0;mLastTimedTurn=map.getTurnNumber();', 'mCreature.refreshGhostHuntVisuals();return false;',
        'if(mLastTimedTurn!=map.getTurnNumber()) { mTurns+=1.0;mLastTimedTurn=map.getTurnNumber(); }',
        'return mTurns>=getPickUpTurns();')
has(body(action, 'void CreatureActionHuntGhost::endPickUp()'), 'then he carries it on to the next target',
    'mTarget.clear();mDestination=nullptr;mState=4;mTurns=0.0;mPickingUp=false;mPickUpWalked=false;',
    'mCreature.refreshGhostHuntVisuals();')
state9 = hunt[hunt.index('    if(mState==9)'):hunt.index('    if(mState==8)')]
ordered(state9, 'state 9: the trap under the caught ghost', 'GhostEntity* boxed=ghostNamed(map,mTarget);',
        'const Ogre::Vector3 point=boxed==nullptr?Ogre::Vector3::ZERO:boxed->getPosition();',
        'if(!pickUpStep(boxed==nullptr?nullptr:&point)) return false;', 'endPickUp();return true;')
# State 8: a previously dropped lying box is picked up visibly too; it stays on the map until the lift is over, then the
# hunter takes over its ghosts (fails on 5391b3dce, where takeGhostNames ran on the first turn of state 8)
state8 = hunt[hunt.index('    if(mState==8)'):hunt.index('    if(mState==4)')]
ordered(state8, 'state 8: the dropped box, same pick-up, contents only at its end',
        'GhostBoxEntity* box=static_cast<GhostBoxEntity*>(map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mTarget));',
        'if(box==nullptr) { endPickUp();return true; }', 'const Ogre::Vector3 point=box->getPosition();',
        'if(!pickUpStep(&point)) return false;',
        'mGhosts=box->takeGhostNames();box->removeFromGameMap();box->deleteYourself();',
        'mReviveGhosts.push_back(name);', 'endPickUp();return true;')
state1 = hunt[hunt.index('    if(mState==1)'):hunt.index('    if(mState==2 || mState==3 || mState==10)')]
has(state1, 'state 1 hands the dropped box over on its tile, also while still walking',
    'if(box!=nullptr && own==there) { mState=8;mTurns=0.0;mPickingUp=false;mPickUpWalked=false;return true; }')
assert 'own==there && !mCreature.isMoving()) { mState=8' not in state1, 'no stop on the middle of the box tile first'
has(body(action, 'uint32_t CreatureActionHuntGhost::getBoxVisualState() const'), 'mode 7 while bending, also over a dropped box',
    'if((mState==9 || mState==8) && mPickingUp) return 7u;', 'if(mState==9) return 6u;')
has(body(action, 'std::string CreatureActionHuntGhost::getThrowGhostName() const'), 'the dropped box is named while lifted',
    'if(mState==8 && mPickingUp) return mTarget;')
has(header, 'members and declarations', 'bool mPickUpWalked = false;', 'bool mPickingUp = false;',
    'static double getPickUpTurns();', 'bool walkInFrontOf(const Ogre::Vector3& point);',
    'bool pickUpStep(const Ogre::Vector3* point);', 'void endPickUp();')
# Save and load of an in-progress pick-up: the record follows the saved walk, old saves without it still load
export = body(action, 'void CreatureActionHuntGhost::exportToStream(std::ostream& stream) const')
ordered(export, 'the pick-up record is saved at the end of the runtime block',
        "for(const Ogre::Vector2& point : mCreature.getWalkQueue()) stream << ' ' << point.x << ' ' << point.y;",
        'stream << " pickup " << mPickUpWalked << \' \' << mPickingUp;', 'stream << " [/GhostHuntRuntime]";')
load = body(action, 'bool CreatureActionHuntGhost::importFromStream(std::istream& stream)')
ordered(load, 'the record is optional and checked',
        'mLoadedPath.push_back(point); }', 'if(!(stream>>close)) return false;',
        'if(close=="pickup" && !(stream>>mPickUpWalked>>mPickingUp>>close)) return false;',
        'if(close!="[/GhostHuntRuntime]") return false;')
assert 'if(!(stream>>close) || close!="[/GhostHuntRuntime]") return false;' not in load
restore = body(action, 'void CreatureActionHuntGhost::restore()')
ordered(restore, 'a loaded hunter bending down goes on from the saved clock, facing the box',
        'if(mState==9 || mState==8)', 'if(mPickingUp)', 'mPickUpWalked=true;mLastTimedTurn=mCreature.getGameMap()->getTurnNumber();',
        'mCreature.getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mTarget);',
        'facing(mCreature,item->getPosition())', 'else if(mLoadedPath.empty()) mPickUpWalked=false;',
        'else { mPickingUp=false;mPickUpWalked=false; }', 'mCreature.refreshGhostHuntVisuals();')
assert 'mTurns=0.0' not in restore, 'the saved pick-up clock is kept'


# Model of the record: the runtime block parsed like importFromStream, with and without the pick-up record
def parse_runtime(tokens):
    tokens = list(tokens)
    walked = bending = False
    close = tokens.pop(0)
    if close == 'pickup':
        walked, bending, close = tokens.pop(0) == '1', tokens.pop(0) == '1', tokens.pop(0)
    assert close == '[/GhostHuntRuntime]', 'malformed record'
    return walked, bending


assert parse_runtime(['[/GhostHuntRuntime]']) == (False, False), 'an old save repeats the pick-up'
assert parse_runtime(['pickup', '1', '1', '[/GhostHuntRuntime]']) == (True, True)
for broken in (['pickup', '1', '[/GhostHuntRuntime]'], ['1', '[/GhostHuntRuntime]']):
    try:
        parse_runtime(broken)
    except (AssertionError, IndexError):
        pass
    else:
        raise AssertionError(('a broken record must not load', broken))
walk = body(action, 'bool CreatureActionHuntGhost::walkInFrontOf(const Ogre::Vector3& point)')
has(walk, 'the last step of the usual tile path ends in front of the trap', 'mCreature.getGameMap()->path(&mCreature,tile);',
    'const Ogre::Vector2 stand=target-approach*reach;', 'path.back()=stand;',
    'mCreature.setWalkPath(EntityAnimation::walk_anim,EntityAnimation::idle_anim,true,true,path,true);')


# Model of walkInFrontOf: the stand lies on the line from the last waypoint to the trap, GhostPickUpReach before it
def stand_for(previous, trap, reach=0.3):
    direction = unit((trap[0] - previous[0], trap[1] - previous[1], 0.0))
    return (trap[0] - direction[0] * reach, trap[1] - direction[1] * reach)


for previous, trap in [((4, 5), (5.1, 5.0)), ((5, 4), (5.0, 5.2)), ((4, 4), (5.0, 5.0))]:
    stand = stand_for(previous, trap)
    assert abs(math.hypot(stand[0] - trap[0], stand[1] - trap[1]) - 0.3) < 1e-9
    assert round(stand[0]) in (previous[0], round(trap[0])) and round(stand[1]) in (previous[1], round(trap[1])), \
        'the stand lies on a tile of the route'

# --- 2. The client pose: one generated clip per hunter, from his live pose, eased by its weight -------------------------
creature = read('source/entities/Creature.cpp')
build = body(creature, 'static Ogre::AnimationState* buildGhostPose(')
ordered(build, 'built from the live pose without the layer, as mesh-space turns',
        'body.getAllAnimationStates()->removeAnimationState(name);', 'shared.removeAnimation(name);',
        'live.setAnimationState(*body.getAllAnimationStates());', 'live._updateTransforms();',
        'const Ogre::Vector3 target=body.getParentNode()->_getFullTransform().inverse()*point;',
        'const Ogre::Vector3 axis=Ogre::Vector3::UNIT_Z.crossProduct(forward).normalisedCopy();',
        'const Ogre::Quaternion bow(Ogre::Degree(pickUp?70.0f:15.0f),axis);',
        'const Ogre::Quaternion thigh(Ogre::Degree(-50.0f),axis),shin(Ogre::Degree(100.0f),axis),foot(Ogre::Degree(-50.0f),axis);',
        'rise+=bentKnee+(thigh*shin)*(ankle-knee)-ankle;', 'if(hips!=nullptr) shift=rise*-0.5f;',
        'const Ogre::Vector3 bowedShoulder=pivot+shift+bow*(shoulder-pivot);',
        'const Ogre::Quaternion upper=upperNow.getRotationTo(bow.Inverse()*aim);',
        'turns[arm.lower]=lowerNow.getRotationTo((bow*upper).Inverse()*aim);',
        'const Ogre::Quaternion local=basis.Inverse()*turn.second*basis;',
        '(hips->getParent()->_getDerivedOrientation().Inverse()*shift)/hips->getParent()->_getDerivedScale();',
        'createAnimationState(name,0.0f,1.0f,0.0f,false);')
assert 'if(!pickUp && (holdingBone.empty()' in build, 'the put-in stretches only the arm that holds the trap'
visuals = body(creature, 'void Creature::updateGhostHuntVisuals(double seconds)')
ordered(visuals, 'built at the start of its phase, laid over Idle with the cumulative blend, weighted every frame',
        'stopGhostPose();', 'mGhostPoseBlend=static_cast<int>(body->getSkeleton()->getBlendMode());',
        'mGhostPose=buildGhostPose(*body,mGhostPoseName,poseTarget,poseMode==7,',
        'body->getSkeleton()->setBlendMode(Ogre::ANIMBLEND_CUMULATIVE);',
        'Ogre::AnimationState* pose=body->getAnimationState(mGhostPoseName);',
        'pose->setEnabled(true);pose->setTimePosition(0.0f);pose->setWeight(poseWeight);')
has(visuals, 'rebuilt if the hunter turned after it was built',
    '!getEntityNode()->_getDerivedOrientation().equals(mGhostPoseFacing,Ogre::Radian(Ogre::Degree(1.0f)))')
stop = body(creature, 'void Creature::stopGhostPose()')
has(stop, 'the layer goes and the blend mode comes back', 'removeAnimationState(mGhostPoseName);',
    'body->getSkeleton()->setBlendMode(static_cast<Ogre::SkeletonAnimationBlendMode>(mGhostPoseBlend));',
    'shared.removeAnimation(mGhostPoseName);')
assert body(creature, 'void Creature::clearGhostHuntVisuals()').index('stopGhostPose();') > 0
has(read('source/entities/Creature.h'), 'members', 'Ogre::AnimationState* mGhostPose = nullptr;', 'void stopGhostPose();',
    'double mGhostPoseClock = -1.0;', 'double mGhostFlowClock = 0.0;', 'std::string mGhostHiddenBox;',
    'Ogre::Vector3 mGhostPickFloor = Ogre::Vector3::ZERO;')

# Model of the clip keys: a local key B^-1 d B on a bone whose live pose is B turns the bone (and so its subtree) by d in
# mesh space, whatever the axes of the bone; nested keys compose as the product of their mesh-space turns.
rng = random.Random(936)
for _ in range(200):
    parent = unit(tuple(rng.uniform(-1, 1) for _ in range(4)))
    local = unit(tuple(rng.uniform(-1, 1) for _ in range(4)))
    child = qmul(parent, local)
    d_parent = axis_angle(tuple(rng.uniform(-1, 1) for _ in range(3)), rng.uniform(-90, 90))
    d_child = axis_angle(tuple(rng.uniform(-1, 1) for _ in range(3)), rng.uniform(-90, 90))
    key_parent = qmul(qmul(qinv(parent), d_parent), parent)
    key_child = qmul(qmul(qinv(child), d_child), child)
    parent_after = qmul(parent, key_parent)
    child_after = qmul(qmul(parent_after, local), key_child)
    want = qmul(qmul(d_parent, d_child), child)
    assert min(sum((a - b) ** 2 for a, b in zip(child_after, want)), sum((a + b) ** 2 for a, b in zip(child_after, want))) < 1e-18

# Model of the bend on a standing figure 1.0 high, facing -y, the trap 0.3 in front of his feet on the floor
hip_l, hip_r = (-0.1, 0.0, 0.5), (0.1, 0.0, 0.5)
knee_l, knee_r = (-0.1, 0.0, 0.27), (0.1, 0.0, 0.27)
ankle_l, ankle_r = (-0.1, 0.0, 0.05), (0.1, 0.0, 0.05)
pivot = (0.0, 0.0, 0.52)
shoulders = [(-0.18, 0.0, 0.82), (0.18, 0.0, 0.82)]
elbows = [(-0.2, 0.0, 0.62), (0.2, 0.0, 0.62)]
hands = [(-0.21, 0.0, 0.44), (0.21, 0.0, 0.44)]
trap = (0.0, -0.3, 0.06)
forward = unit((trap[0] - pivot[0], trap[1] - pivot[1], 0.0))
axis = unit(cross((0.0, 0.0, 1.0), forward))
bow, thigh, shin = axis_angle(axis, 70), axis_angle(axis, -50), axis_angle(axis, 100)
assert rot(axis_angle(axis, 70), (0.0, 0.0, 1.0))[1] < -0.8, 'a positive turn tips the upper body towards the trap'
rise = (0.0, 0.0, 0.0)
for hip, knee, ankle in ((hip_l, knee_l, ankle_l), (hip_r, knee_r, ankle_r)):
    bent_knee = add(hip, rot(thigh, sub(knee, hip)))
    rise = add(rise, sub(add(bent_knee, rot(qmul(thigh, shin), sub(ankle, knee))), ankle))
shift = scale(rise, -0.5)
assert shift[2] < -0.05, ('the hips go down', shift)
for hip, knee, ankle in ((hip_l, knee_l, ankle_l), (hip_r, knee_r, ankle_r)):
    bent_knee = add(add(hip, shift), rot(thigh, sub(knee, hip)))
    foot = add(bent_knee, rot(qmul(thigh, shin), sub(ankle, knee)))
    assert math.dist(foot, ankle) < 1e-9, ('the feet keep their place on the floor', foot, ankle)
    assert bent_knee[1] < hip[1] - 0.05, 'the knees go forward'
lowest = 1.0
for shoulder, elbow, hand in zip(shoulders, elbows, hands):
    bowed_shoulder = add(add(pivot, shift), rot(bow, sub(shoulder, pivot)))
    aim = unit(sub(trap, bowed_shoulder))
    upper = rotation_to(sub(elbow, shoulder), rot(qinv(bow), aim))
    lower = rotation_to(sub(hand, elbow), rot(qinv(qmul(bow, upper)), aim))
    new_elbow = add(bowed_shoulder, rot(qmul(bow, upper), sub(elbow, shoulder)))
    new_hand = add(new_elbow, rot(qmul(qmul(bow, upper), lower), sub(hand, elbow)))
    assert dot(unit(sub(new_hand, bowed_shoulder)), aim) > 0.9999, 'the arm points straight at the trap'
    lowest = min(lowest, new_hand[2])
    assert math.dist(new_hand, trap) < 0.2, ('the hands come down to the trap', new_hand)
assert lowest < 0.13, ('he really bends down: hands near the floor', lowest)

# --- 3. The trap: off the floor into the hand, from the hand onto the seat, no jump --------------------------------------
pick = visuals[visuals.index('else if(mGhostBoxMode==7)'):visuals.index('else if(mGhostBoxMode==6)')]
has(pick, 'the pick-up of the trap', 'const double lifted=pickUp>0.0?std::min(1.0,mGhostPoseClock/pickUp):1.0;',
    'const float grip=static_cast<float>(ghostEase(0.38,0.52,lifted));', 'position=floor+(heldOrigin-floor)*grip;',
    'boxTurn=Ogre::Quaternion::Slerp(grip,Ogre::Quaternion::IDENTITY,heldTurn,true);',
    'poseMode=7;poseWeight=ghostPoseWeight(lifted,0.4,0.6);')
ordered(visuals, 'the pick-up clock starts at the server share, then runs every frame', 'if(mGhostBoxMode==7)',
        'if(mGhostPoseClock<0.0) mGhostPoseClock=mGhostThrowTurns*ConfigManager::getSingleton().getRoomConfigDouble("GhostPickUpSeconds");',
        'else mGhostPoseClock+=seconds*getGameMap()->getGameSpeedFactor();', 'else mGhostPoseClock=-1.0;')
refresh = body(creature, 'void Creature::refreshGhostHuntVisuals()')
has(refresh, 'the pick-up share is sent', 'else if(boxMode==7)', 'const double pickUp=CreatureActionHuntGhost::getPickUpTurns();',
    'turns=pickUp>0.0?std::min(1.0,turns/pickUp):1.0;', 'boxMode==5 || boxMode==7) && turns!=mGhostThrowTurns')
# The dropped box on the client: hidden while lifted, the lift starts where it lay, shown again if the lift ends
# without it (interrupted); the ghost-only calls are skipped for it
ordered(visuals, 'the dropped box is lifted in place of its own mesh',
        'if(mGhostBoxMode==7 && ghost==nullptr)',
        'GameEntity* dropped=getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mGhostThrowTarget);',
        'mGhostPickFloor=dropped->getPosition();', 'dropped->getEntityNode()->setVisible(false);',
        'droppedBox=!mGhostHiddenBox.empty();',
        'else if(!mGhostHiddenBox.empty()) { showGhostBoxEntity(*getGameMap(),mGhostHiddenBox,true);mGhostHiddenBox.clear(); }',
        'if(mGhostBoxMode==7 && ghost==nullptr && !droppedBox) mGhostBoxNode->setVisible(false);',
        'if((ghost!=nullptr || droppedBox) && lyingBox)',
        'const Ogre::Vector3 floor=ghost==nullptr?mGhostPickFloor:',
        'if(ghost!=nullptr)', 'ghost->setCaptureProgress(mGhostCaptureShown);')
has(body(creature, 'static void showGhostBoxEntity('), 'shown again by name if it still exists',
    'GameEntity* box=map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,name);',
    'if(box!=nullptr && box->getEntityNode()!=nullptr) box->getEntityNode()->setVisible(shown);')
has(body(creature, 'void Creature::clearGhostHuntVisuals()'), 'a hunt that ends shows the box again',
    'showGhostBoxEntity(*getGameMap(),mGhostHiddenBox,true);mGhostHiddenBox.clear();')
has(visuals, 'the trap in the hand this frame',
    'const Ogre::Vector3 heldOrigin=mGhostHeldBox->_getParentNodeFullTransform()*Ogre::Vector3::ZERO;',
    'mGhostHeldBox->setVisible(mGhostBoxMode==2);', 'if(mGhostBoxMode!=4) mGhostBoxNode->setOrientation(boxTurn);')
has(body(creature, 'static double ghostEase('), 'smoother step', 'return x*x*x*(x*(x*6.0-15.0)+10.0);')
has(body(creature, 'static Ogre::Real ghostPoseWeight('), 'eased in, held, eased out',
    'return static_cast<Ogre::Real>(ghostEase(0.0,in,p)*(1.0-ghostEase(out,1.0,p)));')


def smoother(a, b, t):
    x = max(0.0, min(1.0, (t - a) / (b - a)))
    return x * x * x * (x * (x * 6 - 15) + 10)


def weight(p, rise_end, fall_start):
    return smoother(0.0, rise_end, p) * (1.0 - smoother(fall_start, 1.0, p))


for rise_end, fall_start in ((0.4, 0.6), (0.35, 0.6)):
    assert weight(0.0, rise_end, fall_start) == 0.0 and weight(1.0, rise_end, fall_start) == 0.0, 'from Idle back to Idle'
    assert weight((rise_end + fall_start) / 2, rise_end, fall_start) == 1.0, 'the full pose is held'
    samples = [weight(i / 1000, rise_end, fall_start) for i in range(1001)]
    assert max(abs(samples[i + 1] - samples[i]) for i in range(1000)) < 0.01, 'no jump of the pose'
# The trap is gripped only while the pose is full (the hands are down at it)
assert smoother(0.38, 0.52, 0.38) == 0.0 and smoother(0.38, 0.52, 0.52) == 1.0
assert weight(0.38, 0.4, 0.6) > 0.98 and weight(0.52, 0.4, 0.6) == 1.0
floor_spot, hand_spot = (0.0, -0.3, 0.0), (0.02, -0.28, 0.15)
path = [add(floor_spot, scale(sub(hand_spot, floor_spot), smoother(0.38, 0.52, i / 1000))) for i in range(1001)]
assert path[0] == floor_spot and path[-1] == hand_spot, 'from the floor into the hand, where mode 2 shows it'
assert max(math.dist(path[i], path[i + 1]) for i in range(1000)) < 0.005

put = visuals[visuals.index('else if(mGhostBoxMode==5)'):visuals.index('else if(mGhostBoxMode==7)')]
ordered(put, 'the hand places the trap onto the seat',
        'const double placed=putIn>0.0?std::max(0.0,std::min(1.0,mGhostDeliveryClock/putIn)):1.0;',
        'const float release=static_cast<float>(ghostEase(0.3,0.62,placed));',
        'const Ogre::Vector3 above=seat+Ogre::Vector3(0.0f,0.0f,0.08f);',
        'position=heldOrigin*((1.0f-release)*(1.0f-release))+above*(2.0f*(1.0f-release)*release)+seat*(release*release);',
        'boxTurn=Ogre::Quaternion::Slerp(release,heldTurn,Ogre::Quaternion::IDENTITY,true);',
        'poseMode=5;poseWeight=ghostPoseWeight(placed,0.35,0.6);',
        'poseTarget=seat+Ogre::Vector3(0.0f,0.0f,0.5f*boxHeight);')
seat, held = (0.5, 1.32, 1.1), (0.52, 1.75, 0.9)
above = add(seat, (0.0, 0.0, 0.08))
curve = []
for i in range(1001):
    r = smoother(0.3, 0.62, i / 1000)
    curve.append(add(add(scale(held, (1 - r) ** 2), scale(above, 2 * (1 - r) * r)), scale(seat, r * r)))
assert curve[0] == held and math.dist(curve[-1], seat) < 1e-12, 'from the hand onto the seat'
assert max(math.dist(curve[i], curve[i + 1]) for i in range(1000)) < 0.01, 'no jump on the way'
moving = [p for i, p in enumerate(curve[1:]) if math.dist(p, curve[i]) > 0.0]
last = unit(sub(seat, moving[-20]))
assert last[2] < -0.9, ('it comes down onto the seat from above', last)
# The bottom of the trap mesh is its origin, so the trap set at the seat lies on it (bounds of models/GhostBox.mesh)
import struct
mesh = (repo / 'models/GhostBox.mesh').read_bytes()
bounds = next(struct.unpack_from('<7f', mesh, i + 6) for i in range(len(mesh) - 34)
              if struct.unpack_from('<HI', mesh, i) == (0x9000, 34))
assert abs(bounds[2]) < 1e-6 and bounds[5] > 0.1, ('the trap stands on its origin', bounds)
print('ghost pick-up and hand placement (decision 936 points 2 and 3): ok')
