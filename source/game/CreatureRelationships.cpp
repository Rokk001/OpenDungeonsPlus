/*
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

#include "game/CreatureRelationships.h"

#include "utils/LogManager.h"

#include <algorithm>
#include <cstdlib>
#include <istream>
#include <ostream>
#include <sstream>

const int32_t RelationshipSettings::VALUE_MIN = -100;
const int32_t RelationshipSettings::VALUE_MAX = 100;

namespace
{
    bool parseInt(const std::string& text, int64_t& value)
    {
        std::istringstream ss(text);
        int64_t tmp;
        if(!(ss >> tmp))
            return false;

        std::string rest;
        if(ss >> rest)
            return false;

        value = tmp;
        return true;
    }

    bool parseDouble(const std::string& text, double& value)
    {
        std::istringstream ss(text);
        double tmp;
        if(!(ss >> tmp))
            return false;

        std::string rest;
        if(ss >> rest)
            return false;

        value = tmp;
        return true;
    }

    //! Reads key from config. Returns false and leaves value untouched if it is missing or invalid.
    bool readSetting(const std::map<std::string, std::string>& config, const std::string& key, int64_t& value)
    {
        std::map<std::string, std::string>::const_iterator it = config.find(key);
        if(it == config.end())
            return false;

        return parseInt(it->second, value);
    }

    bool readSetting(const std::map<std::string, std::string>& config, const std::string& key, double& value)
    {
        std::map<std::string, std::string>::const_iterator it = config.find(key);
        if(it == config.end())
            return false;

        return parseDouble(it->second, value);
    }
}

RelationshipSettings::RelationshipSettings() :
    mThresholdFriends(50),
    mThresholdBestFriends(80),
    mThresholdLovers(90),
    mThresholdHated(-50),
    mThresholdNemesis(-80),
    mDriftAmount(1),
    mDriftIntervalTurns(10),
    mDriftIdleTurns(30),
    mEventTrainingTogether(2),
    mEventDefeatedEnemiesTogether(8),
    mEventArenaLoss(-10),
    mEventChickenSnatched(-12),
    mTrainingTogetherCooldownTurns(40),
    mFightParticipantTurns(100),
    mCombatRadiusTiles(3.0),
    mCombatBonusFriends(0.75),
    mCombatBonusBestFriends(1.5),
    mCombatPenaltyNemesis(0.75),
    mMoodPenaltyHated(250),
    mMoodPenaltyNemesis(400),
    mMoodMaxPairs(2),
    mMaxFriends(3),
    mMaxPartners(1),
    mMaxNemeses(2),
    mBrawlCheckIntervalTurns(20),
    mBrawlChancePercent(20),
    mBrawlMaxDistanceTiles(6),
    mBrawlStopHealthPercent(25),
    mBrawlMaxTurns(150),
    mBrawlValueChange(-6),
    mMentorMinLevelDiff(2),
    mMentorXpBonusPercent(50),
    mTempMoodMax(1000),
    mTempMoodDecayPerTurn(3),
    mGriefMoodPenalty(400),
    mGriefRageTurns(300),
    mGriefRageBonusPercent(30),
    mJealousyValueLoss(3),
    mLeaveTogetherChancePercent(30),
    mSleepNextToFriendMood(150),
    mNeighbourBedTiles(3),
    mEatTogetherMood(100),
    mEatTogetherTiles(6)
{
}

int32_t RelationshipSettings::getRacialStart(const std::string& classA, const std::string& classB) const
{
    std::pair<std::string, std::string> key = (classA < classB) ?
        std::pair<std::string, std::string>(classA, classB) : std::pair<std::string, std::string>(classB, classA);
    std::map<std::pair<std::string, std::string>, int32_t>::const_iterator it = mRacialStart.find(key);
    if(it == mRacialStart.end())
        return 0;

    return it->second;
}

RelationshipSettings RelationshipSettings::fromConfig(const std::map<std::string, std::string>& config)
{
    RelationshipSettings settings;

    struct IntEntry
    {
        const char* mKey;
        int32_t* mTarget;
    };
    struct TurnEntry
    {
        const char* mKey;
        int64_t* mTarget;
    };

    IntEntry intEntries[] =
    {
        {"ThresholdFriends", &settings.mThresholdFriends},
        {"ThresholdBestFriends", &settings.mThresholdBestFriends},
        {"ThresholdLovers", &settings.mThresholdLovers},
        {"ThresholdHated", &settings.mThresholdHated},
        {"ThresholdNemesis", &settings.mThresholdNemesis},
        {"DriftAmount", &settings.mDriftAmount},
        {"EventTrainingTogether", &settings.mEventTrainingTogether},
        {"EventDefeatedEnemiesTogether", &settings.mEventDefeatedEnemiesTogether},
        {"EventArenaLoss", &settings.mEventArenaLoss},
        {"EventChickenSnatched", &settings.mEventChickenSnatched},
        {"MoodPenaltyHated", &settings.mMoodPenaltyHated},
        {"MoodPenaltyNemesis", &settings.mMoodPenaltyNemesis},
        {"MoodMaxPairs", &settings.mMoodMaxPairs},
        {"MaxFriends", &settings.mMaxFriends},
        {"MaxPartners", &settings.mMaxPartners},
        {"MaxNemeses", &settings.mMaxNemeses},
        {"BrawlChancePercent", &settings.mBrawlChancePercent},
        {"BrawlMaxDistanceTiles", &settings.mBrawlMaxDistanceTiles},
        {"BrawlStopHealthPercent", &settings.mBrawlStopHealthPercent},
        {"BrawlValueChange", &settings.mBrawlValueChange},
        {"MentorMinLevelDiff", &settings.mMentorMinLevelDiff},
        {"MentorXpBonusPercent", &settings.mMentorXpBonusPercent},
        {"TempMoodMax", &settings.mTempMoodMax},
        {"TempMoodDecayPerTurn", &settings.mTempMoodDecayPerTurn},
        {"GriefMoodPenalty", &settings.mGriefMoodPenalty},
        {"GriefRageBonusPercent", &settings.mGriefRageBonusPercent},
        {"JealousyValueLoss", &settings.mJealousyValueLoss},
        {"LeaveTogetherChancePercent", &settings.mLeaveTogetherChancePercent},
        {"SleepNextToFriendMood", &settings.mSleepNextToFriendMood},
        {"NeighbourBedTiles", &settings.mNeighbourBedTiles},
        {"EatTogetherMood", &settings.mEatTogetherMood},
        {"EatTogetherTiles", &settings.mEatTogetherTiles}
    };
    struct DoubleEntry
    {
        const char* mKey;
        double* mTarget;
    };
    DoubleEntry doubleEntries[] =
    {
        {"CombatRadiusTiles", &settings.mCombatRadiusTiles},
        {"CombatBonusFriends", &settings.mCombatBonusFriends},
        {"CombatBonusBestFriends", &settings.mCombatBonusBestFriends},
        {"CombatPenaltyNemesis", &settings.mCombatPenaltyNemesis}
    };
    TurnEntry turnEntries[] =
    {
        {"DriftIntervalTurns", &settings.mDriftIntervalTurns},
        {"DriftIdleTurns", &settings.mDriftIdleTurns},
        {"TrainingTogetherCooldownTurns", &settings.mTrainingTogetherCooldownTurns},
        {"FightParticipantTurns", &settings.mFightParticipantTurns},
        {"BrawlCheckIntervalTurns", &settings.mBrawlCheckIntervalTurns},
        {"BrawlMaxTurns", &settings.mBrawlMaxTurns},
        {"GriefRageTurns", &settings.mGriefRageTurns}
    };

    std::string missing;
    for(IntEntry& entry : intEntries)
    {
        int64_t value;
        if(!readSetting(config, entry.mKey, value))
        {
            missing += std::string(" ") + entry.mKey;
            continue;
        }
        *entry.mTarget = static_cast<int32_t>(std::max<int64_t>(-1000000, std::min<int64_t>(1000000, value)));
    }
    for(DoubleEntry& entry : doubleEntries)
    {
        double value;
        if(!readSetting(config, entry.mKey, value))
        {
            missing += std::string(" ") + entry.mKey;
            continue;
        }
        *entry.mTarget = std::max(0.0, std::min(1000.0, value));
    }
    for(TurnEntry& entry : turnEntries)
    {
        int64_t value;
        if(!readSetting(config, entry.mKey, value) || (value < 1))
        {
            missing += std::string(" ") + entry.mKey;
            continue;
        }
        *entry.mTarget = value;
    }

    // Racial start values: "Racial_<ClassA>_<ClassB>  <value>"
    static const std::string racialPrefix = "Racial_";
    for(std::map<std::string, std::string>::const_iterator it = config.begin(); it != config.end(); ++it)
    {
        if(it->first.compare(0, racialPrefix.size(), racialPrefix) != 0)
            continue;

        std::string classes = it->first.substr(racialPrefix.size());
        std::string::size_type pos = classes.find('_');
        int64_t value;
        if((pos == std::string::npos) || (pos == 0) || (pos + 1 >= classes.size())
            || !parseInt(it->second, value))
        {
            missing += " " + it->first;
            continue;
        }

        std::string classA = classes.substr(0, pos);
        std::string classB = classes.substr(pos + 1);
        if(classB < classA)
            std::swap(classA, classB);
        value = std::max<int64_t>(RelationshipSettings::VALUE_MIN, std::min<int64_t>(RelationshipSettings::VALUE_MAX, value));
        settings.mRacialStart[std::pair<std::string, std::string>(classA, classB)] = static_cast<int32_t>(value);
    }

    // Logged once per process, not once per game
    static bool warned = false;
    if(!missing.empty() && !warned)
    {
        warned = true;
        OD_LOG_WRN("relationships.cfg: missing or invalid entries, using defaults for:" + missing);
    }

    return settings;
}

CreatureRelationships::CreatureRelationships() :
    mLastDriftTurn(0)
{
}

CreatureRelationships::CreatureRelationships(const RelationshipSettings& settings) :
    mSettings(settings),
    mLastDriftTurn(0)
{
}

CreatureRelationships::Pair CreatureRelationships::makePair(const std::string& creatureA, const std::string& creatureB)
{
    if(creatureA < creatureB)
        return Pair(creatureA, creatureB);

    return Pair(creatureB, creatureA);
}

void CreatureRelationships::onRelationshipEvent(RelationshipEvent event, const std::string& creatureA,
    const std::string& creatureB, int64_t turn, const std::string& classA, const std::string& classB)
{
    // A creature has no relationship with itself
    if(creatureA == creatureB)
        return;

    Pair pair = makePair(creatureA, creatureB);
    if(event == RelationshipEvent::trainingTogether)
    {
        // Counts once per training cycle, not once per blow
        std::map<Pair, int64_t>::iterator itTraining = mLastTrainingTurn.find(pair);
        if((itTraining != mLastTrainingTurn.end()) &&
           ((turn - itTraining->second) < mSettings.mTrainingTogetherCooldownTurns))
        {
            return;
        }
        mLastTrainingTurn[pair] = turn;
    }

    // The racial start value is applied when the pair first gets a value
    if(!classA.empty() && !classB.empty() && (mPairs.find(pair) == mPairs.end()))
    {
        int32_t start = mSettings.getRacialStart(classA, classB);
        if(start != 0)
            changeValue(creatureA, creatureB, start, turn);
    }

    int32_t amount = 0;
    switch(event)
    {
        case RelationshipEvent::trainingTogether:
            amount = mSettings.mEventTrainingTogether;
            break;
        case RelationshipEvent::defeatedEnemiesTogether:
            amount = mSettings.mEventDefeatedEnemiesTogether;
            break;
        case RelationshipEvent::arenaLoss:
            amount = mSettings.mEventArenaLoss;
            break;
        case RelationshipEvent::chickenSnatched:
            amount = mSettings.mEventChickenSnatched;
            break;
    }

    changeValue(creatureA, creatureB, amount, turn);
}

void CreatureRelationships::changeValue(const std::string& creatureA, const std::string& creatureB,
    int32_t amount, int64_t turn)
{
    // A creature has no relationship with itself
    if(creatureA == creatureB)
        return;

    Pair pair = makePair(creatureA, creatureB);
    int32_t value = amount;
    int32_t oldValue = 0;
    std::map<Pair, PairData>::const_iterator it = mPairs.find(pair);
    if(it != mPairs.end())
    {
        oldValue = it->second.mValue;
        value += oldValue;
    }

    setValue(pair, value, turn, true);
    enforceLimits(creatureA, turn);
    enforceLimits(creatureB, turn);

    // Becoming friends makes the friends of both creatures jealous
    if((mSettings.mJealousyValueLoss > 0) && (oldValue < mSettings.mThresholdFriends)
       && isFriend(creatureA, creatureB))
    {
        applyJealousy(creatureA, creatureB, turn);
        applyJealousy(creatureB, creatureA, turn);
    }
}

void CreatureRelationships::applyJealousy(const std::string& creature, const std::string& newFriend, int64_t turn)
{
    std::vector<std::string> friends;
    getFriends(creature, friends);
    for(size_t i = 0; i < friends.size(); ++i)
    {
        if(friends[i] != newFriend)
            changeValue(friends[i], newFriend, -mSettings.mJealousyValueLoss, turn);
    }
}

void CreatureRelationships::enforceLimits(const std::string& creature, int64_t turn)
{
    std::vector<std::pair<std::string, int32_t> > partners;
    getPartners(creature, partners);
    int32_t nbFriends = 0;
    int32_t nbNemeses = 0;
    for(size_t i = 0; i < partners.size(); ++i)
    {
        if(partners[i].second >= mSettings.mThresholdFriends)
            ++nbFriends;
        else if(partners[i].second <= mSettings.mThresholdNemesis)
            ++nbNemeses;
    }

    while(nbFriends > mSettings.mMaxFriends)
    {
        // The weakest friend falls back to a good acquaintance
        size_t weakest = partners.size();
        for(size_t i = 0; i < partners.size(); ++i)
        {
            if(partners[i].second < mSettings.mThresholdFriends)
                continue;
            if((weakest == partners.size()) || (partners[i].second < partners[weakest].second))
                weakest = i;
        }
        if(weakest == partners.size())
            break;

        setValue(makePair(creature, partners[weakest].first), mSettings.mThresholdFriends - 1, turn, false);
        partners[weakest].second = mSettings.mThresholdFriends - 1;
        --nbFriends;
    }

    while(nbNemeses > mSettings.mMaxNemeses)
    {
        // The weakest nemesis falls back to a hated creature
        size_t weakest = partners.size();
        for(size_t i = 0; i < partners.size(); ++i)
        {
            if(partners[i].second > mSettings.mThresholdNemesis)
                continue;
            if((weakest == partners.size()) || (partners[i].second > partners[weakest].second))
                weakest = i;
        }
        if(weakest == partners.size())
            break;

        setValue(makePair(creature, partners[weakest].first), mSettings.mThresholdNemesis + 1, turn, false);
        partners[weakest].second = mSettings.mThresholdNemesis + 1;
        --nbNemeses;
    }
}

void CreatureRelationships::setValue(const Pair& pair, int32_t value, int64_t turn, bool isEvent)
{
    value = std::max(RelationshipSettings::VALUE_MIN, std::min(RelationshipSettings::VALUE_MAX, value));

    int32_t oldValue = 0;
    std::map<Pair, PairData>::iterator it = mPairs.find(pair);
    if(it != mPairs.end())
        oldValue = it->second.mValue;

    if(value == 0)
    {
        if(it != mPairs.end())
            mPairs.erase(it);
    }
    else if(it == mPairs.end())
    {
        PairData data;
        data.mValue = value;
        data.mLastEventTurn = turn;
        mPairs[pair] = data;
    }
    else
    {
        it->second.mValue = value;
        if(isEvent)
            it->second.mLastEventTurn = turn;
    }

    recordTierChange(pair, oldValue, value);
}

void CreatureRelationships::recordTierChange(const Pair& pair, int32_t oldValue, int32_t newValue)
{
    RelationshipTier oldTier = tierOfValue(oldValue, false);
    RelationshipTier newTier = tierOfValue(newValue, false);
    if(oldTier == newTier)
        return;

    RelationshipTierChange change;
    change.mCreatureA = pair.first;
    change.mCreatureB = pair.second;
    change.mOldTier = oldTier;
    change.mNewTier = newTier;
    mTierChanges.push_back(change);
}

int32_t CreatureRelationships::getValue(const std::string& creatureA, const std::string& creatureB) const
{
    std::map<Pair, PairData>::const_iterator it = mPairs.find(makePair(creatureA, creatureB));
    if(it == mPairs.end())
        return 0;

    return it->second.mValue;
}

RelationshipTier CreatureRelationships::tierOfValue(int32_t value, bool loversAllowed) const
{
    if(loversAllowed && (value >= mSettings.mThresholdLovers))
        return RelationshipTier::lovers;
    if(value >= mSettings.mThresholdBestFriends)
        return RelationshipTier::bestFriends;
    if(value >= mSettings.mThresholdFriends)
        return RelationshipTier::friends;
    if(value <= mSettings.mThresholdNemesis)
        return RelationshipTier::nemesis;
    if(value <= mSettings.mThresholdHated)
        return RelationshipTier::hated;

    return RelationshipTier::neutral;
}

RelationshipTier CreatureRelationships::tierOf(const std::string& creatureA, const std::string& creatureB,
    bool loversAllowed) const
{
    return tierOfValue(getValue(creatureA, creatureB), loversAllowed);
}

bool CreatureRelationships::isFriend(const std::string& creatureA, const std::string& creatureB) const
{
    return getValue(creatureA, creatureB) >= mSettings.mThresholdFriends;
}

bool CreatureRelationships::isNemesis(const std::string& creatureA, const std::string& creatureB) const
{
    return getValue(creatureA, creatureB) <= mSettings.mThresholdNemesis;
}

bool CreatureRelationships::isHated(const std::string& creatureA, const std::string& creatureB) const
{
    return getValue(creatureA, creatureB) <= mSettings.mThresholdHated;
}

double CreatureRelationships::combatModifier(const std::string& creature,
    const std::vector<std::string>& nearbyFighters) const
{
    double bonus = 0.0;
    bool nemesisNearby = false;
    for(size_t i = 0; i < nearbyFighters.size(); ++i)
    {
        if(nearbyFighters[i] == creature)
            continue;

        int32_t value = getValue(creature, nearbyFighters[i]);
        if(value >= mSettings.mThresholdBestFriends)
            bonus = std::max(bonus, mSettings.mCombatBonusBestFriends);
        else if(value >= mSettings.mThresholdFriends)
            bonus = std::max(bonus, mSettings.mCombatBonusFriends);
        else if(value <= mSettings.mThresholdNemesis)
            nemesisNearby = true;
    }

    if(nemesisNearby)
        bonus -= mSettings.mCombatPenaltyNemesis;

    return bonus;
}

double CreatureRelationships::mentoringFactor(const std::string& creature, uint32_t level,
    const std::vector<std::pair<std::string, uint32_t> >& trainees) const
{
    for(size_t i = 0; i < trainees.size(); ++i)
    {
        if(trainees[i].first == creature)
            continue;

        if((trainees[i].second >= level + static_cast<uint32_t>(std::max<int32_t>(0, mSettings.mMentorMinLevelDiff)))
           && isFriend(creature, trainees[i].first))
        {
            return 1.0 + static_cast<double>(std::max<int32_t>(0, mSettings.mMentorXpBonusPercent)) / 100.0;
        }
    }

    return 1.0;
}

int32_t CreatureRelationships::moodModifier(const std::string& creature) const
{
    std::vector<std::pair<std::string, int32_t> > partners;
    getPartners(creature, partners);
    int32_t nbHated = 0;
    int32_t modifier = 0;
    for(size_t i = 0; i < partners.size(); ++i)
    {
        if(nbHated >= mSettings.mMoodMaxPairs)
            break;

        if(partners[i].second <= mSettings.mThresholdNemesis)
            modifier -= mSettings.mMoodPenaltyNemesis;
        else if(partners[i].second <= mSettings.mThresholdHated)
            modifier -= mSettings.mMoodPenaltyHated;
        else
            continue;

        ++nbHated;
    }

    return modifier;
}

std::string CreatureRelationships::getBestFriend(const std::string& creature) const
{
    std::vector<std::pair<std::string, int32_t> > partners;
    getPartners(creature, partners);
    std::string best;
    int32_t bestValue = mSettings.mThresholdBestFriends - 1;
    for(size_t i = 0; i < partners.size(); ++i)
    {
        if(partners[i].second > bestValue)
        {
            best = partners[i].first;
            bestValue = partners[i].second;
        }
    }

    return best;
}

void CreatureRelationships::getFriends(const std::string& creature, std::vector<std::string>& friends) const
{
    friends.clear();
    std::vector<std::pair<std::string, int32_t> > partners;
    getPartners(creature, partners);
    for(size_t i = 0; i < partners.size(); ++i)
    {
        if(partners[i].second >= mSettings.mThresholdFriends)
            friends.push_back(partners[i].first);
    }
}

void CreatureRelationships::getPartners(const std::string& creature,
    std::vector<std::pair<std::string, int32_t> >& partners) const
{
    partners.clear();
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        if(it->first.first == creature)
            partners.push_back(std::pair<std::string, int32_t>(it->first.second, it->second.mValue));
        else if(it->first.second == creature)
            partners.push_back(std::pair<std::string, int32_t>(it->first.first, it->second.mValue));
    }
}

void CreatureRelationships::getNemesisPairs(std::vector<Pair>& pairs) const
{
    pairs.clear();
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        if(it->second.mValue <= mSettings.mThresholdNemesis)
            pairs.push_back(it->first);
    }
}

void CreatureRelationships::removeCreature(const std::string& creature)
{
    std::map<Pair, int64_t>::iterator itTraining = mLastTrainingTurn.begin();
    while(itTraining != mLastTrainingTurn.end())
    {
        if((itTraining->first.first == creature) || (itTraining->first.second == creature))
            itTraining = mLastTrainingTurn.erase(itTraining);
        else
            ++itTraining;
    }

    std::map<Pair, PairData>::iterator it = mPairs.begin();
    while(it != mPairs.end())
    {
        if((it->first.first == creature) || (it->first.second == creature))
            it = mPairs.erase(it);
        else
            ++it;
    }
}

void CreatureRelationships::doTurn(int64_t turn)
{
    if((turn - mLastDriftTurn) < mSettings.mDriftIntervalTurns)
        return;

    mLastDriftTurn = turn;
    std::map<Pair, int64_t>::iterator itTraining = mLastTrainingTurn.begin();
    while(itTraining != mLastTrainingTurn.end())
    {
        if((turn - itTraining->second) >= mSettings.mTrainingTogetherCooldownTurns)
            itTraining = mLastTrainingTurn.erase(itTraining);
        else
            ++itTraining;
    }

    std::map<Pair, PairData>::iterator it = mPairs.begin();
    while(it != mPairs.end())
    {
        if((turn - it->second.mLastEventTurn) < mSettings.mDriftIdleTurns)
        {
            ++it;
            continue;
        }

        int32_t oldValue = it->second.mValue;
        int32_t newValue = oldValue;
        if(oldValue > 0)
            newValue = std::max<int32_t>(0, oldValue - mSettings.mDriftAmount);
        else
            newValue = std::min<int32_t>(0, oldValue + mSettings.mDriftAmount);

        recordTierChange(it->first, oldValue, newValue);
        if(newValue == 0)
        {
            it = mPairs.erase(it);
            continue;
        }

        it->second.mValue = newValue;
        ++it;
    }
}

void CreatureRelationships::takeTierChanges(std::vector<RelationshipTierChange>& changes)
{
    changes.clear();
    changes.swap(mTierChanges);
}

int32_t CreatureRelationships::representativeValue(RelationshipTier tier) const
{
    switch(tier)
    {
        case RelationshipTier::nemesis:
            return mSettings.mThresholdNemesis;
        case RelationshipTier::hated:
            return mSettings.mThresholdHated;
        case RelationshipTier::friends:
            return mSettings.mThresholdFriends;
        case RelationshipTier::bestFriends:
            return mSettings.mThresholdBestFriends;
        case RelationshipTier::lovers:
            return mSettings.mThresholdLovers;
        case RelationshipTier::neutral:
            break;
    }
    return 0;
}

void CreatureRelationships::setTier(const std::string& creatureA, const std::string& creatureB, RelationshipTier tier)
{
    if(creatureA == creatureB)
        return;

    Pair pair = makePair(creatureA, creatureB);
    int32_t value = representativeValue(tier);
    if(value == 0)
    {
        mPairs.erase(pair);
        return;
    }

    PairData data;
    data.mValue = value;
    data.mLastEventTurn = 0;
    mPairs[pair] = data;
}

void CreatureRelationships::getTiers(std::vector<RelationshipTierChange>& tiers) const
{
    tiers.clear();
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        RelationshipTier tier = tierOfValue(it->second.mValue, false);
        if(tier == RelationshipTier::neutral)
            continue;

        RelationshipTierChange entry;
        entry.mCreatureA = it->first.first;
        entry.mCreatureB = it->first.second;
        entry.mOldTier = RelationshipTier::neutral;
        entry.mNewTier = tier;
        tiers.push_back(entry);
    }
}

void CreatureRelationships::writeToStream(std::ostream& os, int64_t turn) const
{
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        int64_t age = std::max<int64_t>(0, turn - it->second.mLastEventTurn);
        os << it->first.first << "\t" << it->first.second << "\t" << it->second.mValue << "\t" << age << "\n";
    }
}

bool CreatureRelationships::readFromStream(std::istream& is, int64_t turn)
{
    mPairs.clear();
    mTierChanges.clear();

    std::string line;
    while(true)
    {
        if(!is.good())
            return false;

        std::getline(is, line);
        if(!line.empty() && (line[line.size() - 1] == '\r'))
            line.erase(line.size() - 1);

        if(line == "[/Relationships]")
            return true;

        if(line.empty() || (line[0] == '#'))
            continue;

        std::vector<std::string> fields;
        std::string::size_type start = 0;
        while(true)
        {
            std::string::size_type pos = line.find('\t', start);
            if(pos == std::string::npos)
            {
                fields.push_back(line.substr(start));
                break;
            }
            fields.push_back(line.substr(start, pos - start));
            start = pos + 1;
        }

        int64_t value;
        int64_t age;
        if((fields.size() != 4) || fields[0].empty() || fields[1].empty() || (fields[0] == fields[1])
            || !parseInt(fields[2], value) || !parseInt(fields[3], age))
        {
            return false;
        }

        value = std::max<int64_t>(RelationshipSettings::VALUE_MIN,
            std::min<int64_t>(RelationshipSettings::VALUE_MAX, value));
        if(value == 0)
            continue;

        PairData data;
        data.mValue = static_cast<int32_t>(value);
        data.mLastEventTurn = turn - std::max<int64_t>(0, age);
        mPairs[makePair(fields[0], fields[1])] = data;
    }
}
