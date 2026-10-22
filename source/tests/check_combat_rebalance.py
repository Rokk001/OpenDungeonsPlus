#!/usr/bin/env python3
"""Check configured combat values, source paths and deterministic combat comparisons without compiling."""

import csv
from dataclasses import replace
import math
import os
from pathlib import Path
import random
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/balance"))
from combat_sim import Roster, building_stat, combat_stat, damage_bounds, duel_turns, evaluate, hit_chance, multiplier

# Approved level-one roster: health, healing, sleep, ratings, six damage endpoints and avoidance.
EXPECTED = """
Kobold 62 .041 0 562 188 3.21 4.07 0 0 0 0 none
DwarfWorker 62 .041 0 562 188 3.21 4.07 0 0 0 0 none
Rat 35.5 .0615 2.05 486 162 0 0 5.87 8.04 0 0 dodge
Orc 184.5 .0615 2.05 247 82 0 0 0 0 48.03 64.85 none
LavaSpawn 106.5 .0615 2.05 156 52 17.69 22.87 0 0 0 0 block
LizardMan 106.5 .0615 2.05 364 121 0 0 18.28 24.45 0 0 none
Goblin 61.5 .0615 2.05 109 36 9.16 12.22 0 0 0 0 parry
PitDemon 184.5 .0615 2.05 223 74 0 0 52.76 71.24 0 0 none
Roach 61.5 .041 2.05 440 147 0 0 0 0 9.19 12.28 none
Spider 35.5 .0615 2.05 402 134 7.19 9.85 0 0 0 0 none
Troll 184.5 .0615 2.05 261 87 44.2 59.68 0 0 0 0 none
Cultist 61.5 .0615 2.05 366 122 0 0 8.63 11.52 0 0 dodge
CaveHornet 35.5 .0615 2.05 344 115 0 0 0 0 5.83 8 dodge
Slime 35.5 .0615 2.05 500 167 0 0 5.26 7.22 0 0 dodge
Skeleton 106.5 .041 2.05 439 146 13.62 20.46 0 0 0 0 none
Lich 106.5 .041 2.05 205 68 0 0 21.91 25.21 0 0 none
Scarab 184.5 .0615 2.05 233 78 0 0 51.93 70.11 0 0 none
Adventurer 35.5 .0615 2.05 356 119 0 0 0 0 6.21 8.52 dodge
Monk 61.5 .0615 2.05 304 101 0 0 0 0 7.54 10.07 block
Dwarf1 35.5 .0615 2.05 407 136 7.01 9.6 0 0 0 0 none
Dwarf2 61.5 .0615 2.05 520 173 8.91 11.89 0 0 0 0 none
Knight 61.5 .0615 2.05 389 130 0 0 7.7 10.29 0 0 block
Wizard 106.5 .0615 2.05 341 114 0 0 18.36 24.56 0 0 none
DarkElf 106.5 .0615 2.05 352 117 0 0 0 0 16.58 22.18 none
Elf 106.5 .0615 2.05 397 132 0 0 0 0 19.8 26.5 none
RunelordDwarf 106.5 .0615 2.05 143 48 16.02 21.31 0 0 0 0 block
NatureMonster 184.5 .0615 2.05 75 25 0 0 0 0 38.46 51.93 block
Defender 184.5 .0615 2.05 264 88 45.54 61.48 0 0 0 0 parry
Wyvern 61.5 .0615 2.05 391 130 0 0 8.31 11.09 0 0 dodge
Gnome 35.5 .0615 2.05 529 176 0 0 5.7 7.81 0 0 dodge
TentacleAlbine 61.5 .0615 2.05 455 152 0 0 8.84 11.81 0 0 none
TentacleGreen 61.5 .0615 2.05 452 151 0 0 8.88 11.86 0 0 none
Dragon 184.5 .0615 2.05 270 90 0 0 0 0 32.07 43.29 none
Kreatur 106.5 .0615 2.05 398 133 0 0 17.66 23.63 0 0 none
"""
STAT_KEYS = ("MinHP", "Heal/Turn", "SleepHeal", "AttackRating", "DefenseRating")
RANGE_KEYS = ("PhyMin", "PhyMax", "MagMin", "MagMax", "EleMin", "EleMax")


# Read production text for explicit source wiring assertions.
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


# Verify all approved fields and optionally compare directly with a supplied values table.
def check_values(roster):
    approved = {}
    for line in EXPECTED.splitlines():
        words = line.split()
        if words:
            approved[words[0]] = (tuple(map(float, words[1:-1])), words[-1])
    values_path = os.environ.get("COMBAT_BALANCE_VALUES")
    if values_path:
        with open(values_path, newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        assert set(approved) == {row["Creature"] for row in rows}
        for row in rows:
            expected = tuple(float(row[key]) for key in ("MinHP", "HealPerTurn", "SleepHeal", "AttackRating", "DefenseRating") + RANGE_KEYS)
            assert approved[row["Creature"]] == (expected, row["Avoidance"]), row["Creature"]
            skill = roster.attack(row["Creature"])[0][0]
            assert skill == {"Melee": "Melee", "Missile": "MissileLaunch"}[row["SkillLine"]]
    for name, (numbers, avoidance) in approved.items():
        fields = roster.creatures[name][0]
        assert tuple(roster.number(fields, key) for key in STAT_KEYS) == numbers[:5], name
        attack, _, start = roster.attack(name)
        assert tuple(map(float, attack[start:start + 6])) == numbers[5:], name
        assert fields["Avoidance"][0] == avoidance, name
    # A fight between two equal creatures at level 10 lasts between 11.5 and 40 turns for every fighter
    # (200 fights each, one generator in Roster.fighters() order).
    rng = random.Random(99)
    for name in roster.fighters():
        turns = duel_turns(roster, roster.unit(name, 10), roster.unit(name, 10), 200, rng)
        assert 11.5 <= turns <= 40, (name, turns)
    assert len(approved) == 34


# Verify the curves numerically and tie every coefficient to the production header.
def check_curves(roster):
    header = read("source/entities/CreatureProgression.h")
    # The curve coefficients live in global.cfg; the header only holds the formulas and reads them.
    glob = read("config/global.cfg")
    for key, value in (("CreatureDamageGrowth", "0.221"), ("CreatureDamageExponent", "1.167"),
                       ("CreatureHpGrowthPerLevel", "0.018"), ("CooldownReductionPerLevel", "0")):
        found = re.findall(r"^\s*" + key + r"\s+(\S+)", glob, re.M)
        assert found == [value], (key, found)
    for constant in ("HP_GROWTH", "HP_EXPONENT", "DAMAGE_GROWTH", "DAMAGE_EXPONENT", "ATTACK_RATING_GROWTH",
                     "ATTACK_RATING_EXPONENT", "COOLDOWN_REDUCTION_PER_LEVEL"):
        assert constant not in header, constant
    body = function(header, "inline double damageMultiplier(")
    assert "getCreatureDamageGrowth() *" in body and "std::pow(" in body and "getCreatureDamageExponent()" in body
    assert "std::max(1u, std::min(MAX_POWER_LEVEL, level))" in body
    body = function(header, "inline double hpMultiplier(")
    assert "damageMultiplier(level) * (1.0 + ConfigManager::getSingleton().getCreatureHpGrowthPerLevel() * steps)" in body
    assert "std::max(1u, std::min(MAX_POWER_LEVEL, level))" in body
    assert "return std::max(1u, std::min(MAX_POWER_LEVEL, level))" in function(header, "inline double attackRatingMultiplier(")
    assert "getCooldownReductionPerLevel()" in function(header, "inline double cooldownAtLevel(")
    assert "return std::max(1u, std::min(MAX_POWER_LEVEL, level))" in function(header, "inline double defenseRatingMultiplier(")
    body = function(header, "inline double combatStat(")
    assert "level = std::max(1u, std::min(MAX_POWER_LEVEL, level))" in body
    assert "std::max(base + (level - 1) * perLevel, base * multiplier(level))" in body
    for level in (1, 5, 10, 20, 30):
        assert multiplier(level, "damage") == 1 + .221 * (level - 1) ** 1.167
        assert multiplier(level, "hp") == multiplier(level, "damage") * (1 + .018 * (level - 1))
        assert multiplier(level, "attack") == level
        assert multiplier(level, "defense") == level
        unit = roster.unit("Goblin", level)
        assert unit.hp == combat_stat(61.5, 1.25, level, "hp")
    for kind in ("hp", "damage", "attack", "defense"):
        assert multiplier(0, kind) == multiplier(1, kind)
        assert multiplier(999, kind) == multiplier(30, kind)
        assert combat_stat(10, 100, 999, kind) == max(2910, 10 * multiplier(30, kind))
    unit = roster.unit("Goblin")
    assert hit_chance(replace(unit, attack_rating=300), replace(unit, defense_rating=100)) == 75
    assert hit_chance(replace(unit, attack_rating=1, level=1), replace(unit, defense_rating=100000, level=30)) == 5
    assert hit_chance(replace(unit, attack_rating=100000, level=30), replace(unit, defense_rating=1, level=1)) == 95


# Compare the retained building columns with fixed pre-change damage examples.
def check_buildings(roster):
    expected = {"Troll": {1: 16.31, 5: 21.371724137931032, 10: 27.698879310344825},
                "Goblin": {1: 10.19, 5: 13.352413793103446, 10: 17.30543103448276}}
    for name, levels in expected.items():
        attack, start, _ = roster.attack(name)
        for level, wanted in levels.items():
            damage = sum(building_stat(float(attack[start + 2 * channel]) + float(attack[start + 2 * channel + 1]), float(attack[start + 2 * channel + 1]), level) for channel in range(3))
            assert math.isclose(damage, wanted, abs_tol=1e-9), (name, level, damage, wanted)
    rooms = read("config/rooms.cfg")
    assert re.search(r"^\s*DungeonHeartHP\s+10000\s*$", rooms, re.M)
    assert 'ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DungeonHeartHP", 10000.0)' in read("source/rooms/RoomDungeonTemple.cpp")
    assert re.search(r"DEFAULT_TILE_HP\s*=\s*10(?:\.0)?\s*;", read("source/entities/Building.cpp"))


# Tie numerical checks to actual hit, avoidance, damage, item and serialization paths.
def check_sources():
    creature = read("source/entities/Creature.cpp")
    hit = function(creature, "bool Creature::rollAttackHit(")
    assert hit.index("if(possessed)") < hit.index("Random::Double(0.0, 100.0)")
    assert "DefenceChance::hitChance(attackRating, getDefenseRating()," in hit
    hit_formula = function(read("source/entities/DefenceChance.h"), "inline double hitChance(")
    assert "HIT_SCALE * attackRating / (attackRating + defenseRating)" in hit_formula
    assert "attackerLevel / static_cast<double>(attackerLevel + defenderLevel)" in hit_formula
    assert "std::max(MIN_HIT_PERCENT, std::min(MAX_HIT_PERCENT, chance))" in hit_formula
    for key, value in (("HIT_SCALE", "200.0"), ("MIN_HIT_PERCENT", "5.0"), ("MAX_HIT_PERCENT", "95.0")):
        assert key + " = " + value in read("source/entities/DefenceChance.h")
    defence = function(creature, "DefenceChance::Outcome Creature::rollMeleeDefence(")
    for needle in ("getMeleeDodgeParry()", "getIsOnServerMap()", "isKo()", "mIsInHand", "mIsBeingDragged", "isPossessed()",
                   "CreatureDefinition::Avoidance::dodge", "CreatureDefinition::Avoidance::parry", "CreatureDefinition::Avoidance::block && hasShield",
                   "missile && avoidance == CreatureDefinition::Avoidance::parry"):
        assert needle in defence, needle
    assert defence.count("Random::Double(0.0, 100.0)") == 1
    melee = function(read("source/creatureskill/CreatureSkillMeleeFight.cpp"), "bool CreatureSkillMeleeFight::tryUseFight(")
    assert melee.index("rollAttackHit(") < melee.index("rollMeleeDefence(false)") < melee.index("CombatDamage::roll(") < melee.index("takeDamage(")
    assert "if(!missed && defence == DefenceChance::none)" in melee
    assert melee.count("CreatureProgression::stat(") == 3
    assert "takeDamage(creature, creatureDamage," in melee
    launch = function(read("source/creatureskill/CreatureSkillMissileLaunch.cpp"), "bool CreatureSkillMissileLaunch::tryUseFight(")
    assert launch.count("CreatureProgression::stat(") == 3
    assert "CombatDamage::scale(" in launch and "setCreatureDamageRange(" in launch
    assert "setCreatureShot(creature->isPossessed())" in launch
    assert "rollAttackHit(" not in launch and "rollMeleeDefence(" not in launch
    guided = function(read("source/creatureskill/CreatureSkillGuidedBolt.cpp"), "MissileOneHit* CreatureSkillGuidedBolt::createMissile(")
    assert "MissileBlast(" in guided and "0.0, true)" in guided and "setShooter(" in guided
    assert "CreatureSkillMissileLaunch" in read("source/creatureskill/CreatureSkillGuidedBolt.h")
    assert "return mBlastRadius <= 0.0;" in read("source/entities/MissileBlast.h")
    missile = read("source/entities/MissileOneHit.cpp")
    hurt = function(missile, "void MissileOneHit::hurt(")
    assert "isCreatureShot() && usesCreatureHitRoll()" in hurt
    assert hurt.index("rollAttackHit(") < hurt.index("rollMeleeDefence(true)") < hurt.index("CombatDamage::roll(")
    assert "mHasCreatureDamageRange && entity->getObjectType() == GameEntityType::creature" in hurt
    assert "takeDamage(this, damage, 0.0, 0.0, 0.0" in hurt
    assert "takeDamage(this, 0.0, mPhysicalDamage, mMagicalDamage, mElementDamage" in hurt
    for signature in ("void MissileOneHit::exportToStream(", "bool MissileOneHit::importFromStream("):
        body = function(missile, signature)
        assert body.index("CreatureDamageRange") < body.index("ShotAccuracy"), signature
    roller = function(read("source/entities/CombatDamage.h"), "inline double roll(")
    assert roller.count("Random::Double(0.0, 1.0)") == 1
    for channel in ("Physical", "Magical", "Element"):
        assert roller.count("target.get" + channel + "Defense()") == 2
    assert "return lo + u * (hi - lo)" in roller
    definition = read("source/entities/CreatureDefinition.cpp")
    for key in ("AttackRating", "DefenseRating", "Avoidance"):
        assert 'nextParam == "' + key + '"' in definition
        assert '"    ' + key + '\\t"' in definition
    for signature in ("ODPacket& operator<<(ODPacket& os, const CreatureDefinition* c)",
                      "ODPacket& operator>>(ODPacket& is, CreatureDefinition* c)"):
        body = function(definition, signature)
        assert "mAttackRating" in body and "mDefenseRating" in body and "mAvoidance" in body
    for key in ("AttackRating", "DefenseRating"):
        getter = function(creature, "double Creature::get" + key + "() const")
        assert "mWeaponL->get" + key + "()" in getter and "mWeaponR->get" + key + "()" in getter
    for filename in ("CreatureSkillMeleeFight.cpp", "CreatureSkillMissileLaunch.cpp"):
        skill = read("source/creatureskill/" + filename)
        assert "mPhyMin = mPhyMax = mPhyAtk + mPhyAtkPerLvl" in skill
        assert "CombatDamage::readRange(" in skill
    grenade = read("source/creatureskill/CreatureSkillGrenade.cpp")
    assert grenade.index("if(!(is >> mBlastRadius))") < grenade.index("CombatDamage::readRange(")


# Verify all absolute damage ranges and their per-application production rolls.
def check_other_damage(roster):
    expected = {
        "spells": {"LightningDamageMin": 20.5, "LightningDamage": 30.75, "TremorDamageMin": 13.67,
                   "TremorDamage": 20.5, "InfernoDamagePerTurnMin": 39.05, "InfernoDamagePerTurn": 58.57,
                   "CreatureHealValue": 10.25},
        "rooms": {"PrisonDamagePerTurnMin": .082, "PrisonDamagePerTurn": .123, "DungeonHeartHP": 10000,
                  "HatcheryHpRecoveredPerChicken": 10.25, "HatcheryGiftHpRecoveredPerChicken": 4.1},
        "traps": {"BoulderDamagePerHitMin": 205, "BoulderDamagePerHitMax": 246,
                  "CannonDamagePerHitMin": 20.5, "CannonDamagePerHitMax": 30.75,
                  "SpikeDamagePerHitMin": 20.5, "SpikeDamagePerHitMax": 30.75,
                  "GasDamagePerHitMin": 27.34, "GasDamagePerHitMax": 41,
                  "LightningDamagePerHitMin": 15.04, "LightningDamagePerHitMax": 22.55,
                  "FireburstDamagePerHitMin": 75.17, "FireburstDamagePerHitMax": 112.75,
                  "RunedDoorDamageMin": 20.5, "RunedDoorDamage": 30.75},
    }
    for filename, fields in expected.items():
        text = read("config/" + filename + ".cfg")
        for key, value in fields.items():
            found = re.findall(r"^\s*" + key + r"\s+(\S+)", text, re.M)
            assert len(found) == 1 and float(found[0]) == value, (filename, key, found)
    for filename, key in (("spells/SpellLightning.cpp", "LightningDamageMin"),
                          ("spells/SpellTremor.cpp", "TremorDamageMin"),
                          ("spells/SpellInferno.cpp", "InfernoDamagePerTurnMin"),
                          ("rooms/RoomPrison.cpp", "PrisonDamagePerTurnMin"),
                          ("traps/TrapDoor.cpp", "RunedDoorDamageMin")):
        text = read("source/" + filename)
        assert key in text, filename
        assert "Random::Double(" in text or "effect->setDamageMin(damagePerTurnMin)" in text, filename
    door = function(read("source/traps/TrapDoor.cpp"), "bool TrapDoor::shoot(")
    assert door.index("for(GameEntity* target : enemyCreatures)") < door.index("Random::Double(damageMin, damageMax)")
    for effect in ("AreaDamage", "Burn", "Explosion"):
        text = read("source/creatureeffect/CreatureEffect" + effect + ".cpp")
        assert "Random::Double(" in function(text, "void CreatureEffect" + effect + "::applyEffect(")
        assert "DamageRangeMin" in text and "CombatDamage::readEffectMinimum(" in text
    for name, (fields, _) in roster.equipment.items():
        for channel in ("Physical", "Magical", "Element"):
            maximum = roster.number(fields, channel + "Damage")
            if "shield" not in name.lower():
                assert roster.number(fields, channel + "DamageMin") == math.ceil(maximum * 2 / 3 * 100 - 1e-9) / 100, (name, channel)
        assert roster.number(fields, "AttackRating") == 0 and roster.number(fields, "DefenseRating") == 0
    champion = roster.creatures["Champion"][0]
    assert roster.number(champion, "AttackRating") == 300 and roster.number(champion, "DefenseRating") == 100
    attack, _, start = roster.attack("Champion")
    assert tuple(map(float, attack[start:start + 6])) == (54.67, 82, 0, 0, 0, 0)


# Verify deterministic simulation thresholds without adjusting the approved roster.
def check_simulation(roster):
    result = evaluate(roster)
    for tier, names in result["tiers"].items():
        for name in names:
            assert abs(result["averages"][name] - result["tier_means"][tier]) <= .08, ("tier spread", tier, name, result["averages"][name], result["tier_means"][tier])
    means = list(result["tier_means"].values())
    assert all(first < second for first, second in zip(means, means[1:])), result["tier_means"]
    for name, outcomes in result["levels"].items():
        assert outcomes["10_vs_3x5"] >= .5, (name, outcomes)
        assert outcomes["30_vs_3x15"] >= .75, (name, outcomes)
        assert outcomes["1_vs_10"] <= .10 and outcomes["5_vs_10"] <= .10, (name, outcomes)
    for name in roster.fighters():
        if roster.number(roster.creatures[name][0], "FeeBase") > 200:
            continue
        for worker in ("Kobold", "DwarfWorker"):
            target = roster.unit(worker)
            assert damage_bounds(roster.unit(name), target)[1] < target.hp, (name, worker)
    print("Simulation: 32 fighters, 150 seeded duels per pair, 60 fights per level comparison")


# Execute the checks as pure Python; production C++ is inspected, never compiled.
def main():
    roster = Roster(ROOT)
    check_values(roster)
    check_curves(roster)
    check_buildings(roster)
    check_sources()
    check_other_damage(roster)
    check_simulation(roster)
    print("check_combat_rebalance: ok")


if __name__ == "__main__":
    main()
