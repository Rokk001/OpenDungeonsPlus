/*!
 *  Copyright (C) 2011-2016  OpenDungeons Team
 *
 *  This program is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 */

#include "ai/AiMath.h"

#include <algorithm>
#include <cmath>
#include <sstream>
#include <limits>

namespace AiMath
{
//! \brief Calculates the clipped mistake probability for a catalogue row.
double mistakeProbability(double base, double rowMultiplier, double levelMultiplier, double minP, double maxP)
{
    return std::max(minP, std::min(maxP, base * rowMultiplier * levelMultiplier));
}

//! \brief Draws a standard normal value from two uniform draws.
double normalDraw(const Uniform01& u)
{
    const double first = std::max(u(), std::numeric_limits<double>::min());
    const double second = u();
    return std::sqrt(-2.0 * std::log(first)) * std::cos(2.0 * std::acos(-1.0) * second);
}

//! \brief Draws a lognormal value with the specified median.
double lognormalMedian(double median, double sigma, const Uniform01& u)
{
    return std::exp(std::log(median) + sigma * normalDraw(u));
}

//! \brief Draws action latency from its mean and standard deviation.
double latency(double mean, double sd, const Uniform01& u)
{
    const double sigma = std::sqrt(std::log(1.0 + (sd / mean) * (sd / mean)));
    return std::exp(std::log(mean) - sigma * sigma / 2.0 + sigma * normalDraw(u));
}

//! \brief Rounds a group boundary to the nearest even integer.
int takeIndex(double share, int n)
{
    return static_cast<int>(std::nearbyint(share * n));
}

//! \brief Draws the interval until the next periodic look.
double lookInterval(double factor, const DelayParams& p, const Uniform01& u)
{
    return std::max(p.periodicMinDelay, -std::log(1.0 - u()) * p.scanPeriod * factor);
}

//! \brief Draws the delay appropriate for the trigger kind.
double reactionDelay(ReactionKind kind, const DelayParams& p, const Uniform01& u)
{
    if(kind == ReactionKind::internal || kind == ReactionKind::hardLimit)
        return 0.0;
    if(kind == ReactionKind::periodic)
        return lookInterval(1.0, p, u);
    double mean = p.scanPeriod;
    if(kind == ReactionKind::alert && u() < p.pi)
        mean = 60.0 / p.rho;
    if(kind == ReactionKind::symptom)
        mean *= p.symptomScanFactor * (2.0 - p.pi);
    return -std::log(1.0 - u()) * mean + latency(p.latencyMean, p.latencySd, u);
}

//! \brief Estimates damage available from the most efficient spell.
double spellPotential(const std::vector<SpellOption>& options, double mana, double fightSeconds, const WarConstants& k)
{
    const SpellOption* best = nullptr;
    for(const SpellOption& option : options)
    {
        if(option.price > 0.0 && (best == nullptr || option.damagePerTarget * option.targets / option.price > best->damagePerTarget * best->targets / best->price))
            best = &option;
    }
    if(best == nullptr)
        return 0.0;
    const double casts = std::min(k.potentialCastsMax, std::floor(k.potentialCastsBase + fightSeconds / k.potentialCastPeriod));
    const double usable = std::max(0.0, mana - k.spellManaReserve * k.maxManaPerSeat);
    return std::min(casts, std::floor(usable / best->price)) * best->damagePerTarget * best->targets * k.spellPotentialEff;
}

//! \brief Estimates damage from the available trap shots.
double trapPotential(const std::vector<TrapKindSet>& set, double doorSeconds, double ready, const WarConstants& k)
{
    double total = 0.0;
    for(const TrapKindSet& trap : set)
    {
        const double exposure = k.trapPassSeconds + (trap.spike ? 0.0 : doorSeconds);
        const double fires = std::min(trap.shots * trap.tiles * ready, trap.tiles * (1.0 + exposure / trap.reloadSeconds));
        total += fires * trap.damagePerShot * trap.targets;
    }
    return total * k.trapEff;
}


//! \brief Estimates the logarithmic advantage of an assault.
double advantage(const AdvantageInput& in, double frac, double bonus, bool heart, const WarConstants& k)
{
    const double doorSeconds = std::min(k.doorTimeCap, in.ownDoorHp / std::max(1.0, frac * in.dpsAll));
    const double dp = std::max(1.0, k.fightEstimateDamageShare * frac * in.dpsAll);
    const double fightSeconds = doorSeconds + k.estimateSetupSeconds + (heart ?
        (dp > in.heartHeal + k.heartHealMargin ? in.heartHp / (dp - in.heartHeal) : k.heartBreakFallbackSeconds) :
        k.estimateRoomTiles * k.estimateTileHp / dp);
    const double mySpell = spellPotential(in.mySpells, in.myMana, fightSeconds, k);
    const double enemySpell = spellPotential(in.enemySpells, in.enemyMana, fightSeconds, k);
    const double traps = trapPotential(in.trapSet, doorSeconds, in.trapReady, k) * in.trapFactor * in.estimateReady;
    const double attackerHp = frac * in.hpAll - traps - enemySpell;
    if(attackerHp <= k.advHpFloorShare * frac * in.hpAll)
        return k.advFloor;
    const double defenderHp = std::max(k.enemyHpFloorShare * in.enemyHp, in.enemyHp - mySpell);
    return std::log(attackerHp * frac * in.dpsAll / std::max(1.0, defenderHp * in.enemyDps)) + bonus - in.attackAdvantage;
}

//! \brief Scores each tactic against the estimated enemy strength.
TacticScores tacticScores(const AdvantageInput& in, double enemyGoldEstimate, bool enemyOut, const WarConstants& k)
{
    const double z = std::min(k.strengthRatioCap, in.enemyHp * in.enemyDps / std::max(1.0, in.hpAll * in.dpsAll));
    TacticScores result;
    result.score[0] = advantage(in, 1.0, 0.0, true, k) - k.scorePenaltyBase * k.scorePenaltyAllin * z;
    result.score[1] = advantage(in, k.groupShareSingle, 0.0, true, k) - k.scorePenaltyBase * k.scorePenaltySingle * z;
    result.score[2] = advantage(in, k.groupShareMain, k.bonusSplit, true, k) - k.scorePenaltyBase * k.scorePenaltySplit * z;
    result.score[3] = advantage(in, k.groupShareRaidTactic, k.bonusRaidBase + k.bonusRaidGold * std::log(1.0 + enemyGoldEstimate / k.bonusRaidGoldDivisor), false, k) - k.scorePenaltyBase * k.scorePenaltyRaid * z;
    result.score[4] = advantage(in, k.counterArmyShare, k.bonusCounter, true, k) - k.scorePenaltyBase * k.scorePenaltyCounter * z * k.scorePenaltyCounterFactor;
    result.valid = {{true, true, true, true, enemyOut}};
    return result;
}


//! \brief Schedules an action on the hand and enforces the rolling click budget.
double clickSchedule(HandState& hand, double due, int clicks, double seconds, double clicksPerWindow,
                     double minGap, double windowSeconds)
{
    double start = std::max(due, hand.busyUntil);
    if(clicks > 0)
    {
        start = std::max(start, hand.lastClickEnd + minGap);
        while(true)
        {
            while(!hand.clickGroups.empty() && hand.clickGroups.front().first <= start - windowSeconds)
                hand.clickGroups.pop_front();
            int used = 0;
            for(const std::pair<double, int>& group : hand.clickGroups)
                used += group.second;
            if(used + clicks <= clicksPerWindow || hand.clickGroups.empty())
                break;
            start = hand.clickGroups.front().first + windowSeconds;
        }
        hand.clickGroups.emplace_back(start, clicks);
        hand.lastClickEnd = start + seconds;
    }
    hand.busyUntil = start + seconds;
    return hand.busyUntil;
}


//! \brief Formats AI state entries as tab-separated lines.
std::vector<std::string> formatAiState(const std::vector<AiStateLine>& lines)
{
    std::vector<std::string> result;
    for(const AiStateLine& line : lines)
    {
        std::string text = line.tag;
        for(const std::string& token : line.tokens)
            text += "\t" + token;
        result.push_back(text);
    }
    return result;
}

//! \brief Parses AI state lines and rejects unknown tags or invalid token counts.
bool parseAiState(const std::vector<std::string>& lines, std::vector<AiStateLine>& out)
{
    std::vector<AiStateLine> parsed;
    for(const std::string& text : lines)
    {
        std::istringstream input(text);
        AiStateLine line;
        if(!(input >> line.tag))
            return false;
        std::string token;
        while(input >> token)
            line.tokens.push_back(token);
        const std::size_t n = line.tokens.size();
        bool valid = (line.tag == "look" && n == 3) || (line.tag == "event" && n == 10) ||
                     (line.tag == "action" && n == 6) || (line.tag == "click" && n == 2) ||
                     (line.tag == "hand" && n == 2) || (line.tag == "draw" && n == 3);
        if(line.tag == "war" && n > 0)
        {
            valid = (line.tokens[0] == "tunnel" && n == 8) || (line.tokens[0] == "assault" && n == 5) ||
                    (line.tokens[0] == "target" && n == 5) || (line.tokens[0] == "defence" && n == 4);
            if(line.tokens[0] == "group" && n >= 10)
            {
                std::istringstream countInput(line.tokens[9]);
                std::size_t count = 0;
                char extra;
                valid = static_cast<bool>(countInput >> count) && !(countInput >> extra) && n == 10 + count;
            }
        }
        if(line.tag == "sighting" && n > 0)
            valid = (line.tokens[0] == "seat" && n == 9) || (line.tokens[0] == "creature" && n == 5) ||
                    (line.tokens[0] == "spell" && n == 3);
        if(!valid)
            return false;
        parsed.push_back(line);
    }
    out = parsed;
    return true;
}

}
