"""Static staged checks for both remaining campaign key doors; no game or compilation."""
from pathlib import Path
import hashlib
import re
import check_campaign_playability as campaign

root = Path(__file__).resolve().parents[2]
BASELINE = {'Ebonrook': ('84261b3c15e22d90f49c31b69b74c84a61912e60f2e4cc0483f990e40a3beced', '52a1e6110a62dcdd3b4507d35c821f6ea5d48c0fd15c72f65f98e45ce2309d67', '450425baa1ee2c367b365944a53c2fba4ba41cb5f2e36b42e5eb979f9a464dbc'), 'Mirewatch': ('80fbd9f452b093b21a9f8d3ac1754b78aa178578956e3464042567a79f312ded', '386e45eba2a2cb2ba4325782ddb9695f22ab9bd92ec424769f5b06c815cde248', '3429a4adfb1c3d4c6b775b500bb00777878ce49aa237588fbc66a8431167632a')}

GOLD_REWARDS = {'Ebonrook': [('firstCoin', 'Action\tgold\t1\t800'), ('westMarch', 'Action\tgold\t1\t700'), ('sealed', 'Action\tgold\t1\t1500'), ('kills', 'Action\tgold\t1\t1000'), ('scoutPossessed', 'Action\tgold\t1\t600'), ('rookHoardOpened', 'Action\tgold\t1\t1500')], 'Mirewatch': [('firstCoin', 'Action\tgold\t1\t600'), ('towerA', 'Action\tgold\t1\t500'), ('scoutTowerC', 'Action\tgold\t1\t400')]}

# Extract one source function body for transport and save-contract assertions.
def body(text, signature):
    return text.split(signature, 1)[1].split("\n}\n", 1)[0]


# Validate immutable inputs and both closed/open stages of the approved door geometry.
def check_map(name, bounds, door, front, owner, key, event, observer, expected_count, inside):
    text = (root / "levels/campaign" / (name + ".level")).read_text(encoding="utf-8")
    level = campaign.parse_level(text)
    digest = lambda value: hashlib.sha256(value.encode()).hexdigest()
    minerals = "\n".join(line.strip() for line in campaign.section(text, "Tiles").splitlines()
                         if len(line.split()) >= 4 and line.split()[2] in ("2", "6"))
    assert (digest(campaign.section(text, "Rooms")), digest(campaign.section(text, "Creatures")),
            digest(minerals)) == BASELINE[name], "rooms, initial creatures and minerals must be preserved"
    x1, x2, y1, y2 = bounds
    walls = {(x, y) for x in range(x1, x2 + 1) for y in range(y1, y2 + 1)
             if x in (x1, x2) or y in (y1, y2)} - {door}
    assert len(walls) == expected_count
    assert all(level["tiles"][q][:2] == (3, 100.0) for q in walls)
    interior = {(x, y) for x in range(x1 + 1, x2) for y in range(y1 + 1, y2)}
    assert all(level["tiles"][q][1] == 0 and level["tiles"][q][0] not in (4, 5) for q in interior)
    initial_inside = {pos for _, _, pos in level["creatures"] if pos in interior}
    assert initial_inside == inside
    assert not any(pos in walls | {door} for _, _, pos in level["creatures"])
    assert not any(q in walls | {door} for _, _, _, fields in level["rooms"] for q in fields)
    triggers = {re.search(r"^Name\s+(\S+)", b, re.M)[1]: b
                for b in re.findall(r"\[Trigger\](.*?)\[/Trigger\]", text, re.S)}
    for b in triggers.values():
        for line in b.splitlines():
            fields = line.split()
            if fields[:2] == ["Action", "spawn"]:
                assert (int(fields[3]), int(fields[4])) not in walls | {door} | interior
    rewards = [(n, row) for n, b in triggers.items() for row in b.splitlines()
               if row.startswith("Action\tgold\t")]
    assert rewards == GOLD_REWARDS[name], "preserve every original reward and add only the approved hoard payout"
    opening = triggers[event]
    conditions = [line.strip() for line in opening.splitlines() if line.startswith("Cond")]
    assert conditions == ["Cond\tdeliveredstone\t" + key]
    assert "Mode\tonce" in opening
    door_name = "RookHoardDoor" if name == "Ebonrook" else "FenwickWatchroomDoor"
    assert "Action\tkeydoor\t" + door_name + "\topen" in opening
    assert re.search(r"4\s+" + door_name + r"\s+2\s+1\s+" + str(door[0]) +
                     r"\s+" + str(door[1]) + r"\s+1\s+1 KeyLock 1", text)
    assert "Cond\ttrigger\t" + event in triggers[observer]
    assert text.index("Name\t" + event + "\n") < text.index("Name\t" + observer + "\n") < text.index("Name\tmainVictory\n")
    drop = "Action\tstonedrop\t" + owner + "\t" + key + "\t1\t" + str(front[0]) + "\t" + str(front[1])
    assert text.count(drop) == 1
    assert "Cond\tevent\t" + owner + "\tkilled" in text
    if name == "Ebonrook":
        assert len(interior) == 6
        actions = [line for line in opening.splitlines() if line.startswith("Action")]
        assert actions == ["Action\tkeydoor\tRookHoardDoor\topen", "Action\tgold\t1\t1500"]
        assert (38, 98) not in walls | interior | {door}
        stages = (((44, 97, 46, 98),), ((25, 84, 25, 86),))
    else:
        assert not any(line.startswith("Action\tgold") for line in opening.splitlines())
        assert not campaign.mirewatch_errors(level), "all original 69 room tiles remain claimable after unlock"
        stages = (((83, 30, 85, 30), (95, 30, 97, 30), (80, 7, 80, 8)),)
    for stage in stages:
        closed = dict(level, tiles=dict(level["tiles"]))
        for ax, ay, bx, by in stage:
            for x in range(ax, bx + 1):
                for y in range(ay, by + 1):
                    closed["tiles"][x, y] = (1, 0.0, None)
        closed["tiles"][door] = (3, 100.0, None)
        area, _ = campaign.reachable(closed)
        assert front in area and not (area & interior)
        assert next(pos for n, _, pos in level["creatures"] if n == owner) in area
        opened = dict(closed, tiles=dict(closed["tiles"]))
        opened["tiles"][door] = (1, 0.0, None)
        area, _ = campaign.reachable(opened)
        assert interior <= area
        if name == "Mirewatch":
            for _, room, _, fields in level["rooms"]:
                if room in ("Prison1", "Workshop1"):
                    before, _ = campaign.reachable(closed)
                    assert set(fields) <= before
    assert not campaign.grouped_goal_errors(text, name)
    # Both premature victory and a wrong key/door are rejected against reviewed requirements.
    for old, new in (("Cond\ttrigger\t" + event, "Cond\talive\t" + owner + "\t0"),
                     ("Cond\tdeliveredstone\t" + key, "Cond\tdeliveredstone\tother-key"),
                     ("Action\tkeydoor\t" + door_name + "\topen", "Action\tkeydoor\tOtherDoor\topen")):
        assert campaign.grouped_goal_errors(text.replace(old, new), name)


check_map("Ebonrook", (37, 41, 91, 94), (37, 93), (36, 93), "SabineRook", "rook-key",
          "rookHoardOpened", "mainWarden", 13, set())
check_map("Mirewatch", (92, 99, 21, 25), (96, 21), (96, 20), "MoraFenwick", "watch-key",
          "watchroomOpened", "mainTowers", 21, {(93, 22), (96, 24)})
stone = (root / "source/entities/MissileStone.cpp").read_text(encoding="utf-8")
carry = (root / "source/creatureaction/CreatureActionCarryEntity.cpp").read_text(encoding="utf-8")
release = body(stone, "void MissileStone::notifyEntityCarryOff(")
complete = body(stone, "void MissileStone::completeDelivery(")
assert "mDelivered =" not in release
assert "mCarried && getDeliveryTile(carrier) != nullptr" in complete
assert "carrier.getPositionTile() == getDeliveryTile(carrier)" in complete
assert "mDelivered = true" in complete
assert "completeDelivery" not in body(carry, "CreatureActionCarryEntity::~CreatureActionCarryEntity()")
assert "new MissileStone" not in release
runner = (root / "source/gamemap/LevelScriptRunner.cpp").read_text(encoding="utf-8")
turn = body(runner, "void LevelScriptRunner::doTurn(")
assert "if(!trigger.mRepeat)" in turn and "continue;" in turn
assert turn.index("++trigger.mTimesFired") < turn.index("runAction(")
assert "MissionTransport" in stone and "mCarried = false;" in stone
script = (root / "source/gamemap/LevelScript.cpp").read_text(encoding="utf-8")
assert 'os << "State\\t" << trigger.mTimesFired' in script
print("Remaining key doors: staged routes, preserved inputs, exact deliveries, rewards, victory gates and save wiring PASS")
