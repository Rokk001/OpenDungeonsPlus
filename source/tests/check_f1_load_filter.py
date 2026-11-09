"""Check the unified load screen wiring and exercise real save classification."""
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
load = (ROOT / "source/modes/MenuModeLoad.cpp").read_text(encoding="utf-8")
layout = ET.parse(ROOT / "gui/MenuLoad.layout")
assert '"Campaign", "Skirmish", "Sandbox", "Replays"' in load
assert len(layout.findall('.//Window[@name="KindFilter"]')) == 1
assert 'name="Sort" value="False"' in (ROOT / "gui/MenuLoad.layout").read_text()
assert 'std::sort(mFilesList.begin(), mFilesList.end(), newerLoadFile)' in load
assert 'return a == b ? left < right : a > b;' in load
assert 'size_t newestKind = 0;' in load and 'if(modified > newestTime)' in load
assert 'filter->setItemSelectState(newestKind, true)' in load
assert 'if(levelSelectList->getSelectedCount() == 0)' in load
assert 'ODClient::getSingleton().replay(level)' in load
assert 'updateFilesList();\n    return true;\n}\n\n//! \\brief Shows the selected' in load

PROBE = r'''
#include "modes/LoadGameFilter.h"
#include <sstream>
#include <iostream>
//! \brief Checks save categories with a locked second campaign level.
int main()
{
    Campaign& campaign = Campaign::getSingleton();
    std::istringstream levels("[Level]\nFile=campaign/One.level\n[Level]\nFile=campaign/Two.level\n");
    std::istringstream progress("Difficulty 1\n");
    if(!campaign.importDefinition(levels) || !campaign.importProgress(progress)) return 1;
    LevelInfo info;
    if(classifyLoadSave("2026-SK-One.level", true, info, campaign) != 0) return 2;
    if(classifyLoadSave("2026-SK-Two.level", true, info, campaign) != 1) return 3;
    info.mCampaignSave.importInfoLine("Campaign\t1 campaign/One.level 1 0 - 0");
    if(classifyLoadSave("renamed.level", true, info, campaign) != 0) return 4;
    info.mCampaignSave.importInfoLine("Campaign\t1 campaign/Two.level 1 0 - 0");
    if(classifyLoadSave("renamed.level", true, info, campaign) != 1) return 5;
    info = LevelInfo();
    info.mIsSandbox = true;
    if(classifyLoadSave("2026-SK-Sandbox.level", true, info, campaign) != 2) return 6;
    if(classifyLoadSave("2026-MP-One.level", true, info, campaign) != -1) return 7;
    info.mIsSandbox = false;
    if(classifyLoadSave("2026-SK-Arena.level", true, info, campaign) != 1) return 8;
    std::cout << "F1 classification: 7 cases passed\n";
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="odp-f1-") as directory:
    work = Path(directory)
    (work / "probe.cpp").write_text(PROBE, encoding="utf-8")
    subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++14", f"/I{ROOT / 'source'}",
                    "probe.cpp", str(ROOT / "source/game/Campaign.cpp"), "/Feprobe.exe"], cwd=work, check=True)
    subprocess.run([str(work / "probe.exe")], cwd=work, check=True)
print("F1 menu wiring: PASS")
