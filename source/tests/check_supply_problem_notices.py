"""Static guards for actual failed supply searches and existing notice throttles; no compilation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Read a source block from its final route-selection failure to its early return.
def failure_block(path, marker):
    source = (ROOT / path).read_text(encoding="utf-8")
    block = source[source.index(marker):]
    return block[:block.index("return true;")]


food = failure_block("source/creatureaction/CreatureActionSearchFood.cpp", "if(chosenTile == nullptr)")
bed = failure_block("source/creatureaction/CreatureActionFindHome.cpp", "if(choosenTile == nullptr)")
assert "notifyCreatureCannotFindFood(creature)" in food
assert "notifyCreatureCannotFindBed(creature)" in bed
for block in (food, bed):
    assert "getIsHuman()" in block
    assert block.index("notifyCreatureCannotFind") < block.index("creature.popAction();")
player = (ROOT / "source/game/Player.cpp").read_text(encoding="utf-8")
for kind in ("Bed", "Food"):
    block = player[player.index("void Player::notifyCreatureCannotFind" + kind):]
    block = block[:block.index("\n}\n")]
    assert "mHasLost" in block
    assert "mCreatureCannotFind" + kind + " <= 0.0f" in block
    assert "_TIME_COUNT" in block
print("Failed supply routes keep existing throttled problem notices: PASS (static only)")
