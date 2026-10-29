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

#include "utils/ConfigManager.h"

#include "entities/CreatureDefinition.h"
#include "entities/ItemDefinition.h"
#include "entities/Tile.h"
#include "entities/Weapon.h"
#include "game/Skill.h"
#include "gamemap/TileSet.h"
#include "rooms/TreasurySettings.h"
#include "spawnconditions/SpawnCondition.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/NameAliases.h"

#include <boost/dynamic_bitset.hpp>
#include <OgreRoot.h>

#include <fstream>

const std::vector<std::string> EMPTY_SPAWNPOOL;
const std::string EMPTY_STRING;
const Ogre::ColourValue DEFAULT_SEAT_COLOURVALUE;
const std::string ConfigManager::DEFAULT_TILESET_NAME = "Default";

const std::string ConfigManager::DEFAULT_KEEPER_VOICE = "Default";

//! \brief Default extra mana per second for each claimed mana well tile; global.cfg can override it.
static const double DEFAULT_MANA_WELL_BONUS_PER_TILE = 10.0;

//! \brief Defaults used when global.cfg does not set the gold keys; the values in global.cfg are the real ones.
static const double DEFAULT_GOLD_PER_SEAM_TILE = 3000.0;
static const double DEFAULT_GOLD_PER_DIG_STEP = 25.0;
static const double DEFAULT_GEM_GOLD_PER_DIG_STEP = 16.67;
static const double DEFAULT_WORKER_CHEER_GOLD_SHARE = 0.35;

const double ConfigManager::AttackTurnSpeedMin = 90.0;
const double ConfigManager::AttackTurnSpeedMax = 1440.0;
const double ConfigManager::AttackTurnMaxDelayMin = 0.0;
const double ConfigManager::AttackTurnMaxDelayMax = 0.6;
const double ConfigManager::HitShareMin = 0.01;
const double ConfigManager::HitGlanceShareMax = 0.9;
const double ConfigManager::HitStrongShareMax = 1.0;
const double ConfigManager::ChanceMin = 0.0;
const double ConfigManager::ChanceMax = 100.0;
const double ConfigManager::ChancePerLevelMax = 10.0;

namespace
{
//! Default angular speed in degrees per second of the turn to the target before a blow
static const double DEFAULT_ATTACK_TURN_SPEED = 540.0;
//! Default most seconds the strike clip waits for the turn to the target
static const double DEFAULT_ATTACK_TURN_MAX_DELAY = 0.25;
//! Default share of the damage below which a blow counts as glancing
static const double DEFAULT_HIT_GLANCE_SHARE = 0.34;
//! Default share of the maximum health of the target from which a hit counts as strong
static const double DEFAULT_HIT_STRONG_SHARE = 0.15;

//! rief Compiled defaults of the [KeeperAILevels] section of ai.cfg: key and the values of the levels easy, medium,
//! normal, hard and hell. They equal the file and are used when it is missing.
static const char* const AI_LEVEL_DEFAULTS[][6] = {
    {"Rho", "12", "15", "20", "25.433", "30"},
    {"Pi", "0.4", "0.55", "0.75", "0.909", "0.99"},
    {"ScanPeriod", "120", "80", "45", "24.834", "10"},
    {"ClickShare", "0.3", "0.42", "0.6", "0.806", "1.0"},
    {"MistakeMultiplier", "4.555556", "3.444444", "2.333333", "1.944444", "0.555556"},
    {"EstimateNoise", "0.206", "0.164", "0.132", "0.106", "0.049"},
    {"TacticTemperature", "2.0", "0.7", "0.45", "0.4", "0.35"},
    {"AttackAdvantage", "-1.2", "-1.15", "-1.1", "-1.05", "-1.0"},
    {"FocusFire", "0.62", "0.698", "0.758", "0.807", "0.914"},
    {"RetreatThreshold", "0.603", "0.661", "0.706", "0.743", "0.823"},
    {"TunnelDetour", "0.215", "0.176", "0.146", "0.122", "0.068"},
    {"TacticPriorAllin", "0.34", "0.33", "0.32", "0.31", "0.3"},
    {"TacticPriorSingle", "0.58", "0.465", "0.35", "0.23", "0.12"},
    {"TacticPriorSplit", "0.04", "0.12", "0.2", "0.25", "0.3"},
    {"TacticPriorRaid", "0.01", "0.015", "0.02", "0.025", "0.03"},
    {"TacticPriorCounter", "0.03", "0.07", "0.11", "0.185", "0.25"},
    {"EnemyManaEstimate", "own", "own", "own", "own", "observed"},
};

//! rief Compiled defaults of the [KeeperAI] section of ai.cfg: key and value. They equal the file.
static const char* const AI_CONFIG_DEFAULTS[][2] = {
    {"AiPollSeconds", "1"},
    {"LookPeriod600", "600"},
    {"ClickBudgetPerMinute", "202.5"},
    {"ClickMinGap", "0.296"},
    {"ClickWindowSeconds", "60"},
    {"ActionLatencyMean", "0.72"},
    {"ActionLatencySd", "0.217"},
    {"PeriodicMinDelay", "5"},
    {"SymptomScanFactor", "0.5"},
    {"ReferenceScanPeriod", "60"},
    {"LookPeriod60", "60"},
    {"LookPeriod120", "120"},
    {"LookFactorBuild", "0.35"},
    {"LookFactorDormitory", "0.25"},
    {"LookFactorTrap", "0.5"},
    {"LookFactorSummon", "0.7"},
    {"LookFactorPlan", "2"},
    {"LookFactorScan", "1"},
    {"FirstPlanSeconds", "600"},
    {"FirstPlanJitterSeconds", "120"},
    {"FightOverSeconds", "10"},
    {"MistakeBaseRoutine", "0.02"},
    {"MistakeBaseRule", "0.09"},
    {"MistakeBaseComplex", "0.16"},
    {"MistakeBaseUnfamiliar", "0.26"},
    {"MistakeBaseRare", "0.55"},
    {"MistakeMin", "0.004"},
    {"MistakeMax", "0.85"},
    {"MistakeTilesDormitory", "9"},
    {"MistakeTilesHatchery", "9"},
    {"MistakeTrapWantDivisor", "2"},
    {"ReserveSlipStartMin", "0.2"},
    {"ReserveSlipStartMax", "0.9"},
    {"RestHpShareSlip", "0.3"},
    {"DigWorkersSlip", "1"},
    {"EarlyDigMultiplier", "0.3"},
    {"SlapMistakePauseSeconds", "120"},
    {"SlapMistakeBaseSeconds", "60"},
    {"SlapMistakeDelayFactor", "2"},
    {"SlapMistakeInterval1", "60"},
    {"SlapMistakeInterval2", "90"},
    {"SlapMistakeInterval3", "120"},
    {"SlapMistakeInterval4", "180"},
    {"SlapMistakeInterval5", "300"},
    {"MinerShareEarly", "0.6"},
    {"MinerShareLate", "0.35"},
    {"MinerShareSwitchMinute", "10"},
    {"MarkedTilesPerWorker", "1"},
    {"SummonManaFactor", "2"},
    {"SummonIncomeMin", "40"},
    {"SummonWorkersMax", "10"},
    {"WalletReserveWindow", "60"},
    {"CreateGoldManaReserve", "0.25"},
    {"GoldShareBuild", "0.85"},
    {"ManaShareSpend", "0.9"},
    {"GoldShareTreasury2", "0.7"},
    {"RoomGoldMargin", "300"},
    {"BedsSpare", "1"},
    {"DormitoryExtensionTiles", "25"},
    {"HatcheryExtensionMinTiles", "9"},
    {"HatcheryExtensionMaxTiles", "25"},
    {"HatcheryTilesPerCreature", "1"},
    {"TavernKeeperPaysFactor", "2"},
    {"MerchantMarginMin", "10"},
    {"MerchantMarginMax", "20"},
    {"LabModeDefault", "1"},
    {"InfirmaryDischargePercent", "100"},
    {"GhostResearchShare", "0.7"},
    {"GhostManaShare", "0.2"},
    {"ReviveManaFactor", "2"},
    {"BridgeMinShortcutTiles", "10"},
    {"PlacementPointsPerWallSpot", "50"},
    {"PlacementHandicapPerTileOffset", "20"},
    {"PlacementFirstSpotTiles", "3"},
    {"PlacementNextSpotTiles", "2"},
    {"ResearchQueueEntries", "2"},
    {"PossessLeaveHpShare", "0.3"},
    {"HealBelow", "0.5"},
    {"HealNeverAbove", "0.7"},
    {"HealCastChance", "0.4"},
    {"HasteFightSeconds", "20"},
    {"EyeCastIntervalMinutes", "5"},
    {"TremorMinTargets", "4"},
    {"InfernoReserveCasts", "2"},
    {"LightningManaReserve", "0.05"},
    {"SpellManaReserve", "0.05"},
    {"CastRecheckSeconds", "5"},
    {"MinRecastSeconds", "3"},
    {"CallToWarMinCreatures", "3"},
    {"TrapTilesPerEntrance", "3"},
    {"GasEveryNthTile", "3"},
    {"TrapGoldMargin", "300"},
    {"CannonManaPerTile", "2500"},
    {"SpikeBehindDoorMinTiles", "3"},
    {"SpikeBehindDoorMaxTiles", "6"},
    {"CannonMaxDoorDistance", "15"},
    {"BoulderCorridorMinTiles", "8"},
    {"AlarmDistanceTiles", "6"},
    {"MaxWaitingForCraft", "2"},
    {"TrapPlanMinRooms", "9"},
    {"PrisonWaitMinutes", "5"},
    {"ExploreTunnelsPerDirection", "1"},
    {"Leveltilesdig", "2"},
    {"HeartDefenceAreaTiles", "5"},
    {"AttackMinMinute", "20"},
    {"AttackMinFighters", "5"},
    {"AttackMinTrapTiles", "2"},
    {"AttackDiggers", "3"},
    {"EarlyDigMinute", "12"},
    {"EarlyDigMinFighters", "3"},
    {"DiggerCapShare", "0.5"},
    {"DigActions", "4"},
    {"DetourSigma", "0.5"},
    {"TunnelProbeSeconds", "5"},
    {"EnemyOutMinCreatures", "3"},
    {"SecondWaveMinutes", "1"},
    {"HeartPossessBelow", "0.6"},
    {"RestHpShare", "0.8"},
    {"AttackMinReady", "3"},
    {"RestSecondsAfterAssault", "45"},
    {"RaidGoldThreshold", "8000"},
    {"RetreatCheckSeconds", "5"},
    {"ContactTimeoutSeconds", "1800"},
    {"ScoutCameraActions", "2"},
    {"ReloadRetrySeconds", "30"},
    {"PoorDefenceShuffleChance", "0.5"},
    {"ChampionExtraSeconds", "30"},
    {"GroupShareMain", "0.55"},
    {"GroupShareRaid", "0.3"},
    {"GroupShareSingle", "0.7"},
    {"GroupShareRaidTactic", "0.4"},
    {"CounterArmyShare", "0.85"},
    {"RaidTargetsSplit", "2"},
    {"RaidTargetsRaid", "3"},
    {"RawHitFactor", "0.9"},
    {"StrengthRatioCap", "3"},
    {"ScorePenaltyBase", "0.6"},
    {"ScorePenaltyAllin", "1.0"},
    {"ScorePenaltySingle", "0.49"},
    {"ScorePenaltySplit", "0.72"},
    {"ScorePenaltyRaid", "0.16"},
    {"ScorePenaltyCounter", "0.72"},
    {"ScorePenaltyCounterFactor", "0.3"},
    {"BonusSplit", "0.2"},
    {"BonusRaidBase", "1.0"},
    {"BonusRaidGold", "0.4"},
    {"BonusRaidGoldDivisor", "3000"},
    {"BonusCounter", "0.7"},
    {"WaitWeight", "1.0"},
    {"TacticExponentClamp", "30"},
    {"AdvFloor", "-4"},
    {"AdvHpFloorShare", "0.1"},
    {"EnemyHpFloorShare", "0.05"},
    {"FightEstimateDamageShare", "0.88"},
    {"EstimateSetupSeconds", "5"},
    {"EstimateRoomTiles", "16"},
    {"EstimateTileHp", "10"},
    {"HeartHealMargin", "1.0"},
    {"HeartBreakFallbackSeconds", "600"},
    {"DoorTimeCap", "60"},
    {"PotentialCastsMax", "40"},
    {"PotentialCastPeriod", "4.5"},
    {"PotentialCastsBase", "1"},
    {"SpellPotentialEff", "0.7"},
    {"TrapEff", "0.45"},
    {"TrapPassSeconds", "4"},
    {"TrapTargetsSpike", "1"},
    {"TrapTargetsCannon", "1"},
    {"TrapTargetsBoulder", "2"},
    {"TrapTargetsGas", "2"},
    {"TrapTargetsLightning", "1"},
    {"TrapTargetsFireburst", "2"},
    {"SpellTargetsLightning", "1"},
    {"SpellTargetsExplosion", "1"},
    {"SpellTargetsTremor", "4"},
    {"SpellTargetsInferno", "2"},
    {"EstimateNoSightingNoise", "0.6"},
    {"EstimateGoldDefault", "5000"},
    {"EstimateReadyFlipRate", "0.08"},
};

//! rief Compiled defaults of the [Actions] section of ai.cfg: action, clicks and seconds. They equal the file.
static const char* const AI_ACTION_DEFAULTS[][3] = {
    {"slap", "1", "1.30"},
    {"pickup", "1", "1.30"},
    {"drop", "1", "1.30"},
    {"dig", "1", "2.40"},
    {"build", "3", "5.00"},
    {"spell", "3", "3.90"},
    {"trap", "3", "3.90"},
    {"setting", "3", "3.90"},
    {"research", "5", "6.50"},
    {"research_auto", "2", "2.60"},
    {"camera", "1", "0.60"},
    {"minimap", "1", "1.30"},
    {"sell", "2", "2.60"},
    {"possess", "3", "3.90"},
    {"think", "0", "1.35"},
};

//! rief Compiled defaults of the [RowClasses] section of ai.cfg: decision id, mistake class and multiplier. They equal the file.
static const char* const AI_ROW_CLASS_DEFAULTS[][3] = {
    {"A01", "rule", "1"},
    {"A02", "rule", "1"},
    {"A03", "routine", "1"},
    {"A04", "rule", "1"},
    {"A05", "rule", "1"},
    {"A06", "routine", "1"},
    {"A07", "routine", "1"},
    {"A08", "complex", "1"},
    {"A09", "rule", "1"},
    {"B01", "rule", "1"},
    {"B02", "rule", "1"},
    {"B03", "rule", "1"},
    {"B04", "rule", "1"},
    {"B05", "rule", "1"},
    {"B06", "rule", "1"},
    {"B07", "rule", "1"},
    {"B08", "unfamiliar", "1"},
    {"B09", "unfamiliar", "1"},
    {"B10", "rule", "1"},
    {"B11", "unfamiliar", "1"},
    {"B12", "rule", "1"},
    {"B13", "rule", "1"},
    {"B14", "rule", "1"},
    {"B15", "unfamiliar", "1"},
    {"B16", "rule", "1"},
    {"B17", "unfamiliar", "1"},
    {"B18", "unfamiliar", "1"},
    {"B19", "rule", "1"},
    {"B20", "rare", "1"},
    {"B21", "rule", "1"},
    {"B22", "rule", "1"},
    {"B23", "complex", "1"},
    {"B24", "unfamiliar", "0.8"},
    {"C01", "rule", "1"},
    {"C02", "routine", "1.5"},
    {"C03", "complex", "1"},
    {"C04", "complex", "1"},
    {"C05", "rule", "1"},
    {"C06", "complex", "1"},
    {"D01", "rule", "1"},
    {"D02", "rule", "1"},
    {"D03", "rule", "1"},
    {"D04", "rule", "0.8"},
    {"D05", "complex", "1"},
    {"D06", "rule", "1"},
    {"D07", "rule", "1"},
    {"D08", "rule", "1"},
    {"D09", "rule", "1"},
    {"D10", "rule", "1"},
    {"D11", "rule", "1"},
    {"E01", "routine", "1"},
    {"E02", "complex", "1"},
    {"E03", "complex", "1"},
    {"E04", "rule", "1"},
    {"E05", "complex", "1"},
    {"E06", "complex", "1"},
    {"E07", "complex", "1"},
    {"E08", "complex", "1"},
    {"E09", "complex", "1"},
    {"E10", "complex", "1"},
    {"E11", "complex", "1"},
    {"E12", "complex", "1"},
    {"E13", "rule", "1"},
    {"E14", "rare", "1"},
    {"E15", "complex", "1"},
    {"E16", "complex", "1"},
    {"E17", "rare", "1"},
    {"E18", "rare", "1"},
    {"E19", "complex", "1"},
    {"F01", "rule", "1"},
    {"F02", "rule", "1"},
    {"F03", "rule", "1"},
    {"F04", "rule", "1"},
    {"F05", "complex", "1"},
    {"F06", "complex", "1"},
    {"F07", "complex", "1"},
    {"F08", "complex", "1"},
    {"F09", "rule", "1"},
    {"F10", "complex", "1"},
    {"F11", "complex", "1"},
    {"F12", "rule", "1"},
    {"F13", "rule", "1"},
    {"F14", "complex", "1"},
    {"F15", "rule", "1"},
    {"G01", "rule", "1"},
    {"G02", "unfamiliar", "1"},
    {"G03", "rule", "1"},
    {"G04", "rule", "1"},
    {"H01", "rule", "1"},
    {"H02", "rule", "1"},
    {"H03", "rule", "1"},
    {"I01", "rule", "1"},
    {"I02", "complex", "1"},
    {"I03", "rule", "1"},
    {"I04", "complex", "1"},
    {"I05", "rule", "1"},
    {"I06", "routine", "1"},
    {"J01", "routine", "1"},
    {"J02", "rule", "1"},
    {"J03", "complex", "1"},
    {"J04", "complex", "1"},
    {"J05", "complex", "1"},
    {"J06", "complex", "1"},
    {"J07", "complex", "1"},
    {"J08", "rule", "1"},
    {"K01", "complex", "1"},
    {"K02", "complex", "1"},
    {"K03", "complex", "1"},
    {"K04", "complex", "1"},
    {"K05", "rule", "1"},
    {"K06", "complex", "1"},
    {"K07", "complex", "1"},
    {"K08", "complex", "1"},
    {"K09", "rule", "1"},
    {"K10", "rule", "1"},
    {"L01", "routine", "0"},
    {"L02", "routine", "0"},
    {"L03", "routine", "0"},
    {"L04", "routine", "0"},
    {"E20", "rule", "1"},
    {"H04", "rule", "1"},
};

//! \brief The field of a keeper AI level that a key of the [KeeperAILevels] section of ai.cfg sets.
//! \return The field, or nullptr when the key is not a number key of the section (EnemyManaEstimate is a word)
double* aiLevelField(AiSettings& settings, const std::string& key)
{
    if(key == "Rho") return &settings.rho;
    if(key == "Pi") return &settings.pi;
    if(key == "ScanPeriod") return &settings.scanPeriod;
    if(key == "ClickShare") return &settings.clickShare;
    if(key == "MistakeMultiplier") return &settings.mistakeMultiplier;
    if(key == "EstimateNoise") return &settings.estimateNoise;
    if(key == "TacticTemperature") return &settings.tacticTemperature;
    if(key == "AttackAdvantage") return &settings.attackAdvantage;
    if(key == "FocusFire") return &settings.focusFire;
    if(key == "RetreatThreshold") return &settings.retreatThreshold;
    if(key == "TunnelDetour") return &settings.tunnelDetour;
    if(key == "TacticPriorAllin") return &settings.tacticPriors[0];
    if(key == "TacticPriorSingle") return &settings.tacticPriors[1];
    if(key == "TacticPriorSplit") return &settings.tacticPriors[2];
    if(key == "TacticPriorRaid") return &settings.tacticPriors[3];
    if(key == "TacticPriorCounter") return &settings.tacticPriors[4];
    return nullptr;
}

//! \brief Tells whether a word is one of the mistake classes of the [RowClasses] section of ai.cfg.
bool isAiMistakeClass(const std::string& word)
{
    return (word == "routine") || (word == "rule") || (word == "complex") || (word == "unfamiliar") || (word == "rare");
}
}

const std::string ConfigManager::DefaultWorkerCreatureDefinition = "DefaultWorker";

template<> ConfigManager* Ogre::Singleton<ConfigManager>::msSingleton = nullptr;

//! \brief Loads game settings, including the global dodge and shield block defaults.
ConfigManager::ConfigManager(const std::string& configPath, const std::string& userConfigPath,
        const std::string& soundPath) :
    mFilenameItems("items.cfg"),
    mFilenamePotions("potions.cfg"),
    mConfigPath(configPath),
    mFilenameCreatureSkills("creatureSkills.cfg"),
    mNetworkPort(0),
    mClientConnectionTimeout(5000),
    mBaseSpawnPoint(10),
    mCreatureDeathCounter(10),
    mGhostLifetimeSeconds(0.0),
    mGhostFloatSpeed(0.0),
    mGhostWanderRadius(0.0),
    mGhostAiGoldPerResearchPoint(0.0),
    mGhostAiGoldPerXp(0.0),
    mSoulCrystalPrice(0.0),
    mSoulCrystalBreakBelow(0.0),
    mSoulCrystalNormalXpPerSecond(0.0),
    mSoulCrystalHeroRareStart(0.0),
    mSoulCrystalHeroRareEnd(0.0),
    mCorpseLieSeconds(0.0),
    mCorpseDecaySeconds(0.0),
    mMaxCreaturesPerSeatAbsolute(30),
    mMaxCreaturesPerSeatDefault(10),
    mCreaturesPerPortal(5),
    mCreatureBaseMood(1000),
    mCreatureMoodHappy(1200),
    mCreatureMoodUpset(0),
    mCreatureMoodAngry(-1000),
    mCreatureMoodFurious(-2000),
    mSlapDamagePercent(15),
    mLavaDamagePerSecond(50),
    mSlapEffectDuration(15),
    mTiredWakefulness(20.0),
    mTiredWalkSpeedFactor(0.8),
    mLowHealthWalkSpeedFactor(0.7),
    mCreatureLevelGrowthMax(0.10),
    mCreatureDamageGrowth(0.221),
    mCreatureDamageExponent(1.167),
    mCreatureHpGrowthPerLevel(0.018),
    mCooldownReductionPerLevel(0.0),
    mCritChancePerDexterity(0.2),
    mCritChancePerLevel(0.3),
    mCritDamageMultiplier(2.0),
    mManaRefillSeconds(120.0),
    mManaPerCasterShot(2.5),
    mManaPerDragonSecondShot(5.0),
    mSkillPointFirstLevel(10),
    mSkillRanksPerSkill(5),
    mSkillTemplateDeviationPercent(25.0),
    mSkillRespecChickens(2),
    mSkillRespecWindowSeconds(60.0),
    mSkillSpellReferenceMinHP(86.1),
    mSkillHealSelfBelow(0.6),
    mSkillHealAllyBelow(0.6),
    mSkillHealAreaBelow(0.7),
    mSkillHealAreaMinCreatures(2),
    mGoldCarryPerStrength(0.01),
    mLowHealthWalkThresholdPercent(50.0),
    mHeartHealthStages(5),
    mHeartHealthStageEvents(true),
    mHitEvents(true),
    mHitGlanceShare(DEFAULT_HIT_GLANCE_SHARE),
    mHitStrongShare(DEFAULT_HIT_STRONG_SHARE),
    mAttackTurnEvents(true),
    mAttackTurnSpeed(DEFAULT_ATTACK_TURN_SPEED),
    mAttackTurnMaxDelay(DEFAULT_ATTACK_TURN_MAX_DELAY),
    mMeleeDodgeParry(true),
    mDodgeBase(10.5),
    mDodgePerLevel(0.0),
    mDodgeMax(15.0),
    mParryBase(10.5),
    mParryPerLevel(0.0),
    mParryMax(15.0),
    mShieldBlockBase(21.0),
    mShieldBlockPerLevel(0.0),
    mShieldBlockMax(25.0),
    mTimePayDay(300),
    mNbTurnsFuriousMax(120),
    mMaxManaPerSeat(200000.0),
    mManaWellBonusPerTile(DEFAULT_MANA_WELL_BONUS_PER_TILE),
    mBedStepMaxHeight(0.09),
    mClaimingWallPenalty(0.8),
    mGoldPerSeamTile(DEFAULT_GOLD_PER_SEAM_TILE),
    mGoldPerDigStep(DEFAULT_GOLD_PER_DIG_STEP),
    mGemGoldPerDigStep(DEFAULT_GEM_GOLD_PER_DIG_STEP),
    mWorkerCheerGoldShare(DEFAULT_WORKER_CHEER_GOLD_SHARE),
    mDigCoefClaimedWall(0.5),
    mNbTurnsKoCreatureAttacked(10),
    mCreatureDefinitionDefaultWorker(nullptr),
    mNbWorkersDigSameFaceTile(3),
    mNbWorkersClaimSameTile(1)
{
    // TODO: it might be better to go through the creature definitions and try to pickup the first worker we can find
    mCreatureDefinitionDefaultWorker = new CreatureDefinition(DefaultWorkerCreatureDefinition,
        CreatureDefinition::CreatureJob::Worker, "Kobold.mesh");
    if(!loadGlobalConfig(configPath))
    {
        OD_LOG_ERR("Couldn't read loadCreatureDefinitions");
        exit(1);
    }
    std::string fileName = configPath + mFilenameCreatureDefinition;
    if(!loadCreatureDefinitions(fileName))
    {
        OD_LOG_ERR("Couldn't read loadCreatureDefinitions");
        exit(1);
    }
    fileName = configPath + mFilenameEquipmentDefinition;
    if(!loadEquipements(fileName))
    {
        OD_LOG_ERR("Couldn't read loadEquipements");
        exit(1);
    }
    if(!loadItems(configPath + mFilenameItems) || !loadPotions(configPath + mFilenamePotions))
    {
        OD_LOG_ERR("Couldn't read item and potion definitions");
        exit(1);
    }
    fileName = configPath + mFilenameSpawnConditions;
    if(!loadSpawnConditions(fileName))
    {
        OD_LOG_ERR("Couldn't read loadSpawnConditions");
        exit(1);
    }
    fileName = configPath + mFilenameFactions;
    if(!loadFactions(fileName))
    {
        OD_LOG_ERR("Couldn't read loadFactions");
        exit(1);
    }
    fileName = configPath + mFilenameRooms;
    if(!loadRooms(fileName))
    {
        OD_LOG_ERR("Couldn't read loadRooms");
        exit(1);
    }
    fileName = configPath + mFilenameTraps;
    if(!loadTraps(fileName))
    {
        OD_LOG_ERR("Couldn't read loadTraps");
        exit(1);
    }
    fileName = configPath + mFilenameSpells;
    if(!loadSpellConfig(fileName))
    {
        OD_LOG_ERR("Couldn't read loadSpellConfig");
        exit(1);
    }
    fileName = configPath + mFilenameSkills;
    if(!loadSkills(fileName))
    {
        OD_LOG_ERR("Couldn't read loadSkills");
        exit(1);
    }
    fileName = configPath + mFilenameCreatureSkills;
    if(!loadCreatureSkills(fileName))
    {
        OD_LOG_ERR("Couldn't read loadCreatureSkills");
        exit(1);
    }
    fileName = configPath + mFilenameTilesets;
    if(!loadTilesets(fileName))
    {
        OD_LOG_ERR("Couldn't read loadTilesets");
        exit(1);
    }
    fileName = configPath + mFilenameEditor;    
    if(!loadEditorSettings(fileName))
    {
        OD_LOG_ERR("Couldn't read loadEditorSettings");
        exit(1);
    }

    loadRelationships(configPath + "relationships.cfg");
    loadTreasury(configPath + "treasury.cfg");
    if(!loadAiConfig(configPath + "ai.cfg"))
    {
        OD_LOG_ERR("Couldn't read loadAiConfig");
        exit(1);
    }

    // Reserve space in any case.
    mUserConfig.resize(Config::Ctg::TOTAL);

    if (!userConfigPath.empty())
        loadUserConfig(userConfigPath);

    loadKeeperVoices(soundPath);
}

//! \brief Releases all configuration-owned definitions, including item lines.
ConfigManager::~ConfigManager()
{
    for(std::pair<const std::string, CreatureDefinition*> pair : mCreatureDefs)
    {
        delete pair.second;
    }

    if(mCreatureDefinitionDefaultWorker != nullptr)
        delete mCreatureDefinitionDefaultWorker;

    for(const Weapon* def : mWeapons)
    {
        delete def;
    }
    mWeapons.clear();

    for(const ItemDefinition* definition : mItems)
        delete definition;
    mItems.clear();

    for(std::pair<const CreatureDefinition*, std::vector<const SpawnCondition*>> p : mCreatureSpawnConditions)
    {
        for(const SpawnCondition* spawnCondition : p.second)
        {
            delete spawnCondition;
        }
    }
    mCreatureSpawnConditions.clear();

    for(std::pair<const std::string, const TileSet*> p : mTileSets)
    {
        delete p.second;
    }
    mTileSets.clear();
    for(std::pair<const std::string, const HighMap*> p : mHighMaps)
    {
        delete p.second;
    }
    mHighMaps.clear();
    recentlyUsedLevels.clear();
}

//! \brief Reads global settings and the numeric item-system rule sections.
bool ConfigManager::loadGlobalConfig(const std::string& configPath)
{
    std::stringstream configFile;
    std::string fileName = configPath + "global.cfg";
    if(!Helper::readFile(fileName, configFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    uint32_t paramsOk = 0;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == "[SeatColors]")
        {
            if(!loadGlobalConfigSeatColors(configFile))
                break;

            paramsOk |= 1;
            continue;
        }

        if(nextParam == "[ConfigFiles]")
        {
            if(!loadGlobalConfigDefinitionFiles(configFile))
                break;

            paramsOk |= 2;
            continue;
        }

        if(nextParam == "[GameConfig]")
        {
            if(!loadGlobalGameConfig(configFile))
                break;

            paramsOk |= 4;
            continue;
        }
        if(nextParam == "[ItemDrops]" || nextParam == "[ItemRating]" || nextParam == "[Potions]")
        {
            const std::string section = nextParam.substr(1, nextParam.size() - 2);
            if(!loadItemSettings(configFile, section))
                return false;
        }

        if(nextParam == "[Dirt]")
        {
            // The dirt block is optional: without it every dirt key reads as 0
            if(!loadGlobalDirtConfig(configFile))
                break;

            continue;
        }

        if(nextParam == "[Tavern]")
        {
            // The tavern block is optional: without it every tavern key reads as 0
            if(!loadGlobalTavernConfig(configFile))
                break;

            continue;
        }
    }

    if(paramsOk != 0x07)
    {
        OD_LOG_ERR("Not enough parameters for config file paramsOk=" + Helper::toString(paramsOk));
        return false;
    }

    return true;
}

//! \brief Reads the [Dirt] block of global.cfg: one "key value" pair per line up to [/Dirt].
bool ConfigManager::loadGlobalDirtConfig(std::stringstream& configFile)
{
    std::string nextParam;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == "[/Dirt]")
            return true;

        std::string value;
        if(!(configFile >> value))
            break;

        mDirtConfig[nextParam] = Helper::toDouble(value);
    }

    OD_LOG_ERR("Missing [/Dirt] in global.cfg");
    return false;
}

//! \brief Reads "key value" pairs up to a closing tag into a map of numbers.
//! \param configFile The stream of global.cfg, positioned after the opening tag.
//! \param closeTag The tag that ends the block.
//! \param values Receives the pairs.
//! \return False if the stream ends before the closing tag.
static bool readGlobalNumberBlock(std::stringstream& configFile, const std::string& closeTag,
    std::map<std::string, double>& values)
{
    std::string nextParam;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == closeTag)
            return true;

        std::string value;
        if(!(configFile >> value))
            break;

        values[nextParam] = Helper::toDouble(value);
    }

    return false;
}

//! \brief Reads the [Tavern] block of global.cfg: one "key value" pair per line up to [/Tavern].
bool ConfigManager::loadGlobalTavernConfig(std::stringstream& configFile)
{
    if(readGlobalNumberBlock(configFile, "[/Tavern]", mTavernConfig))
        return true;

    OD_LOG_ERR("Missing [/Tavern] in global.cfg");
    return false;
}

//! \brief Returns the value of a [Tavern] key of global.cfg, 0 (and an error in the log) when the key is unknown.
double ConfigManager::getTavernConfigDouble(const std::string& param) const
{
    std::map<std::string, double>::const_iterator it = mTavernConfig.find(param);
    if(it == mTavernConfig.end())
    {
        OD_LOG_ERR("Unknown tavern parameter param=" + param);
        return 0.0;
    }

    return it->second;
}

//! \brief Returns the value of a [Dirt] key of global.cfg, 0 (and an error in the log) when the key is unknown.
double ConfigManager::getDirtConfigDouble(const std::string& param) const
{
    std::map<std::string, double>::const_iterator it = mDirtConfig.find(param);
    if(it == mDirtConfig.end())
    {
        OD_LOG_ERR("Unknown dirt parameter param=" + param);
        return 0.0;
    }

    return it->second;
}

//! \brief Reads configured data filenames without changing existing required-file flags.
bool ConfigManager::loadGlobalConfigDefinitionFiles(std::stringstream& configFile)
{
    std::string nextParam;
    uint32_t filesOk = 0;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == "[/ConfigFiles]")
            break;

        if(nextParam != "[ConfigFile]")
        {
            OD_LOG_ERR("Wrong parameter read nextParam=" + nextParam);
            return false;
        }

        uint32_t paramsOk = 0;
        std::string type;
        std::string fileName;
        while(configFile.good())
        {
            if(!(configFile >> nextParam))
                break;

            if(nextParam == "[/ConfigFile]")
            {
                break;
            }

            if(nextParam == "Type")
            {
                configFile >> type;
                paramsOk |= 0x01;
                continue;
            }

            if(nextParam == "Filename")
            {
                configFile >> fileName;
                paramsOk |= 0x02;
                continue;
            }
        }

        if(paramsOk != 0x03)
        {
            OD_LOG_ERR("Missing parameters paramsOk=" + Helper::toString(paramsOk));
            return false;
        }

        if(type == "Creatures")
        {
            mFilenameCreatureDefinition = fileName;
            filesOk |= 1;
        }
        else if(type == "Equipments")
        {
            mFilenameEquipmentDefinition = fileName;
            filesOk |= 2;
        }
        else if(type == "SpawnConditions")
        {
            mFilenameSpawnConditions = fileName;
            filesOk |= 4;
        }
        else if(type == "Items")
            mFilenameItems = fileName;
        else if(type == "Potions")
            mFilenamePotions = fileName;
        else if(type == "Factions")
        {
            mFilenameFactions = fileName;
            filesOk |= 8;
        }
        else if(type == "Rooms")
        {
            mFilenameRooms = fileName;
            filesOk |= 0x10;
        }
        else if(type == "Traps")
        {
            mFilenameTraps = fileName;
            filesOk |= 0x20;
        }
        else if(type == "Spells")
        {
            mFilenameSpells = fileName;
            filesOk |= 0x40;
        }
        else if(type == "Skills")
        {
            mFilenameSkills = fileName;
            filesOk |= 0x080;
        }
        else if(type == "CreatureSkills")
        {
            // Optional entry: without it the default file name is used
            mFilenameCreatureSkills = fileName;
        }
        else if(type == "Tilesets")
        {
            mFilenameTilesets = fileName;
            filesOk |= 0x100;
        }
        else if(type == "EditorSettings")
        {
            mFilenameEditor = fileName;
            filesOk |= 0x200;
        }    
    }

    if(filesOk != 0x3FF)
    {
        OD_LOG_ERR("Missing parameter file filesOk=" + Helper::toString(filesOk));
        return false;
    }

    return true;
}

bool ConfigManager::loadGlobalConfigSeatColors(std::stringstream& configFile)
{
    std::string nextParam;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == "[/SeatColors]")
            break;

        if(nextParam != "[SeatColor]")
        {
            OD_LOG_ERR("Wrong parameter read nextParam=" + nextParam);
            return false;
        }

        uint32_t paramsOk = 0;
        std::string id;
        Ogre::ColourValue colourValue;
        while(configFile.good())
        {
            if(!(configFile >> nextParam))
                break;

            if(nextParam == "[/SeatColor]")
            {
                break;
            }

            if(nextParam == "ID")
            {
                configFile >> id;
                paramsOk |= 0x01;
                continue;
            }

            if(nextParam == "ColorR")
            {
                configFile >> nextParam;
                float v = Helper::toFloat(nextParam);
                if(v < 0.0 || v > 1.0)
                {
                    OD_LOG_ERR("Wrong parameter read nextParam=" + nextParam);
                    return false;
                }
                colourValue.r = v;
                paramsOk |= 0x02;
                continue;
            }

            if(nextParam == "ColorG")
            {
                configFile >> nextParam;
		float v = Helper::toFloat(nextParam);
                if(v < 0.0 || v > 1.0)
                {
                    OD_LOG_ERR("Wrong parameter read nextParam=" + nextParam);
                    return false;
                }
                colourValue.g = v;
                paramsOk |= 0x04;
                continue;
            }

            if(nextParam == "ColorB")
            {
                configFile >> nextParam;
                float v = Helper::toFloat(nextParam);
                if(v < 0.0 || v > 1.0)
                {
                    OD_LOG_ERR("Wrong parameter read nextParam=" + nextParam);
                    return false;
                }
                colourValue.b = v;
                paramsOk |= 0x08;
                continue;
            }
        }

        if(paramsOk != 0x0F)
        {
            OD_LOG_ERR("Missing parameters paramsOk=" + Helper::toString(paramsOk));
            return false;
        }

        mSeatColors[id] = colourValue;
    }

    return true;
}

//! \brief Loads global game values and the settings of each creature avoidance kind.
bool ConfigManager::loadGlobalGameConfig(std::stringstream& configFile)
{
    std::string nextParam;
    uint32_t paramsOk = 0;
    while(configFile.good())
    {
        if(!(configFile >> nextParam))
            break;

        if(nextParam == "[/GameConfig]")
            break;

        nextParam = NameAliases::resolve(nextParam);

        if(nextParam == "NetworkPort")
        {
            configFile >> nextParam;
            mNetworkPort = Helper::toUInt32(nextParam);
            paramsOk |= 1;
        }

        if(nextParam == "ClientConnectionTimeout")
        {
            configFile >> nextParam;
            mClientConnectionTimeout = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "GhostLifetimeSeconds")
        {
            configFile >> nextParam;
            mGhostLifetimeSeconds = Helper::toDouble(nextParam);
        }
        if(nextParam == "GhostFloatSpeed")
        {
            configFile >> nextParam;
            mGhostFloatSpeed = Helper::toDouble(nextParam);
        }
        if(nextParam == "GhostWanderRadius")
        {
            configFile >> nextParam;
            mGhostWanderRadius = Helper::toDouble(nextParam);
        }
        if(nextParam == "GhostAiGoldPerResearchPoint")
        {
            configFile >> nextParam;
            mGhostAiGoldPerResearchPoint = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "GhostAiGoldPerXp")
        {
            configFile >> nextParam;
            mGhostAiGoldPerXp = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "SoulCrystalPrice")
        {
            configFile >> nextParam;
            mSoulCrystalPrice = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "SoulCrystalBreakBelow")
        {
            configFile >> nextParam;
            mSoulCrystalBreakBelow = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "SoulCrystalNormalXpPerSecond")
        {
            configFile >> nextParam;
            mSoulCrystalNormalXpPerSecond = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "SoulCrystalHeroRareStart")
        {
            configFile >> nextParam;
            mSoulCrystalHeroRareStart = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "SoulCrystalHeroRareEnd")
        {
            configFile >> nextParam;
            mSoulCrystalHeroRareEnd = Helper::toDouble(nextParam);
            continue;
        }
        if(nextParam == "CorpseLieSeconds")
        {
            configFile >> nextParam;
            mCorpseLieSeconds = Helper::toDouble(nextParam);
        }
        if(nextParam == "CorpseDecaySeconds")
        {
            configFile >> nextParam;
            mCorpseDecaySeconds = Helper::toDouble(nextParam);
        }

        if(nextParam == "CreatureDeathCounter")
        {
            configFile >> nextParam;
            mCreatureDeathCounter = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "MaxCreaturesPerSeatAbsolute")
        {
            configFile >> nextParam;
            mMaxCreaturesPerSeatAbsolute = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "MaxCreaturesPerSeatDefault")
        {
            configFile >> nextParam;
            mMaxCreaturesPerSeatDefault = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreaturesPerPortal")
        {
            configFile >> nextParam;
            mCreaturesPerPortal = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "SlapDamagePercent")
        {
            configFile >> nextParam;
            mSlapDamagePercent = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "LavaDamagePerSecond")
        {
            configFile >> nextParam;
            mLavaDamagePerSecond = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SlapEffectDuration")
        {
            configFile >> nextParam;
            mSlapEffectDuration = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "TiredWakefulness")
        {
            configFile >> nextParam;
            mTiredWakefulness = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "HeartHealthStages")
        {
            configFile >> nextParam;
            mHeartHealthStages = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "HeartHealthStageEvents")
        {
            configFile >> nextParam;
            mHeartHealthStageEvents = Helper::toInt(nextParam) != 0;
            // Not mandatory
        }

        if(nextParam == "HitEvents")
        {
            configFile >> nextParam;
            mHitEvents = Helper::toInt(nextParam) != 0;
            // Not mandatory
        }

        if(nextParam == "HitGlanceShare")
        {
            configFile >> nextParam;
            mHitGlanceShare = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "HitStrongShare")
        {
            configFile >> nextParam;
            mHitStrongShare = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "AttackTurnEvents")
        {
            configFile >> nextParam;
            mAttackTurnEvents = Helper::toInt(nextParam) != 0;
            // Not mandatory
        }

        if(nextParam == "AttackTurnSpeed")
        {
            configFile >> nextParam;
            mAttackTurnSpeed = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "AttackTurnMaxDelay")
        {
            configFile >> nextParam;
            mAttackTurnMaxDelay = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "MeleeDodgeParry")
        {
            configFile >> nextParam;
            mMeleeDodgeParry = Helper::toInt(nextParam) != 0;
            // Not mandatory
        }

        if(nextParam == "DodgeBase")
        {
            configFile >> nextParam;
            mDodgeBase = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "DodgePerLevel")
        {
            configFile >> nextParam;
            mDodgePerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "DodgeMax")
        {
            configFile >> nextParam;
            mDodgeMax = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ParryBase")
        {
            configFile >> nextParam;
            mParryBase = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ParryPerLevel")
        {
            configFile >> nextParam;
            mParryPerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ParryMax")
        {
            configFile >> nextParam;
            mParryMax = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ShieldBlockBase")
        {
            configFile >> nextParam;
            mShieldBlockBase = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ShieldBlockPerLevel")
        {
            configFile >> nextParam;
            mShieldBlockPerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ShieldBlockMax")
        {
            configFile >> nextParam;
            mShieldBlockMax = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "TiredWalkSpeedFactor")
        {
            configFile >> nextParam;
            mTiredWalkSpeedFactor = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "LowHealthWalkSpeedFactor")
        {
            configFile >> nextParam;
            mLowHealthWalkSpeedFactor = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureLevelGrowthMax")
        {
            configFile >> nextParam;
            mCreatureLevelGrowthMax = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureDamageGrowth")
        {
            configFile >> nextParam;
            mCreatureDamageGrowth = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureDamageExponent")
        {
            configFile >> nextParam;
            mCreatureDamageExponent = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureHpGrowthPerLevel")
        {
            configFile >> nextParam;
            mCreatureHpGrowthPerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CooldownReductionPerLevel")
        {
            configFile >> nextParam;
            mCooldownReductionPerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CritChancePerDexterity")
        {
            configFile >> nextParam;
            mCritChancePerDexterity = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CritChancePerLevel")
        {
            configFile >> nextParam;
            mCritChancePerLevel = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CritDamageMultiplier")
        {
            configFile >> nextParam;
            mCritDamageMultiplier = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ManaRefillSeconds")
        {
            configFile >> nextParam;
            mManaRefillSeconds = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ManaPerCasterShot")
        {
            configFile >> nextParam;
            mManaPerCasterShot = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ManaPerDragonSecondShot")
        {
            configFile >> nextParam;
            mManaPerDragonSecondShot = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillPointFirstLevel")
        {
            configFile >> nextParam;
            mSkillPointFirstLevel = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillRanksPerSkill")
        {
            configFile >> nextParam;
            mSkillRanksPerSkill = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillTemplateDeviationPercent")
        {
            configFile >> nextParam;
            mSkillTemplateDeviationPercent = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillRespecChickens")
        {
            configFile >> nextParam;
            mSkillRespecChickens = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillRespecWindowSeconds")
        {
            configFile >> nextParam;
            mSkillRespecWindowSeconds = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillSpellReferenceMinHP")
        {
            configFile >> nextParam;
            mSkillSpellReferenceMinHP = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillHealSelfBelow")
        {
            configFile >> nextParam;
            mSkillHealSelfBelow = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillHealAllyBelow")
        {
            configFile >> nextParam;
            mSkillHealAllyBelow = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillHealAreaBelow")
        {
            configFile >> nextParam;
            mSkillHealAreaBelow = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "SkillHealAreaMinCreatures")
        {
            configFile >> nextParam;
            mSkillHealAreaMinCreatures = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "GoldCarryPerStrength")
        {
            configFile >> nextParam;
            mGoldCarryPerStrength = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "LowHealthWalkThresholdPercent")
        {
            configFile >> nextParam;
            mLowHealthWalkThresholdPercent = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "TimePayDay")
        {
            configFile >> nextParam;
            mTimePayDay = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "NbTurnsFuriousMax")
        {
            configFile >> nextParam;
            mNbTurnsFuriousMax = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "MaxManaPerSeat")
        {
            configFile >> nextParam;
            mMaxManaPerSeat = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ManaWellBonusPerTile")
        {
            configFile >> nextParam;
            mManaWellBonusPerTile = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "BedStepMaxHeight")
        {
            configFile >> nextParam;
            mBedStepMaxHeight = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "ClaimingWallPenalty")
        {
            configFile >> nextParam;
            mClaimingWallPenalty = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "GoldPerSeamTile")
        {
            configFile >> nextParam;
            mGoldPerSeamTile = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "GoldPerDigStep")
        {
            configFile >> nextParam;
            mGoldPerDigStep = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "GemGoldPerDigStep")
        {
            configFile >> nextParam;
            mGemGoldPerDigStep = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "WorkerCheerGoldShare")
        {
            configFile >> nextParam;
            mWorkerCheerGoldShare = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "DigCoefClaimedWall")
        {
            configFile >> nextParam;
            mDigCoefClaimedWall = Helper::toDouble(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureBaseMood")
        {
            configFile >> nextParam;
            mCreatureBaseMood = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureMoodHappy")
        {
            configFile >> nextParam;
            mCreatureMoodHappy = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureMoodUpset")
        {
            configFile >> nextParam;
            mCreatureMoodUpset = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureMoodAngry")
        {
            configFile >> nextParam;
            mCreatureMoodAngry = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "CreatureMoodFurious")
        {
            configFile >> nextParam;
            mCreatureMoodFurious = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "NbWorkersDigSameFaceTile")
        {
            configFile >> nextParam;
            mNbWorkersDigSameFaceTile = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "NbWorkersClaimSameTile")
        {
            configFile >> nextParam;
            mNbWorkersClaimSameTile = Helper::toUInt32(nextParam);
            // Not mandatory
        }

        if(nextParam == "NbTurnsKoCreatureAttacked")
        {
            configFile >> nextParam;
            mNbTurnsKoCreatureAttacked = Helper::toInt(nextParam);
            // Not mandatory
        }

        if(nextParam == "MainMenuMusic")
        {
            std::string line;
            std::getline(configFile, line);
            std::vector<std::string> elements = Helper::split(line, '\t', true);
            if (elements.empty())
            {
                OD_LOG_WRN("Invalid MainMenuMusic : " + line);
                continue;
            }
            mMainMenuMusic = elements[0];
            // Not mandatory
        }

        if(nextParam == "MasterServerUrl")
        {
            configFile >> mMasterServerUrl;
            // Not mandatory
        }
    }

    if(paramsOk != 0x01)
    {
        OD_LOG_ERR("Missing parameters paramsOk=" + Helper::toString(paramsOk));
        return false;
    }

    return true;
}

bool ConfigManager::loadCreatureDefinitions(const std::string& fileName)
{
    OD_LOG_INF("Load creature definition file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[CreatureDefinitions]")
    {
        OD_LOG_ERR("Invalid Creature classes start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/CreatureDefinitions]")
            break;

        if (nextParam == "[/Creature]")
            continue;

        // Seek the [Creature] tag
        if (nextParam != "[Creature]")
        {
            OD_LOG_ERR("Invalid Creature classes start format. Line was " + nextParam);
            return false;
        }

        // Load the creature definition until a [/Creature] tag is found
        CreatureDefinition* creatureDef = CreatureDefinition::load(defFile, mCreatureDefs);
        if (creatureDef == nullptr)
        {
            OD_LOG_ERR("Invalid Creature classes start format");
            return false;
        }
        mCreatureDefs.emplace(creatureDef->getClassName(), creatureDef);
    }

    return true;
}

bool ConfigManager::loadEquipements(const std::string& fileName)
{
    OD_LOG_INF("Load weapon definition file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[EquipmentDefinitions]")
    {
        OD_LOG_ERR("Invalid weapon start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/EquipmentDefinitions]")
            break;

        if (nextParam == "[/Equipment]")
            continue;

        if (nextParam != "[Equipment]")
        {
            OD_LOG_ERR("Invalid Weapon definition format. Line was " + nextParam);
            return false;
        }

        // Load the definition
        Weapon* weapon = Weapon::load(defFile);
        if (weapon == nullptr)
        {
            OD_LOG_ERR("Invalid Weapon definition format");
            return false;
        }
        mWeapons.push_back(weapon);
    }

    return true;
}

bool ConfigManager::loadSpawnConditions(const std::string& fileName)
{
    OD_LOG_INF("Load creature spawn conditions file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[SpawnConditions]")
    {
        OD_LOG_ERR("Invalid creature spawn condition start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/SpawnConditions]")
            break;

        if (nextParam == "[/SpawnCondition]")
            continue;

        if (nextParam == "BaseSpawnPoint")
        {
            defFile >> nextParam;
            mBaseSpawnPoint = Helper::toUInt32(nextParam);
            continue;
        }

        if (nextParam != "[SpawnCondition]")
        {
            OD_LOG_ERR("Invalid creature spawn condition format. Line was " + nextParam);
            return false;
        }

        if(!(defFile >> nextParam))
                break;
        if (nextParam != "CreatureClass")
        {
            OD_LOG_ERR("Invalid creature spawn condition format. Line was " + nextParam);
            return false;
        }
        defFile >> nextParam;
        const CreatureDefinition* creatureDefinition = getCreatureDefinition(nextParam);
        if(creatureDefinition == nullptr)
        {
            OD_LOG_ERR("nextParam=" + nextParam);
            return false;
        }

        while(defFile.good())
        {
            if(!(defFile >> nextParam))
                break;

            if (nextParam == "[/SpawnCondition]")
                break;

            if (nextParam != "[Condition]")
            {
                OD_LOG_ERR("Invalid creature spawn condition format. nextParam=" + nextParam);
                return false;
            }

            // Load the definition
            SpawnCondition* def = SpawnCondition::load(defFile);
            if (def == nullptr)
            {
                OD_LOG_ERR("Invalid creature spawn condition format");
                return false;
            }
            mCreatureSpawnConditions[creatureDefinition].push_back(def);
        }
    }

    return true;
}

bool ConfigManager::loadFactions(const std::string& fileName)
{
    OD_LOG_INF("Load factions file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[Factions]")
    {
        OD_LOG_ERR("Invalid factions start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/Factions]")
            break;

        if (nextParam != "[Faction]")
        {
            OD_LOG_ERR("Invalid faction. Line was " + nextParam);
            return false;
        }

        std::string factionName;
        std::string workerClass;
        while(defFile.good())
        {
            if(!(defFile >> nextParam))
                break;

            if (nextParam == "[/Faction]")
                break;

            if (nextParam == "[/Factions]")
                break;

            if (nextParam == "Name")
            {
                defFile >> factionName;
                continue;
            }
            if(factionName.empty())
            {
                OD_LOG_ERR("Empty or missing faction name is not allowed");
                return false;
            }

            if (nextParam == "WorkerClass")
            {
                defFile >> workerClass;
                continue;
            }
            if(workerClass.empty())
            {
                OD_LOG_ERR("Empty or missing WorkerClass name is not allowed");
                return false;
            }

            if (nextParam != "[SpawnPool]")
            {
                OD_LOG_ERR("Invalid faction. Line was " + nextParam);
                return false;
            }

            mFactions.push_back(factionName);
            mFactionDefaultWorkerClass[factionName] = workerClass;

            // The first faction in the config file is also used for the rogue seat
            if(mDefaultWorkerRogue.empty())
                mDefaultWorkerRogue = workerClass;

            while(defFile.good())
            {
                if(!(defFile >> nextParam))
                    break;

                if (nextParam == "[/SpawnPool]")
                    break;

                if (nextParam == "[/Faction]")
                    break;

                if (nextParam == "[/Factions]")
                    break;

                // We check if the creature definition exists
                const CreatureDefinition* creatureDefinition = getCreatureDefinition(nextParam);
                if(creatureDefinition == nullptr)
                {
                    OD_LOG_ERR("factionName=" + factionName + ", class=" + nextParam);
                    continue;
                }

                mFactionSpawnPool[factionName].push_back(nextParam);
            }
        }
    }

    return true;
}

//! \brief Loads immutable item lines while preserving catalogue order.
bool ConfigManager::loadItems(const std::string& fileName)
{
    std::stringstream stream;
    if(!Helper::readFile(fileName, stream, true))
        return false;
    std::string tag;
    if(!(stream >> tag) || tag != "[ItemDefinitions]")
        return false;
    while(stream >> tag)
    {
        if(tag == "[/ItemDefinitions]")
            return true;
        if(tag != "[Item]")
            return false;
        ItemDefinition* definition = ItemDefinition::load(stream);
        if(definition == nullptr)
            return false;
        if(getItem(definition->getId()) != nullptr)
        {
            delete definition;
            return false;
        }
        mItems.push_back(definition);
    }
    return false;
}

//! \brief Loads the potion and herb blocks without recalculating any supplied values.
bool ConfigManager::loadPotions(const std::string& fileName)
{
    std::stringstream stream;
    if(!Helper::readFile(fileName, stream, true))
        return false;
    std::string tag;
    while(stream >> tag)
    {
        if(tag == "[Potion]")
        {
            PotionDefinition definition;
            if(!definition.importFromStream(stream) || getPotion(definition.getId()) != nullptr)
                return false;
            mPotions.push_back(definition);
        }
        else if(tag == "[Herb]")
        {
            HerbDefinition definition;
            if(!definition.importFromStream(stream) || getHerb(definition.mId) != nullptr)
                return false;
            mHerbs.push_back(definition);
        }
        else if(tag != "[PotionDefinitions]" && tag != "[/PotionDefinitions]" &&
            tag != "[HerbDefinitions]" && tag != "[/HerbDefinitions]")
            return false;
    }
    return !mPotions.empty() && !mHerbs.empty();
}

//! \brief Reads one numeric settings section used by item rolls, evaluation or drinking.
bool ConfigManager::loadItemSettings(std::stringstream& stream, const std::string& section)
{
    std::string key;
    const std::string end = "[/" + section + "]";
    while(stream >> key)
    {
        if(key == end)
            return true;
        double value = 0.0;
        if(!(stream >> value))
            return false;
        mItemSettings[section][key] = value;
    }
    return false;
}

//! \brief Looks up an immutable item line by id.
const ItemDefinition* ConfigManager::getItem(const std::string& id) const
{
    for(const ItemDefinition* definition : mItems)
    {
        if(definition->getId() == id)
            return definition;
    }
    return nullptr;
}

//! \brief Looks up a potion recipe by id.
const PotionDefinition* ConfigManager::getPotion(const std::string& id) const
{
    for(const PotionDefinition& definition : mPotions)
    {
        if(definition.getId() == id)
            return &definition;
    }
    return nullptr;
}

//! \brief Looks up a herb's growth parameters by id.
const HerbDefinition* ConfigManager::getHerb(const std::string& id) const
{
    for(const HerbDefinition& definition : mHerbs)
    {
        if(definition.mId == id)
            return &definition;
    }
    return nullptr;
}

//! \brief Returns a required configured rule value, failing clearly when its key is missing.
double ConfigManager::getItemSetting(const std::string& section, const std::string& key) const
{
    return mItemSettings.at(section).at(key);
}

bool ConfigManager::loadRooms(const std::string& fileName)
{
    OD_LOG_INF("Load Rooms file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[Rooms]")
    {
        OD_LOG_ERR("Invalid factions start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/Rooms]")
            break;

        defFile >> mRoomsConfig[NameAliases::resolve(nextParam)];
    }

    return true;
}

void ConfigManager::loadRelationships(const std::string& fileName)
{
    OD_LOG_INF("Load relationships file: " + fileName);
    mRelationshipsConfig.clear();
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_WRN("Couldn't read " + fileName + ", using the default relationship values");
        return;
    }

    std::string nextParam;
    defFile >> nextParam;
    if(nextParam != "[Relationships]")
    {
        OD_LOG_WRN("Invalid relationships start format. Line was " + nextParam);
        return;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if(nextParam == "[/Relationships]")
            break;

        std::string value;
        defFile >> value;
        mRelationshipsConfig[nextParam] = value;
    }
}

void ConfigManager::loadTreasury(const std::string& fileName)
{
    OD_LOG_INF("Load treasury file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_WRN("Couldn't read " + fileName + ", using the default treasury values");
        return;
    }

    std::string nextParam;
    defFile >> nextParam;
    if(nextParam != "[Treasury]")
    {
        OD_LOG_WRN("Invalid treasury start format. Line was " + nextParam);
        return;
    }

    std::map<std::string, std::string> values;
    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if(nextParam == "[/Treasury]")
            break;

        std::string value;
        defFile >> value;
        values[nextParam] = value;
    }
    TreasurySettings::current() = TreasurySettings::fromConfig(values);
}

//! \brief Reads config/ai.cfg over the compiled defaults; a missing file keeps the defaults.
bool ConfigManager::loadAiConfig(const std::string& fileName)
{
    OD_LOG_INF("Load AI file: " + fileName);
    setAiConfigDefaults();
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_WRN("Couldn't read " + fileName + ", using the default AI values");
        return true;
    }

    std::string section;
    std::string line;
    while(std::getline(defFile, line))
    {
        std::stringstream lineStream(line);
        std::vector<std::string> words;
        std::string word;
        while(lineStream >> word)
            words.push_back(word);

        if(words.empty())
            continue;

        if(section.empty())
        {
            if((words.size() != 1) || ((words[0] != "[KeeperAILevels]") && (words[0] != "[KeeperAI]") &&
                (words[0] != "[RoomPlan]") && (words[0] != "[Actions]") && (words[0] != "[RowClasses]")))
            {
                OD_LOG_ERR("Invalid AI section in " + fileName + ". Line was " + line);
                return false;
            }
            section = words[0];
            // A table section of the file replaces the compiled table
            if(section == "[RoomPlan]")
                mAiRoomPlan.clear();
            else if(section == "[Actions]")
                mAiActions.clear();
            else if(section == "[RowClasses]")
                mAiRowClasses.clear();
            continue;
        }

        if((words.size() == 1) && (words[0] == "[/" + section.substr(1)))
        {
            section.clear();
            continue;
        }

        if(!readAiConfigLine(section, words))
        {
            OD_LOG_ERR("Invalid AI line in section " + section + " of " + fileName + ". Line was " + line);
            return false;
        }
    }

    if(!section.empty())
    {
        OD_LOG_ERR("Missing end of section " + section + " in " + fileName);
        return false;
    }
    return true;
}

//! \brief Sets every keeper AI value to its compiled default; the room plan stays empty (compiled in KeeperAI).
void ConfigManager::setAiConfigDefaults()
{
    mAiConfig.clear();
    for(const char* const* row : AI_CONFIG_DEFAULTS)
        mAiConfig[row[0]] = row[1];

    for(const char* const* row : AI_LEVEL_DEFAULTS)
        readAiConfigLine("[KeeperAILevels]", std::vector<std::string>(row, row + 6));

    mAiRoomPlan.clear();
    mAiActions.clear();
    for(const char* const* row : AI_ACTION_DEFAULTS)
        readAiConfigLine("[Actions]", std::vector<std::string>(row, row + 3));

    mAiRowClasses.clear();
    for(const char* const* row : AI_ROW_CLASS_DEFAULTS)
        readAiConfigLine("[RowClasses]", std::vector<std::string>(row, row + 3));
}

//! \brief Reads one line of a section of ai.cfg; false for an unknown key or word or a wrong number of words.
bool ConfigManager::readAiConfigLine(const std::string& section, const std::vector<std::string>& words)
{
    if(section == "[KeeperAILevels]")
    {
        if(words.size() != 1 + mAiLevels.size())
            return false;

        if(words[0] == "EnemyManaEstimate")
        {
            for(uint32_t i = 0; i < mAiLevels.size(); ++i)
            {
                if(words[i + 1] == "own")
                    mAiLevels[i].enemyManaEstimate = EnemyManaEstimateMode::own;
                else if(words[i + 1] == "observed")
                    mAiLevels[i].enemyManaEstimate = EnemyManaEstimateMode::observed;
                else
                    return false;
            }
            return true;
        }

        for(uint32_t i = 0; i < mAiLevels.size(); ++i)
        {
            double* field = aiLevelField(mAiLevels[i], words[0]);
            if(field == nullptr)
                return false;

            *field = Helper::toDouble(words[i + 1]);
        }
        return true;
    }

    if(section == "[KeeperAI]")
    {
        // Every key has a compiled default, so a key without one is unknown
        std::map<std::string, std::string>::iterator it = mAiConfig.find(words[0]);
        if((words.size() != 2) || (it == mAiConfig.end()))
            return false;

        it->second = words[1];
        return true;
    }

    if(section == "[RoomPlan]")
    {
        if(words.size() != 2)
            return false;

        mAiRoomPlan.push_back(std::make_pair(words[0], Helper::toUInt32(words[1])));
        return true;
    }

    if(section == "[Actions]")
    {
        if(words.size() != 3)
            return false;

        AiAction action;
        action.mName = words[0];
        action.mClicks = Helper::toUInt32(words[1]);
        action.mSeconds = Helper::toDouble(words[2]);
        mAiActions.push_back(action);
        return true;
    }

    if(section == "[RowClasses]")
    {
        if((words.size() != 3) || !isAiMistakeClass(words[1]))
            return false;

        AiRowClass rowClass;
        rowClass.mId = words[0];
        rowClass.mClass = words[1];
        rowClass.mMultiplier = Helper::toDouble(words[2]);
        mAiRowClasses.push_back(rowClass);
        return true;
    }

    return false;
}

bool ConfigManager::loadTraps(const std::string& fileName)
{
    OD_LOG_INF("Load traps file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[Traps]")
    {
        OD_LOG_ERR("Invalid Traps start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/Traps]")
            break;

        defFile >> mTrapsConfig[NameAliases::resolve(nextParam)];
    }

    return true;
}

bool ConfigManager::loadSpellConfig(const std::string& fileName)
{
    OD_LOG_INF("Load Spell config file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[Spells]")
    {
        OD_LOG_ERR("Invalid Spells start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/Spells]")
            break;

        defFile >> mSpellConfig[NameAliases::resolve(nextParam)];
    }

    return true;
}

//! \brief Reads the creature skill trees: the [Skill], [TierFour] and [Template] blocks of creatureSkills.cfg.
bool ConfigManager::loadCreatureSkills(const std::string& fileName)
{
    OD_LOG_INF("Load creature skills file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile, true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string error;
    if(!mCreatureSkillTree.load(defFile, error))
    {
        OD_LOG_ERR("Invalid creature skills file " + fileName + ": " + error);
        return false;
    }

    return true;
}

bool ConfigManager::loadSkills(const std::string& fileName)
{
    OD_LOG_INF("Load Skills file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    // Read in the creature class descriptions
    defFile >> nextParam;
    if (nextParam != "[Skills]")
    {
        OD_LOG_ERR("Invalid Skills start format. Line was " + nextParam);
        return false;
    }

    while(defFile.good())
    {
        if(!(defFile >> nextParam))
            break;

        if (nextParam == "[/Skills]")
            break;

        defFile >> mSkillPoints[NameAliases::resolve(nextParam)];
    }

    // The optional block with the skills every seat starts with at level 1
    mSkillsFreeLevelOne.clear();
    if(defFile >> nextParam)
    {
        if(nextParam != "[FreeLevelOne]")
        {
            OD_LOG_ERR("Invalid FreeLevelOne start format. Line was " + nextParam);
            return false;
        }

        while(defFile >> nextParam)
        {
            if(nextParam == "[/FreeLevelOne]")
                break;

            mSkillsFreeLevelOne.insert(nextParam);
        }
    }

    // The optional block with the effect of each research level on rooms, traps, doors, spells and the keeper
    mResearchEffects.clear();
    if(defFile >> nextParam)
    {
        if(nextParam != "[ResearchEffects]")
        {
            OD_LOG_ERR("Invalid ResearchEffects start format. Line was " + nextParam);
            return false;
        }

        while(defFile >> nextParam)
        {
            if(nextParam == "[/ResearchEffects]")
                break;

            std::string effect;
            std::string mode;
            ResearchEffectLine line;
            defFile >> effect >> mode;
            if(mode == "mul")
                line.mMode = ResearchEffectMode::mul;
            else if(mode == "add")
                line.mMode = ResearchEffectMode::add;
            else if(mode == "dev")
                line.mMode = ResearchEffectMode::dev;
            else
            {
                OD_LOG_ERR("Invalid research effect mode=" + mode + " for " + nextParam + " " + effect);
                return false;
            }

            for(uint32_t i = 0; i < RESEARCH_LEVELS; ++i)
                defFile >> line.mValues[i];

            mResearchEffects.push_back(std::make_pair(std::make_pair(nextParam, effect), line));
        }
    }
    return true;
}

//! \brief Loads every registered tile visual, including the infirmary floor masks.
bool ConfigManager::loadTilesets(const std::string& fileName)
{
    OD_LOG_INF("Load Tilesets file: " + fileName);
    std::stringstream defFile;
    if(!Helper::readFile(fileName, defFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }

    std::string nextParam;
    defFile >> nextParam;
    if (nextParam != "[Tilesets]")
    {
        OD_LOG_ERR("Invalid Tilesets start format. Line was " + nextParam);
        return false;
    }

    while(true)
    {
        defFile >> nextParam;
        if (nextParam == "[/Tilesets]")
            break;

        if (nextParam == "[/Tileset]")
            continue;

        if (nextParam != "[Tileset]")
        {
            OD_LOG_ERR("Expecting TileSet tag but got=" + nextParam);
            return false;
        }

        defFile >> nextParam;
        if (nextParam != "Name")
        {
            OD_LOG_ERR("Expecting Name tag but got=" + nextParam);
            return false;
        }

        std::string tileSetName;
        defFile >> tileSetName;

        TileSet* tileSet = new TileSet();
        mTileSets[tileSetName] = tileSet;

        HighMap* mHighMap = new HighMap();
        mHighMaps[tileSetName] = mHighMap;
        
        defFile >> nextParam;
        if(nextParam != "[TileLink]")
        {
            OD_LOG_ERR("Expecting TileLink tag but got=" + nextParam);
            return false;
        }

        while(true)
        {
            defFile >> nextParam;
            if(nextParam == "[/TileLink]")
                break;

            TileVisual tileVisual1 = Tile::tileVisualFromString(nextParam);
            if(tileVisual1 == TileVisual::nullTileVisual)
            {
                OD_LOG_ERR("Wrong TileVisual1 in tileset=" + nextParam);
                return false;
            }

            defFile >> nextParam;
            TileVisual tileVisual2 = Tile::tileVisualFromString(nextParam);
            if(tileVisual2 == TileVisual::nullTileVisual)
            {
                OD_LOG_ERR("Wrong TileVisual2 in tileset=" + nextParam);
                return false;
            }

            tileSet->addTileLink(tileVisual1, tileVisual2);
        }
        if(!loadTilesetValues(defFile, TileVisual::nullTileVisual, tileSet->configureTileValues(TileVisual::nullTileVisual),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::goldGround, tileSet->configureTileValues(TileVisual::goldGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::goldFull, tileSet->configureTileValues(TileVisual::goldFull),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::dirtGround, tileSet->configureTileValues(TileVisual::dirtGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::dirtFull, tileSet->configureTileValues(TileVisual::dirtFull),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::rockGround, tileSet->configureTileValues(TileVisual::rockGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::rockFull, tileSet->configureTileValues(TileVisual::rockFull),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::waterGround, tileSet->configureTileValues(TileVisual::waterGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::lavaGround, tileSet->configureTileValues(TileVisual::lavaGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::claimedGround, tileSet->configureTileValues(TileVisual::claimedGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::claimedFull, tileSet->configureTileValues(TileVisual::claimedFull),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::gemGround, tileSet->configureTileValues(TileVisual::gemGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::gemFull, tileSet->configureTileValues(TileVisual::gemFull),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::dungeonTempleRoom, tileSet->configureTileValues(TileVisual::dungeonTempleRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::dormitoryRoom, tileSet->configureTileValues(TileVisual::dormitoryRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::treasuryRoom, tileSet->configureTileValues(TileVisual::treasuryRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::portalRoom, tileSet->configureTileValues(TileVisual::portalRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::workshopRoom, tileSet->configureTileValues(TileVisual::workshopRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::trainingHallRoom, tileSet->configureTileValues(TileVisual::trainingHallRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::libraryRoom, tileSet->configureTileValues(TileVisual::libraryRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::hatcheryRoom, tileSet->configureTileValues(TileVisual::hatcheryRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::cryptRoom, tileSet->configureTileValues(TileVisual::cryptRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::portalWaveRoom, tileSet->configureTileValues(TileVisual::portalWaveRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::prisonRoom, tileSet->configureTileValues(TileVisual::prisonRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::arenaRoom, tileSet->configureTileValues(TileVisual::arenaRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::casinoRoom, tileSet->configureTileValues(TileVisual::casinoRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::tortureRoom, tileSet->configureTileValues(TileVisual::tortureRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::guardRoom, tileSet->configureTileValues(TileVisual::guardRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::manaWellGround, tileSet->configureTileValues(TileVisual::manaWellGround),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::templeRoom, tileSet->configureTileValues(TileVisual::templeRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::toiletRoom, tileSet->configureTileValues(TileVisual::toiletRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::merchantRoom, tileSet->configureTileValues(TileVisual::merchantRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::herbGardenRoom, tileSet->configureTileValues(TileVisual::herbGardenRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::alchemyLabRoom, tileSet->configureTileValues(TileVisual::alchemyLabRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::tavernRoom, tileSet->configureTileValues(TileVisual::tavernRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::infirmaryRoom, tileSet->configureTileValues(TileVisual::infirmaryRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::ghostRoom, tileSet->configureTileValues(TileVisual::ghostRoom),*mHighMap))
            return false;
        if(!loadTilesetValues(defFile, TileVisual::spaRoom, tileSet->configureTileValues(TileVisual::spaRoom),*mHighMap))
            return false;

    }

    // At least the default tileset should be defined
    if(mTileSets.count(DEFAULT_TILESET_NAME) <= 0)
    {
        OD_LOG_ERR("No tileset defined with name=" + DEFAULT_TILESET_NAME);
        return false;
    }
    return true;
}

bool ConfigManager::loadTilesetValues(std::istream& defFile, TileVisual tileVisual, std::vector<std::vector<TileSetValue>>& tileValues, std::map<TileVisual,std::map<int,float>>& highMap)
{
    std::string nextParam;
    std::string beginTag = "[" + Tile::tileVisualToString(tileVisual) + "]";
    std::string endTag = "[/" + Tile::tileVisualToString(tileVisual) + "]";
    defFile >> nextParam;
    if (nextParam != beginTag)
    {
        OD_LOG_ERR("Expecting " + beginTag + " tag but got=" + nextParam);
        return false;
    }
    while(true)
    {
        std::string indexStr;
        defFile >> indexStr;
        if(indexStr == endTag)
            return true;

        boost::dynamic_bitset<> x(indexStr);
        uint32_t index = static_cast<int>(x.to_ulong());

        std::string meshName;
        defFile >> meshName;


        std::string materialName;
        double rotX, rotY, rotZ;
        float high;
        
        if(meshName=="[oneOf]"){
            defFile >> nextParam;
            while(nextParam!="[/oneOf]")
            {

                meshName = nextParam;
               
                defFile >> materialName;
                if(materialName.compare("''") == 0)
                    materialName.clear();

                std::string mLine;
                getline(defFile,mLine);

                std::vector<std::string> resVtr = Helper::split(mLine, '\t', true);

                rotX = Helper::stringToT<double>(resVtr[0]);
                rotY = Helper::stringToT<double>(resVtr[1]);                
                rotZ = Helper::stringToT<double>(resVtr[2]);

                if(resVtr.size() > 3)
                    high =  Helper::stringToT<float>(resVtr[3]);
                else
                    high = 0;
                
                if(index >= tileValues.size())
                {
                    OD_LOG_ERR("Tileset index too high in tileset=" + endTag + ", index=" + indexStr);
                    return false;
                }
                
                highMap[tileVisual][index] = high;
                
                tileValues[index].push_back(TileSetValue(meshName, materialName, rotX, rotY, rotZ));
                defFile >> nextParam;
            }
            continue;
        }         
        defFile >> materialName;
        
        if(materialName.compare("''") == 0)
            materialName.clear();

        std::string mLine;
        getline(defFile,mLine);

        std::vector<std::string> resVtr = Helper::split(mLine, '\t', true);

        rotX = Helper::stringToT<double>(resVtr[0]);
        rotY = Helper::stringToT<double>(resVtr[1]);                
        rotZ = Helper::stringToT<double>(resVtr[2]);

        if(resVtr.size() > 3)
            high =  Helper::stringToT<float>(resVtr[3]);
        else
            high = 0;

        if(index >= tileValues.size())
        {
            OD_LOG_ERR("Tileset index too high in tileset=" + endTag + ", index=" + indexStr);
            return false;
        }

        highMap[tileVisual][index] = high;
        tileValues[index].push_back(TileSetValue(meshName, materialName, rotX, rotY, rotZ));
    }
}

bool ConfigManager::loadEditorSettings(const std::string& fileName)
{
    OD_LOG_INF("Load EditorSettings file:" + fileName);
    std::stringstream editorFile;
    std::string nextParam;
    boost::circular_buffer<boost::filesystem::path>::capacity_type capacity;
    
    if(!Helper::readFile(fileName, editorFile,true))
    {
        OD_LOG_ERR("Couldn't read " + fileName);
        return false;
    }
    editorFile >> nextParam;
    if (nextParam != "[Capacity]")
    {
        OD_LOG_ERR("Invalid EditorSettings start format. Expected [Capacity] Line was " + nextParam);
        return false;
    }
    editorFile >> capacity;
    editorFile >> nextParam;    
    if (nextParam != "[/Capacity]")
    {
        OD_LOG_ERR("Invalid EditorSettings start format. Expected [/Capacity] Line was " + nextParam);
        return false;
    }
    
    recentlyUsedLevels.clear();
    recentlyUsedLevels.set_capacity(capacity);
    boost::filesystem::path pp;

    editorFile >> nextParam;
    if (nextParam != "[FilePath]")
    {
        OD_LOG_ERR("Invalid EditorSettings start format. Expected [FilePath] Line was " + nextParam);
        return false;
    }
    
    while(editorFile.good())
    {
        if (!(editorFile >> nextParam))
        {
            break;
        }
        else if (nextParam == "[/FilePath]")
        {
            break;
        }        
        recentlyUsedLevels.push_front(nextParam);
    }
    return true;
}

bool ConfigManager::saveEditorSettings()
{
    std::ofstream editorFile (mConfigPath + mFilenameEditor);
    editorFile << "[Capacity]" << std::endl;
    editorFile<<recentlyUsedLevels.capacity()  << std::endl;
    editorFile << "[/Capacity]" << std::endl;
    editorFile << "[FilePath]" << std::endl;
    boost::circular_buffer<boost::filesystem::path>::size_type size = recentlyUsedLevels.size();
    while(size--)
    {
        editorFile<<recentlyUsedLevels[size].c_str() << std::endl;
    }
    editorFile << "[/FilePath]";
    return true;
}


void ConfigManager::loadUserConfig(const std::string& fileName)
{
    if (fileName.empty())
        return;

    mFilenameUserCfg = fileName;

    OD_LOG_INF("Load user config file: " + fileName);
    std::stringstream defFile;
    
    if(!boost::filesystem::exists(fileName))
    {
        loadDefaultValuesForUserConfig();
        saveUserConfig();
    }
    else
    {
    
        if(!Helper::readFile(fileName, defFile,true))
        {
        
            OD_LOG_INF("Couldn't read " + fileName);
            return;
        }

        mUserConfig.clear();
        mUserConfig.resize(Config::Ctg::TOTAL);

        std::string nextParam;
        defFile >> nextParam;
        if (nextParam != "[Configuration]")
        {
            OD_LOG_WRN("Invalid User configuration start format. Line was " + nextParam);
            return;
        }

        std::string value;
        Config::Ctg category = Config::Ctg::NONE;
        while(defFile.good())
        {
            if (!(defFile >> nextParam))
            {
                break;
            }
            else if (nextParam == "[/Configuration]")
            {
                break;
            }
            else if (nextParam == "[Audio]")
            {
                category = Config::Ctg::AUDIO;
                continue;
            }
            else if (nextParam == "[Video]")
            {
                category = Config::Ctg::VIDEO;
                continue;
            }
            else if (nextParam == "[Input]")
            {
                category = Config::Ctg::INPUT;
                continue;
            }
            else if (nextParam == "[Game]")
            {
                category = Config::Ctg::GAME;
                continue;
            }
            else if (nextParam == "[/Audio]" || nextParam == "[/Video]" || nextParam == "[/Input]"
                     || nextParam == "[/Game]")
            {
                category = Config::Ctg::NONE;
                continue;
            }
            else if (!nextParam.empty())
            {
                std::string line;
                std::getline(defFile, line);
                // Make sure to cut the line only when encountering a tab.
                line = nextParam + line;
                std::vector<std::string> elements = Helper::split(line, '\t');
                if (elements.size() != 2)
                {
                    OD_LOG_WRN("Invalid parameter line: " + line);
                    continue;
                }

                if (category == Config::Ctg::NONE)
                {
                    OD_LOG_WRN("Parameter set in unknown category. Will be ignored: "
                               + elements[0] + ": " + elements[1]);
                    continue;
                }

                mUserConfig[ category ][ elements[0] ] = elements[1];
                OD_LOG_WRN("Parameter set in " +  Helper::toString( category)  + " KNOWN category. "
                           + elements[0] + ": " + elements[1]);
            }
            else
            {
                continue;
            }
        }
    }
}

bool ConfigManager::saveUserConfig()
{
    if (mFilenameUserCfg.empty())
    {
        OD_LOG_ERR("Can't save config. The user config file isn't set.");
        return false;
    }

    std::ofstream userFile(mFilenameUserCfg.c_str(), std::ifstream::out);
    if (!userFile.is_open())
    {
        OD_LOG_ERR("Couldn't open user config for writing: " + mFilenameUserCfg);
        return false;
    }

    // Split config in categories.
    std::map<std::string, std::string>& mAudioUserConfig = mUserConfig.at(Config::Ctg::AUDIO);
    std::map<std::string, std::string>& mVideoUserConfig = mUserConfig.at(Config::Ctg::VIDEO);
    std::map<std::string, std::string>& mInputUserConfig = mUserConfig.at(Config::Ctg::INPUT);
    std::map<std::string, std::string>& mGameUserConfig = mUserConfig.at(Config::Ctg::GAME);

    userFile << "[Configuration]" << std::endl;

    userFile << "[Audio]" << std::endl;
    for(std::pair<std::string, std::string> audio : mAudioUserConfig)
        userFile << audio.first << "\t" << audio.second << std::endl;
    userFile << "[/Audio]" << std::endl;

    userFile << "[Video]" << std::endl;
    for(std::pair<std::string, std::string> video : mVideoUserConfig)
        userFile << video.first << "\t" << video.second << std::endl;
    userFile << "[/Video]" << std::endl;

    userFile << "[Input]" << std::endl;
    for(std::pair<std::string, std::string> input : mInputUserConfig)
        userFile << input.first << "\t" << input.second << std::endl;
    userFile << "[/Input]" << std::endl;

    userFile << "[Game]" << std::endl;
    for(std::pair<std::string, std::string> input : mGameUserConfig)
        userFile << input.first << "\t" << input.second << std::endl;
    userFile << "[/Game]" << std::endl;

    userFile << "[/Configuration]" << std::endl;
    userFile.close();
    return true;
}

const std::string ConfigManager::getUserValue(Config::Ctg category,
                                               const std::string& param,
                                               const std::string& defaultValue,
                                               bool triggerError) const
{
    if (category >= mUserConfig.size())
    {
        OD_LOG_ERR("User configuration categories uninitialized!");
        return defaultValue;
    }
    const std::map<std::string, std::string>& userCfg = mUserConfig[category];

    std::map<std::string, std::string>::const_iterator it = userCfg.find(param);
    if(it == userCfg.end())
    {
        if (triggerError)
            OD_LOG_ERR("Unknown parameter param=" + param);
        return defaultValue;
    }

    return it->second;
}

bool ConfigManager::hasRoomConfig(const std::string& param) const
{
    return mRoomsConfig.find(param) != mRoomsConfig.end();
}

const std::string& ConfigManager::getRoomConfigString(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if(it == mRoomsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return EMPTY_STRING;
    }

    return it->second;
}

uint32_t ConfigManager::getRoomConfigUInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if(it == mRoomsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toUInt32(it->second);
}

int32_t ConfigManager::getRoomConfigInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if(it == mRoomsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toInt(it->second);
}

double ConfigManager::getRoomConfigDouble(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if(it == mRoomsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0.0;
    }

    return Helper::toDouble(it->second);
}

double ConfigManager::getRoomConfigDoubleOrDefault(const std::string& param, double defaultValue) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if(it == mRoomsConfig.end())
        return defaultValue;

    return Helper::toDouble(it->second);
}

std::string ConfigManager::getRoomConfigStringOrDefault(const std::string& param, const std::string& defaultValue) const
{
    std::map<const std::string, std::string>::const_iterator it = mRoomsConfig.find(param);
    if((it == mRoomsConfig.end()) || it->second.empty())
        return defaultValue;

    return it->second;
}

const std::string& ConfigManager::getTrapConfigString(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mTrapsConfig.find(param);
    if(it == mTrapsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return EMPTY_STRING;
    }

    return it->second;
}

uint32_t ConfigManager::getTrapConfigUInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mTrapsConfig.find(param);
    if(it == mTrapsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toUInt32(it->second);
}

int32_t ConfigManager::getTrapConfigInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mTrapsConfig.find(param);
    if(it == mTrapsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toInt(it->second);
}

double ConfigManager::getTrapConfigDouble(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mTrapsConfig.find(param);
    if(it == mTrapsConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0.0;
    }

    return Helper::toDouble(it->second);
}

double ConfigManager::getTrapConfigDoubleOrDefault(const std::string& param, double defaultValue) const
{
    std::map<const std::string, std::string>::const_iterator it = mTrapsConfig.find(param);
    if(it == mTrapsConfig.end())
        return defaultValue;

    return Helper::toDouble(it->second);
}

const std::string& ConfigManager::getSpellConfigString(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mSpellConfig.find(param);
    if(it == mSpellConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return EMPTY_STRING;
    }

    return it->second;
}

uint32_t ConfigManager::getSpellConfigUInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mSpellConfig.find(param);
    if(it == mSpellConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toUInt32(it->second);
}

int32_t ConfigManager::getSpellConfigInt32(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mSpellConfig.find(param);
    if(it == mSpellConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toInt(it->second);
}

double ConfigManager::getSpellConfigDouble(const std::string& param) const
{
    std::map<const std::string, std::string>::const_iterator it = mSpellConfig.find(param);
    if(it == mSpellConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0.0;
    }

    return Helper::toDouble(it->second);
}

//! \brief The values of a keeper AI level; the column follows the display order of the levels.
AiSettings ConfigManager::getAiLevel(KeeperAIType type) const
{
    for(uint32_t i = 0; i < KeeperAITypes::displayOrder.size(); ++i)
    {
        if(KeeperAITypes::displayOrder[i] == type)
            return mAiLevels[i];
    }

    OD_LOG_ERR("Unknown AI level=" + Helper::toString(static_cast<uint32_t>(type)));
    return getAiLevel(KeeperAIType::normal);
}

//! \brief A whole-number value of the [KeeperAI] section of ai.cfg; an unknown key logs an error and gives 0.
int32_t ConfigManager::getAiConfigInt32(const std::string& param) const
{
    std::map<std::string, std::string>::const_iterator it = mAiConfig.find(param);
    if(it == mAiConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0;
    }

    return Helper::toInt(it->second);
}

//! \brief A value of the [KeeperAI] section of ai.cfg; an unknown key logs an error and gives 0.
double ConfigManager::getAiConfigDouble(const std::string& param) const
{
    std::map<std::string, std::string>::const_iterator it = mAiConfig.find(param);
    if(it == mAiConfig.end())
    {
        OD_LOG_ERR("Unknown parameter param=" + param);
        return 0.0;
    }

    return Helper::toDouble(it->second);
}

//! \brief The action of the [Actions] section of ai.cfg with the given name, or nullptr.
const ConfigManager::AiAction* ConfigManager::getAiAction(const std::string& name) const
{
    for(const AiAction& action : mAiActions)
    {
        if(action.mName == name)
            return &action;
    }

    OD_LOG_ERR("Unknown AI action=" + name);
    return nullptr;
}

//! \brief The line of the [RowClasses] section of ai.cfg with the given decision id, or nullptr.
const ConfigManager::AiRowClass* ConfigManager::getAiRowClass(const std::string& id) const
{
    for(const AiRowClass& rowClass : mAiRowClasses)
    {
        if(rowClass.mId == id)
            return &rowClass;
    }

    OD_LOG_ERR("Unknown AI row=" + id);
    return nullptr;
}

int32_t ConfigManager::getSkillPoints(const std::string& res) const
{
    std::map<const std::string, int32_t>::const_iterator it = mSkillPoints.find(res);
    if(it == mSkillPoints.end())
    {
        OD_LOG_ERR("Unknown parameter res=" + res);
        return SKILL_POINTS_MISSING_ENTRY;
    }

    return it->second;
}

bool ConfigManager::isSkillFreeLevelOne(const std::string& res) const
{
    return mSkillsFreeLevelOne.find(res) != mSkillsFreeLevelOne.end();
}

const ConfigManager::ResearchEffectLine* ConfigManager::getResearchEffect(const std::string& skill,
    const std::string& effect) const
{
    for(const std::pair<std::pair<std::string, std::string>, ResearchEffectLine>& entry : mResearchEffects)
    {
        if((entry.first.first == skill) && (entry.first.second == effect))
            return &entry.second;
    }

    return nullptr;
}

void ConfigManager::getResearchEffects(const std::string& skill,
    std::vector<std::pair<std::string, ResearchEffectLine> >& effects) const
{
    effects.clear();
    for(const std::pair<std::pair<std::string, std::string>, ResearchEffectLine>& entry : mResearchEffects)
    {
        if(entry.first.first == skill)
            effects.push_back(std::make_pair(entry.first.second, entry.second));
    }
}

const CreatureDefinition* ConfigManager::getCreatureDefinition(const std::string& name) const
{
    std::map<std::string, CreatureDefinition*>::const_iterator it = mCreatureDefs.find(name);
    if(it != mCreatureDefs.end())
    {
        return it->second;
    }
    return nullptr;
}

const Weapon* ConfigManager::getWeapon(const std::string& name) const
{
    for(const Weapon* def : mWeapons)
    {
        if(name.compare(def->getName()) == 0)
            return def;
    }

    return nullptr;
}

const Ogre::ColourValue& ConfigManager::getColorFromId(const std::string& id) const
{
    std::map<std::string, Ogre::ColourValue>::const_iterator it = mSeatColors.find(id);
    if(it == mSeatColors.end())
        return DEFAULT_SEAT_COLOURVALUE;

    return it->second;

}

const std::vector<const SpawnCondition*>& ConfigManager::getCreatureSpawnConditions(const CreatureDefinition* def) const
{
    std::map<const CreatureDefinition*, std::vector<const SpawnCondition*>>::const_iterator it = mCreatureSpawnConditions.find(def);
    if(it == mCreatureSpawnConditions.end())
        return SpawnCondition::EMPTY_SPAWNCONDITIONS;

    return it->second;
}

const std::vector<std::string>& ConfigManager::getFactionSpawnPool(const std::string& faction) const
{
    std::map<const std::string, std::vector<Ogre::String>>::const_iterator it = mFactionSpawnPool.find(faction);
    if(it == mFactionSpawnPool.end())
        return EMPTY_SPAWNPOOL;

    return it->second;
}

const std::string& ConfigManager::getFactionWorkerClass(const std::string& faction) const
{
    std::map<const std::string, std::string>::const_iterator it = mFactionDefaultWorkerClass.find(faction);
    if(it == mFactionDefaultWorkerClass.end())
        return EMPTY_STRING;

    return it->second;
}

const TileSet* ConfigManager::getTileSet(const std::string& tileSetName) const
{
    if(tileSetName.empty())
        return mTileSets.at(DEFAULT_TILESET_NAME);

    std::map<std::string, const TileSet*>::const_iterator it = mTileSets.find(tileSetName);
    if(it == mTileSets.end())
    {
        OD_LOG_ERR("Cannot find requested tileset name=" + tileSetName);
        // We return the default tileset
        return mTileSets.at(DEFAULT_TILESET_NAME);
    }

    return it->second;
}

const HighMap* ConfigManager::getHighMap(const std::string& tileSetName) const
{
    if(tileSetName.empty())
        return mHighMaps.at(DEFAULT_TILESET_NAME);

    std::map<std::string, const HighMap*>::const_iterator it = mHighMaps.find(tileSetName);
    if(it == mHighMaps.end())
    {
        OD_LOG_ERR("Cannot find requested highMap for a given tileset name=" + tileSetName);
        // We return the default tileset
        return mHighMaps.at(DEFAULT_TILESET_NAME);
    }

    return it->second;
}




bool ConfigManager::initVideoConfig(Ogre::Root& ogreRoot)
{
    // Also creates the config entry if it doesn't exist in config yet.
    std::string rendererName = getVideoValue(Config::RENDERER, std::string(), false);
    // Try the default OpenGL 3+ renderer first, if empty.
    // also I set  Separate Shader Objects here, this is ad-hoc solution so the game starts up
    // when no config.cfg file is present ( that should never happen , because currently the game checks
    // for the config.cfg and if no present it creates one )



    if (rendererName.empty()){
        rendererName = "OpenGL 3+ Rendering Subsystem";
        ogreRoot.getRenderSystemByName(rendererName)->setConfigOption("Separate Shader Objects", "true");
    }
    Ogre::RenderSystem* renderSystem = ogreRoot.getRenderSystemByName(rendererName);
    bool sameRenderer = true;
    if (renderSystem == nullptr)
    {
        const Ogre::RenderSystemList& renderers = ogreRoot.getAvailableRenderers();
        if(renderers.empty())
        {
            OD_LOG_ERR("No valid renderer found. Exiting...");
            return false;
        }
        renderSystem = *renderers.begin();
        OD_LOG_INF("No OpenGL renderer found. Using the first available: " + renderSystem->getName());
        sameRenderer = false;
    }

    ogreRoot.setRenderSystem(renderSystem);
    const Ogre::ConfigOptionMap& options = renderSystem->getConfigOptions();

    // If the renderer was changed, we need to reset the video options.
    if (sameRenderer == false)
    {

        mUserConfig[Config::Ctg::VIDEO].clear();

        for (std::pair<Ogre::String, Ogre::ConfigOption> option : options)
        {
            std::string optionName = option.first;
            Ogre::ConfigOption& values = option.second;
            // We don't store options that are immutable or empty
            if (values.immutable || values.possibleValues.empty())
                continue;

            setVideoValue(optionName, values.currentValue);
        }
    }
    else {
        std::vector<std::string> optionsToRemove;

        // The renderer system was initialized. Let's load its new option values.
        std::map<std::string, std::string>& mVideoUserConfig = mUserConfig[Config::Ctg::VIDEO];
        for (std::pair<std::string, std::string> setting : mVideoUserConfig)
        {
            // Check the option exists.
            if (options.find(setting.first) == options.end())
            {
                optionsToRemove.push_back(setting.first);
                continue;
            }

            // Check the desired option value exists.
            const Ogre::ConfigOption& values = options.find(setting.first)->second;
            bool valueIsPossible = false;
            for (std::string value : values.possibleValues)
            {
                if (setting.second == value)
                {
                    valueIsPossible = true;
                    break;
                }
            }
            if (!valueIsPossible)
            {
                // The video mode also sizes the window when running windowed, where it
                // need not be one of the render system's fullscreen modes. Dropping it
                // would silently fall back to the minimum window size, so keep the
                // user's value and simply don't push it to the render system.
                if (setting.first != Config::VIDEO_MODE)
                    optionsToRemove.push_back(setting.first);
                continue;
            }

            renderSystem->setConfigOption(setting.first, setting.second);
        }

        // Removes now invalid options from the video options.
        for (const std::string& option : optionsToRemove)
            mVideoUserConfig.erase(option);
    }
    

    return true;
}

void ConfigManager::loadKeeperVoices(const std::string& soundPath)
{
    std::vector<std::string> directories;
    std::string parentPath = soundPath + "Relative";
    if(!Helper::fillDirList(parentPath, directories, false))
    {
        OD_LOG_ERR("Error while loading sounds in directory=" + parentPath);
        return;
    }

    for(const std::string& directory : directories)
    {
        // We add the keeper voice
        OD_LOG_INF("Keeper voice found=" + directory);
        mKeeperVoices.push_back(directory);
    }

    if(mKeeperVoices.empty())
    {
        OD_LOG_ERR("No keeper voice found. Relative sounds will not work");
        return;
    }

    if(std::find(mKeeperVoices.begin(), mKeeperVoices.end(), ConfigManager::DEFAULT_KEEPER_VOICE) == mKeeperVoices.end())
    {
        OD_LOG_ERR("No default keeper voice found");
    }
}


void ConfigManager::loadDefaultValuesForUserConfig(void)
{
    setAudioValue("Dynamic Shadows" , "No");
    setAudioValue("Music Volume", "100");
    setVideoValue("Debug Layer", "Off");
    setVideoValue("FSAA",  "0");
    setVideoValue("Full Screen", "No");
    setVideoValue("Renderer",  "OpenGL 3+ Rendering Subsystem");
    setVideoValue("Reversed Z-Buffer", "No");
    setVideoValue("Separate Shader Objects", "Yes");
    setVideoValue("VSync", "Yes");
    setVideoValue("VSync Interval", "1");
    setVideoValue("Video Mode",	"1024 x 768");
    setVideoValue("sRGB Gamma Conversion", "No");
    setInputValue("Autoscroll",	"Yes");
    setInputValue("Keyboard Grab","Yes");
    setInputValue("Mouse Grab",	"Yes");
    setGameValue("KeeperVoice",	"Default");
    setGameValue("LightFactor",	"100");
    setGameValue("MinimapType",	"MiniMapDrawn");
    setGameValue("Nickname", "Player");
    setGameValue("UI Scale", "100");
    setGameValue("Blood Effects", "Yes");
}
