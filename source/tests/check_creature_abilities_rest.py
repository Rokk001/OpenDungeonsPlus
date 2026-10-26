"""Check the creature abilities added after freeze, drain and invisible.

Whirlwind, Teleport, GasCloud, HailStorm, GuidedBolt, Grenade, RaiseDead and SkeletonArmy are skills of their own,
Disruption is a slow, strong MissileLaunch. Every skill must be registered under its config name, be part of the
build, and every config line must have as many values as the column comment above it names."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


cmake = read("CMakeLists.txt")
skill_sources = {
    "Whirlwind": "creatureskill/CreatureSkillWhirlwind",
    "Teleport": "creatureskill/CreatureSkillTeleport",
    "GasCloud": "creatureskill/CreatureSkillAreaDamage",
    "HailStorm": "creatureskill/CreatureSkillAreaDamage",
    "GuidedBolt": "creatureskill/CreatureSkillGuidedBolt",
    "Grenade": "creatureskill/CreatureSkillGrenade",
    "RaiseDead": "creatureskill/CreatureSkillRaiseDead",
    "SkeletonArmy": "creatureskill/CreatureSkillSkeletonArmy",
}
for name, base in skill_sources.items():
    assert f"{{SRC}}/{base}.cpp".replace("{SRC}", "${SRC}") in cmake, f"{base}.cpp is part of the build"
    source = read(f"source/{base}.cpp")
    assert f'"{name}"' in source, f"{name} is registered by its config name"
    assert "CreatureSkillRegister" in source, f"{name} registers a factory"
for extra in ("creatureeffect/CreatureEffectAreaDamage", "creatureeffect/CreatureEffectTemporary",
              "creatureskill/CreatureSkillSummon", "entities/MissileBlast"):
    assert f"${{SRC}}/{extra}.cpp" in cmake, f"{extra}.cpp is part of the build"

# The missile type is known to the loader and the homing hook is used by the missile loop
missile = read("source/entities/MissileObject.cpp")
assert "MissileObjectType::blast" in missile and "MissileBlast::getMissileBlastFromStream" in missile
assert "MissileBlast::getMissileBlastFromPacket" in missile
assert "updateDirection();" in missile, "the missile loop calls the homing hook"
assert "blast" in read("source/entities/MissileObject.h")

# The creature helpers
creature_h = read("source/entities/Creature.h")
for decl in ("void teleportTo(Tile* tile);", "Tile* getWalkDestinationTile() const;", "bool takeCorpse();"):
    assert decl in creature_h, decl

# The config: the abilities come from the skill trees (creatureSkills.cfg); a type has them as its pre-skill or through
# the paths of its skill group. The creature lists keep only Melee and the MissileLaunch lines.
creatures = read("config/creatures.cfg")
blocks = {}
for block in re.findall(r"^\[Creature\]\n(.*?)^\[/Creature\]", creatures, re.M | re.S):
    blocks[re.search(r"^\s+Name\s+(\S+)", block, re.M).group(1)] = block
skill_config = read("config/creatureSkills.cfg")
skill_blocks = {}
for block in re.findall(r"^\[Skill\]\n(.*?)^\[/Skill\]", skill_config, re.M | re.S):
    skill_blocks[re.search(r"^Id\s+(\S+)", block, re.M).group(1)] = block


def base_line_of(skill_id):
    return re.search(r"^BaseLine\s+(.*?)\s*$", skill_blocks[skill_id], re.M).group(1)


# Every ability: the catalog skill that carries it, its class and the base line with the values of the ability
abilities = {
    "Whirlwind": ("VRM_1", "Whirlwind 14 1 2 8 3 3"),
    "Teleport": ("WRK_C1", "Teleport 7 0 8 8 30"),
    "GasCloud": ("WLD_1", "GasCloud 7 1 2 4 1.5 2 14.35 Examples/Smoke 9.57"),
    "HailStorm": ("DRK_1", "HailStorm 21 2 4 8 2 11 3.08 none 2.05"),
    "SkeletonArmy": ("UND_3", "SkeletonArmy 21 2 10 3 42 Skeleton"),
    "GuidedBolt": ("ARC_A2", "GuidedBolt 3 2 7 0 8 ArrowProjectile none 2 0 0 0 0 13 0.25 0 0 0 0 18.11 27.17"),
    "Grenade": ("ARC_A3", "Grenade 10 2 6 0 8 Cannonball none 1 0 0 0 0 5 0.1 2 0 0 0 0 6.97 10.46"),
    "RaiseDead": ("UND_1", "RaiseDead 24 2 10 4 3 42 Skeleton"),
}
for ability, (skill_id, line) in abilities.items():
    assert base_line_of(skill_id) == line, f"{skill_id} scales the {ability} line"
    assert len(line.split()) > 1

# Types that have an ability from level 1 carry it as their pre-skill
pre_skills = {"CaveHornet": "VRM_1", "Kobold": "WRK_C1", "DwarfWorker": "WRK_C1", "Slime": "WLD_1", "Dragon": "DRK_1",
              "DarkElf": "ARC_A2", "Elf": "ARC_A3", "Lich": "UND_1"}
for creature, skill_id in pre_skills.items():
    assert re.search(rf"^\s+PreSkill\s+{skill_id}$", blocks[creature], re.M), f"{creature} has pre-skill {skill_id}"

# The Elf and the DarkElf reach the other bow ability through the Bow path; the undead types have the skeleton skills
for creature in ("Elf", "DarkElf"):
    assert re.search(r"^\s+SkillGroup\s+archer$", blocks[creature], re.M), creature
for creature in ("Lich", "Skeleton"):
    assert re.search(r"^\s+SkillFamily\s+undead$", blocks[creature], re.M), creature

# The Dragon keeps its second attack line (the slow, strong missile) and has no ability lines in its list
dragon = blocks["Dragon"]
section = dragon[dragon.index("[CreatureSkills]"):dragon.index("[/CreatureSkills]")]
lines = [l.strip() for l in section.splitlines()[1:] if l.strip()]
missile_lines = [i for i, l in enumerate(lines) if not l.startswith("#") and l.split()[0] == "MissileLaunch"]
assert len(missile_lines) == 1 and "none\tMissileMagic\t1.7" in lines[missile_lines[0]]
comment = lines[missile_lines[0] - 1]
assert comment.startswith("#"), "the Dragon missile has a column comment"
assert len(comment.lstrip("# ").split()) == len(lines[missile_lines[0]].split()), "the Dragon missile column count"
for name in abilities:
    assert not re.search(rf"^\s+{name}\t", dragon, re.M), f"the Dragon list no longer has {name}"

print("ok")
