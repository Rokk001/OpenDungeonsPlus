"""Check that AI actions use the same legality gates as player actions."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
ai = repo / "source/ai"
for path in sorted(list(ai.glob("*.cpp")) + list(ai.glob("*.h"))):
    text = path.read_text(encoding="utf-8")
    assert not re.search(r"\brepairRoom\w*\b", text), f"{path.name}: room repair"
    assert not re.search(r"GiftBoxBonus::(?:applyBonus|applyEffect)\b", text), f"{path.name}: gift shortcut"
    if path.name != "AiActions.cpp":
        for name in ("SpellManager::castSpell", "buildRoomOnTiles", "buildTrapOnTiles"):
            assert name not in text, f"{path.name}: {name} outside action wrappers"

actions = (ai / "AiActions.cpp").read_text(encoding="utf-8")
# Extract an action wrapper to verify its own gates.
def wrapper(name):
    match = re.search(r"\bACTS::" + name + r"\s*\([^;]*?\)\s*\{", actions, re.S)
    if match is None:
        namespace = re.search(r"\bnamespace\s+ACTS\s*\{", actions)
        assert namespace, "missing ACTS namespace"
        match = re.search(r"\b" + name + r"\s*\([^;{}]*?\)\s*\{", actions[namespace.end():], re.S)
        assert match, f"missing wrapper {name}"
        start = namespace.end() + match.end() - 1
    else:
        start = match.end() - 1
    assert match, f"missing wrapper {name}"
    end = start + 1
    depth = 1
    while depth and end < len(actions):
        depth += (actions[end] == "{") - (actions[end] == "}")
        end += 1
    assert depth == 0, name
    return actions[start:end]

for name, gates in (("castSpell", ("isSpellAvailable", "getSpellCooldownTurns", "SpellManager::castSpell", "setSpellCooldownTurns")),
                    ("buildRoom", ("isRoomAvailable", "buildRoomOnTiles")),
                    ("buildTrap", ("isTrapAvailable", "buildTrapOnTiles"))):
    text = wrapper(name)
    positions = [text.find(gate) for gate in gates]
    assert all(pos >= 0 for pos in positions) and positions == sorted(positions), f"{name}: missing or misplaced gate"
print("OK")
