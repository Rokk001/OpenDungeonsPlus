"""Check without compiling the ghost catch flow of GHOSTS-PLAN D17-D22 after owner decision 697 (build 40).

The owner saw the capture boxes float in the air instead of lying in the hunter's hand, and dark flat panels at the
ghost room wall. This check pins the fixed flow in the game source and reads the shipped hook meshes:
- the carried box hangs on a hand bone of the hunter (or a node that moves with the hunter), never on a free scene node
  placed at a fixed height in front of the body;
- within beam range the hunter first throws the box under the ghost (GhostBoxThrowSeconds), then the beam pulls the
  ghost into the lying box (GhostBeamSeconds), the box snaps shut (GhostBoxSnapSeconds), the hunter walks to it and
  takes it into his hand;
- a thrown or lying box lands on the floor (z 0) under the ghost and a dropped box (D21) stays where it lay;
- the bell makes alarm lamps blink without any wall panel;
- no ghost room wall object carries a dark flat panel at its back.
Each part fails on the code and meshes of build 40 (base 831bcf98d).
Owner decision 711 (build 41) saw the held and thrown box as a large black untextured block. The box must be the small
trap of D17: hand-sized (no larger than the tavern mug, at most a fifth of the smallest hunter), its main surface a bright
texture with visible grain, opaque green glowing windows on front and back, and the hand and the throw keep that size.
This part fails on the GhostBox mesh, textures and code of build 41 (base 94b29d74a).
Owner decision 726 wants the whole catch to take about 20 s so the player can follow it: 2 s throw, 16 s beam and 2 s
snap, the same for every hunter; efficiency and the CatchTime research only act on emptying the box (GhostEmptyTurns).
Each visual step stays visible for its full time. This part fails on the code and config of base e877bfe66 (0.5 s
throw, 5.5 beam turns divided by efficiency and research, no snap step)."""
from pathlib import Path
import re
import struct
import zlib

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
    for state in range(11):
        for backpack in (False, True):
            mode = eval(expression, {}, {"mState": state, "backpack": backpack})  # noqa: S307 - own source
            expected = 0 if not backpack else 1 if state == 2 else 3 if state in (3, 9) else 4 if state == 10 else 2
            assert mode == expected, (state, backpack, mode, expected)
    throw = re.search(r"std::string getThrowGhostName\(\) const \{ return (.*?); \}", header).group(1)
    has(throw, "the lying box stays under its ghost while thrown, pulled, snapping and shut", "mState==2", "mState==3",
        "mState==10", "mState==9")
    print("box phases (hand, throw, lying under the ghost, snapping shut): ok")


# Throw first, then beam, then snap, then walk to the box and take it into the hand.
def catch_order():
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    hunt = body(action, "bool CreatureActionHuntGhost::handleHunt()")
    approach = body(hunt, "    if(mState==1)")
    start = approach[approach.index("<=range)"):]
    has(start, "within range the throw starts", "EntityAnimation::throw_anim", "ghost->setState(GhostState::beamed);mState=2;mBeamTarget.clear();")
    assert "beam_anim" not in start.split("return true;")[0], "the beam must not start before the box is thrown"
    capture = body(hunt, "    if(mState==2 || mState==3 || mState==10)")
    ordered(capture, "throw, then beam, then snap with the bang, then caught",
        'config.getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond',
        "mState=3;mBeamTarget=mTarget;", "EntityAnimation::beam_anim",
        'config.getRoomConfigDouble("GhostBeamSeconds")*ODApplication::turnsPerSecond', "mBeamTarget.clear();mState=10;",
        '"Rooms/GhostRoom/BoxSnap"', 'config.getRoomConfigDouble("GhostBoxSnapSeconds")*ODApplication::turnsPerSecond',
        "ghost->setState(GhostState::boxed);", "mState=9;")
    assert "mTarget.clear();mState=4;" not in capture, "after the snap the hunter first fetches the box"
    fetch = body(hunt, "    if(mState==9)")
    ordered(fetch, "walk to the shut box, then carry it", "moveTo(there)", "mCreature.isMoving()", "mState=4;")
    has(action, "saves accept the fetch and snap states", "mState>10")
    interrupt = body(action, "void CreatureActionHuntGhost::interrupt()")
    ordered(interrupt, "a dropped box stays where it lay under the ghost (D21)",
        "Ogre::Vector3 dropPosition=mLastPosition;", "mState==2 || mState==3 || mState==10 || mState==9", "dropPosition=lying->getPosition();",
        "releaseTarget();", "box->setPosition(dropPosition);")
    restore = body(action, "void CreatureActionHuntGhost::restore()")
    has(restore, "a loaded hunt resumes the same pose", "mState==3?EntityAnimation::beam_anim:EntityAnimation::throw_anim")
    creature = read("source/entities/Creature.cpp")
    refresh = body(creature, "void Creature::refreshGhostHuntVisuals()")
    has(refresh, "the pulled-in share reaches the client", "hunt->getCaptureTurns()",
        "(boxMode==1 || boxMode==3 || boxMode==4) && turns!=mGhostThrowTurns")
    print("catch order throw -> beam -> snap -> fetch -> carry: ok")


# Numeric room configuration rows by key.
def room_config():
    values = {}
    for line in read("config/rooms.cfg").splitlines():
        row = line.split("#", 1)[0].split()
        if len(row) == 2:
            try:
                values[row[0]] = float(row[1])
            except ValueError:
                pass
    return values


# Code lines of a C++ text without its // comments.
def code_only(text):
    return "\n".join(line.split("//", 1)[0] for line in text.splitlines())


# Owner decision 726: the catch takes 2 s throw + 16 s beam + 2 s snap for every hunter, each step visible to its end.
def catch_timing():
    room = room_config()
    durations = (room.get("GhostBoxThrowSeconds"), room.get("GhostBeamSeconds"), room.get("GhostBoxSnapSeconds"))
    assert durations == (2, 16, 2), ("catch durations throw, beam, snap", durations)
    assert "GhostBeamTurns" not in room, "the efficiency-scaled beam turns are replaced by GhostBeamSeconds"
    rows = read("config/rooms.cfg").splitlines()
    for key in ("GhostBoxThrowSeconds", "GhostBeamSeconds", "GhostBoxSnapSeconds"):
        index = next(i for i, row in enumerate(rows) if row.split()[:1] == [key])
        assert rows[index - 1].lstrip().startswith("#"), (key, "documentation line")
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    hunt = body(action, "bool CreatureActionHuntGhost::handleHunt()")
    capture = code_only(body(hunt, "    if(mState==2 || mState==3 || mState==10)"))
    # Base e877bfe66: researched("GhostBeamTurns","CatchTime")/efficiency made a strong hunter beam a sixth as long.
    for fragment in ("efficiency", "getEfficiency", "CatchTime", "GhostBeamTurns"):
        assert fragment not in capture, ("catch time must not depend on the hunter or research", fragment)
    capture_turns = code_only(body(action, "double CreatureActionHuntGhost::getCaptureTurns() const"))
    has(capture_turns, "the client share uses the fixed beam time", 'getRoomConfigDouble("GhostBeamSeconds")*ODApplication::turnsPerSecond')
    assert "getEfficiency" not in capture_turns and "researched(" not in capture_turns, "beam share independent of the hunter"
    empty = body(hunt, "    if(mState==6)")
    has(empty, "efficiency and research act on emptying only",
        'researched("GhostEmptyTurns","CatchTime")/mCreature.getDefinition()->getRoomAffinity(RoomType::ghostRoom).getEfficiency()')
    assert code_only(action).count('"CatchTime"') == 1, "CatchTime acts only on emptying"
    manager = read("source/game/SkillManager.cpp")
    has(manager, "CatchTime research is based on the emptying turns",
        '{SkillType::roomGhostRoom, "CatchTime", ResearchBaseSource::rooms, "GhostEmptyTurns", ""}',
        'texts[ResearchEffect::CatchTime] = "Box emptying time";')
    restore = body(action, "void CreatureActionHuntGhost::restore()")
    has(restore, "a loaded snap resumes with the beam lowered", "if(mState==10) mCreature.setAnimationState(EntityAnimation::idle_anim,")
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    has(update, "the throw arc runs the full throw time",
        'getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond', "position.z+=4.0f*progress*(1.0f-progress)*0.5f;")
    has(update, "the lying box is shown during throw, beam and snap",
        "const bool lyingBox=mGhostBoxMode==1 || mGhostBoxMode==3 || mGhostBoxMode==4;", "mGhostBoxNode->setVisible(lyingBox);")
    snap = update[update.index("else if(mGhostBoxMode==4)"):]
    snap = snap[:snap.index("            else\n")]
    has(snap, "the snap jolts the box over the full snap time with the ghost fully inside",
        'getRoomConfigDouble("GhostBoxSnapSeconds")*ODApplication::turnsPerSecond', "mGhostThrowClientTurns/duration",
        "mGhostBoxNode->setOrientation(", "mGhostCaptureShown=1.0;")
    has(update, "the beam still shrinks the ghost towards the pulled-in share",
        "mGhostCaptureShown+=(mGhostThrowTurns-mGhostCaptureShown)*std::min(1.0,seconds*6.0);")
    header = read("source/creatureaction/CreatureActionHuntGhost.h")
    has(header, "the hunt documents the snap state", "10 the lying box snaps shut over the pulled-in ghost")
    print("catch timing 2 s throw + 16 s beam + 2 s snap = 20 s for every hunter: ok")


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


# Material names of the index buffers of a binary OGRE mesh, in the order mesh() returns them.
def submesh_materials(name):
    data = (repo / "models" / (name + ".mesh")).read_bytes()
    end = data.index(b"\n", 2)
    _, length = struct.unpack_from("<HI", data, end + 1)
    names, cursor = [], end + 1 + 7
    while cursor < end + 1 + length:
        kind, size = struct.unpack_from("<HI", data, cursor)
        if kind == 0x4000:
            names.append(data[cursor + 6:data.index(b"\n", cursor + 6)].decode("ascii"))
        cursor += size
    return names


# Mean and standard deviation of the luminance (0-255) of an 8-bit grey, RGB or RGBA, non-interlaced PNG.
def png_luminance(path):
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", path
    cursor, idat, header = 8, b"", None
    while cursor < len(data):
        length, kind = struct.unpack_from(">I4s", data, cursor)
        chunk = data[cursor + 8:cursor + 8 + length]
        if kind == b"IHDR":
            header = struct.unpack(">IIBBBBB", chunk)
        elif kind == b"IDAT":
            idat += chunk
        cursor += 12 + length
    width, height, depth, colour, _, _, interlace = header
    channels = {0: 1, 2: 3, 4: 2, 6: 4}[colour]
    assert depth == 8 and interlace == 0, (path, depth, interlace)
    raw, stride = zlib.decompress(idat), width * channels
    previous, values = bytearray(stride), []
    for row in range(height):
        start = row * (stride + 1)
        kind, line = raw[start], bytearray(raw[start + 1:start + 1 + stride])
        for i in range(stride):
            left = line[i - channels] if i >= channels else 0
            up, corner = previous[i], previous[i - channels] if i >= channels else 0
            if kind == 1:
                line[i] = (line[i] + left) & 255
            elif kind == 2:
                line[i] = (line[i] + up) & 255
            elif kind == 3:
                line[i] = (line[i] + (left + up) // 2) & 255
            elif kind == 4:
                guess = left + up - corner
                pa, pb, pc = abs(guess - left), abs(guess - up), abs(guess - corner)
                line[i] = (line[i] + (left if pa <= pb and pa <= pc else up if pb <= pc else corner)) & 255
        previous = line
        for i in range(0, stride, channels * 4):
            pixel = line[i:i + channels]
            values.append(pixel[0] if channels < 3 else 0.299 * pixel[0] + 0.587 * pixel[1] + 0.114 * pixel[2])
    mean = sum(values) / len(values)
    return mean, (sum((value - mean) ** 2 for value in values) / len(values)) ** 0.5


# Bodies of all material definitions in the shipped material scripts, by material name.
def material_scripts():
    found = {}
    for script in (repo / "materials" / "scripts").glob("*.material"):
        text = script.read_text(encoding="utf-8")
        for match in re.finditer(r"^material (\w+)\b[^\n]*\n\{(.*?)^\}", text, re.M | re.S):
            found[match.group(1)] = match.group(2)
    return found


# Owner decision 711: the held and thrown box is the small, textured trap of D17 that fits the hunter's hand.
def small_textured_box():
    positions, submeshes = mesh("GhostBox")
    materials = submesh_materials("GhostBox")
    size = [max(p[i] for p in positions) - min(p[i] for p in positions) for i in range(3)]
    mug_positions, _ = mesh("TavernMug")
    mug = max(max(p[i] for p in mug_positions) - min(p[i] for p in mug_positions) for i in range(3))
    dwarf_positions, _ = mesh("RunelordDwarf")
    hunter = max(p[2] for p in dwarf_positions) - min(p[2] for p in dwarf_positions)
    # Build 41: 0.25 x 0.25 x 0.20, larger than the mug (0.18) and more than a quarter of the dwarf hunter (0.74).
    assert max(size) <= mug and max(size) <= 0.2 * hunter, ("box larger than a hand", [round(s, 3) for s in size], mug, hunter)
    assert min(size) >= 0.06, ("box too small to read", [round(s, 3) for s in size])
    assert abs(min(p[2] for p in positions)) < 1e-4, "the box origin stays on its floor so it lies on the ground"
    scripts = material_scripts()
    areas = {}
    glow_front = glow_back = 0.0
    front, back = max(p[1] for p in positions), min(p[1] for p in positions)
    for material, indices in zip(materials, submeshes):
        assert material in scripts, ("box material without a definition", material)
        glow = "scene_blend" not in scripts[material] and re.search(r"emissive\s+[\d.]+\s+(0\.[89]\d*|1(\.0*)?)\s", scripts[material])
        for first in range(0, len(indices), 3):
            a, b, c = (positions[index] for index in indices[first:first + 3])
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            area = sum(value * value for value in normal) ** 0.5 / 2.0
            areas[material] = areas.get(material, 0.0) + area
            if glow and min(a[1], b[1], c[1]) > front - 0.2 * size[1]:
                glow_front += area
            if glow and max(a[1], b[1], c[1]) < back + 0.2 * size[1]:
                glow_back += area
    # Build 41: GhostIron covered the box; its baked texture is a nearly flat dark grey (luminance 52, deviation 3.4).
    main = max(areas, key=areas.get)
    texture = re.search(r"^\s*texture\s+(\S+\.png)", scripts[main], re.M)
    assert texture, ("main box surface without texture", main)
    mean, deviation = png_luminance(repo / "materials" / "textures" / texture.group(1))
    assert mean >= 90 and deviation >= 10, ("main box surface is dark or flat", main, round(mean, 1), round(deviation, 1))
    assert len(set(materials)) >= 3, ("box needs case, fittings and glow", materials)
    # Build 41: one translucent slit on the front only, no opaque glow on the back.
    assert glow_front > 0.0 and glow_back > 0.0, ("opaque green glowing windows front and back", glow_front, glow_back)
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    has(update, "the held box middle sits in the palm",
        "mGhostHeldBox->getMesh()->getBounds().getSize().z", "Ogre::Vector3(0.0f,-0.5f*boxHeight,0.0f)")
    has(update, "a scaled rig bone does not blow the held box up", "palm->setInheritScale(false);")
    has(update, "the thrown and lying box keeps the hand size", "mGhostBoxNode->setScale(getEntityNode()->getScale());")
    assert not re.search(r"mGhostHeldBox->getParentNode\(\)->setScale|palm->setScale", update), "the held box must not be rescaled"
    print("small textured ghost box in the hand: ok")


def main():
    box_in_hand()
    visual_states()
    catch_order()
    catch_timing()
    alarm_lamps()
    no_flat_panels()
    small_textured_box()
    print("ghost catch flow: ok")


if __name__ == "__main__":
    main()
