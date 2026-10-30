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

#include "creatureskill/CreatureSkillTree.h"

#include "utils/LogManager.h"

#include "utils/ConfigManager.h"

#include <algorithm>
#include <cstdlib>
#include <iomanip>
#include <istream>
#include <ostream>
#include <sstream>

namespace CreatureSkillTree
{
const std::string TIER_FOUR_PREFIX = "T4_";
const uint32_t MAX_TIER = 3;

namespace
{
//! \brief Multiplier of the linear congruential generator of the personal deviation draws.
static const uint64_t RNG_MULTIPLIER = 1103515245ull;
//! \brief Increment of the linear congruential generator of the personal deviation draws.
static const uint64_t RNG_INCREMENT = 12345ull;
//! \brief Mask that keeps the generator state below 2^31.
static const uint64_t RNG_MASK = 0x7FFFFFFFull;
//! \brief A deviation draw is a number below this limit.
static const uint32_t DEVIATION_RANGE = 100;
//! \brief Digits written for the numbers of a generated skill line.
static const int LINE_PRECISION = 12;
//! \brief Digits written for the reset window in a saved build.
static const int WINDOW_PRECISION = 17;
//! \brief Prefix of a passive kind token.
static const std::string PASSIVE_PREFIX = "PASSIVE_";
//! \brief The cell text of a value that is not used.
static const std::string UNUSED_CELL = "-";
//! \brief The characters trimmed from config text.
static const std::string WHITESPACE = " \t\r\n";

//! \brief Returns the text with leading and trailing whitespace removed.
static std::string trim(const std::string& text)
{
    const std::string::size_type first = text.find_first_not_of(WHITESPACE);
    if(first == std::string::npos)
        return std::string();
    const std::string::size_type last = text.find_last_not_of(WHITESPACE);
    return text.substr(first, last - first + 1);
}

//! \brief Returns the text in lower case.
static std::string toLower(const std::string& text)
{
    std::string result = text;
    for(std::string::size_type i = 0; i < result.size(); ++i)
    {
        if(result[i] >= 'A' && result[i] <= 'Z')
            result[i] = static_cast<char>(result[i] - 'A' + 'a');
    }
    return result;
}

//! \brief Splits the text at whitespace.
static std::vector<std::string> splitTokens(const std::string& text)
{
    std::vector<std::string> tokens;
    std::istringstream stream(text);
    std::string token;
    while(stream >> token)
        tokens.push_back(token);
    return tokens;
}

//! \brief Parses a whole token as a number.
//! \return false when the token is not a number.
static bool parseNumber(const std::string& token, double& value)
{
    if(token.empty())
        return false;
    char* end = nullptr;
    value = std::strtod(token.c_str(), &end);
    return (end != nullptr) && (*end == '\0');
}

//! \brief Writes a number the way a generated skill line holds it.
static std::string formatNumber(double value)
{
    std::ostringstream stream;
    stream << std::setprecision(LINE_PRECISION) << value;
    return stream.str();
}

//! \brief Parses a cell that is a number or "-".
static bool parseSkillNumber(const std::string& text, SkillNumber& number)
{
    const std::string cell = trim(text);
    number = SkillNumber();
    if(cell == UNUSED_CELL)
        return true;
    double value = 0.0;
    if(!parseNumber(cell, value))
        return false;
    number.mSet = true;
    number.mValue = value;
    return true;
}

//! \brief Parses a list of numbers or "-" (empty list).
static bool parseNumberList(const std::string& text, std::vector<double>& numbers)
{
    numbers.clear();
    const std::vector<std::string> tokens = splitTokens(text);
    if(tokens.size() == 1 && tokens[0] == UNUSED_CELL)
        return true;
    for(std::vector<std::string>::const_iterator it = tokens.begin(); it != tokens.end(); ++it)
    {
        double value = 0.0;
        if(!parseNumber(*it, value))
            return false;
        numbers.push_back(value);
    }
    return true;
}

//! \brief Returns a base line cell as an empty text when it is "-".
static std::string parseBaseLine(const std::string& text)
{
    const std::string line = trim(text);
    if(line == UNUSED_CELL)
        return std::string();
    return line;
}

//! \brief True when the id is the id of a tier 4 skill.
static bool isTierFourId(const std::string& id)
{
    return id.compare(0, TIER_FOUR_PREFIX.size(), TIER_FOUR_PREFIX) == 0;
}

//! \brief True when the skill belongs to the group or family with the given (lower case) name.
static bool belongsTo(const SkillDef& skill, const std::string& groupOrFamily)
{
    if(groupOrFamily.empty())
        return false;
    return (toLower(skill.mGroup) == groupOrFamily) || (toLower(skill.mFamily) == groupOrFamily);
}

//! \brief True when the skill is a path skill of the creature type.
static bool belongsToType(const SkillDef& skill, const TypeInfo& type)
{
    return belongsTo(skill, toLower(type.mGroup)) || belongsTo(skill, toLower(type.mFamily));
}

//! \brief Which columns of a skill line a kind scales or replaces (positions after the skill name).
struct KindSpec
{
    KindSpec() :
        mCount(0),
        mLevelMin(-1),
        mDuration(-1),
        mRange(-1),
        mRadius(-1),
        mNeedsBase(false),
        mPair(false)
    {}

    //! \brief Class name of the skill.
    std::string mClass;
    //! \brief Number of columns after the name.
    size_t mCount;
    //! \brief Column of LevelMin (-1 = none).
    int mLevelMin;
    //! \brief Column of the duration (-1 = none).
    int mDuration;
    //! \brief Column of the range (-1 = none).
    int mRange;
    //! \brief Column of the radius (-1 = none).
    int mRadius;
    //! \brief Columns the rank value replaces.
    std::vector<int> mReplace;
    //! \brief Columns the rank value multiplies.
    std::vector<int> mMultiply;
    //! \brief True when the kind needs a base line (the rest of its columns cannot be made up).
    bool mNeedsBase;
    //! \brief True when the value is a "p/s" pair replacing the first two columns of mReplace.
    bool mPair;
};

//! \brief Fills the column layout of a kind of 7.4 / 7.6 (the order of the columns is the one of the class loader).
//! \return false for kinds without a skill line.
static bool getKindSpec(const std::string& kind, KindSpec& spec)
{
    spec = KindSpec();
    if(kind == "BUFF_SELF_StrengthChange" || kind == "BUFF_SELF_SpeedChange")
    {
        spec.mClass = (kind == "BUFF_SELF_StrengthChange") ? "StrengthSelf" : "HasteSelf";
        spec.mCount = 5;
        spec.mLevelMin = 2;
        spec.mDuration = 3;
        spec.mReplace.push_back(4);
    }
    else if(kind == "BUFF_SELF_Defense")
    {
        spec.mClass = "DefenseSelf";
        spec.mCount = 7;
        spec.mLevelMin = 2;
        spec.mDuration = 3;
        spec.mReplace.push_back(4);
        spec.mReplace.push_back(5);
        spec.mReplace.push_back(6);
    }
    else if(kind == "DEBUFF_Weak" || kind == "DEBUFF_Slow")
    {
        spec.mClass = (kind == "DEBUFF_Weak") ? "Weak" : "Slow";
        spec.mCount = 6;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mDuration = 4;
        spec.mReplace.push_back(5);
    }
    else if(kind == "AURA_ALLY_StrengthChange")
    {
        spec.mClass = "AuraAlly";
        spec.mCount = 7;
        spec.mLevelMin = 2;
        spec.mRadius = 3;
        spec.mDuration = 4;
        spec.mReplace.push_back(5);
    }
    else if(kind == "STRIKE")
    {
        spec.mClass = "Strike";
        spec.mCount = 4;
        spec.mLevelMin = 2;
        spec.mReplace.push_back(3);
    }
    else if(kind == "HEAL_SELF")
    {
        spec.mClass = "HealSelf";
        spec.mCount = 6;
        spec.mLevelMin = 2;
        spec.mDuration = 3;
        spec.mReplace.push_back(5);
    }
    else if(kind == "HEAL_ALLY")
    {
        spec.mClass = "HealAlly";
        spec.mCount = 5;
        spec.mLevelMin = 2;
        spec.mRange = 3;
        spec.mReplace.push_back(4);
    }
    else if(kind == "HEAL_AREA")
    {
        spec.mClass = "HealArea";
        spec.mCount = 5;
        spec.mLevelMin = 2;
        spec.mRadius = 3;
        spec.mReplace.push_back(4);
    }
    else if(kind == "EXPLOSION")
    {
        spec.mClass = "Explosion";
        spec.mCount = 7;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mDuration = 4;
        spec.mMultiply.push_back(5);
        spec.mMultiply.push_back(6);
        spec.mNeedsBase = true;
    }
    else if(kind == "HAILSTORM" || kind == "GASCLOUD")
    {
        spec.mClass = (kind == "HAILSTORM") ? "HailStorm" : "GasCloud";
        spec.mCount = 9;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mRadius = 4;
        spec.mDuration = 5;
        spec.mMultiply.push_back(6);
        spec.mMultiply.push_back(8);
        spec.mNeedsBase = true;
    }
    else if(kind == "GUIDEDBOLT" || kind == "GRENADE")
    {
        const bool grenade = (kind == "GRENADE");
        spec.mClass = grenade ? "Grenade" : "GuidedBolt";
        spec.mCount = grenade ? 21 : 20;
        spec.mRange = 2;
        spec.mLevelMin = 4;
        for(int column = 8; column <= 13; ++column)
            spec.mMultiply.push_back(column);
        for(int column = (grenade ? 15 : 14); column < static_cast<int>(spec.mCount); ++column)
            spec.mMultiply.push_back(column);
        spec.mNeedsBase = true;
    }
    else if(kind == "WHIRLWIND")
    {
        spec.mClass = "Whirlwind";
        spec.mCount = 6;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mReplace.push_back(4);
        spec.mReplace.push_back(5);
        spec.mPair = true;
        spec.mNeedsBase = true;
    }
    else if(kind == "FREEZE")
    {
        spec.mClass = "Freeze";
        spec.mCount = 5;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mMultiply.push_back(4);
        spec.mNeedsBase = true;
    }
    else if(kind == "INVISIBLE")
    {
        spec.mClass = "Invisible";
        spec.mCount = 4;
        spec.mLevelMin = 2;
        spec.mReplace.push_back(3);
        spec.mNeedsBase = true;
    }
    else if(kind == "TELEPORT")
    {
        spec.mClass = "Teleport";
        spec.mCount = 5;
        spec.mLevelMin = 2;
        spec.mNeedsBase = true;
    }
    else if(kind == "DRAIN")
    {
        spec.mClass = "Drain";
        spec.mCount = 5;
        spec.mRange = 2;
        spec.mLevelMin = 3;
        spec.mReplace.push_back(4);
        spec.mNeedsBase = true;
    }
    else if(kind == "RAISEDEAD")
    {
        spec.mClass = "RaiseDead";
        spec.mCount = 7;
        spec.mLevelMin = 2;
        spec.mDuration = 5;
        spec.mReplace.push_back(4);
        spec.mNeedsBase = true;
    }
    else if(kind == "SKELARMY")
    {
        spec.mClass = "SkeletonArmy";
        spec.mCount = 7;
        spec.mRadius = 6;
        spec.mLevelMin = 2;
        spec.mDuration = 4;
        spec.mReplace.push_back(3);
        spec.mNeedsBase = true;
    }
    else
        return false;

    return true;
}

//! \brief Splits a rank value "p/s" into its two numbers; a plain number gives the same number twice.
static bool parsePair(const std::string& value, double& first, double& second)
{
    const std::string::size_type slash = value.find('/');
    if(slash == std::string::npos)
    {
        if(!parseNumber(value, first))
            return false;
        second = first;
        return true;
    }
    return parseNumber(value.substr(0, slash), first) && parseNumber(value.substr(slash + 1), second);
}

//! \brief Returns the rank of the skill, 0 when it has none.
static uint32_t rankOf(const SkillBuild& build, const std::string& id)
{
    std::map<std::string, uint32_t>::const_iterator it = build.mRanks.find(id);
    if(it == build.mRanks.end())
        return 0;
    return it->second;
}

//! \brief Raises the first skill of a list that can be raised.
//! \return The id that was raised, empty if none.
static std::string raiseFirst(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build,
    const std::vector<std::string>& ids, uint32_t maxRank)
{
    for(std::vector<std::string>::const_iterator it = ids.begin(); it != ids.end(); ++it)
    {
        if(it->empty() || !canRaise(config, type, build, *it, maxRank))
            continue;

        ++build.mRanks[*it];
        return *it;
    }
    return std::string();
}

//! \brief Returns the name of the family path of the type (empty if it has no family or the config has no skill of it).
static std::string familyPathName(const SkillTreeConfig& config, const TypeInfo& type)
{
    const std::string family = toLower(type.mFamily);
    if(family.empty())
        return std::string();
    const std::vector<SkillDef>& skills = config.getSkills();
    for(std::vector<SkillDef>::const_iterator it = skills.begin(); it != skills.end(); ++it)
    {
        if(toLower(it->mFamily) == family)
            return it->mPath;
    }
    return std::string();
}

//! \brief The ids of tier 1 to 3 of a path in tier order.
static std::vector<std::string> pathIds(const SkillTreeConfig& config, const std::string& groupOrFamily,
    const std::string& pathName)
{
    std::vector<std::string> ids;
    for(uint32_t tier = 1; tier <= MAX_TIER; ++tier)
        ids.push_back(config.findPathSkill(groupOrFamily, pathName, tier));
    return ids;
}
}

//! \brief Loads skill definitions including per-skill ally thresholds.
bool SkillTreeConfig::load(std::istream& is, std::string& error)
{
    mSkills.clear();
    mTierFours.clear();
    mTemplates.clear();

    enum Section
    {
        sectionNone,
        sectionSkill,
        sectionTierFour,
        sectionTemplate
    };
    Section section = sectionNone;
    SkillDef skill;
    TierFourDef tierFour;
    TemplateDef templ;
    uint32_t lineNumber = 0;
    std::string line;
    while(std::getline(is, line))
    {
        ++lineNumber;
        const std::string::size_type comment = line.find('#');
        if(comment != std::string::npos)
            line = line.substr(0, comment);
        line = trim(line);
        if(line.empty())
            continue;

        std::ostringstream where;
        where << "line " << lineNumber << ": ";
        std::string key = line;
        std::string rest;
        const std::string::size_type split = line.find_first_of(" \t");
        if(split != std::string::npos)
        {
            key = line.substr(0, split);
            rest = trim(line.substr(split));
        }

        if(key == "[Skill]" || key == "[TierFour]" || key == "[Template]")
        {
            if(section != sectionNone)
            {
                error = where.str() + "block not closed";
                return false;
            }
            if(key == "[Skill]")
            {
                section = sectionSkill;
                skill = SkillDef();
            }
            else if(key == "[TierFour]")
            {
                section = sectionTierFour;
                tierFour = TierFourDef();
            }
            else
            {
                section = sectionTemplate;
                templ = TemplateDef();
            }
            continue;
        }

        if(key == "[/Skill]")
        {
            if(section != sectionSkill || skill.mId.empty() || skill.mKind.empty() || skill.mPath.empty() ||
               skill.mTier < 1 || skill.mTier > MAX_TIER || skill.mValues.empty() ||
               (skill.mGroup.empty() == skill.mFamily.empty()))
            {
                error = where.str() + "incomplete [Skill] " + skill.mId;
                return false;
            }
            if(findSkill(skill.mId) != nullptr)
            {
                error = where.str() + "duplicate skill " + skill.mId;
                return false;
            }
            mSkills.push_back(skill);
            section = sectionNone;
            continue;
        }
        if(key == "[/TierFour]")
        {
            if(section != sectionTierFour || tierFour.mCreature.empty() || tierFour.mKind.empty() ||
               tierFour.mValue.empty())
            {
                error = where.str() + "incomplete [TierFour] " + tierFour.mCreature;
                return false;
            }
            if(findTierFour(tierFour.mCreature) != nullptr)
            {
                error = where.str() + "duplicate tier four skill " + tierFour.mCreature;
                return false;
            }
            mTierFours.push_back(tierFour);
            section = sectionNone;
            continue;
        }
        if(key == "[/Template]")
        {
            if(section != sectionTemplate || templ.mGroup.empty() || templ.mIndex < 1 || templ.mName.empty() ||
               templ.mPrimary.empty() || templ.mAlternative.empty())
            {
                error = where.str() + "incomplete [Template] " + templ.mName;
                return false;
            }
            mTemplates.push_back(templ);
            section = sectionNone;
            continue;
        }

        bool ok = true;
        if(section == sectionSkill)
        {
            double number = 0.0;
            if(key == "Id")
                skill.mId = rest;
            else if(key == "Name")
                skill.mName = rest;
            else if(key == "Kind")
                skill.mKind = rest;
            else if(key == "Group")
                skill.mGroup = rest;
            else if(key == "Family")
                skill.mFamily = toLower(rest);
            else if(key == "Path")
                skill.mPath = rest;
            else if(key == "Tier")
            {
                ok = parseNumber(rest, number);
                skill.mTier = static_cast<uint32_t>(number);
            }
            else if(key == "Values")
                skill.mValues = splitTokens(rest);
            else if(key == "Mana")
                ok = parseNumberList(rest, skill.mMana);
            else if(key == "Cooldown")
                ok = parseSkillNumber(rest, skill.mCooldown);
            else if(key == "Duration")
                ok = parseSkillNumber(rest, skill.mDuration);
            else if(key == "Radius")
                ok = parseSkillNumber(rest, skill.mRadius);
            else if(key == "MinAllies")
                ok = parseSkillNumber(rest, skill.mMinAllies);
            else if(key == "Range")
                ok = parseSkillNumber(rest, skill.mRange);
            else if(key == "BaseLine")
                skill.mBaseLine = parseBaseLine(rest);
            else
                ok = false;
        }
        else if(section == sectionTierFour)
        {
            if(key == "Creature")
                tierFour.mCreature = rest;
            else if(key == "Name")
                tierFour.mName = rest;
            else if(key == "Kind")
                tierFour.mKind = rest;
            else if(key == "Value")
                tierFour.mValue = rest;
            else if(key == "Cooldown")
                ok = parseSkillNumber(rest, tierFour.mCooldown);
            else if(key == "Duration")
                ok = parseSkillNumber(rest, tierFour.mDuration);
            else if(key == "Mana")
                ok = parseSkillNumber(rest, tierFour.mMana);
            else if(key == "Radius")
                ok = parseSkillNumber(rest, tierFour.mRadius);
            else if(key == "Range")
                ok = parseSkillNumber(rest, tierFour.mRange);
            else if(key == "BaseLine")
                tierFour.mBaseLine = parseBaseLine(rest);
            else
                ok = false;
        }
        else if(section == sectionTemplate)
        {
            double number = 0.0;
            if(key == "Group")
                templ.mGroup = rest;
            else if(key == "Index")
            {
                ok = parseNumber(rest, number);
                templ.mIndex = static_cast<uint32_t>(number);
            }
            else if(key == "Name")
                templ.mName = rest;
            else if(key == "Primary")
                templ.mPrimary = rest;
            else if(key == "Alternative")
                templ.mAlternative = rest;
            else
                ok = false;
        }
        else
            ok = false;

        if(!ok)
        {
            error = where.str() + "cannot read '" + key + "'";
            return false;
        }
    }

    if(section != sectionNone)
    {
        error = "last block not closed";
        return false;
    }
    return true;
}

const SkillDef* SkillTreeConfig::findSkill(const std::string& id) const
{
    for(std::vector<SkillDef>::const_iterator it = mSkills.begin(); it != mSkills.end(); ++it)
    {
        if(it->mId == id)
            return &(*it);
    }
    return nullptr;
}

const TierFourDef* SkillTreeConfig::findTierFour(const std::string& creature) const
{
    for(std::vector<TierFourDef>::const_iterator it = mTierFours.begin(); it != mTierFours.end(); ++it)
    {
        if(it->mCreature == creature)
            return &(*it);
    }
    return nullptr;
}

const TierFourDef* SkillTreeConfig::findTierFourById(const std::string& id) const
{
    if(!isTierFourId(id))
        return nullptr;
    return findTierFour(id.substr(TIER_FOUR_PREFIX.size()));
}

std::vector<const TemplateDef*> SkillTreeConfig::getTemplates(const std::string& group) const
{
    std::vector<const TemplateDef*> templates;
    for(std::vector<TemplateDef>::const_iterator it = mTemplates.begin(); it != mTemplates.end(); ++it)
    {
        if(it->mGroup != group)
            continue;
        std::vector<const TemplateDef*>::iterator position = templates.begin();
        while(position != templates.end() && (*position)->mIndex < it->mIndex)
            ++position;
        templates.insert(position, &(*it));
    }
    return templates;
}

const TemplateDef* SkillTreeConfig::findTemplate(const std::string& group, int32_t index) const
{
    if(index < 0)
        return nullptr;
    std::vector<const TemplateDef*> templates = getTemplates(group);
    if(static_cast<size_t>(index) >= templates.size())
        return nullptr;
    return templates[static_cast<size_t>(index)];
}

std::string SkillTreeConfig::findPathSkill(const std::string& groupOrFamily, const std::string& pathName,
    uint32_t tier) const
{
    const std::string owner = toLower(groupOrFamily);
    const std::string path = toLower(pathName);
    for(std::vector<SkillDef>::const_iterator it = mSkills.begin(); it != mSkills.end(); ++it)
    {
        if(it->mTier == tier && toLower(it->mPath) == path && belongsTo(*it, owner))
            return it->mId;
    }
    return std::string();
}

std::vector<std::string> SkillTreeConfig::getPathNames(const TypeInfo& type) const
{
    std::vector<std::string> names;
    const std::string owners[2] = {toLower(type.mGroup), toLower(type.mFamily)};
    for(uint32_t i = 0; i < 2; ++i)
    {
        for(std::vector<SkillDef>::const_iterator it = mSkills.begin(); it != mSkills.end(); ++it)
        {
            if(!belongsTo(*it, owners[i]))
                continue;
            if(std::find(names.begin(), names.end(), it->mPath) == names.end())
                names.push_back(it->mPath);
        }
    }
    return names;
}

uint32_t pointsAtLevel(uint32_t level, uint32_t firstLevel)
{
    if(level < firstLevel)
        return 0;
    return level - firstLevel + 1;
}

uint32_t getRank(const SkillBuild& build, const std::string& id)
{
    return rankOf(build, id);
}

uint32_t spentInPaths(const SkillBuild& build, const TypeInfo& type)
{
    uint32_t spent = 0;
    for(std::map<std::string, uint32_t>::const_iterator it = build.mRanks.begin(); it != build.mRanks.end(); ++it)
    {
        if(!isTierFourId(it->first))
            spent += it->second;
    }
    // The free rank of the pre-skill is not a spent point
    if(!type.mPreSkill.empty() && rankOf(build, type.mPreSkill) >= 1 && spent > 0)
        --spent;
    return spent;
}

uint32_t spentPoints(const SkillBuild& build, const TypeInfo& type)
{
    uint32_t spent = spentInPaths(build, type);
    if(!type.mTierFour.empty() && rankOf(build, type.mTierFour) > 0)
        ++spent;
    return spent;
}

//! \brief Checks configured tier unlock requirements for a skill rank.
bool canRaise(const SkillTreeConfig& config, const TypeInfo& type, const SkillBuild& build, const std::string& id,
    uint32_t maxRank)
{
    if(id.empty())
        return false;

    if(isTierFourId(id))
    {
        return (id == type.mTierFour) && (rankOf(build, id) == 0) && (maxRank >= 1) &&
            (spentInPaths(build, type) >= static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier4MinSpent()));
    }

    const SkillDef* skill = config.findSkill(id);
    if(skill == nullptr || !belongsToType(*skill, type))
        return false;
    if(rankOf(build, id) >= maxRank)
        return false;

    if(skill->mTier <= 1)
        return true;

    const std::string owner = skill->mGroup.empty() ? skill->mFamily : skill->mGroup;
    const std::string previous = config.findPathSkill(owner, skill->mPath, skill->mTier - 1);
    const uint32_t needed = (skill->mTier == 2) ? static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier2UnlockRanks()) : static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier3UnlockRanks());
    return !previous.empty() && (rankOf(build, previous) >= needed);
}

//! \brief Builds template picks using the configured tier unlock ranks.
std::vector<std::string> templatePicks(const SkillTreeConfig& config, const TypeInfo& type, int32_t templateIndex,
    uint32_t maxRank)
{
    std::vector<std::string> picks;
    const TemplateDef* templ = config.findTemplate(type.mGroup, templateIndex);
    if(templ == nullptr)
        return picks;

    const std::vector<std::string> primary = pathIds(config, type.mGroup, templ->mPrimary);
    // The order is derived from the configured unlock ranks: tier 1 up to the rank that unlocks tier 2, tier 2 up to
    // the rank that unlocks tier 3, tier 3 once, then every tier up to the highest rank
    const uint32_t tier2Ranks = std::min(maxRank,
        static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier2UnlockRanks()));
    const uint32_t tier3Ranks = std::min(maxRank,
        static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier3UnlockRanks()));
    for(uint32_t i = 0; i < tier2Ranks; ++i)
        picks.push_back(primary[0]);
    for(uint32_t i = 0; i < tier3Ranks; ++i)
        picks.push_back(primary[1]);
    picks.push_back(primary[2]);
    for(uint32_t i = tier2Ranks; i < maxRank; ++i)
        picks.push_back(primary[0]);
    for(uint32_t i = tier3Ranks; i < maxRank; ++i)
        picks.push_back(primary[1]);
    for(uint32_t i = 1; i < maxRank; ++i)
        picks.push_back(primary[2]);

    if(!type.mFamily.empty())
    {
        const std::vector<std::string> family = pathIds(config, type.mFamily, familyPathName(config, type));
        picks.push_back(family[0]);
        picks.push_back(family[0]);
        picks.push_back(family[1]);
        picks.push_back(family[1]);
        picks.push_back(family[2]);
    }
    return picks;
}

uint32_t nextDeviationDraw(SkillBuild& build)
{
    const uint64_t state = (RNG_MULTIPLIER * static_cast<uint64_t>(build.mRngState) + RNG_INCREMENT) & RNG_MASK;
    build.mRngState = static_cast<uint32_t>(state);
    return static_cast<uint32_t>(state % DEVIATION_RANGE);
}

void startBuild(SkillBuild& build, const TypeInfo& type, uint32_t seed)
{
    if(build.mSeed != 0 || seed == 0)
        return;

    build.mSeed = seed;
    build.mRngState = seed;
    if(!type.mPreSkill.empty())
        build.mRanks[type.mPreSkill] = 1;
}

//! \brief Spends the next skill point using the configured deviation and tier limits.
std::string spendNextPoint(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build,
    double deviationPercent, uint32_t maxRank)
{
    if(type.mGroup.empty() || build.mTemplate < 0)
        return std::string();

    const uint32_t spent = spentInPaths(build, type);
    if(spent >= static_cast<uint32_t>(ConfigManager::getSingleton().getSkillTier4MinSpent()))
    {
        std::vector<std::string> tierFour;
        tierFour.push_back(type.mTierFour);
        return raiseFirst(config, type, build, tierFour, maxRank);
    }

    const TemplateDef* templ = config.findTemplate(type.mGroup, build.mTemplate);
    if(templ == nullptr)
        return std::string();

    // The points that deviate go to the alternative path (tier 1 to 5, then tier 2, then tier 3)
    if(spent < static_cast<uint32_t>(ConfigManager::getSingleton().getSkillDeviationPoints()))
    {
        const uint32_t draw = nextDeviationDraw(build);
        if(static_cast<double>(draw) < deviationPercent)
        {
            const std::string raised = raiseFirst(config, type, build,
                pathIds(config, type.mGroup, templ->mAlternative), maxRank);
            if(!raised.empty())
                return raised;
        }
    }

    // The template order: a pick at the highest rank is skipped and used up
    const std::vector<std::string> picks = templatePicks(config, type, build.mTemplate, maxRank);
    while(build.mPickCursor < picks.size())
    {
        const std::string pick = picks[build.mPickCursor];
        ++build.mPickCursor;
        if(canRaise(config, type, build, pick, maxRank))
        {
            ++build.mRanks[pick];
            return pick;
        }
    }

    // Nothing is left of the template: the family path, then every other path of the creature
    std::vector<std::string> overflow;
    const std::string familyPath = familyPathName(config, type);
    if(!familyPath.empty())
    {
        const std::vector<std::string> family = pathIds(config, type.mFamily, familyPath);
        overflow.insert(overflow.end(), family.begin(), family.end());
    }
    const std::vector<std::string> names = config.getPathNames(type);
    for(size_t i = 0; i < names.size(); ++i)
    {
        if(names[i] == familyPath)
            continue;
        const std::vector<std::string> path = pathIds(config, type.mGroup, names[i]);
        overflow.insert(overflow.end(), path.begin(), path.end());
    }
    return raiseFirst(config, type, build, overflow, maxRank);
}

void spendUpToLevel(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build, uint32_t level,
    uint32_t firstLevel, double deviationPercent, uint32_t maxRank)
{
    const uint32_t target = pointsAtLevel(level, firstLevel);
    while(spentPoints(build, type) < target)
    {
        if(spendNextPoint(config, type, build, deviationPercent, maxRank).empty())
            break;
    }
}

//! \brief Chooses a template with the configured weight for unfollowed templates.
int32_t chooseTemplate(const std::vector<uint32_t>& followers, double unit)
{
    if(followers.empty())
        return -1;

    uint32_t total = 0;
    for(size_t i = 0; i < followers.size(); ++i)
        total += (followers[i] == 0) ? static_cast<uint32_t>(ConfigManager::getSingleton().getSkillUnfollowedWeight()) : 1;

    double position = unit * static_cast<double>(total);
    for(size_t i = 0; i < followers.size(); ++i)
    {
        position -= static_cast<double>((followers[i] == 0) ? static_cast<uint32_t>(ConfigManager::getSingleton().getSkillUnfollowedWeight()) : 1);
        if(position < 0.0)
            return static_cast<int32_t>(i);
    }
    return static_cast<int32_t>(followers.size() - 1);
}

void resetBuild(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build, int32_t newTemplate,
    uint32_t level, uint32_t firstLevel, double deviationPercent, uint32_t maxRank)
{
    build.mRanks.clear();
    if(!type.mPreSkill.empty())
        build.mRanks[type.mPreSkill] = 1;
    build.mTemplate = newTemplate;
    build.mPickCursor = 0;
    build.mRngState = build.mSeed;
    spendUpToLevel(config, type, build, level, firstLevel, deviationPercent, maxRank);
}

//! \brief Finds a reset template after the configured follower minimum.
int32_t findResetTemplate(int32_t current, const std::vector<uint32_t>& followers)
{
    if(current < 0 || static_cast<size_t>(current) >= followers.size())
        return -1;
    if(followers[static_cast<size_t>(current)] < static_cast<uint32_t>(ConfigManager::getSingleton().getSkillResetMinFollowers()))
        return -1;

    for(size_t i = 0; i < followers.size(); ++i)
    {
        if(static_cast<int32_t>(i) != current && followers[i] == 0)
            return static_cast<int32_t>(i);
    }
    return -1;
}

void countChicken(SkillBuild& build, uint32_t chickensNeeded, double windowSeconds)
{
    if(chickensNeeded == 0)
        return;

    ++build.mChickens;
    if(build.mChickens >= chickensNeeded)
    {
        build.mChickens = 0;
        build.mRespecWindow = windowSeconds;
    }
}

void tickRespecWindow(SkillBuild& build, double seconds)
{
    if(build.mRespecWindow <= 0.0)
        return;
    build.mRespecWindow = std::max(0.0, build.mRespecWindow - seconds);
}

double rankValue(const SkillDef& skill, uint32_t rank)
{
    if(rank == 0 || skill.mValues.empty())
        return 0.0;

    const size_t index = std::min(static_cast<size_t>(rank), skill.mValues.size()) - 1;
    double first = 0.0;
    double second = 0.0;
    if(!parsePair(skill.mValues[index], first, second))
        return 0.0;
    return first;
}

double passiveSum(const SkillTreeConfig& config, const SkillBuild& build, const std::string& stat)
{
    const std::string kind = PASSIVE_PREFIX + stat;
    double sum = 0.0;
    for(std::map<std::string, uint32_t>::const_iterator it = build.mRanks.begin(); it != build.mRanks.end(); ++it)
    {
        if(it->second == 0)
            continue;

        if(isTierFourId(it->first))
        {
            const TierFourDef* tierFour = config.findTierFourById(it->first);
            double value = 0.0;
            if(tierFour != nullptr && tierFour->mKind == kind && parseNumber(tierFour->mValue, value))
                sum += value;
            continue;
        }

        const SkillDef* skill = config.findSkill(it->first);
        if(skill != nullptr && skill->mKind == kind)
            sum += rankValue(*skill, it->second);
    }
    return sum;
}

std::string skillClassOfKind(const std::string& kind)
{
    KindSpec spec;
    if(!getKindSpec(kind, spec))
        return std::string();
    return spec.mClass;
}

//! \brief Builds the runtime skill line with configured ally thresholds and radii.
std::string buildSkillLine(const std::string& kind, const std::string& value, const SkillNumber& cooldown,
    const SkillNumber& duration, const SkillNumber& radius, const SkillNumber& range, const std::string& baseLine,
    const SkillNumber& minAllies)
{
    KindSpec spec;
    if(!getKindSpec(kind, spec))
        return std::string();

    std::vector<std::string> tokens(spec.mCount, "0");
    if(!baseLine.empty())
    {
        std::vector<std::string> base = splitTokens(baseLine);
        // Older base lines omit the new aura threshold or summoning radius.
        if(base.size() == spec.mCount && (spec.mClass == "SkeletonArmy" || spec.mClass == "AuraAlly"))
            base.push_back(std::to_string(spec.mClass == "AuraAlly" ?
                ConfigManager::getSingleton().getAuraAllyMinAllies() : ConfigManager::getSingleton().getSkeletonArmyRadius()));
        // The first token is the class name of the line
        if(base.size() != spec.mCount + 1 || base[0] != spec.mClass)
            return std::string();
        tokens.assign(base.begin() + 1, base.end());
    }
    else if(spec.mNeedsBase)
        return std::string();

    if(spec.mClass == "AuraAlly")
    {
        tokens[6] = formatNumber(ConfigManager::getSingleton().getAuraAllyMinAllies());
    }
    if(spec.mClass == "SkeletonArmy" && !radius.mSet)
    {
        tokens[6] = std::to_string(ConfigManager::getSingleton().getSkeletonArmyRadius());
    }
    if(cooldown.mSet)
        tokens[0] = formatNumber(cooldown.mValue);
    // The rank 1 reached means the skill is usable: no level limit
    if(spec.mLevelMin >= 0)
        tokens[static_cast<size_t>(spec.mLevelMin)] = "0";
    if(duration.mSet && spec.mDuration >= 0)
        tokens[static_cast<size_t>(spec.mDuration)] = formatNumber(duration.mValue);
    if(radius.mSet && spec.mRadius >= 0)
        tokens[static_cast<size_t>(spec.mRadius)] = formatNumber(radius.mValue);
    if(range.mSet && spec.mRange >= 0)
        tokens[static_cast<size_t>(spec.mRange)] = formatNumber(range.mValue);

    double first = 0.0;
    double second = 0.0;
    if(!parsePair(value, first, second))
        return std::string();

    if(spec.mPair)
    {
        tokens[static_cast<size_t>(spec.mReplace[0])] = formatNumber(first);
        tokens[static_cast<size_t>(spec.mReplace[1])] = formatNumber(second);
    }
    else
    {
        for(size_t i = 0; i < spec.mReplace.size(); ++i)
            tokens[static_cast<size_t>(spec.mReplace[i])] = formatNumber(first);
    }
    for(size_t i = 0; i < spec.mMultiply.size(); ++i)
    {
        double column = 0.0;
        std::string& token = tokens[static_cast<size_t>(spec.mMultiply[i])];
        if(!parseNumber(token, column))
            return std::string();
        token = formatNumber(column * first);
    }

    std::string line = spec.mClass;
    for(size_t i = 0; i < tokens.size(); ++i)
        line += " " + tokens[i];
    return line;
}

void writeBuild(const SkillBuild& build, std::ostream& os)
{
    // The window is written with the digits of a double; the precision of the caller's stream is restored
    const std::streamsize oldPrecision = os.precision(WINDOW_PRECISION);
    os << build.mTemplate << " " << build.mSeed << " " << build.mRngState << " " << build.mPickCursor << " "
       << build.mChickens << " " << build.mRespecWindow << " " << build.mRanks.size();
    os.precision(oldPrecision);
    for(std::map<std::string, uint32_t>::const_iterator it = build.mRanks.begin(); it != build.mRanks.end(); ++it)
        os << " " << it->first << " " << it->second;
}

bool readBuild(std::istream& is, SkillBuild& build)
{
    build = SkillBuild();
    size_t nbRanks = 0;
    if(!(is >> build.mTemplate >> build.mSeed >> build.mRngState >> build.mPickCursor >> build.mChickens >>
         build.mRespecWindow >> nbRanks))
    {
        return false;
    }

    for(size_t i = 0; i < nbRanks; ++i)
    {
        std::string id;
        uint32_t rank = 0;
        if(!(is >> id >> rank))
            return false;
        build.mRanks[id] = rank;
    }
    return true;
}
}
