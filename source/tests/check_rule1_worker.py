"""Rule 1 of the combat balance: the worker survives the worst level-1 critical blow, also with items and potions."""
from pathlib import Path
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/balance"))
from combat_sim import Roster, World, world_rule_one


# Read a tracked file using the repository root rather than the caller's directory.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# The best Damage% bonus of the Common quality in every item slot, summed over the slots (the Common set).
def common_set_damage_percent():
    best = {}
    for item in re.findall(r"\[Item\](.*?)\[/Item\]", read("config/items.cfg"), re.S):
        slot = re.search(r"^\s*Slot\s+(\S+)", item, re.M).group(1)
        for quality in re.findall(r"\[Quality\]\s*Name\s+Common\b(.*?)\[/Quality\]", item, re.S):
            for match in re.finditer(r"^\s*Bonus\s+Damage%\s+\S+\s+(\S+)", quality, re.M):
                best[slot] = max(best.get(slot, 0.0), float(match.group(1)))
    return sum(best.values())


# The worst level-1 critical blow of a wage 50-200 fighter, times the Common set, times the Strength research 3 factor,
# times the small Strength potion, stays below the worker MinHP.
def main():
    spell = float(re.search(r"^\s*CreatureStrengthValue\s+(\S+)", read("config/spells.cfg"), re.M).group(1))
    research = float(re.search(r"^\s*spellCreatureStrength\s+Factor\s+dev\s+\S+\s+\S+\s+(\S+)", read("config/skills.cfg"), re.M).group(1))
    strength = 1 + (spell - 1) * research
    potion = re.search(r"Id\s+strength_small\b.*?^\s*Value\s+(\S+)", read("config/potions.cfg"), re.S | re.M)
    small_potion = float(potion.group(1))
    items = 1 + common_set_damage_percent() / 100.0
    min_hp = float(re.search(r"^\s*MinHP\s+(\S+)", read("config/creatures.cfg"), re.M).group(1))
    worker_hp, blow, by = world_rule_one(World(Roster(ROOT)))
    assert worker_hp == min_hp == 70, (worker_hp, min_hp)
    assert math.isclose(strength, 1.2) and math.isclose(small_potion, 1.1), (strength, small_potion)
    total = blow * items * strength * small_potion
    assert total < worker_hp, (blow, items, strength, small_potion, total, worker_hp, by)
    print("rule 1 worker ok: %.2f x %.2f x %.2f x %.2f = %.2f < %g (%s)" % (blow, items, strength, small_potion, total, worker_hp, by))


if __name__ == "__main__":
    main()
