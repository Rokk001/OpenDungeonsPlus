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

refresh = body(script, 'void LevelScript::refreshMainObjectives(')
assert 'LevelScriptObjectiveState::failed' in refresh and 'LevelScriptObjectiveState::open' in refresh
assert 'LevelScriptObjectiveGroup::optional' not in refresh
assert turn.index('script.refreshMainObjectives(') < turn.index('for(LevelScriptTrigger& trigger')
print('Current main-state refresh preserves optional successes and terminal failures: static wiring PASS')

assert 'hasMainObjectives(s->getId()) && !objectivesUpdated' in win
assert 'gameMap.addWinningSeat(seat, true);' in turn
assert '!gameMap.seatIsAWinner(seat)' in turn
runner = read('source/gamemap/LevelScriptRunner.cpp')
assert 'script.hasMainObjectives(player->getSeat()->getId()) &&' in runner
assert 'gameMap.seatIsAWinner(player->getSeat()) ||' in runner
assert 'script.getObjectiveState(player->getSeat()->getId(), action.mObjectiveId) == LevelScriptObjectiveState::failed' in runner
print('Grouped victories wait for the current observer pass; completed outcomes stay frozen: static wiring PASS')

assert win.index('checkGameDuration();') < win.index('getHasLost()')
print('Original deadline is applied before grouped victory: static wiring PASS')

assert 'LevelScriptConditionType::groundFootprintClaimed' in script and 'groundclaimed' in script
assert 'if(className == "@fighters")' in runner and 'return !creature->getDefinition()->isWorker();' in runner
assert '(cond.mType == LevelScriptConditionType::roomFootprintClaimed && room == nullptr)' in runner
print('Natural floor ownership and living fighter-only assembly: static wiring PASS')
