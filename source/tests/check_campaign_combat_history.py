"""Static wiring for attributed combat history; does not execute the C++ behavior tests."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


# Read a production file without compiling or running the game.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Isolate a production function for guard and ordering checks.
def body(text, signature):
    text = text[text.index(signature):]
    return text[:text.index("\n}\n")]


creature = body(read("source/entities/Creature.cpp"), "double Creature::takeDamage(")
start = creature.index('if(wasAlive && (damageDone > 0.0))')
end = creature.index("if(mHp <= 0)", start)
hit = creature[start:end]
for guard in ('recordScriptEvent(*this, "attacked")', "getIsOnServerMap()", "creatureAttacking != nullptr",
              "!attackingSeat->isAlliedSeat(getSeat())", "getPositionTile() != nullptr",
              "observeRegionAttack(attackingSeat->getId()", "getSeat()->getId()"):
    assert guard in hit, guard
assert creature.index("mHp -= damageDone;") < start
script = read("source/gamemap/LevelScript.cpp")
observer = body(script, "void LevelScript::observeRegionAttack(")
for guard in ("condition.mSeatId != attackingSeat", "condition.mNumber != targetSeat",
              "region->contains(x, y)", "wasRegionAttacked(attackingSeat, targetSeat, condition.mName)"):
    assert guard in observer, guard
assert 'getEventCount("Seat" + std::to_string(attackingSeat)' in script
assert 'os << "attackedregion' in script
assert "script.wasRegionAttacked(cond.mSeatId" in read("source/gamemap/LevelScriptRunner.cpp")
assert "BOOST_AUTO_TEST_CASE(regional_attack_attribution_and_save)" in read("source/tests/test_LevelScript.cpp")
print("Positive hostile creature hits, seat/region attribution and saved event wiring: static PASS")
print("C++ behavior tests present; not compiled or executed")

assert "static_cast<MissileObject*>(attacker)->isCreatureShot()" in hit
assert "attackingSeat = attacker->getSeat();" in hit
launch = body(read("source/creatureskill/CreatureSkillMissileLaunch.cpp"), "bool CreatureSkillMissileLaunch::tryUseFight(")
assert launch.index("setCreatureShot(creature->isPossessed())") < launch.index("missile->doUpkeep();")
missile = read("source/entities/MissileObject.cpp")
assert missile.count("mCreatureShot(false)") == 2 and missile.count("mPossessedShot(false)") == 2
assert 'os << "ShotOrigin' in body(missile, "void MissileObject::exportToStream(")
loaded = body(missile, "bool MissileObject::importFromStream(")
assert loaded.index("mCreatureShot = false;") < loaded.index("if(is.peek() == 'S')")
assert 'marker != "ShotOrigin"' in loaded and "possessed != 0 && possessed != 1" in loaded
print("Creature projectile attribution survives shooter loss and saves; legacy origin remains unknown: static PASS")
