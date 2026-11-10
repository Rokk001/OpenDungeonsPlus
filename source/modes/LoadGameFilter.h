#ifndef LOADGAMEFILTER_H
#define LOADGAMEFILTER_H

#include "gamemap/MapHandler.h"

#include <algorithm>
#include <ctime>
#include <vector>

//! \brief Classifies a save using the same campaign eligibility as loading.
inline int classifyLoadSave(const std::string& filename, bool valid, const LevelInfo& info, const Campaign& campaign)
{
    size_t mp = filename.find("MP-");
    size_t sk = filename.find("SK-");
    if(mp != std::string::npos && (sk == std::string::npos || mp < sk))
        return -1;
    if(valid && campaign.findSavedLevel(info.mCampaignSave, filename) < campaign.getNumLevels())
        return 0;
    return valid && info.mIsSandbox ? 2 : 1;
}

//! \brief A file offered by the load screen with its filter kind (0 Campaign, 1 Skirmish, 2 Sandbox, 3 Replays).
struct LoadEntry
{
    std::string mPath;
    std::time_t mModified;
    int mKind;
};

//! \brief Orders entries newest first, breaking ties by path.
inline bool newerLoadEntry(const LoadEntry& left, const LoadEntry& right)
{
    return left.mModified == right.mModified ? left.mPath < right.mPath : left.mModified > right.mModified;
}

//! \brief Kind of the newest entry of all kinds, Campaign (0) when there is none.
inline int openingLoadKind(const std::vector<LoadEntry>& entries)
{
    int kind = 0;
    std::time_t newest = 0;
    bool any = false;
    for(const LoadEntry& entry : entries)
    {
        if(!any || entry.mModified > newest)
        {
            any = true;
            newest = entry.mModified;
            kind = entry.mKind;
        }
    }
    return kind;
}

//! \brief Entries of one kind, newest first.
inline std::vector<LoadEntry> visibleLoadEntries(const std::vector<LoadEntry>& entries, int kind)
{
    std::vector<LoadEntry> result;
    for(const LoadEntry& entry : entries)
        if(entry.mKind == kind)
            result.push_back(entry);
    std::sort(result.begin(), result.end(), newerLoadEntry);
    return result;
}

//! \brief What confirming does: 0 nothing, 1 load a saved game, 2 play a replay.
inline int loadConfirmAction(int kind, bool hasSelection)
{
    return !hasSelection ? 0 : (kind == 3 ? 2 : 1);
}

#endif
