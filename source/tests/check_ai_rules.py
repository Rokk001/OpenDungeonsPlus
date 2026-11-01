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

# The wrappers only schedule; the executor "perform" runs the same legality gates as the human handlers, in this order.
perform = re.search(r"\bvoid perform\s*\(KeeperAI& ai, const std::string& target\)\s*\{", actions)
assert perform, "missing executor perform"
body_start = perform.end() - 1
depth = 1
body_end = body_start + 1
while depth and body_end < len(actions):
    depth += (actions[body_end] == "{") - (actions[body_end] == "}")
    body_end += 1
executor = actions[body_start:body_end]
for name, gates, scheduled in (("castSpell", ("isSpellAvailable", "getSpellCooldownTurns", "SpellManager::castSpell", "setSpellCooldownTurns"), "schedule("),
                               ("buildRoom", ("isRoomAvailable", "buildRoomOnTiles"), "scheduleTiles("),
                               ("buildTrap", ("isTrapAvailable", "buildTrapOnTiles"), "scheduleTiles(")):
    assert scheduled in wrapper(name), f"{name}: wrapper does not schedule through the executor"
    position = 0
    for gate in gates:
        found = executor.find(gate, position)
        assert found >= 0, f"{name}: missing or misplaced gate {gate}"
        position = found
print("OK")
