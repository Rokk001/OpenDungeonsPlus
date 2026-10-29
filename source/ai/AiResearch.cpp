/*!
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  This program is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 *
 *  You should have received a copy of the GNU General Public License
 *  along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "ai/AiResearch.h"

#include "ai/AiActions.h"
#include "ai/AiMath.h"
#include "ai/AiMind.h"
#include "ai/KeeperAI.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/Skill.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <iomanip>
#include <limits>
#include <functional>
#include <sstream>
#include <vector>

namespace
{
//! \brief Restores research-owned saved lines after the Mind loads its state.
RES::ResearchState& stateFor(KeeperAI& ai)
{
    RES::ResearchState& state = ai.getResearchState();
    if(!state.mLoaded)
    {
        state.mLoaded = true;
        for(const AiMath::AiStateLine& line : ai.getMind().savedRows())
        {
            if(line.tag != "draw" || line.tokens.size() != 3)
                continue;
            if(line.tokens[0] == "C01" && line.tokens[1] == "tunnel")
                state.mTunnelOpen = line.tokens[2] == "1";
            if(line.tokens[0] == "C02" && line.tokens[1] == "nextLook")
            {
                std::istringstream input(line.tokens[2]);
                input >> state.mNextLook;
                state.mNextLook += ai.getMind().now();
            }
        }
    }
    return state;
}

//! \brief Returns the number of level-one entries still needed for the tab's next gate.
int gateDistance(const Seat& seat, SkillType type)
{
    std::vector<SkillType> entries;
    SkillManager::listTabSkills(SkillManager::getSkillTab(type), entries);
    int allowed = 0;
    int done = 0;
    for(SkillType entry : entries)
    {
        if(seat.isSkillNotAllowed(entry))
            continue;
        ++allowed;
        if(seat.getSkillLevel(entry) > 0)
            ++done;
    }
    const int half = (allowed + 1) / 2;
    if(done == allowed)
        return std::numeric_limits<int>::max();
    return done < half ? half - done : allowed - done;
}

//! \brief Orders equal-cost entries by tab gate distance and the reference tree order.
bool cheaper(const Seat& seat, SkillType left, SkillType right)
{
    const int32_t leftCost = SkillManager::getSkill(left)->getNeededSkillPoints(seat.getSkillLevel(left) + 1);
    const int32_t rightCost = SkillManager::getSkill(right)->getNeededSkillPoints(seat.getSkillLevel(right) + 1);
    if(leftCost != rightCost)
        return leftCost < rightCost;
    const int leftGate = gateDistance(seat, left);
    const int rightGate = gateDistance(seat, right);
    if(leftGate != rightGate)
        return leftGate < rightGate;
    const uint32_t leftTier = SkillManager::getSkillTier(left);
    const uint32_t rightTier = SkillManager::getSkillTier(right);
    if(leftTier != rightTier)
        return leftTier < rightTier;
    return Skills::toString(left) < Skills::toString(right);
}

//! \brief Supplies the uniform draw used by the shared symptom-delay formula.
double uniformDraw()
{
    return Random::Double(0.0, 1.0);
}
//! \brief Refills research after the shared queue-empty symptom delay.
void queueEmptyEvent(KeeperAI& ai, const AiEvent&)
{
    RES::refillQueue(ai);
}

//! \brief Records only a tunnel opening reported to this keeper's Mind.
void tunnelOpenEvent(KeeperAI& ai, const AiEvent&)
{
    stateFor(ai).mTunnelOpen = true;
}

//! \brief Reports whether this keeper's library lacks a queued entry.
bool queueEmpty(KeeperAI& ai)
{
    return ai.getControlledPlayer().getSeat()->getSkillPending().empty();
}

//! \brief Saves the known tunnel and the remaining retry delay for clock-relative restoration.
void saveState(KeeperAI& ai, std::vector<AiMath::AiStateLine>& lines)
{
    const RES::ResearchState& state = stateFor(ai);
    const std::function<bool(const AiMath::AiStateLine&)> owned = [](const AiMath::AiStateLine& line)
    {
        return line.tag == "draw" && !line.tokens.empty() && (line.tokens[0] == "C01" || line.tokens[0] == "C02");
    };
    lines.erase(std::remove_if(lines.begin(), lines.end(), owned), lines.end());
    std::ostringstream remaining;
    remaining << std::setprecision(std::numeric_limits<double>::max_digits10) <<
        std::max(0.0, state.mNextLook - ai.getMind().now());
    lines.push_back({"draw", {"C01", "tunnel", state.mTunnelOpen ? "1" : "0"}});
    lines.push_back({"draw", {"C02", "nextLook", remaining.str()}});
}
}

namespace RES
{
//! \brief Selects a legal entry, applying defence, attack-spell and cheapest-first precedence.
SkillType chooseResearch(KeeperAI& ai)
{
    // AI row C01
    // AI row C03
    // AI row C04
    // AI row C05
    // AI row C06
    const Seat& seat = *ai.getControlledPlayer().getSeat();
    const ConfigManager& cfg = ConfigManager::getSingleton();
    RES::ResearchState& state = stateFor(ai);
    std::vector<SkillType> candidates;
    const std::vector<std::pair<SkillType, int>> none;
    for(int index = 1; index < static_cast<int>(SkillType::countSkill); ++index)
    {
        const SkillType type = static_cast<SkillType>(index);
        if(Skills::isRewardSkill(type) || SkillManager::getSkill(type) == nullptr ||
            std::find(state.mQueue.begin(), state.mQueue.end(), type) != state.mQueue.end())
            continue;
        if(seat.canResearchLevel(type, static_cast<int>(seat.getSkillLevel(type)) + 1, none))
            candidates.push_back(type);
    }
    if(candidates.empty())
        return SkillType::nullSkillType;

    // The shared Mind caches a row per callback; research requires a fresh C01 draw for each pick.
    const ConfigManager::AiRowClass* row = cfg.getAiRowClass("C01");
    const double mistake = row == nullptr ? 0.0 : AiMath::mistakeProbability(
        cfg.getAiConfigDouble("MistakeBaseRule"), row->mMultiplier, ai.getSettings().mistakeMultiplier,
        cfg.getAiConfigDouble("MistakeMin"), cfg.getAiConfigDouble("MistakeMax"));
    if(Random::Double(0.0, 1.0) < mistake)
        return candidates[Random::Uint(0, static_cast<unsigned int>(candidates.size()) - 1)];

    const std::function<bool(SkillType, SkillType)> order = [&seat](SkillType left, SkillType right)
    {
        return cheaper(seat, left, right);
    };
    std::sort(candidates.begin(), candidates.end(), order);
    if(ai.getMind().now() / 60.0 < cfg.getAiConfigDouble("AttackMinMinute") && !state.mTunnelOpen)
    {
        const std::vector<SkillType> defence = {SkillType::roomWorkshop, SkillType::trapSpike,
            SkillType::trapCannon, SkillType::trapGas, SkillType::trapDoorIronbound,
            SkillType::trapDoorSteel, SkillType::keeperHeartFortitude, SkillType::keeperHeartMending};
        for(SkillType type : candidates)
        {
            if(std::find(defence.begin(), defence.end(), type) != defence.end())
                return type;
        }
    }
    const std::vector<SkillType> attack = {SkillType::spellCreatureExplosion, SkillType::spellInferno,
        SkillType::spellLightning, SkillType::spellTremor};
    for(SkillType type : attack)
    {
        if(type == SkillType::spellInferno && seat.getManaIncomePerSecond() * cfg.getAiConfigDouble("LookPeriod600") <
            cfg.getAiConfigDouble("InfernoReserveCasts") * cfg.getSpellConfigInt32("InfernoPrice"))
            continue;
        if(std::find(candidates.begin(), candidates.end(), type) != candidates.end())
            return type;
    }
    // The reference cheapest-first order always researches the library before other entries.
    if(std::find(candidates.begin(), candidates.end(), SkillType::roomLibrary) != candidates.end())
        return SkillType::roomLibrary;
    return candidates.front();
}

//! \brief Queues the configured number of entries on an idle library look and starts its symptom retry delay.
void refillQueue(KeeperAI& ai)
{
    // AI row C02
    RES::ResearchState& state = stateFor(ai);
    const Seat& seat = *ai.getControlledPlayer().getSeat();
    if(!seat.getSkillPending().empty() || ai.getMind().now() < state.mNextLook)
        return;
    state.mQueue.clear();
    const ConfigManager& cfg = ConfigManager::getSingleton();
    for(int count = 0; count < cfg.getAiConfigInt32("ResearchQueueEntries"); ++count)
    {
        const SkillType type = chooseResearch(ai);
        if(type == SkillType::nullSkillType)
            break;
        state.mQueue.push_back(type);
    }
    if(state.mQueue.empty())
        return;
    ACTS::setResearch(ai, state.mQueue);
    const AiSettings& settings = ai.getSettings();
    const AiMath::DelayParams delay = {settings.rho, settings.pi, settings.scanPeriod,
        cfg.getAiConfigDouble("SymptomScanFactor"), cfg.getAiConfigDouble("PeriodicMinDelay"),
        cfg.getAiConfigDouble("ActionLatencyMean"), cfg.getAiConfigDouble("ActionLatencySd")};
    state.mNextLook = ai.getMind().now() + AiMath::reactionDelay(AiMath::ReactionKind::symptom, delay, uniformDraw);
    state.mQueue.clear();
}

//! \brief Binds the shared research look, queue-empty symptom, tunnel observation and save lines.
void bind(KeeperAI& ai)
{
    ai.getResearchState() = ResearchState();
    ai.getMind().onLook("C02", ConfigManager::getSingleton().getAiConfigDouble("LookFactorScan"),
        std::bind(refillQueue, std::ref(ai)));
    ai.getMind().onLook("C03", ConfigManager::getSingleton().getAiConfigDouble("LookPeriod600") /
        ConfigManager::getSingleton().getAiConfigDouble("ReferenceScanPeriod"),
        std::bind(refillQueue, std::ref(ai)));
    ai.getMind().onEvent("C01", {AiEventType::NoSkillInQueue},
        std::bind(queueEmptyEvent, std::ref(ai), std::placeholders::_1));
    ai.getMind().onPoll("C02", AiEventType::NoSkillInQueue, std::bind(queueEmpty, std::ref(ai)));
    ai.getMind().onEvent("C03", {AiEventType::TunnelOpen},
        std::bind(tunnelOpenEvent, std::ref(ai), std::placeholders::_1));
    ai.getMind().onSave(std::bind(saveState, std::ref(ai), std::placeholders::_1));
}
}
