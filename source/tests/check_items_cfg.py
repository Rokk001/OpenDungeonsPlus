"""Validate the equipment catalogue, prices and actual creature weapon compatibility."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
KINDS = {"Damage%", "MaxHP%", "CritChance", "Defense%", "AttackRating%", "DefenseRating%",
         "MoveSpeed%", "Avoid", "Cooldown%", "DamageAttribute", "Life", "Mana", "ManaCost%",
         "Wakefulness%", "Dig%", "Claim%", "Carry%"}


def read(name):
    """Read a repository input without discarding its Unicode display names."""
    return (ROOT / name).read_text(encoding="utf-8")


def blocks(text, tag):
    """Return complete tagged blocks after removing configuration comments."""
    text = re.sub(r"#[^\n]*", "", text)
    return re.findall(r"\[" + tag + r"\]([\s\S]*?)\[/" + tag + r"\]", text)


def values(block, key):
    """Return each complete value line for a possibly repeated configuration key."""
    return re.findall(r"^\s*" + re.escape(key) + r"[ \t]+([^\r\n]+)", block, re.M)


def value(block, key):
    """Require one occurrence of a scalar configuration field."""
    found = values(block, key)
    assert len(found) == 1, (key, found)
    return found[0].strip()


def main():
    """Assert every prescribed catalogue count, quality, range, price and weapon class."""
    items = blocks(read("config/items.cfg"), "Item")
    assert len(items) == 187, "expected five Poor and 182 path lines"
    equipment = {value(block, "Name"): block for block in blocks(read("config/equipments.cfg"), "Equipment")}
    creatures = blocks(read("config/creatures.cfg"), "Creature")
    effects_source = read("source/entities/ItemEffects.cpp")
    effect_table = effects_source.split("EFFECT_NAMES[]", 1)[1].split("};", 1)[0]
    effects = set(re.findall(r'\{"([^"]+)",\s*"[^"]+"\}', effect_table))
    identifiers, displays, poor, paths = set(), set(), [], []
    for item in items:
        item_id = value(item, "Id")
        assert item_id not in identifiers, item_id
        identifiers.add(item_id)
        qualities = {value(block, "Name"): block for block in blocks(item, "Quality")}
        if value(item, "Path") == "none":
            poor.append(item_id)
            assert set(qualities) == {"Poor"}, item_id
        else:
            paths.append(item_id)
            assert set(qualities) == {"Common", "Rare", "Epic"}, item_id
        representative = value(item, "PoorEquipment")
        if representative != "none":
            assert representative in equipment, (item_id, representative)
        slot, weapon_class = value(item, "Slot"), value(item, "WeaponClass")
        if slot in {"weapon", "shield"} and value(item, "Path") != "none":
            eligible = []
            for creature in creatures:
                group = value(creature, "SkillGroup")
                family = value(creature, "SkillFamily")
                if not (family.casefold() == value(item, "Path").casefold() if value(item, "Group") == "family"
                        else group == value(item, "Group")):
                    continue
                for hand in ("WeaponSpawnR", "WeaponSpawnL"):
                    for spawned in values(creature, hand):
                        if spawned in equipment:
                            eligible.append(value(equipment[spawned], "WeaponType"))
            assert weapon_class in eligible, (item_id, weapon_class, eligible)
            assert value(equipment[representative], "WeaponType") == weapon_class, item_id
        for quality, block in qualities.items():
            display = value(block, "Display")
            if quality != "Poor":
                assert display.casefold() not in displays, display
                displays.add(display.casefold())
            minimum = {"Poor": 1, "Common": 1, "Rare": 10, "Epic": 20}[quality]
            assert int(value(block, "LevelMin")) == minimum, (item_id, quality)
            counts = tuple(map(int, value(block, "BonusCount").split()))
            assert counts == {"Poor": (0, 0), "Common": (1, 1), "Rare": (2, 3), "Epic": (4, 5)}[quality], item_id
            bonuses = values(block, "Bonus")
            assert len(bonuses) >= counts[1], (item_id, quality)
            for bonus in bonuses:
                kind, low, high = bonus.split()
                assert kind in KINDS and float(low) <= float(high), (item_id, bonus)
            actual_effects = values(block, "Effect")
            assert len(actual_effects) == {"Poor": 0, "Common": 0, "Rare": 1, "Epic": 2}[quality], item_id
            assert all(effect.split()[0] in effects for effect in actual_effects), item_id
            price = tuple(map(float, value(block, "Price").split()))
            assert price == {"Poor": (20,), "Common": (100,), "Rare": (300, 100), "Epic": (1500, 250)}[quality], item_id
    assert len(poor) == 5 and len(paths) == 182 and len(displays) == 546
    assert set(poor) == {"POOR_Head", "POOR_Armour", "POOR_Boots", "POOR_Ring", "POOR_Shield"}
    print("equipment catalogue: 187 lines, 546 distinct path displays, ranges/effects/prices/weapons passed")


if __name__ == "__main__":
    main()
