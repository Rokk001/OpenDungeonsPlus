"""Check that the three AI levels use the numbers of the reference AI rows
(hard = Master Keeper, normal = Greyman, easy = Idiot): attack at 15 creatures and
minimum creature level 2 / 5 / 8 and retreat at 10 / 20 / 20 percent health. Reaction scale, cooldowns and trap and door
counts stay our own."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
src = (repo / "source/ai/AIFactory.cpp").read_text(encoding="utf-8")

expected = {
    "easy": ("150", "20", "15", "2"),
    "normal": ("100", "20", "15", "5"),
    "hard": ("60", "10", "15", "8"),
}
for level, (reaction, retreat, attack, minLevel) in expected.items():
    m = re.search(r"case KeeperAIType::%s:\s*return new KeeperAI\(([^;]*)\);" % level, src)
    assert m, f"no KeeperAI for level {level}"
    args = [a.strip() for a in m.group(1).split(",")]
    # gameMap, player, 6 cooldowns, reaction, retreat HP percent, attack threshold, min level, traps, doors
    assert len(args) == 14, f"{level}: unexpected argument count {len(args)}"
    assert args[8:12] == [reaction, retreat, attack, minLevel], \
        f"{level}: reaction/retreat/attack is {args[8:12]}, expected {[reaction, retreat, attack, minLevel]}"

doc = (repo / "docs/development/AI-LEVELS.md").read_text(encoding="utf-8")
assert "not built" in doc
print("OK")
