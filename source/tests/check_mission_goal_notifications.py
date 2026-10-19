"""Guard objective-only presentation without compiling or starting the game."""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]


# Extract one existing C++ function, including its nested branches.
def body(source, signature):
    function = source[source.index(signature):]
    return function[:function.index("\n}\n")]


# Reject every objective notification while retaining state transitions and voice cues.
def check(seat, runner):
    completed = body(seat, "unsigned int Seat::checkAllCompletedGoals(")
    pending = body(seat, "unsigned int Seat::checkAllGoals(")
    for function in (completed, pending):
        assert "ServerNotification" not in function
        assert "queueServerNotification" not in function
        assert "sendMessage(" not in function
        assert "mFailedGoals.push_back(" in function
        assert "mHasGoalsChanged = true;" in function
        assert "SoundRelativeKeeperStatements::GoalFailed" in function
    assert "mUncompleteGoals.push_back(*currentGoal);" in completed
    assert "mCompletedGoals.push_back(goal);" in pending
    assert "SoundRelativeKeeperStatements::GoalMet" in pending
    action = body(runner, "void runAction(")
    objective = action.split("case LevelScriptActionType::objective:", 1)[1].split(
        "case LevelScriptActionType::objectiveState:", 1)[0]
    objective = re.sub(r"//[^\n]*", "", objective)
    assert objective.strip() == "break;", "Every objective kind must be notification-free"
    state = action.split("case LevelScriptActionType::objectiveState:", 1)[1].split(
        "case LevelScriptActionType::spawn:", 1)[0]
    assert "sendMessage(" not in state and "ServerNotification" not in state
    assert "script.setObjectiveState(" in state
    assert 'sendMessage(gameMap, action.mSeatId, action.mText);' in action
    assert 'sendMessage(gameMap, action.mSeatId, "Hint: " + action.mText);' in action


seat = (ROOT / "source/game/Seat.cpp").read_text(encoding="utf-8")
runner = (ROOT / "source/gamemap/LevelScriptRunner.cpp").read_text(encoding="utf-8")
check(seat, runner)

# Prove that each former notification path is independently rejected.
mutations = [
    (seat, runner.replace("case LevelScriptActionType::objective:",
                         'case LevelScriptActionType::objective:\n sendMessage(gameMap, action.mSeatId, action.mText);', 1)),
    (seat, runner.replace("case LevelScriptActionType::objectiveState:",
                         'case LevelScriptActionType::objectiveState:\n sendMessage(gameMap, action.mSeatId, action.mText);', 1)),
]
for signature in ("unsigned int Seat::checkAllCompletedGoals()", "unsigned int Seat::checkAllGoals()"):
    mutations.append((seat.replace(signature + "\n{", signature + "\n{\n ServerNotification* notice;", 1), runner))
for changed_seat, changed_runner in mutations:
    try:
        check(changed_seat, changed_runner)
    except AssertionError:
        pass
    else:
        raise AssertionError("Objective notification negative control was accepted")

# Keep the independent mission panel transport and legacy/identified goal rendering intact.
server = (ROOT / "source/network/ODServer.cpp").read_text(encoding="utf-8")
client = (ROOT / "source/network/ODClient.cpp").read_text(encoding="utf-8")
display = body((ROOT / "source/gamemap/GameMap.cpp").read_text(encoding="utf-8"),
               "std::string GameMap::getGoalsStringForPlayer(")
assert "getGoalsStringForPlayer(player)" in server
assert "serverNotification->mPacket << goals;" in server
assert "gm->refreshPlayerGoals(goalsString);" in client
for token in ("GoalStatus/Open", "GoalStatus/Reached", "GoalStatus/Failed",
              "numFailedGoals()", "numUncompleteGoals()", "numCompletedGoals()",
              "LevelScriptActionType::objective", "action.mText"):
    assert token in display
print("Mission goals: notification-free declarations/status, preserved panel/state/voice; 4 negative controls PASS")
