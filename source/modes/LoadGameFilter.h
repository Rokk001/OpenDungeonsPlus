#ifndef LOADGAMEFILTER_H
#define LOADGAMEFILTER_H

#include "gamemap/MapHandler.h"

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

#endif
