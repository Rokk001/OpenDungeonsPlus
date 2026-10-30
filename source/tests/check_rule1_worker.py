"""Rule 1 of the combat balance: the worker survives the worst level-1 critical blow, also with items and potions."""
from pathlib import Path
import math
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/balance"))
from combat_sim import Roster, World


# Read a tracked file using the repository root rather than the caller's directory.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Return the largest Common damage bonus in items.cfg.
def common_weapon_damage_percent():
    values = []
    for quality in re.findall(r"\[Quality\]\s*Name\s+Common\b(.*?)\[/Quality\]", read("config/items.cfg"), re.S):
        values.extend(float(match.group(1)) for match in re.finditer(r"^\s*Bonus\s+Damage%\s+\S+\s+(\S+)", quality, re.M))
    return max(values)


# Check the worst critical blow of every eligible type and template against both workers.
def main():
    roster = Roster(ROOT)
    world = World(roster)
    worker = world.unit("Kobold", 1, -1)[0]
    crit = world.glob["CritDamageMultiplier"]
    bonus = common_weapon_damage_percent()
    blows = []
    for name in world.names:
        if world.wage[name] > 200:
            continue
        weapons = 0
        for hand in ("R", "L"):
            item = world.field(name, "WeaponSpawn" + hand)
            if item and roster.equipment[item][0].get("WeaponType", [""])[0] != "shield":
                weapons += 1
        factor = 1 + bonus / 100 * weapons
        for template in (0, 1, 2):
            maximum = world.unit(name, 1, template)[0].maximum
            blow = sum(max(crit * value * factor - defense, 0) for value, defense in zip(maximum, worker.defense))
            blows.append((blow, name, template))
    blow, name, template = max(blows)
    spell = float(re.search(r"^\s*CreatureStrengthValue\s+(\S+)", read("config/spells.cfg"), re.M).group(1))
    research = float(re.search(r"^\s*spellCreatureStrength\s+Factor\s+dev\s+\S+\s+\S+\s+(\S+)", read("config/skills.cfg"), re.M).group(1))
    strength = 1 + (spell - 1) * research
    potion = float(re.search(r"Id\s+strength_small\b.*?^\s*Value\s+(\S+)", read("config/potions.cfg"), re.S | re.M).group(1))
    assert math.isclose(blow, 52.56, abs_tol=1e-9) and (name, template) == ("Elf", 2), (blow, name, template)
    assert math.isclose(strength, 1.2) and math.isclose(potion, 1.1), (strength, potion)
    total = blow * strength * potion
    assert math.isclose(total, 69.3792, abs_tol=1e-9), total
    for worker_name in ("Kobold", "DwarfWorker"):
        hp = roster.number(roster.creatures[worker_name][0], "MinHP")
        assert hp > total, (worker_name, hp, total)
    print("rule 1 worker ok: %.4f < both workers' MinHP" % total)


if __name__ == "__main__":
    main()
