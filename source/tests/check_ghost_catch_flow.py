"""Check without compiling the ghost catch flow of GHOSTS-PLAN D17-D22 after owner decision 697 (build 40).

The owner saw the capture boxes float in the air instead of lying in the hunter's hand, and dark flat panels at the
ghost room wall. This check pins the fixed flow in the game source and reads the shipped hook meshes:
- the carried box hangs on a hand bone of the hunter (or a node that moves with the hunter), never on a free scene node
  placed at a fixed height in front of the body;
- within beam range the hunter first throws the box under the ghost (GhostBoxThrowSeconds), then the beam pulls the
  ghost into the lying box (GhostBeamTurns), the box snaps shut, the hunter walks to it and takes it into his hand;
- a thrown or lying box lands on the floor (z 0) under the ghost and a dropped box (D21) stays where it lay;
- the bell makes alarm lamps blink without any wall panel;
- no ghost room wall object carries a dark flat panel at its back.
Each part fails on the code and meshes of build 40 (base 831bcf98d)."""
from pathlib import Path
import re
import struct

repo = Path(__file__).resolve().parents[2]


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")


# Return a complete brace-delimited body that starts at the signature.
def body(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


# Assert that every fragment occurs in the text, naming the step it pins.
def has(text, step, *fragments):
    for fragment in fragments:
        assert fragment in text, (step, fragment)


# Assert that the fragments occur in the given order.
def ordered(text, step, *fragments):
    position = -1
    for fragment in fragments:
        found = text.find(fragment, position + 1)
        assert found > position, (step, fragment)
        position = found


# The carried box follows the hunter's hand; nothing places it at a fixed point in front of the body.
def box_in_hand():
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    has(update, "held box is created for the hand", '"_HeldGhostBox","GhostBox.mesh"')
    has(update, "held box hangs on a hand bone", "attachObjectToBone(bone,mGhostHeldBox,")
    has(update, "creatures without hand bones hold it on a node that moves with them",
        "getEntityNode()->createChildSceneNode(", "attachObject(mGhostHeldBox)")
    has(update, "the held box is shown exactly while carried", "mGhostHeldBox->setVisible(mGhostBoxMode==2);")
    # Build 40 placed the carried box on the scene root at getPosition()+getWalkDirection()*0.35+(0,0,0.65).
    assert "getWalkDirection()" not in update, "carried box must not be placed from the walk direction"
    assert "_HeldGhostBoxNode" not in update, "the held box must not hang on a free scene root node"
    root = re.findall(r'getRootSceneNode\(\)->createChildSceneNode\(getName\(\)\+"(\w+)"\)', update)
    assert "_ThrownGhostBoxNode" in root and not any("Held" in node for node in root), root
    has(update, "a thrown or lying box rests on the floor under the ghost",
        "const Ogre::Vector3 floor(ghost->getPosition().x,ghost->getPosition().y,0.0f);", "position=hand+(floor-hand)*progress;")
    hand = body(creature, "static std::string ghostBoxHandBone(")
    has(hand, "the free weapon hand is preferred", '"Weapon_L"', '"Weapon_R"', '"LeftHand"', '"RightHand"')
    clear = body(creature, "void Creature::clearGhostHuntVisuals()")
    has(clear, "the held box leaves the hand bone before it is destroyed", "detachObjectFromBone(mGhostHeldBox)",
        "scene->destroyEntity(mGhostHeldBox);mGhostHeldBox=nullptr;")
    header = read("source/entities/Creature.h")
    has(header, "held box members", "Ogre::Entity* mGhostHeldBox = nullptr;", "Ogre::SceneNode* mGhostHandNode = nullptr;")
    print("box held in the hunter's hand: ok")


# Visual box phase of the hunt header, evaluated for every state with and without backpack.
def visual_states():
    header = read("source/creatureaction/CreatureActionHuntGhost.h")
    line = re.search(r"uint32_t getBoxVisualState\(\) const \{ return (.*?); \}", header).group(1)
    expression = line.replace("!hasBackpack()", "not backpack").replace("||", " or ")
    expression = re.sub(r"([^?:]+)\?([^:]+):", r"(\2) if (\1) else ", expression)
    expression = expression.replace("u", "")
    for state in range(10):
        for backpack in (False, True):
            mode = eval(expression, {}, {"mState": state, "backpack": backpack})  # noqa: S307 - own source
            expected = 0 if not backpack else 1 if state == 2 else 3 if state in (3, 9) else 2
            assert mode == expected, (state, backpack, mode, expected)
    throw = re.search(r"std::string getThrowGhostName\(\) const \{ return (.*?); \}", header).group(1)
    has(throw, "the lying box stays under its ghost while thrown, pulled and shut", "mState==2", "mState==3", "mState==9")
    print("box phases (hand, throw, lying under the ghost): ok")


# Throw first, then beam, then snap, then walk to the box and take it into the hand.
def catch_order():
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    hunt = body(action, "bool CreatureActionHuntGhost::handleHunt()")
    approach = body(hunt, "    if(mState==1)")
    start = approach[approach.index("<=range)"):]
    has(start, "within range the throw starts", "EntityAnimation::throw_anim", "ghost->setState(GhostState::beamed);mState=2;mBeamTarget.clear();")
    assert "beam_anim" not in start.split("return true;")[0], "the beam must not start before the box is thrown"
    capture = body(hunt, "    if(mState==2 || mState==3)")
    ordered(capture, "throw, then beam, then snap",
        'config.getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond',
        "mState=3;mBeamTarget=mTarget;", "EntityAnimation::beam_anim",
        'researched("GhostBeamTurns","CatchTime")/efficiency', "ghost->setState(GhostState::boxed);",
        '"Rooms/GhostRoom/BoxSnap"', "mState=9;")
    assert "mTarget.clear();mState=4;" not in capture, "after the snap the hunter first fetches the box"
    fetch = body(hunt, "    if(mState==9)")
    ordered(fetch, "walk to the shut box, then carry it", "moveTo(there)", "mCreature.isMoving()", "mState=4;")
    has(action, "saves accept the fetch state", "mState>9")
    interrupt = body(action, "void CreatureActionHuntGhost::interrupt()")
    ordered(interrupt, "a dropped box stays where it lay under the ghost (D21)",
        "Ogre::Vector3 dropPosition=mLastPosition;", "mState==2 || mState==3 || mState==9", "dropPosition=lying->getPosition();",
        "releaseTarget();", "box->setPosition(dropPosition);")
    restore = body(action, "void CreatureActionHuntGhost::restore()")
    has(restore, "a loaded hunt resumes the same pose", "mState==3?EntityAnimation::beam_anim:EntityAnimation::throw_anim")
    creature = read("source/entities/Creature.cpp")
    refresh = body(creature, "void Creature::refreshGhostHuntVisuals()")
    has(refresh, "the pulled-in share reaches the client", "hunt->getCaptureTurns()", "(boxMode==1 || boxMode==3) && turns!=mGhostThrowTurns")
    print("catch order throw -> beam -> snap -> fetch -> carry: ok")


# The bell rings and the alarm lamps beside it blink for GhostBellSeconds without a panel behind them.
def alarm_lamps():
    room = read("source/rooms/RoomGhostRoom.cpp")
    ring = body(room, "void RoomGhostRoom::ringBell()")
    has(ring, "bell rings for GhostBellSeconds", '"Rooms/GhostRoom/Bell"', 'getRoomConfigDouble("GhostBellSeconds")',
        "for(BuildingObject* object : mWallObjects) object->setGhostRoomState(-1.0,mAlarmTurns);")
    building = read("source/entities/BuildingObject.cpp")
    update = body(building, "void BuildingObject::update(Ogre::Real seconds)")
    has(update, "lamps blink beside the bell", 'getMeshName()!="GhostBell"', "createBillboardSet(", "mGhostLampNode->setVisible(flash);")
    assert "GhostWallGauges" not in building, "no lamp may depend on the removed gauge panel"
    print("bell and blinking alarm lamps: ok")


# Read the shared vertex positions and the index buffers (start, count, wide, material) of a binary OGRE mesh.
def mesh(name):
    data = (repo / "models" / (name + ".mesh")).read_bytes()
    end = data.index(b"\n", 2)
    kind, length = struct.unpack_from("<HI", data, end + 1)
    assert kind == 0x3000, name
    positions, submeshes, cursor = None, [], end + 1 + 7
    while cursor < end + 1 + length:
        kind, size = struct.unpack_from("<HI", data, cursor)
        if kind == 0x4000:
            stop = data.index(b"\n", cursor + 6)
            shared, count, wide = struct.unpack_from("<BIB", data, stop + 1)
            assert shared == 1, name
            submeshes.append(struct.unpack_from(("<%dI" if wide else "<%dH") % count, data, stop + 7))
        elif kind == 0x5000:
            vertices = struct.unpack_from("<I", data, cursor + 6)[0]
            inner, elements, buffers = cursor + 10, [], {}
            while inner < cursor + size:
                child, child_size = struct.unpack_from("<HI", data, inner)
                if child == 0x5100:
                    element = inner + 6
                    while element < inner + child_size:
                        _, element_size = struct.unpack_from("<HI", data, element)
                        elements.append(struct.unpack_from("<5H", data, element + 6))
                        element += element_size
                elif child == 0x5200:
                    binding, stride = struct.unpack_from("<HH", data, inner + 6)
                    buffers[binding] = (stride, inner + 16)
                inner += child_size
            source, _, _, offset, _ = next(element for element in elements if element[2] == 1)
            stride, begin = buffers[source]
            positions = [struct.unpack_from("<3f", data, begin + index * stride + offset) for index in range(vertices)]
        cursor += size
    return positions, submeshes


# Area of visible flat faces that face the wall or the room (normal along y) in the rear 0.07 of the object.
def rear_panel_area(name):
    positions, submeshes = mesh(name)
    rear = min(position[1] for position in positions)
    area = 0.0
    for indices in submeshes:
        for first in range(0, len(indices), 3):
            a, b, c = (positions[index] for index in indices[first:first + 3])
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            length = sum(value * value for value in normal) ** 0.5
            if length > 0.0 and abs(normal[1]) / length > 0.95 and max(a[1], b[1], c[1]) < rear + 0.07:
                area += length / 2.0
    return area


# Only bell, hooks and the three apparatuses stand at the wall, and none of them carries a dark flat panel.
def no_flat_panels():
    room = read("source/rooms/RoomGhostRoom.cpp")
    assert "GhostWallGauges" not in room, "the gauge panels must not come back to the wall"
    spot = body(room, "BuildingObject* RoomGhostRoom::notifyActiveSpotCreated(")
    has(spot, "wall items are the bell and the hooks", 'mDecorationTiles.empty()?"GhostBell":"GhostHook"')
    wall = body(room, "void RoomGhostRoom::updateActiveSpots(")
    has(wall, "one wall item per backpack plus the bell", "const size_t slots=static_cast<size_t>(getBackpackCount())+1;")
    meshes = set(re.findall(r'"(Ghost\w+|ManaStill|SoulForge)"', room))
    created = {name for name in meshes if (repo / "models" / (name + ".mesh")).exists()}
    assert created <= {"GhostCauldron", "GhostBell", "GhostHook", "GhostHookEmpty", "GhostRack", "GhostPress", "ManaStill", "SoulForge"}, created
    # Build 40: every hook (3 per cauldron) showed a 0.4 x 0.8 dark iron backing board (0.29 and 0.59 square units here).
    for name in ("GhostHook", "GhostHookEmpty", "GhostBell"):
        area = rear_panel_area(name)
        assert area < 0.06, (name, "dark flat panel at the wall", round(area, 4))
    print("no dark flat panels at the ghost room wall: ok")


def main():
    box_in_hand()
    visual_states()
    catch_order()
    alarm_lamps()
    no_flat_panels()
    print("ghost catch flow: ok")


if __name__ == "__main__":
    main()
