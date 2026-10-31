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

#ifndef CREATUREDEFINITION_H
#define CREATUREDEFINITION_H

#include <Ogre.h>

#include <algorithm>
#include <string>
#include <iosfwd>
#include <cstdint>

//! \brief Lowest speed factor of the walk clips of a creature type (WalkClipRate, WalkHurtClipRate)
static const double WALK_CLIP_RATE_MIN = 0.2;

//! \brief Highest speed factor of the walk clips of a creature type (WalkClipRate, WalkHurtClipRate)
static const double WALK_CLIP_RATE_MAX = 8.0;

class CreatureBehaviour;
class CreatureMood;
class CreatureSkill;
class ODPacket;

enum class RoomType;

//! \brief The maximum level of a creature
static const uint32_t MAX_LEVEL = 30;

//! \brief GUI text markup of the crown picture that is shown instead of the level of the champion
static const std::string CHAMPION_CROWN_MARKUP = "[image-size='w:16 h:16'][image='ChampionCrown/Crown']";

class CreatureRoomAffinity
{
public:
    CreatureRoomAffinity(RoomType roomType, int32_t likeness, double efficiency):
        mRoomType(roomType),
        mLikeness(likeness),
        mEfficiency(efficiency)
    {
    }

    inline RoomType getRoomType() const
    { return mRoomType; }

    inline int32_t getLikeness() const
    { return mLikeness; }

    inline double getEfficiency() const
    { return mEfficiency; }

    bool operator==(const CreatureRoomAffinity& creatureRoomAffinity) const
    {
        return mRoomType == creatureRoomAffinity.mRoomType &&
            mLikeness == creatureRoomAffinity.mLikeness &&
            mEfficiency == creatureRoomAffinity.mEfficiency;
    }

private:
    RoomType mRoomType;
    int32_t mLikeness;
    double mEfficiency;
};

//! \brief Stores creature type statistics, combat ratings, avoidance and skill definitions.
class CreatureDefinition
{
public:
    enum CreatureJob
    {
        Worker = 1, // Dig, claim tile and deposit gold. Only fights workers
        Fighter,    // Sleep, eat, train and fight any enemy thing.
    };

    //! \brief The role of a creature in group fights.
    //! Blocker: holds the position and attacks the nearest enemy.
    //! Blitzer: storms the front line to reach the enemy support creatures.
    //! Flanker: prefers enemy support and ranged creatures and tries to get behind the enemy.
    //! Support: keeps its distance and supports with ranged attacks or healing.
    enum CombatClass
    {
        CombatBlocker = 1,
        CombatBlitzer,
        CombatFlanker,
        CombatSupport
    };

    //! \brief The single avoidance mechanism available to this creature type.
    enum class Avoidance
    {
        none,
        dodge,
        parry,
        block
    };

    //! \brief Creates a creature definition with backwards-compatible stat defaults.
    CreatureDefinition(
            const std::string&      className   = std::string(),
            CreatureJob             job         = Fighter,
            const std::string&      meshName    = std::string(),
            const std::string&      bedMeshName = std::string(),
            int                     bedDim1     = 1,
            int                     bedDim2     = 1,
            int                     bedPosX     = 1,
            int                     bedPosY     = 1,
            double                  bedOrientX  = 0,
            double                  bedOrientY  = -1,
            double                  sightRadius = 15.0,

            int                     maxGoldCarryable = 0,
            double                  digRate     = 10.0,
            double                  digRatePerLevel = 2.1,
            double                  claimRate   = 0.35,
            double                  claimRatePerLevel = 0.06,

            double                  minHP       = 1.0,
            double                  hpPerLevel  = 5.0,
            double                  hpHealPerTurn = 0.1,

            double                  wakefulnessLostPerTurn = 0.1,
            double                  hungerGrowthPerTurn = 0.1,

            double                  moveSpeedGround     = 1.0,
            double                  moveSpeedWater      = 0.0,
            double                  moveSpeedLava       = 0.0,
            double                  groundSpeedPerLevel = 0.02,
            double                  waterSpeedPerLevel  = 0.0,
            double                  lavaSpeedPerLevel   = 0.0,

            double                  physicalDefense     = 3.0,
            double                  physicalDefPerLevel = 0.2,
            double                  magicalDefense      = 1.5,
            double                  magicalDefPerLevel  = 0.1,
            double                  elementDefense      = 1.5,
            double                  elementDefPerLevel  = 0.1,
            int32_t                 fightIdleDist       = 1,
            int32_t                 feeBase             = 0,
            int32_t                 feePerLevel         = 0,
            int32_t                 sleepHeal           = 1.0,
            int32_t                 turnsStunDropped    = 0);

    //! \brief Copies a definition, including combat ratings and avoidance.
    CreatureDefinition(const CreatureDefinition& def);

    virtual ~CreatureDefinition();

    static CreatureJob creatureJobFromString(const std::string& s);
    static std::string creatureJobToString(CreatureJob c);
    //! \brief Converts the name of a combat class (as written in the configuration) to the enum value
    static CombatClass combatClassFromString(const std::string& s);
    //! \brief Converts a combat class to the name used in the configuration
    static std::string combatClassToString(CombatClass c);
    //! \brief Converts a configured avoidance name to its mechanism; unknown names use none.
    static Avoidance avoidanceFromString(const std::string& s);
    //! \brief Returns the configuration name of an avoidance mechanism.
    static std::string avoidanceToString(Avoidance avoidance);
    //! \brief Writes the differences between def1 and def2 in the given file. Note that def1 can be null. In
    //! this case, every parameters in def2 will be written. def2 cannot be null.
    static void writeCreatureDefinitionDiff(
        const CreatureDefinition* def1, const CreatureDefinition* def2, std::ostream& file, const std::map<std::string, CreatureDefinition*>& defMap);

    inline bool isWorker() const
    { return (mCreatureJob == Worker); }

    //! \brief True for undead creatures (Skeleton, Lich): they are never knocked out and leave no corpse or ghost.
    inline bool                 isUndead        () const    { return mUndead; }

    //! \brief The runners of the heart defence: the workers, plus the two cheap and
    //! fast scout creatures, the hornet and the goblin.
    inline bool isHeartDefenceRunner() const
    { return isWorker() || mClassName == "CaveHornet" || mClassName == "Goblin"; }

    //! \brief Sends the creature definition, including its combat model, to a client.
    friend ODPacket& operator <<(ODPacket& os, const CreatureDefinition *c);
    //! \brief Reads a creature definition and its combat model from a packet.
    friend ODPacket& operator >>(ODPacket& is, CreatureDefinition *c);

    //! \brief Loads a definition from the creature definition file sub [Creature][/Creature] part
    //! \returns A creature definition if valid, nullptr otherwise.
    static CreatureDefinition* load(std::stringstream& defFile, const std::map<std::string, CreatureDefinition*>& defMap);
    //! \brief Applies the configured fields to an existing creature definition.
    static bool update(CreatureDefinition* creatureDef, std::stringstream& defFile, const std::map<std::string, CreatureDefinition*>& defMap);

    inline CreatureJob          getCreatureJob  () const    { return mCreatureJob; }
    inline CombatClass          getCombatClass  () const    { return mCombatClass; }
    inline int32_t              getStealGold    () const    { return mStealGold; }
    //! \brief True for types that flee from visible ghosts.
    bool isAfraidOfGhosts() const { return mAfraidOfGhosts; }

    //! \brief True for creatures that are never scared by a Fear trap.
    inline bool                 isFearless      () const    { return mFearless; }
    //! \brief True for the champion definition (the creature the Summon champion spell calls).
    inline bool                 isChampion      () const    { return mChampion; }
    //! \brief Mana taken per second while a player possesses a creature of this definition (after the free period).
    inline double               getPossessManaCost () const { return mPossessManaCost; }
    //! \brief Own walk speed factor of a badly hurt creature of this type, negative when the global value applies
    inline double               getLowHealthWalkSpeedFactor () const    { return mLowHealthWalkSpeedFactor; }
    //! \brief Speed factor of the walk clips of this type on the client (1 = as authored), limited to 0.2 - 8.0
    inline double               getWalkClipRate () const    { return std::max(WALK_CLIP_RATE_MIN, std::min(WALK_CLIP_RATE_MAX, mWalkClipRate)); }
    //! \brief Speed factor of the WalkHurt clip of this type on the client, limited to 0.2 - 8.0. Without an own value
    //! (key WalkHurtClipRate not set) it is the walk clip rate
    inline double               getWalkHurtClipRate () const
    {
        if(mWalkHurtClipRate < 0.0)
            return getWalkClipRate();
        return std::max(WALK_CLIP_RATE_MIN, std::min(WALK_CLIP_RATE_MAX, mWalkHurtClipRate));
    }
    //! \brief Factor on every damage the skills of this type deal (Explosion, HailStorm, GasCloud, Grenade, GuidedBolt)
    inline double               getSkillDamageFactor () const   { return mSkillDamageFactor; }
    //! \brief Returns the start value of Strength (level 1, without equipment).
    inline double getStrength() const { return mStrength; }
    //! \brief Returns the start value of Dexterity.
    inline double getDexterity() const { return mDexterity; }
    //! \brief Returns the start value of Life.
    inline double getLife() const { return mLife; }
    //! \brief Returns the start value of Mana.
    inline double getMana() const { return mMana; }
    //! \brief Returns the Strength points gained per level.
    inline double getStrengthPerLevel() const { return mStrengthPerLevel; }
    //! \brief Returns the Dexterity points gained per level.
    inline double getDexterityPerLevel() const { return mDexterityPerLevel; }
    //! \brief Returns the Life points gained per level.
    inline double getLifePerLevel() const { return mLifePerLevel; }
    //! \brief Returns the Mana points gained per level.
    inline double getManaPerLevel() const { return mManaPerLevel; }
    //! \brief Returns the mana pool size per Mana point.
    inline double getManaPerPoint() const { return mManaPerPoint; }
    //! \brief Returns the critical chance bonus in percent of this type.
    inline double getCritChanceBonus() const { return mCritChanceBonus; }
    //! \brief Returns the skill group (blocker, blitzer, flanker, archer, caster, worker or none).
    inline const std::string& getSkillGroup() const { return mSkillGroup; }
    //! \brief Returns the skill family id (greenskin, dwarf, ... or none).
    inline const std::string& getSkillFamily() const { return mSkillFamily; }
    //! \brief Returns the id of the skill that has rank 1 from level 1 for free (or none).
    inline const std::string& getPreSkill() const { return mPreSkill; }
    //! \brief Returns the id of the tier 4 skill of this type (or none).
    inline const std::string& getTierFourSkill() const { return mTierFourSkill; }
    //! \brief Returns how fast the urge to use a toilet grows per turn (0 = the creature has no urge).
    inline double getUrgeGrowthPerTurn() const { return mUrgeGrowthPerTurn; }
    //! \brief Returns how much the creature minds dirt (0 = not at all, 1 = normal, 2 = twice as much).
    inline double getCleanliness() const { return mCleanliness; }
    //! \brief Returns the factor on all dirt the creature produces (1 = normal, 2 = twice as much).
    inline double getDirtFactor() const { return mDirtFactor; }
    //! \brief Returns how fast the thirst grows per turn (0 = the creature never gets thirsty).
    inline double getThirstGrowthPerTurn() const { return mThirstGrowthPerTurn; }
    //! \brief Returns true if the creature type can get thirsty (a type without hunger has no thirst either).
    inline bool hasThirst() const { return mThirstGrowthPerTurn > 0.0; }
    //! \brief Returns the seconds after its death the body of this type is removed (0 = the normal corpse rule applies).
    inline double getDeathVanishSeconds() const { return mDeathVanishSeconds; }
    inline const std::string&   getClassName    () const    { return mClassName; }

    inline const std::string&   getMeshName     () const    { return mMeshName; }

    inline const std::string&   getBedMeshName  () const    { return mBedMeshName; }
    inline int                  getBedDim1      () const    { return mBedDim1; }
    inline int                  getBedDim2      () const    { return mBedDim2; }
    inline int                  getBedPosX      () const    { return mBedPosX; }
    inline int                  getBedPosY      () const    { return mBedPosY; }
    inline double               getBedOrientX   () const    { return mBedOrientX; }
    inline double               getBedOrientY   () const    { return mBedOrientY; }

    inline int                  getSightRadius  () const    { return mSightRadius; }

    inline double               getClaimRate    () const    { return mClaimRate; }
    inline double               getClaimRatePerLevel() const{ return mClaimRatePerLevel; }
    inline int                  getMaxGoldCarryable () const    { return mMaxGoldCarryable; }
    inline double               getDigRate      () const    { return mDigRate; }
    inline double               getDigRatePerLevel() const  { return mDigRatePerLevel; }

    inline double               getMinHp        () const    { return mMinHP; }
    inline double               getHpPerLevel   () const    { return mHpPerLevel; }
    inline double               getHpHealPerTurn() const    { return mHpHealPerTurn; }

    inline double               getWakefulnessLostPerTurn() const{ return mWakefulnessLostPerTurn; }
    inline double               getHungerGrowthPerTurn() const { return mHungerGrowthPerTurn; }

    inline double               getMoveSpeedGround  () const    { return mMoveSpeedGround; }
    inline double               getMoveSpeedWater   () const    { return mMoveSpeedWater; }
    inline double               getMoveSpeedLava    () const    { return mMoveSpeedLava; }

    inline double               getGroundSpeedPerLevel() const  { return mGroundSpeedPerLevel; }
    inline double               getWaterSpeedPerLevel () const  { return mWaterSpeedPerLevel; }
    inline double               getLavaSpeedPerLevel  () const  { return mLavaSpeedPerLevel; }

    inline double               getPhysicalDefense() const      { return mPhysicalDefense; }
    inline double               getPhysicalDefPerLevel () const { return mPhysicalDefPerLevel; }
    inline double               getMagicalDefense  () const     { return mMagicalDefense; }
    inline double               getMagicalDefPerLevel () const  { return mMagicalDefPerLevel; }
    inline double               getElementDefense  () const     { return mElementDefense; }
    inline double               getElementDefPerLevel () const  { return mElementDefPerLevel; }

    //! \brief Tells whether the given skill is the first attack line of this type: the first Melee or MissileLaunch
    //! line of its skill list. The first MissileLaunch line of a type without bow is its spell attack.
    //! \param skill The skill to test.
    bool isFirstAttackSkill(const CreatureSkill* skill) const;

    //! \brief Returns the natural attack rating at level one.
    inline double getAttackRating() const { return mAttackRating; }
    //! \brief Returns the natural defense rating at level one.
    inline double getDefenseRating() const { return mDefenseRating; }
    //! \brief Returns this creature type's avoidance mechanism.
    inline Avoidance getAvoidance() const { return mAvoidance; }

    inline int32_t              getFightIdleDist() const        { return mFightIdleDist; }

    inline const std::string&   getWeaponSpawnL () const        { return mWeaponSpawnL; }
    inline const std::string&   getWeaponSpawnR () const        { return mWeaponSpawnR; }

    int32_t                     getFee (unsigned int level) const;

    inline double               getSleepHeal () const           { return mSleepHeal; }

    inline int32_t              getTurnsStunDropped () const    { return mTurnsStunDropped; }

    double                      getXPNeededWhenLevel(unsigned int level) const;

    //! \brief Returns the creature affinity. The returned vector is assumed to be
    //! sorted so that highest likeness is at first
    inline const std::vector<CreatureRoomAffinity>& getRoomAffinity() const
    { return mRoomAffinity; }

    inline const std::vector<const CreatureSkill*>& getCreatureSkills() const
    { return mCreatureSkills; }

    inline const std::vector<const CreatureBehaviour*>& getCreatureBehaviours() const
    { return mCreatureBehaviours; }

    inline const std::vector<const CreatureMood*>& getCreatureMoods() const
    { return mCreatureMoods; }

    const CreatureRoomAffinity& getRoomAffinity(RoomType roomType) const;

    inline const std::string& getMoodModifierName() const
    { return mMoodModifierName; }

    inline const std::string& getSoundFamilyPickup() const
    { return mSoundFamilyPickup; }
    inline const std::string& getSoundFamilyDrop() const
    { return mSoundFamilyDrop; }
    inline const std::string& getSoundFamilyAttack() const
    { return mSoundFamilyAttack; }
    inline const std::string& getSoundFamilyDie() const
    { return mSoundFamilyDie; }
    //! \brief Returns true if a bone pile of its own class is created where the body vanishes (DeathVanishPile).
    inline bool hasDeathVanishPile() const
    { return mDeathVanishPile; }
    //! \brief Returns the effect family fired when the creature dies (DeathVanishEffect), empty for none.
    inline const std::string& getDeathVanishEffect() const
    { return mDeathVanishEffect; }
    inline const std::string& getSoundFamilySlap() const
    { return mSoundFamilySlap; }

private:
    //! \brief The job of the creature (e.g. worker, fighter, ...)
    CreatureJob mCreatureJob;

    //! \brief The role in group fights (default blocker)
    CombatClass mCombatClass;
    //! brief Gold taken from one free gold pile by a thief, 0 for creatures that do not steal
    int32_t mStealGold;
    //! \brief True for creatures that are never scared by a Fear trap
    bool mFearless;
    //! \brief True for non-worker types that flee from visible ghosts.
    bool mAfraidOfGhosts;
    //! \brief True for the summoned champion: it cannot be hurt, possessed or turned, needs no fee and charges at enemies
    bool mChampion;
    //! \brief Mana taken per second while a player possesses a creature of this definition (after the free period)
    double mPossessManaCost;
    //! \brief True for undead creatures (Optional Undead, default 0): never knocked out, no corpse, no ghost
    bool mUndead;

    //! \brief Optional (LowHealthWalkSpeedFactor): negative means the value of global.cfg is used
    double mLowHealthWalkSpeedFactor;

    //! \brief Optional (WalkClipRate): speed factor of the Walk and CarryWalk clips on the client (and of WalkHurt when
    //! WalkHurtClipRate is not set), so that the feet of a creature type do not slide. Cosmetic: the move speed does not
    //! change. 1 when not set
    double mWalkClipRate;

    //! \brief Optional (WalkHurtClipRate): speed factor of the WalkHurt clip only, matching its own stride length.
    //! Negative when not set, then mWalkClipRate is used
    double mWalkHurtClipRate;

    //! \brief Optional (SkillDamageFactor): factor on every damage the skills of this type deal (Explosion, HailStorm,
    //! GasCloud, Grenade, GuidedBolt). 1 when not set
    double mSkillDamageFactor;

    //! \brief Optional (Strength): start value of Strength (level 1, without equipment). Default 20.0 when not set
    double mStrength;

    //! \brief Optional (Dexterity): start value of Dexterity. Default 20.0 when not set
    double mDexterity;

    //! \brief Optional (Life): start value of Life. Default 20.0 when not set
    double mLife;

    //! \brief Optional (Mana): start value of Mana. Default 20.0 when not set
    double mMana;

    //! \brief Optional (StrengthPerLevel): Strength points gained per level. Default 1.0 when not set
    double mStrengthPerLevel;

    //! \brief Optional (DexterityPerLevel): Dexterity points gained per level. Default 2.0 when not set
    double mDexterityPerLevel;

    //! \brief Optional (LifePerLevel): Life points gained per level. Default 1.0 when not set
    double mLifePerLevel;

    //! \brief Optional (ManaPerLevel): Mana points gained per level. Default 1.0 when not set
    double mManaPerLevel;

    //! \brief Optional (ManaPerPoint): mana pool size per Mana point. Default 1.5 when not set
    double mManaPerPoint;

    //! \brief Optional (CritChanceBonus): critical chance bonus in percent of this type. Default 0.0 when not set
    double mCritChanceBonus;

    //! \brief Optional (SkillGroup): skill group (blocker, blitzer, flanker, archer, caster, worker or none). Default "none" when not set
    std::string mSkillGroup;

    //! \brief Optional (SkillFamily): skill family id (greenskin, dwarf, ... or none). Default "none" when not set
    std::string mSkillFamily;

    //! \brief Optional (PreSkill): id of the skill that has rank 1 from level 1 for free (or none). Default "none" when not set
    std::string mPreSkill;

    //! \brief Optional (TierFourSkill): id of the tier 4 skill of this type (or none). Default "none" when not set
    std::string mTierFourSkill;

    //! \brief Optional (UrgeGrowth/Turn): how fast the urge to use a toilet grows per turn. Default 0.0 when not set
    double mUrgeGrowthPerTurn;

    //! \brief Optional (Cleanliness, 0 - 2): factor on the mood the dirt around the creature costs. Default 1.0 when not set
    double mCleanliness;

    //! \brief Optional (DirtFactor, 0 - 2): factor on all dirt the creature produces. Default 1.0 when not set
    double mDirtFactor;

    //! \brief Optional (ThirstGrowth/Turn): how fast the thirst grows per turn. Default 0.0 when not set
    double mThirstGrowthPerTurn;

    //! \brief Optional (DeathVanishSeconds): seconds after its death the body is removed. Default 0.0 = normal corpse rule
    double mDeathVanishSeconds;

    //! \brief The name of the creatures class
    std::string mClassName;

    //! \brief The name of the creature definition this one is based on (can be empty if no base class)
    std::string mBaseDefinition;

    //! \brief The name of the model file
    std::string mMeshName;

    //! \brief The name of the bed model file
    std::string mBedMeshName;

    //! \brief size of the bed (x)
    int mBedDim1;

    //! \brief size of the bed (y)
    int mBedDim2;

    //! \brief Position and orientation of the creature when it goes to sleep
    int mBedPosX;
    int mBedPosY;
    double mBedOrientX;
    double mBedOrientY;

    //! \brief The inner radius where the creature sees everything
    int mSightRadius;

    //! \brief Maximum gold amount a worker can carry before having to deposit it into a treasury
    int mMaxGoldCarryable;

    //! \brief Fullness removed per turn of digging
    double mDigRate;

    //! \brief How much dig rate is earned at each level up.
    double mDigRatePerLevel;

    //! \brief How quick a worker can claim a ground or wall tile.
    double mClaimRate;

    //! \brief How much claim rate is earned at each level up.
    double mClaimRatePerLevel;

    //! \brief The minimum HP the creature can ever have
    double mMinHP;

    //! \brief How much HP the creature gets per level up
    double mHpPerLevel;

    //! \brief How much HP are healed per turn.
    double mHpHealPerTurn;

    //! \brief How much wakefulness is lost per turn.
    double mWakefulnessLostPerTurn;

    //! \brief How fast hunger grows per turn.
    double mHungerGrowthPerTurn;

    //! \brief How fast the creature moves (0 -> The creature cannot go through corresponding tile)
    double mMoveSpeedGround;
    double mMoveSpeedWater;
    double mMoveSpeedLava;

    //! \brief how much speed is earn per level on each tile type.
    double mGroundSpeedPerLevel;
    double mWaterSpeedPerLevel;
    double mLavaSpeedPerLevel;

    //! \brief Defense stats (without equipment)
    double mPhysicalDefense;
    double mPhysicalDefPerLevel;
    double mMagicalDefense;
    double mMagicalDefPerLevel;
    double mElementDefense;
    double mElementDefPerLevel;

    //! \brief Natural accuracy and evasion ratings at level one, without equipment.
    double mAttackRating;
    double mDefenseRating;
    //! \brief The one avoidance mechanism configured for this creature type.
    Avoidance mAvoidance;

    //! \brief Distance from the nearest enemy creature that the creature will try to let when no skill can be used
    int32_t mFightIdleDist;

    //! \brief The base fee for this creature.
    int32_t mFeeBase;
    int32_t mFeePerLevel;

    //! \brief How many HP the creature will get per turn while sleeping
    double mSleepHeal;

    //! \brief Number of turns the creature will stay stunned after being dropped
    int32_t mTurnsStunDropped;

    //! \brief Weapons a creature should spawn with ("none" if no weapon)
    std::string mWeaponSpawnL;
    std::string mWeaponSpawnR;

    //! \brief The XP table, used to know how XP is needed to reach the next level.
    //! \note The creature starting at level 1, it can only change its level MAX_LEVEL - 1 times.
    std::vector<double> mXPTable;

    //! \brief Skills the creature can use
    std::vector<const CreatureSkill*> mCreatureSkills;

    //! \brief Creature specific behaviours
    std::vector<const CreatureBehaviour*> mCreatureBehaviours;

    //! \brief Creature specific mood modifiers
    std::vector<const CreatureMood*> mCreatureMoods;

    //! \brief The rooms the creature should choose according to availability
    std::vector<CreatureRoomAffinity> mRoomAffinity;

    //! \brief The rooms the creature mood modifier that should be used to compute
    //! creature mood
    std::string mMoodModifierName;

    //! \brief Sound family used by the creature
    std::string mSoundFamilyPickup;
    std::string mSoundFamilyDrop;
    std::string mSoundFamilyAttack;
    std::string mSoundFamilyDie;
    //! \brief Optional (DeathVanishPile): true if a pile of its own class is created where the body vanishes
    bool mDeathVanishPile;
    //! \brief Optional (DeathVanishEffect): effect family fired at the death of the creature, empty for none
    std::string mDeathVanishEffect;
    std::string mSoundFamilySlap;

    //! \brief Loads the creature XP values for the given definition.
    static void loadXPTable(std::stringstream& defFile, CreatureDefinition* creatureDef);

    //! \brief Loads the creature skills for the given definition.
    static void loadCreatureSkills(std::stringstream& defFile, CreatureDefinition* creatureDef);

    //! \brief Loads the creature specific behaviours for the given definition.
    static void loadCreatureBehaviours(std::stringstream& defFile, CreatureDefinition* creatureDef);

    //! \brief Loads the creature specific mood modifiers for the given definition.
    static void loadCreatureMoods(std::stringstream& defFile, CreatureDefinition* creatureDef);

    //! \brief Loads the creature room affinity for the given definition.
    static void loadRoomAffinity(std::stringstream& defFile, CreatureDefinition* creatureDef);
};

#endif // CREATUREDEFINITION_H
