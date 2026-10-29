#ifndef AIEVENTS_H
#define AIEVENTS_H

#include "ai/AiMind.h"
#include <cstdint>
#include <map>
#include <string>

class KeeperAI;

//! \brief Observes keeper-visible symptoms and retains their edges across saved games.
class AiEvents
{
public:
    //! \brief Associates the event source with its keeper without owning it.
    explicit AiEvents(KeeperAI& ai);
    //! \brief Registers the poll and persistence callbacks with the keeper's mind.
    void bind();
    //! \brief Observes raw game notices before their reaction delay or mistake draw.
    void notify(const AiEvent& event);

private:
    //! \brief Restores the event source's own persistent counters once the mind has loaded.
    void load();
    //! \brief Polls visible symptoms once per AiPollSeconds through the mind's poll timer.
    bool poll();
    //! \brief Queues only a rising edge, retaining the event's visible location.
    void edge(const std::string& name, AiEventType type, bool value, Tile* tile = nullptr);
    //! \brief Writes this source's counters and relative times as I06 draw records.
    void save(std::vector<AiMath::AiStateLine>& lines);
    //! \brief Reads the build owner's published next look without drawing an extra periodic timer.
    double buildLookDue();

    KeeperAI& mAi;
    bool mLoaded;
    bool mPayday;
    bool mArrival;
    bool mPendingArrival;
    double mBuildDue;
    uint32_t mPotions;
    std::map<std::string, bool> mEdges;
};

#endif // AIEVENTS_H
