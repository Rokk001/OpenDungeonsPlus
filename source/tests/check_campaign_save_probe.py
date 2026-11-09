"""Compile and run the real campaign save/progress code. Run only in FINAL.

This probe needs the compiler environment, but no game, assets or third-party
libraries. The companion check_campaign_save.py checks the server/menu wiring.
"""
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]

PROBE = r'''
#include "game/Campaign.h"
#include "ai/KeeperAIType.h"
#include <iostream>
#include <sstream>
#include <string>

static int failures = 0;
static int checks = 0;

//! \brief Reports each fixed gameplay expectation without stopping the other cases.
static void check(bool condition, const char* message)
{
    ++checks;
    if(!condition)
    {
        ++failures;
        std::cerr << "FAIL: " << message << '\n';
    }
}

static const std::string definition =
    "[Level]\nFile=campaign/One.level\nTitle=First\n"
    "[Level]\nFile=campaign/Two.level\nTitle=Second\n"
    "[Level]\nFile=campaign/Bonus.level\nTitle=Hidden\nBonus=1\n";

//! \brief Starts every scenario with known progress and no disk writes.
static void fresh(const std::string& progress = "Difficulty 1\n")
{
    Campaign& campaign = Campaign::getSingleton();
    campaign.stopCampaign();
    campaign.setProgressPath("");
    std::istringstream levels(definition);
    check(campaign.importDefinition(levels), "test definition loads");
    std::istringstream saved(progress);
    check(campaign.importProgress(saved), "test progress loads");
}

//! \brief Runs save round trips, eligibility, restored effects and victory progression.
int main()
{
    Campaign& campaign = Campaign::getSingleton();
    const uint32_t hard = static_cast<uint32_t>(KeeperAIType::hard);
    const uint32_t easy = static_cast<uint32_t>(KeeperAIType::easy);
    fresh();
    check(!campaign.getSaveState().mPresent, "inactive skirmish has no campaign record");
    campaign.setDifficulty(hard);
    campaign.startLevel(0);
    campaign.discoverBonusLevel("campaign/Bonus.level");
    campaign.setKeptMinion("Worker", 7);
    CampaignSave state = campaign.getSaveState();
    check(state.mPresent && state.mValid, "campaign save carries a valid record");
    check(state.mLevelFile == "campaign/One.level", "record identifies level by file");
    check(state.mDifficulty == hard, "record stores played difficulty");
    check(state.mHeartstoneComplete, "record stores champion spell entitlement");
    check(state.mKeptClass == "Worker" && state.mKeptLevel == 7,
        "record stores the creature chosen for the next level");
    std::ostringstream encoded;
    state.exportInfo(encoded);
    check(encoded.str() == "Campaign\t1 campaign/One.level 2 1 Worker 7\n",
        "campaign record has stable versioned text format");
    CampaignSave decoded;
    check(decoded.importInfoLine(encoded.str()), "reader recognizes written record");
    check(decoded.mPresent && decoded.mValid && decoded.mLevelFile == "campaign/One.level" &&
        decoded.mDifficulty == hard && decoded.mHeartstoneComplete &&
        decoded.mKeptClass == "Worker" && decoded.mKeptLevel == 7, "all record fields round trip");

    fresh("Difficulty 0\nKeptMinion Fighter 11\n");
    check(campaign.findSavedLevel(decoded, "renamed.level") == 0,
        "recorded file wins over save filename");
    check(campaign.findSavedLevel(decoded, "2026-11-09_100000-MP-One.level") == 3,
        "multiplayer filename is never classified as campaign even with metadata");
    check(campaign.restoreSavedLevel(decoded, "renamed.level"), "unlocked recorded save loads as campaign");
    check(campaign.isActive() && campaign.getPlayedLevel() == 0 && !campaign.getPlayedLevelWon(),
        "restored campaign has the correct active level and unfinished result");
    check(campaign.getLevelDifficulty() == hard && campaign.getDifficulty() == easy,
        "recorded difficulty overrides gameplay while menu difficulty stays changed");
    check(campaign.isLevelHeartstoneComplete(), "champion follows save despite absent current pieces");
    CampaignSave resaved = campaign.getSaveState();
    check(resaved.mDifficulty == hard && resaved.mHeartstoneComplete &&
        resaved.mKeptClass == "Worker" && resaved.mKeptLevel == 7,
        "resaving keeps restored difficulty, champion and pending creature");
    check(campaign.onLevelWon(), "loaded campaign victory counts");
    check(campaign.isCompleted(0) && campaign.isUnlocked(1) && campaign.getPlayedLevelWon(),
        "victory completes the played level and unlocks the next");
    std::string className;
    uint32_t level = 0;
    check(campaign.takeKeptMinion(className, level) && className == "Worker" && level == 7,
        "restored pending creature goes to next level after victory");
    check(!campaign.takeKeptMinion(className, level), "next-level creature is consumed only once");

    CampaignSave finalState = decoded;
    finalState.mLevelFile = "campaign/Two.level";
    check(campaign.restoreSavedLevel(finalState, "final.level"), "unlocked final level restores");
    check(campaign.onLevelWon() && campaign.isFinished(), "loaded final victory finishes campaign");
    check(campaign.isHellUnlocked(), "finished difficulty is recorded hard and unlocks Hell");
    check(campaign.getDifficulty() == easy, "finishing loaded campaign preserves menu difficulty");
    std::ostringstream completed;
    campaign.exportProgress(completed);
    check(completed.str().find("Difficulty 0\n") != std::string::npos &&
        completed.str().find("Finished hard\n") != std::string::npos,
        "progress persists recorded completion difficulty and unchanged menu difficulty");

    fresh("Completed 1\nDifficulty 0\n");
    check(campaign.restoreSavedLevel(decoded, "first.level") && campaign.onLevelWon() &&
        campaign.isFinished() && campaign.isHellUnlocked() && campaign.getDifficulty() == easy,
        "any loaded level completing campaign records saved difficulty, regardless of list position");

    fresh("Difficulty 1\nDiscovered 2\n");
    CampaignSave withoutChampion = decoded;
    withoutChampion.mHeartstoneComplete = false;
    check(campaign.restoreSavedLevel(withoutChampion, "first.level") && !campaign.isLevelHeartstoneComplete(),
        "current complete Heartstone cannot override save without champion");
    check(campaign.getSaveState().mHeartstoneComplete == false,
        "resave does not acquire champion from current progress");

    fresh();
    CampaignSave locked = decoded;
    locked.mLevelFile = "campaign/Two.level";
    check(campaign.findSavedLevel(locked, "first.level") == 3,
        "recorded locked level is classified as ordinary save");
    campaign.startLevel(0);
    check(!campaign.restoreSavedLevel(locked, "first.level") && !campaign.isActive(),
        "recorded locked level loads without active campaign state");
    check(!campaign.onLevelWon() && !campaign.hasProgress(),
        "ordinary fallback victory cannot change campaign progress");
    CampaignSave missing = decoded;
    missing.mLevelFile = "campaign/Removed.level";
    check(campaign.findSavedLevel(missing, "2026-11-09_100000-SK-One.level") == 3 &&
        !campaign.restoreSavedLevel(missing, "2026-11-09_100000-SK-One.level"),
        "removed recorded level cannot fall back to a matching old filename");

    CampaignSave legacy;
    check(!legacy.mPresent, "old save starts with no record");
    check(campaign.findSavedLevel(legacy, "2026-11-09_100000-SK-One.level") == 0,
        "old save of unlocked campaign file is classified as campaign");
    check(campaign.findSavedLevel(legacy, "2026-11-09_100000-SK-Two.level") == 3,
        "old save of locked level stays ordinary");
    check(!campaign.restoreSavedLevel(legacy, "2026-11-09_100000-SK-Two.level"),
        "old locked save loads without campaign");
    check(!campaign.restoreSavedLevel(legacy, "2026-11-09_100000-SK-Arena.level") &&
        !campaign.isActive() && !campaign.getSaveState().mPresent,
        "skirmish save remains ordinary and gets no campaign record");
    campaign.setKeptMinion("StaleCreature", 29);
    check(campaign.restoreSavedLevel(legacy, "2026-11-09_100000-SK-One.level"),
        "old unlocked campaign save restores");
    check(campaign.getLevelDifficulty() == static_cast<uint32_t>(KeeperAIType::normal),
        "old campaign save takes current progress difficulty");
    check(!campaign.isLevelHeartstoneComplete() && campaign.getSaveState().mKeptClass.empty(),
        "old campaign save has no pending creature or champion from stale state");
    std::ostringstream noCreature;
    campaign.getSaveState().exportInfo(noCreature);
    check(noCreature.str() == "Campaign\t1 campaign/One.level 1 0 - 0\n",
        "new record for a legacy save explicitly stores no pending creature");
    campaign.stopCampaign();
    check(!campaign.isActive() && !campaign.hasProgress() && !campaign.getPlayedLevelWon(),
        "quitting or losing before victory does not complete a level");
    fresh("Difficulty 3\nDiscovered 2\n");
    check(campaign.restoreSavedLevel(legacy, "2026-11-09_100000-SK-One.level") &&
        campaign.isLevelHeartstoneComplete() && campaign.getLevelDifficulty() == 3,
        "old saves use Heartstone and difficulty of current progress");

    fresh("Difficulty 1\nKeptMinion Fighter 11\n");
    CampaignSave noPending = decoded;
    noPending.mKeptClass.clear();
    noPending.mKeptLevel = 0;
    check(campaign.restoreSavedLevel(noPending, "first.level"), "recorded save without chosen creature restores");
    std::ostringstream beforeQuit;
    campaign.exportProgress(beforeQuit);
    check(beforeQuit.str().find("KeptMinion Fighter 11\n") != std::string::npos,
        "loading does not consume or replace current progress creature");
    campaign.stopCampaign();
    std::ostringstream afterQuit;
    campaign.exportProgress(afterQuit);
    check(beforeQuit.str() == afterQuit.str(), "quitting loaded level preserves current progress creature");
    check(campaign.restoreSavedLevel(noPending, "first.level") && campaign.onLevelWon() &&
        !campaign.takeKeptMinion(className, level),
        "winning recorded save with no chosen creature clears unrelated progress carry-over");
    fresh("Difficulty 1\nKeptMinion Fighter 11\n");
    check(campaign.restoreSavedLevel(legacy, "2026-11-09_100000-SK-One.level") && campaign.onLevelWon() &&
        !campaign.takeKeptMinion(className, level),
        "winning legacy save carries no creature from unrelated current progress");

    campaign.stopCampaign();
    std::istringstream reordered(
        "[Level]\nFile=campaign/Two.level\n[Level]\nFile=campaign/One.level\n");
    campaign.importDefinition(reordered);
    std::istringstream reorderedProgress("Completed 0\nDifficulty 0\n");
    campaign.importProgress(reorderedProgress);
    check(campaign.findSavedLevel(decoded, "renamed.level") == 1 &&
        campaign.restoreSavedLevel(decoded, "renamed.level") && campaign.getPlayedLevel() == 1,
        "campaign list reorder restores by file, never old index");

    CampaignSave malformed;
    check(malformed.importInfoLine("Campaign\t1 campaign/One.level 99 1 Worker 7") &&
        malformed.mPresent && !malformed.mValid, "invalid recorded difficulty is not accepted");
    check(!campaign.restoreSavedLevel(malformed, "2026-11-09_100000-SK-One.level"),
        "malformed record cannot masquerade as a legacy save");
    CampaignSave future;
    check(future.importInfoLine("Campaign\t2 campaign/One.level 1 1 - 0") &&
        future.mPresent && !future.mValid, "unknown campaign record versions stay in ordinary fallback");
    CampaignSave truncated;
    check(truncated.importInfoLine("Campaign\t1 campaign/One.level 1") && !truncated.mValid,
        "incomplete campaign records cannot activate a campaign");
    CampaignSave unrelated;
    check(!unrelated.importInfoLine("Name\tFirst level"), "ordinary info line is not a campaign record");
    std::ostringstream empty;
    unrelated.exportInfo(empty);
    check(empty.str().empty(), "ordinary save writes no campaign metadata");
    std::cout << "campaign save probe: checks=" << checks << " failures=" << failures << '\n';
    return failures == 0 ? 0 : 1;
}
'''

with tempfile.TemporaryDirectory(prefix="odp-campaign-save-") as directory:
    work = Path(directory)
    (work / "probe.cpp").write_text(PROBE, encoding="utf-8")
    subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++14",
                    f"/I{ROOT / 'source'}", "probe.cpp",
                    str(ROOT / "source/game/Campaign.cpp"), "/Feprobe.exe"],
                   cwd=work, check=True)
    subprocess.run([str(work / "probe.exe")], cwd=work, check=True)
