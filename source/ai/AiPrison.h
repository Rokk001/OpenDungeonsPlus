#ifndef AIPRISON_H
#define AIPRISON_H

#include <string>
#include <set>

class KeeperAI;
class Tile;

namespace PRIS
{
//! \brief Per-mind decisions that must survive saving and loading.
struct State
{
    std::set<std::string> triedPrisoners;
    std::set<std::string> acceptedPrisoners;
    std::set<std::string> pendingPrisoners;
};
//! \brief Resolves a queued prisoner pickup against the current game state.
void pickup(KeeperAI& ai, Tile* tile, const std::string& name);
//! \brief Resolves a queued prisoner drop and releases its pending status.
void drop(KeeperAI& ai, State& state, Tile* tile, const std::string& name);
//! \brief Moves old enough prisoners to torture, drawing conversion neglect only once per prisoner.
void tortureStep(KeeperAI& ai, State& state);
//! \brief Restores the name of a prisoner whose one-time decision has already been drawn.
void importDraw(State& state, const std::string& name, const std::string& value);
}

#endif // AIPRISON_H
