"""Static checks of paying a wage owed by dropping gold from the hand on an own creature.

Run from any directory. It does not compile or start a game.
"""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[2]
treasury = (root / "source/entities/TreasuryObject.cpp").read_text(encoding="utf-8")
treasury_header = (root / "source/entities/TreasuryObject.h").read_text(encoding="utf-8")
creature_header = (root / "source/entities/Creature.h").read_text(encoding="utf-8")
player = (root / "source/game/Player.cpp").read_text(encoding="utf-8")
failures = []


def check(condition, message):
    if not condition:
        failures.append(message)


# The creature uses at most the wage owed and keeps no credit.
receive = re.search(r"int32_t receiveTreat\(int32_t gold\)\n    \{.*?\n    \}\n", creature_header, re.S)
check(receive is not None, "Creature::receiveTreat is missing")
body = receive.group(0) if receive else ""
check("(gold < mGoldFee) ? gold : mGoldFee" in body, "receiveTreat must use at most the wage owed")
check("mGoldFee = 0;" in body, "receiveTreat must clear the wage owed")
check("mMoodCooldownTurns = 0;" in body, "receiveTreat must clear the pay day annoyance")
check("return used;" in body and "return 0;" in body, "receiveTreat must return the gold used")

# Only own living creatures that are owed a wage count, the one owed the most is paid.
check("creatureAliveOwned" in treasury, "target must be an own living creature")
check("creature->getGoldFee() <= 0" in treasury and "creature->getGoldFee() > target->getGoldFee()" in treasury,
      "target must be the creature owed the most")

# The gold is used once, during the upkeep after the drop, and the rest stays as a pile.
check("mDroppedByHand = false;" in treasury, "the drop flag must be cleared after one upkeep")
check("mGoldValue -= target->receiveTreat(mGoldValue);" in treasury, "the gold used must be taken from the pile")
check("if(mGoldValue <= 0)" in treasury and "deleteYourself();" in treasury, "an empty pile must be removed")
check("if(getTreatTarget(tile, seat) != nullptr)" in treasury and "return true;" in treasury,
      "gold may be dropped on an own creature owed a wage")
check("void drop(const Ogre::Vector3& v) override" in treasury_header.replace("virtual ", ""), "drop override missing")

# The seat of the dropping player is remembered on the server only.
check("setDropSeat(getSeat())" in player and "GameEntityType::treasuryObject" in player,
      "the dropping seat must be set for gold dropped from the hand")

if failures:
    print("FAIL")
    for failure in failures:
        print(" - " + failure)
    sys.exit(1)
print("OK")
