"""Check crossing source wiring; C++ behavior tests require the integrator build."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Read one production source file without compiling or launching the game.
def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


# Restrict assertions to one production function.
def body(text, signature):
    text = text[text.index(signature):]
    return text[:text.index("\n}\n")]


script = read("source/gamemap/LevelScript.cpp")
walk = read("source/entities/MovableGameEntity.cpp")
observer = body(script, "void LevelScript::observeCrossingStep(")
for guard in ("condition.mSeatId != seatId", "required->mTimesFired == 0",
              "candidate->mCreature == creature", "candidate->mX != fromX",
              "std::abs(toX - fromX) > 1", "region->contains(toX, toY)",
              "before == low && after == low - 1", "before == high && after == high + 1",
              "!observed.insert(key).second"):
    assert guard in observer, guard
hook = body(walk, "void recordScriptWalk(")
for guard in ("!entity.getIsOnServerMap()", "GameEntityType::creature", "!entity.getIsOnMap()",
              "!creature.isAlive()", "!script.hasCrossingObservers()", "std::ceil", "script.observeCrossingStep("):
    assert guard in hook, guard
movement = body(walk, "void MovableGameEntity::update(")
assert movement.count("recordScriptWalk(*this, stepStart, newPosition);") == 2
assert movement.index("recordScriptWalk(*this, stepStart, newPosition);") < movement.index("mWalkQueue.pop_front();")
assert 'key == "CrossingProgress"' in script
assert 'os << "CrossingProgress' in script
assert "mCrossingProgress.clear();" in body(script, "void LevelScript::clear()")
assert "mHasCrossingObservers = false;" in body(script, "void LevelScript::clear()")
assert "clearCreatureCrossings(cc->getName())" in body(read("source/gamemap/GameMap.cpp"), "void GameMap::addCreature(")
assert "script.wasRegionCrossed(" in read("source/gamemap/LevelScriptRunner.cpp")
unit = read("source/tests/test_LevelScript.cpp")
for name in ("actual_crossing_progress_and_save_round_trip", "crossing_order_and_negative_paths",
             "crossing_directions_and_backtracking"):
    assert "BOOST_AUTO_TEST_CASE(" + name + ")" in unit
print("Crossing movement hooks, seat/instance/order guards and save wiring: static PASS")
print("C++ crossing behavior cases present; not compiled or executed by this check")
