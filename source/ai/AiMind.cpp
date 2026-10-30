/*!
 * Copyright (C) 2011-2016 OpenDungeons Team
 * This program is free software under the GNU General Public License, version 3 or later.
 */
#include "ai/AiMind.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <sstream>

namespace
{
const char* const eventNames[] = {
    "Fight", "HeartCritical", "Payday", "NotEnoughGold", "NoSkillInQueue", "NoWorker", "NoTreasury",
    "NoBed", "NoFood", "CreatureKilled", "CreatureMood", "CreatureLeft", "CreatureArrived", "RoomLost",
    "BuildingDestroyed", "Dirt", "InfirmaryNoMana", "TavernThirst", "EnemySpellSeen", "SpecialStored",
    "NoMarkedTile", "GoldBelowBill", "WoundedCreature", "PotionReady", "PrisonerAge", "SurplusCreature",
    "RouteBlocked", "TunnelOpen", "EnemyOut", "EnemyTrapEmpty", "FightOver", "FirstPortalArrival",
    "Loot", "LabIdle", "Plan", "Start", "Launch", "March", "Contact", "AssaultOver"
};

//! \brief Supplies one uniform draw for the pure probability functions.
double uniformDraw()
{
    return Random::Double(0.0, 1.0);
}

//! \brief Writes a number with enough precision to restore its exact double value.
template<typename T> std::string token(T value)
{
    std::ostringstream os;
    os << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return os.str();
}

//! \brief Reads a complete numeric token, rejecting trailing characters and nonfinite doubles.
template<typename T> bool number(const std::string& text, T& value)
{
    std::istringstream is(text);
    char extra;
    return static_cast<bool>(is >> value) && !(is >> extra) && std::isfinite(static_cast<double>(value));
}

//! \brief Maps a stored event name back to its enum value.
bool eventType(const std::string& name, AiEventType& type)
{
    for(std::size_t i = 0; i < sizeof(eventNames) / sizeof(eventNames[0]); ++i)
    {
        if(name == eventNames[i])
        {
            type = static_cast<AiEventType>(i);
            return true;
        }
    }
    return false;
}

//! \brief Classifies the event by how a human keeper notices it (specification 3.1-3.4).
AiMath::ReactionKind reactionKind(AiEventType type)
{
    if(type >= AiEventType::Plan)
        return AiMath::ReactionKind::internal;
    if(type >= AiEventType::NoMarkedTile || type == AiEventType::NoSkillInQueue ||
        type == AiEventType::Dirt || type == AiEventType::NoBed || type == AiEventType::NoFood)
        return AiMath::ReactionKind::symptom;
    return AiMath::ReactionKind::alert;
}

//! \brief Returns the serialized name of a reaction kind.
std::string kindName(AiMath::ReactionKind kind)
{
    switch(kind)
    {
        case AiMath::ReactionKind::alert: return "alert";
        case AiMath::ReactionKind::symptom: return "symptom";
        case AiMath::ReactionKind::periodic: return "periodic";
        default: return "internal";
    }
}

//! \brief Parses the four reaction kinds permitted in a saved event.
bool readKind(const std::string& name, AiMath::ReactionKind& kind)
{
    if(name == "alert") kind = AiMath::ReactionKind::alert;
    else if(name == "symptom") kind = AiMath::ReactionKind::symptom;
    else if(name == "periodic") kind = AiMath::ReactionKind::periodic;
    else if(name == "internal") kind = AiMath::ReactionKind::internal;
    else return false;
    return true;
}

//! \brief Finds the configured base probability key for one row class.
std::string classKey(const std::string& name)
{
    if(name == "routine") return "MistakeBaseRoutine";
    if(name == "rule") return "MistakeBaseRule";
    if(name == "complex") return "MistakeBaseComplex";
    if(name == "unfamiliar") return "MistakeBaseUnfamiliar";
    if(name == "rare") return "MistakeBaseRare";
    return "";
}

//! \brief Identifies the four legality and speed limits, which never draw mistakes.
bool hardLimit(const std::string& row)
{
    return row == "L01" || row == "L02" || row == "L03" || row == "L04";
}

//! \brief Rebases a relative state token while an imported row waits for its owner to bind.
void rebase(std::string& value, double delta, bool sentinel)
{
    double n;
    if(number(value, n) && (!sentinel || n != -1.0))
        value = token(n + delta);
}
}

//! \brief Starts a keeper mind with its level's settings and no pending actions.
Mind::Mind(GameMap& gameMap, Player& player, const AiSettings& settings) :
    mGameMap(gameMap), mPlayer(player), mSettings(settings), mNow(0.0), mSavedAt(0.0),
    mLoaded(false), mInTrigger(false)
{
    mLooks["I06"] = {0.0, false};
}

//! \brief Returns the current mind time used by action and row callbacks.
double Mind::now() const
{
    return mNow;
}

//! \brief Collects the configured timing keys for pure delay calculations.
AiMath::DelayParams Mind::delayParams() const
{
    const ConfigManager& cfg = ConfigManager::getSingleton();
    AiMath::DelayParams p = {mSettings.rho, mSettings.pi, mSettings.scanPeriod,
        cfg.getAiConfigDouble("SymptomScanFactor"), cfg.getAiConfigDouble("PeriodicMinDelay"),
        cfg.getAiConfigDouble("ActionLatencyMean"), cfg.getAiConfigDouble("ActionLatencySd")};
    return p;
}

//! \brief Binds a catalogue row to its hooked, polled or internal event types.
void Mind::onEvent(const std::string& rowId, const std::vector<AiEventType>& events,
                   const std::function<void(const AiEvent&)>& handler)
{
    mEventHandlers[rowId] = {events, handler};
}

//! \brief Starts a periodic topic unless its exact next look was already loaded.
void Mind::onLook(const std::string& rowId, double factor, const std::function<void()>& handler)
{
    mLookHandlers[rowId] = {factor, handler};
    if(mLooks.find(rowId) == mLooks.end())
        mLooks[rowId] = {mNow + AiMath::lookInterval(factor, delayParams(), uniformDraw), false};
}

//! \brief Binds a symptom predicate without discarding its restored edge flag.
void Mind::onPoll(const std::string& rowId, AiEventType type, const std::function<bool()>& predicate)
{
    mPollHandlers[rowId] = {type, predicate};
    if(mLooks.find(rowId) == mLooks.end())
        mLooks[rowId] = {mNow, false};
}

//! \brief Binds the server-call resolver for a row's restored hand action.
void Mind::onAction(const std::string& actionKey, const std::string& rowId,
                    const std::function<void(Tile*, const std::string&)>& handler)
{
    mActionHandlers[std::make_pair(actionKey, rowId)] = handler;
}

//! \brief Returns the elapsed time since an enemy cast the keeper actually saw.
double Mind::enemySpellAge(int seatId) const
{
    const std::map<int, double>::const_iterator cast = mEnemySpells.find(seatId);
    return cast == mEnemySpells.end() ? -1.0 : mNow - cast->second;
}

//! \brief Exposes imported state to the row owners that restore their own records and draws.
const std::vector<AiMath::AiStateLine>& Mind::savedRows() const
{
    return mSavedRows;
}

//! \brief Adds a state exporter; it replaces its own rows in the supplied state vector.
void Mind::onSave(const std::function<void(std::vector<AiMath::AiStateLine>&)>& handler)
{
    mSaveHandlers.push_back(handler);
}

//! \brief Queues one event and draws its shared reaction delay exactly once.
void Mind::enqueue(const AiEvent& event)
{
    // AI row I06
    if(event.type == AiEventType::EnemySpellSeen)
    {
        mEnemySpells[event.otherSeatId] = mNow;
        // A visible cast is information, so its observers receive it immediately without a mistake roll.
        for(const std::pair<const std::string, EventHandler>& entry : mEventHandlers)
        {
            if(std::find(entry.second.types.begin(), entry.second.types.end(), event.type) != entry.second.types.end())
                entry.second.perform(event);
        }
        return;
    }
    const AiMath::ReactionKind kind = reactionKind(event.type);
    if(event.type < AiEventType::NoMarkedTile)
    {
        // Every hooked event has its own I06 draw, including events raised inside another reaction.
        const bool inTrigger = mInTrigger;
        mInTrigger = false;
        const bool ignored = slip("I06");
        mInTrigger = inTrigger;
        if(ignored)
            return;
    }
    Reaction reaction;
    reaction.type = event.type;
    reaction.due = mNow + AiMath::reactionDelay(kind, delayParams(), uniformDraw);
    reaction.kind = kind;
    reaction.x = event.tile == nullptr ? -1 : event.tile->getX();
    reaction.y = event.tile == nullptr ? -1 : event.tile->getY();
    reaction.creature = event.creature == nullptr ? "-" : event.creature->getName();
    reaction.seatId = event.otherSeatId;
    reaction.amount = event.amount;
    reaction.noticed = false;
    reaction.rowId = "-";
    mEvents.push_back(reaction);
}

//! \brief Reserves the single hand and queues each server call at its scheduled finish time.
double Mind::exec(const std::string& actionKey, int count, double from, const std::string& rowId,
                  Tile* tile, const std::string& target, const std::function<void()>& perform)
{
    // AI row L01
    const ConfigManager& cfg = ConfigManager::getSingleton();
    const ConfigManager::AiAction* definition = cfg.getAiAction(actionKey);
    if(definition == nullptr || count <= 0)
        return std::max(from, mNow);
    double done = std::max(from, mNow);
    for(int i = 0; i < count; ++i)
    {
        done = AiMath::clickSchedule(mHand, done, definition->mClicks, definition->mSeconds,
            mSettings.clickShare * cfg.getAiConfigDouble("ClickBudgetPerMinute"),
            cfg.getAiConfigDouble("ClickMinGap"), cfg.getAiConfigDouble("ClickWindowSeconds"));
        Action action = {actionKey, done, rowId, tile == nullptr ? -1 : tile->getX(),
            tile == nullptr ? -1 : tile->getY(), target.empty() ? "-" : target, perform};
        mActions.push_back(action);
    }
    return done;
}

//! \brief Draws a row's configured mistake once within its current trigger callback.
bool Mind::slip(const std::string& rowId)
{
    if(hardLimit(rowId))
        return false;
    const ConfigManager::AiRowClass* row = ConfigManager::getSingleton().getAiRowClass(rowId);
    return row != nullptr && slip(rowId, row->mMultiplier);
}

//! \brief Draws a mistake using the supplied multiplier and the row's configured class.
bool Mind::slip(const std::string& rowId, double rowMultiplier)
{
    if(hardLimit(rowId))
        return false;
    if(mInTrigger && mTriggerSlips.find(rowId) != mTriggerSlips.end())
        return mTriggerSlips[rowId];
    const ConfigManager& cfg = ConfigManager::getSingleton();
    const ConfigManager::AiRowClass* row = cfg.getAiRowClass(rowId);
    if(row == nullptr || classKey(row->mClass).empty())
    {
        OD_LOG_ERR("Missing AI mistake class for row " + rowId);
        return false;
    }
    mDrawnRows.insert(rowId);
    const double p = AiMath::mistakeProbability(cfg.getAiConfigDouble(classKey(row->mClass)), rowMultiplier,
        mSettings.mistakeMultiplier, cfg.getAiConfigDouble("MistakeMin"), cfg.getAiConfigDouble("MistakeMax"));
    const bool mistake = uniformDraw() < p;
    if(mInTrigger)
        mTriggerSlips[rowId] = mistake;
    return mistake;
}

//! \brief Draws the five tactics and wait in their fixed order with clipped exponential weights.
int Mind::drawTactic(const std::array<double, 5>& priors, const AiMath::TacticScores& scores, double tau)
{
    const ConfigManager& cfg = ConfigManager::getSingleton();
    const double clamp = cfg.getAiConfigDouble("TacticExponentClamp");
    std::array<double, 5> weights = {{0.0, 0.0, 0.0, 0.0, 0.0}};
    double total = cfg.getAiConfigDouble("WaitWeight");
    for(std::size_t i = 0; i < weights.size(); ++i)
    {
        if(scores.valid[i])
            weights[i] = priors[i] * std::exp(std::max(-clamp, std::min(clamp, scores.score[i] / tau)));
        total += weights[i];
    }
    double draw = uniformDraw() * total;
    for(std::size_t i = 0; i < weights.size(); ++i)
    {
        draw -= weights[i];
        if(draw < 0.0)
            return static_cast<int>(i);
    }
    return -1;
}

//! \brief Audits mistake classes and enforces the unconditional legality and speed rows.
bool Mind::rowClassAudit() const
{
    // AI row L02
    const ConfigManager& cfg = ConfigManager::getSingleton();
    for(const ConfigManager::AiRowClass& row : cfg.getAiRowClasses())
    {
        if(classKey(row.mClass).empty() || (hardLimit(row.mId) ? row.mMultiplier != 0.0 : row.mMultiplier <= 0.0))
            return false;
    }
    const char* limits[] = {"L01", "L02", "L03", "L04"};
    for(const char* id : limits)
    {
        const ConfigManager::AiRowClass* row = cfg.getAiRowClass(id);
        if(row == nullptr || row->mMultiplier != 0.0)
            return false;
    }
    for(const std::string& id : mDrawnRows)
    {
        if(cfg.getAiRowClass(id) == nullptr || hardLimit(id))
            return false;
    }
    // Planning never pauses the server or changes the game clock.
    return true;
}

//! \brief Polls edges, dispatches due rows in catalogue order, then performs completed hand actions.
void Mind::doTurn(double timeSinceLastTurn)
{
    if(!mLoaded)
    {
        mLoaded = true;
        const std::vector<std::string> lines = mPlayer.getSeat()->takeAiStateLoaded();
        if(!lines.empty() && !importState(lines))
            OD_LOG_WRN("Invalid AI state; starting a fresh keeper mind");
        if(!rowClassAudit())
            OD_LOG_ERR("Invalid AI row-class table");
    }
    mNow += timeSinceLastTurn;
    if(mNow >= mLooks["I06"].due)
    {
        mLooks["I06"].due = mNow + ConfigManager::getSingleton().getAiConfigDouble("AiPollSeconds");
        std::set<AiEventType> queued;
        for(const std::pair<const std::string, PollHandler>& entry : mPollHandlers)
        {
            const bool current = entry.second.predicate();
            Look& look = mLooks[entry.first];
            if(current && !look.flag && queued.insert(entry.second.type).second)
            {
                const AiEvent event = {entry.second.type, nullptr, nullptr, -1, 0.0, mNow};
                enqueue(event);
            }
            look.flag = current;
        }
    }
    for(const std::pair<const std::string, LookHandler>& entry : mLookHandlers)
    {
        Look& look = mLooks[entry.first];
        if(mNow < look.due)
            continue;
        look.due = mNow + AiMath::lookInterval(entry.second.factor, delayParams(), uniformDraw);
        mTriggerSlips.clear();
        mInTrigger = true;
        entry.second.perform();
        mInTrigger = false;
    }
    // Copy due reactions before calling row code, because a reaction may enqueue another event.
    std::vector<Reaction> due;
    for(std::vector<Reaction>::iterator it = mEvents.begin(); it != mEvents.end();)
    {
        if(it->due <= mNow)
        {
            due.push_back(*it);
            it = mEvents.erase(it);
        }
        else
            ++it;
    }
    std::stable_sort(due.begin(), due.end());
    for(const Reaction& reaction : due)
    {
        const AiEvent event = {reaction.type, mGameMap.getTile(reaction.x, reaction.y),
            reaction.creature == "-" ? nullptr : mGameMap.getCreature(reaction.creature),
            reaction.seatId, reaction.amount, reaction.due};
        mTriggerSlips.clear();
        mInTrigger = true;
        for(const std::pair<const std::string, EventHandler>& entry : mEventHandlers)
        {
            if((reaction.rowId == "-" || reaction.rowId == entry.first) &&
                std::find(entry.second.types.begin(), entry.second.types.end(), event.type) != entry.second.types.end())
                entry.second.perform(event);
        }
        mInTrigger = false;
    }
    // The reservation order is also the hand's execution order, including zero-click mental steps.
    while(!mActions.empty() && mActions.front().due <= mNow)
    {
        const Action action = mActions.front();
        if(action.perform)
        {
            mActions.erase(mActions.begin());
            action.perform();
        }
        else
        {
            const std::pair<std::string, std::string> key(action.key, action.rowId);
            const std::map<std::pair<std::string, std::string>, std::function<void(Tile*, const std::string&)>>::const_iterator handler = mActionHandlers.find(key);
            if(handler == mActionHandlers.end())
            {
                OD_LOG_ERR("No restored AI action handler for " + action.rowId + " " + action.key);
                break;
            }
            mActions.erase(mActions.begin());
            handler->second(mGameMap.getTile(action.x, action.y), action.target == "-" ? "" : action.target);
        }
    }
}

//! \brief Clears all imported scheduling state and restarts the registered periodic topics.
void Mind::resetState()
{
    mHand = AiMath::HandState();
    mHand.busyUntil = mNow;
    mEvents.clear();
    mActions.clear();
    mSavedRows.clear();
    mEnemySpells.clear();
    mSavedAt = mNow;
    mLooks.clear();
    mLooks["I06"] = {mNow, false};
    for(const std::pair<const std::string, LookHandler>& entry : mLookHandlers)
        mLooks[entry.first] = {mNow + AiMath::lookInterval(entry.second.factor, delayParams(), uniformDraw), false};
    for(const std::pair<const std::string, PollHandler>& entry : mPollHandlers)
        mLooks[entry.first].flag = false;
}

//! \brief Writes relative times and all scheduler, action, row and observation state at full precision.
void Mind::exportState(std::ostream& os) const
{
    std::vector<AiMath::AiStateLine> lines = mSavedRows;
    const double elapsed = mNow - mSavedAt;
    for(AiMath::AiStateLine& line : lines)
    {
        std::vector<std::string>& t = line.tokens;
        if(line.tag == "sighting" && t[0] == "seat")
            rebase(t[2], elapsed, false);
        else if(line.tag == "war" && t[0] == "tunnel")
            rebase(t[7], -elapsed, true);
        else if(line.tag == "war" && t[0] == "assault")
        {
            rebase(t[3], elapsed, true);
            rebase(t[4], -elapsed, false);
        }
        else if(line.tag == "war" && t[0] == "group")
            rebase(t[6], -elapsed, true);
        else if(line.tag == "draw" && (t[1] == "slipFrom" || t[1] == "slipUntil" || t[1] == "episodeUntil"))
            rebase(t[2], -elapsed, false);
    }
    for(const std::function<void(std::vector<AiMath::AiStateLine>&)>& handler : mSaveHandlers)
        handler(lines);
    // Visible enemy spell times belong to the immediate information path, not delayed row reactions.
    for(const std::pair<const int, double>& cast : mEnemySpells)
        lines.push_back({"sighting", {"spell", token(cast.first), token(mNow - cast.second)}});
    for(const std::pair<const std::string, Look>& look : mLooks)
        lines.push_back({"look", {look.first, token(look.second.due - mNow), token(look.second.flag ? 1 : 0)}});
    for(const Reaction& e : mEvents)
        lines.push_back({"event", {eventNames[static_cast<int>(e.type)], token(e.due - mNow), kindName(e.kind),
            token(e.x), token(e.y), e.creature, token(e.seatId), token(e.amount), token(e.noticed ? 1 : 0), e.rowId}});
    for(const Action& a : mActions)
        lines.push_back({"action", {a.key, token(a.due - mNow), a.rowId, token(a.x), token(a.y), a.target}});
    for(const std::pair<double, int>& click : mHand.clickGroups)
    {
        if(click.first > mNow - ConfigManager::getSingleton().getAiConfigDouble("ClickWindowSeconds"))
            lines.push_back({"click", {token(mNow - click.first), token(click.second)}});
    }
    lines.push_back({"hand", {token(mHand.busyUntil - mNow), token(mNow - mHand.lastClickEnd)}});
    for(const std::string& line : AiMath::formatAiState(lines))
        os << line << '\n';
}

//! \brief Restores scheduler entries atomically; malformed entries restart a fresh mind.
bool Mind::importState(const std::vector<std::string>& input)
{
    std::vector<AiMath::AiStateLine> lines;
    if(!AiMath::parseAiState(input, lines))
    {
        resetState();
        return false;
    }
    std::vector<Reaction> events;
    std::vector<Action> actions;
    std::map<std::string, Look> looks;
    AiMath::HandState hand;
    std::vector<AiMath::AiStateLine> rows;
    std::map<int, double> enemySpells;
    bool valid = true;
    for(const AiMath::AiStateLine& line : lines)
    {
        const std::vector<std::string>& t = line.tokens;
        if(line.tag == "event")
        {
            Reaction e;
            double remaining;
            int noticed;
            valid = eventType(t[0], e.type) && number(t[1], remaining) && readKind(t[2], e.kind) &&
                number(t[3], e.x) && number(t[4], e.y) && number(t[6], e.seatId) &&
                number(t[7], e.amount) && number(t[8], noticed) && (noticed == 0 || noticed == 1);
            if(!valid) break;
            e.due = mNow + remaining;
            e.creature = t[5];
            e.noticed = noticed != 0;
            e.rowId = t[9];
            events.push_back(e);
        }
        else if(line.tag == "action")
        {
            Action a;
            double remaining;
            valid = ConfigManager::getSingleton().getAiAction(t[0]) != nullptr && number(t[1], remaining) &&
                number(t[3], a.x) && number(t[4], a.y);
            if(!valid) break;
            a.key = t[0];
            a.due = mNow + remaining;
            a.rowId = t[2];
            a.target = t[5];
            actions.push_back(a);
        }
        else if(line.tag == "look")
        {
            double remaining;
            int flag;
            valid = number(t[1], remaining) && number(t[2], flag) && (flag == 0 || flag == 1);
            if(!valid) break;
            looks[t[0]] = {mNow + remaining, flag != 0};
        }
        else if(line.tag == "click")
        {
            double age;
            int clicks;
            valid = number(t[0], age) && number(t[1], clicks) && clicks >= 0;
            if(!valid) break;
            hand.clickGroups.push_back(std::make_pair(mNow - age, clicks));
        }
        else if(line.tag == "hand")
        {
            double busy, age;
            valid = number(t[0], busy) && number(t[1], age);
            if(!valid) break;
            hand.busyUntil = mNow + busy;
            hand.lastClickEnd = mNow - age;
        }
        else if(line.tag == "sighting" && t[0] == "spell")
        {
            int seat;
            double age;
            valid = number(t[1], seat) && number(t[2], age);
            if(!valid) break;
            enemySpells[seat] = mNow - age;
        }
        else
            rows.push_back(line);
    }
    if(!valid)
    {
        resetState();
        return false;
    }
    // Preserve bindings established by the package owners before the first turn.
    for(const std::pair<const std::string, Look>& look : mLooks)
    {
        if(looks.find(look.first) == looks.end())
            looks.insert(look);
    }
    mEvents.swap(events);
    mActions.swap(actions);
    mLooks.swap(looks);
    mHand = hand;
    mSavedRows.swap(rows);
    mEnemySpells.swap(enemySpells);
    mSavedAt = mNow;
    return true;
}
