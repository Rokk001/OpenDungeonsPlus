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
snap, the same for every hunter; efficiency and the CatchTime research only act on emptying the box (GhostEmptyTurns;
since decision 845 the emptying is the fixed 20 s transfer at the cauldron's trap socket, see check_ghost_transfer.py).
Each visual step stays visible for its full time. This part fails on the code and config of base e877bfe66 (0.5 s
throw, 5.5 beam turns divided by efficiency and research, no snap step).
Owner decisions 855 and 857 (newer than 726): better ghost hunters are faster at catching and the CatchTime research
shortens the catch too. The beam lasts GhostBeamSeconds (16 s at research level 1 and efficiency 1) times the CatchTime
factor of the keeper divided by the hunter efficiency; throw and snap stay 2 s each for every hunter, and the 20 s
transfer is shortened only by CatchTime, never by the efficiency. The beam part fails on base b8dac69e3 (fixed 16 s).
Owner decision 733: the hunter wears the capture-beam backpack on his back (taken from and hung back on its hook), only
the small box is in the hand on the way back to the cauldron, the box is thrown under the ghost and the beam comes from
the weapon. This part fails on base 0c9e8c329 (pack in front of the hunter, beam from the backpack nozzle).
Owner decision 791 (build 45): the beam starts at the emitter tip of the visible capture cannon of the backpack, which
every hunter holds while beaming (in its holster on the pack otherwise), and the worn pack is a readable textured
ghost-hunter pack sized to each hunter. These parts replace the decision 733 weapon-origin part and fail on base
89fbc6bd7.
Owner decision 798 (build 46): the pack on the wall hook still showed the old dark untextured look; it must look like the
textured pack the hunter wears. The full hook is drawn as the bare hook with the worn pack and its holstered cannon on
it. This part fails on base 636e678c8 (GhostHook.mesh with the old GhostLeather pack drawn as it is).
Owner decision 865 (build 0.7.4.51): the capture beam must hit the ghost itself (chest or head), not the trap; the trap
lies shut until the hunter is in beam range, opens first, then the ghost is pulled in, then it shuts and stays shut while
the hunter carries it to the ghost room; at the cauldron he puts it by hand into a delivery device beside him (see
check_ghost_transfer.py). The decision 865 parts fail on base 6c97ae45c (beam end at the ghost position + 0.4 over the
trap, the shut trap waiting for pick-up drawn as phase 3 with the lid opening again, the ghost shrinking while the lid
still opens)."""
from pathlib import Path
import re
import struct
import zlib

repo = Path(__file__).resolve().parents[2]
import sys
# ODP_ASSETS_SRC (else <repo>/assets-src) holds the asset sources, see scripts/assets_src.py
sys.path.insert(0, str(repo / 'scripts'))
from assets_src import resolve  # noqa: E402


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return resolve(repo, path).read_text(encoding="utf-8")


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
        "const Ogre::Vector3 floor=ghost==nullptr?mGhostPickFloor:Ogre::Vector3(ghost->getPosition().x,ghost->getPosition().y,0.0f);",
        "position=hand+(floor-hand)*progress;")
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
    # Since decision 845 the phases live in the source file and add 5, the open trap in the cauldron's trap socket
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    phases = body(action, "uint32_t CreatureActionHuntGhost::getBoxVisualState() const")
    rules = re.findall(r"if\((.*?)\) return (\d)u;", phases)
    # Decision 865: the shut trap waiting under the caught ghost (state 9) is its own phase 6, no longer the open phase 3
    # Decision 936 point 2: while the hunter bends down and lifts the shut trap into his hand it is phase 7, also for a
    # previously dropped lying box (state 8)
    assert rules == [("!hasBackpack()", "0"), ("mState==2", "1"), ("mState==3", "3"), ("mState==10", "4"),
                     ("(mState==9 || mState==8) && mPickingUp", "7"), ("mState==9", "6"), ("isTransferring()", "5")], rules
    assert phases.rstrip("}\n ").endswith("return 2u;"), "held in the hand otherwise"
    for state in range(11):
        for backpack in (False, True):
            for transferring in ((False, True) if state == 6 else (False,)):
              for picking in ((False, True) if state in (8, 9) else (False,)):
                values = {"!hasBackpack()": not backpack, "mState==2": state == 2, "mState==3": state == 3,
                          "mState==10": state == 10, "(mState==9 || mState==8) && mPickingUp": state in (8, 9) and picking,
                          "mState==9": state == 9, "isTransferring()": transferring}
                mode = next((int(m) for condition, m in rules if values[condition]), 2)
                expected = 0 if not backpack else 1 if state == 2 else 3 if state == 3 else 4 if state == 10 else \
                    (7 if picking else 6) if state == 9 else 7 if state == 8 and picking else 5 if transferring else 2
                assert mode == expected, (state, backpack, transferring, picking, mode, expected)
    throw = body(action, "std::string CreatureActionHuntGhost::getThrowGhostName() const")
    has(throw, "the lying box stays under its ghost while thrown, pulled, snapping and shut",
        "if(mState==2 || mState==3 || mState==10 || mState==9) return mTarget;", "if(mState==8 && mPickingUp) return mTarget;",
        "if(isTransferring()) return mGhosts.front();")
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
        "const double duration=getBeamSeconds(mCreature)*ODApplication::turnsPerSecond;", "mBeamTarget.clear();mState=10;",
        '"Rooms/GhostRoom/BoxSnap"', 'config.getRoomConfigDouble("GhostBoxSnapSeconds")*ODApplication::turnsPerSecond',
        "ghost->setState(GhostState::boxed);", "mState=9;")
    assert "mTarget.clear();mState=4;" not in capture, "after the snap the hunter first fetches the box"
    fetch = body(hunt, "    if(mState==9)")
    # Decision 936 point 2: he walks in front of the shut box, turns to it, bends down and lifts it over
    # GhostPickUpSeconds, then carries it (the shared pick-up step of states 9 and 8)
    ordered(fetch, "walk in front of the shut box, bend down and pick it up, then carry it",
        "GhostEntity* boxed=ghostNamed(map,mTarget);", "if(!pickUpStep(boxed==nullptr?nullptr:&point)) return false;",
        "endPickUp();return true;")
    step = body(action, "bool CreatureActionHuntGhost::pickUpStep(const Ogre::Vector3* point)")
    ordered(step, "the pick-up step",
        "if(point!=nullptr && walkInFrontOf(*point)) return false;", "if(mCreature.isMoving()) return false;",
        "facing(mCreature,*point)", "mPickingUp=true;mTurns=0.0;",
        "if(mLastTimedTurn!=map.getTurnNumber()) { mTurns+=1.0;mLastTimedTurn=map.getTurnNumber(); }",
        "return mTurns>=getPickUpTurns();")
    has(body(action, "void CreatureActionHuntGhost::endPickUp()"), "then he carries it", "mState=4;")
    walk = body(action, "bool CreatureActionHuntGhost::walkInFrontOf(const Ogre::Vector3& point)")
    has(walk, "the last step ends GhostPickUpReach before the box",
        'getRoomConfigDouble("GhostPickUpReach")', "const Ogre::Vector2 stand=target-approach*reach;", "path.back()=stand;",
        "if(!onRoute) return mCreature.getPositionTile()!=tile && moveTo(tile) && mCreature.isMoving();")
    has(body(action, "double CreatureActionHuntGhost::getPickUpTurns()"), "pick-up time",
        'getRoomConfigDouble("GhostPickUpSeconds")*ODApplication::turnsPerSecond')
    has(body(action, "void CreatureActionHuntGhost::restore()"), "a loaded pick-up goes on, or starts again without a record",
        "if(mState==9 || mState==8)", "else if(mLoadedPath.empty()) mPickUpWalked=false;")
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
        "(boxMode==1 || boxMode==3 || boxMode==4 || boxMode==5 || boxMode==7) && turns!=mGhostThrowTurns")
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


# Owner decision 726: the catch takes 2 s throw + 16 s beam + 2 s snap, each step visible to its end; decisions 855 and
# 857: the beam (only the beam) is shortened by the CatchTime research of the keeper and by the hunter efficiency.
def catch_timing():
    room = room_config()
    durations = (room.get("GhostBoxThrowSeconds"), room.get("GhostBeamSeconds"), room.get("GhostBoxSnapSeconds"))
    assert durations == (2, 16, 2), ("catch durations throw, beam, snap", durations)
    assert "GhostBeamTurns" not in room, "the efficiency-scaled beam turns are replaced by GhostBeamSeconds"
    rows = read("config/rooms.cfg").splitlines()
    for key in ("GhostBoxThrowSeconds", "GhostBeamSeconds", "GhostBoxSnapSeconds"):
        index = next(i for i, row in enumerate(rows) if row.split()[:1] == [key])
        assert rows[index - 1].lstrip().startswith("#"), (key, "documentation line")
    beam_row = next(i for i, row in enumerate(rows) if row.split()[:1] == ["GhostBeamSeconds"])
    beam_doc = " ".join(row.lstrip("# ") for row in rows[beam_row - 4:beam_row])
    has(beam_doc, "the beam doc line explains the 16 s base and what shortens it",
        "16 s at research level 1 and hunter efficiency 1", "CatchTime research factor", "divided by the")
    catch_time = re.search(r"^\s*roomGhostRoom\s+CatchTime\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$", read("config/skills.cfg"), re.M)
    assert catch_time and [float(value) for value in catch_time.groups()] == [1.0, 0.8, 0.667], "CatchTime 1.0/0.8/0.667"
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    hunt = body(action, "bool CreatureActionHuntGhost::handleHunt()")
    capture = code_only(body(hunt, "    if(mState==2 || mState==3 || mState==10)"))
    # Throw and snap stay fixed for every hunter: nothing in the capture branch reads efficiency or research itself.
    for fragment in ("efficiency", "getEfficiency", "CatchTime", "GhostBeamTurns"):
        assert fragment not in capture, ("throw and snap must not depend on the hunter or research", fragment)
    has(capture, "throw and snap keep their configured seconds",
        'config.getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond',
        'config.getRoomConfigDouble("GhostBoxSnapSeconds")*ODApplication::turnsPerSecond')
    beam_state = capture[capture.index("if(mState==3)"):capture.index("mBeamTarget.clear();mState=10;")]
    has(beam_state, "the beam step uses the beam time of the hunter",
        "const double duration=getBeamSeconds(mCreature)*ODApplication::turnsPerSecond;")
    assert 'getRoomConfigDouble("GhostBeamSeconds")' not in beam_state, "the beam step no longer uses the fixed 16 s"
    beam = code_only(body(action, "double CreatureActionHuntGhost::getBeamSeconds(const Creature& hunter)"))
    ordered(beam, "beam = GhostBeamSeconds x CatchTime research / hunter efficiency (guarded)",
        "SkillManager::getResearchValue(hunter.getSeat(),SkillType::roomGhostRoom,",
        'getRoomConfigDouble("GhostBeamSeconds"),"CatchTime")',
        "getRoomAffinity(RoomType::ghostRoom).getEfficiency()", "efficiency>0.0?beam/efficiency:beam")
    capture_turns = code_only(body(action, "double CreatureActionHuntGhost::getCaptureTurns() const"))
    has(capture_turns, "the pulled-in share uses the same beam time", "getBeamSeconds(mCreature)*ODApplication::turnsPerSecond")
    assert "GhostBeamSeconds" not in capture_turns, "the share must not use the fixed 16 s"
    header = read("source/creatureaction/CreatureActionHuntGhost.h")
    has(header, "the beam time is shared by server and client", "static double getBeamSeconds(const Creature& hunter);")
    # Decision 845: the emptying is the 20 s transfer at the trap socket (check_ghost_transfer.py); decision 857: hunter
    # efficiency does not shorten it, only the CatchTime research of the keeper does
    empty = body(hunt, "    if(mState==6)")
    has(empty, "the transfer takes the fixed time", "const double duration=getTransferTurns();")
    transfer = code_only(body(action, "double CreatureActionHuntGhost::getTransferTurns() const"))
    assert "fficiency" not in transfer and "getBeamSeconds" not in transfer, "the transfer stays independent of the hunter"
    assert code_only(action).count('"CatchTime"') == 2, "CatchTime acts on the beam and on the transfer, nowhere else"
    assert "getEfficiency" not in code_only(hunt), "the hunt steps read the hunter efficiency only through getBeamSeconds"
    manager = read("source/game/SkillManager.cpp")
    has(manager, "CatchTime research is based on the transfer and the beam seconds",
        '{SkillType::roomGhostRoom, "CatchTime", ResearchBaseSource::rooms, "GhostTransferSeconds", "GhostBeamSeconds"}',
        'texts[ResearchEffect::CatchTime] = "Beam and transfer time";')
    restore = body(action, "void CreatureActionHuntGhost::restore()")
    has(restore, "a loaded snap resumes with the beam lowered", "if(mState==10) mCreature.setAnimationState(EntityAnimation::idle_anim,")
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    has(update, "the throw arc runs the full throw time",
        'getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond', "position.z+=4.0f*progress*(1.0f-progress)*0.5f;")
    has(update, "the lying box is shown during throw, beam and snap",
        "const bool lyingBox=mGhostBoxMode==1 || mGhostBoxMode==3 || mGhostBoxMode==4 || mGhostBoxMode==5 || mGhostBoxMode==6 || mGhostBoxMode==7;",
        "mGhostBoxNode->setVisible(lyingBox);")
    snap = update[update.index("else if(mGhostBoxMode==4)"):]
    snap = snap[:snap.index("            else\n")]
    has(snap, "the snap jolts the box over the full snap time with the ghost fully inside",
        'getRoomConfigDouble("GhostBoxSnapSeconds")*ODApplication::turnsPerSecond', "mGhostThrowClientTurns/duration",
        "mGhostBoxNode->setOrientation(", "mGhostCaptureShown=1.0;")
    has(update, "the beam still shrinks the ghost towards the pulled-in share, once the lid is open (decision 865)",
        "mGhostCaptureShown+=(pulled-mGhostCaptureShown)*std::min(1.0,seconds*6.0);")
    has(update, "the client lid uses the beam time of the hunter, as the server does",
        "const double beamed=mGhostThrowTurns*CreatureActionHuntGhost::getBeamSeconds(*this);")
    assert 'mGhostThrowTurns*config.getRoomConfigDouble("GhostBeamSeconds")' not in update, "the client must not assume 16 s"
    header = read("source/creatureaction/CreatureActionHuntGhost.h")
    has(header, "the hunt documents the snap state", "10 the lying box snaps shut over the pulled-in ghost")
    print("catch timing 2 s throw + 16 s x CatchTime / efficiency beam + 2 s snap: ok")


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


# Hunter creature blocks of creatures.cfg: creature name, right and left spawn weapon, ghost room efficiency.
def ghost_hunters():
    hunters = {}
    for block in re.findall(r"^\s*\[Creature\]\s*$(.*?)^\s*\[/Creature\]", read("config/creatures.cfg"), re.M | re.S):
        name = re.search(r"^\s*Name\s+(\S+)", block, re.M).group(1)
        ghost = re.search(r"^\s*GhostRoom\s+\S+\s+([0-9.]+)\s*$", block, re.M)
        if ghost and float(ghost.group(1)) > 0.0:
            weapons = dict(re.findall(r"^\s*WeaponSpawn([RL])\s+(\S+)", block, re.M))
            hunters[name] = (weapons.get("R", "none"), weapons.get("L", "none"))
    return hunters


# Material areas of a binary OGRE mesh and the area of each material in the given y slab (min, max), by material name.
def material_areas(name, slab=None):
    positions, submeshes = mesh(name)
    areas, inside = {}, {}
    for material, indices in zip(submesh_materials(name), submeshes):
        for first in range(0, len(indices), 3):
            a, b, c = (positions[index] for index in indices[first:first + 3])
            u = [b[i] - a[i] for i in range(3)]
            v = [c[i] - a[i] for i in range(3)]
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            area = sum(value * value for value in normal) ** 0.5 / 2.0
            areas[material] = areas.get(material, 0.0) + area
            if slab and slab[0] <= min(a[slab[2]], b[slab[2]], c[slab[2]]) and max(a[slab[2]], b[slab[2]], c[slab[2]]) <= slab[1]:
                inside[material] = inside.get(material, 0.0) + area
    return areas, inside


# Whether a material definition glows opaquely (a strong emissive term and no blending).
def glowing(script):
    return "scene_blend" not in script and re.search(r"emissive\s+[\d.]+\s+(0\.[89]\d*|1(\.0*)?)\s", script)


# Bone names stored in a binary OGRE skeleton (each bone record starts with its name and a newline).
def skeleton_bones(path):
    data = path.read_bytes()
    return set(re.findall(rb"\x00\x20.{4}([A-Za-z_.][\w.]*)\n", data, re.S))


# Owner decision 791 (build 45): the beam came out of the skeleton hunter's hands. GHOSTS-PLAN D20 and section 5 GhostBeam
# want it to start at the weapon tip of the backpack, the capture cannon: every hunter, also one without a weapon of its
# own, holds the visible cannon while beaming and the beam leaves its emitter tip; otherwise the cannon waits in its
# holster on the pack. The pack stays on the hunter's back (decision 733) and the small box is the only thing in the hand
# on the way out and back. Fails on base 89fbc6bd7: no cannon mesh, the beam started at the hunter's own weapon
# (ghostBeamOrigin) or at a backpack nozzle constant.
def beam_from_capture_cannon():
    render = read("source/render/RenderManager.cpp")
    has(render, "creatures face the negative y axis of their node", "creatures face the negative y axis of the mesh")
    orient = body(render, "void RenderManager::rrOrientEntityToward(")
    has(orient, "the facing rotation turns local -y to the walk direction",
        "Ogre::Vector3 tempVector = node->getOrientation() * Ogre::Vector3::NEGATIVE_UNIT_Y;", "node->rotate(tempVector.getRotationTo(direction));")
    # The cannon mesh: grip at the origin, barrel along +z (the weapon mount turns it along the hand bone), centred on
    # the barrel axis, and its top is the glowing emitter tip.
    positions, _ = mesh("GhostCaptureGun")
    low = [min(p[i] for p in positions) for i in range(3)]
    high = [max(p[i] for p in positions) for i in range(3)]
    size = [high[i] - low[i] for i in range(3)]
    assert abs(low[2]) < 1e-4 and size[2] > 3.0 * max(size[0], size[1]), ("cannon barrel along +z from the grip", size)
    assert abs(low[0] + high[0]) < 1e-3 and abs(low[1] + high[1]) < 1e-3, ("emitter tip on the barrel axis", low, high)
    scripts = material_scripts()
    _, top = material_areas("GhostCaptureGun", (high[2] - 0.05 * size[2], high[2] + 1.0, 2))
    assert any(glowing(scripts[name]) for name in top), ("the emitter tip glows", top)
    areas, _ = material_areas("GhostCaptureGun")
    for material in areas:
        assert material in scripts, ("cannon material without a definition", material)
    credits = read("CREDITS")
    assert any("models/GhostCaptureGun.mesh" in row and "GPL" in row for row in credits.splitlines()), "cannon credit"
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    # Every hunter holds the cannon on a hand bone: weapon hands first, then hand bones; without any, a node at the chest.
    hand = body(creature, "static std::string ghostCannonHandBone(")
    bones = ["Weapon_R", "RightHand", "Hand_R", "hand.R", "Hand.R", "R_Hand", "hand_r",
             "Weapon_L", "LeftHand", "Hand_L", "hand.L", "Hand.L", "L_Hand", "hand_l"]
    has(hand, "cannon hand bones in order", "const char* names[]={" + ",".join('"%s"' % b for b in bones[:7]) + ",\n        " +
        ",".join('"%s"' % b for b in bones[7:]) + "};")
    blocks = {re.search(r"^\s*Name\s+(\S+)", block, re.M).group(1): block
              for block in re.findall(r"^\s*\[Creature\]\s*$(.*?)^\s*\[/Creature\]", read("config/creatures.cfg"), re.M | re.S)}
    hunters = ghost_hunters()
    assert sorted(hunters) == ["Defender", "Knight", "PitDemon", "RunelordDwarf", "Skeleton", "Troll"], sorted(hunters)
    for name in hunters:
        skeleton = re.search(r"^\s*MeshName\s+(\S+)\.mesh", blocks[name], re.M).group(1) + ".skeleton"
        names = {bone.decode() for bone in skeleton_bones(repo / "models" / skeleton)}
        assert any(bone in names for bone in bones), (name, "holds the cannon in a hand", sorted(names)[:12])
    has(update, "the cannon goes into the hand with the game's weapon mount",
        '"_GhostCaptureGun","GhostCaptureGun.mesh"', "mount.FromAngleAxis(Ogre::Degree(-90.0),Ogre::Vector3::UNIT_X);",
        "body->attachObjectToBone(bone,mGhostCaptureGun,mount,Ogre::Vector3::ZERO);", "grip->setInheritScale(false);",
        "const Ogre::Real scale=0.30f*height/mGhostCaptureGun->getMesh()->getBounds().getSize().z;")
    has(update, "a hunter without hand bones holds the cannon on a node that moves with it",
        'mGhostGunHandNode=getEntityNode()->createChildSceneNode(getName()+"_GhostGunHandNode",', "mGhostGunHandNode->attachObject(mGhostCaptureGun);")
    has(update, "the cannon is in the hand exactly while the beam is on, else in its holster on the pack",
        "const bool beaming=target!=nullptr && mGhostBoxMode==3 && ghostAboveTrap(scene,*target);", "mGhostCaptureGun->setVisible(beaming);", "mGhostPackGun->setVisible(!beaming);",
        'mGhostPackGun=scene->createEntity(getName()+"_GhostPackGun","GhostCaptureGun.mesh");', "holsterNode->attachObject(mGhostPackGun);")
    has(update, "the cannon takes the place of the hunter's own weapons while beaming",
        "if(beaming) { setGhostHunterWeaponsVisible(scene,*this,false);mGhostOwnWeaponsHidden=true; }",
        "else if(mGhostOwnWeaponsHidden) { CreatureCombatReactions::showWeaponsForClip(this);mGhostOwnWeaponsHidden=false; }")
    ordered(update, "the beam and its sparks start at the cannon's emitter tip",
        "const Ogre::Vector3 end=ghostBeamAimPoint(scene,*target);",
        "const Ogre::Vector3 start=ghostCannonTip(*mGhostCaptureGun);",
        "mGhostSparkNode->setPosition(start);", "Ogre::Vector3 point=start+(end-start)*fraction;")
    tip = body(creature, "static Ogre::Vector3 ghostCannonTip(")
    has(tip, "the tip is the top of the cannon mesh in the world",
        "const Ogre::Vector3 tip(bounds.getCenter().x,bounds.getCenter().y,bounds.getMaximum().z);",
        "return cannon._getParentNodeFullTransform()*tip;")
    # Build 45 fired from the hunter's own weapon or from a fitted nozzle constant of the backpack.
    assert "ghostBeamOrigin" not in creature and "nozzlePosition" not in creature, "the beam must not leave a weapon or the pack"
    assert update.count("attachObjectToBone(") == 2 and "attachObjectToBone(bone,mGhostHeldBox," in update, \
        "only the small box and, while beaming, the cannon go into the hand"
    clear = body(creature, "void Creature::clearGhostHuntVisuals()")
    has(clear, "the cannon leaves the hand and the hunter's weapons come back",
        "detachObjectFromBone(mGhostCaptureGun)", "scene->destroyEntity(mGhostCaptureGun);mGhostCaptureGun=nullptr;",
        "scene->destroyEntity(mGhostPackGun);mGhostPackGun=nullptr;", "CreatureCombatReactions::showWeaponsForClip(this);")
    has(read("source/entities/Creature.h"), "cannon members", "Ogre::Entity* mGhostCaptureGun = nullptr;",
        "Ogre::SceneNode* mGhostGunHandNode = nullptr;", "Ogre::Entity* mGhostPackGun = nullptr;", "bool mGhostOwnWeaponsHidden = false;")
    weapon = body(render, "void RenderManager::rrCreateWeapon(")
    has(weapon, "the renderer names the weapon mesh the same way", "mSceneManager->createEntity(curWeapon->getOgreNamePrefix()\n                                + hand + \"_\" + curCreature->getName(),")
    has(body(creature, "static void setGhostHunterWeaponsVisible("), "own weapons by their renderer names",
        'const std::string name=weapons[i]->getOgreNamePrefix()+hands[i]+"_"+hunter.getName();')
    # The beam reaches 1 tile in a level-1 room (GHOSTS-PLAN D20: ghost tile 1, hunter tile 2).
    assert room_config()["GhostBeamRange"] == 1.0, "beam range of a level-1 room"
    # The box is in the hand on the way out and on the whole way back to the cauldron and the hook (mode 2), it is
    # thrown under the ghost (mode 1) and lies there (3, 4); the held box is shown only in mode 2.
    header = read("source/creatureaction/CreatureActionHuntGhost.h")
    has(header, "box phases", "uint32_t getBoxVisualState() const;", "bool hasBackpack() const { return mEquipped && !mInterrupted; }")
    has(update, "only the small box is in the hand", "mGhostHeldBox->setVisible(mGhostBoxMode==2);", '"_HeldGhostBox","GhostBox.mesh"',
        "position=hand+(floor-hand)*progress;")
    has(update, "no backpack, no hunter equipment", "if(!mGhostBackpack) { clearGhostHuntVisuals();return; }")
    # The pack comes from its hook and goes back to it.
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    hunt = body(action, "bool CreatureActionHuntGhost::handleHunt()")
    ordered(body(hunt, "    if(mState==0)"), "taken from the hook", "Tile* hook=map.getTile(mHookX,mHookY);", "if(!moveTo(hook))",
        "room->equipHook(mCreature,true);mEquipped=true;mState=1;")
    ordered(body(hunt, "    if(mState==7)"), "hung back on the hook", "Tile* hook=map.getTile(mHookX,mHookY);", "if(!moveTo(hook))",
        "if(mCreature.isMoving()) return false;", "interrupt();mCreature.popAction();")
    has(body(action, "void CreatureActionHuntGhost::interrupt()"), "the hook gets the pack back", "releaseHunter(mCreature);", "mEquipped=false;")
    room = read("source/rooms/RoomGhostRoom.cpp")
    has(body(room, "void RoomGhostRoom::releaseHunter("), "release shows the pack on the hook", "equipHook(hunter,false);")
    has(body(room, "void RoomGhostRoom::equipHook("), "an empty hook while the pack is worn", 'const std::string mesh=equipped?"GhostHookEmpty":"GhostHook";')
    print("beam from the capture cannon in the hand, box in the hand, pack from the hook: ok")


# Owner decision 791 (build 45): the worn backpack was a large black untextured block (0.35 x 0.25 x 0.50 for every
# hunter, 68 % of the dwarf's height, almost all of it GhostLeather with luminance 33 and deviation 3). It is now a
# readable textured ghost-hunter pack sized to each hunter and worn on its back (decision 733 stays): bright canvas
# with a visible weave as its main surface, steel, rubber, brass, warning stripes and green power cells on the outer
# face. Fails on base 89fbc6bd7.
def textured_backpack_sized_to_hunter():
    scripts = material_scripts()
    positions, _ = mesh("GhostBackpack")
    low = [min(p[i] for p in positions) for i in range(3)]
    high = [max(p[i] for p in positions) for i in range(3)]
    depth = high[1] - low[1]
    areas, outer = material_areas("GhostBackpack", (low[1], low[1] + 0.25 * depth, 1))
    _, inner = material_areas("GhostBackpack", (high[1] - 0.25 * depth, high[1], 1))
    for material in areas:
        assert material in scripts, ("pack material without a definition", material)
    main = max(areas, key=areas.get)
    texture = re.search(r"^\s*texture\s+(\S+\.png)", scripts[main], re.M)
    assert texture, ("main pack surface without texture", main)
    mean, deviation = png_luminance(repo / "materials" / "textures" / texture.group(1))
    assert mean >= 90 and deviation >= 10, ("main pack surface is dark or flat", main, round(mean, 1), round(deviation, 1))
    assert areas[main] >= 0.4 * sum(areas.values()), ("the textured main surface covers the pack", main)
    assert not {"GhostLeather", "GhostIron"} & set(areas), ("no near-black leather or iron on the worn pack", sorted(areas))
    assert len(areas) >= 5, ("canvas, steel, straps, fittings and glow", sorted(areas))
    # The straps lie on the +y side (turned to the hunter's back), the green power cells glow on the outer -y face.
    assert any(glowing(scripts[name]) for name in outer), ("green power cells on the outer face", sorted(outer))
    assert not any(glowing(scripts[name]) for name in inner), ("no glow against the hunter's back", sorted(inner))
    assert "GhostPackRubber" in inner, ("padded straps on the hunter's side", sorted(inner))
    assert abs(low[2]) < 1e-4, "the pack origin is its bottom"
    for name in ("GhostPackCanvas", "GhostPackSteel", "GhostPackRubber"):
        assert any("materials/textures/%s.png" % name in row and "GPL" in row for row in read("CREDITS").splitlines()), name
    models = read("assets-src/rooms/ghostroom/create_models.py")
    has(models, "the pack straps lie on its +y side", "box('Padded shoulder strap',(x,.094,.27)", "'GhostBackpack':worn_backpack,")
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    has(update, "the pack moves with the hunter, is worn on the back, turned with its straps to the hunter and sized to it",
        '"GhostBackpack.mesh"', "const Ogre::Real fit=0.36f*creatureHeight/packSize.z;",
        "const Ogre::Real back=std::min(creatureBounds.getMaximum().y,0.12f*creatureHeight);",
        'mGhostBackpackNode=getEntityNode()->createChildSceneNode(getName()+"_GhostPackNode",\n'
        "            Ogre::Vector3(0.0f,back+0.5f*fit*packSize.y,0.38f*creatureHeight),\n"
        "            Ogre::Quaternion(Ogre::Degree(180.0f),Ogre::Vector3::UNIT_Z));",
        "mGhostBackpackNode->setScale(Ogre::Vector3(fit,fit,fit));")
    # Build 45: a fixed 0.3 behind the centre (the skeleton's back is at 0.075) and the mesh size for every hunter.
    assert "Ogre::Vector3(0.0f,0.3f," not in update and "Ogre::Vector3(0.0f,-0.3f," not in update, "the pack sits on the back"
    # With the authored proportions the pack is 36 % of the hunter's height and lies against its back (the dwarf: 0.27
    # of 0.74, build 45: 0.50).
    for hunter, height, rear in (("RunelordDwarf", 0.745, 0.125), ("skeleton", 1.377, 0.075), ("PitDemon", 1.172, 0.618)):
        fit = 0.36 * height / (high[2] - low[2])
        front = min(rear, 0.12 * height)
        assert fit * (high[2] - low[2]) <= 0.37 * height and front <= rear + 1e-6, (hunter, fit, front)
    print("textured backpack sized to the hunter on its back: ok")


# Decision 798: the full wall hook shows the same textured pack, with the same holstered cannon, as the hunter wears.
def hook_pack_like_worn_pack():
    render = body(read("source/render/RenderManager.cpp"), "void RenderManager::rrCreateRenderedMovableEntity(")
    ordered(render, "a full hook is drawn bare, before the entity is made", "meshName = TreasuryGoldMesh::prepareMesh(mSceneManager, meshName, pileFar);",
        'if(meshName == "GhostHook")\n            meshName = "GhostHookEmpty";', "ent = mSceneManager->createEntity(tempString, meshPtr);")
    building = read("source/entities/BuildingObject.cpp")
    create = body(building, "void BuildingObject::createMeshLocal(")
    hook = create[create.index('getMeshName()=="GhostHook"'):]
    hook = hook[:hook.index("if(!getIsOnServerMap() && mItemBagQuality >= 0)")]
    has(create, "only a full hook on the client", 'if(!getIsOnServerMap() && getMeshName()=="GhostHook" && getEntityNode()!=nullptr)')
    has(hook, "the worn pack and its cannon hang on the hook",
        'scene->createEntity(getName()+"_GhostHookPack","GhostBackpack.mesh");',
        'scene->createEntity(getName()+"_GhostHookPackGun","GhostCaptureGun.mesh");',
        "const Ogre::Real packHeight=0.30f,packBackY=0.03f,packTopZ=0.56f;", "const Ogre::Real fit=packHeight/packSize.z;",
        "packBackY+fit*packBounds.getMaximum().y,packTopZ-fit*packBounds.getMaximum().z),",
        "Ogre::Quaternion(Ogre::Degree(180.0f),Ogre::Vector3::UNIT_Z));", "mGhostHookPackNode->setScale(Ogre::Vector3(fit,fit,fit));",
        "mGhostHookPackNode->attachObject(pack);", "holsterNode->attachObject(gun);")
    # The holster is the one of the worn pack, line for line
    worn = body(read("source/entities/Creature.cpp"), "void Creature::updateGhostHuntVisuals(double seconds)")
    for line in ("const Ogre::Real holster=0.85f*packSize.z/", "Ogre::Vector3(-0.5f*packSize.x-0.045f,0.0f,0.05f*packSize.z));",
            "holsterNode->setScale(Ogre::Vector3(holster,holster,holster));"):
        assert line in worn and line in hook, ("same holster as the worn pack", line)
    has(body(building, "void BuildingObject::destroyMeshLocal("), "the pack, the holster and the cannon are released",
        "if(mGhostHookPackNode!=nullptr)", "scene->destroySceneNode(child);", "scene->destroySceneNode(mGhostHookPackNode);mGhostHookPackNode=nullptr;")
    has(read("source/entities/BuildingObject.h"), "client node", "Ogre::SceneNode* mGhostHookPackNode = nullptr;")
    # The bare hook carries none of the old dark pack, the hanging pack is the textured worn one
    assert "GhostLeather" not in submesh_materials("GhostHookEmpty"), "the bare hook has no old leather pack"
    assert "GhostLeather" in submesh_materials("GhostHook"), "the old hook mesh is the one with the dark pack"
    worn_materials = set(submesh_materials("GhostBackpack"))
    assert {"GhostPackCanvas", "GhostPackSteel", "GhostPackRubber"} <= worn_materials and "GhostLeather" not in worn_materials, worn_materials
    # The pack hangs on the hook: the hook tip reaches into its strap side and its top, and it stays inside the hook object
    positions, _ = mesh("GhostBackpack")
    low = [min(p[i] for p in positions) for i in range(3)]
    high = [max(p[i] for p in positions) for i in range(3)]
    fit = 0.30 / (high[2] - low[2])
    top, bottom, back, front = 0.56, 0.56 - fit * (high[2] - low[2]), 0.03, 0.03 + fit * (high[1] - low[1])
    hook_positions, _ = mesh("GhostHookEmpty")
    tip = [p for p in hook_positions if p[1] > 0.04]
    assert max(p[1] for p in tip) > back and min(p[2] for p in tip) < top and max(p[2] for p in tip) > top - 0.1, "the hook holds the pack"
    assert bottom > 0.1 and top < 0.8 and front < 0.2, ("the pack stays on the hook object", bottom, top, front)
    print("pack on the wall hook looks like the worn textured pack: ok")


# Owner decision 865, part 1: the beam ends on the ghost's body; part 2: shut until in beam range, open first, then
# pull, then shut for good.
def decision_865_beam_and_trap_order():
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    aim = body(creature, "static Ogre::Vector3 ghostBeamAimPoint(")
    # The beam end is a point of the ghost's drawn body: the share GhostBeamAimShare of the height of its world bounds
    has(aim, "the beam hits the ghost's body",
        "const std::string name=ghost.getOgreNamePrefix()+ghost.getName();",
        "const Ogre::AxisAlignedBox bounds=scene->getEntity(name)->getWorldBoundingBox(true);",
        'getRoomConfigDouble("GhostBeamAimShare")',
        "return Ogre::Vector3(bounds.getCenter().x,bounds.getCenter().y,bounds.getMinimum().z+share*bounds.getSize().z);")
    code = code_only(update)
    assert "target->getPosition()+" not in code and "0.0f,0.0f,0.4f" not in code, "the beam no longer ends at a fixed point over the trap"
    assert code.count("ghostBeamAimPoint(scene,*target)") == 2, "the cannon aim (decision 894) and the beam end share the one aim point"
    for chain in ("Ogre::Vector3 point=start+(end-start)*fraction;", "points[i]=start+(end-start)*fraction;",
                  "mGhostBeamImpact->getBillboard(0)->setPosition(end);"):
        assert chain in code, ("core, bolts and impact glow end on the ghost", chain)
    rows = read("config/rooms.cfg").splitlines()
    index = next(i for i, row in enumerate(rows) if row.split()[:1] == ["GhostBeamAimShare"])
    assert rows[index].split()[1] == "0.7" and rows[index - 1].lstrip().startswith("#"), "GhostBeamAimShare 0.7 with its doc line"
    doc = " ".join(row.lstrip("# ") for row in rows[index - 3:index])
    has(doc, "the doc line names the target", "chest", "decision 865", "never ends at the trap")
    share = float(rows[index].split()[1])
    # Chest below the head, and for every capture share of the look model (scale 0.5 to 1, sunk by up to GhostPullDepth)
    # the point lies inside the ghost's body; while the ghost still floats it is well above the trap on the floor
    room = room_config()
    assert 0.5 < share < 0.9, share
    for capture in [i / 20.0 for i in range(21)]:
        pull_start, min_scale = room["GhostPullStartShare"], room["GhostCaptureMinScale"]
        shrink = min(1.0, capture / pull_start)
        scale = 1.0 - (1.0 - min_scale) * shrink
        pull = 0.0 if capture <= pull_start else min(1.0, (capture - pull_start) / (1.0 - pull_start))
        bottom = 0.3 * (1.0 - pull) - pull * room["GhostPullDepth"]
        height = scale * 1.0  # the ghost is about one tile high; its world bounds scale with its node
        hit = bottom + share * height
        assert bottom < hit < bottom + height, (capture, hit)
        if pull == 0.0:
            assert hit > 0.3 + 0.12, ("above the top of the trap on the floor while the ghost floats", capture, hit)
    # Trap order: the phases on the client in the order of the catch
    throw = update[update.index("if(mGhostBoxMode==1)"):update.index("else if(mGhostBoxMode==4)")]
    shut = update[update.index("else if(mGhostBoxMode==6)"):update.index("            else\n            {\n                // The beam weakens")]
    beam = update[update.index("            else\n            {\n                // The beam weakens"):update.index("// Only the snap rocks the box")]
    has(throw, "shut until it lies under the ghost in beam range", "mGhostLidShown=0.0;")
    has(shut, "shut for good once snapped, no light", "mGhostLidShown=0.0;", "mGhostCaptureShown=1.0;")
    assert "lidTarget" not in shut and "trapLight" not in shut, "the shut trap never opens or shines again"
    ordered(beam, "the lid opens first, only then is the ghost pulled in",
        'lidTarget=std::min(1.0,beamed/config.getRoomConfigDouble("GhostLidOpenSeconds"));',
        "const double pulled=beamSeconds>lidOpen?std::max(0.0,(beamed-lidOpen)/(beamSeconds-lidOpen)):mGhostThrowTurns;",
        "mGhostCaptureShown+=(pulled-mGhostCaptureShown)*std::min(1.0,seconds*6.0);")
    has(beam, "the beam time of the hunter", "const double beamSeconds=CreatureActionHuntGhost::getBeamSeconds(*this);",
        'const double lidOpen=config.getRoomConfigDouble("GhostLidOpenSeconds");')
    action = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    ordered(body(action, "uint32_t CreatureActionHuntGhost::getBoxVisualState() const"), "the waiting box is the shut phase",
        "if(mState==3) return 3u;", "if(mState==10) return 4u;", "if(mState==9) return 6u;")
    # Replay the catch and the time after it in 10 ms steps for research levels and efficiencies: the lid and the pull
    lid_open, lid_snap = room["GhostLidOpenSeconds"], room["GhostLidSnapSeconds"]
    throw_s, snap_s = room["GhostBoxThrowSeconds"], room["GhostBoxSnapSeconds"]
    for beam_seconds in (16.0, 16.0 * 0.8 / 1.5, 16.0 * 0.667 / 3.0):
        frames, opened_at, pulled_at, shut_at = [], None, None, None
        for step in range(int((throw_s + beam_seconds + snap_s + 5.0) * 100) + 1):
            t = step / 100.0
            if t < throw_s:
                lid, pulled = 0.0, 0.0
            elif t < throw_s + beam_seconds:
                beamed = t - throw_s
                lid = min(1.0, beamed / lid_open)
                pulled = max(0.0, (beamed - lid_open) / (beam_seconds - lid_open))
            elif t < throw_s + beam_seconds + snap_s:
                lid, pulled = max(0.0, 1.0 - (t - throw_s - beam_seconds) / lid_snap), 1.0
            else:
                lid, pulled = 0.0, 1.0  # phase 6 under the ghost, then carried shut in the hand (phase 2)
            if lid == 1.0 and opened_at is None:
                opened_at = t
            if pulled > 0.0 and pulled_at is None:
                pulled_at = t
            if opened_at is not None and t > throw_s + beam_seconds and lid == 0.0 and shut_at is None:
                shut_at = t
            frames.append((t, lid, pulled))
        assert all(lid == 0.0 for t, lid, _ in frames if t < throw_s), "shut until in beam range and thrown"
        assert opened_at is not None and pulled_at is not None and opened_at <= pulled_at, ("open first, then pull", opened_at, pulled_at)
        assert all(p == 0.0 for t, lid, p in frames if lid < 1.0 and t < throw_s + beam_seconds), "no pull before the lid is open"
        assert abs(max(p for t, lid, p in frames if t < throw_s + beam_seconds) - 1.0) < 0.01, "fully inside at the end of the beam"
        assert shut_at is not None and all(lid == 0.0 for t, lid, _ in frames if t >= shut_at), "shut and stays shut"
    print("decision 865: beam on the ghost's chest, trap shut -> open -> pull -> shut for good: ok")


def main():
    box_in_hand()
    visual_states()
    catch_order()
    catch_timing()
    alarm_lamps()
    no_flat_panels()
    small_textured_box()
    beam_from_capture_cannon()
    textured_backpack_sized_to_hunter()
    hook_pack_like_worn_pack()
    decision_865_beam_and_trap_order()
    print("ghost catch flow: ok")


if __name__ == "__main__":
    main()
