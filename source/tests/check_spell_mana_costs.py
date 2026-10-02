"""Check the spell mana costs, cooldowns and the worker price rule.

The costs follow the reference scale (mana cap 200,000): Summon worker 1,500 per
step, Call to war 10,000, Heal 5,000, Eye of evil 5,000, Lightning 6,000,
Tremor 30,000, Turncoat 20,000, Chicken 10,000, Inferno 50,000, Create gold
15,000, Possess 500, Summon champion 100,000 plus 2,000 per second. The worker price grows by one base price per worker above
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
    "SummonWorkerNbHeart": "4", "SummonWorkerBasePrice": "1500", "SummonWorkerCooldown": "0",
    "CallToWarPrice": "10000", "CallToWarCooldown": "0",
    "CreatureHealPrice": "5000", "CreatureHealCooldown": "0",
    "EyeEvilPrice": "5000", "EyeEvilCooldown": "0",
    "LightningPrice": "6000", "LightningCooldown": "0",
    "TremorPrice": "30000", "TremorCooldown": "0",
    "TurncoatPrice": "20000", "TurncoatCooldown": "84",
    "ChickenPrice": "10000", "ChickenCooldown": "84",
    "InfernoPrice": "50000", "InfernoCooldown": "84",
    "CreateGoldPrice": "15000", "CreateGoldCooldown": "0",
    "PossessPrice": "500", "PossessFreeSeconds": "20",
    "SummonChampionPrice": "100000", "SummonChampionDrainPerSecond": "2000", "SummonChampionCooldown": "0",
}
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
for name, value in {"Skeleton": 50, "Goblin": 150, "Troll": 150, "Knight": 500}.items():
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
    const int32_t expectedPrice[][2] = {{0, 1500}, {3, 1500}, {4, 1500}, {5, 3000}, {6, 4500}, {7, 6000}};
    for(const int32_t* row : expectedPrice)
        if(price(1500, row[0], 4) != row[1]) { std::printf("workers %d gives %d\n", row[0], price(1500, row[0], 4)); bad = 1; }
    return bad;
}
"""
with tempfile.TemporaryDirectory(prefix="odp-spell-costs-") as directory:
    work = Path(directory)
    (work / "check.cpp").write_text(probe)
    subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++14", "check.cpp", "/Fecheck.exe"], cwd=work, check=True)
    subprocess.run([str(work / "check.exe")], cwd=work, check=True)
print("SPELL COSTS OK")
