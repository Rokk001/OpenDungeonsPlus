"""Pure Python checks of campaign-save wiring; compiles nothing.

Runtime record, progress and difficulty expectations live in the companion
check_campaign_save_probe.py, which is run by FINAL after compilation is allowed.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def read(path):
    """Read the production source without invoking a compiler."""
    return (ROOT / path).read_text(encoding="utf-8")


def body(source, signature):
    """Extract a complete function, retaining nested guards for ordering checks."""
    start = source.index(signature)
    opening = source.index("{", start)
    depth = 1
    end = opening + 1
    while depth:
        depth += (source[end] == "{") - (source[end] == "}")
        end += 1
    return source[start:end]


campaign = read("source/game/Campaign.cpp")
header = read("source/game/Campaign.h")
handler = read("source/gamemap/MapHandler.cpp")
handler_header = read("source/gamemap/MapHandler.h")
server = read("source/network/ODServer.cpp")
load = read("source/modes/MenuModeLoad.cpp")
game = read("source/modes/GameMode.cpp")
game_map = read("source/gamemap/GameMap.cpp")

# The record is optional, versioned and available to the load-screen classifier.
for field in ("mPresent", "mValid", "mLevelFile", "mDifficulty", "mHeartstoneComplete",
              "mKeptClass", "mKeptLevel"):
    assert field in header, field
assert "CampaignSave mCampaignSave" in handler_header
info = body(handler, "bool getMapInfo(")
assert "mCampaignSave.importInfoLine(nextParam)" in info

# Every game save writes campaign metadata, while editor map output does not.
writer = body(handler, "bool writeGameMapToFile(")
assert "gameMap.isServerGameMap() && !gameMap.isInEditorMode()" in writer
save_start = writer.index("if(isGameSave)")
save_block = body(writer[save_start:], "if(isGameSave)")
assert "getSaveState()" in save_block and "exportInfo(levelFile)" in save_block
assert writer.index("getSaveState()") < writer.index('levelFile << "[/Info]"')
snapshot = body(campaign, "CampaignSave Campaign::getSaveState(")
for field in ("mActive", "mLevels", "mPlayedLevel", "mKeptPendingClass", "mKeptPendingLevel"):
    assert field in snapshot, field

# Eligibility and startup share a single filename/progress rule; both legacy and
# recorded saves go through it, before seat setup can choose campaign effects.
eligibility = body(campaign, "size_t Campaign::findSavedLevelNoLock(")
assert "mLevelFile" in eligibility and "mPresent" in eligibility
assert "isUnlockedNoLock(i)" in eligibility
assert "findSavedLevelNoLock(saved, saveFilename)" in body(campaign, "size_t Campaign::findSavedLevel(")
restore = body(campaign, "bool Campaign::restoreSavedLevel(")
assert "findSavedLevel" in restore
start = body(server, "bool ODServer::startServer(")
assert "mode == ServerMode::ModeGameLoaded" in start
assert start.index("gameMap->loadLevel(levelFilename)") < start.index("restoreSavedLevel(")
assert start.index("restoreSavedLevel(") < start.index("seat->getAiLevel()")
assert "getLevelDifficulty()" in start
assert start.index("if((mode == ServerMode::ModeGameLoaded) && Campaign::getSingleton().isActive())") < start.index("else if(seat->getAiLevel()")
assert "loadCampaignProgress()" in load
assert "bool loadCampaignProgress(" in handler and "loadCampaignProgress()" in handler_header

# A loaded creature already exists in the entity snapshot, so startup never
# consumes current campaign carry-over or creates a second copy on this path.
spawn = server.index("LevelScriptRunner::spawnKeptMinion(*gameMap)")
assert "mServerMode != ServerMode::ModeGameLoaded" in server[spawn - 200:spawn]
assert "isLevelHeartstoneComplete()" in server
assert "const bool championAvailable = Campaign::getSingleton().isLevelHeartstoneComplete();" in server
assert "SkillType::spellSummonChampion, championAvailable, championAvailable" in server
champion = body(campaign, "bool Campaign::isLevelHeartstoneComplete(")
assert "mActive && mLoadedCampaignSave" in champion and "return mSavedHeartstoneComplete" in champion
assert "return isHeartstoneComplete()" in champion

# Victory still follows the established campaign path, including its message,
# progress write and menu return. Defeat and ordinary quit use the same active flag.
won = body(campaign, "bool Campaign::onLevelWon(")
assert "mCompleted[mPlayedLevel] = true" in won
assert "mPlayedLevelWon = true" in won and "saveProgress()" in won
assert "mKeptPendingClass" in won and "mKeptPendingLevel" in won
assert "!mKeptPendingClass.empty() || mRestoredLevel" in won
assert "mRestoredLevel = mActive" in restore
assert "mRestoredLevel = false" in body(campaign, "void Campaign::startLevel(")
assert "mDifficulty =" not in won, "loaded victory must preserve menu difficulty"
victory = body(game_map, "void GameMap::addWinningSeat(")
assert victory.index("onLevelWon()") < victory.index("ServerNotificationType::campaignVictory")
victory_ui = body(game, "void GameMode::showCampaignVictory(")
assert "Campaign::getSingleton().isActive()" in victory_ui
assert "MENU_CAMPAIGN" in body(game, "bool GameMode::onClickCampaignVictoryConfirm(")
for function in ("bool GameMode::onClickDefeatDebriefingConfirm(",
                 "bool GameMode::onClickYesQuitMenu("):
    route = body(game, function)
    assert "Campaign::getSingleton().isActive()" in route and "MENU_CAMPAIGN" in route

# Ensure FINAL has executable production-code coverage for the cases that static
# wiring cannot prove. Fixed names make accidental loss of a scenario visible.
probe = read("source/tests/check_campaign_save_probe.py")
for expectation in ("all record fields round trip", "recorded file wins over save filename",
                    "recorded difficulty overrides gameplay while menu difficulty stays changed",
                    "champion follows save despite absent current pieces",
                    "victory completes the played level and unlocks the next",
                    "finished difficulty is recorded hard and unlocks Hell",
                    "current complete Heartstone cannot override save without champion",
                    "recorded locked level loads without active campaign state",
                    "removed recorded level cannot fall back to a matching old filename",
                    "old save of unlocked campaign file is classified as campaign",
                    "old save of locked level stays ordinary",
                    "skirmish save remains ordinary and gets no campaign record",
                    "old campaign save takes current progress difficulty",
                    "old saves use Heartstone and difficulty of current progress",
                    "winning recorded save with no chosen creature clears unrelated progress carry-over",
                    "winning legacy save carries no creature from unrelated current progress",
                    "campaign list reorder restores by file, never old index"):
    assert expectation in probe, expectation
print("campaign save record, load effects, carry-over guard and campaign exit wiring: PASS")
print("Runtime campaign save probe is present; execution is deferred to FINAL")
