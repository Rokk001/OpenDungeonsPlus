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

#ifndef CREATURESKILLTREE_H
#define CREATURESKILLTREE_H

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <vector>

//! \brief Data and rules of the creature skill trees (config/creatureSkills.cfg): skill definitions, tier 4 skills,
//! templates, the point order of a template, the personal deviation, the reset rules and the saved state of a build.
//! This file only depends on the standard library so that its rules can be tested on their own.
namespace CreatureSkillTree
{
//! \brief A number of the skill table that may be written as "-" (not used).
struct SkillNumber
{
    SkillNumber() :
        mSet(false),
        mValue(0.0)
    {}

    //! \brief True when the cell holds a number, false when it was written as "-".
    bool mSet;
    //! \brief The number (0 while not set).
    double mValue;
};

//! \brief One [Skill] block: a skill of a path of a group or family (tier 1 to 3, ranks 1 to 5).
struct SkillDef
{
    //! \brief Creates an empty skill definition.
    SkillDef() :
        mTier(0)
    {}

    //! \brief Config id, e.g. BLK_C3.
    std::string mId;
    //! \brief Display name.
    std::string mName;
    //! \brief Kind token, e.g. PASSIVE_dmg%, BUFF_SELF_StrengthChange, EXPLOSION.
    std::string mKind;
    //! \brief Group name (blocker, blitzer, ...) or empty for a family skill.
    std::string mGroup;
    //! \brief Family name (lower case) or empty for a group skill.
    std::string mFamily;
    //! \brief Name of the path the skill belongs to.
    std::string mPath;
    //! \brief Tier 1 to 3.
    uint32_t mTier;
    //! \brief The rank values as written (one token per rank; WHIRLWIND uses "p/s").
    std::vector<std::string> mValues;
    //! \brief Mana cost per rank (empty when the skill costs no mana).
    std::vector<double> mMana;
    SkillNumber mCooldown;
    SkillNumber mDuration;
    //! \brief Fewest allies required by an ally aura.
    SkillNumber mMinAllies;
    SkillNumber mRadius;
    SkillNumber mRange;
    //! \brief The today line the skill scales (empty when "-").
    std::string mBaseLine;
};

//! \brief One [TierFour] block: the single rank skill of a creature type.
struct TierFourDef
{
    //! \brief The creature type (class name).
    std::string mCreature;
    //! \brief Display name.
    std::string mName;
    //! \brief Kind token.
    std::string mKind;
    //! \brief The value as written (a number or "p/s").
    std::string mValue;
    SkillNumber mCooldown;
    SkillNumber mDuration;
    SkillNumber mMana;
    SkillNumber mRadius;
    SkillNumber mRange;
    //! \brief The today line the skill scales (empty when "-").
    std::string mBaseLine;
};

//! \brief One [Template] block: a point order of a group.
struct TemplateDef
{
    TemplateDef() :
        mIndex(0)
    {}

    std::string mGroup;
    //! \brief 1-based index of the template in the group.
    uint32_t mIndex;
    std::string mName;
    //! \brief Name of the primary path (15 points).
    std::string mPrimary;
    //! \brief Name of the path that deviating points go to.
    std::string mAlternative;
};

//! \brief What the skill rules need to know about a creature type.
struct TypeInfo
{
    //! \brief Skill group name or empty (none).
    std::string mGroup;
    //! \brief Skill family name (lower case) or empty (none).
    std::string mFamily;
    //! \brief Id of the skill that has rank 1 for free or empty (none).
    std::string mPreSkill;
    //! \brief Id of the tier 4 skill (T4_<type>) or empty (none).
    std::string mTierFour;
};

//! \brief The skill state of one creature, saved and sent to clients.
struct SkillBuild
{
    SkillBuild() :
        mTemplate(-1),
        mSeed(0),
        mRngState(0),
        mPickCursor(0),
        mChickens(0),
        mRespecWindow(0.0)
    {}

    //! \brief 0-based template index inside the group, -1 while no template was chosen.
    int32_t mTemplate;
    //! \brief Personal random seed (0 while the build was never started).
    uint32_t mSeed;
    //! \brief State of the personal generator used for the deviation draws.
    uint32_t mRngState;
    //! \brief Number of picks of the template order that were used up (a deviated point does not use up a pick).
    uint32_t mPickCursor;
    //! \brief Number of chickens eaten since the reset window last opened.
    uint32_t mChickens;
    //! \brief Seconds left of the open reset window (0 = closed).
    double mRespecWindow;
    //! \brief Rank per skill id (tier 4 skills included, the free rank of the pre-skill included).
    std::map<std::string, uint32_t> mRanks;
};

//! \brief All skill definitions of the config file and the rules working on them.
class SkillTreeConfig
{
public:
    //! \brief Reads the blocks of config/creatureSkills.cfg.
    //! \param is The config text.
    //! \param error Receives a description of the first error.
    //! \return false on a syntax error (the content is then unspecified).
    bool load(std::istream& is, std::string& error);

    //! \brief Returns the skill (tier 1 to 3) with the given id or nullptr.
    const SkillDef* findSkill(const std::string& id) const;
    //! \brief Returns the tier 4 skill of the given creature type or nullptr.
    const TierFourDef* findTierFour(const std::string& creature) const;
    //! \brief Returns the tier 4 skill with the given id (T4_<type>) or nullptr.
    const TierFourDef* findTierFourById(const std::string& id) const;
    //! \brief Returns the templates of a group in the order of their index.
    std::vector<const TemplateDef*> getTemplates(const std::string& group) const;
    //! \brief Returns the template of a group with the given 0-based index or nullptr.
    const TemplateDef* findTemplate(const std::string& group, int32_t index) const;
    //! \brief Returns the id of the skill of the given tier in the named path of a group or family, empty if none.
    //! \param pathName The path name (compared without regard to case).
    std::string findPathSkill(const std::string& groupOrFamily, const std::string& pathName, uint32_t tier) const;
    //! \brief Returns the names of the paths a type has: the 3 group paths, then the family path.
    std::vector<std::string> getPathNames(const TypeInfo& type) const;

    inline const std::vector<SkillDef>& getSkills() const
    { return mSkills; }
    inline const std::vector<TierFourDef>& getTierFours() const
    { return mTierFours; }
    inline const std::vector<TemplateDef>& getTemplateDefs() const
    { return mTemplates; }

private:
    std::vector<SkillDef> mSkills;
    std::vector<TierFourDef> mTierFours;
    std::vector<TemplateDef> mTemplates;
};

//! \brief Prefix of a tier 4 skill id.
extern const std::string TIER_FOUR_PREFIX;
//! \brief Highest tier of a path.
extern const uint32_t MAX_TIER;
//! \brief Ranks needed in tier 1 before tier 2 of a path can be raised.
// Read at use time through ConfigManager::getSkillTier2UnlockRanks().
//! \brief Ranks needed in tier 2 before tier 3 of a path can be raised.
// Read at use time through ConfigManager::getSkillTier3UnlockRanks().
//! \brief Points that must be spent in the paths before the tier 4 skill can be raised.
// Read at use time through ConfigManager::getSkillTier4MinSpent().
//! \brief Number of points (the first ones) that draw a personal deviation.
// Read at use time through ConfigManager::getSkillDeviationPoints().
//! \brief Number of templates followers needed to allow a reset.
// Read at use time through ConfigManager::getSkillResetMinFollowers().
//! \brief Weight factor of a template that no creature of the group follows.
// Read at use time through ConfigManager::getSkillUnfollowedWeight().

//! \brief Skill points of a creature of the given level (0 below the first level with a point).
//! \param firstLevel The level of the first point (SkillPointFirstLevel).
uint32_t pointsAtLevel(uint32_t level, uint32_t firstLevel);

//! \brief Rank of the skill with the given id (0 when it has none).
uint32_t getRank(const SkillBuild& build, const std::string& id);

//! \brief Points spent in the paths: all ranks of tier 1 to 3 skills, without the free rank of the pre-skill.
uint32_t spentInPaths(const SkillBuild& build, const TypeInfo& type);

//! \brief Points spent altogether: spentInPaths plus the tier 4 skill.
uint32_t spentPoints(const SkillBuild& build, const TypeInfo& type);

//! \brief True when the one rank of the given skill can be raised now: rank below maxRank and the unlock rules of
//! 7.2 are met (tier 2 needs 1 rank in tier 1 of the same path, tier 3 needs 2 ranks in tier 2, tier 4 needs
//! TIER_FOUR_MIN_SPENT points spent in the paths and has rank 1 only).
//! \param id The id of a tier 1 to 3 skill or the tier 4 id of the type.
bool canRaise(const SkillTreeConfig& config, const TypeInfo& type, const SkillBuild& build, const std::string& id,
    uint32_t maxRank);

//! \brief The picks of a template in their order: each entry is the id of the skill whose rank is raised by 1
//! (primary path 15 points, then the family path tier 1, 1, 2, 2, 3).
//! \param maxRank SkillRanksPerSkill.
std::vector<std::string> templatePicks(const SkillTreeConfig& config, const TypeInfo& type, int32_t templateIndex,
    uint32_t maxRank);

//! \brief Draws the next number 0..99 of the personal generator (x = (1103515245 x + 12345) mod 2^31, d = x mod 100).
uint32_t nextDeviationDraw(SkillBuild& build);

//! \brief Starts a build: sets the seed and the generator state, gives rank 1 of the pre-skill. Does nothing when
//! the build was started already (seed not 0).
//! \param seed A random 32-bit seed that is not 0.
void startBuild(SkillBuild& build, const TypeInfo& type, uint32_t seed);

//! \brief Spends one point as the template order (with the personal deviation) says. Does nothing when no point
//! can be spent (nothing left to raise or no template).
//! \param deviationPercent SkillTemplateDeviationPercent.
//! \param maxRank SkillRanksPerSkill.
//! \return The id of the raised skill, empty if no point could be spent.
std::string spendNextPoint(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build,
    double deviationPercent, uint32_t maxRank);

//! \brief Spends points until the build has spent the points a creature of the level owns.
//! \param level The creature level.
void spendUpToLevel(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build, uint32_t level,
    uint32_t firstLevel, double deviationPercent, uint32_t maxRank);

//! \brief Chooses the template of a first skill point.
//! \param followers Number of already choosing creatures of the group per template (index = template).
//! \param unit A random number in [0, 1).
//! \return The 0-based template index (weight 1 per template, times UNFOLLOWED_WEIGHT when nobody follows it).
int32_t chooseTemplate(const std::vector<uint32_t>& followers, double unit);

//! \brief Takes back all spent points (the free rank of the pre-skill stays), sets the template and spends the
//! points again from the personal seed.
void resetBuild(const SkillTreeConfig& config, const TypeInfo& type, SkillBuild& build, int32_t newTemplate,
    uint32_t level, uint32_t firstLevel, double deviationPercent, uint32_t maxRank);

//! \brief Finds the template a creature may reset to: the creature's template needs at least RESET_MIN_FOLLOWERS
//! followers and another template of the group none.
//! \param followers Followers per template among the own creatures of the group.
//! \return The new template (the one with the lowest index that has no follower), -1 if no reset is allowed.
int32_t findResetTemplate(int32_t current, const std::vector<uint32_t>& followers);

//! \brief Counts one eaten chicken. Opens the reset window when the counter reaches the limit (and sets the counter
//! back to 0).
//! \param chickensNeeded SkillRespecChickens.
//! \param windowSeconds SkillRespecWindowSeconds.
void countChicken(SkillBuild& build, uint32_t chickensNeeded, double windowSeconds);

//! \brief Lets the reset window run down.
//! \param seconds The time that passed.
void tickRespecWindow(SkillBuild& build, double seconds);

//! \brief Sum of the PASSIVE skills of the given stat (e.g. "hp%") at the ranks of the build. The tier 4 skill of a
//! PASSIVE kind counts with its single value at rank 1.
double passiveSum(const SkillTreeConfig& config, const SkillBuild& build, const std::string& stat);

//! \brief The rank value of a skill as a number (the first number of a "p/s" token).
double rankValue(const SkillDef& skill, uint32_t rank);

//! \brief Name of the creature skill class a kind token is built from (e.g. "Explosion"), empty for PASSIVE kinds
//! and unknown kinds.
std::string skillClassOfKind(const std::string& kind);

//! \brief Builds the skill line (class name followed by its columns, as the loader of the class reads it) of an
//! active skill at a rank, from the kind, the table cells and the base line (7.6).
//! \param kind The kind token.
//! \param value The rank value (a number or "p/s").
//! \param cooldown The cooldown cell.
//! \param duration The duration cell.
//! \param radius The radius cell.
//! \param range The range cell.
//! \param baseLine The base line (empty = none).
//! \return The line, empty when the kind has no line.
std::string buildSkillLine(const std::string& kind, const std::string& value, const SkillNumber& cooldown,
    const SkillNumber& duration, const SkillNumber& radius, const SkillNumber& range, const std::string& baseLine,
    const SkillNumber& minAllies = SkillNumber());

//! \brief Writes the build as one line of whitespace separated tokens (the stream and packet form).
void writeBuild(const SkillBuild& build, std::ostream& os);

//! \brief Reads a build written by writeBuild.
//! \return false on a short or malformed input.
bool readBuild(std::istream& is, SkillBuild& build);
}

#endif // CREATURESKILLTREE_H
