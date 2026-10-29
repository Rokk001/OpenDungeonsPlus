#ifndef AIPRISON_H
#define AIPRISON_H

#include <string>
#include <set>
#include <vector>

class KeeperAI;

namespace PRIS
{
//! \brief Per-mind decisions that must survive saving and loading.
struct State
{
    std::set<std::string> triedPrisoners;
};
//! \brief Moves old enough prisoners to torture, drawing conversion neglect only once per prisoner.
void tortureStep(KeeperAI& ai, State& state);
//! \brief Returns the persistent prisoner decisions as tokens for the Mind's draw lines.
std::vector<std::string> exportDraws(const State& state);
//! \brief Restores the name of a prisoner whose one-time decision has already been drawn.
void importDraw(State& state, const std::string& name, const std::string& value);
}

#endif // AIPRISON_H
