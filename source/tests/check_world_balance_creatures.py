#!/usr/bin/env python3
"""Check the creature strength balance: creature table, level-file classes, growth curves, avoidance, fractional
timers, SkillDamageFactor and the 1-versus-2 fight criterion. Pure Python; production C++ is inspected, never compiled."""

from decimal import Decimal, ROUND_HALF_UP
import json
import math
from pathlib import Path
import random
import re
import statistics
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/balance"))
import combat_sim
from combat_sim import Roster, fight_group

# Creature table: type, FeeBase, FeePerLevel, MinHP, attack line, the six damage columns of that line
# (phyMin phyMax magMin magMax eleMin eleMax) and the SkillDamageFactor of the type.
TABLE = """
Adventurer 50 8 35.5 Melee 0 0 0 0 6.21 8.52 1.0303
CaveHornet 50 8 35.5 Melee 0 0 0 0 5.83 8 0.9498
Dwarf1 50 8 35.5 Melee 7.01 9.6 0 0 0 0 1.0243
Gnome 50 8 35.5 Melee 0 0 5.7 7.81 0 0 1.0134
Rat 50 8 35.5 Melee 0 0 5.87 8.04 0 0 1.0191
Slime 50 8 35.5 Melee 0 0 5.26 7.22 0 0 0.922
Spider 50 8 35.5 Melee 7.19 9.85 0 0 0 0 1.0478
Cultist 100 16 61.5 Melee 0 0 8.63 11.52 0 0 0.9773
Dwarf2 100 16 61.5 Melee 8.91 11.89 0 0 0 0 0.9952
Goblin 100 16 61.5 Melee 9.16 12.22 0 0 0 0 1.061
Knight 100 16 61.5 Melee 0 0 7.7 10.29 0 0 0.9226
Monk 100 16 61.5 Melee 0 0 0 0 7.54 10.07 0.9145
Roach 100 16 61.5 Melee 0 0 0 0 9.19 12.28 0.9988
TentacleAlbine 100 16 61.5 Melee 0 0 8.84 11.81 0 0 1.0282
TentacleGreen 100 16 61.5 Melee 0 0 8.88 11.86 0 0 1.0304
Wyvern 100 16 61.5 Melee 0 0 8.31 11.09 0 0 0.9653
DarkElf 200 32 106.5 MissileLaunch 0 0 0 0 16.58 22.18 0.9845
Elf 200 32 106.5 MissileLaunch 0 0 0 0 19.8 26.5 0.9741
Kreatur 200 32 106.5 MissileLaunch 0 0 17.66 23.63 0 0 0.9699
LavaSpawn 200 32 106.5 Melee 17.69 22.87 0 0 0 0 0.9125
Lich 200 32 106.5 MissileLaunch 0 0 21.91 25.21 0 0 1.036
LizardMan 200 32 106.5 MissileLaunch 0 0 18.28 24.45 0 0 0.9614
RunelordDwarf 200 32 106.5 Melee 16.02 21.31 0 0 0 0 0.9636
Skeleton 200 32 106.5 Melee 13.62 20.46 0 0 0 0 0.9972
Wizard 200 32 106.5 MissileLaunch 0 0 18.36 24.56 0 0 0.945
Defender 400 64 184.5 Melee 45.54 61.48 0 0 0 0 1.0575
Dragon 400 64 184.5 Melee 0 0 0 0 32.07 43.29 0.6029
NatureMonster 400 64 184.5 Melee 0 0 0 0 38.46 51.93 0.923
Orc 400 64 184.5 Melee 0 0 0 0 48.03 64.85 0.8813
PitDemon 400 64 184.5 Melee 0 0 52.76 71.24 0 0 0.9146
Scarab 400 64 184.5 Melee 0 0 51.93 70.11 0 0 0.9075
Troll 400 64 184.5 Melee 44.2 59.68 0 0 0 0 0.9783
"""

# Level-file creature classes with their own MinHP: file, class, MinHP, FeeBase, FeePerLevel, SkillDamageFactor and the
# multiplier that was applied to every damage column of every Melee and MissileLaunch line of the class.
LEVEL_CLASSES = (
    ("levels/campaign/Bonus1.level", "DragonBoss", "153.8", "0", "0", "0.6029", "2.1890"),
    ("levels/skirmish/TestSingleplayerSmall.level", "DragonBoss", "153.8", "0", "0", "0.6029", "2.1890"),
    ("levels/multiplayer/GreedOrMight.level", "BossDragon", "107.6", "0", "0", "0.6029", "2.1890"),
    ("levels/multiplayer/RuinsOfTheConfluent.level", "VeteranScarab", "153.8", "300", "48", "0.9075", "3.5447"),
)

# Six damage columns (min/max pairs) of the Melee and MissileLaunch lines of the level-file classes before the
# change, in line order; the check recomputes the new values from them (rounded half up to 2 decimals).
LEVEL_OLD_RANGES = {
    ("levels/campaign/Bonus1.level", "DragonBoss"): (
        ("MissileLaunch", "3.42 5.13 3.42 5.13 2.05 3.08"), ("Melee", "16.68 25.01 0 0 0 0")),
    ("levels/skirmish/TestSingleplayerSmall.level", "DragonBoss"): (
        ("MissileLaunch", "3.42 5.13 3.42 5.13 2.05 3.08"), ("Melee", "16.68 25.01 0 0 0 0")),
    ("levels/multiplayer/GreedOrMight.level", "BossDragon"): (("Melee", "19.14 28.7 9.57 14.35 0 0"),),
    ("levels/multiplayer/RuinsOfTheConfluent.level", "VeteranScarab"): (("Melee", "0 0 22.3 33.44 0 0"),),
}

# Level-file classes: MinHP before the change (the new value is MinHP x 1.5 rounded half up to 1 decimal).
LEVEL_OLD_MINHP = {"DragonBoss": "102.5", "BossDragon": "71.75", "VeteranScarab": "102.5"}

# Weapon parry values after the change: own ParryBase -> ParryMax (ParryBase = min(max, old base + 15 x old step)).
PARRY_AFTER = {"10.5": "15", "5.25": "7.5"}


# Read production text for explicit source assertions.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Extract a complete production function with balanced braces.
def function(text, signature):
    start = text.index(signature)
    cursor = text.index("{", start) + 1
    depth = 1
    while depth:
        depth += (text[cursor] == "{") - (text[cursor] == "}")
        cursor += 1
    return text[start:cursor]


# Parse the creature table into one dictionary per type.
def table_rows():
    rows = {}
    for line in TABLE.splitlines():
        words = line.split()
        if words:
            rows[words[0]] = {"fee_base": words[1], "fee_per_level": words[2], "min_hp": words[3], "attack": words[4],
                              "damage": words[5:11], "factor": words[11]}
    return rows


# Compare two numbers given as text.
def same(first, second):
    return math.isclose(float(first), float(second), abs_tol=1e-9)


# The creature values of config/creatures.cfg equal the table (MinHP, fee, damage columns, SkillDamageFactor).
def check_creature_table(roster):
    rows = table_rows()
    assert len(rows) == 32
    for name, row in rows.items():
        fields = roster.creatures[name][0]
        assert same(fields["MinHP"][0], row["min_hp"]), (name, "MinHP")
        assert same(fields["FeeBase"][0], row["fee_base"]), (name, "FeeBase")
        assert same(fields["FeePerLevel"][0], row["fee_per_level"]), (name, "FeePerLevel")
        assert same(fields["SkillDamageFactor"][0], row["factor"]), (name, "SkillDamageFactor")
        words, _, start = roster.attack(name)
        assert words[0] == row["attack"], (name, "attack line")
        assert len(words) >= start + 6, (name, "damage columns")
        for index in range(6):
            assert same(words[start + index], row["damage"][index]), (name, "damage column", index)
    for worker in ("Kobold", "DwarfWorker"):
        assert same(roster.creatures[worker][0]["MinHP"][0], "70"), worker
    champion = roster.creatures["Champion"][0]
    assert "SkillDamageFactor" not in champion


# The level-file classes follow the base type: MinHP x 1.5, damage columns x the damage multiplier, fee and factor.
def check_level_classes():
    for path, name, min_hp, fee_base, fee_per_level, factor, multiplier in LEVEL_CLASSES:
        text = read(path)
        block = text[text.index("Name\t" + name):]
        block = block[:block.index("[/Creature]")]
        values = {}
        lines = {}
        for line in block.splitlines():
            words = line.split()
            if words and not words[0].startswith("#"):
                values.setdefault(words[0], words[1:])
                lines.setdefault(words[0], []).append(words[1:])
        assert values["MinHP"][0] == min_hp, (path, name, "MinHP")
        expected_hp = (Decimal(LEVEL_OLD_MINHP[name]) * Decimal("1.5")).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
        assert Decimal(min_hp) == expected_hp, (path, name, "MinHP rule")
        assert values["FeeBase"][0] == fee_base and values["FeePerLevel"][0] == fee_per_level, (path, name, "fee")
        assert Decimal(fee_per_level) == (Decimal("0.16") * Decimal(fee_base)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        assert values["SkillDamageFactor"][0] == factor, (path, name, "SkillDamageFactor")
        found = [(key, words[-6:]) for key in ("MissileLaunch", "Melee") for words in lines.get(key, [])]
        wanted = LEVEL_OLD_RANGES[(path, name)]
        assert len(found) == len(wanted), (path, name, "attack lines")
        for (key, columns), (old_key, old_columns) in zip(sorted(found), sorted(wanted)):
            assert key == old_key, (path, name)
            for new, old in zip(columns, old_columns.split()):
                expected = (Decimal(old) * Decimal(multiplier)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                assert same(new, expected), (path, name, key, new, expected)


# The curve coefficients, the avoidance values and the weapon parry values of the configuration.
def check_global_and_equipment():
    glob = read("config/global.cfg")
    wanted = (("CreatureDamageGrowth", "0.221"), ("CreatureDamageExponent", "1.167"), ("CreatureHpGrowthPerLevel", "0.018"),
              ("CooldownReductionPerLevel", "0"), ("DodgeBase", "10.5"), ("DodgePerLevel", "0"), ("ParryBase", "10.5"),
              ("ParryPerLevel", "0"), ("ShieldBlockBase", "21"), ("ShieldBlockPerLevel", "0"), ("DodgeMax", "15"),
              ("ParryMax", "15"), ("ShieldBlockMax", "25"))
    for key, value in wanted:
        found = re.findall(r"^\s*" + key + r"\s+(\S+)", glob, re.M)
        assert found == [value], (key, found)
    equipment = read("config/equipments.cfg")
    bases = re.findall(r"^\s*ParryBase\s+(\S+)", equipment, re.M)
    steps = re.findall(r"^\s*ParryPerLevel\s+(\S+)", equipment, re.M)
    maxima = re.findall(r"^\s*ParryMax\s+(\S+)", equipment, re.M)
    assert len(bases) == len(steps) == len(maxima) and bases
    for base, step, maximum in zip(bases, steps, maxima):
        assert step == "0" and PARRY_AFTER[base] == maximum, (base, step, maximum)
    # The mirror constants of the simulator equal the configuration.
    assert combat_sim.DAMAGE_GROWTH == 0.221 and combat_sim.DAMAGE_EXPONENT == 1.167
    assert combat_sim.HP_GROWTH_PER_LEVEL == 0.018 and combat_sim.COOLDOWN_REDUCTION_PER_LEVEL == 0.0
    for level, damage, health in ((1, 1.0, 1.0), (10, 3.871, 4.498), (20, 7.866, 10.556), (30, 12.246, 18.639)):
        assert abs(combat_sim.multiplier(level, "damage") - damage) < 0.0006, level
        assert abs(combat_sim.multiplier(level, "hp") - health) < 0.0006, level
        assert combat_sim.multiplier(level, "attack") == level


# The header holds the formulas only, the fractions of the timers and effects are kept, the new field is wired.
def check_sources():
    header = read("source/entities/CreatureProgression.h")
    for constant in ("HP_GROWTH", "DAMAGE_GROWTH", "ATTACK_RATING_GROWTH", "COOLDOWN_REDUCTION_PER_LEVEL"):
        assert constant not in header, constant
    config = read("source/utils/ConfigManager.cpp")
    for key in ("CreatureDamageGrowth", "CreatureDamageExponent", "CreatureHpGrowthPerLevel", "CooldownReductionPerLevel"):
        assert 'nextParam == "' + key + '"' in config, key
    creature = read("source/entities/Creature.cpp")
    upkeep = creature[creature.index("// The creature skills keep recovering while the player controls the creature"):]
    upkeep = upkeep[:upkeep.index("decidePrioritaryAction();")]
    assert upkeep.count("skillData.mCooldown -= 1.0;") == 2 and upkeep.count("skillData.mWarmup -= 1.0;") == 2
    assert "std::max(0.0, skillData.mCooldown - 1.0)" not in upkeep
    assert upkeep.count("skillData.mCooldown += ") == 1 and upkeep.count("skillData.mWarmup += ") == 1
    use = function(creature, "void Creature::useAttack(")
    assert "skillData.mCooldown += getAppliedCooldownNbTurns(*skillData.mSkill);" in use
    assert "skillData.mWarmup += skillData.mSkill->getWarmupNbTurns();" in use
    assert "double mWarmup;" in read("source/entities/Creature.h")
    assert "(skillData.mCooldown <= 0.0) && (skillData.mWarmup <= 0.0)" in creature
    effect = read("source/creatureeffect/CreatureEffect.cpp")
    body = function(effect, "bool CreatureEffect::upkeepEffect(")
    assert "mTurnFraction = std::min(1.0, mNbTurnsEffect);" in body
    assert "mNbTurnsEffect = std::max(0.0, mNbTurnsEffect - 1.0);" in body
    assert "double mNbTurnsEffect;" in read("source/creatureeffect/CreatureEffect.h")
    for name in ("AreaDamage", "Burn", "Explosion", "Heal"):
        text = read("source/creatureeffect/CreatureEffect" + name + ".cpp")
        assert "getTurnFraction()" in function(text, "void CreatureEffect" + name + "::applyEffect("), name
    definition = read("source/entities/CreatureDefinition.cpp")
    assert 'nextParam == "SkillDamageFactor"' in definition and '"    SkillDamageFactor\\t"' in definition
    for signature in ("ODPacket& operator<<(ODPacket& os, const CreatureDefinition* c)",
                      "ODPacket& operator>>(ODPacket& is, CreatureDefinition* c)"):
        assert "mSkillDamageFactor" in function(definition, signature)
    assert "inline double               getSkillDamageFactor" in read("source/entities/CreatureDefinition.h")
    assert "getSkillDamageFactor()" in function(read("source/creatureskill/CreatureSkillExplosion.cpp"),
                                                "bool CreatureSkillExplosion::tryUseFight(")
    assert "getSkillDamageFactor()" in function(read("source/creatureskill/CreatureSkillAreaDamage.cpp"),
                                                "bool CreatureSkillAreaDamage::tryUseFight(")
    launch = function(read("source/creatureskill/CreatureSkillMissileLaunch.cpp"), "bool CreatureSkillMissileLaunch::tryUseFight(")
    assert "appliesSkillDamageFactor() ? creature->getDefinition()->getSkillDamageFactor() : 1.0" in launch
    assert "appliesSkillDamageFactor() const override" in read("source/creatureskill/CreatureSkillGrenade.h")
    assert "appliesSkillDamageFactor() const override" in read("source/creatureskill/CreatureSkillGuidedBolt.h")
    assert "appliesSkillDamageFactor() const override" not in read("source/creatureskill/CreatureSkillMissileLaunch.h")


# One creature of twice the wage against two of half the wage, and the level-group criteria (procedure of the plan:
# one generator, levels 1, 10, 30; classes 100, 200, 400; 200 fights per pairing).
def check_fights(roster):
    names = roster.fighters()
    wage = {name: roster.number(roster.creatures[name][0], "FeeBase") for name in names}
    rng = random.Random(99)
    means = {}
    for level in (1, 10, 30):
        units = {name: roster.unit(name, level) for name in names}
        for high in (100, 200, 400):
            shares = [fight_group(roster, units[first], units[second], 2, 200, rng)
                      for first in names if wage[first] == high for second in names if wage[second] == high // 2]
            means[(level, high)] = statistics.mean(shares)
            assert 0.35 <= means[(level, high)] <= 0.65, (level, high, means[(level, high)])
    for name in names:
        share = fight_group(roster, roster.unit(name, 10), roster.unit(name, 5), 3, 200, rng)
        assert share >= 0.5, (name, "level 10 against 3 x level 5", share)
    for name in names:
        share = fight_group(roster, roster.unit(name, 30), roster.unit(name, 15), 3, 200, rng)
        assert share >= 0.85, (name, "level 30 against 3 x level 15", share)
    print("class means " + json.dumps({"L%d/%d" % key: round(value, 3) for key, value in means.items()}))


# Execute all checks.
def main():
    roster = Roster(ROOT)
    check_creature_table(roster)
    check_level_classes()
    check_global_and_equipment()
    check_sources()
    check_fights(roster)
    print("check_world_balance_creatures: ok")


if __name__ == "__main__":
    main()
