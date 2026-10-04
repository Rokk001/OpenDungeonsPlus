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
#include <set>
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
    mDriftIntervalTurns(30),
    mDriftIdleTurns(420),
    mEventTrainingTogether(3),
    mEventDefeatedEnemiesTogether(8),
    mEventArenaLoss(-10),
    mEventChickenSnatched(-12),
    mEventPrayedTogether(4),
    mPrayerTogetherCooldownTurns(30),
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
    mBrawlChancePercent(6),
    mBrawlMaxDistanceTiles(6),
    mBrawlStopHealthPercent(25),
    mBrawlMaxTurns(150),
    mBrawlValueChange(-6),
    mMentorMinLevelDiff(2),
    mMentorXpBonusPercent(30),
    mTempMoodMax(1000),
    mTempMoodDecayPerTurn(3),
    mGriefMoodPenalty(400),
    mGriefRageTurns(200),
    mGriefRageBonusPercent(20),
    mJealousyValueLoss(3),
    mLoversJealousyValueLoss(8),
    mLoversBreakValue(70),
    mCombatBonusLovers(2.5),
    mMoodBonusLovers(300),
    mPartnerGriefMoodPenalty(800),
    mLeavePartnerChancePercent(70),
    mLeaveTogetherChancePercent(30),
    mSleepNextToFriendMood(50),
    mNeighbourBedTiles(3),
    mEatTogetherMood(100),
    mEatTogetherTiles(6),
    mSlapFriendsMoodPenalty(60),
    mConvertedCaptorValue(-20)
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
        {"EventPrayedTogether", &settings.mEventPrayedTogether},
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
        {"LoversJealousyValueLoss", &settings.mLoversJealousyValueLoss},
        {"LoversBreakValue", &settings.mLoversBreakValue},
        {"MoodBonusLovers", &settings.mMoodBonusLovers},
        {"PartnerGriefMoodPenalty", &settings.mPartnerGriefMoodPenalty},
        {"LeavePartnerChancePercent", &settings.mLeavePartnerChancePercent},
        {"LeaveTogetherChancePercent", &settings.mLeaveTogetherChancePercent},
        {"SleepNextToFriendMood", &settings.mSleepNextToFriendMood},
        {"NeighbourBedTiles", &settings.mNeighbourBedTiles},
        {"EatTogetherMood", &settings.mEatTogetherMood},
        {"EatTogetherTiles", &settings.mEatTogetherTiles},
        {"SlapFriendsMoodPenalty", &settings.mSlapFriendsMoodPenalty},
        {"ConvertedCaptorValue", &settings.mConvertedCaptorValue}
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
        {"CombatBonusLovers", &settings.mCombatBonusLovers},
        {"CombatPenaltyNemesis", &settings.mCombatPenaltyNemesis}
    };
    TurnEntry turnEntries[] =
    {
        {"DriftIntervalTurns", &settings.mDriftIntervalTurns},
        {"DriftIdleTurns", &settings.mDriftIdleTurns},
        {"TrainingTogetherCooldownTurns", &settings.mTrainingTogetherCooldownTurns},
        {"PrayerTogetherCooldownTurns", &settings.mPrayerTogetherCooldownTurns},
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

void CreatureRelationships::startConverted(const std::string& creature, const std::vector<std::string>& captors,
    int64_t turn)
{
    for(size_t i = 0; i < captors.size(); ++i)
    {
        if((captors[i] == creature) || (getValue(creature, captors[i]) != 0))
            continue;

        changeValue(creature, captors[i], mSettings.mConvertedCaptorValue, turn);
    }
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

    if(event == RelationshipEvent::prayedTogether)
    {
        // Only hated pairs reconcile, slowly: once per cooldown
        std::map<Pair, PairData>::const_iterator itPair = mPairs.find(pair);
        if((itPair == mPairs.end()) || (itPair->second.mValue > mSettings.mThresholdHated))
            return;

        std::map<Pair, int64_t>::iterator itPrayer = mLastPrayerTurn.find(pair);
        if((itPrayer != mLastPrayerTurn.end()) && ((turn - itPrayer->second) < mSettings.mPrayerTogetherCooldownTurns))
            return;

        mLastPrayerTurn[pair] = turn;
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
        case RelationshipEvent::prayedTogether:
            amount = mSettings.mEventPrayedTogether;
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
    updateLovers(pair);
    enforceLimits(creatureA, turn);
    enforceLimits(creatureB, turn);

    // Becoming friends makes the friends of both creatures jealous
    if(((mSettings.mJealousyValueLoss > 0) || (mSettings.mLoversJealousyValueLoss > 0))
       && (oldValue < mSettings.mThresholdFriends) && isFriend(creatureA, creatureB))
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
        if(friends[i] == newFriend)
            continue;

        // A partner is hurt more than a friend
        int32_t loss = isLovers(creature, friends[i]) ? mSettings.mLoversJealousyValueLoss : mSettings.mJealousyValueLoss;
        if(loss > 0)
            changeValue(friends[i], newFriend, -loss, turn);
    }
}

void CreatureRelationships::enforceLimits(const std::string& creature, int64_t turn)
{
    std::vector<std::pair<std::string, int32_t> > partners;
    getPartners(creature, partners);
    int32_t nbFriends = 0;
    int32_t nbNemeses = 0;
    int32_t nbLovers = 0;
    for(size_t i = 0; i < partners.size(); ++i)
    {
        if(isLovers(creature, partners[i].first))
            ++nbLovers;
        else if(partners[i].second >= mSettings.mThresholdFriends)
            ++nbFriends;
        else if(partners[i].second <= mSettings.mThresholdNemesis)
            ++nbNemeses;
    }

    while(nbLovers > mSettings.mMaxPartners)
    {
        // The weakest couple falls back to best friends
        size_t weakest = partners.size();
        for(size_t i = 0; i < partners.size(); ++i)
        {
            if(!isLovers(creature, partners[i].first))
                continue;
            if((weakest == partners.size()) || (partners[i].second < partners[weakest].second))
                weakest = i;
        }
        if(weakest == partners.size())
            break;

        Pair pair = makePair(creature, partners[weakest].first);
        std::map<Pair, PairData>::iterator it = mPairs.find(pair);
        it->second.mValue = std::min(it->second.mValue, mSettings.mThresholdLovers - 1);
        clearLovers(pair, it->second);
        partners[weakest].second = it->second.mValue;
        --nbLovers;
    }

    while(nbFriends > mSettings.mMaxFriends)
    {
        // The weakest friend falls back to a good acquaintance
        size_t weakest = partners.size();
        for(size_t i = 0; i < partners.size(); ++i)
        {
            if((partners[i].second < mSettings.mThresholdFriends) || isLovers(creature, partners[i].first))
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

    RelationshipTier oldTier = RelationshipTier::neutral;
    std::map<Pair, PairData>::iterator it = mPairs.find(pair);
    if(it != mPairs.end())
        oldTier = tierOfData(*this, it->second);

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
        data.mLovers = false;
        mPairs[pair] = data;
    }
    else
    {
        it->second.mValue = value;
        if(isEvent)
            it->second.mLastEventTurn = turn;
        // Lovers break up below the break value
        if(it->second.mLovers && (value < mSettings.mLoversBreakValue))
            it->second.mLovers = false;
    }

    RelationshipTier newTier = RelationshipTier::neutral;
    it = mPairs.find(pair);
    if(it != mPairs.end())
        newTier = tierOfData(*this, it->second);
    recordTierChange(pair, oldTier, newTier);
}

RelationshipTier CreatureRelationships::tierOfData(const CreatureRelationships& self, const PairData& data)
{
    if(data.mLovers)
        return RelationshipTier::lovers;

    return self.tierOfValue(data.mValue, false);
}

bool CreatureRelationships::haveLoversGenders(const Pair& pair) const
{
    if(!mGenderLookup)
        return false;

    std::string genderA = mGenderLookup(pair.first);
    std::string genderB = mGenderLookup(pair.second);
    return ((genderA == "Male") && (genderB == "Female")) || ((genderA == "Female") && (genderB == "Male"));
}

bool CreatureRelationships::canTakeLover(const std::string& creature, int32_t value) const
{
    if(mSettings.mMaxPartners <= 0)
        return false;

    int32_t nbLovers = 0;
    int32_t weakest = RelationshipSettings::VALUE_MAX;
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        if(!it->second.mLovers || ((it->first.first != creature) && (it->first.second != creature)))
            continue;

        ++nbLovers;
        weakest = std::min(weakest, it->second.mValue);
    }

    // A weaker partner is replaced by the stronger new couple
    return (nbLovers < mSettings.mMaxPartners) || (value > weakest);
}

void CreatureRelationships::updateLovers(const Pair& pair)
{
    std::map<Pair, PairData>::iterator it = mPairs.find(pair);
    if((it == mPairs.end()) || it->second.mLovers || (it->second.mValue < mSettings.mThresholdLovers))
        return;

    if(!haveLoversGenders(pair) || !canTakeLover(pair.first, it->second.mValue)
       || !canTakeLover(pair.second, it->second.mValue))
    {
        return;
    }

    RelationshipTier oldTier = tierOfData(*this, it->second);
    it->second.mLovers = true;
    recordTierChange(pair, oldTier, RelationshipTier::lovers);
}

void CreatureRelationships::clearLovers(const Pair& pair, PairData& data)
{
    data.mLovers = false;
    recordTierChange(pair, RelationshipTier::lovers, tierOfValue(data.mValue, false));
}

void CreatureRelationships::recordTierChange(const Pair& pair, RelationshipTier oldTier, RelationshipTier newTier)
{
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
    std::map<Pair, PairData>::const_iterator it = mPairs.find(makePair(creatureA, creatureB));
    if(it == mPairs.end())
        return RelationshipTier::neutral;

    if(loversAllowed && it->second.mLovers)
        return RelationshipTier::lovers;

    return tierOfValue(it->second.mValue, false);
}

bool CreatureRelationships::isLovers(const std::string& creatureA, const std::string& creatureB) const
{
    std::map<Pair, PairData>::const_iterator it = mPairs.find(makePair(creatureA, creatureB));
    return (it != mPairs.end()) && it->second.mLovers;
}

std::string CreatureRelationships::getPartner(const std::string& creature) const
{
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        if(!it->second.mLovers)
            continue;
        if(it->first.first == creature)
            return it->first.second;
        if(it->first.second == creature)
            return it->first.first;
    }

    return std::string();
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
        if(isLovers(creature, nearbyFighters[i]))
            bonus = std::max(bonus, mSettings.mCombatBonusLovers);
        else if(value >= mSettings.mThresholdBestFriends)
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
        // The partner is a pure bonus and does not count against the hated limit
        if(isLovers(creature, partners[i].first))
        {
            modifier += mSettings.mMoodBonusLovers;
            continue;
        }

        if(nbHated >= mSettings.mMoodMaxPairs)
            continue;

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
    std::map<Pair, int64_t>::iterator itPrayer = mLastPrayerTurn.begin();
    while(itPrayer != mLastPrayerTurn.end())
    {
        if((itPrayer->first.first == creature) || (itPrayer->first.second == creature))
            itPrayer = mLastPrayerTurn.erase(itPrayer);
        else
            ++itPrayer;
    }

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
    std::map<Pair, int64_t>::iterator itPrayer = mLastPrayerTurn.begin();
    while(itPrayer != mLastPrayerTurn.end())
    {
        if((turn - itPrayer->second) >= mSettings.mPrayerTogetherCooldownTurns)
            itPrayer = mLastPrayerTurn.erase(itPrayer);
        else
            ++itPrayer;
    }

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
        RelationshipTier oldTier = tierOfData(*this, it->second);
        int32_t newValue = oldValue;
        if(oldValue > 0)
            newValue = std::max<int32_t>(0, oldValue - mSettings.mDriftAmount);
        else
            newValue = std::min<int32_t>(0, oldValue + mSettings.mDriftAmount);

        if(newValue == 0)
        {
            recordTierChange(it->first, oldTier, RelationshipTier::neutral);
            it = mPairs.erase(it);
            continue;
        }

        it->second.mValue = newValue;
        if(it->second.mLovers && (newValue < mSettings.mLoversBreakValue))
            it->second.mLovers = false;
        recordTierChange(it->first, oldTier, tierOfData(*this, it->second));
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
    data.mLovers = (tier == RelationshipTier::lovers);
    mPairs[pair] = data;
}

void CreatureRelationships::getTiers(std::vector<RelationshipTierChange>& tiers) const
{
    tiers.clear();
    for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
    {
        RelationshipTier tier = tierOfData(*this, it->second);
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
        os << it->first.first << "\t" << it->first.second << "\t" << it->second.mValue << "\t" << age << "\t"
           << (it->second.mLovers ? 1 : 0) << "\n";
    }
}

bool CreatureRelationships::readFromStream(std::istream& is, int64_t turn)
{
    mPairs.clear();
    mTierChanges.clear();
    std::set<Pair> legacy;

    std::string line;
    while(true)
    {
        if(!is.good())
            return false;

        std::getline(is, line);
        if(!line.empty() && (line[line.size() - 1] == '\r'))
            line.erase(line.size() - 1);

        if(line == "[/Relationships]")
        {
            // Pairs of old saves have no lovers flag: they are lovers when they qualify now
            for(std::map<Pair, PairData>::iterator it = mPairs.begin(); it != mPairs.end(); ++it)
            {
                if(legacy.count(it->first) != 0)
                    updateLovers(it->first);
            }
            // The limits are applied once per creature that has a partner
            std::vector<std::string> names;
            for(std::map<Pair, PairData>::const_iterator it = mPairs.begin(); it != mPairs.end(); ++it)
            {
                if(it->second.mLovers)
                {
                    names.push_back(it->first.first);
                    names.push_back(it->first.second);
                }
            }
            for(size_t i = 0; i < names.size(); ++i)
                enforceLimits(names[i], turn);

            // Nothing of this is news for the clients
            mTierChanges.clear();
            return true;
        }

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
        int64_t lovers = 0;
        bool hasFlag = (fields.size() == 5);
        if(((fields.size() != 4) && !hasFlag) || fields[0].empty() || fields[1].empty() || (fields[0] == fields[1])
            || !parseInt(fields[2], value) || !parseInt(fields[3], age) || (hasFlag && !parseInt(fields[4], lovers)))
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
        data.mLovers = hasFlag && (lovers != 0) && (data.mValue >= mSettings.mLoversBreakValue);
        Pair pair = makePair(fields[0], fields[1]);
        mPairs[pair] = data;
        if(!hasFlag)
            legacy.insert(pair);
    }
}

bool relationshipsAllowed(bool optionOnServerMap, bool hasSeat, bool rogueSeat, bool heroFaction,
    bool worker, bool inPrison)
{
    if(!optionOnServerMap)
        return false;

    if(!hasSeat || rogueSeat || heroFaction)
        return false;

    return !worker && !inPrison;
}

bool relationshipEventAllowed(bool firstAllowed, bool secondAllowed, bool sameSeat)
{
    return firstAllowed && secondAllowed && sameSeat;
}

bool anyHatedCoworker(const CreatureRelationships& relationships, bool creatureAllowed,
    const std::string& creature, const std::vector<std::string>& coworkers)
{
    if(!creatureAllowed)
        return false;

    for(size_t i = 0; i < coworkers.size(); ++i)
    {
        if(relationships.isHated(creature, coworkers[i]))
            return true;
    }

    return false;
}

bool useDislikedRoomAsFallback(bool haveDislikedRoom, size_t nbOtherSuitableRooms)
{
    return haveDislikedRoom && (nbOtherSuitableRooms == 0);
}

bool canStartBrawl(const BrawlCandidateState& state, const RelationshipSettings& settings)
{
    if(!state.mAllowed || !state.mOnMap || !state.mAlive || state.mKo || state.mPossessed || state.mBrawling)
        return false;

    if(!state.mHasTile)
        return false;

    // Not while fighting, in the arena or the casino, and not when badly hurt
    if(state.mFighting || state.mInArenaOrCasino)
        return false;

    return (state.mHp * 100.0) > (state.mMaxHp * static_cast<double>(settings.mBrawlStopHealthPercent + 25));
}

bool shouldStopBrawl(const BrawlFighterState& first, const BrawlFighterState& second, int64_t turnsSinceStart,
    bool stillFighting, const RelationshipSettings& settings)
{
    double stopRatio = static_cast<double>(settings.mBrawlStopHealthPercent) / 100.0;
    return !first.mAlive || !second.mAlive || first.mKo || second.mKo
        || first.mPossessed || second.mPossessed
        || (first.mHp <= (first.mMaxHp * stopRatio)) || (second.mHp <= (second.mMaxHp * stopRatio))
        || (turnsSinceStart >= settings.mBrawlMaxTurns)
        || !stillFighting;
}

bool isBrawlCheckTurn(int64_t turn, const RelationshipSettings& settings)
{
    return (turn % settings.mBrawlCheckIntervalTurns) == 0;
}

bool isWithinBrawlDistance(double dx, double dy, const RelationshipSettings& settings)
{
    double maxDistance = static_cast<double>(settings.mBrawlMaxDistanceTiles);
    return (dx * dx + dy * dy) <= (maxDistance * maxDistance);
}

bool brawlChanceHit(int32_t roll, const RelationshipSettings& settings)
{
    return roll < settings.mBrawlChancePercent;
}
