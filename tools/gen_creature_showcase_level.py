#!/usr/bin/env python3
"""Writes levels/skirmish/TestCreatureShowcase.level (run from the repository root).

A test map for the creature reactions: one claimed 5x5 hall per room type (the portal takes
3x3), corridors between them, and a line-up hall at the bottom with one creature of every
creature type from config/creatures.cfg. Every hall also gets a few creatures, chosen so that
all types stand next to some room.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "levels" / "skirmish" / "TestCreatureShowcase.level"

COLUMNS = 5
CELL = 7
HALL = 5
ORIGIN = 2

# (room type number, name prefix, size). Numbers follow RoomType in source/rooms/RoomType.h.
HALLS = [
    (1, "DungeonTemple", 5), (2, "Dormitory", 5), (3, "Treasury", 5), (4, "Portal", 3), (5, "Workshop", 5),
    (6, "TrainingHall", 5), (7, "Library", 5), (8, "Hatchery", 5), (9, "Crypt", 5), (11, "Prison", 5),
    (14, "Arena", 5), (15, "Casino", 5), (16, "Torture", 5), (17, "GuardRoom", 5), (18, "Temple", 5),
]

SKILLS = [
    "roomTreasury", "roomDormitory", "roomHatchery", "roomLibrary", "spellSummonWorker", "roomArena",
    "roomBridgeStone", "roomBridgeWooden", "roomCasino", "roomCrypt", "roomPrison", "roomTorture",
    "roomTrainingHall", "roomWorkshop", "roomGuardRoom", "roomTemple", "trapCannon", "trapBoulder",
    "trapSpike", "trapDoorWooden", "spellCallToWar", "spellCreatureDefense", "spellCreatureExplosion",
    "spellCreatureHaste", "spellCreatureHeal", "spellCreatureSlow", "spellCreatureStrength",
    "spellCreatureWeak", "spellEyeEvil",
]


def read_creatures():
    text = (ROOT / "config" / "creatures.cfg").read_text(encoding="utf-8")
    result = []
    for block in re.findall(r"\[Creature\](.*?)\[/Creature\]", text, re.S):
        def value(key):
            m = re.search(r"^\s*" + key + r"\s+(\S+)", block, re.M)
            return m.group(1) if m else None
        name = value("Name")
        mesh = value("MeshName")
        if name is None or mesh is None:
            continue
        result.append((name, mesh, value("WeaponSpawnL") or "none", value("WeaponSpawnR") or "none"))
    return result


def main():
    creatures = read_creatures()
    if not creatures:
        sys.exit("no creatures found in config/creatures.cfg")
    rows = (len(HALLS) + COLUMNS - 1) // COLUMNS
    line_y = ORIGIN + rows * CELL + 1
    size_x = ORIGIN + COLUMNS * CELL + 2
    size_y = line_y + 4
    floor = set()
    halls = []
    for index, (number, prefix, size) in enumerate(HALLS):
        col, row = index % COLUMNS, index // COLUMNS
        x0 = ORIGIN + col * CELL + (HALL - size) // 2
        y0 = ORIGIN + row * CELL + (HALL - size) // 2
        tiles = [(x, y) for x in range(x0, x0 + size) for y in range(y0, y0 + size)]
        floor.update(tiles)
        halls.append((number, "%s%d" % (prefix, index + 1), tiles, x0, y0, size))
        # Corridor to the right neighbour and to the row below (or to the line-up hall).
        cell_x, cell_y = ORIGIN + col * CELL, ORIGIN + row * CELL
        if col + 1 < COLUMNS and index + 1 < len(HALLS):
            for x in range(cell_x + HALL, cell_x + CELL):
                floor.add((x, cell_y + HALL // 2))
        for y in range(cell_y + HALL, (cell_y + CELL) if row + 1 < rows else line_y):
            floor.add((cell_x + HALL // 2, y))
    for x in range(ORIGIN, size_x - 2):
        floor.add((x, line_y))
    heart = halls[0]
    out = []
    out.append("OpenDungeons_Version:0.7.1  # The version of OpenDungeons which created this file (for compatibility reasons).\n")
    out.append("[Info]\nName\t\\[Test\\] Creature showcase\n"
               "Description\tOne hall per room type and a line-up of every creature type, for checking creature reactions and room effects.\n"
               "Music\tSearching_yd.ogg\nFightMusic\tTheDarkAmulet_MP.ogg\nSandbox\t1\n[/Info]\n")
    out.append("[Seats]\n[Seat]\nseatId\t1\nteamId\t1\nplayer\tHuman\nfaction\tKeeper\nstartingX\t%d\nstartingY\t%d\n"
               "colorId\t1\ngold\t5000\ngoldMined\t100\nmana\t100\n[SkillDone]\n%s\n[/SkillDone]\n[SkillNotAllowed]\n"
               "[/SkillNotAllowed]\n[SkillPending]\n[/SkillPending]\n[/Seat]\n[/Seats]\n"
               % (heart[3] + 2, heart[4] + 2, "\n".join(SKILLS)))
    out.append("[Goals]\n# goalName\targuments\n[/Goals]\n")
    out.append("[Tiles]\n# Map Size\n%d # MapSizeX\n%d # MapSizeY\n# posX\tposY\ttype\tfullness\tseatId(optional)\n" % (size_x, size_y))
    for x, y in sorted(floor):
        out.append("%d\t%d\t1\t0\t1\n" % (x, y))
    out.append("[/Tiles]\n")
    out.append("[Rooms]\n# typeRoom\tname\tseatId\tnumTiles\t\tSubsequent Lines: tileX\ttileY\n")
    for number, name, tiles, _x0, _y0, _size in halls:
        out.append("[Room]\n%d\t%s\t1\t%d\n" % (number, name, len(tiles)))
        for x, y in tiles:
            out.append("%d\t%d\n" % (x, y))
        out.append("[/Room]\n")
    out.append("[/Rooms]\n")
    out.append("[Traps]\n# typeTrap\tname\tseatId\tnumTiles\t\tSubsequent Lines: tileX\ttileY\tisActivated(0/1)\t\tSubsequent Lines: optional specific data\n[/Traps]\n")
    out.append("[Lights]\n# posX\tposY\tposZ\tdiffuseR\tdiffuseG\tdiffuseB\tspecularR\tspecularG\tspecularB\tattenRange\tattenConst\tattenLin\tattenQuad\n[/Lights]\n")
    out.append("[CreatureDefinitions]\n[/CreatureDefinitions]\n[EquipmentDefinitions]\n[/EquipmentDefinitions]\n")
    out.append("[Creatures]\n# SeatId\tName\tMeshName\tPosX\tPosY\tPosZ\tClassName\tLevel\tCurrentXP\tCurrentHP\tCurrentWakefulness\t"
               "CurrentHunger\tGoldToDeposit\tLeftWeapon\tRightWeapon\tCarriedSkill\tCarriedWeapon\tNbCreatureEffects\tN*CreatureEffects\n")
    counter = [0]

    def creature(entry, x, y):
        counter[0] += 1
        name, mesh, left, right = entry
        out.append("1\t%s%d\t%s\t%d\t%d\t0\t%s\t1\t0\tmax\t100\t0\t0\t%s\t%s\tnullSkillType\tnone\t0\n"
                   % (name, counter[0], mesh, x, y, name, left, right))

    # Line-up hall: every creature type once, one tile apart.
    for i, entry in enumerate(creatures):
        creature(entry, ORIGIN + i, line_y)
    # Three creatures inside every hall (not the heart), cycling through the types so that
    # every type stands next to some room.
    cursor = 0
    for number, _name, _tiles, x0, y0, size in halls:
        if number == 1:
            continue
        for k in range(3):
            creature(creatures[cursor % len(creatures)], x0 + 1 + k, y0 + size // 2)
            cursor += 1
    out.append("[/Creatures]\n")
    for section, header in (
            ("Spells", "# typeSpell\tSeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\toptionalData"),
            ("CraftedTraps", "# SeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\ttrapType\tPosX\tPosY\tPosZ"),
            ("SkillEntity", "# SeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\tskillPoints\tPosX\tPosY\tPosZ"),
            ("GiftBoxEntity", "# GiftBoxType\tSeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\toptionalData"),
            ("Missiles", "# missileType\tSeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\tdirectionX\tdirectionY\tdirectionZ\tmissileAlive\tdamageAllies\tspeed\toptionalData"),
            ("TreasuryObject", "# SeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\tvalue"),
            ("Chickens", "# SeatId\tName\tMeshName\tPosX\tPosY\tPosZ\topacity\trotationAngle\tPosX\tPosY\tPosZ")):
        out.append("[%s]\n%s\n[/%s]\n" % (section, header, section))
    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    print("wrote %s: %d floor tiles, %d creatures" % (OUT, len(floor), counter[0]))


main()
