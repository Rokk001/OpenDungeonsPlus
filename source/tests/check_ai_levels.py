"""Check AI level values, order, factory cases and damage calculation."""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

repo = Path(__file__).resolve().parents[2]
EXPECTED = {'Rho': ['12', '15', '20', '25.433', '30'], 'Pi': ['0.4', '0.55', '0.75', '0.909', '0.99'], 'ScanPeriod': ['120', '80', '45', '24.834', '10'], 'ClickShare': ['0.3', '0.42', '0.6', '0.806', '1.0'], 'MistakeMultiplier': ['4.555556', '3.444444', '2.333333', '1.944444', '0.555556'], 'EstimateNoise': ['0.206', '0.164', '0.132', '0.106', '0.049'], 'TacticTemperature': ['2.0', '0.7', '0.45', '0.4', '0.35'], 'AttackAdvantage': ['-1.2', '-1.15', '-1.1', '-1.05', '-1.0'], 'FocusFire': ['0.62', '0.698', '0.758', '0.807', '0.914'], 'RetreatThreshold': ['0.603', '0.661', '0.706', '0.743', '0.823'], 'TunnelDetour': ['0.215', '0.176', '0.146', '0.122', '0.068'], 'TacticPriorAllin': ['0.34', '0.33', '0.32', '0.31', '0.3'], 'TacticPriorSingle': ['0.58', '0.465', '0.35', '0.23', '0.12'], 'TacticPriorSplit': ['0.04', '0.12', '0.2', '0.25', '0.3'], 'TacticPriorRaid': ['0.01', '0.015', '0.02', '0.025', '0.03'], 'TacticPriorCounter': ['0.03', '0.07', '0.11', '0.185', '0.25'], 'EnemyManaEstimate': ['own', 'own', 'own', 'own', 'observed']}

config = (repo / "config/ai.cfg").read_text(encoding="utf-8")
section = config.split("[KeeperAILevels]", 1)[1].split("[/KeeperAILevels]", 1)[0]
rows = {}
for line in section.splitlines():
    fields = line.split("#", 1)[0].split()
    if fields:
        assert fields[0] not in rows, f"duplicate {fields[0]}"
        rows[fields[0]] = fields[1:]
assert set(rows) == set(EXPECTED), "level keys differ"
for key, expected in EXPECTED.items():
    assert len(rows[key]) == 5, key
    if key == "EnemyManaEstimate":
        assert rows[key] == expected, key
    else:
        assert [float(v) for v in rows[key]] == [float(v) for v in expected], key
for key in ("Rho", "Pi", "ClickShare", "AttackAdvantage", "FocusFire", "RetreatThreshold"):
    values = [float(v) for v in rows[key]]
    assert values == sorted(values), key
for key in ("ScanPeriod", "MistakeMultiplier", "EstimateNoise", "TacticTemperature", "TunnelDetour"):
    values = [float(v) for v in rows[key]]
    assert values == sorted(values, reverse=True), key
for i in range(5):
    assert abs(sum(float(rows["TacticPrior" + suffix][i]) for suffix in ("Allin", "Single", "Split", "Raid", "Counter")) - 1) < 1e-9
noticed_cycles = [float(rho) * float(pi) for rho, pi in zip(rows["Rho"], rows["Pi"])]
assert noticed_cycles == sorted(noticed_cycles), "Rho x Pi"
factory = (repo / "source/ai/AIFactory.cpp").read_text(encoding="utf-8")
for level in ("easy", "medium", "normal", "hard", "hell"):
    assert re.search(r"case\s+KeeperAIType::" + level + r"\s*:", factory), level
assert "## Not built" in (repo / "docs/development/AI-LEVELS.md").read_text(encoding="utf-8")

# Compile the actual raw-DPS function with level-one configured attack stubs.
sys.path.insert(0, str(repo / "tools/balance"))
from combat_sim import Roster
roster = Roster(repo)
single_section = config.split("[KeeperAI]", 1)[1].split("[/KeeperAI]", 1)[0]
hit_match = re.search(r"^\s*RawHitFactor\s+(\S+)", single_section, re.M)
assert hit_match, "missing RawHitFactor"
hit_factor = float(hit_match.group(1))
creature_source = (repo / "source/entities/Creature.cpp").read_text(encoding="utf-8")
match = re.search(r"double Creature::getRawDamagePerSecond\(\) const\s*\{", creature_source)
assert match, "missing raw damage getter"
start = match.end() - 1
end = start + 1
depth = 1
while depth and end < len(creature_source):
    depth += (creature_source[end] == "{") - (creature_source[end] == "}")
    end += 1
assert depth == 0
function = creature_source[match.start():end]

cases = []
for name in ("Goblin", "Troll", "Wizard"):
    fields = roster.creatures[name][0]
    items = [roster.equipment[item][0] for item in
             (fields.get("WeaponSpawnL", ["none"])[0], fields.get("WeaponSpawnR", ["none"])[0])
             if item != "none"]
    section = re.search(r"\[CreatureSkills\](.*?)\[/CreatureSkills\]", roster.creatures[name][1], re.S)
    assert section, name
    attacks = []
    for line in section[1].splitlines():
        attack = line.split()
        if not attack or attack[0] not in ("Melee", "MissileLaunch"):
            continue
        old, ranges, level_index = (4, 10, 3) if attack[0] == "Melee" else (9, 15, 5)
        minimum = maximum = 0.0
        for index, channel in enumerate(("Physical", "Magical", "Element")):
            legacy = float(attack[old + 2 * index]) + float(attack[old + 2 * index + 1])
            low = float(attack[ranges + 2 * index]) if len(attack) >= ranges + 6 else legacy
            high = float(attack[ranges + 2 * index + 1]) if len(attack) >= ranges + 6 else legacy
            minimum += low + sum(roster.number(item, channel + "DamageMin", roster.number(item, channel + "Damage")) for item in items)
            maximum += high + sum(roster.number(item, channel + "Damage") for item in items)
        skill_cooldown = float(attack[1])
        weapon_cooldown = max((roster.number(item, "CooldownNbTurns") for item in items), default=0) if attack[0] == "Melee" else 0
        cooldown = max(skill_cooldown, weapon_cooldown)
        factor = weapon_cooldown / skill_cooldown if weapon_cooldown > skill_cooldown > 0 else 1
        kind = "CreatureSkillMeleeFight" if attack[0] == "Melee" else "CreatureSkillMissileLaunch"
        attacks.append((kind, minimum * factor, maximum * factor, cooldown, int(attack[level_index]) <= 1))
    unit = roster.unit(name, 1)
    expected = hit_factor * 0.5 * (sum(unit.minimum) + sum(unit.maximum)) / max(1, unit.cooldown) * 1.4
    cases.append((attacks, expected))

stub = r'''#include <algorithm>
#include <cmath>
#include <vector>
struct Creature;
struct CreatureSkill { virtual ~CreatureSkill() = default; virtual bool canBeUsedBy(const Creature*) const { return usable; } double lo, hi, cooldown; bool usable; };
struct CreatureSkillMeleeFight : CreatureSkill { void getCreatureDamageRange(const Creature&, double& a, double& b) const { a=lo; b=hi; } };
struct CreatureSkillMissileLaunch : CreatureSkill { void getCreatureDamageRange(const Creature&, double& a, double& b) const { a=lo; b=hi; } };
struct CreatureSkillData { CreatureSkill* mSkill; };
bool isLevelScaledAttack(const CreatureSkill&) { return true; }
struct ConfigManager { static ConfigManager& getSingleton() { static ConfigManager c; return c; } double getAiConfigDouble(const char*) const { return HIT_FACTOR; } };
struct ODApplication { static constexpr double turnsPerSecond = 1.4; };
struct Creature { std::vector<CreatureSkillData> mSkillData; double getAppliedCooldownNbTurns(const CreatureSkill& s) const { return s.cooldown; } double getRawDamagePerSecond() const; };
'''.replace("HIT_FACTOR", repr(hit_factor))
main = "int main() {\n"
for index, (attacks, expected) in enumerate(cases):
    main += f"  Creature c{index};\n"
    for slot, (kind, low, high, cooldown, usable) in enumerate(attacks):
        skill = f"s{index}_{slot}"
        main += (f"  {kind} {skill}; {skill}.lo={low!r}; {skill}.hi={high!r}; "
                 f"{skill}.cooldown={cooldown!r}; {skill}.usable={str(usable).lower()};\n"
                 f"  c{index}.mSkillData.push_back({{&{skill}}});\n")
    main += f"  if (std::abs(c{index}.getRawDamagePerSecond() - {expected!r}) > std::abs({expected!r}) * 0.01) return {index + 1};\n"
main += "  return 0;\n}\n"
with tempfile.TemporaryDirectory(prefix="odp-ai-dps-") as directory:
    work = Path(directory)
    (work / "check.cpp").write_text(stub + function + "\n" + main, encoding="utf-8")
    subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++17", "check.cpp", "/Fecheck.exe"], cwd=work, check=True)
    subprocess.run([str(work / "check.exe")], cwd=work, check=True)
print("OK")
