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

#ifndef AIMATH_H
#define AIMATH_H

// Pure functions of the keeper AI levels. This header includes only standard headers
// (no game header, no Ogre, no logging) so that the unit tests can link it alone.
// Five-element arrays are ordered allin, single, split, raid, counter.

#include <array>
#include <deque>
#include <functional>
#include <string>
#include <utility>
#include <vector>

namespace AiMath
{
//! \brief One uniform draw in [0, 1). The Mind passes Random::Double(0.0, 1.0), the tests a fixed sequence;
//! a normal draw is made from two uniform draws (Box-Muller).
using Uniform01 = std::function<double()>;

//! \brief How the keeper notices a trigger, which decides the reaction delay.
enum class ReactionKind { alert, symptom, periodic, internal, hardLimit };

//! \brief The level and scheduler values the reaction delays read.
struct DelayParams { double rho, pi, scanPeriod, symptomScanFactor, periodicMinDelay, latencyMean, latencySd; };

//! \brief The one-hand state of the click budget (the hand and click lines of the saved AI state).
struct HandState
{
    double busyUntil = 0.0;
    double lastClickEnd = -1.0e18;
    //! \brief (start time, clicks) of every click group inside the last ClickWindowSeconds.
    std::deque<std::pair<double, int>> clickGroups;
};

//! \brief One researched damage spell: damage per target, number of targets and mana price.
struct SpellOption { double damagePerTarget, targets, price; };

//! \brief One trap kind of a trap set: tile count, reload time, mean remaining shots per tile,
//! damage per shot, targets per shot and whether it is a spike trap.
struct TrapKindSet { int tiles; double reloadSeconds, shots, damagePerShot, targets; bool spike; };

//! \brief The war model keys and the two shares the formulas read.
struct WarConstants
{
    double doorTimeCap, fightEstimateDamageShare, estimateSetupSeconds, estimateRoomTiles, estimateTileHp, heartHealMargin,
           heartBreakFallbackSeconds, potentialCastsMax, potentialCastsBase, potentialCastPeriod, spellPotentialEff, spellManaReserve,
           maxManaPerSeat, trapEff, trapPassSeconds, advFloor, advHpFloorShare, enemyHpFloorShare, strengthRatioCap, scorePenaltyBase,
           scorePenaltyAllin, scorePenaltySingle, scorePenaltySplit, scorePenaltyRaid, scorePenaltyCounter, scorePenaltyCounterFactor,
           bonusSplit, bonusRaidBase, bonusRaidGold, bonusRaidGoldDivisor, bonusCounter, groupShareSingle, groupShareMain,
           groupShareRaidTactic, counterArmyShare;
};

//! \brief The inputs of the advantage of an attack, with the estimate of the enemy.
struct AdvantageInput
{
    //! \brief Hit points and damage per second of all own eligible fighters.
    double hpAll, dpsAll;
    //! \brief Door hit points, heart hit points and heart healing of the enemy, assumed like the own.
    double ownDoorHp, heartHp, heartHeal;
    //! \brief Own damage spells (Inferno and Tremor only) and own mana.
    std::vector<SpellOption> mySpells; double myMana;
    //! \brief Enemy damage spells (taken from the own list) and the estimated enemy mana.
    std::vector<SpellOption> enemySpells; double enemyMana;
    //! \brief Enemy trap set, its ready share, the trap factor and the ready flag of the estimate.
    std::vector<TrapKindSet> trapSet; double trapReady, trapFactor, estimateReady;
    //! \brief Estimated hit points and damage per second of the enemy.
    double enemyHp, enemyDps;
    //! \brief The AttackAdvantage value of the level.
    double attackAdvantage;
};

//! \brief The scores of the five tactics; valid[4] (counter) is true only while the enemy assault is out.
struct TacticScores { std::array<double, 5> score; std::array<bool, 5> valid; };

//! \brief One line of the saved AI state: the tag and the tokens after it.
struct AiStateLine { std::string tag; std::vector<std::string> tokens; };

//! \brief Probability of a mistake: base x rowMultiplier x levelMultiplier, clipped to [minP, maxP].
double mistakeProbability(double base, double rowMultiplier, double levelMultiplier, double minP, double maxP);

//! \brief A standard normal draw N(0, 1), made with Box-Muller from two uniform draws.
double normalDraw(const Uniform01& u);

//! \brief A lognormal draw exp(ln(median) + sigma x normalDraw(u)).
double lognormalMedian(double median, double sigma, const Uniform01& u);

//! \brief The action latency: a lognormal draw with the given mean and standard deviation.
double latency(double mean, double sd, const Uniform01& u);

//! \brief The delay from a trigger to the first action for the given reaction kind, latency included.
double reactionDelay(ReactionKind kind, const DelayParams& p, const Uniform01& u);

//! \brief The interval to the next periodic look of a topic with the given look factor (no latency).
double lookInterval(double factor, const DelayParams& p, const Uniform01& u);

//! \brief Schedules one action on the hand under the click budget and updates the hand state.
//! \param due Earliest start time.
//! \param clicks Clicks of the action (0 for a mental step).
//! \param seconds Duration of the action.
//! \param clicksPerWindow Allowed clicks per window (ClickShare x ClickBudgetPerMinute).
//! \param minGap Minimum time between the end of one click action and the start of the next.
//! \param windowSeconds Length of the rolling click window.
//! \return The end time of the action.
double clickSchedule(HandState& hand, double due, int clicks, double seconds, double clicksPerWindow,
                     double minGap, double windowSeconds);

//! \brief Damage the given spells can deal with the mana during a fight of fightSeconds.
double spellPotential(const std::vector<SpellOption>& options, double mana, double fightSeconds, const WarConstants& k);

//! \brief Damage a trap set deals to attackers that need doorSeconds at the doors, with the ready share.
double trapPotential(const std::vector<TrapKindSet>& set, double doorSeconds, double ready, const WarConstants& k);

//! \brief The advantage of an attack with the share frac of the own fighters and the tactic bonus.
//! \param heart True when the target is the enemy heart, false for rooms.
double advantage(const AdvantageInput& in, double frac, double bonus, bool heart, const WarConstants& k);

//! \brief The scores of the five tactics.
//! \param enemyGoldEstimate Estimated enemy gold (raid bonus).
//! \param enemyOut True while the enemy assault is out (counter is valid only then).
TacticScores tacticScores(const AdvantageInput& in, double enemyGoldEstimate, bool enemyOut, const WarConstants& k);

//! \brief Index round(share x n) into the list of the n ready fighters, strongest first.
int takeIndex(double share, int n);

//! \brief Writes the lines of the saved AI state, one item per line, tag first.
std::vector<std::string> formatAiState(const std::vector<AiStateLine>& lines);

//! \brief Reads the lines of the saved AI state.
//! \return false on an unknown tag or a wrong token count.
bool parseAiState(const std::vector<std::string>& lines, std::vector<AiStateLine>& out);
}

#endif // AIMATH_H
