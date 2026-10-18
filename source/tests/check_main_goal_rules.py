"""Static wiring checks for main-goal victory gating and grouped presentation.

The C++ parser/state/save cases are in test_LevelScript.cpp; this check does not compile them.
"""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]


# Read source without executing the game or a compiler.
def read(name):
    return (ROOT / name).read_text(encoding="utf-8")


# Isolate one production function for ordered gate assertions.
def body(source, signature):
    function = source[source.index(signature):]
    return function[:function.index("\n}\n")]


script = read("source/gamemap/LevelScript.cpp")
header = read("source/gamemap/LevelScript.h")
for keyword in ("mainobjectiveid", "optionalobjectiveid", "conditionalobjectiveid"):
    assert script.count('"' + keyword + '"') >= 2
rule = body(script, "bool LevelScript::areMainObjectivesReached(")
assert "LevelScriptObjectiveGroup::main" in rule
assert "LevelScriptObjectiveGroup::conditionalMain && trigger.mTimesFired > 0" in rule
assert "LevelScriptObjectiveGroup::optional" not in rule
assert "getObjectiveState(seatId, action.mObjectiveId) != LevelScriptObjectiveState::reached" in rule
assert 'key == "VictoryRequest"' in script and 'os << "VictoryRequest' in script
assert 'mVictoryRequests.clear();' in body(script, 'void LevelScript::clear()')
assert 'mVictoryRequests.empty()' in header
win = body(read('source/gamemap/GameMap.cpp'), 'void GameMap::addWinningSeat(')
assert win.index('getHasLost()') < win.index('mWinningSeats.push_back')
assert win.index('areMainObjectivesReached') < win.index('mWinningSeats.push_back')
assert win.index('requestVictory(') < win.index('areMainObjectivesReached')
turn = body(read('source/gamemap/LevelScriptRunner.cpp'), 'void LevelScriptRunner::doTurn(')
assert turn.index('runAction(') < turn.index('script.hasVictoryRequest(')
assert 'script.areMainObjectivesReached(seat->getId())' in turn
assert '!player->getHasLost()' in turn
for name in ('source/gamemap/GameMap.cpp', 'source/modes/MenuModeCampaign.cpp'):
    text = read(name)
    assert '"Main goals' in text and 'Optional goals' in text
    assert 'LevelScriptObjectiveGroup::optional' in text
    assert 'GoalStatus/Open' in text
unit = read('source/tests/test_LevelScript.cpp')
assert 'required_objectives_and_pending_victory_round_trip' in unit
assert 'legacy_objectives_keep_their_original_victory_rules' in unit
print('Main/optional/conditional goals, shared victory gate and grouped display: static wiring PASS')
