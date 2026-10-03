"""Check the spell mana costs, cooldowns and the worker price rule.

The costs use one own scale (mana cap 200,000, prices in 50 mana steps, see docs/development/VALUE-SCALES.md):
Summon worker 1,400 per step, Call to war 9,200, Heal 5,400, Eye of evil 4,600, Lightning 6,600,
Tremor 27,600, Defector 21,600, Hexen hen 10,600, Inferno 46,400, Create gold
14,000, Possess 450, Summon champion 108,000 plus 2,250 per second. The worker price grows by one base price per worker above
the four the heart supplies."""
from pathlib import Path
import re
import subprocess
import tempfile

repo = Path(__file__).resolve().parents[2]

config = (repo / "config/spells.cfg").read_text()
section = config[config.rindex("[Spells]"):config.rindex("[/Spells]")]
values = dict(re.findall(r"^\s+(\w+)\s+([\d.]+)\s*$", section, re.M))

expected = {
    "SummonWorkerNbHeart": "4", "SummonWorkerBasePrice": "1400", "SummonWorkerCooldown": "0",
    "CallToWarPrice": "9200", "CallToWarCooldown": "0",
    "CreatureHealPrice": "5400", "CreatureHealCooldown": "0",
    "EyeEvilPrice": "4600", "EyeEvilCooldown": "0",
    "LightningPrice": "6600", "LightningCooldown": "0",
    "TremorPrice": "27600", "TremorCooldown": "0",
    "DefectorPrice": "21600", "DefectorCooldown": "76",
    "HexenHenPrice": "10600", "HexenHenCooldown": "92",
    "InfernoPrice": "46400", "InfernoCooldown": "78",
    "CreateGoldPrice": "14000", "CreateGoldCooldown": "0",
    "PossessPrice": "450", "PossessFreeSeconds": "20",
    "SummonChampionPrice": "108000", "SummonChampionDrainPerSecond": "2250", "SummonChampionCooldown": "0",
    "CreatureHastePrice": "2200", "CreatureHasteCooldown": "13",
    "CreatureSlowPrice": "1800", "CreatureSlowCooldown": "11",
    "CreatureDefensePrice": "2650", "CreatureDefenseCooldown": "17",
    "CreatureStrengthPrice": "2300", "CreatureStrengthCooldown": "22",
    "CreatureWeakPrice": "2150", "CreatureWeakCooldown": "18",
    "CreatureExplosionPrice": "4600", "CreatureExplosionCooldown": "15",
}
for key, value in values.items():
    if key.endswith("Price") or key == "SummonWorkerBasePrice":
        assert int(value) % 50 == 0, f"{key} is not a multiple of the 50 mana step"
for key, value in expected.items():
    assert values.get(key) == value, f"{key} is {values.get(key)}, expected {value}"
assert "SummonWorkerNbFree" not in config, "the free-worker key is gone"
assert "PossessDrainPerSecond" not in config, "the flat drain key is gone"

# Possession: free for PossessFreeSeconds, then the drain per second of the creature type
creatures = (repo / "config/creatures.cfg").read_text()
blocks = re.findall(r"^\[Creature\]\n(.*?)^\[/Creature\]", creatures, re.M | re.S)
assert blocks, "creature blocks found"
costs = {}
for block in blocks:
    name = re.search(r"^\s+Name\s+(\w+)", block, re.M).group(1)
    match = re.search(r"^\s+PossessManaCost\s+(\d+)\s*$", block, re.M)
    assert match, f"{name} has no PossessManaCost"
    costs[name] = int(match.group(1))
for name in ("Kobold", "DwarfWorker"):
    assert costs[name] == 0, f"{name} (worker) possesses for free"
for name, value in {"Skeleton": 40, "Dwarf1": 40, "Dwarf2": 40, "Goblin": 120, "Troll": 120, "Monk": 120,
                    "Wizard": 120, "DarkElf": 120, "Elf": 120, "Orc": 240, "Knight": 400, "Dragon": 600}.items():
    assert costs[name] == value, f"{name} is {costs[name]}, expected {value}"
action = (repo / "source/creatureaction/CreatureActionPossessed.cpp").read_text()
assert "PossessFreeSeconds" in action and "getPossessManaCost" in action,     "the possession action uses the free period and the creature drain"
assert "PossessDrainPerSecond" not in action

spell = (repo / "source/spells/SpellSummonWorker.cpp").read_text()
assert "std::pow" not in spell, "the worker price no longer doubles"
assert "SummonWorkerNbFree" not in spell
assert spell.count("getWorkerPrice(basePrice, nbWorkers)") == 3, \
    "cast check, server cast and next price use the same rule"

probe = r"""
#include <algorithm>
#include <cstdint>
#include <cstdio>
static int32_t price(int32_t base, int32_t workers, int32_t heart)
{ return base * std::max(1, workers - heart + 1); }
int main()
{
    int bad = 0;
    // the heart supplies four workers: the fifth costs the base price, then 2x, 3x ...
    const int32_t expectedPrice[][2] = {{0, 1400}, {3, 1400}, {4, 1400}, {5, 2800}, {6, 4200}, {7, 5600}};
    for(const int32_t* row : expectedPrice)
        if(price(1400, row[0], 4) != row[1]) { std::printf("workers %d gives %d\n", row[0], price(1400, row[0], 4)); bad = 1; }
    return bad;
}
"""
with tempfile.TemporaryDirectory(prefix="odp-spell-costs-") as directory:
    work = Path(directory)
    (work / "check.cpp").write_text(probe)
    subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++14", "check.cpp", "/Fecheck.exe"], cwd=work, check=True)
    subprocess.run([str(work / "check.exe")], cwd=work, check=True)
print("SPELL COSTS OK")
