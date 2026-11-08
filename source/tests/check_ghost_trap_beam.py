"""Check the opening ghost trap and the stronger capture beam without compiling (GHOSTS-PLAN D17, D20, D22 and
section 16.4 GhostBeam; owner decisions 801, 802, 805 and 806).

Trap: the lid of the small box opens at the start of the beam step and stays open while the beam weakens the ghost to
half its size (never smaller, it never vanishes) and the open trap then pulls the half-size ghost down into its opening;
the lid snaps shut with the bang only at the start of the snap step, after the ghost is fully inside. While it is open
the trap shines a bright glow and a light cone upwards in the green-white of the beam, fading when the lid shuts. The
catch keeps 2 s throw, 16 s beam including the pull and 2 s snap. The box mesh has a Lid bone with an Open clip.
Beam: a thick bright core, several jagged flickering bolts at once with forks, a glow round the beam, sparks at the
cannon tip and a flickering impact glow on the ghost for the whole beam step, all from documented config keys, within a
fixed per-hunter billboard budget.
Expected values are fixed, counted once on this branch. Each part fails on base 636e678c8 (no lid, the ghost shrank to
nothing, a thin three-bolt beam with sparks only in its first 0.1 s)."""
from pathlib import Path
import math
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


# Assert that every fragment occurs in the text, naming the rule it proves.
def has(text, rule, *fragments):
    for fragment in fragments:
        assert fragment in text, (rule, fragment)


# Assert that the fragments occur in this order.
def ordered(text, rule, *fragments):
    position = -1
    for fragment in fragments:
        found = text.find(fragment, position + 1)
        assert found > position, (rule, fragment)
        position = found


# Numeric rows of config/rooms.cfg and, for every key, whether a comment documents it (directly above, or above the
# block of keys it belongs to).
def config():
    rows = read("config/rooms.cfg").splitlines()
    values, documented = {}, {}
    for index, row in enumerate(rows):
        parts = row.split("#", 1)[0].split()
        if len(parts) == 2 and parts[0].startswith("Ghost"):
            try:
                values[parts[0]] = float(parts[1])
            except ValueError:
                continue
            above = index - 1
            while above >= 0 and rows[above].split()[:1] and rows[above].split()[0].startswith("Ghost") and \
                    not rows[above].lstrip().startswith("#"):
                above -= 1
            documented[parts[0]] = above >= 0 and rows[above].lstrip().startswith("#")
    return values, documented


TRAP = {"GhostLidOpenSeconds": 0.5, "GhostLidSnapSeconds": 0.15, "GhostCaptureMinScale": 0.5, "GhostPullStartShare": 0.75,
        "GhostPullDepth": 0.8, "GhostTrapGlowSize": 0.45, "GhostTrapConeHeight": 1.4, "GhostTrapConeBaseWidth": 0.14,
        "GhostTrapConeTopWidth": 0.6, "GhostTrapFadeSeconds": 0.4}
BEAM = {"GhostBeamSegments": 10, "GhostBeamBolts": 4, "GhostBeamBranches": 2, "GhostBeamCoreWidth": 0.07,
        "GhostBeamBoltWidth": 0.035, "GhostBeamGlowWidth": 0.32, "GhostBeamJitter": 0.12, "GhostBeamBranchLength": 0.16,
        "GhostBeamFlickerSeconds": 0.05, "GhostBeamTipSparkRate": 140, "GhostBeamTipSparkSize": 0.07,
        "GhostBeamImpactSize": 0.55}


def config_values():
    values, documented = config()
    for key, value in {**TRAP, **BEAM, "GhostBoxThrowSeconds": 2, "GhostBeamSeconds": 16, "GhostBoxSnapSeconds": 2}.items():
        assert values.get(key) == value, (key, values.get(key), value)
        assert documented[key], (key, "documentation line")
    print("trap and beam config keys with their documentation lines: ok")
    return values


# Model of GhostEntity::updateLook during the capture: (scale, height above the floor) for a capture share.
def ghost_look(values, capture):
    capture = max(0.0, min(1.0, capture))
    pull_start, min_scale = values["GhostPullStartShare"], values["GhostCaptureMinScale"]
    shrink = min(1.0, capture / pull_start) if pull_start > 0 else 1.0
    scale = 1.0 - (1.0 - min_scale) * shrink
    pull = 0.0 if capture <= pull_start else min(1.0, (capture - pull_start) / (1.0 - pull_start))
    return scale, 0.3 * (1.0 - pull) - pull * values["GhostPullDepth"]


def ghost_source():
    look = body(read("source/entities/GhostEntity.cpp"), "void GhostEntity::updateLook()")
    has(look, "shrink to the smallest size, then the pull into the opening",
        "const double capture = std::max(0.0, std::min(1.0, mCaptureProgress));",
        'config.getRoomConfigDouble("GhostCaptureMinScale");', 'config.getRoomConfigDouble("GhostPullStartShare");',
        "const double shrink = pullStart > 0.0 ? std::min(1.0, capture / pullStart) : 1.0;",
        "const double scale = 1.0 - (1.0 - minScale) * shrink;",
        "const double pull = capture <= pullStart ? 0.0 : std::min(1.0, (capture - pullStart) / (1.0 - pullStart));",
        'const double sink = height * (1.0 - pull) - pull * config.getRoomConfigDouble("GhostPullDepth");',
        "node->setPosition(mPosition + Ogre::Vector3(0, 0, static_cast<Ogre::Real>(sink)));")
    assert "1.0-mCaptureProgress" not in look, "the ghost no longer shrinks to nothing"


# The client trap code in Creature::updateGhostHuntVisuals.
def trap_source():
    creature = read("source/entities/Creature.cpp")
    update = body(creature, "void Creature::updateGhostHuntVisuals(double seconds)")
    # Throw: lid shut; beam: lid opens within GhostLidOpenSeconds; snap: lid slams within GhostLidSnapSeconds
    throw = update[update.index("if(mGhostBoxMode==1)"):update.index("else if(mGhostBoxMode==4)")]
    snap = update[update.index("else if(mGhostBoxMode==4)"):update.index("            else\n            {\n                // The beam weakens")]
    beam = update[update.index("            else\n            {\n                // The beam weakens"):update.index("// Only the snap rocks the box")]
    has(throw, "shut in flight", "mGhostLidShown=0.0;")
    has(beam, "opens at the start of the beam step and stays open",
        'const double beamed=mGhostThrowTurns*CreatureActionHuntGhost::getBeamSeconds(*this);',
        'lidTarget=std::min(1.0,beamed/config.getRoomConfigDouble("GhostLidOpenSeconds"));',
        "mGhostLidShown+=(lidTarget-mGhostLidShown)*std::min(1.0,seconds*12.0);", "trapLight=mGhostLidShown;",
        "mGhostCaptureShown+=(mGhostThrowTurns-mGhostCaptureShown)*std::min(1.0,seconds*6.0);")
    has(snap, "slams shut with the bang at the start of the snap step, the light fades",
        "const double snapped=mGhostThrowClientTurns/ODApplication::turnsPerSecond;",
        'mGhostLidShown=std::max(0.0,1.0-snapped/config.getRoomConfigDouble("GhostLidSnapSeconds"));',
        'trapLight=std::max(0.0,1.0-snapped/config.getRoomConfigDouble("GhostTrapFadeSeconds"));', "mGhostCaptureShown=1.0;")
    # Only the snap closes an open lid
    assert update.count("mGhostLidShown=std::max(0.0,1.0-") == 1
    has(update, "the lid clip follows the open share",
        'if(trap->hasSkeleton() && trap->hasAnimationState("Open"))', 'Ogre::AnimationState* open=trap->getAnimationState("Open");',
        "open->setEnabled(true);open->setLoop(false);",
        "open->setTimePosition(static_cast<Ogre::Real>(mGhostLidShown)*open->getLength());")
    has(update, "glow and light cone in the beam colours while open",
        "if(trapLight>0.0)", 'mGhostTrapGlow=scene->createBillboardSet(getName()+"_GhostTrapGlow",2);',
        'mGhostTrapGlow->setMaterialName("GhostBeam");', 'mGhostTrapCone=scene->createBillboardChain(getName()+"_GhostTrapCone");',
        'mGhostTrapCone->setMaterialName("GhostBeam");', 'config.getRoomConfigDouble("GhostTrapGlowSize")',
        'config.getRoomConfigDouble("GhostTrapConeHeight")', 'config.getRoomConfigDouble("GhostTrapConeBaseWidth")',
        'config.getRoomConfigDouble("GhostTrapConeTopWidth")',
        "mGhostTrapGlow->getBillboard(0)->setColour(Ogre::ColourValue(0.55f,1.0f,0.65f,0.75f*light));",
        "mGhostTrapGlow->getBillboard(1)->setColour(Ogre::ColourValue(0.92f,1.0f,0.94f,light));",
        "Ogre::ColourValue(0.7f,1.0f,0.78f,0.6f*light*(1.0f-up))",
        "if(trapLight<=0.0 && mGhostTrapNode!=nullptr) mGhostTrapNode->setVisible(false);")
    clear = body(creature, "void Creature::clearGhostHuntVisuals()")
    has(clear, "trap light and impact glow released", "scene->destroyBillboardSet(mGhostTrapGlow);mGhostTrapGlow=nullptr;",
        "scene->destroyBillboardChain(mGhostTrapCone);mGhostTrapCone=nullptr;", "scene->destroySceneNode(mGhostTrapNode);mGhostTrapNode=nullptr;",
        "scene->destroyBillboardSet(mGhostBeamImpact);mGhostBeamImpact=nullptr;", "mGhostLidShown=0.0;")
    # The green-white of the beam: the same colours as the GhostBeam bolts and the GhostGlow material's green
    material = read("materials/scripts/GhostParticles.material")
    assert re.search(r"material GhostBeam\s*\{[^}]*scene_blend src_alpha one", material, re.S), "additive beam material"
    # The bang plays when the snap step starts, which is when the lid slams
    hunt = read("source/creatureaction/CreatureActionHuntGhost.cpp")
    ordered(hunt, "snap step and bang together", "mTurns-=duration;mBeamTarget.clear();mState=10;",
        'playSound(map,*ghost->getPositionTile(),"Rooms/GhostRoom/BoxSnap");')


# Replay the 20 s catch on the client: lid, light and ghost every 10 ms.
def timeline(values):
    throw, beam, snap = values["GhostBoxThrowSeconds"], values["GhostBeamSeconds"], values["GhostBoxSnapSeconds"]
    lid_open, lid_snap, fade = values["GhostLidOpenSeconds"], values["GhostLidSnapSeconds"], values["GhostTrapFadeSeconds"]
    frames, smallest, fully_in_open, closed_at = [], 1.0, None, None
    for step in range(int((throw + beam + snap) * 100) + 1):
        t = step / 100.0
        if t < throw:
            lid, light, capture = 0.0, 0.0, 0.0
        elif t < throw + beam:
            beamed = t - throw
            capture = beamed / beam
            lid = min(1.0, beamed / lid_open)
            light = lid
        else:
            snapped = t - throw - beam
            capture = 1.0
            lid = max(0.0, 1.0 - snapped / lid_snap)
            light = max(0.0, 1.0 - snapped / fade)
        scale, height = ghost_look(values, capture)
        smallest = min(smallest, scale)
        if height <= -values["GhostPullDepth"] + 1e-9 and fully_in_open is None:
            fully_in_open = (t, lid)
        if t >= throw + beam and lid == 0.0 and closed_at is None:
            closed_at = t
        frames.append((t, lid, light, scale, height))
    # The lid is shut in flight, opens at the start of the beam step and is open for the whole rest of it
    assert all(lid == 0.0 for t, lid, *_ in frames if t < throw)
    assert all(lid == 1.0 for t, lid, *_ in frames if throw + lid_open + 0.005 <= t < throw + beam), "open during the beam"
    assert all(0.0 < lid for t, lid, *_ in frames if throw < t < throw + beam), "open state during the beam"
    # The glow shines whenever the lid is open and fades with the snap
    assert all(light > 0.0 for t, lid, light, *_ in frames if lid > 0.0), "the open box has its glow"
    assert all(light == 0.0 for t, lid, light, *_ in frames if t >= throw + beam + fade + 0.005)
    # Smallest size 0.5, never smaller: it never vanishes
    assert abs(smallest - 0.5) < 1e-12, smallest
    assert all(scale >= 0.5 for *_, scale, height in frames)
    # Half size reached at the end of the shrink share, then the pull into the opening
    pull_from = throw + beam * values["GhostPullStartShare"]
    assert all(height == 0.3 for t, lid, light, scale, height in frames if t <= pull_from), "no pull before"
    assert all(abs(scale - 0.5) < 1e-12 for t, lid, light, scale, height in frames if t >= pull_from)
    # Pulled fully into the opening before the lid closes: at the end of the beam step with the lid still open
    assert fully_in_open == (throw + beam, 1.0), fully_in_open
    # The lid closes at the end, within GhostLidSnapSeconds of the snap step, and stays shut
    assert closed_at is not None and closed_at <= throw + beam + lid_snap + 0.01, closed_at
    assert all(lid == 0.0 for t, lid, *_ in frames if t >= throw + beam + lid_snap + 0.005)
    assert frames[-1][0] == 20.0
    print("trap timeline: shut in flight, open for the beam, ghost half size then pulled in, lid shuts at the end: ok")


# Read a binary OGRE string that ends with a newline.
def ogre_string(data, position):
    end = data.index(b"\n", position)
    return data[position:end].decode("ascii"), end + 1


# Bones and the Lid track of the Open clip of the box skeleton: [(time, angle about x in degrees)].
def box_skeleton():
    data = (repo / "models/GhostBox.skeleton").read_bytes()
    _, position = ogre_string(data, 2)
    bones, clips = {}, {}
    while position < len(data):
        kind, size = struct.unpack_from("<HI", data, position)
        if kind == 0x2000:
            bone, inner = ogre_string(data, position + 6)
            handle = struct.unpack_from("<H", data, inner)[0]
            bones[handle] = bone
            position += size + (inner - (position + 6))
            continue
        if kind == 0x4000:
            clip, inner = ogre_string(data, position + 6)
            length = struct.unpack_from("<f", data, inner)[0]
            inner += 4
            tracks = {}
            while inner < position + size:
                child, child_size = struct.unpack_from("<HI", data, inner)
                if child == 0x4100:
                    bone = struct.unpack_from("<H", data, inner + 6)[0]
                    key, keys = inner + 8, []
                    while key < inner + child_size:
                        key_kind, key_size = struct.unpack_from("<HI", data, key)
                        if key_kind == 0x4110:
                            time, x, y, z, w = struct.unpack_from("<5f", data, key + 6)
                            keys.append((round(time, 4), round(math.degrees(2 * math.atan2(x, w)), 2), abs(y) + abs(z)))
                        key += key_size
                    tracks[bone] = keys
                inner += child_size
            clips[clip] = (length, tracks)
        position += size
    return bones, clips


def box_mesh():
    bones, clips = box_skeleton()
    assert set(bones.values()) == {"Root", "Lid"}, bones
    assert set(clips) == {"Open"}, set(clips)
    length, tracks = clips["Open"]
    assert abs(length - 1.0) < 1e-6
    lid = next(handle for handle, name in bones.items() if name == "Lid")
    keys = tracks[lid]
    assert keys[0][:2] == (0.0, 0.0) and keys[-1][0] == 1.0 and abs(keys[-1][1] + 110.0) < 0.05, keys
    assert all(rest < 1e-4 for *_, rest in keys), "the lid turns only about its hinge axis"
    # The lid opens steadily (the game sets the clip time to the open share)
    angles = [angle for _, angle, _ in keys]
    assert all(b < a for a, b in zip(angles, angles[1:])), angles
    mesh = (repo / "models/GhostBox.mesh").read_bytes()
    assert b"GhostBox.skeleton" in mesh, "the box mesh uses its rig"
    models = read("assets-src/rooms/ghostroom/create_models.py")
    has(models, "lid parts on the Lid bone, glow in the opening",
        "box('Hinged lid',(0,0,.182),(.25,.21,.03),'GhostBoxCase',.009,group='Lid')",
        "box('Inner containment glow',(0,0,.1712),(.20,.16,.003),'GhostBoxGlow',.001)",
        "rod('Handle grip',(-.07,0,.236),(.07,0,.236),.013,'GhostBoxCase',12,'Lid')",
        "rod('Rear hinge pin',(x-.025,.108,.17),(x+.025,.108,.17),.011,'GhostBrass',10)",
        "pivot=(Vector((0,.108,.17))-centre)*factors",
        "else box_rig(obj,factors,centre) if name=='GhostBox' else None")
    credits = read("CREDITS")
    for name in ("models/GhostBox.mesh", "models/GhostBox.skeleton"):
        assert any(row.startswith(name + " ") and "Lid" in row and "GPLv3+" in row for row in credits.splitlines()), name
    print("box mesh with a Lid bone and an Open clip to 110 degrees: ok")


# The capture beam: layers, flicker, sparks and impact glow from the config keys, within a billboard budget.
def beam(values):
    update = body(read("source/entities/Creature.cpp"), "void Creature::updateGhostHuntVisuals(double seconds)")
    for key in BEAM:
        assert '"%s"' % key in update, (key, "read by the beam code")
    has(update, "glow, core, bolts and forks in one chain set",
        "mGhostBeamChain->setNumberOfChains(2+bolts+bolts*branches);mGhostBeamChain->setMaxChainElements(segments+1);",
        "const size_t fork=2+bolts+bolt*branches+branch;", "if(segments<3) continue;")
    has(update, "re-shaped every GhostBeamFlickerSeconds", "if(mGhostBeamSample<flickerSeconds) return;",
        "mGhostBeamSample=std::fmod(mGhostBeamSample,flickerSeconds);")
    has(update, "sparks for the whole beam step", "mGhostBeamSparks->getEmitter(i)->setDuration(0.0f);",
        'setEmissionRate(static_cast<Ogre::Real>(config.getRoomConfigDouble("GhostBeamTipSparkRate")));',
        "mGhostBeamSparks->setDefaultDimensions(spark,spark);", "if(mGhostSparkNode!=nullptr) mGhostSparkNode->setPosition(start);")
    has(update, "flickering impact glow on the ghost", 'mGhostBeamImpact=scene->createBillboardSet(getName()+"_GhostBeamImpact",2);',
        "const Ogre::Real flare=impact*static_cast<Ogre::Real>(Random::Double(0.7,1.15));",
        "mGhostBeamImpact->getBillboard(0)->setPosition(end);", "mGhostBeamImpact->getBillboard(1)->setPosition(end);")
    has(update, "green-white colours", "glowColour(0.35f,0.9f,0.45f,0.4f),coreColour(0.92f,1.0f,0.94f,1.0f),boltColour(0.55f,1.0f,0.65f,1.0f)",
        "Ogre::ColourValue colour=boltColour;colour.a=static_cast<float>(Random::Double(0.6,1.0));")
    has(update, "the beam still leaves the cannon tip", "const Ogre::Vector3 start=ghostCannonTip(*mGhostCaptureGun);")
    assert "setNumberOfChains(3)" not in update and "0.025f,fraction" not in update, "the thin three-bolt beam is gone"
    # Clearly more intense than the base beam (3 bolts of 0.025, jitter 0.08, re-shaped every 0.1 s, 35 sparks per s
    # for 0.1 s only)
    assert values["GhostBeamBolts"] >= 4 and values["GhostBeamBranches"] >= 1
    assert values["GhostBeamCoreWidth"] >= 2.5 * 0.025 and values["GhostBeamBoltWidth"] > 0.025
    assert values["GhostBeamGlowWidth"] >= 4 * values["GhostBeamCoreWidth"]
    assert values["GhostBeamCoreWidth"] > values["GhostBeamBoltWidth"]
    assert values["GhostBeamJitter"] > 0.08 and values["GhostBeamFlickerSeconds"] < 0.1
    assert values["GhostBeamTipSparkRate"] >= 4 * 35
    # Frame budget per beaming hunter: chain elements, two impact billboards and the spark quota
    chains = 2 + values["GhostBeamBolts"] + values["GhostBeamBolts"] * values["GhostBeamBranches"]
    billboards = chains * (values["GhostBeamSegments"] + 1) + 2
    quota = int(re.search(r"particle_system GhostBeam\s*\{[^}]*?quota (\d+)", read("particles/ChickenFeathers.particle"), re.S).group(1))
    assert (chains, billboards, quota) == (14, 156, 64), (chains, billboards, quota)
    assert billboards + quota <= 250, "no visible frame drop: at most 250 quads per beaming hunter"
    # Re-shapes per second stay low: 20, each one rewrites the 156 chain elements once
    assert round(1.0 / values["GhostBeamFlickerSeconds"]) == 20
    print("stronger beam: core, 4 bolts with 2 forks, glow, tip sparks, impact glow within 220 quads (156 billboards and 64 sparks): ok")


def main():
    values = config_values()
    ghost_source()
    trap_source()
    timeline(values)
    box_mesh()
    beam(values)
    print("ghost trap and beam: ok")


if __name__ == "__main__":
    main()
