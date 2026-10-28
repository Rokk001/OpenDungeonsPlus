#include "creatureaction/CreatureActionHuntGhost.h"
#include <OgreBillboardChain.h>
#include <OgreParticleSystem.h>
/*
 *  Copyright (C) 2011-2017  OpenDungeons Team
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

#include "entities/Creature.h"
#include "entities/GhostEntity.h"
#include "creaturemood/CreatureMoodFee.h"
#include "creaturemood/CreatureMoodRested.h"
#include "entities/CreatureProgression.h"

#include "ODApplication.h"
#include "creatureaction/CreatureAction.h"
#include "creatureaction/CreatureActionClaimGroundTile.h"
#include "creatureaction/CreatureActionClaimWallTile.h"
#include "creatureaction/CreatureActionDigTile.h"
#include "creatureaction/CreatureActionFight.h"
#include "creatureaction/CreatureActionFightFriendly.h"
#include "creatureaction/CreatureActionFindHome.h"
#include "creatureaction/CreatureActionFlee.h"
#include "creatureaction/CreatureActionGetFee.h"
#include "creatureaction/CreatureActionGoCallToWar.h"
#include "creatureaction/CreatureActionGoDefendHeart.h"
#include "creatureaction/CreatureActionGrabEntity.h"
#include "creatureaction/CreatureActionLeaveDungeon.h"
#include "creatureaction/CreatureActionParkToTile.h"
#include "creatureaction/CreatureActionPossessed.h"
#include "creatureaction/CreatureActionReloadTrap.h"
#include "creatureaction/CreatureActionSearchDirtToClean.h"
#include "creatureaction/CreatureActionSearchDrink.h"
#include "creatureaction/CreatureActionSearchSpa.h"
#include "creatureaction/CreatureActionSearchEntityToCarry.h"
#include "creatureaction/CreatureActionSearchFood.h"
#include "creatureaction/CreatureActionSearchGroundTileToClaim.h"
#include "creatureaction/CreatureActionSearchJob.h"
#include "creatureaction/CreatureActionSearchToilet.h"
#include "creatureaction/CreatureActionSearchTileToDig.h"
#include "creatureaction/CreatureActionSearchWallTileToClaim.h"
#include "creatureaction/CreatureActionSleep.h"
#include "creatureaction/CreatureActionStealFreeGold.h"
#include "creatureaction/CreatureActionTunnel.h"
#include "creatureaction/CreatureActionUseRoom.h"
#include "creatureaction/CreatureActionUseToilet.h"
#include "creatureaction/CreatureActionVomit.h"
#include "creatureaction/CreatureActionWalkToTile.h"
#include "creaturebehaviour/CreatureBehaviour.h"
#include "creaturebehaviour/CreatureBehaviourAttackEnemy.h"
#include "creaturebehaviour/CreatureBehaviourFleeWhenWeak.h"
#include "creaturebehaviour/CreatureBehaviourFleeWhenOutmatched.h"
#include "creatureeffect/CreatureEffect.h"
#include "creatureeffect/CreatureEffectDigTile.h"
#include "creatureeffect/CreatureEffectManager.h"
#include "creatureeffect/CreatureEffectSlap.h"
#include "creaturemood/CreatureMood.h"
#include "creaturemood/CreatureMoodManager.h"
#include "creaturemood/CreatureMoodOutOfWork.h"
#include "creatureskill/CreatureSkill.h"
#include "creatureskill/CreatureSkillManager.h"
#include "creatureskill/CreatureSkillMeleeFight.h"


#include "entities/ChickenEntity.h"
#include "entities/CreatureDefinition.h"
#include "entities/MissileObject.h"
#include "entities/CreatureMoodValues.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "entities/DirtPileEntity.h"
#include "entities/TreasuryObject.h"
#include "entities/Weapon.h"
#include "entities/ItemEffects.h"
#include "creatureaction/CreatureActionPickupItem.h"
#include "creatureaction/CreatureActionStealItem.h"
#include "game/CreatureMerchantAI.h"
#include "entities/ItemInstance.h"



#include "game/CreatureAppearance.h"
#include "game/CreatureRelationships.h"
#include "game/Player.h"
#include "game/ItemDrops.h"
#include "game/Skill.h"
#include "game/SkillType.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/LevelScript.h"
#include "gamemap/LevelScriptRunner.h"
#include "gamemap/SandboxMode.h"
#include "gamemap/Pathfinding.h"
#include "gamemap/RoomObjectNavigation.h"
#include "gamemap/RoomObjectBounds.h"
#include "giftboxes/GiftBoxSkill.h"

#include "modes/GameEditorModeConsole.h"
#include "modes/GameMode.h"
#include "modes/ModeManager.h"

#include "network/CosmeticEvent.h"
#include "network/ODClient.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "render/CreatureOverlayStatus.h"
#include "render/CreatureAppearancePicture.h"
#include "render/CreaturePortrait.h"
#include "render/Gui.h"
#include "render/ODFrameListener.h"
#include "render/CreatureReactions.h"
#include "render/DungeonbookAppearanceConfig.h"
#include "render/DungeonbookQuirks.h"
#include "render/PortraitCatalogRegistry.h"
#include "render/RenderManager.h"
#include "render/RoomAmbience.h"
#include "render/SocialWindow.h"
#include "social/CreaturePosts.h"
#include "social/PostLog.h"
#include "social/SocialGenerator.h"
#include "social/SocialProfileCache.h"
#include "social/SocialRng.h"
#include "rooms/RoomCrypt.h"
#include "rooms/RoomDormitory.h"
#include "rooms/RoomInfirmary.h"
#include "rooms/RoomPrison.h"
#include "rooms/RoomArena.h"
#include "rooms/RoomSpa.h"
#include "rooms/RoomToilet.h"
#include "sound/SoundEffectsManager.h"
#include "spells/Spell.h"
#include "spells/SpellType.h"
#include "traps/Trap.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"
#include "utils/ResourceManager.h"

#include <CEGUI/Event.h>
#include <CEGUI/Image.h>
#include <CEGUI/ImageManager.h>
#include <CEGUI/System.h>
#include <CEGUI/UDim.h>
#include <CEGUI/Vector.h>
#include <CEGUI/WindowManager.h>
#include <CEGUI/Window.h>
#include <CEGUI/widgets/FrameWindow.h>
#include <CEGUI/widgets/ProgressBar.h>
#include <CEGUI/widgets/PushButton.h>

#include <OgreQuaternion.h>
#include <Ogre.h>
#include <Ogre.h>

#include <cmath>
#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <iomanip>
#include <limits>
#include <sstream>
#include <utility>



//! \brief Number of hand slots visible when the viewing seat does not own the creature.
static const std::size_t VISIBLE_ITEM_HAND_SLOTS = 2;

//! \brief Returns a slot's catalogue name and quality, with a dash for an empty slot.
static std::string getItemSlotDisplayText(const ItemInstance* item, const GameMap* gameMap)
{
    if(item == nullptr)
        return "-";

    if(!item->mPotionId.empty())
        return item->getDisplayName(gameMap);
    const std::string description = item->describe(gameMap);
    return description.substr(0, description.find('\n')) + " [" + qualityName(item->mQuality) + "]";
}

static const Ogre::Real CANNON_MISSILE_HEIGHT = 0.3;

//! \brief Squared length below which a possession move direction counts as no movement
static const Ogre::Real POSSESSION_MIN_DIRECTION_SQUARED_LENGTH = 0.0001f;
//! \brief Squared length below which a possession aim direction counts as no aim
static const Ogre::Real POSSESSION_MIN_AIM_SQUARED_LENGTH = 0.0001f;
//! \brief Pit mood points lost per second when the room config has no PitMoodDecay
static const double DEFAULT_PIT_MOOD_DECAY_PER_SECOND = 3.0;
//! \brief Largest pit mood (positive or negative) when the room config has no PitMoodMax
static const double DEFAULT_PIT_MOOD_MAX = 1500.0;
//! \brief Radius in tiles of the hated company check when the room config has no HatedCompanyRadius
static const double DEFAULT_HATED_COMPANY_RADIUS = 5.0;
//! \brief Squared distance in tiles (3 tiles) up to which a creature in a possession group stays where it is instead of walking to the leader
static const int POSSESSION_GROUP_MAX_SQUARED_DISTANCE = 9;
//! \brief Distance in tiles below which a target is too close for the aim direction check of a possession skill
static const Ogre::Real POSSESSION_AIM_MIN_DISTANCE = 0.5;

// Target selection by combat class: the distance to an enemy support creature is multiplied by this
// factor for blitzers and flankers, so they prefer it over closer enemies
static const double COMBAT_CLASS_SUPPORT_TARGET_FACTOR = 0.5;

//! \brief Returns the factor applied to the squared distance of a potential target. Lower means preferred.
//! Blockers and support creatures attack the nearest enemy. Blitzers and flankers prefer enemy support creatures.
static double getTargetDistanceFactor(const Creature& attacker, const GameEntity& target)
{
    if(target.getObjectType() != GameEntityType::creature)
        return 1.0;

    const CreatureDefinition::CombatClass attackerClass = attacker.getDefinition()->getCombatClass();
    if((attackerClass != CreatureDefinition::CombatBlitzer) && (attackerClass != CreatureDefinition::CombatFlanker))
        return 1.0;

    const Creature& targetCreature = static_cast<const Creature&>(target);
    if(targetCreature.getDefinition()->isWorker())
        return 1.0;

    if(targetCreature.getDefinition()->getCombatClass() == CreatureDefinition::CombatSupport)
        return COMBAT_CLASS_SUPPORT_TARGET_FACTOR;

    return 1.0;
}

namespace
{
//! \brief Records server-side script events and exact death observations.
void recordScriptEvent(const Creature& creature, const std::string& eventName);

//! Turns between two tries to assign a missing appearance
const uint32_t APPEARANCE_RETRY_TURNS = 200;
//! Turns between two repeats of the bed status of a creature without a bed (cosmetic events)
const int64_t BED_STATUS_REPEAT_TURNS = 200;
//! Length in seconds of the Jump clip of the creature skeletons
const double JUMP_CLIP_SECONDS = 1.4;

//! \brief Server side registry of the whole-image catalogs used to assign the Dungeonbook appearance.
//! Configured once from config/dungeonbook-appearance.cfg; messages are logged once.
PortraitCatalogRegistry& getAppearanceRegistry()
{
    static PortraitCatalogRegistry registry;
    static bool initialized = false;
    if(!initialized)
    {
        initialized = true;
        std::string path = ConfigManager::getSingleton().getConfigPath();
        if(!path.empty() && (path[path.size() - 1] != '/') && (path[path.size() - 1] != '\\'))
            path += "/";

        DungeonbookAppearanceConfig config;
        config.loadFromFile(path + "dungeonbook-appearance.cfg");
        const std::vector<std::string>& warnings = config.getWarnings();
        for(std::vector<std::string>::const_iterator it = warnings.begin(); it != warnings.end(); ++it)
        {
            OD_LOG_WRN("Dungeonbook appearance: " + *it);
        }

        std::string root = config.getAssetRoot();
        if(root.empty())
            root = "materials/portraits/whole";

        bool isAbsolute = (root.size() > 1) && ((root[1] == ':') || (root[0] == '/') || (root[0] == '\\'));
        if(!isAbsolute)
            root = ResourceManager::getSingleton().getGameDataPath() + root;

        registry.setAssetRoot(root);
    }
    return registry;
}

uint32_t getAppearanceRandom(uint32_t min, uint32_t max)
{
    return Random::Uint(min, max);
}

//! \brief Name of the token that starts the saved skill state of a creature in the creature stream.
static const std::string SKILL_BUILD_MARKER = "SkillTree";
//! \brief Highest personal skill seed (the seed is a random number from 1 to this value).
static const uint32_t SKILL_SEED_MAX = 0xFFFFFFFFu;
//! \brief Sort positions of the skills of the skill tree in the skill list of a creature.
static const uint32_t TREE_SKILL_PRIORITY_TIER_FOUR = 0;
static const uint32_t TREE_SKILL_PRIORITY_HEAL = 1;
static const uint32_t TREE_SKILL_PRIORITY_BUFF = 2;
static const uint32_t TREE_SKILL_PRIORITY_DEBUFF = 3;
static const uint32_t TREE_SKILL_PRIORITY_DAMAGE = 4;
//! \brief Prefixes of the kind tokens of the skill table that decide the sort position of a skill.
static const std::string TREE_KIND_HEAL = "HEAL_";
static const std::string TREE_KIND_BUFF = "BUFF_SELF_";
static const std::string TREE_KIND_AURA = "AURA_ALLY_";
static const std::string TREE_KIND_STRIKE = "STRIKE";
static const std::string TREE_KIND_DEBUFF = "DEBUFF_";
//! \brief Text of a type key that means the type has no such skill entry.
static const std::string SKILL_KEY_NONE = "none";
//! \brief Names of the effects whose strength, speed or defense factor stacks with other sources.
static const std::string EFFECT_NAME_STRENGTH = "StrengthChange";
static const std::string EFFECT_NAME_SPEED = "SpeedChange";
static const std::string EFFECT_NAME_DEFENSE = "Defense";

//! \brief Returns the text of a skill key of a creature type, empty when it is "none".
static std::string skillTextOrEmpty(const std::string& text)
{
    if(text == SKILL_KEY_NONE)
        return std::string();
    return text;
}

//! \brief Returns the key under which a running strength, speed or defense effect is refreshed instead of added: the
//! id of its source (skill or spell), else its particle script (which names the spell).
static std::string effectRefreshKey(const CreatureEffect& effect)
{
    if(!effect.getSourceId().empty())
        return effect.getSourceId();
    return effect.getParticleEffectScript();
}

//! \brief True for the effects whose factor stacks with other effects (strength, speed and defense).
static bool isStackingEffect(const CreatureEffect& effect)
{
    const std::string& name = effect.getEffectName();
    return name == EFFECT_NAME_STRENGTH || name == EFFECT_NAME_SPEED || name == EFFECT_NAME_DEFENSE ||
        name == "Bleed" || name == "Potion";
}
}

//! \brief Lowest ratio between the speed of the tile under a creature and its ground speed (see getTileSpeedRatio)
static const double TILE_SPEED_RATIO_MIN = 0.2;

//! \brief Highest ratio between the speed of the tile under a creature and its ground speed (see getTileSpeedRatio)
static const double TILE_SPEED_RATIO_MAX = 4.0;

//! \brief Most the shown tile speed ratio of the walk clips changes per second (see updateClientPose)
static const double TILE_SPEED_RATIO_MAX_CHANGE_PER_SECOND = 4.0;

//! \brief Health stages (see mOverlayHealthValue) from which a standing creature breathes slower, from the worst to the lightest
static const uint32_t IDLE_BREATH_STAGE_HEAVY = 6;
static const uint32_t IDLE_BREATH_STAGE_MEDIUM = 5;
static const uint32_t IDLE_BREATH_STAGE_LIGHT = 4;

//! \brief Speed factors of the idle clip of a hurt creature in the stages IDLE_BREATH_STAGE_HEAVY, _MEDIUM and _LIGHT
static const double IDLE_BREATH_FACTOR_HEAVY = 0.78;
static const double IDLE_BREATH_FACTOR_MEDIUM = 0.85;
static const double IDLE_BREATH_FACTOR_LIGHT = 0.92;
//! \brief Tolerance that keeps a health border that falls exactly on a stage in the lower stage (see isLowHealthWalkStage)
static const double HEALTH_STAGE_ROUNDING_TOLERANCE = 0.000001;
//! \brief Number of closest targets for which a path is tried when a creature looks for a destination
static const uint32_t MAX_PATH_CHECK_TARGET_TRIES = 5;

const int32_t Creature::NB_TURNS_BEFORE_CHECKING_TASK = 15;
const uint32_t Creature::NB_OVERLAY_HEALTH_VALUES = 8;
//! \brief The mana ring is an atlas of 64 frames (0 empty .. 63 full): steps 0..63 of the current/max mana share
const uint32_t Creature::MANA_RING_STEPS = 63;
//! \brief Label in front of the current mana in a creature save, so it cannot be mistaken for the appearance token
static const std::string MANA_SAVE_LABEL = "Mana=";
static const std::string MERCHANT_MOOD_SAVE_LABEL = "MerchantMood=";
static const std::string GOLD_REMAINDER_SAVE_LABEL = "GoldRemainder=";
//! \brief Tag that opens the optional block of the needs (urge and creature dirt) at the end of a saved creature.
static const std::string NEEDS_SAVE_OPEN = "[Needs]";
//! \brief Tag that closes the block of the needs.
static const std::string NEEDS_SAVE_CLOSE = "[/Needs]";
//! \brief Tag that opens the optional block of the thirst state (thirst, tavern mood, drunkenness, hangover) at the
//! end of a saved creature, after the needs block. The blocks are read in any order.
static const std::string THIRST_SAVE_OPEN = "[Thirst]";
static const std::string CORPSE_CARRIER_SAVE_LABEL = "CorpseCarrier=";
//! \brief Tag that closes the block of the thirst state.
static const std::string THIRST_SAVE_CLOSE = "[/Thirst]";
//! \brief Tag that opens the optional block with the turns until the next leisure visit to a tavern (after the thirst block).
static const std::string TAVERN_COOLDOWN_SAVE_OPEN = "[TavernCooldown]";
//! \brief Tag that closes the block of the tavern cooldown.
static const std::string TAVERN_COOLDOWN_SAVE_CLOSE = "[/TavernCooldown]";
//! \brief Tag that opens the optional block of the lava spa state (spa mood, relaxation turns, tiles that still get
//! mud) at the end of a saved creature, after the thirst block. The blocks are read in any order.
static const std::string SPA_SAVE_OPEN = "[Spa]";
//! \brief Tag that closes the block of the lava spa state.
static const std::string SPA_SAVE_CLOSE = "[/Spa]";
//! \brief Factor of the parabola that gives the height of a jump: 4 x p x (1 - p) is 1 at the apex.
static const Ogre::Real JUMP_ARC_FACTOR = 4.0f;
//! \brief The highest value of the thirst and of the drunkenness (both go from 0 to this value).
static const double THIRST_STATE_MAX = 100.0;
//! \brief The highest value of the urge and of the creature dirt (both go from 0 to this value).
static const double NEED_MAX = 100.0;
//! \brief Divisor that turns the creature dirt (0 - NEED_MAX) into the share (0 - 1) of the trail dirt it leaves.
static const double CREATURE_DIRT_SHARE_DIVISOR = NEED_MAX;

//! \brief Returns the mana ring step 0 .. Creature::MANA_RING_STEPS for a mana value: floor(mana / maxMana x steps).
//! \param mana The current mana.
//! \param maxMana The size of the mana pool; a pool of 0 or less counts as empty.
static uint32_t manaRingStep(double mana, double maxMana)
{
    if(maxMana <= 0.0)
        return 0;

    const double share = std::max(0.0, std::min(1.0, mana / maxMana));
    return static_cast<uint32_t>(share * static_cast<double>(Creature::MANA_RING_STEPS));
}
const std::string Creature::POSSESSION_AURA_SCRIPT = "SpellCreaturePossess";
const double Creature::WOUNDED_DRAG_LAY_TURNS_DEFAULT = 12.0;
const double Creature::WOUNDED_CARRY_ENEMY_RADIUS_DEFAULT = 6.0;
const double Creature::WOUNDED_CARRY_MAX_TURNS_DEFAULT = 400.0;
const double Creature::WOUNDED_DRAG_MAX_DISTANCE_DEFAULT = 3.5;
const double Creature::WOUNDED_DRAG_GAP_DEFAULT = 0.9;
const double Creature::WOUNDED_DRAG_FOLLOW_SPEED_FACTOR_DEFAULT = 1.3;
const double Creature::WOUNDED_DRAG_WORKER_SPEED_FACTOR_DEFAULT = 0.6;
const double Creature::WOUNDED_CARRY_RADIUS_DEFAULT = 8.0;
const double Creature::WOUNDED_CARRY_PRIORITY_DEFAULT = 1.0;
const double Creature::WOUNDED_CARRY_HP_PERCENT_DEFAULT = 35.0;
const double Creature::WOUNDED_CARRY_TEMP_KO_DEFAULT = 1.0;
const double Creature::WOUNDED_CARRY_COOLDOWN_DEFAULT = 150.0;
const double Creature::PERCENT_FACTOR = 100.0;

namespace
{
//! \brief Friends are the creatures of the seat with an affinity above this value
const uint32_t PROFILE_FRIEND_MIN_AFFINITY = 600;
//! \brief The foe is the creature with an affinity below this value
const uint32_t PROFILE_FOE_MAX_AFFINITY = 150;
const uint32_t PROFILE_MAX_FRIENDS = 2;
//! \brief The handle of the card gets a number from PROFILE_HANDLE_MIN_NUMBER to PROFILE_HANDLE_MIN_NUMBER + PROFILE_HANDLE_NUMBER_COUNT - 1
const int PROFILE_HANDLE_MIN_NUMBER = 10;
const int PROFILE_HANDLE_NUMBER_COUNT = 90;
//! \brief Number of likes and of dislikes in a profile
const std::size_t PROFILE_LIST_SIZE = 2;

typedef std::pair<uint32_t, std::string> ProfileAffinity;

bool isHigherAffinity(const ProfileAffinity& a, const ProfileAffinity& b)
{
    if(a.first != b.first)
        return a.first > b.first;

    return a.second < b.second;
}

//! \brief Picks the friends and the foe of a creature among the creatures of a seat (see
//! SocialGenerator::affinity). Only computed when the creature card is refreshed.
void findFriendsAndFoe(const std::string& name, const std::vector<Creature*>& mates,
    std::vector<std::string>& friends, std::string& foe)
{
    std::vector<ProfileAffinity> affinities;
    for(Creature* mate : mates)
    {
        if(mate->getName() == name)
            continue;

        affinities.push_back(ProfileAffinity(social::SocialGenerator::affinity(name, mate->getName()), mate->getName()));
    }
    std::sort(affinities.begin(), affinities.end(), isHigherAffinity);

    for(const ProfileAffinity& affinity : affinities)
    {
        if((affinity.first <= PROFILE_FRIEND_MIN_AFFINITY) || (friends.size() >= PROFILE_MAX_FRIENDS))
            break;

        friends.push_back(affinity.second);
    }
    if(!affinities.empty() && (affinities.back().first < PROFILE_FOE_MAX_AFFINITY))
        foe = affinities.back().second;
}

//! \brief State name used to look up the mood line of the creature (see social-texts.cfg)
std::string getProfileMoodState(uint32_t moodBits, CreatureMoodLevel moodLevel)
{
    if((moodBits & CreatureMoodValues::KoTemp) != 0)
        return "KoTemp";
    if((moodBits & CreatureMoodValues::InJail) != 0)
        return "InJail";
    if((moodBits & CreatureMoodValues::LeaveDungeon) != 0)
        return "LeaveDungeon";
    if((moodBits & CreatureMoodValues::GetFee) != 0)
        return "GetFee";
    if((moodBits & CreatureMoodValues::Hungry) != 0)
        return "Hungry";
    if((moodBits & CreatureMoodValues::Tired) != 0)
        return "Tired";

    switch(moodLevel)
    {
        case CreatureMoodLevel::Happy:
            return "Happy";
        case CreatureMoodLevel::Neutral:
            return "Neutral";
        case CreatureMoodLevel::Upset:
            return "Upset";
        case CreatureMoodLevel::Angry:
            return "Angry";
        case CreatureMoodLevel::Furious:
            return "Furious";
        default:
            return "Unknown";
    }
}

//! \brief A made-up handle derived from the profile name ("Mold the Damp" -> "@mold47"), so that the internal
//! creature name never shows on the card
std::string makeProfileHandle(const social::CreatureProfile& profile)
{
    std::string handle = "@";
    for(char c : profile.mFirstName)
    {
        if(((c >= 'a') && (c <= 'z')) || ((c >= '0') && (c <= '9')))
            handle += c;
        else if((c >= 'A') && (c <= 'Z'))
            handle += static_cast<char>(c - 'A' + 'a');
    }
    handle += Helper::toString(PROFILE_HANDLE_MIN_NUMBER +
        static_cast<int>(social::fnv1a64(profile.mCreatureName + "|handle") % PROFILE_HANDLE_NUMBER_COUNT));
    return handle;
}

//! \brief Profile name of the creature with the given internal name, empty if there is no such creature
std::string getProfileNameOfCreature(GameMap* gameMap, const std::string& creatureName)
{
    Creature* creature = gameMap->getCreature(creatureName);
    if(creature == nullptr)
        return std::string();

    const CreatureDefinition* definition = creature->getDefinition();
    return social::SocialProfileCache::getSingleton().getProfile(creatureName, definition->getClassName(),
        definition->isWorker()).getFullName();
}

//! \brief The relationships of a creature as the client knows them (tiers sent by the server).
struct ProfileRelations
{
    ProfileRelations() :
        mHasPartner(false),
        mHasHated(false),
        mHasNemesis(false)
    {
    }

    //! Friends, best friends and partners, the strongest first
    std::vector<std::string> mClose;
    //! Hated creatures and nemeses, the worst first
    std::vector<std::string> mAgainst;
    //! Shown text per creature name, e.g. "Name (best friend)"
    std::map<std::string, std::string> mTierText;
    bool mHasPartner;
    bool mHasHated;
    bool mHasNemesis;
};

//! \brief Orders two (creature name, relationship value) pairs: the stronger value first, equal values by name.
bool isStrongerRelationship(const std::pair<std::string, int32_t>& a, const std::pair<std::string, int32_t>& b)
{
    if(a.second != b.second)
        return a.second > b.second;

    return a.first < b.first;
}

//! \brief Fills the relations of a creature from the tiers of the client: who is close to it (friends, best friends,
//! partner), who is against it (hated, nemesis) and the text that is shown per creature.
//! \param gameMap The map the creatures are looked up in
//! \param relationships The relationship table of the map
//! \param name Name of the creature the profile belongs to
//! \param result Receives the lists and texts
void collectProfileRelations(GameMap* gameMap, CreatureRelationships& relationships, const std::string& name,
    ProfileRelations& result)
{
    std::vector<std::pair<std::string, int32_t> > partners;
    relationships.getPartners(name, partners);
    std::sort(partners.begin(), partners.end(), isStrongerRelationship);

    for(const std::pair<std::string, int32_t>& partner : partners)
    {
        std::string partnerName = getProfileNameOfCreature(gameMap, partner.first);
        if(partnerName.empty())
            continue;

        RelationshipTier tier = relationships.tierOf(name, partner.first, true);
        const char* label = nullptr;
        switch(tier)
        {
            case RelationshipTier::lovers:
                label = "partner";
                result.mHasPartner = true;
                result.mClose.push_back(partner.first);
                break;
            case RelationshipTier::bestFriends:
                label = "best friend";
                result.mClose.push_back(partner.first);
                break;
            case RelationshipTier::friends:
                label = "friend";
                result.mClose.push_back(partner.first);
                break;
            case RelationshipTier::hated:
                label = "dislikes";
                result.mHasHated = true;
                result.mAgainst.insert(result.mAgainst.begin(), partner.first);
                break;
            case RelationshipTier::nemesis:
                label = "nemesis";
                result.mHasNemesis = true;
                result.mAgainst.insert(result.mAgainst.begin(), partner.first);
                break;
            default:
                break;
        }
        if(label != nullptr)
            result.mTierText[partner.first] = partnerName + " (" + label + ")";
    }
}

std::string joinProfileList(const std::vector<std::string>& values)
{
    std::string result;
    for(const std::string& value : values)
    {
        if(value.empty())
            continue;

        if(!result.empty())
            result += ", ";
        result += value;
    }
    return result;
}
}

CreatureParticleEffect::CreatureParticleEffect(Creature& creature, const std::string& name, const std::string& script, int32_t nbTurnsEffect,
        CreatureEffect* effect) :
    EntityParticleEffect(name, script, nbTurnsEffect),
    mEffect(effect),
    mCreature(creature)
{
    if(mEffect == nullptr)
    {
        OD_LOG_ERR("null effect on creature=" + mCreature.getName() + ", name=" + name + ", script=" + script);
        return;
    }

    mEffect->startEffect(mCreature);
}

CreatureParticleEffect::~CreatureParticleEffect()
{
    if(mEffect != nullptr)
    {
        // We don't call release here as the
        // creature object is already partially destroyed.
        // mEffect->releaseEffect(mCreature);
        delete mEffect;
    }
    
}

//! \brief Creates a living creature with inactive corpse timers and no worker carrier.
Creature::Creature(GameMap* gameMap, const CreatureDefinition* definition, Seat* seat, Ogre::Vector3 position) :

    MovableGameEntity        (gameMap),
    parkingBit               (false),
    parkedBit                (false),
    mPhysicalDefense         (3.0),
    mMagicalDefense          (1.5),
    mElementDefense          (0.0),
    mModifierStrength        (1.0),
    mWeaponL                 (nullptr),
    mWeaponR                 (nullptr),
    mHomeTile                (nullptr),
    mDefinition              (definition),
    mHasVisualDebuggingEntities (false),
    mWakefulness             (100.0),
    mHunger                  (0.0),
    mUrge                    (0.0),
    mCreatureDirt            (0.0),
    mLevel                   (1),
    mHp                      (10.0),
    mMaxHP                   (10.0),
    mExp                     (0.0),
    mGroundSpeed             (1.0),
    mWaterSpeed              (0.0),
    mLavaSpeed               (0.0),
    mDigRate                 (0.0),
    mClaimRate               (0.0),
    mDeathCounter            (0),
    mCorpseTurns             (0.0),
    mDecayTurns              (-1.0),
    mIsCarried               (false),
    mMana                    (0.0),
    mManaFromSave            (false),
    mManaRingStepNotified    (MANA_RING_STEPS),
    mChampionTurns           (0),
    mJobCooldown             (0),
    mGoldFee                 (0),
    mGoldCarried             (0),
    mGoldRemainder           (0.0),
    mGoldCarriedNotified     (0),
    mGoldCarriedCosmeticNotified(0),
    mBedNotified             (-1),
    mSkillTypeDropDeath      (SkillType::nullSkillType),
    mWeaponDropDeath         ("none"),
    mStatsWindow             (nullptr),
    mNbTurnsWithoutBattle    (0),
    mDirtKoThisFight         (false),
    mFoughtSinceFightEnd     (false),
    mCasinoMood              (0.0),
    mInfirmaryMood           (0.0),
    mInfirmaryMoodTurns      (0.0),
    mThirst                  (0.0),
    mTavernMood              (0.0),
    mTavernMoodTurns         (0.0),
    mDrunk                   (0.0),
    mVomited                 (false),
    mHangoverTurns           (0.0),
    mTavernCooldownTurns     (0),
    mHangoverPending         (false),
    mSpaMood                 (0.0),
    mRelaxTurns              (0.0),
    mSpaMudTilesLeft         (0),
    mSpaBathing              (false),
    mJumpFrom                (Ogre::Vector3::ZERO),
    mJumpTo                  (Ogre::Vector3::ZERO),
    mJumpTurns               (0),
    mJumpTurnsLeft           (0),
    mJumpElapsed             (0.0f),
    mCarriedEntity           (nullptr),
    mClientCarrying          (false),
    mMoodCooldownTurns       (0),
    mMoodValue               (gameMap->isServerGameMap() ? CreatureMoodLevel::Neutral : CreatureMoodLevel::Unknown),
    mMoodPoints              (0),
    mPrayerRelief            (0),
    mSpecialMood             (0),
    mNbTurnFurious           (-1),
    mOverlayHealthValue      (0),
    mOverlayMoodValue        (CreatureMoodValues::Nothing),
    mClientTileSpeedRatio    (-1.0),
    mOverlayStatus           (nullptr),
    mNeedFireRefresh         (false),
    mDropCooldown            (0),
    mSpeedModifier           (1.0),
    mKoTurnCounter           (0),
    mSeatPrison              (nullptr),
    mNbTurnsTorture          (0),
    mNbTurnsPrison           (0),
    mActiveSlapsCount        (0),
    mNbTurnsInHand           (0),
    mIsInHand                (false),
    mIsBeingDragged          (false),
    mDragDirtFactor          (1.0),
    mWoundedCarryNextTurn    (0),
    mNbTurnsOutOfWork        (0),
    mNbTurnsTortureMood      (0),
    mNbTurnsRested           (0),
    mTorturedThisTurn        (false),
    mRestedThisTurn          (false),
    mNbTurnsHatedCompany     (0),
    mPitMood                 (0.0),
    mIsHexenHen               (false),
    mHexenHenMeshShown        (false)
{
    //TODO: This should be set in initialiser list in parent classes
    setSeat(seat);
    mPosition = position;
    setMeshName(definition->getMeshName());
    setName(getGameMap()->nextUniqueNameCreature(definition->getClassName()));

    // First spawn: the Dungeonbook appearance is chosen once and never changed afterwards
    if(getIsOnServerMap())
        assignAppearance(true);

    mMaxHP = mDefinition->getMinHp();
    setHP(mMaxHP);

    mGroundSpeed = mDefinition->getMoveSpeedGround();
    mWaterSpeed = mDefinition->getMoveSpeedWater();
    mLavaSpeed = mDefinition->getMoveSpeedLava();

    mDigRate = mDefinition->getDigRate();
    mClaimRate = mDefinition->getClaimRate();

    // Fighting stats
    mPhysicalDefense = mDefinition->getPhysicalDefense();
    mMagicalDefense = mDefinition->getMagicalDefense();
    mElementDefense = mDefinition->getElementDefense();

    if(mDefinition->getWeaponSpawnL().compare("none") != 0)
        mWeaponL = gameMap->getWeapon(mDefinition->getWeaponSpawnL());

    if(mDefinition->getWeaponSpawnR().compare("none") != 0)
        mWeaponR = gameMap->getWeapon(mDefinition->getWeaponSpawnR());

    setupDefinition(*gameMap, *ConfigManager::getSingleton().getCreatureDefinitionDefaultWorker());

    // A new creature spawns with a full mana pool
    mMana = getMaxMana();

    if(!getIsOnServerMap())
    {
        registerObserver(GameEditorModeConsole::getSingleton());
    }
    
}

//! \brief Initializes a creature for loading, with legacy corpse phase defaults.
Creature::Creature(GameMap* gameMap) :
    MovableGameEntity        (gameMap),
    parkingBit               (false),
    parkedBit                (false),
    mPhysicalDefense         (3.0),
    mMagicalDefense          (1.5),
    mElementDefense          (0.0),
    mModifierStrength        (1.0),
    mWeaponL                 (nullptr),
    mWeaponR                 (nullptr),
    mHomeTile                (nullptr),
    mDefinition              (nullptr),
    mHasVisualDebuggingEntities (false),
    mWakefulness             (100.0),
    mHunger                  (0.0),
    mUrge                    (0.0),
    mCreatureDirt            (0.0),
    mLevel                   (1),
    mHp                      (10.0),
    mMaxHP                   (10.0),
    mExp                     (0.0),
    mGroundSpeed             (1.0),
    mWaterSpeed              (0.0),
    mLavaSpeed               (0.0),
    mDigRate                 (0.0),
    mClaimRate               (0.0),
    mDeathCounter            (0),
    mCorpseTurns             (0.0),
    mDecayTurns              (-1.0),
    mIsCarried               (false),
    mMana                    (0.0),
    mManaFromSave            (false),
    mManaRingStepNotified    (MANA_RING_STEPS),
    mChampionTurns           (0),
    mJobCooldown             (0),
    mGoldFee                 (0),
    mGoldCarried             (0),
    mGoldRemainder           (0.0),
    mGoldCarriedNotified     (0),
    mGoldCarriedCosmeticNotified(0),
    mBedNotified             (-1),
    mSkillTypeDropDeath      (SkillType::nullSkillType),
    mWeaponDropDeath         ("none"),
    mStatsWindow             (nullptr),
    mNbTurnsWithoutBattle    (0),
    mDirtKoThisFight         (false),
    mFoughtSinceFightEnd     (false),
    mCasinoMood              (0.0),
    mInfirmaryMood           (0.0),
    mInfirmaryMoodTurns      (0.0),
    mThirst                  (0.0),
    mTavernMood              (0.0),
    mTavernMoodTurns         (0.0),
    mDrunk                   (0.0),
    mVomited                 (false),
    mHangoverTurns           (0.0),
    mTavernCooldownTurns     (0),
    mHangoverPending         (false),
    mSpaMood                 (0.0),
    mRelaxTurns              (0.0),
    mSpaMudTilesLeft         (0),
    mSpaBathing              (false),
    mJumpFrom                (Ogre::Vector3::ZERO),
    mJumpTo                  (Ogre::Vector3::ZERO),
    mJumpTurns               (0),
    mJumpTurnsLeft           (0),
    mJumpElapsed             (0.0f),
    mCarriedEntity           (nullptr),
    mClientCarrying          (false),
    mMoodCooldownTurns       (0),
    mMoodValue               (gameMap->isServerGameMap() ? CreatureMoodLevel::Neutral : CreatureMoodLevel::Unknown),
    mMoodPoints              (0),
    mPrayerRelief            (0),
    mSpecialMood             (0),
    mNbTurnFurious           (-1),
    mOverlayHealthValue      (0),
    mOverlayMoodValue        (0),
    mClientTileSpeedRatio    (-1.0),
    mOverlayStatus           (nullptr),
    mNeedFireRefresh         (false),
    mDropCooldown            (0),
    mSpeedModifier           (1.0),
    mKoTurnCounter           (0),
    mSeatPrison              (nullptr),
    mNbTurnsTorture          (0),
    mNbTurnsPrison           (0),
    mActiveSlapsCount        (0),
    mNbTurnsInHand           (0),
    mIsInHand                (false),
    mIsBeingDragged          (false),
    mDragDirtFactor          (1.0),
    mWoundedCarryNextTurn    (0),
    mNbTurnsOutOfWork        (0),
    mNbTurnsTortureMood      (0),
    mNbTurnsRested           (0),
    mTorturedThisTurn        (false),
    mRestedThisTurn          (false),
    mNbTurnsHatedCompany     (0),
    mPitMood                 (0.0),
    mIsHexenHen               (false),
    mHexenHenMeshShown        (false)
{
    if(!getIsOnServerMap())
    {
        registerObserver(GameEditorModeConsole::getSingleton());
    }
}

//! \brief Frees the active skills made from the skill tree and, on a client, clears the highlighted creature pointer.
Creature::~Creature()
{
    interruptGhostHunt();
    clearGhostHuntVisuals();
    if(getIsOnServerMap())
        unregisterHeldEpics();
    // The active skills made from the skill tree belong to the creature
    for(CreatureSkill* skill : mTreeSkills)
        delete skill;
    mTreeSkills.clear();

    // The client remembers the creature the mouse is hovering in a bare pointer, so that
    // it can restore its ambient once the mouse leaves it. Nothing used to clear that
    // pointer when the creature itself went away, so a creature dying while highlighted
    // left it dangling and the next mouse move dereferenced freed memory.
    if(getIsOnServerMap())
        return;

    // May already be gone when the game map is torn down at shutdown.
    InputManager* inputManager = InputManager::getSingletonPtr();
    if(inputManager != nullptr && inputManager->mHighlightedCreature == this)
        inputManager->mHighlightedCreature = nullptr;
}

void Creature::createMeshLocal(NodeType nt)
{
    MovableGameEntity::createMeshLocal(nt);
    if(!getIsOnServerMap())
    {
        mHexenHenMeshShown = isHexenHen();
        RenderManager::getSingleton().rrCreateCreature(this);

        // By default, we set the creature in idle state
        RenderManager::getSingleton().rrSetObjectAnimationState(this, EntityAnimation::idle_anim, true);
    }

    createMeshWeapons();
}

void Creature::destroyMeshLocal(NodeType nt)
{
    clearGhostHuntVisuals();
    destroyMeshWeapons();
    MovableGameEntity::destroyMeshLocal();
    if(getIsOnServerMap())
        return;

    destroyStatsWindow();
    RenderManager::getSingleton().rrDestroyCreature(this);
}

void Creature::createMeshWeapons()
{
    if(getIsOnServerMap())
        return;

    if(mHexenHenMeshShown)
        return;

    if(mWeaponL != nullptr)
        RenderManager::getSingleton().rrCreateWeapon(this, mWeaponL, "L");

    if(mWeaponR != nullptr)
        RenderManager::getSingleton().rrCreateWeapon(this, mWeaponR, "R");

    RenderManager::getSingleton().rrCreateWorkerTool(this);
}

void Creature::destroyMeshWeapons()
{
    if(getIsOnServerMap())
        return;

    if(mHexenHenMeshShown)
        return;

    if(mWeaponL != nullptr)
        RenderManager::getSingleton().rrDestroyWeapon(this, mWeaponL, "L");

    if(mWeaponR != nullptr)
        RenderManager::getSingleton().rrDestroyWeapon(this, mWeaponR, "R");

    RenderManager::getSingleton().rrDestroyWorkerTool(this);
}

GameEntityType Creature::getObjectType() const
{
    return GameEntityType::creature;
}

void Creature::addToGameMap(GameMap* gameMap)
{
    getGameMap()->addCreature(this);
    getGameMap()->addAnimatedObject(this);
    getGameMap()->addClientUpkeepEntity(this);

    if(!getIsOnServerMap())
        return;

    getGameMap()->addActiveObject(this);
}

//! \brief Removes the creature and releases any crypt spot or delivery reservation holding its body.
void Creature::removeFromGameMap(GameMap* gameMap)
{
    interruptGhostHunt();
    if(getIsOnServerMap())
    {
        for(Room* room : getGameMap()->getRoomsByType(RoomType::crypt))
            static_cast<RoomCrypt*>(room)->removeCorpse(*this);
    }
    fireEntityRemoveFromGameMap();
    removeEntityFromPositionTile();
    getGameMap()->removeCreature(this);
    getGameMap()->removeAnimatedObject(this);
    getGameMap()->removeClientUpkeepEntity(this);

    // Relationships only exist between creatures of the same keeper that are on the map
    if(getGameMap()->isRelationshipsEnabled())
        getGameMap()->getCreatureRelationships()->removeCreature(getName());

    if(!getIsOnServerMap())
        return;

    // If the creature has a homeTile where it sleeps, its bed needs to be destroyed.
    if (getHomeTile() != nullptr)
    {
        RoomDormitory* home = static_cast<RoomDormitory*>(getHomeTile()->getCoveringBuilding());
        home->releaseTileForSleeping(getHomeTile(), this);
    }

    fireRemoveEntityToSeatsWithVision();
    getGameMap()->removeActiveObject(this);
}

//! \brief Restores the base visual state, then seeks a decaying body to its authoritative phase counter.
void Creature::restoreEntityState()
{
    MovableGameEntity::restoreEntityState();
    if(!getIsOnServerMap() && mDecayTurns >= 0.0 &&
       getAnimationStateName() == EntityAnimation::rot_anim && getAnimationState() != nullptr)
        getAnimationState()->setTimePosition(static_cast<Ogre::Real>(mDecayTurns));
}

//! \brief Describes the legacy creature fields and optional trailing appearance, skill and item data.
std::string Creature::getCreatureStreamFormat()
{
    std::string format = MovableGameEntity::getMovableGameEntityStreamFormat();
    if(!format.empty())
        format += "\t";

    format += "ClassName\tLevel\tCurrentXP\tCurrentHP\tCurrentWakefulness"
            "\tCurrentHunger\tGoldToDeposit\tLeftWeapon\tRightWeapon\tCarriedSkill\tCarriedWeapon"
            "\tNbCreatureEffects\tN*CreatureEffects\t[Appearance]\t[Mana]\t[SkillBuild]\t[Items]\t[Needs urge dirt /Needs]"
            "\t[Thirst thirst tavernMood tavernMoodTurns drunk vomited hangoverTurns /Thirst]"
            "\t[Spa spaMood relaxTurns mudTilesLeft /Spa]"
            "\t[Corpse corpseTurns decayTurns /Corpse]";

    return format;
}

//! \brief Writes the creature, its optional skill state and its trailing tagged item block.
void Creature::exportToStream(std::ostream& os) const
{
    const std::streamsize precision = os.precision();
    os << std::setprecision(std::numeric_limits<double>::max_digits10);
    MovableGameEntity::exportToStream(os);
    os << mDefinition->getClassName() << "\t";
    os << getLevel() << "\t" << mExp << "\t";
    // Numeric health preserves the current value while aura sources are rebuilt after loading all holders.
    os << getHP();
    os << "\t" << mWakefulness << "\t" << mHunger << "\t" << mGoldCarried;

    // Check creature weapons
    if(mWeaponL != nullptr)
        os << "\t" << mWeaponL->getName();
    else
        os << "\tnone";

    if(mWeaponR != nullptr)
        os << "\t" << mWeaponR->getName();
    else
        os << "\tnone";

    os << "\t" << Skills::toString(mSkillTypeDropDeath);

    os << "\t" << mWeaponDropDeath;

    uint32_t nbCreatureEffects = 0;
    for(EntityParticleEffect* effect : mEntityParticleEffects)
    {
        if(effect->getEntityParticleEffectType() == EntityParticleEffectType::creature)
            ++nbCreatureEffects;
    }
    os << "\t" << nbCreatureEffects;
    for(EntityParticleEffect* effect : mEntityParticleEffects)
    {
        // We only save creature particle effects. The other are expected to be re-created
        // automatically (for example if it is a permanent effect for a creature)
        if(effect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        CreatureParticleEffect* creatureParticleEffect = static_cast<CreatureParticleEffect*>(effect);
        os << "\t";
        CreatureEffectManager::write(*creatureParticleEffect->mEffect, os);
    }

    // Optional last token, missing in old saves and for creatures without appearance
    if(!mAppearance.isEmpty())
        os << "\t" << CreatureAppearanceLogic::toToken(mAppearance);

    // Current mana as a labelled token after the appearance, missing in old saves (they load with full mana)
    os << "\t" << MANA_SAVE_LABEL << mMana;
    os << "\tMerchantMood=" << mMerchantMood << "\tGoldRemainder=" << mGoldRemainder;
    os << "\t[Infirmary] " << mInfirmaryMood << " " << mInfirmaryMoodTurns << " [/Infirmary]";

    // Optional skill state (after the mana token), missing in old saves: their points are spent again at load
    if(mSkillBuild.mSeed != 0)
    {
        os << "\t" << SKILL_BUILD_MARKER << " ";
        CreatureSkillTree::writeBuild(mSkillBuild, os);
    }
    exportItemsToStream(os);

    // Optional needs block (urge and creature dirt), last; missing in old saves and when both are 0
    if((mUrge > 0.0) || (mCreatureDirt > 0.0))
        os << "\t" << NEEDS_SAVE_OPEN << " " << mUrge << " " << mCreatureDirt << " " << NEEDS_SAVE_CLOSE;

    // Optional thirst block, after the needs block; missing in old saves and when all its values are 0
    if((mThirst > 0.0) || (mTavernMood != 0.0) || (mTavernMoodTurns > 0.0) || (mDrunk > 0.0) || mVomited ||
       (mHangoverTurns > 0.0))
    {
        os << "\t" << THIRST_SAVE_OPEN << " " << mThirst << " " << mTavernMood << " " << mTavernMoodTurns << " "
           << mDrunk << " " << (mVomited ? 1 : 0) << " " << mHangoverTurns << " " << THIRST_SAVE_CLOSE;
    }

    // Optional tavern cooldown block, after the thirst block; missing in old saves and when the cooldown is over
    if(mTavernCooldownTurns > 0)
        os << "\t" << TAVERN_COOLDOWN_SAVE_OPEN << " " << mTavernCooldownTurns << " " << TAVERN_COOLDOWN_SAVE_CLOSE;

    // Optional lava spa block, after the thirst block; missing in old saves and when all its values are 0
    if((mSpaMood > 0.0) || (mRelaxTurns > 0.0) || (mSpaMudTilesLeft > 0))
    {
        os << "\t" << SPA_SAVE_OPEN << " " << mSpaMood << " " << mRelaxTurns << " " << mSpaMudTilesLeft << " "
           << SPA_SAVE_CLOSE;
    }
    if(!isAlive())
    {
        os << "\t[Corpse] " << mCorpseTurns << " " << mDecayTurns << " [/Corpse]";
        if(mDeathCounter == std::numeric_limits<unsigned int>::max())
            os << "\tCorpseConsumed=1";
        else if(mDeathCounter == 0)
            os << "\tCorpseDeathPending=1";
        if(mIsCarried)
            os << "\t" << CORPSE_CARRIER_SAVE_LABEL << mCorpseCarrierName;
    }
    if(mGhostRevived)
        os << " [GhostRevival] " << mSpecialMood << ' ' << mThirst << " [/GhostRevival]";
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
            static_cast<const CreatureActionHuntGhost*>(action.get())->exportToStream(os);
    os.precision(precision);
}

//! \brief Reads legacy creature data with optional appearance, mana, skill state and item data.
bool Creature::importFromStream(std::istream& is)
{
    // Beware: A generic class name might be used here so we shouldn't use mDefinition
    // here as it is not set yet (for example, default worker will be available only after
    // seat lobby configuration)
    if(!MovableGameEntity::importFromStream(is))
        return false;
    std::string tempString;

    if(!(is >> mDefinitionString))
        return false;
    if(!(is >> mLevel))
        return false;
    if(!(is >> mExp))
        return false;
    if(!(is >> mHpString))
        return false;
    if(!(is >> mWakefulness))
        return false;
    if(!(is >> mHunger))
        return false;
    if(!(is >> mGoldCarried))
        return false;
    if(!(is >> tempString))
        return false;
    if(tempString != "none")
    {
        mWeaponL = getGameMap()->getWeapon(tempString);
        if(mWeaponL == nullptr)
        {
            OD_LOG_ERR("Unknown weapon name=" + tempString);
        }
    }

    if(!(is >> tempString))
        return false;
    if(tempString != "none")
    {
        mWeaponR = getGameMap()->getWeapon(tempString);
        if(mWeaponR == nullptr)
        {
            OD_LOG_ERR("Unknown weapon name=" + tempString);
        }
    }

    if(!(is >> tempString))
        return false;
    mSkillTypeDropDeath = Skills::fromString(tempString);

    if(!(is >> mWeaponDropDeath))
        return false;

    mLevel = std::min(MAX_LEVEL, mLevel);

    uint32_t nbEffects;
    if(!(is >> nbEffects))
        return false;
    while(nbEffects > 0)
    {
        --nbEffects;
        CreatureEffect* effect = CreatureEffectManager::load(is);
        if(effect == nullptr)
            continue;

        addCreatureEffect(effect);
    }

    // Optional trailing tokens. Old saves end after the effects. The appearance token comes first (if any), then the
    // labelled mana token (see exportToStream) and the skill state marker with its tokens; each of them can also stand
    // alone when the creature has no appearance or the save is older.
    std::string appearanceToken;
    bool corpseConsumed = false;
    bool corpseDeathPending = false;
    while(is >> appearanceToken)
    {
        if(appearanceToken.compare(0, CORPSE_CARRIER_SAVE_LABEL.size(), CORPSE_CARRIER_SAVE_LABEL) == 0)
        {
            mCorpseCarrierName = appearanceToken.substr(CORPSE_CARRIER_SAVE_LABEL.size());
            continue;
        }
        if(appearanceToken == "CorpseDeathPending=1")
        {
            corpseDeathPending = true;
            continue;
        }
        if(appearanceToken == "CorpseConsumed=1")
        {
            corpseConsumed = true;
            continue;
        }
        if(appearanceToken == "[GhostRevival]")
        {
            std::string close;
            if(!(is >> mSpecialMood >> mSavedRevivalThirst >> close) || close!="[/GhostRevival]" ||
               !std::isfinite(mSavedRevivalThirst) || mSavedRevivalThirst<0.0 || mSavedRevivalThirst>THIRST_STATE_MAX) return false;
            mGhostRevived=true;mRevivalThirstFromSave=true;
            continue;
        }
        if(appearanceToken == "[GhostHunt]")
        {
            std::unique_ptr<CreatureActionHuntGhost> hunt(new CreatureActionHuntGhost(*this));
            if(!hunt->importFromStream(is)) return false;
            mActions.emplace_back(std::move(hunt));mGhostHuntLoaded=true;
            continue;
        }
        if(appearanceToken == "[Corpse]")
        {
            std::string close;
            if(!(is >> mCorpseTurns >> mDecayTurns >> close) || close != "[/Corpse]" ||
               !std::isfinite(mCorpseTurns) || !std::isfinite(mDecayTurns) ||
               mCorpseTurns < 0.0 || mDecayTurns < -1.0)
                return false;
            // Loaded corpses must never repeat the death drops, blood, notice or ghost.
            if(mHpString != "max" && Helper::toDouble(mHpString) <= 0.0)
                mDeathCounter = 1;
            continue;
        }
        if(appearanceToken == "[Infirmary]")
        {
            std::string close;
            if(!(is >> mInfirmaryMood >> mInfirmaryMoodTurns >> close) || close != "[/Infirmary]")
                return false;
            continue;
        }
        if(appearanceToken.compare(0, MERCHANT_MOOD_SAVE_LABEL.size(), MERCHANT_MOOD_SAVE_LABEL) == 0 ||
            appearanceToken.compare(0, GOLD_REMAINDER_SAVE_LABEL.size(), GOLD_REMAINDER_SAVE_LABEL) == 0)
        {
            const bool merchantMood = appearanceToken.compare(0, MERCHANT_MOOD_SAVE_LABEL.size(), MERCHANT_MOOD_SAVE_LABEL) == 0;
            const std::string value = appearanceToken.substr(merchantMood ? MERCHANT_MOOD_SAVE_LABEL.size() : GOLD_REMAINDER_SAVE_LABEL.size());
            char* end = nullptr;
            const double loaded = std::strtod(value.c_str(), &end);
            if(value.empty() || end == nullptr || *end != '\0' || !std::isfinite(loaded)) return false;
            if(merchantMood) mMerchantMood = loaded;
            else
            {
                if(loaded < 0.0 || loaded >= 1.0) return false;
                mGoldRemainder = loaded;
            }
            continue;
        }
        if(appearanceToken.compare(0, MANA_SAVE_LABEL.size(), MANA_SAVE_LABEL) == 0)
        {
            const std::string manaValue = appearanceToken.substr(MANA_SAVE_LABEL.size());
            char* parseEnd = nullptr;
            const double loadedMana = std::strtod(manaValue.c_str(), &parseEnd);
            if(!manaValue.empty() && (parseEnd != nullptr) && (*parseEnd == '\0') && (loadedMana >= 0.0))
            {
                mMana = loadedMana;
                mManaFromSave = true;
            }
            else
            {
                OD_LOG_WRN("Invalid mana token=" + appearanceToken);
            }
            continue;
        }

        if(appearanceToken == NEEDS_SAVE_OPEN)
        {
            std::string needsClose;
            double loadedUrge = 0.0;
            double loadedDirt = 0.0;
            if(!(is >> loadedUrge >> loadedDirt >> needsClose) || (needsClose != NEEDS_SAVE_CLOSE))
            {
                OD_LOG_WRN("Invalid needs block for creature=" + getName() + ", reason="
                    + (is.fail() ? "a value is missing or not a number" : "closing token is '" + needsClose
                    + "' instead of '" + NEEDS_SAVE_CLOSE + "'"));
                return false;
            }
            setUrge(loadedUrge);
            setCreatureDirt(loadedDirt);
            continue;
        }

        if(appearanceToken == THIRST_SAVE_OPEN)
        {
            std::string thirstClose;
            double loadedThirst = 0.0;
            double loadedTavernMood = 0.0;
            double loadedTavernMoodTurns = 0.0;
            double loadedDrunk = 0.0;
            int32_t loadedVomited = 0;
            double loadedHangoverTurns = 0.0;
            if(!(is >> loadedThirst >> loadedTavernMood >> loadedTavernMoodTurns >> loadedDrunk >> loadedVomited >>
                 loadedHangoverTurns >> thirstClose) || (thirstClose != THIRST_SAVE_CLOSE))
            {
                OD_LOG_WRN("Invalid thirst block for creature=" + getName() + ", reason="
                    + (is.fail() ? "a value is missing or not a number" : "closing token is '" + thirstClose
                    + "' instead of '" + THIRST_SAVE_CLOSE + "'"));
                return false;
            }
            // The definition is not resolved yet (see the note at the top), so only the range is limited here;
            // setupDefinition clears non-thirsty types except the exact thirst restored by GhostRevival.
            mThirst = std::min(THIRST_STATE_MAX, std::max(0.0, loadedThirst));
            addTavernMood(loadedTavernMood, loadedTavernMoodTurns);
            setDrunk(loadedDrunk);
            setVomited(loadedVomited != 0);
            setHangoverTurns(loadedHangoverTurns);
            continue;
        }

        if(appearanceToken == TAVERN_COOLDOWN_SAVE_OPEN)
        {
            std::string cooldownClose;
            int32_t loadedCooldown = 0;
            if(!(is >> loadedCooldown >> cooldownClose) || (cooldownClose != TAVERN_COOLDOWN_SAVE_CLOSE))
            {
                OD_LOG_WRN("Invalid tavern cooldown block for creature=" + getName() + ", reason="
                    + (is.fail() ? "a value is missing or not a number" : "closing token is '" + cooldownClose
                    + "' instead of '" + TAVERN_COOLDOWN_SAVE_CLOSE + "'"));
                return false;
            }
            setTavernCooldownTurns(loadedCooldown);
            continue;
        }

        if(appearanceToken == SPA_SAVE_OPEN)
        {
            std::string spaClose;
            double loadedSpaMood = 0.0;
            double loadedRelaxTurns = 0.0;
            int32_t loadedMudTilesLeft = 0;
            if(!(is >> loadedSpaMood >> loadedRelaxTurns >> loadedMudTilesLeft >> spaClose) || (spaClose != SPA_SAVE_CLOSE))
            {
                OD_LOG_WRN("Invalid spa block for creature=" + getName() + ", reason="
                    + (is.fail() ? "a value is missing or not a number" : "closing token is '" + spaClose
                    + "' instead of '" + SPA_SAVE_CLOSE + "'"));
                return false;
            }
            setSpaMood(loadedSpaMood);
            setRelaxTurns(loadedRelaxTurns);
            setSpaMudTilesLeft(loadedMudTilesLeft);
            continue;
        }

        if(appearanceToken == SKILL_BUILD_MARKER)
        {
            if(!CreatureSkillTree::readBuild(is, mSkillBuild))
                return false;
        }
        else if(appearanceToken == "[Items]")
        {
            if(!importItemsFromStream(is))
                return false;
        }
        else
        {
            if(!CreatureAppearanceLogic::fromToken(appearanceToken, mAppearance))
            {
                OD_LOG_WRN("Invalid appearance token=" + appearanceToken);
            }
        }
    }

    // Apply last so arbitrary tag order preserves unprocessed deaths and consumed bodies exactly.
    if(mHpString != "max" && Helper::toDouble(mHpString) <= 0.0)
    {
        if(corpseConsumed)
            mDeathCounter = std::numeric_limits<unsigned int>::max();
        else if(corpseDeathPending)
            mDeathCounter = 0;
    }
    return true;
}

//! \brief Assigns a unique whole portrait on spawn or stably migrates a saved image number.
void Creature::assignAppearance(bool firstSpawn)
{
    if(!getIsOnServerMap() || (mDefinition == nullptr))
        return;

    PortraitCatalogRegistry& registry = getAppearanceRegistry();
    CreatureAppearanceLogic::CatalogExistsFunction exists =
        std::bind(&PortraitCatalogRegistry::hasCatalog, &registry, std::placeholders::_1);
    std::string catalogId = CreatureAppearanceLogic::resolveCatalogId(mDefinition->getMeshName(), getGender(), exists);
    if(catalogId.empty())
    {
        mAppearanceNoCatalog = true;
        mAppearanceNoCatalogGeneration = registry.getCatalogGeneration();
        return;
    }
    mAppearanceNoCatalog = false;

    const PortraitCatalog* catalog = registry.getCatalog(catalogId);
    std::vector<std::string> messages = registry.takeMessages();
    for(std::vector<std::string>::const_iterator it = messages.begin(); it != messages.end(); ++it)
    {
        OD_LOG_WRN("Dungeonbook appearance: " + *it);
    }

    // No catalog (yet): the appearance is derived later like for old saves, a stored one is kept
    if(catalog == nullptr)
        return;

    if(firstSpawn)
    {
        std::vector<CreatureAppearance> taken;
        std::vector<Creature*> mates = getGameMap()->getCreaturesBySeat(getSeat());
        for(std::vector<Creature*>::const_iterator it = mates.begin(); it != mates.end(); ++it)
        {
            const CreatureAppearance& other = (*it)->getAppearance();
            if(other.getCatalogId() == catalogId)
                taken.push_back(other);
        }

        mAppearance = CreatureAppearanceLogic::pickRandom(*catalog, catalogId, getAppearanceRandom, taken);
        mAppearanceValidated = true;
        return;
    }

    if(mAppearance.isEmpty())
        mAppearance = CreatureAppearanceLogic::pickStable(*catalog, catalogId, getName());
    else
        CreatureAppearanceLogic::validate(*catalog, catalogId, getName(), mAppearance);

    mAppearanceValidated = true;
}

//! \brief Retries unavailable whole catalogs and sends an updated appearance only when it changes.
void Creature::retryAppearance()
{
    // A creature without catalog id is only looked at when the catalog generation changed: no waiting period
    if((mAppearanceRetryTurns > 0) && !mAppearanceNoCatalog)
    {
        --mAppearanceRetryTurns;
        return;
    }
    mAppearanceRetryTurns = APPEARANCE_RETRY_TURNS;

    // A catalog that was missing or invalid at spawn may be there now: the registry looks again, then the
    // appearance is derived like for old saves
    getAppearanceRegistry().retryFailed();
    CreatureAppearance before = mAppearance;
    assignAppearance(false);
    if(mAppearance.isEmpty() || (mAppearance == before))
        return;

    // Clients that already know the creature get the new appearance once, the others receive it
    // with the full creature data when they see it
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* notification = new ServerNotification(
            ServerNotificationType::creatureAppearance, seat->getPlayer());
        notification->mPacket << getName() << CreatureAppearanceLogic::toToken(mAppearance);
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

void Creature::setAppearanceFromServer(const CreatureAppearance& appearance)
{
    if(getIsOnServerMap())
        return;

    mAppearance = appearance;
}

namespace
{
//! \brief Writes one nullable item slot in the compact save format.
void writeItemSlot(std::ostream& stream, const std::unique_ptr<ItemInstance>& item)
{
    stream << ' ';
    if(item.get() == nullptr)
        stream << "none";
    else
        item->exportToStream(stream);
}

//! \brief Reads one nullable save slot without consuming data belonging to following slots.
bool readItemSlot(std::istream& stream, std::unique_ptr<ItemInstance>& item)
{
    std::string id;
    if(!(stream >> id))
        return false;
    if(id == "none")
    {
        item.reset();
        return true;
    }
    std::unique_ptr<ItemInstance> loaded(new ItemInstance);
    if(!loaded->importFromStream(stream, id))
        return false;
    item = std::move(loaded);
    return true;
}

//! \brief Writes a packet slot with a presence bit, masking private slots for foreign seats.
void writeItemSlotPacket(ODPacket& packet, const std::unique_ptr<ItemInstance>& item, bool visible)
{
    const bool present = visible && item.get() != nullptr;
    packet << present;
    if(present)
        item->exportToPacket(packet);
}

//! \brief Reads a nullable packet slot, retaining no partially received instance.
bool readItemSlotPacket(ODPacket& packet, std::unique_ptr<ItemInstance>& item)
{
    bool present = false;
    if(!(packet >> present))
        return false;
    if(!present)
    {
        item.reset();
        return true;
    }
    std::unique_ptr<ItemInstance> loaded(new ItemInstance);
    if(!loaded->importFromPacket(packet))
        return false;
    item = std::move(loaded);
    return true;
}
}

//! \brief Writes every carried item in the optional trailing creature block.
void Creature::exportItemsToStream(std::ostream& stream) const
{
    stream << " [Items]";
    for(const std::unique_ptr<ItemInstance>& item : mEquipment)
        writeItemSlot(stream, item);
    stream << ' ' << mPotionSlots.size();
    for(const std::unique_ptr<ItemInstance>& item : mPotionSlots)
        writeItemSlot(stream, item);
    for(const std::unique_ptr<ItemInstance>& item : mInventory)
        writeItemSlot(stream, item);
    stream << " [/Items]";
}

//! \brief Loads a complete carried-item block and reconstructs its share of the Epic registry.
bool Creature::importItemsFromStream(std::istream& stream)
{
    static const uint32_t MAX_POTION_SLOTS = 3;
    std::array<std::unique_ptr<ItemInstance>, 6> equipment;
    std::array<std::unique_ptr<ItemInstance>, 4> inventory;
    std::vector<std::unique_ptr<ItemInstance>> potions;
    for(std::unique_ptr<ItemInstance>& item : equipment)
    {
        if(!readItemSlot(stream, item))
            return false;
    }
    uint32_t count = 0;
    if(!(stream >> count) || count > MAX_POTION_SLOTS)
        return false;
    potions.resize(count);
    for(std::unique_ptr<ItemInstance>& item : potions)
    {
        if(!readItemSlot(stream, item))
            return false;
    }
    for(std::unique_ptr<ItemInstance>& item : inventory)
    {
        if(!readItemSlot(stream, item))
            return false;
    }
    std::string end;
    if(!(stream >> end) || end != "[/Items]")
        return false;
    mEquipment = std::move(equipment);
    mInventory = std::move(inventory);
    mPotionSlots = std::move(potions);
    for(const std::unique_ptr<ItemInstance>& item : mEquipment)
    {
        if(item.get() != nullptr)
            getGameMap()->registerEpic(*item);
    }
    for(const std::unique_ptr<ItemInstance>& item : mInventory)
    {
        if(item.get() != nullptr)
            getGameMap()->registerEpic(*item);
    }
    return true;
}

//! \brief Sends hand appearances to everyone and private equipment, potions and inventory only to the owner.
void Creature::exportItemsToPacket(ODPacket& packet, const Seat* seat) const
{
    const bool ownData = seat != nullptr && seat == getSeat();
    packet << mMaxHP;
    for(size_t index = 0; index < mEquipment.size(); ++index)
        writeItemSlotPacket(packet, mEquipment[index], ownData || index < 2);
    packet << static_cast<uint32_t>(mPotionSlots.size());
    for(const std::unique_ptr<ItemInstance>& item : mPotionSlots)
        writeItemSlotPacket(packet, item, ownData);
    for(const std::unique_ptr<ItemInstance>& item : mInventory)
        writeItemSlotPacket(packet, item, ownData);
    const uint32_t potionCount = ownData ? static_cast<uint32_t>(mPotionContributions.size()) : 0;
    packet << potionCount;
    if(ownData)
    {
        for(const std::pair<const CreatureEffect* const, std::pair<std::string, double>>& entry : mPotionContributions)
            packet << entry.second.first << entry.second.second;
    }
    const double guardWall = ownData ? getGameMap()->getItemAura(*this, "GuardWall") : 0.0;
    const double rally = ownData ? getGameMap()->getItemAura(*this, "Rally") : 0.0;
    packet << guardWall << rally;
    packet << (ownData ? mMerchantMood : 0.0) << static_cast<uint8_t>(ownData ? mLastItemDeal : 0)
        << (ownData ? mLastItemName : std::string());
    if(ownData) { mLastItemDeal = 0; mLastItemName.clear(); }
}

//! \brief Adopts a complete item update and refreshes client hand meshes when their quality changes.
bool Creature::importItemsFromPacket(ODPacket& packet)
{
    static const uint32_t MAX_POTION_SLOTS = 3;
    std::array<std::unique_ptr<ItemInstance>, 6> equipment;
    std::array<std::unique_ptr<ItemInstance>, 4> inventory;
    std::vector<std::unique_ptr<ItemInstance>> potions;
    double maximumHealth = 0.0;
    if(!(packet >> maximumHealth) || !std::isfinite(maximumHealth) || maximumHealth < 0.0)
        return false;
    for(std::unique_ptr<ItemInstance>& item : equipment)
    {
        if(!readItemSlotPacket(packet, item))
            return false;
    }
    uint32_t count = 0;
    if(!(packet >> count) || count > MAX_POTION_SLOTS)
        return false;
    potions.resize(count);
    for(std::unique_ptr<ItemInstance>& item : potions)
    {
        if(!readItemSlotPacket(packet, item))
            return false;
    }
    for(std::unique_ptr<ItemInstance>& item : inventory)
    {
        if(!readItemSlotPacket(packet, item))
            return false;
    }
    uint32_t contributionCount = 0;
    if(!(packet >> contributionCount) || contributionCount > ConfigManager::getSingleton().getPotions().size())
        return false;
    std::vector<std::pair<std::string, double>> contributions;
    for(uint32_t index = 0; index < contributionCount; ++index)
    {
        std::pair<std::string, double> value("", 0.0);
        if(!(packet >> value.first >> value.second) || !std::isfinite(value.second))
            return false;
        contributions.push_back(value);
    }
    double guardWall = 0.0;
    double rally = 0.0;
    if(!(packet >> guardWall >> rally) || !std::isfinite(guardWall) || !std::isfinite(rally))
        return false;
    double merchantMood = 0.0;
    uint8_t deal = 0;
    std::string itemName;
    if(!(packet >> merchantMood >> deal >> itemName) || !std::isfinite(merchantMood) || deal > 5) return false;
    bool handChanged = false;
    for(size_t index = 0; index < 2; ++index)
    {
        const ItemInstance* oldItem = mEquipment[index].get();
        const ItemInstance* newItem = equipment[index].get();
        if(oldItem == nullptr || newItem == nullptr)
            handChanged = handChanged || oldItem != newItem;
        else
            handChanged = handChanged || oldItem->mDefinitionId != newItem->mDefinitionId || oldItem->mQuality != newItem->mQuality;
    }
    mEquipment = std::move(equipment);
    mInventory = std::move(inventory);
    mPotionSlots = std::move(potions);
    mMaxHP = maximumHealth;
    mClientPotionContributions = contributions;
    mClientGuardWall = guardWall;
    mClientRally = rally;
    mMerchantMood = merchantMood;
    if(deal != 0 && mDefinition != nullptr && isSocialFeedSource())
    {
        social::PostCategory category = social::PostCategory::Bought;
        if(deal == 2) category = social::PostCategory::Bargain;
        else if(deal == 3) category = social::PostCategory::Fleeced;
        else if(deal == 4) category = social::PostCategory::Gift;
        else if(deal == 5) category = social::PostCategory::EpicFind;
        social::PostLog::getSingleton().addPost(getGameMap()->getTurnNumber(), getName(),
            mDefinition->getClassName(), mDefinition->isWorker(), category, 0, itemName);
        if(CreatureReactions::getSingletonPtr() != nullptr)
        {
            std::string event;
            if(deal == 2) event = "ItemBargain";
            else if(deal == 3) event = "ItemFleeced";
            else if(deal == 4) event = "ItemGift";
            else if(deal == 5) event = "ItemEpic";
            if(!event.empty()) CreatureReactions::getSingleton().trigger(this, event);
        }
    }
    if(handChanged && !getIsOnServerMap() && getEntityNode() != nullptr)
    {
        destroyMeshWeapons();
        createMeshWeapons();
    }
    return true;
}

//! \brief Returns the sum of the requested bonus across worn slots.
double Creature::getItemBonus(const std::string& kind) const
{
    double sum = 0.0;
    for(const std::unique_ptr<ItemInstance>& item : mEquipment)
    {
        if(item.get() != nullptr)
            sum += item->getBonus(kind);
    }
    return sum;
}

//! \brief Returns the sum of one special effect across worn slots.
double Creature::getItemEffect(const std::string& id) const
{
    double sum = 0.0;
    for(const std::unique_ptr<ItemInstance>& item : mEquipment)
    {
        if(item.get() != nullptr)
            sum += item->getEffect(id);
    }
    return sum;
}

//! \brief Converts level-equivalent equipment bonuses to the wearer's natural attribute points.
double Creature::getItemAttribute(const std::string& attribute) const
{
    if(mDefinition == nullptr)
        return 0.0;
    if(attribute == "Life")
        return getItemBonus("Life") * mDefinition->getLifePerLevel();
    if(attribute == "Mana")
        return getItemBonus("Mana") * mDefinition->getManaPerLevel();
    const std::string& group = mDefinition->getSkillGroup();
    const bool dexterity = group == "archer" || group == "caster";
    if(attribute == "Dexterity" && dexterity)
        return getItemBonus("DamageAttribute") * mDefinition->getDexterityPerLevel();
    if(attribute == "Strength" && !dexterity)
        return getItemBonus("DamageAttribute") * mDefinition->getStrengthPerLevel();
    return 0.0;
}

//! \brief Rebuilds derived equipment stats, preserving existing health rather than healing on an equip change.
void Creature::itemsChanged()
{
    mNeedFireRefresh = true;
    if(mDefinition == nullptr)
        return;
    buildStats();
    mHp = std::min(mHp, mMaxHP);
    mMana = std::min(mMana, getMaxMana());
    computeCreatureOverlayHealthValue();
}

//! \brief Exchanges one equipment slot and returns the replaced item to its new holder.
std::unique_ptr<ItemInstance> Creature::setEquipment(size_t slot, std::unique_ptr<ItemInstance> item)
{
    std::unique_ptr<ItemInstance> previous = std::move(mEquipment.at(slot));
    mEquipment.at(slot) = std::move(item);
    itemsChanged();
    return previous;
}

//! \brief Exchanges one carried inventory slot and marks the creature for refresh.
std::unique_ptr<ItemInstance> Creature::setInventorySlot(size_t slot, std::unique_ptr<ItemInstance> item)
{
    std::unique_ptr<ItemInstance> previous = std::move(mInventory.at(slot));
    mInventory.at(slot) = std::move(item);
    mNeedFireRefresh = true;
    return previous;
}

//! \brief Exchanges one unstacked potion slot and marks it for refresh.
std::unique_ptr<ItemInstance> Creature::setPotionSlot(size_t slot, std::unique_ptr<ItemInstance> item)
{
    std::unique_ptr<ItemInstance> previous = std::move(mPotionSlots.at(slot));
    mPotionSlots.at(slot) = std::move(item);
    mNeedFireRefresh = true;
    return previous;
}

//! \brief Adds the second potion slot at level ten and the third at level twenty.
void Creature::resizePotionSlots()
{
    static const uint32_t SECOND_SLOT_LEVEL = 10;
    static const uint32_t THIRD_SLOT_LEVEL = 20;
    size_t count = 1;
    if(mLevel >= THIRD_SLOT_LEVEL)
        count = 3;
    else if(mLevel >= SECOND_SLOT_LEVEL)
        count = 2;
    if(mPotionSlots.size() < count)
    {
        mPotionSlots.resize(count);
        mNeedFireRefresh = true;
    }
}

//! \brief Multiplies the active contributions of a single potion kind.
double Creature::getPotionFactor(const std::string& kind) const
{
    double factor = 1.0;
    if(!getIsOnServerMap())
    {
        for(const std::pair<std::string, double>& entry : mClientPotionContributions)
        {
            if(entry.first == kind)
                factor *= entry.second;
        }
        return factor;
    }
    for(const std::pair<const CreatureEffect* const, std::pair<std::string, double>>& entry : mPotionContributions)
    {
        if(entry.second.first == kind)
            factor *= entry.second.second;
    }
    return factor;
}

//! \brief Gives dexterity potions their two, four or six critical chance points.
double Creature::getPotionCritChance() const
{
    static const double DEXTERITY_SMALL = 1.10;
    static const double DEXTERITY_MEDIUM = 1.15;
    static const double DEXTERITY_LARGE = 1.20;
    double points = 0.0;
    if(!getIsOnServerMap())
    {
        const double factor = getPotionFactor("DexterityChange");
        if(factor >= DEXTERITY_LARGE) return 6.0;
        if(factor >= DEXTERITY_MEDIUM) return 4.0;
        if(factor >= DEXTERITY_SMALL) return 2.0;
        return 0.0;
    }
    for(const std::pair<const CreatureEffect* const, std::pair<std::string, double>>& entry : mPotionContributions)
    {
        if(entry.second.first != "DexterityChange")
            continue;
        if(entry.second.second >= DEXTERITY_LARGE)
            points += 6.0;
        else if(entry.second.second >= DEXTERITY_MEDIUM)
            points += 4.0;
        else if(entry.second.second >= DEXTERITY_SMALL)
            points += 2.0;
    }
    return points;
}

//! \brief Applies one timed potion multiplier and scales current health only for a maximum-health potion.
void Creature::setPotionContribution(const CreatureEffect* source, const std::string& kind, double value)
{
    const double oldMaximum = mMaxHP;
    mPotionContributions[source] = std::make_pair(kind, value);
    if(mDefinition == nullptr)
        return;
    buildStats();
    if(kind == "MaxHPChange" && oldMaximum > 0.0)
        mHp *= mMaxHP / oldMaximum;
    mNeedFireRefresh = true;
}

//! \brief Removes one timed potion multiplier and reverses its health scaling without killing the creature.
void Creature::removePotionContribution(const CreatureEffect* source)
{
    std::map<const CreatureEffect*, std::pair<std::string, double>>::iterator found = mPotionContributions.find(source);
    if(found == mPotionContributions.end())
        return;
    const bool healthPotion = found->second.first == "MaxHPChange";
    const double oldMaximum = mMaxHP;
    mPotionContributions.erase(found);
    if(mDefinition == nullptr)
        return;
    buildStats();
    if(healthPotion && oldMaximum > 0.0 && mHp > 0.0)
        mHp = std::max(1.0, mHp * mMaxHP / oldMaximum);
    mMana = std::min(mMana, getMaxMana());
    mNeedFireRefresh = true;
}

//! \brief Adds conditional item defense after the natural defense curve.
double Creature::getItemDefenseFactor() const
{
    static const double LAST_STAND_HEALTH_SHARE = 0.25;
    static const double BULWARK_RADIUS = 2.0;
    double bonus = getItemBonus("Defense%") + getItemEffect("ThickPlates");
    if(mMaxHP > 0.0 && mHp < mMaxHP * LAST_STAND_HEALTH_SHARE)
        bonus += getItemEffect("LastStand");
    if(getItemEffect("Bulwark") != 0.0)
    {
        for(const Creature* mate : getOwnCreaturesWithin(BULWARK_RADIUS))
        {
            if(mate != this)
            {
                bonus += getItemEffect("Bulwark");
                break;
            }
        }
    }
    return (1.0 + bonus / 100.0) * getPotionFactor("DefenseChange");
}

//! \brief Ends every running freeze effect while preserving other effects.
void Creature::endFreeze()
{
    for(EntityParticleEffect* particle : mEntityParticleEffects)
    {
        if(particle->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;
        CreatureParticleEffect* effect = static_cast<CreatureParticleEffect*>(particle);
        if(effect->mEffect->getEffectName() != "Frozen")
            continue;
        effect->mEffect->releaseEffect(*this);
        effect->mEffect->mNbTurnsEffect = 0.0;
        effect->mNbTurnsEffect = 0;
    }
    mNeedFireRefresh = true;
}

//! \brief Returns natural sight extended by worn Far Sight effects.
int32_t Creature::getTileSightRadius() const
{
    return mDefinition->getSightRadius() + static_cast<int32_t>(getItemEffect("FarSight"));
}

//! \brief Builds natural health and defenses with their combat curves, retaining other stat growth. The move%
//! passives of the skills raise the speeds.
void Creature::buildStats()
{
    resizePotionSlots();
    // Get the base value
    mMaxHP = mDefinition->getMinHp();
    mDigRate = mDefinition->getDigRate();
    mClaimRate = mDefinition->getClaimRate();
    mGroundSpeed = mDefinition->getMoveSpeedGround();
    mWaterSpeed = mDefinition->getMoveSpeedWater();
    mLavaSpeed  = mDefinition->getMoveSpeedLava();

    mPhysicalDefense = mDefinition->getPhysicalDefense();
    mMagicalDefense = mDefinition->getMagicalDefense();
    mElementDefense = mDefinition->getElementDefense();

    // Hit points follow the Life attribute level, so equipment can raise them even at level 1, then the hp% passives
    mMaxHP = CreatureProgression::combatStatAt(mMaxHP, mDefinition->getHpPerLevel(), getLifeLevel(),
        CreatureProgression::hpMultiplierAt) * (1.0 + getSkillPassive("hp%") / 100.0) * getPotionFactor("MaxHPChange");

    // Improve the stats to the current level
    double multiplier = mLevel - 1;
    if (multiplier <= 0.0)
    {
        for(const std::pair<const CreatureEffect* const, CreatureDefenseBonus>& entry : mDefenseContributions)
        {
            mPhysicalDefense += entry.second.mPhy;
            mMagicalDefense += entry.second.mMag;
            mElementDefense += entry.second.mEle;
        }
        applyMovePassive();
        return;
    }

    mDigRate += mDefinition->getDigRatePerLevel() * multiplier;
    mClaimRate += mDefinition->getClaimRatePerLevel() * multiplier;
    mGroundSpeed += mDefinition->getGroundSpeedPerLevel() * multiplier;
    mWaterSpeed += mDefinition->getWaterSpeedPerLevel() * multiplier;
    mLavaSpeed += mDefinition->getLavaSpeedPerLevel() * multiplier;

    mPhysicalDefense = CreatureProgression::combatStat(mPhysicalDefense, mDefinition->getPhysicalDefPerLevel(), mLevel,
        CreatureProgression::damageMultiplier);
    mMagicalDefense = CreatureProgression::combatStat(mMagicalDefense, mDefinition->getMagicalDefPerLevel(), mLevel,
        CreatureProgression::damageMultiplier);
    mElementDefense = CreatureProgression::combatStat(mElementDefense, mDefinition->getElementDefPerLevel(), mLevel,
        CreatureProgression::damageMultiplier);
    for(const std::pair<const CreatureEffect* const, CreatureDefenseBonus>& entry : mDefenseContributions)
    {
        mPhysicalDefense += entry.second.mPhy;
        mMagicalDefense += entry.second.mMag;
        mElementDefense += entry.second.mEle;
    }
    applyMovePassive();
}

//! \brief Multiplies the three move speeds by the move% passives of the skills.
void Creature::applyMovePassive()
{
    const double factor = mSpeedModifier * (1.0 + getSkillPassive("move%") / 100.0);
    mGroundSpeed *= factor;
    mWaterSpeed *= factor;
    mLavaSpeed *= factor;
}

Creature* Creature::getCreatureFromStream(GameMap* gameMap, std::istream& is)
{
    Creature* creature = new Creature(gameMap);
    if(!creature->importFromStream(is))
    {
        delete creature;
        return nullptr;
    }
    return creature;
}

Creature* Creature::getCreatureFromPacket(GameMap* gameMap, ODPacket& is)
{
    Creature* creature = new Creature(gameMap);
    creature->importFromPacket(is);
    return creature;
}

//! \brief Writes full creature data with private item slots masked for foreign seats.
void Creature::exportToPacket(ODPacket& os, const Seat* seat) const
{
    MovableGameEntity::exportToPacket(os, seat);
    const std::string& className = mDefinition->getClassName();
    os << className;
    os << mLevel;
    os << mExp;

    os << mHp;
    os << mMaxHP;

    os << mDigRate;
    os << mClaimRate;
    os << mWakefulness;
    os << mHunger;

    os << getMoveSpeedGround();
    os << getMoveSpeedWater();
    os << getMoveSpeedLava();

    os << mPhysicalDefense;
    os << mMagicalDefense;
    os << mElementDefense;
    os << mOverlayHealthValue;

    // Only allied players should see creature mood (except some states)
    uint32_t moodValue = 0;
    if(seat->isAlliedSeat(getSeat()))
        moodValue = mOverlayMoodValue;
    else if(mSeatPrison != nullptr)
    {
        if(mSeatPrison->isAlliedSeat(seat))
            moodValue = mOverlayMoodValue & CreatureMoodValues::MoodPrisonFiltersPrisonAllies;
        else
            moodValue = mOverlayMoodValue & CreatureMoodValues::MoodPrisonFiltersAllPlayers;
    }

    os << moodValue;
    os << mSpeedModifier;

    if(mWeaponL != nullptr)
        os << mWeaponL->getName();
    else
        os << "none";

    if(mWeaponR != nullptr)
        os << mWeaponR->getName();
    else
        os << "none";

    os << isHexenHen();
    exportMoodToPacket(os, seat);
    exportActivityToPacket(os, seat);
    exportProgressToPacket(os, seat);
    // Current mana (the maximum follows from type, level and equipment on the client)
    os << mMana;
    // Dungeonbook appearance: chosen by the server, sent once with the full creature data (empty: none)
    os << CreatureAppearanceLogic::toToken(mAppearance);
    // The skill state and carried gold are followed by the visible item slots and active owner contributions, then
    // the needs (urge and creature dirt) for the stats window, then the thirst state (thirst, tavern mood,
    // drunkenness, hangover), followed by corpse lie and decay turns
    exportSkillBuildToPacket(os);
    os << mGoldCarried;
    exportItemsToPacket(os, seat);
    os << (seat == getSeat() ? mInfirmaryMood : 0.0);
    os << mUrge;
    os << mCreatureDirt;
    exportThirstStateToPacket(os);
    // The lava spa state is only sent to the own seat (the same two fields as in the update packet, 0 for every other
    // seat)
    if(seat == getSeat())
        exportSpaStateToPacket(os);
    else
    {
        os << 0.0;
        os << 0.0;
    }
    os << mCorpseTurns << mDecayTurns;
    os << mGhostBackpack << mGhostBeamTarget << mGhostBoxMode << mGhostThrowTarget << mGhostThrowTurns;
}

//! \brief Reads full creature data, including the trailing rolled item slots.
void Creature::importFromPacket(ODPacket& is)
{
    MovableGameEntity::importFromPacket(is);
    std::string tempString;

    OD_ASSERT_TRUE(is >> mDefinitionString);

    OD_ASSERT_TRUE(is >> mLevel);
    OD_ASSERT_TRUE(is >> mExp);

    OD_ASSERT_TRUE(is >> mHp);
    OD_ASSERT_TRUE(is >> mMaxHP);

    OD_ASSERT_TRUE(is >> mDigRate);
    OD_ASSERT_TRUE(is >> mClaimRate);
    OD_ASSERT_TRUE(is >> mWakefulness);
    OD_ASSERT_TRUE(is >> mHunger);

    OD_ASSERT_TRUE(is >> mGroundSpeed);
    OD_ASSERT_TRUE(is >> mWaterSpeed);
    OD_ASSERT_TRUE(is >> mLavaSpeed);

    OD_ASSERT_TRUE(is >> mPhysicalDefense);
    OD_ASSERT_TRUE(is >> mMagicalDefense);
    OD_ASSERT_TRUE(is >> mElementDefense);

    OD_ASSERT_TRUE(is >> mOverlayHealthValue);
    OD_ASSERT_TRUE(is >> mOverlayMoodValue);
    OD_ASSERT_TRUE(is >> mSpeedModifier);

    OD_ASSERT_TRUE(is >> tempString);
    if(tempString != "none")
    {
        mWeaponL = getGameMap()->getWeapon(tempString);
        if(mWeaponL == nullptr)
        {
            OD_LOG_ERR("Unknown weapon name=" + tempString);
        }
    }

    OD_ASSERT_TRUE(is >> tempString);
    if(tempString != "none")
    {
        mWeaponR = getGameMap()->getWeapon(tempString);
        if(mWeaponR == nullptr)
        {
            OD_LOG_ERR("Unknown weapon name=" + tempString);
        }
    }

    OD_ASSERT_TRUE(is >> mIsHexenHen);
    importMoodFromPacket(is);
    importActivityFromPacket(is);
    importProgressFromPacket(is);
    OD_ASSERT_TRUE(is >> mMana);
    // The client only takes over the appearance the server has chosen, it never rolls one itself
    std::string appearanceToken;
    OD_ASSERT_TRUE(is >> appearanceToken);
    mAppearance = CreatureAppearance();
    if(!appearanceToken.empty() && !CreatureAppearanceLogic::fromToken(appearanceToken, mAppearance))
    {
        OD_LOG_ERR("Invalid appearance token=" + appearanceToken);
    }
    importSkillBuildFromPacket(is);
    OD_ASSERT_TRUE(is >> mGoldCarried);
    OD_ASSERT_TRUE(importItemsFromPacket(is));
    OD_ASSERT_TRUE(is >> mInfirmaryMood);
    OD_ASSERT_TRUE(is >> mUrge);
    OD_ASSERT_TRUE(is >> mCreatureDirt);
    importThirstStateFromPacket(is);
    importSpaStateFromPacket(is);
    OD_ASSERT_TRUE(is >> mCorpseTurns >> mDecayTurns);
    OD_ASSERT_TRUE(is >> mGhostBackpack >> mGhostBeamTarget >> mGhostBoxMode >> mGhostThrowTarget >> mGhostThrowTurns);
    mGhostThrowClientTurns=mGhostThrowTurns;

    setupDefinition(*getGameMap(), *ConfigManager::getSingleton().getCreatureDefinitionDefaultWorker());
}

void Creature::setPosition(const Ogre::Vector3& v, GameMap *gameMap )
{
    // The tile the creature leaves, to know whether it enters a new one (null while it is not on the map)
    Tile* leftTile = (getIsOnServerMap() && getIsOnMap()) ? getPositionTile() : nullptr;

    MovableGameEntity::setPosition(v);
    if(mCarriedEntity != nullptr)
        mCarriedEntity->notifyCarryMove(v);

    // A creature that enters a new tile leaves dirt on it
    if(leftTile != nullptr)
    {
        Tile* enteredTile = getPositionTile();
        if((enteredTile != nullptr) && (enteredTile != leftTile))
            dirtyEnteredTile(enteredTile);
    }

    if(!getIsOnServerMap()){

    
        InputManager& inputManager = InputManager::getSingleton();

        // getPositionTile() returns null whenever the creature sits outside the map,
        // which happens while it is held in the keeper hand or carried around.
        Tile* positionTile = getPositionTile();

        if(positionTile != nullptr &&
           positionTile->getX() == inputManager.mXPos &&
           positionTile->getY() == inputManager.mYPos)
        {

            Creature* closestCreature = positionTile->getClosestCreature(inputManager.mCreatureTypeForOutliner );
            if(closestCreature != nullptr)
            {
                if(closestCreature != inputManager.mHighlightedCreature)
                {
                    if(inputManager.mHighlightedCreature != nullptr)
                    {
                        inputManager.mHighlightedCreature->normalizeAmbient();
                    }
                    inputManager.mHighlightedCreature = closestCreature;
                    closestCreature->maxAmbient();

                    // The creature notices the hand that comes over it
                    if(CreatureReactions::getSingletonPtr() != nullptr)
                        CreatureReactions::getSingleton().noteHandHover(closestCreature);
                }
            }
        }
        else if(inputManager.mHighlightedCreature == this)
        {
            inputManager.mHighlightedCreature->normalizeAmbient();
            inputManager.mHighlightedCreature = nullptr;        

        }
    }
}

void Creature::setHP(double nHP)
{
    if (nHP > mMaxHP)
        mHp = mMaxHP;
    else
        mHp = nHP;

    computeCreatureOverlayHealthValue();
}

void Creature::heal(double hp)
{
    mHp = std::min(mHp + hp, mMaxHP);

    computeCreatureOverlayHealthValue();
}

double Creature::getLevelScale() const
{
    const double levelSteps = static_cast<double>(std::max(1u, std::min(MAX_LEVEL, getLevel())) - 1u);
    return 1.0 + ConfigManager::getSingleton().getCreatureLevelGrowthMax() * levelSteps / static_cast<double>(MAX_LEVEL - 1u);
}

bool Creature::isAlive() const
{
    if(!getIsOnServerMap())
        return mOverlayHealthValue < (NB_OVERLAY_HEALTH_VALUES - 1);

    return mHp > 0.0;
}

void Creature::update(Ogre::Real timeSinceLastFrame)
{
    Tile* previousPositionTile = getPositionTile();
    // Update movements, direction, ...
    MovableGameEntity::update(timeSinceLastFrame);

    // A client moves a jumping creature along the arc the server told (the server steps it once per turn)
    if(!getIsOnServerMap() && (mJumpTurnsLeft > 0))
    {
        // The server ended the jump (a fight, the hand, a removed room): the clip is not the jump clip any more, so the
        // arc stops and the creature stands on the floor again
        if(getAnimationStateName() != EntityAnimation::jump_anim)
        {
            mJumpTurnsLeft = 0;
            setPosition(Ogre::Vector3(getPosition().x, getPosition().y, mJumpTo.z));
        }
        else
        {
            mJumpElapsed = std::min(static_cast<Ogre::Real>(mJumpTurns), mJumpElapsed +
                static_cast<Ogre::Real>(ODApplication::turnsPerSecond * timeSinceLastFrame * getGameMap()->getGameSpeedFactor()));
            setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
            showJumpClipPhase();
            if(mJumpElapsed >= static_cast<Ogre::Real>(mJumpTurns))
                mJumpTurnsLeft = 0;
        }
    }

    // Update the visual debugging entities
    //if we are standing in a different tile than we were last turn
    if (mHasVisualDebuggingEntities &&
        getIsOnServerMap() &&
        (getPositionTile() != previousPositionTile))
    {
        computeVisualDebugEntities();
    }

    if(getOverlayStatus() != nullptr)
    {
        getOverlayStatus()->update(timeSinceLastFrame);
    }
}

void Creature::computeVisibleTiles()
{
    // dead Creatures do not give vision
    if (getHP() <= 0.0)
        return;

    // KO Creatures do not give vision
    if (isKo())
        return;

    // creatures in jail do not give vision
    if (mSeatPrison != nullptr)
        return;

    if (!getIsOnMap())
        return;

    // Look at the surrounding area
    updateTilesInSight();
    for(Tile* tile : mVisibleTiles)
    {
        getSeat()->notifyOwnCreatureVision(tile);
        tile->notifyVision(getSeat());
    }
}

//! \brief Sets the level, spends the skill points the level pays and rebuilds the stats. The current hit points and the
//! current mana keep their share of the maximum when the maximum grows.
void Creature::setLevel(unsigned int level)
{
    // The size of the mana pool before the new level, to keep the mana share
    const double previousMaxMana = getMaxMana();

    // Reset XP once the level has been acquired.
    mLevel = std::max(1u, std::min(MAX_LEVEL, level));
    mExp = 0.0;

    // The new level may pay skill points; their passives are part of the stats built below
    updateSkillPoints();

    const double previousMaxHP = mMaxHP;
    buildStats();
    if(mHp > 0.0 && previousMaxHP > 0.0)
        mHp = std::min(mMaxHP, mHp * mMaxHP / previousMaxHP);

    // The pool grows with the level; the mana keeps its share of the pool like the hit points (a pool of 0 before
    // the level-up keeps the mana as it is, then capped at the new size)
    if(previousMaxMana > 0.0)
        setCurrentMana(mMana * getMaxMana() / previousMaxMana);
    else
        setCurrentMana(mMana);

    mNeedFireRefresh = true;
}

//! \brief Drops carried gold and death items; combat knockout item loss is handled by takeDamage.
void Creature::dropCarriedEquipment()
{
    if(!isAlive())
        dropItems(true);
    fireCreatureSound(CreatureSound::Die);
    clearActionQueue();
    clearDestinations(EntityAnimation::die_anim, false, false);
    setAnimationState(EntityAnimation::die_anim, false, Ogre::Vector3::ZERO, false);

    // We drop what we are carrying
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
        return;
    }

    if(mGoldCarried > 0)
    {
        TreasuryObject* obj = new TreasuryObject(getGameMap(), mGoldCarried);
        obj->addToGameMap();
        Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(myTile->getX()),
                                    static_cast<Ogre::Real>(myTile->getY()), 0.0f);
        obj->createMesh();
        obj->setPosition(spawnPosition);
        mGoldCarried = 0;
    }

    if(mSkillTypeDropDeath != SkillType::nullSkillType)
    {
        GiftBoxSkill* skillEntity = new GiftBoxSkill(getGameMap(),
            "DroppedBy" + getName(), mSkillTypeDropDeath);
        skillEntity->addToGameMap();
        Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(myTile->getX()),
                                    static_cast<Ogre::Real>(myTile->getY()), 0.0f);
        skillEntity->createMesh();
        skillEntity->setPosition(spawnPosition);
        mSkillTypeDropDeath = SkillType::nullSkillType;
    }

    // TODO: drop weapon when available
}

//! \brief Advances creature upkeep and records an expired lethal knockout as an actual script death.
//! Spaces authoritative standing bodies before their next action without changing action targets.
void Creature::doUpkeep()
{
    upkeepGhostHunt();
    const double oldMaximumHealth = mMaxHP;
    buildStats();
    if(oldMaximumHealth != mMaxHP)
    {
        mHp = std::min(mHp, mMaxHP);
        mNeedFireRefresh = true;
    }
    if(isAlive() && !isActionInList(CreatureActionType::fight))
    {
        static const double MENDING_SECONDS = 10.0;
        const double healing = getItemEffect("Mending") / 100.0 * mMaxHP / (MENDING_SECONDS * ODApplication::turnsPerSecond);
        if(healing > 0.0)
            heal(healing);
    }
    // No manifest was available when the creature spawned: assign the appearance as soon as it is
    // (or the stored one was never checked against a catalog): the appearance is derived or checked as soon as one is
    if(getIsOnServerMap())
    {
        // New catalog folders are looked for once per retry period for all creatures together, never per creature
        static int64_t lastCatalogRefresh = -1;
        int64_t turn = getGameMap()->getTurnNumber();
        if((lastCatalogRefresh < 0) || (turn < lastCatalogRefresh) || (turn - lastCatalogRefresh >= APPEARANCE_RETRY_TURNS))
        {
            lastCatalogRefresh = turn;
            getAppearanceRegistry().invalidateCatalogs();
        }

        if(CreatureAppearanceLogic::needsAppearanceCheck(mAppearance.isEmpty(), mAppearanceValidated,
            mAppearanceNoCatalog, mAppearanceNoCatalogGeneration, getAppearanceRegistry().getCatalogGeneration()))
        {
            retryAppearance();
        }
    }

    // A creature that cannot be controlled anymore is given back to the AI
    if(isPossessed() && (!isAlive() || isKo() || !getIsOnMap()))
        endPossession();

    // If the creature is in jail, we check if it is still standing on it (if not picked up). If
    // not, it is free
    if((mSeatPrison != nullptr) &&
       getIsOnMap())
    {
        Tile* myTile = getPositionTile();
        if(myTile == nullptr)
        {
            OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
            return;
        }

        // We check if the creature is in containment
        Room* roomPrison = myTile->getCoveringRoom();
        if((roomPrison == nullptr) ||
           (!roomPrison->isInContainment(*this)))
        {
            // it is not standing on a jail. It is free
            mSeatPrison = nullptr;
            mNeedFireRefresh = true;
        }
    }

    // The creature may be killed while temporary KO
    if((mKoTurnCounter != 0) && !isAlive())
        mKoTurnCounter = 0;

    // If the creature is KO to death or dead, we remove its particle effects
    if(!mEntityParticleEffects.empty() &&
       ((mKoTurnCounter < 0) || !isAlive()))
    {
        for(EntityParticleEffect* effect : mEntityParticleEffects)
        {
            // The strength, speed and defense factors of the effect leave the modifiers of the creature
            if(effect->getEntityParticleEffectType() == EntityParticleEffectType::creature)
            {
                CreatureEffect* creatureEffect = static_cast<CreatureParticleEffect*>(effect)->mEffect;
                if(isStackingEffect(*creatureEffect))
                    creatureEffect->releaseEffect(*this);
            }

            delete effect;
        }
        mEntityParticleEffects.clear();
    }

    // We apply creature effects if any
    for(std::vector<EntityParticleEffect*>::iterator it =  mEntityParticleEffects.begin(); it != mEntityParticleEffects.end();)
    {
        EntityParticleEffect* entityEffect = *it;
        if(entityEffect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
        {
            if(entityEffect->mNbTurnsEffect < 0)
            {
                ++it;
                continue;
            }

            if(entityEffect->mNbTurnsEffect > 0)
            {
                --entityEffect->mNbTurnsEffect;
                ++it;
                continue;
            }

            delete entityEffect;
            it = mEntityParticleEffects.erase(it);
            continue;
        }

        CreatureParticleEffect* effect = static_cast<CreatureParticleEffect*>(*it);
        if(effect->mEffect->upkeepEffect(*this))
        {
            ++it;
            continue;
        }

        // The effect ended: only its own factor leaves the strength, speed and defense modifiers
        if(isStackingEffect(*effect->mEffect))
            effect->mEffect->releaseEffect(*this);
        delete effect;
        it = mEntityParticleEffects.erase(it);
    }

    // The creature resents being held in the hand for long periods. The resentment fades once dropped
    if(mIsInHand)
        ++mNbTurnsInHand;
    else if(mNbTurnsInHand > 0)
        --mNbTurnsInHand;

    // Torture weighs on the mood while it lasts, sleeping in the lair relieves it. Both fade afterwards
    if(mTorturedThisTurn)
        ++mNbTurnsTortureMood;
    else if(mNbTurnsTortureMood > 0)
        --mNbTurnsTortureMood;

    if(mRestedThisTurn)
        ++mNbTurnsRested;
    else if(mNbTurnsRested > 0)
        --mNbTurnsRested;

    // Staying near a creature of the opposite alignment annoys, the annoyance fades afterwards
    if(isHatedCompanyNear())
        ++mNbTurnsHatedCompany;
    else if(mNbTurnsHatedCompany > 0)
        --mNbTurnsHatedCompany;

    if(getIsOnServerMap())
        upkeepCreatureDirt();

    mTorturedThisTurn = false;
    mRestedThisTurn = false;

    if(mInfirmaryMoodTurns > 0.0)
    {
        mInfirmaryMoodTurns -= 1.0;
        if(mInfirmaryMoodTurns <= 0.0)
            mInfirmaryMood = 0.0;
    }

    // Off-map living creatures stay idle; delivered bodies still advance their own corpse phases.
    if(!getIsOnMap() && isAlive())
        return;

    // The champion costs mana and leaves when the owner cannot pay it
    if(isAlive() && getDefinition()->isChampion() && handleChampionUpkeep())
        return;

    // A creature that is working is not frustrated anymore
    if(isActionInList(CreatureActionType::useRoom))
        mNbTurnsOutOfWork = 0;

    // If the creature is temporary KO, it should do nothing
    if(mKoTurnCounter > 0)
    {
        mKoTurnCounter = std::max(0.0, mKoTurnCounter - 1.0);
        if(mKoTurnCounter == 0.0)
            mKoDroppedThisFight = false;
        if(mKoTurnCounter > 0)
            return;

        if(!getGameMap()->isInEditorMode())
            setAnimationState(EntityAnimation::getup_anim, false,
                Ogre::Vector3::ZERO, false);
        computeCreatureOverlayMoodValue();
        return;
    }

    // A creature a worker pulls to its bed does nothing on its own (a KO to death one and a dead one go on below,
    // nothing here holds back a death)
    if(mIsBeingDragged && (mKoTurnCounter == 0) && isAlive())
        return;

    if(mKoTurnCounter < 0)
    {

        if(getIsOnMap())
        {
            Tile* myTile = getPositionTile();
            if(myTile == nullptr)
            {
                OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
                return;
            }
            Room* myRoom = myTile->getCoveringRoom();
            if( myRoom!=nullptr && myRoom->getType() == RoomType::arena)
            {
                
                RoomArena* myRoomArena = static_cast<RoomArena*>(myRoom);
                Ogre::Vector3 dest = myRoomArena->getGateTile()->getPosition();
                setPosition(dest);

                for(Seat* seat : mSeatsWithVisionNotified)
                {
                    if(seat->getPlayer() == nullptr)
                        continue;
                    if(!seat->getPlayer()->getIsHuman())
                        continue;

                    ServerNotification* serverNotification = new ServerNotification(
                        ServerNotificationType::entityTeleported, seat->getPlayer());
                    serverNotification->mPacket << getName() << dest;
                    ODServer::getSingleton().queueServerNotification(serverNotification);
                }
            }  
            
        }

        
        // If the counter reaches 0, the creature is dead
        mKoTurnCounter = std::min(0.0, mKoTurnCounter + 1.0);
        if(mKoTurnCounter < 0)
            return;

        mHp = 0;
        recordScriptEvent(*this, "killed");
        computeCreatureOverlayHealthValue();
        computeCreatureOverlayMoodValue();
    }

    // Handle creature death
    if (!isAlive())
    {
        // A consumed body is removed on the next upkeep, without a decay reward.
        if(mDeathCounter == std::numeric_limits<unsigned int>::max())
        {
            removeFromGameMap();
            deleteYourself();
            return;
        }
        // The corpse dirties the tile it lies on, never the tile under a carrying worker.
        if(getIsOnServerMap() && !mIsCarried)
            dirtyTileByCorpse();

        if(mDeathCounter == 0)
        {
            OD_LOG_INF("Creature=" + getName() + " RIP");
            dropCarriedEquipment();

            // The fight leaves blood on the tile where the creature fell.
            if(getIsOnServerMap() && (getPositionTile() != nullptr))
                DirtPileEntity::createOnTile(getGameMap(), getPositionTile(), DirtPileKind::blood, getDefinition()->getClassName());

            if(getIsOnServerMap() && (getSeat()->getPlayer() != nullptr))
                getSeat()->getPlayer()->notifyCreatureKilled(*this);
            if(getIsOnServerMap() && !getDefinition()->isWorker())
            {
                GhostEntity* ghost = new GhostEntity(getGameMap(), *this);
                ghost->addToGameMap();
                ghost->createMesh();
                ghost->setPosition(ghost->getPosition());
            }
            mDeathCounter = 1;
        }
        if(getDefinition()->isWorker())
        {
            if(getIsOnServerMap() && getPositionTile() != nullptr)
                Spell::fireSpellEffect(*getPositionTile(), "WorkerVanish", "");
            // Worker bodies never remain on the map, even for one extra upkeep.
            removeFromGameMap();
            deleteYourself();
            return;
        }
        if(!mIsCarried)
        {
            mCorpseTurns += 1.0;
            ConfigManager& config = ConfigManager::getSingleton();
            if(mDecayTurns < 0.0 && mCorpseTurns >= config.getCorpseLieSeconds() * ODApplication::turnsPerSecond)
            {
                mDecayTurns = 0.0;
                mNeedFireRefresh = true;
                clearDestinations(EntityAnimation::rot_anim, false, false);
                setAnimationState(EntityAnimation::rot_anim, false, Ogre::Vector3::ZERO, false);
            }
            if(mDecayTurns >= 0.0)
            {
                mDecayTurns += 1.0;
                if(mDecayTurns >= config.getCorpseDecaySeconds() * ODApplication::turnsPerSecond)
                {
                    Tile* tile = getPositionTile();
                    Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
                    if(room != nullptr && room->getType() == RoomType::crypt)
                    {
                        static_cast<RoomCrypt*>(room)->notifyCorpseDecayed(*this);
                        return;
                    }
                    else if(tile != nullptr)
                        tile->addDirt(Tile::MAX_DIRT);
                    removeFromGameMap();
                    deleteYourself();
                }
            }
        }
        return;
    }

    // If the creature is in jail, it should not auto heal or do anything
    if(mSeatPrison != nullptr)
    {
        Tile* myTile = getPositionTile();
        if(myTile == nullptr)
        {
            OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
            return;
        }

        // If the creature is in a containment room, it should use it
        Room* roomPrison = myTile->getCoveringRoom();
        if((roomPrison != nullptr) && (decreaseJobCooldown()))
            roomPrison->useRoom(*this, true);

        return;
    }

    // If we are not standing somewhere on the map, do nothing.
    if (getPositionTile() == nullptr)
    {
        OD_LOG_ERR("creature=" + getName() + " not on map position=" + Helper::toString(getPosition()));
        return;
    }

    // An old save can carry more gold than the capacity allows: the excess is dropped as a pile
    dropExcessGold();

    // The ground under the creature or under its walk path may have stopped being walkable
    // (a sold or burnt bridge), and bare lava hurts a creature that cannot walk on it
    if(getIsOnServerMap())
    {
        checkWalkPathIsStillValid();
        applyLavaDamage();
    }

    // Check to see if we have earned enough experience to level up.
    checkLevelUp();


    // Heal.
    mHp += mDefinition->getHpHealPerTurn();
    if (mHp > getMaxHp())
        mHp = getMaxHp();

    computeCreatureOverlayHealthValue();

    // The mana pool refills a little every turn, always
    regenerateMana();

    // Rogue creatures are not affected by wakefulness/hunger
    if(!getSeat()->isRogueSeat())
    {
        // The wake% passives lower the wakefulness lost per turn
        decreaseWakefulness(mDefinition->getWakefulnessLostPerTurn() * (1.0 - getSkillPassive("wake%") / 100.0));

        increaseHunger(mDefinition->getHungerGrowthPerTurn());
        increaseUrge(mDefinition->getUrgeGrowthPerTurn());
        increaseThirst(mDefinition->getThirstGrowthPerTurn());
    }

    mVisibleEnemyObjects         = getVisibleEnemyObjects();
    mVisibleAlliedObjects        = getVisibleAlliedObjects();
    mReachableAlliedObjects      = getReachableAttackableObjects(mVisibleAlliedObjects);

    // The relief from praying fades
    if(mPrayerRelief > 0)
    {
        mPrayerRelief -= ConfigManager::getSingleton().getRoomConfigInt32("TemplePrayerReliefDecayPerTurn");
        if(mPrayerRelief < 0)
            mPrayerRelief = 0;
    }

    // A nemesis brawl may end, a brawl restored from a saved game may start
    if(!mBrawlOpponent.empty())
        updateBrawl();
    else if(!mBrawlResumeOpponent.empty())
        resumeBrawl();

    // The mood from relationship events fades
    if(mRelationshipTempMood != 0)
    {
        CreatureRelationships* relationships = getGameMap()->getCreatureRelationships();
        int32_t decay = (relationships == nullptr) ? std::abs(mRelationshipTempMood) :
            relationships->getSettings().mTempMoodDecayPerTurn;
        if(mRelationshipTempMood > 0)
            mRelationshipTempMood = std::max(0, mRelationshipTempMood - decay);
        else
            mRelationshipTempMood = std::min(0, mRelationshipTempMood + decay);
    }

    // The mood set by the specials fades
    if(mSpecialMood != 0)
    {
        int32_t decay = ConfigManager::getSingleton().getRoomConfigInt32("SpecialMoodDecayPerTurn");
        if(mSpecialMood > 0)
            mSpecialMood = std::max(0, mSpecialMood - decay);
        else
            mSpecialMood = std::min(0, mSpecialMood + decay);
    }

    // The clients show the gold on the body of the carrier. They are told when it changed (cosmetic only).
    if(mGoldCarried != mGoldCarriedCosmeticNotified)
    {
        mGoldCarriedCosmeticNotified = mGoldCarried;
        fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::carriedGold), mGoldCarried,
            getGoldCapacity(), false);
    }

    // The clients show a creature without a bed lying down in the open. They are told when that changes and, for a
    // creature without a bed, now and then again (cosmetic only).
    if(!mDefinition->isWorker())
    {
        int32_t hasBed = (mHomeTile != nullptr) ? 1 : 0;
        if((hasBed != mBedNotified) ||
           ((hasBed == 0) && ((getGameMap()->getTurnNumber() % BED_STATUS_REPEAT_TURNS) == 0)))
        {
            mBedNotified = hasBed;
            fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::bedStatus), hasBed, 0, true);
        }
    }

    // Check if we should compute mood
    if(mMoodCooldownTurns > 0)
    {
        --mMoodCooldownTurns;
    }
    // Rogue creatures do not have mood
    else if(!getSeat()->isRogueSeat())
    {
        computeMood();
        computeCreatureOverlayMoodValue();
        mMoodCooldownTurns = Random::Int(0, 5);
    }

    if(mMoodValue < CreatureMoodLevel::Furious)
    {
        mNbTurnFurious = -1;
    }
    else
    {
        // If the creature is furious for too long, it will become rogue
        if(mNbTurnFurious < 0)
            mNbTurnFurious = 0;
        else
            ++mNbTurnFurious;

        if(mNbTurnFurious >= ConfigManager::getSingleton().getNbTurnsFuriousMax())
        {
            // We couldn't leave the dungeon in time, we become rogue
            fireChatMsgBecameRogue();

            Seat* rogueSeat = getGameMap()->getSeatRogue();
            changeSeat(rogueSeat);
        }
    }

    ++mNbTurnsWithoutBattle;
    // The turn the counter goes from 0 to 1 is the end of a fight: the creature gets a little dirty
    // unless it was already dirtied by being knocked out in this fight. A creature that never fought (the counter
    // starts at 0 on spawn and load) gets nothing.
    if(mNbTurnsWithoutBattle == 1)
    {
        if(mFoughtSinceFightEnd && !mDirtKoThisFight)
            increaseCreatureDirt(ConfigManager::getSingleton().getDirtConfigDouble("CreatureDirtPerFightWon"));
        mDirtKoThisFight = false;
        mFoughtSinceFightEnd = false;
    }

    // The pit mood fades towards 0
    if(mPitMood != 0.0)
    {
        double decay = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("PitMoodDecay", DEFAULT_PIT_MOOD_DECAY_PER_SECOND)
            / ODApplication::turnsPerSecond;
        if(mPitMood > 0.0)
            mPitMood = std::max(0.0, mPitMood - decay);
        else
            mPitMood = std::min(0.0, mPitMood + decay);
    }

    // The merchant contribution fades by its configured points per simulation turn.
    if(mMerchantMood != 0.0)
    {
        const double decay = ConfigManager::getSingleton().getRoomConfigDouble("MerchantMoodDecay");
        if(mMerchantMood > 0.0) mMerchantMood = std::max(0.0, mMerchantMood - decay);
        else mMerchantMood = std::min(0.0, mMerchantMood + decay);
    }
    // The casino mood fades towards 0
    if(mCasinoMood != 0.0)
    {
        double decay = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("CasinoMoodDecay", 3.0)
            / ODApplication::turnsPerSecond;
        if(mCasinoMood > 0.0)
            mCasinoMood = std::max(0.0, mCasinoMood - decay);
        else
            mCasinoMood = std::min(0.0, mCasinoMood + decay);
    }

    // The drunkenness falls, the tavern mood and the hangover run out
    upkeepTavernState();

    // The spa mood fades and the relaxation runs out
    upkeepSpaState();

    // The skill tree: reset window, reset and the active skills of changed ranks
    upkeepSkillTree();

    decidePotion();

    // A frozen creature can neither move nor fight
    if(isFrozen())
    {
        if(!mActions.empty())
        {
            clearActionQueue();
            clearDestinations(EntityAnimation::idle_anim, true, true);
        }
        else if(isMoving())
        {
            clearDestinations(EntityAnimation::idle_anim, true, true);
        }
        return;
    }

    // A chicken cannot fight, use skills or work. It only wanders around
    if(isHexenHen())
    {
        handleHexenHenUpkeep();
        return;
    }

    // The recovery display follows the skill timers in both AI and possessed control.
    if(mAttackRecoveryTurns > 0.0)
    {
        mAttackRecoveryTurns = std::max(0.0, mAttackRecoveryTurns - 1.0);
        mNeedFireRefresh = true;
    }

    // If a player controls the creature, its other actions are paused. Only the possessed
    // action runs and the movement comes from the player input
    if(isPossessed())
    {
        if(mActions.empty() || (mActions.back()->getType() != CreatureActionType::possessed))
            pushAction(Utils::make_unique<CreatureActionPossessed>(*this));

        // The creature skills keep recovering while the player controls the creature
        for(CreatureSkillData& skillData : mSkillData)
        {
            // The timers keep their fractions: they count down while positive and are not clamped to 0,
            // so the negative remainder carries over to the next use
            if(skillData.mWarmup > 0.0)
                skillData.mWarmup -= 1.0;

            if(skillData.mCooldown > 0.0)
                skillData.mCooldown -= 1.0;
        }

        std::function<bool()> possessedFunc = mActions.back()->action();
        possessedFunc();
        return;
    }

    bool isWarmUp = false;
    // We use creature skills if we can
    for(CreatureSkillData& skillData : mSkillData)
    {
        if(skillData.mWarmup > 0.0)
        {
            skillData.mWarmup -= 1.0;
            isWarmUp = true;
        }

        // The cooldown counts down while positive (no clamp to 0); the skill is usable when it is <= 0
        if(skillData.mCooldown > 0.0)
            skillData.mCooldown -= 1.0;

        if(skillData.mCooldown > 0.0)
            continue;

        if(!skillData.mSkill->canBeUsedBy(this))
            continue;

        // A skill that costs more mana than the creature has is not used, like a skill on cooldown
        if(!hasManaFor(*skillData.mSkill))
            continue;

        if(!skillData.mSkill->tryUseSupport(*getGameMap(), this))
            continue;

        // The mana is paid when the skill starts
        payManaFor(*skillData.mSkill);

        // The new cooldown and warmup are added, so the remainder of the last turn carries over
        skillData.mCooldown += skillData.mSkill->getCooldownNbTurns();
        skillData.mWarmup += skillData.mSkill->getWarmupNbTurns();
        // Successful self-casts use the same recovery display as attacks.
        mAttackRecoveryDuration = std::max(static_cast<double>(skillData.mWarmup), skillData.mCooldown);
        mAttackRecoveryTurns = mAttackRecoveryDuration;
        ++mAttackRecoverySerial;
        mNeedFireRefresh = true;

        if(skillData.mWarmup > 0.0)
            isWarmUp = true;
    }

    // If a warmup is active, we do nothing
    if(isWarmUp)
        return;

    decidePrioritaryAction();
    handleHeartDefence();
    handleUrge();

    // Keep combat in its current attack tile; free waiting creatures may use adjacent floor space.
    const CreatureActionType standingAction = mActions.empty() ? CreatureActionType::nb : mActions.back()->getType();
    Room* standingRoom = getPositionTile()->getCoveringRoom();
    const bool freeRoomStand = CreatureAction::isRoomWorkAction(standingAction) && standingRoom != nullptr &&
        (standingRoom->getType() == RoomType::temple || standingRoom->getType() == RoomType::guardRoom ||
         standingRoom->getType() == RoomType::arena || standingRoom->getType() == RoomType::hatchery);
    // Prayer spots, guard posts and watch banners remain bound to their assigned tile.
    const bool adjacentStand = mActions.empty() || (freeRoomStand &&
        (standingRoom->getType() == RoomType::arena || standingRoom->getType() == RoomType::hatchery));
    if(!isMoving() && (mActions.empty() || standingAction == CreatureActionType::fight ||
        standingAction == CreatureActionType::fightFriendly || standingAction == CreatureActionType::watchBanner || freeRoomStand))
    {
        const Ogre::Vector2 position(getPosition().x, getPosition().y);
        std::vector<Ogre::Vector2> path{position};
        if(RoomObjectNavigation::separate(*this, path, adjacentStand, freeRoomStand ? standingRoom : nullptr) && path.back() != position)
        {
            setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
            pushAction(Utils::make_unique<CreatureActionWalkToTile>(*this));
            return;
        }
    }

    // The loopback variable allows creatures to begin processing a new
    // action immediately after some other action happens.
    bool loopBack = false;
    unsigned int loops = 0;

    mActionTry.clear();

    do
    {
        ++loops;
        loopBack = false;

        if (mActions.empty())
        {
            loopBack = handleIdleAction();
            OD_LOG_DBG("creature=" + getName() + " action queue empty, defaulting to idle, result=" + (loopBack?"1":"0"));
        }
        else
        {
            CreatureAction* act = mActions.back().get();
            // We save the action type here because the action may be removed after calling
            // the action function
            CreatureActionType actType = act->getType();
            std::function<bool()> func = act->action();
            loopBack = func();
            OD_LOG_DBG("creature=" + getName() + " trying action=" + CreatureAction::toString(actType) + ", result=" + std::string(loopBack?"1":"0"));
        }
    } while (loopBack && loops < 20);

    refreshGhostHuntVisuals();
    if(!mActions.empty())
        mActions.back().get()->increaseNbTurnActive();

    for(std::unique_ptr<CreatureAction>& creatureAction : mActions)
        creatureAction.get()->increaseNbTurn();

    if(loops >= 20)
    {
        OD_LOG_INF("> 20 loops in Creature::doUpkeep name:" + getName() +
                " seat id: " + Helper::toString(getSeat()->getId()) + ". Breaking out..");
    }
}

void Creature::decidePrioritaryAction()
{
    const bool patient = isActionInList(CreatureActionType::infirmaryRest);
    const bool tooWeakToRise = getHP() * 100.0 < getMaxHp() * ConfigManager::getSingleton().getRoomConfigDouble("DormitoryWoundedCarryHpPercent");
    if((patient || isActionInList(CreatureActionType::sleep)) && tooWeakToRise)
        return;
    if(patient && getVisibleEnemyObjects().empty())
        return;
    for(const CreatureBehaviour* behaviour : getDefinition()->getCreatureBehaviours())
    {
        // A patient may answer visible enemies using its configured combat policy, but cannot leave treatment for a job.
        if(patient && behaviour->getName() != CreatureBehaviourAttackEnemy::mNameCreatureBehaviourAttackEnemy &&
            behaviour->getName() != CreatureBehaviourFleeWhenWeak::mNameCreatureBehaviourFleeWhenWeak &&
            behaviour->getName() != CreatureBehaviourFleeWhenOutmatched::mNameCreatureBehaviourFleeWhenOutmatched)
            continue;
        if(!behaviour->processBehaviour(*this))
            return;
    }
}

void Creature::handleHeartDefence()
{
    if(isActionInList(CreatureActionType::infirmaryRest) ||
        (isActionInList(CreatureActionType::sleep) && getHP() * 100.0 < getMaxHp() *
            ConfigManager::getSingleton().getRoomConfigDouble("DormitoryWoundedCarryHpPercent")))
        return;
    if(!getDefinition()->isHeartDefenceRunner())
        return;

    Seat* seat = getSeat();
    if(seat == nullptr || !seat->getHeartDefenceActive())
        return;

    if(isActionInList(CreatureActionType::goDefendHeart))
        return;

    // Existing combat and retreat decisions take priority over gathering at the defence point.
    if(isActionInList(CreatureActionType::fight) || isActionInList(CreatureActionType::flee))
        return;

    // The heart defence is on: drop the current job and run to the defence point
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionGoDefendHeart>(*this));
}

//! \brief Chooses equipment, trade and visible item actions among the existing idle needs.
bool Creature::handleIdleAction()
{
    setAnimationState(EntityAnimation::idle_anim);

    if (mDefinition->isWorker())
    {
        // A trap of the keeper that used up its shots is armed again before the other jobs
        if(!hasActionBeenTried(CreatureActionType::reloadTrap) && getSeat()->getPlayer()->isWorkerReloadShareOpen() &&
           CreatureActionReloadTrap::tryStart(*this))
            return true;

        // Decide what to do
        std::vector<CreatureActionType> workerActions = getSeat()->getPlayer()->getWorkerPreferredActions(*this);
        for(CreatureActionType actionType : workerActions)
        {
            if(hasActionBeenTried(actionType))
                continue;

            switch(actionType)
            {
                case CreatureActionType::searchEntityToCarry:
                    pushAction(Utils::make_unique<CreatureActionSearchEntityToCarry>(*this, false));
                    return true;
                case CreatureActionType::searchGroundTileToClaim:
                    pushAction(Utils::make_unique<CreatureActionSearchGroundTileToClaim>(*this, false));
                    return true;
                case CreatureActionType::searchTileToDig:
                    pushAction(Utils::make_unique<CreatureActionSearchTileToDig>(*this, false));
                    return true;
                case CreatureActionType::searchWallTileToClaim:
                    pushAction(Utils::make_unique<CreatureActionSearchWallTileToClaim>(*this, false));
                    return true;
                case CreatureActionType::searchDirtToClean:
                    pushAction(Utils::make_unique<CreatureActionSearchDirtToClean>(*this));
                    return true;
                default:
                    OD_LOG_ERR("name=" + getName() + ", unexpected worker action=" + CreatureAction::toString(actionType));
                    break;
            }
        }
    }

    // A standing order of the level script (go to a point, attack a dungeon, wait, ...) comes first
    if(LevelScriptRunner::doCreatureOrder(*this))
        return false;

    // The champion has no needs. It charges at the enemies and waits when there is none
    if(mDefinition->isChampion())
    {
        handleChampionIdle();
        return false;
    }

    // A creature in the group of a possessed creature follows it. Fights are handled by the
    // prioritary actions as usual
    if(isInPossessionGroup() && followPossessionLeader())
        return false;

    // We check if we are looking for our fee
    if(!mDefinition->isWorker() &&
       !hasActionBeenTried(CreatureActionType::getFee) &&
       (mGoldFee > 0))
    {
        pushAction(Utils::make_unique<CreatureActionGetFee>(*this));
        return true;
    }

    decideEquipment();
    if(CreatureMerchantAI::decideTrade(*this))
        return true;
    if(!mDefinition->isWorker() && !hasActionBeenTried(CreatureActionType::pickupItem))
    {
        pushAction(Utils::make_unique<CreatureActionPickupItem>(*this));
        return true;
    }

    if(CreatureMerchantAI::decideSoulCrystal(*this))
        return true;

    // We check if there is a go to war spell reachable
    std::vector<Spell*> callToWars = getGameMap()->getSpellsBySeatAndType(getSeat(), SpellType::callToWar);
    if(!callToWars.empty())
    {
        std::vector<Spell*> reachableCallToWars;
        for(Spell* callToWar : callToWars)
        {
            if(!callToWar->getIsOnMap())
                continue;

            Tile* callToWarTile = callToWar->getPositionTile();
            if(callToWarTile == nullptr)
                continue;

            if (!getGameMap()->pathExists(this, getPositionTile(), callToWarTile))
                continue;

            reachableCallToWars.push_back(callToWar);
        }

        if(!reachableCallToWars.empty())
        {
            // We go there
            uint32_t index = Random::Uint(0,reachableCallToWars.size()-1);
            Spell* callToWar = reachableCallToWars[index];
            Tile* callToWarTile = callToWar->getPositionTile();
            std::list<Tile*> tempPath = getGameMap()->path(this, callToWarTile);
            // If we are 5 tiles from the call to war, we don't go there
            if(tempPath.size() >= 5)
            {
                std::vector<Ogre::Vector2> path;
                tileToVector2(tempPath, path, true, 0.0);
                setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true);
                pushAction(Utils::make_unique<CreatureActionGoCallToWar>(*this));
                return false;
            }
        }
    }

    // Check to see if we have found a "home" tile where we can sleep. Even if we are not sleepy,
    // we want to have a bed
    if (!mDefinition->isWorker() &&
        !hasActionBeenTried(CreatureActionType::findHome) &&
        (mHomeTile == nullptr) &&
        (Random::Double(0.0, 1.0) < 0.5))
    {
        pushAction(Utils::make_unique<CreatureActionFindHome>(*this, false));
        return true;
    }

    // If we are sleepy, we go to sleep
    if (!mDefinition->isWorker() &&
        !hasActionBeenTried(CreatureActionType::sleep) &&
        (mHomeTile != nullptr) &&
        (Random::Double(20.0, 30.0) > mWakefulness))
    {
        pushAction(Utils::make_unique<CreatureActionSleep>(*this));
        return true;
    }

    // If we are drunk enough, we vomit once per drunk episode (at the next idle turn)
    if (!mDefinition->isWorker() &&
        !mVomited &&
        (mDrunk > 0.0) &&
        (mDrunk >= ConfigManager::getSingleton().getTavernConfigDouble("VomitAt")))
    {
        mVomited = true;
        pushAction(Utils::make_unique<CreatureActionVomit>(*this));
        return true;
    }

    // If we are hungry, we go to eat
    if (!mDefinition->isWorker() &&
        !hasActionBeenTried(CreatureActionType::searchFood) &&
        (Random::Double(70.0, 80.0) < mHunger))
    {
        pushAction(Utils::make_unique<CreatureActionSearchFood>(*this, false));
        return true;
    }

    // If we are thirsty, we go to a tavern. Without a tavern nothing happens here: the thirst keeps rising and
    // its mood malus acts
    if (!mDefinition->isWorker() &&
        mDefinition->hasThirst() &&
        !hasActionBeenTried(CreatureActionType::searchDrink) &&
        (mThirst >= ConfigManager::getSingleton().getTavernConfigDouble("ThirstSeek")))
    {
        pushAction(Utils::make_unique<CreatureActionSearchDrink>(*this, false));
        return true;
    }

    // If we are in a bad mood or have a hangover, we go to a lava spa. Without a spa that can take us nothing
    // happens here and we try again at the next search
    if (wantsSpaBath() &&
        !hasActionBeenTried(CreatureActionType::searchSpa))
    {
        pushAction(Utils::make_unique<CreatureActionSearchSpa>(*this));
        return true;
    }

    // If we have to relieve ourselves, we go to a toilet. Without a toilet room nothing happens here: the
    // creature goes on until the urge is too strong
    if (!mDefinition->isWorker() &&
        !hasActionBeenTried(CreatureActionType::searchToilet) &&
        (mUrge >= ConfigManager::getSingleton().getDirtConfigDouble("UrgeSeek")))
    {
        pushAction(Utils::make_unique<CreatureActionSearchToilet>(*this));
        return true;
    }

    if(!mDefinition->isWorker() && !hasActionBeenTried(CreatureActionType::stealItem) && Random::Double(0.0, 1.0) < 0.2)
    {
        pushAction(Utils::make_unique<CreatureActionStealItem>(*this));
        return true;
    }

    // We try to steal some gold if there is some on the ground. Only creatures
    // with a StealGold amount in their definition (thieves) do that
    if (!mDefinition->isWorker() &&
        (mDefinition->getStealGold() > 0) &&
        !hasActionBeenTried(CreatureActionType::stealFreeGold) &&
        (Random::Uint(0, 10) > 8))
    {
        pushAction(Utils::make_unique<CreatureActionStealFreeGold>(*this));
        return true;
    }

    // Creatures with a dig rate (tunnellers) dig their way to an enemy heart they cannot reach on foot
    if (!mDefinition->isWorker() &&
        (getDigRate() > 0.0) &&
        !hasActionBeenTried(CreatureActionType::tunnel) &&
        (Random::Uint(0, 10) > 6))
    {
        pushAction(Utils::make_unique<CreatureActionTunnel>(*this));
        return true;
    }

    // Otherwise, we try to work
    if (!mDefinition->isWorker() &&
        !hasActionBeenTried(CreatureActionType::searchJob) &&
        (Random::Double(0.0, 1.0) < 0.4))
    {
        pushAction(Utils::make_unique<CreatureActionSearchJob>(*this, false));
        return true;
    }

    // Any creature.

    // Workers should move around randomly at large jumps.  Non-workers either wander short distances or follow workers.
    Tile* tileDest = nullptr;
    // Define reachable tiles from the tiles within radius
    std::vector<Tile*> reachableTiles;
    for (Tile* tile: mTilesWithinSightRadius)
    {
        // A tile this creature cannot enter (closed door of its own side, fenced room it is not in) is
        // in the same area as the creature for the flood fill but can never be a walking destination
        if (canGoThroughTile(tile) && getGameMap()->pathExists(this, getPositionTile(), tile))
            reachableTiles.push_back(tile);
    }
    // A random walking target must be a tile with a free standing point, not one covered by furniture
    RoomObjectNavigation::keepTilesWithStandingPosition(*this, reachableTiles);

    if (!mDefinition->isWorker())
    {
        // Non-workers only.

        // Check to see if we want to try to follow a worker around or if we want to try to explore.
        double r = Random::Double(0.0, 1.0);
        if (r < 0.7)
        {
            bool workerFound = false;
            // Try to find a worker to follow around.
            for (unsigned int i = 0; !workerFound && i < mReachableAlliedObjects.size(); ++i)
            {
                // Check to see if we found a worker.
                if (mReachableAlliedObjects[i]->getObjectType() == GameEntityType::creature
                    && static_cast<Creature*>(mReachableAlliedObjects[i])->mDefinition->isWorker())
                {
                    // We found a worker so find a tile near the worker to walk to.  See if the worker is digging.
                    Tile* tempTile = mReachableAlliedObjects[i]->getCoveredTile(0);
                    if (static_cast<Creature*>(mReachableAlliedObjects[i])->isActionInList(CreatureActionType::digTile))
                    {
                        // Worker is digging, get near it since it could expose enemies.
                        int x = static_cast<int>(static_cast<double>(tempTile->getX()) + 3.0
                                * Random::gaussianRandomDouble());
                        int y = static_cast<int>(static_cast<double>(tempTile->getY()) + 3.0
                                * Random::gaussianRandomDouble());
                        tileDest = getGameMap()->getTile(x, y);
                    }
                    else
                    {
                        // Worker is not digging, wander a bit farther around the worker.
                        int x = static_cast<int>(static_cast<double>(tempTile->getX()) + 8.0
                                * Random::gaussianRandomDouble());
                        int y = static_cast<int>(static_cast<double>(tempTile->getY()) + 8.0
                                * Random::gaussianRandomDouble());
                        tileDest = getGameMap()->getTile(x, y);
                    }
                    workerFound = true;
                }

                // If there are no workers around, choose tiles far away to "roam" the dungeon.
                if (!workerFound)
                {
                    if (!reachableTiles.empty())
                    {
                        tileDest = reachableTiles[static_cast<unsigned int>(Random::Double(0.6, 0.8)
                                                                           * (reachableTiles.size() - 1))];
                    }
                }
            }
        }
        else
        {
            // Randomly choose a tile near where we are standing to walk to.
            if (!reachableTiles.empty())
            {
                unsigned int tileIndex = static_cast<unsigned int>(reachableTiles.size()
                                                                   * Random::Double(0.1, 0.3));
                tileDest = reachableTiles[tileIndex];
            }
        }
    }
    else
    {
        // Workers only.

        // Choose a tile far away from our current position to wander to.
        if (!reachableTiles.empty())
        {
            tileDest = reachableTiles[Random::Uint(reachableTiles.size() / 2,
                                                   reachableTiles.size() - 1)];
        }
    }

    // A spot picked around a worker is not taken from the reachable tiles. It can be a wall, a tile that
    // cannot be entered or a tile in another closed-off area: then we walk to a reachable tile instead of
    // asking for a route that does not exist every turn
    if((tileDest != nullptr) &&
       (!canGoThroughTile(tileDest) || !getGameMap()->pathExists(this, getPositionTile(), tileDest) ||
        !RoomObjectNavigation::hasStandingPosition(*this, *tileDest)))
    {
        tileDest = nullptr;
        if(!reachableTiles.empty())
            tileDest = reachableTiles[Random::Uint(0, reachableTiles.size() - 1)];
    }

    if(setDestination(tileDest))
        return false;

    // Retry failed wandering next turn, not repeatedly in this upkeep.
    return false;
}

//! \brief Selects existing combat targets and attack tiles, preferring legal body-free stances before crowded fallback.
bool Creature::searchBestTargetInList(const std::vector<GameEntity*>& listObjects, const std::vector<Tile*>& tilesFilter, GameEntity*& attackedEntity,
        Tile*& attackedTile, Tile*& positionTile, CreatureSkillData*& creatureSkillData)
{
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("name=" + getName() + ", position=" + Helper::toString(getPosition()));
        return false;
    }

    GameEntity* entityFlee = nullptr;
    // Closest creature
    GameEntity* entityAttack = nullptr;
    Tile* tileAttack = nullptr;
    CreatureSkillData* skillData = nullptr;
    Tile* tilePosition = nullptr;
    // Distance to the target, divided by its threat factor and weighted by its combat class (see below)
    double closestDistWeighted = -1.0;
    double ownThreat = getThreat();
    // We try to attack creatures first
    for(GameEntity* entity : listObjects)
    {
        // Invisible creatures cannot be seen by the enemy and are not targeted
        if((entity->getObjectType() == GameEntityType::creature) &&
           static_cast<Creature*>(entity)->isInvisible())
        {
            continue;
        }

        // Strong enemy creatures are targeted first: the more threatening a creature is compared to us,
        // the closer it appears to be. Other entities are not weighted.
        double threatFactor = 1.0;
        if((entity->getObjectType() == GameEntityType::creature) && (ownThreat > 0.0))
        {
            threatFactor = static_cast<Creature*>(entity)->getThreat() / ownThreat;
            threatFactor = std::max(0.5, std::min(2.0, threatFactor));
        }

        GameEntity* entityAttackCheck = nullptr;
        Tile* tileAttackCheck = nullptr;
        CreatureSkillData* skillDataCheck = nullptr;
        int closestDistCheck = -1;
        // We check the closest tile of this entity
        std::vector<Tile*> coveredTiles = entity->getCoveredTiles();
        for(Tile* tile : coveredTiles)
        {
            if(std::find(mVisibleTiles.begin(), mVisibleTiles.end(), tile) == mVisibleTiles.end())
                continue;

            int dist = static_cast<int>(Pathfinding::squaredDistanceTile(*tile, *myTile) / threatFactor);
            if((closestDistCheck != -1) && (dist >= closestDistCheck))
                continue;

            // We found a tile closer
            // Note that we don't break because if this entity is on more than 1 tile,
            // we want to attack the closest tile
            closestDistCheck = dist;
            entityAttackCheck = entity;
            tileAttackCheck = tile;
        }

        if((entityAttackCheck == nullptr) || (tileAttackCheck == nullptr))
            continue;

        // We check if this entity is closer than the other one (if any), weighted by the combat class
        double closestDistCheckWeighted = static_cast<double>(closestDistCheck) * getTargetDistanceFactor(*this, *entityAttackCheck);
        if((closestDistWeighted >= 0.0) && (closestDistCheckWeighted >= closestDistWeighted))
            continue;

        // We check if we are supposed to flee from this entity
        if((entityFlee == nullptr) && entityAttackCheck->isDangerous(this, closestDistCheck))
            entityFlee = entityAttackCheck;

        // If we found a suitable enemy, we check if we can attack it
        double skillRangeMax = 0.0;
        for(CreatureSkillData& skillDataTmp : mSkillData)
        {
            if(skillDataTmp.mCooldown > 0.0)
                continue;

            if(!skillDataTmp.mSkill->canBeUsedBy(this))
                continue;

            // A shot or skill that costs more mana than the creature has is skipped, like a skill on cooldown
            if(!hasManaFor(*skillDataTmp.mSkill))
                continue;

            double skillRange = skillDataTmp.mSkill->getRangeMax(this, entityAttackCheck);
            if(skillRange <= 0)
                continue;
            if(skillRange < skillRangeMax)
                continue;

            skillRangeMax = skillRange;
            skillDataCheck = &skillDataTmp;
        }
        if(skillRangeMax <= 0)
            continue;

        // Check if we can attack from our position
        int rangeTarget = Pathfinding::squaredDistanceTile(*tileAttackCheck, *myTile);
        const bool inRange = rangeTarget <= (skillRangeMax * skillRangeMax);
        bool freePosition = false;
        if(inRange)
        {
             // We can attack
             tilePosition = myTile;
             entityAttack = entityAttackCheck;
             tileAttack = tileAttackCheck;
             skillData = skillDataCheck;
             closestDistWeighted = closestDistCheckWeighted;
             std::vector<Ogre::Vector2> standing{Ogre::Vector2(getPosition().x, getPosition().y)};
             if(RoomObjectNavigation::separate(*this, standing))
                 continue;
        }

        // We check if we can attack from somewhere. To do that, we check
        // from the target point of view if there is a tile with visibility within range
        int skillRangeMaxInt = static_cast<int>(skillRangeMax);
        int skillRangeMaxIntSquared = skillRangeMaxInt * skillRangeMaxInt;
        int bestScoreAttack = -1;
        std::vector<Tile*> tiles;
        if(tilesFilter.empty())
            tiles = getGameMap()->visibleTiles(tileAttackCheck->getX(), tileAttackCheck->getY(), skillRangeMaxInt);
        else
        {
            float radiusSquared = skillRangeMaxInt * skillRangeMaxInt;
            for(Tile* tile : tilesFilter)
            {
                float dist = Pathfinding::squaredDistanceTile(*tileAttackCheck, *tile);
                if(dist > radiusSquared)
                    continue;

                tiles.push_back(tile);
            }
        }
        for(Tile* tile : tiles)
        {
            if(tile->isFullTile())
                continue;

            if(!getGameMap()->pathExists(this, myTile, tile))
                continue;

            // A tile this creature cannot enter (locked door, barricade, fence) has no walkable path
            if((tile != myTile) && !canGoThroughTile(tile))
                continue;

            std::vector<Ogre::Vector2> standing{tile->getPosition2d()};
            const bool freeTile = RoomObjectNavigation::separate(*this, standing);
            if(!freeTile && (freePosition || inRange))
                continue;
            if(freeTile && !freePosition)
                bestScoreAttack = -1;

            int distFoeTmp = Pathfinding::squaredDistanceTile(*tile, *tileAttackCheck);
            int distAttackTmp = Pathfinding::squaredDistanceTile(*tile, *myTile);
            // We compute a score for each tile. We will choose the best one. Note that we try to be as close as possible
            // from the fightIdleDist but by walking the less possible. We need to find a compromise
            int scoreAttack = std::abs(skillRangeMaxIntSquared - distFoeTmp) * 2 + distAttackTmp;
            // Support creatures keep their distance, flankers prefer to get behind the target
            CreatureDefinition::CombatClass combatClass = getDefinition()->getCombatClass();
            if((combatClass == CreatureDefinition::CombatSupport) && (distFoeTmp < skillRangeMaxIntSquared))
                scoreAttack += (skillRangeMaxIntSquared - distFoeTmp) * 2;
            else if(combatClass == CreatureDefinition::CombatFlanker)
            {
                int behindTarget = (tile->getX() - tileAttackCheck->getX()) * (myTile->getX() - tileAttackCheck->getX()) +
                    (tile->getY() - tileAttackCheck->getY()) * (myTile->getY() - tileAttackCheck->getY());
                if(behindTarget < 0)
                    scoreAttack /= 2;
            }
            if((bestScoreAttack != -1) && (bestScoreAttack <= scoreAttack))
                continue;

            // We found a better target
            bestScoreAttack = scoreAttack;
            freePosition = freeTile;
            tilePosition = tile;
            entityAttack = entityAttackCheck;
            tileAttack = tileAttackCheck;
            skillData = skillDataCheck;
            closestDistWeighted = closestDistCheckWeighted;
            // We don't break because there might be a better spot
        }
    }

    // If there is a dangerous entity and we cannot attack, we should try to get away
    if((entityFlee != nullptr) && (skillData == nullptr))
    {
        // Let's try to run to the closest spot at the distance closest to the fight idle distance
        Tile* tileEntityFlee = entityFlee->getPositionTile();
        if(tileEntityFlee == nullptr)
        {
            OD_LOG_ERR("entity=" + entityFlee->getName() + ", position=" + Helper::toString(entityFlee->getPosition()));
            return false;
        }

        int bestScoreFlee = -1;
        int32_t fightIdleDist = getDefinition()->getFightIdleDist();
        Tile* fleeTile = nullptr;
        std::vector<Tile*> tiles;
        if(tilesFilter.empty())
            tiles = getGameMap()->visibleTiles(tileEntityFlee->getX(), tileEntityFlee->getY(), fightIdleDist);
        else
        {
            float radiusSquared = fightIdleDist * fightIdleDist;
            for(Tile* tile : tilesFilter)
            {
                float dist = Pathfinding::squaredDistanceTile(*tileEntityFlee, *tile);
                if(dist > radiusSquared)
                    continue;

                tiles.push_back(tile);
            }
        }
        int32_t fightIdleDistSquared = fightIdleDist * fightIdleDist;
        for(Tile* tile : tiles)
        {
            if(tile->isFullTile())
                continue;

            if(!getGameMap()->pathExists(this, myTile, tile))
                continue;

            // A tile this creature cannot enter has no walkable path
            if((tile != myTile) && !canGoThroughTile(tile))
                continue;

            int distFoeTmp = Pathfinding::squaredDistanceTile(*tile, *tileEntityFlee);
            int fleeDistTmp = Pathfinding::squaredDistanceTile(*tile, *myTile);
            // We compute a score for each tile. We will choose the best one. Note that we try to be as close as possible
            // from the fightIdleDist but by walking the less possible. We need to find a compromise
            int scoreFlee = std::abs(fightIdleDistSquared - distFoeTmp) * 2 + fleeDistTmp;
            if((bestScoreFlee != -1) && (bestScoreFlee <= scoreFlee))
                continue;

            bestScoreFlee = scoreFlee;
            fleeTile = tile;
        }

        if(fleeTile == nullptr)
            return false;

        attackedEntity = nullptr;
        attackedTile = nullptr;
        positionTile = fleeTile;
    }
    else if ((entityAttack == nullptr) ||
        (tileAttack == nullptr) ||
        (tilePosition == nullptr))
    {
        // We couldn't find an entity to attack
        return false;
    }
    else
    {
        attackedEntity = entityAttack;
        attackedTile = tileAttack;
        creatureSkillData = skillData;
        positionTile = tilePosition;
    }

    return true;
}

void Creature::engageAlliedNaturalEnemy(Creature& attackerCreature)
{
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("name=" + getName() + ", pos=" + Helper::toString(getPosition()));
        return;
    }

    // If we are already fighting, do nothing
    if(isActionInList(CreatureActionType::fight))
        return;

    // When fighting a natural enemy, we always fight to death
    // We want to notify the player that his creatures are fighting
    fightCreature(attackerCreature, false, true);
}

double Creature::getMoveSpeed() const
{
    return getMoveSpeed(getPositionTile());
}

double Creature::getMoveSpeed(Tile* tile) const
{
    if(tile == nullptr)
    {
        OD_LOG_ERR("creature=" + getName());
        return 1.0;
    }

    // A tired creature drags its feet. Server and clients both use the mood bit Tired
    // (see isTired), so both move it at the same slower speed
    double tiredFactor = 1.0;
    if(isTired())
        tiredFactor = ConfigManager::getSingleton().getTiredWalkSpeedFactor();

    // A badly hurt creature limps along: it moves slower too (tired and hurt add up, see getLowHealthWalkFactor)
    tiredFactor *= getLowHealthWalkFactor();

    // A staggering (drunk) creature is slower too (see isStaggering)
    if(isStaggering())
        tiredFactor *= ConfigManager::getSingleton().getTavernConfigDouble("StaggerSpeedFactor");

    // A worker that pulls a hurt creature is slower (clip drag_anim). The pulled creature does not walk
    // by itself: it slides after the worker a bit faster than the worker pulls, so it never falls behind.
    // Server and clients know both by the clip name, so both move them at the same speed
    const std::string& clip = getAnimationStateName();
    if(clip == EntityAnimation::drag_anim)
    {
        tiredFactor *= getDragWorkerSpeedFactor();
    }
    else if(clip == EntityAnimation::dragged_anim)
    {
        const CreatureDefinition* workerDefinition = ConfigManager::getSingleton().getCreatureDefinitionDefaultWorker();
        double workerSpeed = (workerDefinition != nullptr) ? workerDefinition->getMoveSpeedGround() : 1.0;
        ConfigManager& config = ConfigManager::getSingleton();
        return workerSpeed * getDragWorkerSpeedFactor() *
            std::max(1.0, config.getRoomConfigDoubleOrDefault("DormitoryWoundedDragFollowSpeedFactor", WOUNDED_DRAG_FOLLOW_SPEED_FACTOR_DEFAULT));
    }

    if(getIsOnServerMap())
    {
        // Check if the covering building allows this creature to go through
        if(tile->getCoveringBuilding() != nullptr)
            return tile->getCoveringBuilding()->getCreatureSpeed(this, tile) * tiredFactor;
        else
            return tile->getCreatureSpeedDefault(this) * tiredFactor;
    }
    else
    {
        if(tile->getHasBridge())
            return getMoveSpeedGround() * tiredFactor;
        else
            return tile->getCreatureSpeedDefault(this) * tiredFactor;
    }
}

double Creature::getDragWorkerSpeedFactor()
{
    double factor = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedDragWorkerSpeedFactor", WOUNDED_DRAG_WORKER_SPEED_FACTOR_DEFAULT);
    return std::max(0.1, std::min(1.0, factor));
}

bool Creature::isLowHealthWalkStage(uint32_t healthStage)
{
    // The health stage (0 = unhurt, 1 to 6 = lost a sixth more each, 7 = no health left) is known on the
    // server and on the clients. Stage s means the health is below 100 * (1 - (s - 1) / 6) percent, so
    // a creature is badly hurt from the first stage that lies completely below the configured percent
    const double nbSteps = static_cast<double>(NB_OVERLAY_HEALTH_VALUES - 2);
    double thresholdPercent = ConfigManager::getSingleton().getLowHealthWalkThresholdPercent();
    double firstStage = std::ceil((FULL_HEALTH_PERCENT - thresholdPercent) / FULL_HEALTH_PERCENT * nbSteps
        - HEALTH_STAGE_ROUNDING_TOLERANCE) + 1.0;
    return static_cast<double>(healthStage) >= firstStage;
}

double Creature::getLowHealthWalkFactor() const
{
    if(!isLowHealthWalking())
        return 1.0;

    // A creature type can have its own factor (same limits as the global one), the global one is the default
    if((mDefinition != nullptr) && (mDefinition->getLowHealthWalkSpeedFactor() >= 0.0))
        return std::max(0.2, std::min(1.0, mDefinition->getLowHealthWalkSpeedFactor()));

    return ConfigManager::getSingleton().getLowHealthWalkSpeedFactor();
}

double Creature::getTileSpeedRatio() const
{
    // The same tile speed the client moves the creature with (see getMoveSpeed): no covering building on the client
    Tile* tile = getPositionTile();
    double groundSpeed = getMoveSpeedGround();
    if((tile == nullptr) || (groundSpeed <= 0.0))
        return 1.0;

    double tileSpeed = tile->getHasBridge() ? groundSpeed : tile->getCreatureSpeedDefault(this);
    if(tileSpeed <= 0.0)
        return 1.0;

    return std::max(TILE_SPEED_RATIO_MIN, std::min(TILE_SPEED_RATIO_MAX, tileSpeed / groundSpeed));
}

void Creature::updateClientPose(double timeSinceLastFrame)
{
    updateGhostHuntVisuals(timeSinceLastFrame);
    if(getAnimationStateName() != EntityAnimation::walk_anim)
    {
        mClientTileSpeedRatio = -1.0;
        return;
    }

    double target = getTileSpeedRatio();
    if(mClientTileSpeedRatio < 0.0)
    {
        mClientTileSpeedRatio = target;
        return;
    }

    // The ratio changes by 4 per second at most, so a step between two tile types takes a fraction of a second
    double maxStep = std::max(0.0, timeSinceLastFrame) * TILE_SPEED_RATIO_MAX_CHANGE_PER_SECOND;
    double diff = target - mClientTileSpeedRatio;
    if(std::abs(diff) <= maxStep)
        mClientTileSpeedRatio = target;
    else
        mClientTileSpeedRatio += (diff > 0.0) ? maxStep : -maxStep;
}

double Creature::getClientPoseSpeedFactor() const
{
    double factor = 1.0;
    if(getAnimationStateName() == EntityAnimation::idle_anim)
    {
        // Hurt creatures breathe a little slower when they stand
        if(mOverlayHealthValue >= IDLE_BREATH_STAGE_HEAVY)
            factor = IDLE_BREATH_FACTOR_HEAVY;
        else if(mOverlayHealthValue == IDLE_BREATH_STAGE_MEDIUM)
            factor = IDLE_BREATH_FACTOR_MEDIUM;
        else if(mOverlayHealthValue == IDLE_BREATH_STAGE_LIGHT)
            factor = IDLE_BREATH_FACTOR_LIGHT;
    }
    else
    {
        // The walk clip keeps up with the slower speed of a badly hurt creature (see getMoveSpeed)
        factor = getLowHealthWalkFactor();
    }

    // A tired creature also walks slower on the server (see getMoveSpeed): the walk clip keeps up
    if((mOverlayMoodValue & CreatureMoodValues::Tired) != 0)
        factor *= ConfigManager::getSingleton().getTiredWalkSpeedFactor();

    // A staggering creature also walks slower (see getMoveSpeed): the walk clip keeps up
    if(isStaggering())
        factor *= ConfigManager::getSingleton().getTavernConfigDouble("StaggerSpeedFactor");

    // The worker that pulls a hurt creature walks slower too (see getMoveSpeed)
    if(getAnimationStateName() == EntityAnimation::drag_anim)
        factor *= getDragWorkerSpeedFactor();

    // The walk clips (Walk, WalkHurt, CarryWalk) of a type can run faster or slower than the move speed so that the
    // feet do not slide (WalkClipRate, WalkHurtClipRate for the clip WalkHurt). Only the shown clip, the move speed is not
    // touched. The rate follows the clip that plays (the client switches it when the health stage crosses the threshold).
    // The rate is measured on the unscaled model: a bigger creature (see RenderManager::rrScaleCreature) takes longer
    // strides, so the scale is divided out
    if((getAnimationStateName() == EntityAnimation::walk_anim) && (mDefinition != nullptr))
    {
        Ogre::AnimationState* clipState = getAnimationState();
        bool playsHurtClip = (clipState != nullptr) && (clipState->getAnimationName() == EntityAnimation::walk_hurt_anim);
        double clipRate = playsHurtClip ? mDefinition->getWalkHurtClipRate() : mDefinition->getWalkClipRate();
        factor *= clipRate / getLevelScale();

        // The creature moves with the speed of the tile it stands on (water, lava, ...) while the clip rate is fitted
        // to the ground speed: the clip keeps up with the ratio (tired and hurt factors above are already in both)
        factor *= (mClientTileSpeedRatio >= 0.0) ? mClientTileSpeedRatio : getTileSpeedRatio();
    }
    return factor;
}

//! \brief Adds Second Wind to the movement percentage sum only while below half health.
double Creature::getConditionalItemMoveFactor() const
{
    static const double SECOND_WIND_HEALTH_SHARE = 0.5;
    if(mMaxHP <= 0.0 || mHp >= mMaxHP * SECOND_WIND_HEALTH_SHARE)
        return 1.0;
    return 1.0 + getItemEffect("SecondWind") / (100.0 + getSkillPassive("move%"));
}

//! \brief Returns ground speed with its current health-dependent equipment bonus.
double Creature::getMoveSpeedGround() const
{
    if(!getIsOnServerMap())
        return mGroundSpeed;
    return mGroundSpeed * getConditionalItemMoveFactor();
}

//! \brief Keeps non-swimmers immobile while applying water equipment speed to swimmers.
double Creature::getMoveSpeedWater() const
{
    if(!getIsOnServerMap())
        return mWaterSpeed;
    return mWaterSpeed * getConditionalItemMoveFactor() * (1.0 + getItemEffect("Wader") / 100.0);
}

//! \brief Keeps creatures unable to cross lava immobile while applying lava speed effects.
double Creature::getMoveSpeedLava() const
{
    if(!getIsOnServerMap())
        return mLavaSpeed;
    return mLavaSpeed * getConditionalItemMoveFactor() * (1.0 + getItemEffect("LavaStride") / 100.0);
}

//! \brief Returns the attack rating scaled by the Dexterity attribute level and the ar% passives, plus the unscaled
//! ratings of both held items.
double Creature::getAttackRating() const
{
    double rating = CreatureProgression::combatStatAt(mDefinition->getAttackRating(), 0.0, getDexterityLevel(),
        CreatureProgression::attackRatingMultiplierAt) * (1.0 + getSkillPassive("ar%") / 100.0);
    if(mWeaponL != nullptr)
        rating += mWeaponL->getAttackRating();
    if(mWeaponR != nullptr)
        rating += mWeaponR->getAttackRating();
    return rating * getPotionFactor("DexterityChange");
}

//! \brief Returns the defense rating scaled by the Dexterity attribute level and the dr% passives, plus the unscaled
//! ratings of both held items.
double Creature::getDefenseRating() const
{
    double rating = CreatureProgression::combatStatAt(mDefinition->getDefenseRating(), 0.0, getDexterityLevel(),
        CreatureProgression::defenseRatingMultiplierAt) * (1.0 + getSkillPassive("dr%") / 100.0);
    if(mWeaponL != nullptr)
        rating += mWeaponL->getDefenseRating();
    if(mWeaponR != nullptr)
        rating += mWeaponR->getDefenseRating();
    return rating * getPotionFactor("DexterityChange");
}

namespace
{
//! \brief The attributes and bonuses an item can add to a creature.
enum class EquipmentAttribute
{
    strength,
    dexterity,
    life,
    mana,
    critChance
};

//! \brief Returns the bonus one item gives for the given attribute (0 for no item).
//! \param weapon The held item, may be null.
//! \param attribute The attribute to read.
double weaponBonus(const Weapon* weapon, EquipmentAttribute attribute)
{
    if(weapon == nullptr)
        return 0.0;
    switch(attribute)
    {
    case EquipmentAttribute::strength:
        return weapon->getStrength();
    case EquipmentAttribute::dexterity:
        return weapon->getDexterity();
    case EquipmentAttribute::life:
        return weapon->getLife();
    case EquipmentAttribute::mana:
        return weapon->getMana();
    case EquipmentAttribute::critChance:
        return weapon->getCritChance();
    }
    return 0.0;
}

//! \brief Returns the summed bonus of both held items for the given attribute.
//! \param weaponL The item in the left hand, may be null.
//! \param weaponR The item in the right hand, may be null.
//! \param attribute The attribute to read.
double equipmentBonus(const Weapon* weaponL, const Weapon* weaponR, EquipmentAttribute attribute)
{
    return weaponBonus(weaponL, attribute) + weaponBonus(weaponR, attribute);
}

//! \brief Returns the attribute level LA of one attribute: 1 + (value - start value) / points per level, which is
//! level + equipment bonus / points per level, at least 1; the creature level when the points per level are 0.
//! \param perLevel Points per level of the attribute.
//! \param level The creature level.
//! \param equipmentBonusValue The summed equipment bonus of the attribute.
double attributeLevel(double perLevel, unsigned int level, double equipmentBonusValue)
{
    if(perLevel == 0.0)
        return static_cast<double>(level);
    return std::max(1.0, static_cast<double>(level) + equipmentBonusValue / perLevel);
}
}

//! \brief Returns the Strength attribute at the current level, including the equipment bonus.
double Creature::getStrength() const
{
    return mDefinition->getStrength() + mDefinition->getStrengthPerLevel() * (mLevel - 1) +
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::strength) + getItemAttribute("Strength");
}

//! \brief Returns the Dexterity attribute at the current level, including the equipment bonus.
double Creature::getDexterity() const
{
    return mDefinition->getDexterity() + mDefinition->getDexterityPerLevel() * (mLevel - 1) +
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::dexterity) + getItemAttribute("Dexterity");
}

//! \brief Returns the Life attribute at the current level, including the equipment bonus.
double Creature::getLife() const
{
    return mDefinition->getLife() + mDefinition->getLifePerLevel() * (mLevel - 1) +
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::life) + getItemAttribute("Life");
}

//! \brief Returns the Mana attribute at the current level, including the equipment bonus.
double Creature::getMana() const
{
    return mDefinition->getMana() + mDefinition->getManaPerLevel() * (mLevel - 1) +
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::mana) + getItemAttribute("Mana");
}

//! \brief Returns the Strength attribute level LA (the creature level plus the equipment bonus in levels).
double Creature::getStrengthLevel() const
{
    return attributeLevel(mDefinition->getStrengthPerLevel(), mLevel,
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::strength) + getItemAttribute("Strength"));
}

//! \brief Returns the Dexterity attribute level LA (the creature level plus the equipment bonus in levels).
double Creature::getDexterityLevel() const
{
    return attributeLevel(mDefinition->getDexterityPerLevel(), mLevel,
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::dexterity) + getItemAttribute("Dexterity"));
}

//! \brief Returns the Life attribute level LA (the creature level plus the equipment bonus in levels).
double Creature::getLifeLevel() const
{
    return attributeLevel(mDefinition->getLifePerLevel(), mLevel,
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::life) + getItemAttribute("Life"));
}

//! \brief Returns the Mana attribute level LA (the creature level plus the equipment bonus in levels).
double Creature::getManaLevel() const
{
    return attributeLevel(mDefinition->getManaPerLevel(), mLevel,
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::mana) + getItemAttribute("Mana"));
}

//! \brief Returns the critical chance bonus in percent that both held items add.
double Creature::getEquipmentCritChance() const
{
    return equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::critChance) + getItemBonus("CritChance") +
        getItemEffect("KeenEye") + getItemEffect("Fortune") + getPotionCritChance();
}

//! \brief Returns the critical chance in percent: CritChancePerDexterity x (start Dexterity of the type + equipment
//! Dexterity) + CritChancePerLevel x (level - 1) + CritChanceBonus + crit passives + equipment critical chance.
double Creature::getCritChance() const
{
    ConfigManager& config = ConfigManager::getSingleton();
    const double dexterity = mDefinition->getDexterity() +
        equipmentBonus(mWeaponL, mWeaponR, EquipmentAttribute::dexterity) + getItemAttribute("Dexterity");
    return config.getCritChancePerDexterity() * dexterity +
        config.getCritChancePerLevel() * static_cast<double>(mLevel - 1) +
        mDefinition->getCritChanceBonus() + getSkillPassive("crit") + getEquipmentCritChance();
}

//! \brief Rolls one critical hit against the critical chance; a chance of 0 or less never rolls.
bool Creature::rollCritical() const
{
    const double chance = getCritChance();
    if(chance <= 0.0)
        return false;
    return Random::Double(0.0, 100.0) < chance;
}

//! \brief Returns the claim rate of the creature: the config rate with the level bonus times 1 + claim% / 100.
double Creature::getClaimRate() const
{
    return mClaimRate * (1.0 + getSkillPassive("claim%") / 100.0);
}

//! \brief Returns 1 + dig% / 100: the factor of the dig% passives on the dig rate and on the gold of a dig step.
double Creature::getDigFactor() const
{
    return 1.0 + getSkillPassive("dig%") / 100.0;
}

//! \brief Returns true if one of the held items has the weapon type bow or crossbow.
bool Creature::carriesBowOrCrossbow() const
{
    const Weapon* weapons[] = {mWeaponL, mWeaponR};
    for(const Weapon* weapon : weapons)
    {
        if(weapon == nullptr)
            continue;
        const std::string weaponType = weapon->getWeaponType();
        if(weaponType == "bow" || weaponType == "crossbow")
            return true;
    }
    return false;
}

//! \brief Returns the sum of the ranked passive skills of the skill tree for the stat (percentages add up).
//! \param stat The passive stat name (hp%, ar%, dr%, dmg%, spell%, alldmg%, crit, cd%, avoid, move%, ...).
double Creature::getSkillPassive(const std::string& stat) const
{
    double sum = CreatureSkillTree::passiveSum(ConfigManager::getSingleton().getCreatureSkillTree(), mSkillBuild, stat);
    static const std::map<std::string, std::string> BONUS_STATS = {
        {"hp%", "MaxHP%"}, {"cd%", "Cooldown%"}, {"avoid", "Avoid"}, {"ar%", "AttackRating%"},
        {"dr%", "DefenseRating%"}, {"move%", "MoveSpeed%"}, {"wake%", "Wakefulness%"},
        {"manacost%", "ManaCost%"}, {"dig%", "Dig%"}, {"claim%", "Claim%"}, {"carry%", "Carry%"}
    };
    std::map<std::string, std::string>::const_iterator bonus = BONUS_STATS.find(stat);
    if(bonus != BONUS_STATS.end())
        sum += getItemBonus(bonus->second);
    const bool caster = mDefinition != nullptr && mDefinition->getSkillGroup() == "caster";
    if((caster && stat == "spell%") || (!caster && stat == "dmg%"))
        sum += getItemBonus("Damage%");
    if(stat == "move%") sum += getItemEffect("SwiftStep");
    else if(stat == "avoid") sum += getItemEffect("LightStep");
    else if(stat == "wake%") sum += getItemEffect("Tireless") + getItemEffect("Stamina");
    else if(stat == "manacost%") sum += getItemEffect("ClearMind");
    else if(stat == "cd%") sum += getItemEffect("Swift");
    else if(stat == "dig%") sum += getItemEffect("GoldNose");
    if(getGameMap() != nullptr)
    {
        if(stat == "dr%") sum += getIsOnServerMap() ? getGameMap()->getItemAura(*this, "GuardWall") : mClientGuardWall;
        else if(stat == "hp%") sum += getIsOnServerMap() ? getGameMap()->getItemAura(*this, "Rally") : mClientRally;
    }
    return sum;
}

//! \brief Returns the rank of the skill tree entry with the given id, 0 when the creature has none.
uint32_t Creature::getSkillRank(const std::string& skillId) const
{
    return CreatureSkillTree::getRank(mSkillBuild, skillId);
}

//! \brief Returns the skill points the level has paid so far (0 for a type without skill group).
uint32_t Creature::getSkillPointsEarned() const
{
    if(mDefinition == nullptr || skillTextOrEmpty(mDefinition->getSkillGroup()).empty())
        return 0;

    return CreatureSkillTree::pointsAtLevel(mLevel, ConfigManager::getSingleton().getSkillPointFirstLevel());
}

//! \brief Returns the skill points the creature has spent in its paths and on its tier 4 skill.
uint32_t Creature::getSkillPointsSpent() const
{
    return CreatureSkillTree::spentPoints(mSkillBuild, getSkillTypeInfo());
}

//! \brief Returns the name of the template the creature follows, empty while it follows none.
std::string Creature::getSkillTemplateName() const
{
    if(mDefinition == nullptr)
        return std::string();

    const CreatureSkillTree::TemplateDef* templ = ConfigManager::getSingleton().getCreatureSkillTree().findTemplate(
        skillTextOrEmpty(mDefinition->getSkillGroup()), mSkillBuild.mTemplate);
    if(templ == nullptr)
        return std::string();

    return templ->mName;
}

//! \brief Text shown for an empty template, skill list or hand in the displays.
static const std::string DISPLAY_NONE_TEXT = "none";
//! \brief Number of decimals of the attribute values and the critical chance in the displays.
static const int32_t DISPLAY_DECIMALS = 1;
//! \brief Text a value with DISPLAY_DECIMALS decimals ends with when the decimals are zero.
static const std::string DISPLAY_ZERO_DECIMALS_SUFFIX = ".0";

//! \brief Writes a number with exactly DISPLAY_DECIMALS decimals.
//! \param value The number to write.
static std::string formatFixedNumber(double value)
{
    std::stringstream text;
    text << std::fixed << std::setprecision(DISPLAY_DECIMALS) << value;
    return text.str();
}

//! \brief Writes a number with DISPLAY_DECIMALS decimals; a whole number is written without decimals.
//! \param value The number to write.
static std::string formatDisplayNumber(double value)
{
    std::string result = formatFixedNumber(value);
    if(result.size() > DISPLAY_ZERO_DECIMALS_SUFFIX.size() &&
       result.compare(result.size() - DISPLAY_ZERO_DECIMALS_SUFFIX.size(), DISPLAY_ZERO_DECIMALS_SUFFIX.size(),
           DISPLAY_ZERO_DECIMALS_SUFFIX) == 0)
    {
        result.erase(result.size() - DISPLAY_ZERO_DECIMALS_SUFFIX.size());
    }
    return result;
}

//! \brief Returns the template name for the displays ("none" while the creature follows no template).
std::string Creature::getSkillPathText() const
{
    const std::string templateName = getSkillTemplateName();
    if(templateName.empty())
        return DISPLAY_NONE_TEXT;

    return templateName;
}

//! \brief Returns the ranked skills for the displays as "<name> <rank>, ..." ("none" while there are none).
std::string Creature::getSkillListText() const
{
    const CreatureSkillTree::SkillTreeConfig& config = ConfigManager::getSingleton().getCreatureSkillTree();
    std::string result;
    for(std::map<std::string, uint32_t>::const_iterator it = mSkillBuild.mRanks.begin();
        it != mSkillBuild.mRanks.end(); ++it)
    {
        if(it->second == 0)
            continue;

        std::string skillName = it->first;
        const CreatureSkillTree::SkillDef* skill = config.findSkill(it->first);
        const CreatureSkillTree::TierFourDef* tierFour = config.findTierFourById(it->first);
        if(skill != nullptr)
            skillName = skill->mName;
        else if(tierFour != nullptr)
            skillName = tierFour->mName;

        if(!result.empty())
            result += ", ";
        result += skillName + " " + Helper::toString(it->second);
    }
    if(result.empty())
        return DISPLAY_NONE_TEXT;

    return result;
}

//! \brief Returns the attribute line of the displays: "Strength s - Dexterity d - Life l - Mana m -
//! Critical x.x %".
std::string Creature::getAttributeSummaryText() const
{
    return "Strength " + formatDisplayNumber(getStrength()) + " - Dexterity " + formatDisplayNumber(getDexterity())
        + " - Life " + formatDisplayNumber(getLife()) + " - Mana " + formatDisplayNumber(getMana())
        + " - Critical " + formatFixedNumber(getCritChance()) + " %";
}

//! \brief Returns the carried items for the displays as "<right> / <left>" ("none" for an empty hand).
std::string Creature::getEquipmentText() const
{
    const std::string right = (mWeaponR == nullptr) ? DISPLAY_NONE_TEXT : mWeaponR->getName();
    const std::string left = (mWeaponL == nullptr) ? DISPLAY_NONE_TEXT : mWeaponL->getName();
    return right + " / " + left;
}

//! \brief Fills the skill group, family, pre-skill and tier 4 skill of the type of the creature (empty = none).
CreatureSkillTree::TypeInfo Creature::getSkillTypeInfo() const
{
    CreatureSkillTree::TypeInfo type;
    if(mDefinition == nullptr)
        return type;

    type.mGroup = skillTextOrEmpty(mDefinition->getSkillGroup());
    type.mFamily = skillTextOrEmpty(mDefinition->getSkillFamily());
    type.mPreSkill = skillTextOrEmpty(mDefinition->getPreSkill());
    type.mTierFour = skillTextOrEmpty(mDefinition->getTierFourSkill());
    return type;
}

//! \brief Starts the skill build of a new creature: a personal seed, the free rank of the pre-skill and the points the
//! level has paid. A creature that was loaded with its skill state keeps it.
void Creature::initSkillBuild()
{
    if(!getIsOnServerMap() || mDefinition == nullptr)
        return;

    const CreatureSkillTree::TypeInfo type = getSkillTypeInfo();
    if(type.mGroup.empty())
        return;

    if(mSkillBuild.mSeed == 0)
        CreatureSkillTree::startBuild(mSkillBuild, type, Random::Uint(1, SKILL_SEED_MAX));

    updateSkillPoints();
    mTreeSkillsDirty = true;
}

//! \brief Counts the own creatures of the skill group per template; the creature itself counts once it has chosen.
//! \param followers Receives one count per template of the group.
void Creature::countTemplateFollowers(std::vector<uint32_t>& followers) const
{
    const std::string group = skillTextOrEmpty(mDefinition->getSkillGroup());
    const CreatureSkillTree::SkillTreeConfig& tree = ConfigManager::getSingleton().getCreatureSkillTree();
    followers.assign(tree.getTemplates(group).size(), 0);
    if(getGameMap() == nullptr || getSeat() == nullptr)
        return;

    const std::vector<Creature*> mates = getGameMap()->getCreaturesBySeat(getSeat());
    for(Creature* mate : mates)
    {
        if(mate == this || mate->mDefinition == nullptr)
            continue;

        if(skillTextOrEmpty(mate->mDefinition->getSkillGroup()) != group)
            continue;

        const int32_t mateTemplate = mate->mSkillBuild.mTemplate;
        if(mateTemplate >= 0 && static_cast<size_t>(mateTemplate) < followers.size())
            ++followers[static_cast<size_t>(mateTemplate)];
    }

    const int32_t ownTemplate = mSkillBuild.mTemplate;
    if(ownTemplate >= 0 && static_cast<size_t>(ownTemplate) < followers.size())
        ++followers[static_cast<size_t>(ownTemplate)];
}

//! \brief Spends the skill points the level has paid. At the first point the template is chosen: weight 1 per template,
//! times 3 for a template that no own creature of the group follows.
void Creature::updateSkillPoints()
{
    if(!getIsOnServerMap() || mDefinition == nullptr || mSkillBuild.mSeed == 0)
        return;

    const CreatureSkillTree::TypeInfo type = getSkillTypeInfo();
    ConfigManager& config = ConfigManager::getSingleton();
    if(type.mGroup.empty() || CreatureSkillTree::pointsAtLevel(mLevel, config.getSkillPointFirstLevel()) == 0)
        return;

    if(mSkillBuild.mTemplate < 0)
    {
        std::vector<uint32_t> followers;
        countTemplateFollowers(followers);
        mSkillBuild.mTemplate = CreatureSkillTree::chooseTemplate(followers, Random::Double(0.0, 1.0));
        if(mSkillBuild.mTemplate < 0)
            return;
    }

    const uint32_t spentBefore = CreatureSkillTree::spentPoints(mSkillBuild, type);
    CreatureSkillTree::spendUpToLevel(config.getCreatureSkillTree(), type, mSkillBuild, mLevel,
        config.getSkillPointFirstLevel(), config.getSkillTemplateDeviationPercent(), config.getSkillRanksPerSkill());
    if(CreatureSkillTree::spentPoints(mSkillBuild, type) != spentBefore)
    {
        mTreeSkillsDirty = true;
        mNeedFireRefresh = true;
    }
}

//! \brief Counts one eaten chicken; the configured number of chickens opens the reset window of the skills.
void Creature::registerChickenEaten()
{
    if(!getIsOnServerMap() || mDefinition == nullptr || skillTextOrEmpty(mDefinition->getSkillGroup()).empty())
        return;

    ConfigManager& config = ConfigManager::getSingleton();
    CreatureSkillTree::countChicken(mSkillBuild, config.getSkillRespecChickens(), config.getSkillRespecWindowSeconds());
    mNeedFireRefresh = true;
}

//! \brief Lets the reset window run. While it is open, a creature whose template has at least three followers among the
//! own creatures of its group, while another template of the group has none, switches to that template and spends all
//! its points again. Then rebuilds the active skills when the ranks changed.
void Creature::upkeepSkillTree()
{
    if(!getIsOnServerMap() || mDefinition == nullptr)
        return;

    if(mSkillBuild.mRespecWindow > 0.0)
    {
        CreatureSkillTree::tickRespecWindow(mSkillBuild, 1.0 / ODApplication::turnsPerSecond);
        if(mSkillBuild.mRespecWindow > 0.0 && mSkillBuild.mTemplate >= 0)
        {
            std::vector<uint32_t> followers;
            countTemplateFollowers(followers);
            const int32_t newTemplate = CreatureSkillTree::findResetTemplate(mSkillBuild.mTemplate, followers);
            if(newTemplate >= 0)
            {
                ConfigManager& config = ConfigManager::getSingleton();
                CreatureSkillTree::resetBuild(config.getCreatureSkillTree(), getSkillTypeInfo(), mSkillBuild,
                    newTemplate, mLevel, config.getSkillPointFirstLevel(), config.getSkillTemplateDeviationPercent(),
                    config.getSkillRanksPerSkill());
                // One reset per window
                mSkillBuild.mRespecWindow = 0.0;
                mTreeSkillsDirty = true;
                mNeedFireRefresh = true;

                // The passives of the new ranks change the maximum hit points
                const double previousMaxHP = mMaxHP;
                buildStats();
                if(mHp > 0.0 && previousMaxHP > 0.0)
                    mHp = std::min(mMaxHP, mHp * mMaxHP / previousMaxHP);
            }
        }
    }

    if(mTreeSkillsDirty)
        rebuildTreeSkills();
}

//! \brief Returns the sort position of a skill of the skill tree: the tier 4 skill first, then heals, buffs, debuffs
//! and at last damage and control skills.
//! \param skillId The id of the skill tree entry.
//! \param kind The kind token of the entry.
static uint32_t treeSkillPriority(const std::string& skillId, const std::string& kind)
{
    if(skillId.compare(0, CreatureSkillTree::TIER_FOUR_PREFIX.size(), CreatureSkillTree::TIER_FOUR_PREFIX) == 0)
        return TREE_SKILL_PRIORITY_TIER_FOUR;
    if(kind.compare(0, TREE_KIND_HEAL.size(), TREE_KIND_HEAL) == 0)
        return TREE_SKILL_PRIORITY_HEAL;
    if(kind.compare(0, TREE_KIND_BUFF.size(), TREE_KIND_BUFF) == 0 ||
       kind.compare(0, TREE_KIND_AURA.size(), TREE_KIND_AURA) == 0 || kind == TREE_KIND_STRIKE)
    {
        return TREE_SKILL_PRIORITY_BUFF;
    }
    if(kind.compare(0, TREE_KIND_DEBUFF.size(), TREE_KIND_DEBUFF) == 0)
        return TREE_SKILL_PRIORITY_DEBUFF;
    return TREE_SKILL_PRIORITY_DAMAGE;
}

//! \brief Replaces the active skills made from the skill tree ranks. A skill that stays keeps its cooldown and warmup.
//! The skills stand in front of the attack lines of the definition in the order of the AI: tier 4, heals, buffs,
//! debuffs, damage and control skills.
void Creature::rebuildTreeSkills()
{
    mTreeSkillsDirty = false;
    if(!getIsOnServerMap() || mDefinition == nullptr)
        return;

    // Remember the timers of the skills that are replaced
    std::map<std::string, std::pair<double, double> > timers;
    for(std::vector<CreatureSkillData>::iterator it = mSkillData.begin(); it != mSkillData.end();)
    {
        if(it->mTreeSkillId.empty())
        {
            ++it;
            continue;
        }

        timers[it->mTreeSkillId] = std::make_pair(it->mCooldown, it->mWarmup);
        it = mSkillData.erase(it);
    }
    for(CreatureSkill* skill : mTreeSkills)
        delete skill;
    mTreeSkills.clear();

    const CreatureSkillTree::SkillTreeConfig& tree = ConfigManager::getSingleton().getCreatureSkillTree();
    std::vector<std::pair<uint32_t, CreatureSkillData> > sorted;
    for(std::map<std::string, uint32_t>::const_iterator it = mSkillBuild.mRanks.begin();
        it != mSkillBuild.mRanks.end(); ++it)
    {
        if(it->second == 0)
            continue;

        CreatureSkill* skill = createTreeSkill(it->first, it->second);
        if(skill == nullptr)
            continue;

        mTreeSkills.push_back(skill);
        std::string kind;
        const CreatureSkillTree::TierFourDef* tierFour = tree.findTierFourById(it->first);
        const CreatureSkillTree::SkillDef* def = tree.findSkill(it->first);
        if(tierFour != nullptr)
            kind = tierFour->mKind;
        else if(def != nullptr)
            kind = def->mKind;

        CreatureSkillData skillData(skill, getAppliedCooldownNbTurns(*skill), 0);
        skillData.mTreeSkillId = it->first;
        std::map<std::string, std::pair<double, double> >::const_iterator timer = timers.find(it->first);
        if(timer != timers.end())
        {
            skillData.mCooldown = timer->second.first;
            skillData.mWarmup = timer->second.second;
        }
        sorted.push_back(std::make_pair(treeSkillPriority(it->first, kind), skillData));
    }

    // Sorted by priority; inside one priority the order of the ids stays
    std::vector<CreatureSkillData> ordered;
    for(uint32_t priority = TREE_SKILL_PRIORITY_TIER_FOUR; priority <= TREE_SKILL_PRIORITY_DAMAGE; ++priority)
    {
        for(size_t i = 0; i < sorted.size(); ++i)
        {
            if(sorted[i].first == priority)
                ordered.push_back(sorted[i].second);
        }
    }
    mSkillData.insert(mSkillData.begin(), ordered.begin(), ordered.end());
    mNeedFireRefresh = true;
}

//! \brief Creates the active skill of a skill tree entry at the given rank from its table row (kind, rank value,
//! cooldown, duration, radius, range and base line).
//! \param skillId The id of the skill tree entry (a tier 4 id is T4_<type>).
//! \param rank The rank (ignored for the tier 4 skill).
//! \return The skill, nullptr when the entry is a passive or has no valid skill line. The caller owns the skill.
CreatureSkill* Creature::createTreeSkill(const std::string& skillId, uint32_t rank) const
{
    const CreatureSkillTree::SkillTreeConfig& tree = ConfigManager::getSingleton().getCreatureSkillTree();
    std::string line;
    double manaCost = 0.0;
    const CreatureSkillTree::TierFourDef* tierFour = tree.findTierFourById(skillId);
    const CreatureSkillTree::SkillDef* def = tree.findSkill(skillId);
    if(tierFour != nullptr)
    {
        line = CreatureSkillTree::buildSkillLine(tierFour->mKind, tierFour->mValue, tierFour->mCooldown,
            tierFour->mDuration, tierFour->mRadius, tierFour->mRange, tierFour->mBaseLine);
        manaCost = tierFour->mMana.mValue;
    }
    else if(def != nullptr && rank > 0 && !def->mValues.empty())
    {
        const size_t index = std::min(static_cast<size_t>(rank), def->mValues.size()) - 1;
        line = CreatureSkillTree::buildSkillLine(def->mKind, def->mValues[index], def->mCooldown, def->mDuration,
            def->mRadius, def->mRange, def->mBaseLine);
        if(index < def->mMana.size())
            manaCost = def->mMana[index];
    }

    if(line.empty())
        return nullptr;

    std::istringstream lineStream(line);
    CreatureSkill* skill = CreatureSkillManager::load(lineStream);
    if(skill == nullptr)
    {
        OD_LOG_ERR("creature=" + getName() + ", cannot load the skill line of " + skillId + ": " + line);
        return nullptr;
    }

    skill->setTreeSkill(skillId, manaCost);
    return skill;
}

//! \brief Returns the heal amount of 100 percent of a heal skill: the MinHP of the type times the damage multiplier of
//! the Mana attribute level.
double Creature::getHealBase() const
{
    return mDefinition->getMinHp() * CreatureProgression::damageMultiplierAt(getManaLevel());
}

//! \brief Returns the factor on the damage of a damage skill of the skill tree: the damage multiplier of the level, the
//! own MinHP divided by the calibration MinHP, and the spell% and alldmg% passives. The SkillDamageFactor of the type
//! is applied by the skills themselves.
double Creature::getTreeSpellDamageFactor() const
{
    ConfigManager& config = ConfigManager::getSingleton();
    double factor = CreatureProgression::damageMultiplierAt(static_cast<double>(mLevel));
    if(config.getSkillSpellReferenceMinHP() > 0.0)
        factor *= mDefinition->getMinHp() / config.getSkillSpellReferenceMinHP();

    return factor * (1.0 + (getSkillPassive("spell%") + getSkillPassive("alldmg%")) / 100.0);
}

//! \brief Arms the next melee blow against a creature to do its damage times the factor.
void Creature::armStrike(double factor)
{
    mStrikeMultiplier = factor;
}

//! \brief True while a melee blow is armed.
bool Creature::isStrikeArmed() const
{
    return mStrikeMultiplier > 1.0;
}

//! \brief Returns the factor of the armed melee blow and unarms it; 1 when none is armed.
double Creature::consumeStrikeMultiplier()
{
    const double factor = mStrikeMultiplier;
    mStrikeMultiplier = 1.0;
    return factor;
}

//! \brief Returns the own creatures (same seat, alive, on the map) within the radius in tiles, itself included.
//! \param radius The radius in tiles around the position of the creature.
std::vector<Creature*> Creature::getOwnCreaturesWithin(double radius) const
{
    std::vector<Creature*> found;
    if(getGameMap() == nullptr || getSeat() == nullptr || !getIsOnMap())
        return found;

    const std::vector<Creature*> mates = getGameMap()->getCreaturesBySeat(getSeat());
    for(Creature* mate : mates)
    {
        if(!mate->isAlive() || !mate->getIsOnMap())
            continue;

        const double dx = mate->getPosition().x - getPosition().x;
        const double dy = mate->getPosition().y - getPosition().y;
        if(dx * dx + dy * dy <= radius * radius)
            found.push_back(mate);
    }
    return found;
}

//! \brief True when a running effect of the creature was made by the skill or spell with the given source id.
//! \param sourceId The source id of the effect (the id of a skill tree entry).
bool Creature::hasActiveEffectSource(const std::string& sourceId) const
{
    for(const EntityParticleEffect* entityEffect : mEntityParticleEffects)
    {
        if(entityEffect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        const CreatureParticleEffect* effect = static_cast<const CreatureParticleEffect*>(entityEffect);
        if(effect->mEffect->getSourceId() == sourceId && effect->mEffect->getNbTurnsEffect() != 0.0)
            return true;
    }
    return false;
}

//! \brief Recomputes the strength modifier as the product of the factors of all running strength effects.
void Creature::updateStrengthModifier()
{
    double modifier = 1.0;
    for(std::map<const CreatureEffect*, double>::const_iterator it = mStrengthContributions.begin();
        it != mStrengthContributions.end(); ++it)
    {
        modifier *= it->second;
    }
    setStrengthModifier(modifier);
}

//! \brief Sets the factor of a running strength effect.
//! \param source The effect that holds the factor.
//! \param factor The damage factor of the effect.
void Creature::setStrengthContribution(const CreatureEffect* source, double factor)
{
    mStrengthContributions[source] = factor;
    updateStrengthModifier();
}

//! \brief Removes the factor of a strength effect that ended; the others stay.
void Creature::removeStrengthContribution(const CreatureEffect* source)
{
    mStrengthContributions.erase(source);
    updateStrengthModifier();
}

//! \brief Recomputes the speed modifier as the product of the factors of all running speed effects.
void Creature::updateSpeedModifier()
{
    double modifier = 1.0;
    for(std::map<const CreatureEffect*, double>::const_iterator it = mSpeedContributions.begin();
        it != mSpeedContributions.end(); ++it)
    {
        modifier *= it->second;
    }
    // Only a change is applied, so that a running effect does not refresh the speeds every turn
    if(modifier != mSpeedModifier)
        setMoveSpeedModifier(modifier);
}

//! \brief Sets the factor of a running speed effect; the speed modifier is the product of all factors.
//! \param source The effect that holds the factor.
//! \param factor The speed factor of the effect.
void Creature::setSpeedContribution(const CreatureEffect* source, double factor)
{
    mSpeedContributions[source] = factor;
    updateSpeedModifier();
}

//! \brief Removes the factor of a speed effect that ended; the others stay.
void Creature::removeSpeedContribution(const CreatureEffect* source)
{
    mSpeedContributions.erase(source);
    updateSpeedModifier();
}

//! \brief Recomputes the defense modifier as the sum of the bonuses of all running defense effects.
void Creature::updateDefenseModifier()
{
    double phy = 0.0;
    double mag = 0.0;
    double ele = 0.0;
    for(std::map<const CreatureEffect*, CreatureDefenseBonus>::const_iterator it = mDefenseContributions.begin();
        it != mDefenseContributions.end(); ++it)
    {
        phy += it->second.mPhy;
        mag += it->second.mMag;
        ele += it->second.mEle;
    }
    setDefenseModifier(phy, mag, ele);
}

//! \brief Sets the bonus of a running defense effect; the defense modifier is the sum of all bonuses.
//! \param source The effect that holds the bonus.
//! \param phy The bonus on the physical defense.
//! \param mag The bonus on the magical defense.
//! \param ele The bonus on the elemental defense.
void Creature::setDefenseContribution(const CreatureEffect* source, double phy, double mag, double ele)
{
    CreatureDefenseBonus& bonus = mDefenseContributions[source];
    bonus.mPhy = phy;
    bonus.mMag = mag;
    bonus.mEle = ele;
    updateDefenseModifier();
}

//! \brief Removes the bonus of a defense effect that ended; the others stay.
void Creature::removeDefenseContribution(const CreatureEffect* source)
{
    mDefenseContributions.erase(source);
    updateDefenseModifier();
}

//! \brief Writes the skill state (template, ranks, seed, generator state, reset counters) for clients.
void Creature::exportSkillBuildToPacket(ODPacket& os) const
{
    os << mSkillBuild.mTemplate;
    os << mSkillBuild.mSeed;
    os << mSkillBuild.mRngState;
    os << mSkillBuild.mPickCursor;
    os << mSkillBuild.mChickens;
    os << mSkillBuild.mRespecWindow;
    os << static_cast<uint32_t>(mSkillBuild.mRanks.size());
    for(std::map<std::string, uint32_t>::const_iterator it = mSkillBuild.mRanks.begin();
        it != mSkillBuild.mRanks.end(); ++it)
    {
        os << it->first;
        os << it->second;
    }
}

//! \brief Reads the skill state written by exportSkillBuildToPacket. A short packet leaves the state empty.
void Creature::importSkillBuildFromPacket(ODPacket& is)
{
    CreatureSkillTree::SkillBuild build;
    uint32_t nbRanks = 0;
    if(!(is >> build.mTemplate >> build.mSeed >> build.mRngState >> build.mPickCursor >> build.mChickens >>
         build.mRespecWindow >> nbRanks))
    {
        OD_LOG_ERR("creature=" + getName() + ", short skill state in packet");
        return;
    }

    for(uint32_t i = 0; i < nbRanks; ++i)
    {
        std::string skillId;
        uint32_t rank = 0;
        if(!(is >> skillId >> rank))
        {
            OD_LOG_ERR("creature=" + getName() + ", short skill ranks in packet");
            return;
        }
        build.mRanks[skillId] = rank;
    }

    mSkillBuild = build;
}

//! \brief Returns the size of the mana pool: Mana attribute (with equipment) x ManaPerPoint of the type.
double Creature::getMaxMana() const
{
    return std::max(0.0, getMana() * mDefinition->getManaPerPoint() * getPotionFactor("MaxManaChange"));
}

//! \brief Returns the mana the creature has right now (0 .. getMaxMana()).
double Creature::getCurrentMana() const
{
    return mMana;
}

//! \brief Sets the current mana, clamped to 0 .. getMaxMana(), and tells the clients when the mana ring changes.
//! \param mana The new current mana.
void Creature::setCurrentMana(double mana)
{
    const double maxMana = getMaxMana();
    mMana = std::max(0.0, std::min(mana, maxMana));

    if(!getIsOnServerMap())
        return;

    const uint32_t step = manaRingStep(mMana, maxMana);
    if(step != mManaRingStepNotified)
    {
        mManaRingStepNotified = step;
        mNeedFireRefresh = true;
    }
}

//! \brief Returns a mana cost after the manacost% passives: baseCost x (1 - manacost% / 100), never below 0.
//! \param baseCost The cost before the passives.
double Creature::getManaCost(double baseCost) const
{
    const double factor = std::max(0.0, 1.0 - getSkillPassive("manacost%") / 100.0);
    return std::max(0.0, baseCost) * factor;
}

//! \brief Returns the mana the skill costs this creature now: the rank cost of a skill of the skill tree, the shot cost
//! of a caster's first MissileLaunch or of a second MissileLaunch line like the Dragon's (all with manacost%), 0 for
//! every free attack.
//! \param skill The skill or attack line to price.
double Creature::getSkillManaCost(const CreatureSkill& skill) const
{
    // A skill of the skill tree costs its rank cost, whatever its kind (also a MissileLaunch or Grenade)
    if(skill.isTreeSkill())
        return getManaCost(skill.getTreeManaCost());

    // Only the MissileLaunch attack lines cost mana per shot; Melee and the weapon shots of the first line are free
    if(skill.getSkillName() != "MissileLaunch")
        return 0.0;

    const bool firstAttack = mDefinition->isFirstAttackSkill(&skill);
    if(firstAttack && carriesBowOrCrossbow())
        return 0.0;

    // The shot of a caster costs the caster rate. A type with a skill group is
    // told by its group, because a level file may list the Dragon's spell shot before its melee line; a type
    // without a group is told by the line order: the first attack line is the spell shot.
    const std::string& group = mDefinition->getSkillGroup();
    bool casterShot = firstAttack;
    if(group != "none")
        casterShot = (group == "caster");

    if(casterShot)
        return getManaCost(ConfigManager::getSingleton().getManaPerCasterShot());

    return getManaCost(ConfigManager::getSingleton().getManaPerDragonSecondShot());
}

//! \brief Returns true if the current mana covers the cost of the skill (a free skill is always affordable).
//! \param skill The skill or attack line to check.
bool Creature::hasManaFor(const CreatureSkill& skill) const
{
    return mMana >= getSkillManaCost(skill);
}

//! \brief Subtracts the mana cost of the skill; called when the skill or shot starts.
//! \param skill The skill or attack line that starts.
void Creature::payManaFor(const CreatureSkill& skill)
{
    const double cost = getSkillManaCost(skill);
    if(cost <= 0.0)
        return;

    setCurrentMana(mMana - cost);
}

//! \brief Adds one turn of mana regeneration: max mana / (ManaRefillSeconds x turns per second), capped at max.
void Creature::regenerateMana()
{
    const double maxMana = getMaxMana();
    if(mMana >= maxMana)
    {
        // The pool may have shrunk (equipment removed): the mana above the new size is lost
        if(mMana > maxMana)
            setCurrentMana(maxMana);
        return;
    }

    const double refillTurns = ConfigManager::getSingleton().getManaRefillSeconds() * ODApplication::turnsPerSecond;
    if(refillTurns <= 0.0)
    {
        setCurrentMana(maxMana);
        return;
    }

    const double itemFactor = 1.0 + (getItemEffect("Focus") + getItemEffect("ManaSpring")) / 100.0;
    setCurrentMana(mMana + maxMana / refillTurns * itemFactor * getPotionFactor("ManaRegenChange"));
}

double Creature::getPhysicalDefense() const
{
    double defense = mPhysicalDefense;
    if (mWeaponL != nullptr)
        defense += mWeaponL->getPhysicalDefense();
    if (mWeaponR != nullptr)
        defense += mWeaponR->getPhysicalDefense();

    return std::max(0.0, defense * getItemDefenseFactor() + getRelationshipCombatModifier());
}

double Creature::getMagicalDefense() const
{
    double defense = mMagicalDefense;
    if (mWeaponL != nullptr)
        defense += mWeaponL->getMagicalDefense();
    if (mWeaponR != nullptr)
        defense += mWeaponR->getMagicalDefense();

    return std::max(0.0, defense * getItemDefenseFactor() * (1.0 + getItemEffect("SpellWard") / 100.0) + getRelationshipCombatModifier());
}

double Creature::getElementDefense() const
{
    double defense = mElementDefense;
    if (mWeaponL != nullptr)
        defense += mWeaponL->getElementDefense();
    if (mWeaponR != nullptr)
        defense += mWeaponR->getElementDefense();

    return std::max(0.0, defense * getItemDefenseFactor() * (1.0 + getItemEffect("FireWard") / 100.0) + getRelationshipCombatModifier());
}

void Creature::checkLevelUp()
{
    while(getLevel() < MAX_LEVEL)
    {
        const double newXP = mDefinition->getXPNeededWhenLevel(getLevel());
        if(!std::isfinite(newXP) || newXP <= 0.0)
        {
            OD_LOG_ERR("creature=" + getName() + ", newXP=" + Helper::toString(newXP));
            return;
        }
        if(mExp < newXP)
            return;

        const double remainingXP = mExp - newXP;
        setLevel(mLevel + 1);
        mExp = remainingXP;
    }
    mExp = 0.0;
}

//! \brief Writes changing creature data with public hands and owner-only private item slots.
void Creature::exportToPacketForUpdate(ODPacket& os, Seat* seat) 
{
    MovableGameEntity::exportToPacketForUpdate(os, seat);

    int seatId = getSeat()->getId();
    os << mLevel;
    os << seatId;
    os << mOverlayHealthValue;

    // Only allied players should see creature mood (except some states)
    uint32_t moodValue = 0;
    if(seat->isAlliedSeat(getSeat()))
        moodValue = mOverlayMoodValue;
    else if(mSeatPrison != nullptr)
    {
        if(mSeatPrison->isAlliedSeat(seat))
            moodValue = mOverlayMoodValue & CreatureMoodValues::MoodPrisonFiltersPrisonAllies;
        else
            moodValue = mOverlayMoodValue & CreatureMoodValues::MoodPrisonFiltersAllPlayers;
    }

    os << moodValue;
    os << getMoveSpeedGround();
    os << getMoveSpeedWater();
    os << getMoveSpeedLava();
    os << mSpeedModifier;

    int seatPrisonId = -1;
    if(mSeatPrison != nullptr)
        seatPrisonId = mSeatPrison->getId();

    os << seatPrisonId;
    os << isHexenHen();
    exportMoodToPacket(os, seat);
    exportActivityToPacket(os, seat);
    exportProgressToPacket(os, seat);
    // Current mana, next to the health value (the maximum follows from type, level and equipment)
    os << mMana;
    // The skill state and carried gold are followed by the visible item slots and active owner contributions, then
    // the needs (urge and creature dirt) as the last fields, followed by the thirst state: only the own seat sees
    // them, every other seat gets 0 for all. The final two fields are public corpse phase counters.
    exportSkillBuildToPacket(os);
    os << mGoldCarried;
    exportItemsToPacket(os, seat);
    os << (seat == getSeat() ? mInfirmaryMood : 0.0);
    if(seat == getSeat())
    {
        os << mUrge;
        os << mCreatureDirt;
        exportThirstStateToPacket(os);
        exportSpaStateToPacket(os);
    }
    else
    {
        os << 0.0;
        os << 0.0;
        // The thirst state of other seats is not sent: every value is 0 (the lava spa state follows the tavern fields)
        os << 0.0;
        os << 0.0;
        os << 0.0;
        os << 0.0;
        os << 0.0;
        os << 0.0;
    }
    os << mCorpseTurns << mDecayTurns;
    os << mGhostBackpack << mGhostBeamTarget << mGhostBoxMode << mGhostThrowTarget << mGhostThrowTurns;
}

//! \brief Writes the thirst state to a packet: thirst, tavern mood, drunkenness and the turns of the hangover.
void Creature::exportThirstStateToPacket(ODPacket& os) const
{
    os << mThirst;
    os << mTavernMood;
    os << mDrunk;
    os << mHangoverTurns;
}

//! \brief Writes the lava spa state to a packet: the spa mood and the turns of the relaxation.
void Creature::exportSpaStateToPacket(ODPacket& os) const
{
    os << mSpaMood;
    os << mRelaxTurns;
}

//! \brief Reads the thirst state written by exportThirstStateToPacket.
void Creature::importThirstStateFromPacket(ODPacket& is)
{
    OD_ASSERT_TRUE(is >> mThirst);
    OD_ASSERT_TRUE(is >> mTavernMood);
    OD_ASSERT_TRUE(is >> mDrunk);
    OD_ASSERT_TRUE(is >> mHangoverTurns);
}

//! \brief Reads the lava spa state written by exportSpaStateToPacket.
void Creature::importSpaStateFromPacket(ODPacket& is)
{
    OD_ASSERT_TRUE(is >> mSpaMood);
    OD_ASSERT_TRUE(is >> mRelaxTurns);
}

//! \brief Reads the changing creature data sent by the server, the skill state last, and refreshes equipment
//! presentation.
void Creature::updateFromPacket(ODPacket& is)
{
    // What changed in this update can become a post of the feed. The state is only copied
    // for creatures of the local player while the feed is running.
    const bool postSource = isSocialFeedSource();
    social::CreatureSnapshot socialBefore;
    if(postSource)
        fillSocialSnapshot(socialBefore);
    const bool wasStaggering = isStaggering();
    const bool hadHangover = (mHangoverTurns > 0.0);

    MovableGameEntity::updateFromPacket(is);

    int seatId;
    unsigned int oldLevel = mLevel;
    uint32_t oldMoodValue = mOverlayMoodValue;
    uint32_t oldHealthValue = mOverlayHealthValue;
    Seat* oldSeat = getSeat();
    Seat* oldSeatPrison = mSeatPrison;
    OD_ASSERT_TRUE(is >> mLevel);
    OD_ASSERT_TRUE(is >> seatId);
    OD_ASSERT_TRUE(is >> mOverlayHealthValue);
    OD_ASSERT_TRUE(is >> mOverlayMoodValue);
    OD_ASSERT_TRUE(is >> mGroundSpeed);
    OD_ASSERT_TRUE(is >> mWaterSpeed);
    OD_ASSERT_TRUE(is >> mLavaSpeed);
    OD_ASSERT_TRUE(is >> mSpeedModifier);

    // A creature that walks changes between the walk clip and the hurt walk clip when it becomes badly hurt or
    // recovers (the clip is chosen in RenderManager::rrSetObjectAnimationState)
    if(!getIsOnServerMap() && getIsOnMap() && (getAnimationStateName() == EntityAnimation::walk_anim) &&
       (isLowHealthWalkStage(oldHealthValue) != isLowHealthWalking()))
    {
        RenderManager::getSingleton().rrSetObjectAnimationState(this, EntityAnimation::walk_anim, true);
    }

    // We do not scale the creature if it is picked up (because it is already not at its normal size). It will be
    // resized anyway when dropped
    if(getIsOnMap())
        RenderManager::getSingleton().rrScaleCreature(*this);

    if(getSeat()->getId() != seatId)
    {
        Seat* seat = getGameMap()->getSeatById(seatId);
        if(seat == nullptr)
        {
            OD_LOG_ERR("Creature " + getName() + ", wrong seatId=" + Helper::toString(seatId));
        }
        else
        {
            Seat* oldSeat = getSeat();
            setSeat(seat);
            social::PostLog::getSingleton().rosterChanged();
            // A creature that joins the local keeper from another seat was converted
            Player* localPlayer = getGameMap()->getLocalPlayer();
            if(getGameMap()->isRelationshipsEnabled() && (oldSeat != nullptr) && !oldSeat->isRogueSeat()
               && (localPlayer != nullptr) && (seat == localPlayer->getSeat()))
            {
                socialEvent(social::PostCategory::Converted);
            }
        }
    }

    OD_ASSERT_TRUE(is >> seatId);
    if(seatId == -1)
        mSeatPrison = nullptr;
    else
    {
        mSeatPrison = getGameMap()->getSeatById(seatId);
        if(mSeatPrison == nullptr)
        {
            OD_LOG_ERR("Creature " + getName() + ", wrong seatId=" + Helper::toString(seatId));
        }
    }

    OD_ASSERT_TRUE(is >> mIsHexenHen);
    updateHexenHenMesh();

    importMoodFromPacket(is);
    importActivityFromPacket(is);
    importProgressFromPacket(is);
    OD_ASSERT_TRUE(is >> mMana);
    importSkillBuildFromPacket(is);
    OD_ASSERT_TRUE(is >> mGoldCarried);
    OD_ASSERT_TRUE(importItemsFromPacket(is));
    OD_ASSERT_TRUE(is >> mInfirmaryMood);
    OD_ASSERT_TRUE(is >> mUrge);
    OD_ASSERT_TRUE(is >> mCreatureDirt);
    importThirstStateFromPacket(is);
    importSpaStateFromPacket(is);
    OD_ASSERT_TRUE(is >> mCorpseTurns >> mDecayTurns);
    OD_ASSERT_TRUE(is >> mGhostBackpack >> mGhostBeamTarget >> mGhostBoxMode >> mGhostThrowTarget >> mGhostThrowTurns);
    mGhostThrowClientTurns=mGhostThrowTurns;
    // The thief sack follows the gold carried; the creature mesh may not exist yet
    RenderManager::getSingleton().rrRefreshCreatureGoldSack(this);

    if(postSource)
    {
        social::CreatureSnapshot socialAfter;
        fillSocialSnapshot(socialAfter);
        social::CreaturePosts::reportUpdate(getGameMap()->getTurnNumber(), getName(),
            getDefinition()->getClassName(), getDefinition()->isWorker(), socialBefore, socialAfter);
        if(!socialAfter.mFilthyRoom.empty() && (socialAfter.mFilthyRoom != socialBefore.mFilthyRoom))
            socialFilthyRoom(socialAfter.mFilthyRoom);

        // The creature began to stagger (first time of a drunk episode) or woke up with a hangover
        if(!wasStaggering && isStaggering())
        {
            socialEvent(social::PostCategory::Drunk);
            if(CreatureReactions::getSingletonPtr() != nullptr)
                CreatureReactions::getSingleton().trigger(this, "Drunk");
        }
        if(!hadHangover && (mHangoverTurns > 0.0))
        {
            socialEvent(social::PostCategory::Hungover);
            if(CreatureReactions::getSingletonPtr() != nullptr)
                CreatureReactions::getSingleton().trigger(this, "Hangover");
        }
    }

    // Level up and payday are shown as cosmetic reactions of the creature
    if(CreatureReactions::getSingletonPtr() != nullptr)
        CreatureReactions::getSingleton().noteCreatureUpdate(this, oldLevel, oldMoodValue, oldHealthValue, oldSeat, oldSeatPrison);
}

bool Creature::isSocialFeedSource() const
{
    if(!social::PostLog::getSingleton().isActive() || getIsOnServerMap())
        return false;

    Player* localPlayer = getGameMap()->getLocalPlayer();
    return (localPlayer != nullptr) && (getSeat() == localPlayer->getSeat());
}

//! \brief Dirt stage from which a creature's room is filthy (the post "filthy room").
static const uint32_t FILTHY_ROOM_DIRT_STAGE = 3;

//! \brief The dirt stage of a room as the client knows it. The tiles of the client map carry no dirt value; the server
//! tells the dirt stage of every room in sight in the tile dirt cosmetic event, which the room ambience keeps.
//! \param room The room to ask.
//! \return The stage (1 - 3), 0 if the server has not told it (yet).
static uint32_t getClientRoomDirtStage(const Room& room)
{
    if(RoomAmbience::getSingletonPtr() == nullptr)
        return 0;

    return RoomAmbience::getSingleton().getRoomDirtStage(room.getName());
}

void Creature::fillSocialSnapshot(social::CreatureSnapshot& snapshot) const
{
    snapshot.mLevel = mLevel;
    snapshot.mHealthStage = mOverlayHealthValue;
    snapshot.mMoodBits = mOverlayMoodValue;
    snapshot.mMoodLevel = mMoodValue;
    snapshot.mActivity = mActivity;

    // The filthy room the creature stands in (the client map has no tile dirt: the room stage comes from the cosmetic dirt event)
    snapshot.mFilthyRoom.clear();
    const Tile* tile = getPositionTile();
    const Room* room = (tile == nullptr) ? nullptr : tile->getCoveringRoom();
    if((room != nullptr) && (room->getType() != RoomType::prison) && (room->getType() != RoomType::torture) &&
       (room->getType() != RoomType::crypt) && (getClientRoomDirtStage(*room) >= FILTHY_ROOM_DIRT_STAGE))
        snapshot.mFilthyRoom = room->getName();
}

void Creature::socialCreatureAdded()
{
    social::PostLog::getSingleton().rosterChanged();
    socialEvent(social::PostCategory::Arrived);
}

void Creature::socialCreatureRemoved()
{
    social::PostLog::getSingleton().rosterChanged();
    if(!isSocialFeedSource())
        return;

    social::CreaturePosts::reportRemoval(getGameMap()->getTurnNumber(), getName(),
        getDefinition()->getClassName(), getDefinition()->isWorker(), mOverlayMoodValue);
}

//! \brief Adds the mood points of the keeper's margin or a direct gift without an invented cap.
void Creature::addMerchantMood(double points)
{ mMerchantMood += points; mNeedFireRefresh = true; }

//! \brief Keeps one owner-only deal notification until its next creature update is written.
void Creature::setLastItemDeal(uint8_t deal, const std::string& name)
{ mLastItemDeal = deal; mLastItemName = name; mNeedFireRefresh = true; }

//! \brief Adds a post of the given category for this creature to the feed. Only creatures of the local player post.
//! \param category What the creature posts about.
//! \param other Profile name of the second creature of the post (the opponent of a duel), empty for other posts.
void Creature::socialEvent(social::PostCategory category, const std::string& other)
{
    if(!isSocialFeedSource())
        return;

    social::PostLog::getSingleton().addPost(getGameMap()->getTurnNumber(), getName(),
        getDefinition()->getClassName(), getDefinition()->isWorker(), category, 0, other);
}

//! \brief Posts "filthy room" for this creature, at most once per FilthyPostSeconds for the same room.
void Creature::socialFilthyRoom(const std::string& roomName)
{
    if(!isSocialFeedSource())
        return;

    int64_t turn = getGameMap()->getTurnNumber();
    int64_t limitTurns = static_cast<int64_t>(
        ConfigManager::getSingleton().getDirtConfigDouble("FilthyPostSeconds") * ODApplication::turnsPerSecond);
    std::map<std::string, int64_t>::iterator it = mFilthyPostTurn.find(roomName);
    if((it != mFilthyPostTurn.end()) && (turn >= it->second) && (turn - it->second < limitTurns))
        return;

    mFilthyPostTurn[roomName] = turn;
    socialEvent(social::PostCategory::Filthy);
}

double Creature::getExperienceProgress() const
{
    if(!getIsOnServerMap())
        return mExperienceProgress;
    if(mLevel >= MAX_LEVEL)
        return 1.0;
    const double needed = mDefinition->getXPNeededWhenLevel(mLevel);
    return needed > 0.0 ? std::max(0.0, std::min(1.0, mExp / needed)) : 0.0;
}

//! \brief Sends the active room-work or attack recovery without dropping specialized job progress.
void Creature::exportProgressToPacket(ODPacket& os, const Seat* seat) const
{
    if(!ODServer::getSingleton().supportsCreatureProgress(seat->getPlayer()))
        return;
    const bool working = CreatureAction::isRoomWorkAction(getActivity().action) &&
        mJobCooldown > 0 && mJobCooldownDuration > 0;
    // The attack recovery can be a fraction of a turn, so both values travel as double
    const double remaining = working ? static_cast<double>(mJobCooldown) : mAttackRecoveryTurns;
    const double duration = working ? static_cast<double>(mJobCooldownDuration) : mAttackRecoveryDuration;
    os << getExperienceProgress() << remaining << duration << mAttackRecoverySerial;
}

void Creature::importProgressFromPacket(ODPacket& is)
{
    mHasProgressInformation = false;
    if(!ODClient::getSingleton().supportsCreatureProgress())
        return;
    double experience = 0.0;
    double remaining = 0.0;
    double duration = 0.0;
    uint32_t serial = 0;
    if(!(is >> experience >> remaining >> duration >> serial))
    {
        OD_LOG_ERR("Incomplete creature progress for " + getName());
        return;
    }
    if(!std::isfinite(experience) || experience < 0.0 || experience > 1.0 ||
       !std::isfinite(remaining) || !std::isfinite(duration) || remaining < 0.0 || remaining > duration)
    {
        OD_LOG_ERR("Invalid creature progress for " + getName());
        return;
    }
    mExperienceProgress = experience;
    mAttackRecoveryTurns = remaining;
    mAttackRecoveryDuration = duration;
    mAttackRecoverySerial = serial;
    mHasProgressInformation = true;
}

void Creature::exportMoodToPacket(ODPacket& os, const Seat* seat) const
{
    if(!ODServer::getSingleton().supportsCreatureMood(seat->getPlayer()))
        return;

    int32_t mood = static_cast<int32_t>(seat->isAlliedSeat(getSeat()) ?
        mMoodValue : CreatureMoodLevel::Unknown);
    os << mood;
}

void Creature::importMoodFromPacket(ODPacket& is)
{
    mMoodValue = CreatureMoodLevel::Unknown;
    if(!ODClient::getSingleton().supportsCreatureMood())
        return;

    int32_t mood = static_cast<int32_t>(CreatureMoodLevel::Unknown);
    OD_ASSERT_TRUE(is >> mood);
    if(mood < static_cast<int32_t>(CreatureMoodLevel::Unknown) ||
       mood > static_cast<int32_t>(CreatureMoodLevel::Furious))
    {
        OD_LOG_ERR("Invalid creature mood=" + Helper::toString(mood));
        return;
    }
    mMoodValue = static_cast<CreatureMoodLevel>(mood);
}

//! \brief Derives activity and assigned room from ordinary and specialized room actions.
CreatureActivity Creature::getActivity() const
{
    CreatureActivity activity;
    if(!getIsOnMap() || !isAlive() || isKo())
        return activity;

    if(!getIsOnServerMap())
        return mActivity;

    activity.known = true;
    if(!mActions.empty())
        activity.action = mActions.back()->getType();

    // Walk from the active end of mActions to the oldest action
    std::vector<std::unique_ptr<CreatureAction>>::const_reverse_iterator it;
    for(it = mActions.rbegin(); it != mActions.rend(); ++it)
    {
        const CreatureActionType type = (*it)->getType();
        if(activity.task == CreatureActionType::nb && type != CreatureActionType::walkToTile &&
           type != CreatureActionType::parkToTile)
            activity.task = type;

        if((type == CreatureActionType::useToilet) &&
           (static_cast<const CreatureActionUseToilet*>(it->get())->getSeatTile() != nullptr))
        {
            activity.assignedRoom = RoomType::toilet;
            activity.inAssignedRoom = true;
            break;
        }

        if(!CreatureAction::isRoomWorkAction(type))
            continue;

        const Room* room = static_cast<const CreatureActionUseRoom*>(it->get())->getRoom();
        if(room != nullptr)
        {
            activity.assignedRoom = room->getType();
            const Tile* tile = getPositionTile();
            activity.inAssignedRoom = tile != nullptr && tile->getCoveringRoom() == room;
        }
        break;
    }
    return activity;
}

void Creature::exportActivityToPacket(ODPacket& os, const Seat* seat) const
{
    if(!ODServer::getSingleton().supportsCreatureActivity(seat->getPlayer()))
        return;

    const CreatureActivity activity = seat->isAlliedSeat(getSeat()) ? getActivity() : CreatureActivity();
    os << activity.known;
    if(!activity.known)
        return;

    os << static_cast<int32_t>(activity.action) << static_cast<int32_t>(activity.task)
       << static_cast<int32_t>(activity.assignedRoom) << activity.inAssignedRoom;
}

void Creature::importActivityFromPacket(ODPacket& is)
{
    mActivity = CreatureActivity();
    if(!ODClient::getSingleton().supportsCreatureActivity())
        return;

    CreatureActivity activity;
    if(!(is >> activity.known))
    {
        OD_LOG_ERR("Missing creature activity for " + getName());
        return;
    }
    if(!activity.known)
        return;

    int32_t action = 0;
    int32_t task = 0;
    int32_t room = 0;
    if(!(is >> action >> task >> room >> activity.inAssignedRoom))
    {
        OD_LOG_ERR("Incomplete creature activity for " + getName());
        return;
    }
    if(action < 0 || action > static_cast<int32_t>(CreatureActionType::nb) ||
       task < 0 || task > static_cast<int32_t>(CreatureActionType::nb) ||
       room < 0 || room >= static_cast<int32_t>(RoomType::nbRooms))
    {
        OD_LOG_ERR("Invalid creature activity for " + getName());
        return;
    }
    activity.action = static_cast<CreatureActionType>(action);
    activity.task = static_cast<CreatureActionType>(task);
    activity.assignedRoom = static_cast<RoomType>(room);
    mActivity = activity;
}

void Creature::updateTilesInSight()
{
    Tile* posTile = getPositionTile();
    if (posTile == nullptr)
        return;

    // The tiles with sight radius without constraints
    mTilesWithinSightRadius = getGameMap()->circularRegion(posTile->getX(), posTile->getY(), getTileSightRadius());

    // Only the tiles the creature can "see".
    mVisibleTiles = getGameMap()->visibleTiles(posTile->getX(), posTile->getY(), getTileSightRadius());
}

std::vector<GameEntity*> Creature::getVisibleEnemyObjects()
{
    return getVisibleForce(getSeat(), true);
}

std::vector<GameEntity*> Creature::getReachableAttackableObjects(const std::vector<GameEntity*>& objectsToCheck)
{
    std::vector<GameEntity*> tempVector;
    Tile* myTile = getPositionTile();

    // Loop over the vector of objects we are supposed to check.
    for (unsigned int i = 0; i < objectsToCheck.size(); ++i)
    {
        // Try to find a valid path from the tile this creature is in to the nearest tile where the current target object is.
        GameEntity* entity = objectsToCheck[i];
        // We only consider alive objects
        if(entity->getHP(nullptr) <= 0)
            continue;

        Tile* objectTile = entity->getCoveredTile(0);
        if (getGameMap()->pathExists(this, myTile, objectTile))
            tempVector.push_back(objectsToCheck[i]);
    }

    return tempVector;
}

std::vector<GameEntity*> Creature::getCreaturesFromList(const std::vector<GameEntity*> &objectsToCheck, bool workersOnly)
{
    std::vector<GameEntity*> tempVector;

    // Loop over the vector of objects we are supposed to check.
    for (std::vector<GameEntity*>::const_iterator it = objectsToCheck.begin(); it != objectsToCheck.end(); ++it)
    {
        // Try to find a valid path from the tile this creature is in to the nearest tile where the current target object is.
        GameEntity* entity = *it;
        // We only consider alive objects
        if(entity->getObjectType() != GameEntityType::creature)
            continue;

        if(workersOnly && !static_cast<Creature*>(entity)->getDefinition()->isWorker())
            continue;

        tempVector.push_back(entity);
    }

    return tempVector;
}

std::vector<GameEntity*> Creature::getVisibleAlliedObjects()
{
    return getVisibleForce(getSeat(), false);
}

std::vector<GameEntity*> Creature::getVisibleForce(Seat* seat, bool invert)
{
    return getGameMap()->getVisibleForce(mVisibleTiles, seat, invert);
}

void Creature::computeVisualDebugEntities()
{
    if(!getIsOnServerMap())
        return;

    mHasVisualDebuggingEntities = true;

    updateTilesInSight();

    ServerNotification *serverNotification = new ServerNotification(
        ServerNotificationType::refreshCreatureVisDebug, nullptr);

    const std::string& name = getName();
    serverNotification->mPacket << name;
    serverNotification->mPacket << true;
    if(getIsOnMap())
    {
        uint32_t nbTiles = mVisibleTiles.size();
        serverNotification->mPacket << nbTiles;

        for (Tile* tile : mVisibleTiles)
            getGameMap()->tileToPacket(serverNotification->mPacket, tile);
    }
    else
    {
        uint32_t nbTiles = 0;
        serverNotification->mPacket << nbTiles;
    }

    ODServer::getSingleton().queueServerNotification(serverNotification);
}

void Creature::refreshVisualDebugEntities(const std::vector<Tile*>& tiles)
{
    if(getIsOnServerMap())
        return;

    mHasVisualDebuggingEntities = true;

    for (Tile* tile : tiles)
    {
        // We check if the visual debug is already on this tile
        if(std::find(mVisualDebugEntityTiles.begin(), mVisualDebugEntityTiles.end(), tile) != mVisualDebugEntityTiles.end())
            continue;

        RenderManager::getSingleton().rrCreateCreatureVisualDebug(this, tile);

        mVisualDebugEntityTiles.push_back(tile);
    }

    // now, we check if visual debug should be removed from a tile
    for (std::vector<Tile*>::iterator it = mVisualDebugEntityTiles.begin(); it != mVisualDebugEntityTiles.end();)
    {
        Tile* tile = *it;
        if(std::find(tiles.begin(), tiles.end(), tile) != tiles.end())
        {
            ++it;
            continue;
        }

        it = mVisualDebugEntityTiles.erase(it);

        RenderManager::getSingleton().rrDestroyCreatureVisualDebug(this, tile);
    }
}

void Creature::stopComputeVisualDebugEntities()
{
    if(!getIsOnServerMap())
        return;

    mHasVisualDebuggingEntities = false;

    ServerNotification *serverNotification = new ServerNotification(
        ServerNotificationType::refreshCreatureVisDebug, nullptr);
    const std::string& name = getName();
    serverNotification->mPacket << name;
    serverNotification->mPacket << false;
    ODServer::getSingleton().queueServerNotification(serverNotification);
}

void Creature::destroyVisualDebugEntities()
{
    if(getIsOnServerMap())
        return;

    mHasVisualDebuggingEntities = false;

    for (Tile* tile : mVisualDebugEntityTiles)
    {
        if (tile == nullptr)
            continue;

        RenderManager::getSingleton().rrDestroyCreatureVisualDebug(this, tile);
    }
    mVisualDebugEntityTiles.clear();
}

std::vector<Tile*> Creature::getCoveredTiles()
{
    std::vector<Tile*> tempVector;
    tempVector.push_back(getPositionTile());
    return tempVector;
}

Tile* Creature::getCoveredTile(int index)
{
    if(index > 0)
    {
        OD_LOG_ERR("name=" + getName() + ", index=" + Helper::toString(index));
        return nullptr;
    }

    return getPositionTile();
}

uint32_t Creature::numCoveredTiles() const
{
    if(getPositionTile() == nullptr)
        return 0;

    return 1;
}

bool Creature::CloseStatsWindow(const CEGUI::EventArgs& /*e*/)
{
    destroyStatsWindow();
    return true;
}

void Creature::createStatsWindow()
{
    if (mStatsWindow != nullptr)
        return;

    ClientNotification *clientNotification = new ClientNotification(
        ClientNotificationType::askCreatureInfos);
    std::string name = getName();
    clientNotification->mPacket << name << true;
    ODClient::getSingleton().queueClientNotification(clientNotification);

    CEGUI::Window* rootWindow = CEGUI::System::getSingleton().getDefaultGUIContext().getRootWindow();

    Gui& gui = ODFrameListener::getSingleton().getModeManager()->getGui();
    mStatsWindow = gui.createCreatureProfileWindow(std::string("CreatureStatsWindows_") + getName());
    gui.createCreatureProfilePage(mStatsWindow->getChild("ProfilePage"));

    // We want to close the window when the cross is clicked
    mStatsWindow->subscribeEvent(CEGUI::FrameWindow::EventCloseClicked,
        CEGUI::Event::Subscriber(&Creature::CloseStatsWindow, this));
    mStatsWindow->getChild("ProfileTab")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&Creature::ProfileTabClicked, this));
    mStatsWindow->getChild("StatsTab")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&Creature::StatsTabClicked, this));
    mStatsWindow->getChild("BookTab")->subscribeEvent(CEGUI::PushButton::EventClicked,
        CEGUI::Event::Subscriber(&Creature::BookTabClicked, this));
    const char* const linkNames[] = {"FriendLink0", "FriendLink1", "FoeLink"};
    for(const char* linkName : linkNames)
    {
        mStatsWindow->getChild(std::string("ProfilePage/Content/") + linkName)->subscribeEvent(
            CEGUI::PushButton::EventClicked, CEGUI::Event::Subscriber(&Creature::ProfileLinkClicked, this));
    }

    rootWindow->addChild(mStatsWindow);
    mStatsWindow->show();

    showStatsPage(false);
    updateStatsWindow("Loading...");
}

void Creature::destroyStatsWindow()
{
    if (mStatsWindow != nullptr)
    {
        ClientNotification *clientNotification = new ClientNotification(
            ClientNotificationType::askCreatureInfos);
        std::string name = getName();
        clientNotification->mPacket << name << false;
        ODClient::getSingleton().queueClientNotification(clientNotification);

        mStatsWindow->destroy();
        mStatsWindow = nullptr;
    }
}

void Creature::updateStatsWindow(const std::string& txt)
{
    if (mStatsWindow == nullptr)
        return;

    CEGUI::Window* textWindow = mStatsWindow->getChild("StatsText");
    textWindow->setText(txt);
    // The server refreshes the statistics while the card is open, so the profile page follows
    refreshProfilePage();
}

bool Creature::ProfileTabClicked(const CEGUI::EventArgs& /*e*/)
{
    showStatsPage(false);
    return true;
}

bool Creature::StatsTabClicked(const CEGUI::EventArgs& /*e*/)
{
    showStatsPage(true);
    return true;
}

bool Creature::BookTabClicked(const CEGUI::EventArgs& /*e*/)
{
    GameMode* gameMode = dynamic_cast<GameMode*>(ODFrameListener::getSingleton().getModeManager()->getCurrentMode());
    if(gameMode != nullptr)
        gameMode->showSocialWindow(getName());
    return true;
}

bool Creature::ProfileLinkClicked(const CEGUI::EventArgs& e)
{
    const CEGUI::WindowEventArgs& args = static_cast<const CEGUI::WindowEventArgs&>(e);
    if(!args.window->isUserStringDefined("Creature"))
        return true;

    GameMode* gameMode = dynamic_cast<GameMode*>(ODFrameListener::getSingleton().getModeManager()->getCurrentMode());
    if(gameMode != nullptr)
        gameMode->showSocialWindow(std::string(args.window->getUserString("Creature").c_str()));
    return true;
}

void Creature::showStatsPage(bool stats)
{
    if (mStatsWindow == nullptr)
        return;

    mStatsWindow->getChild("ProfilePage")->setVisible(!stats);
    mStatsWindow->getChild("StatsText")->setVisible(stats);
    // The active tab stays enabled and is shown in gold between brackets
    SocialWindow::setTabState(mStatsWindow->getChild("ProfileTab"), "Profile", !stats);
    SocialWindow::setTabState(mStatsWindow->getChild("StatsTab"), "Stats", stats);
}

void Creature::refreshProfilePage()
{
    if (mStatsWindow == nullptr)
        return;

    const CreatureDefinition* definition = getDefinition();
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const social::CreatureProfile& profile = cache.getProfile(getName(), definition->getClassName(), definition->isWorker());
    std::string classDisplayName = social::SocialGenerator::displayClassName(cache.getData(), definition->getClassName());
    mStatsWindow->setText(profile.getFullName() + " (" + classDisplayName + ")");

    fillProfilePage(mStatsWindow->getChild("ProfilePage/Content"));
}

std::string Creature::getGender() const
{
    return social::SocialProfileCache::getCreatureGender(getName(), getDefinition()->getClassName());
}

//! \brief Seconds of one minute, for the time in the effect lines of the Dungeonbook page.
static const uint32_t PROFILE_SECONDS_PER_MINUTE = 60;

//! \brief The lines of the active buffs and debuffs of a creature for the Dungeonbook page, buffs first: the buff
//! Relaxed while the relaxation lasts, the debuff Hangover while the hangover lasts. Each line shows the time that is
//! left as minutes:seconds (turns divided by the turns per second, seconds rounded down).
//! \param relaxTurns The turns the relaxation lasts, 0 or less for none.
//! \param hangoverTurns The turns the hangover lasts, 0 or less for none.
//! \return The lines separated by a line break, empty when no effect is active.
static std::string getProfileEffectsText(double relaxTurns, double hangoverTurns)
{
    std::string effects;
    const double turnsPerSecond = ODApplication::turnsPerSecond;
    for(uint32_t kind = 0; kind < 2; ++kind)
    {
        const bool isBuff = (kind == 0);
        const double turns = isBuff ? relaxTurns : hangoverTurns;
        if(turns <= 0.0)
            continue;

        const uint32_t totalSeconds = static_cast<uint32_t>(std::floor(turns / turnsPerSecond));
        const uint32_t seconds = totalSeconds % PROFILE_SECONDS_PER_MINUTE;
        std::string line = isBuff ? "Buff: Relaxed (" : "Debuff: Hangover (";
        line += Helper::toString(totalSeconds / PROFILE_SECONDS_PER_MINUTE) + ":" + (seconds < 10 ? "0" : "") +
            Helper::toString(seconds) + ")";
        if(!effects.empty())
            effects += "\n";
        effects += line;
    }
    return effects;
}

//! \brief Fills the social page and transmitted item slots before its normal responsive layout.
float Creature::fillProfilePage(CEGUI::Window* page)
{
    const CreatureDefinition* definition = getDefinition();
    social::SocialProfileCache& cache = social::SocialProfileCache::getSingleton();
    const social::CreatureProfile& profile = cache.getProfile(getName(), definition->getClassName(), definition->isWorker());

    // Mood, friends and the like are only known for creatures of the local player and its allies
    Seat* localSeat = nullptr;
    if(getGameMap()->getLocalPlayer() != nullptr)
        localSeat = getGameMap()->getLocalPlayer()->getSeat();
    bool isAllied = (localSeat != nullptr) &&
        (getSeat()->isAlliedSeat(localSeat) || ((mSeatPrison != nullptr) && mSeatPrison->isAlliedSeat(localSeat)));
    // The relaxation and hangover effects are only shown for the creatures of the own seat
    const bool isOwn = (localSeat != nullptr) && (getSeat() == localSeat);

    // The composed picture of the creature's appearance; without one (no appearance yet, missing or invalid
    // manifest) the tinted preview portrait is the fallback and no remarks are shown. Asked on every fill, since
    // the appearance can arrive later, and the image is set right away because the cache may release it.
    const CEGUI::Image* appearanceImage = getCreatureAppearanceImage(getName(), mAppearance);
    if(appearanceImage != nullptr)
    {
        page->getChild("Portrait/Image")->setProperty("Image", appearanceImage->getName());
    }
    else
    {
        page->getChild("Portrait/Image")->setProperty("Image",
            getCreatureProfilePortraitImage(getName(), definition->getMeshName(), profile.mGender).getName());
    }
    page->getChild("NameText")->setText(profile.getFullName());

    // The champion shows a crown instead of its level
    std::string handle = makeProfileHandle(profile) + " - " + (definition->isWorker() ? "Worker" : "Fighter");
    if(definition->isChampion())
        handle += " - " + CHAMPION_CROWN_MARKUP;
    else
        handle += " - Level " + Helper::toString(getLevel());
    page->getChild("HandleText")->setText(handle);

    std::string age = (profile.mAgeText == Helper::toString(profile.mAge)) ? "Age " + profile.mAgeText : profile.mAgeText;
    if(!profile.mGender.empty())
        age += " - " + profile.mGender;
    page->getChild("AgeText")->setText(age);
    // With the relationship option the status of the own creatures comes from the real relationships
    // and nothing changes for other creatures or with the option off
    ProfileRelations relations;
    bool showRelations = isAllied && getGameMap()->isRelationshipsEnabled() &&
        (getGameMap()->getCreatureRelationships() != nullptr);
    if(showRelations)
        collectProfileRelations(getGameMap(), *getGameMap()->getCreatureRelationships(), getName(), relations);
    if(showRelations)
    {
        page->getChild("RelationText")->setText("Relationship: " + social::CreaturePosts::getRelationshipStatus(
            relations.mHasPartner, !relations.mClose.empty(), relations.mHasHated, relations.mHasNemesis));
    }
    else
    {
        page->getChild("RelationText")->setText("Relationship: " + profile.mRelationship);
    }
    page->getChild("FromText")->setText("From: " + profile.mHometown);
    page->getChild("JobText")->setText("Job: " + profile.mJob);
    page->getChild("AttributesText")->setText(getAttributeSummaryText());
    page->getChild("EquipmentText")->setText("Equipment: " + getEquipmentText());
    // Only the owning seat receives private slots; foreign copies reveal the two hands.
    for(std::size_t slot = 0; slot < 13; ++slot)
    {
        std::unique_ptr<ItemInstance> spawnFallback;
        const ItemInstance* item = nullptr;
        if(slot < mEquipment.size())
            item = mEquipment[slot].get();
        else if(localSeat == getSeat() && slot < 9 && slot - 6 < mPotionSlots.size())
            item = mPotionSlots[slot - 6].get();
        else if(localSeat == getSeat() && slot >= 9)
            item = mInventory[slot - 9].get();
        if(localSeat != getSeat() && slot >= VISIBLE_ITEM_HAND_SLOTS)
            item = nullptr;
        // Empty worn hand slots retain the creature's visible permanent spawn equipment.
        if(item == nullptr && slot < VISIBLE_ITEM_HAND_SLOTS)
        {
            const Weapon* weapon = slot == 0 ? mWeaponR : mWeaponL;
            if(weapon != nullptr)
            {
                spawnFallback = ItemDrops::poorWeapon(*weapon);
                item = spawnFallback.get();
            }
        }
        CEGUI::Window* image = page->getChild("EquipmentRow/Slot" + Helper::toString(slot));
        const std::string name = item == nullptr ? "" : "ItemImages/" + item->getImageName();
        image->setProperty("Image", !name.empty() && CEGUI::ImageManager::getSingleton().isDefined(name) ?
            name : "OpenDungeonsIcons/ItemSlotEmpty");
        image->setTooltipText(item == nullptr ? "" : item->describe(getGameMap()));
        CEGUI::Window* frame = image->getChild("QualityFrame");
        frame->setVisible(item != nullptr);
        if(item != nullptr)
            frame->setProperty("Image", "OpenDungeonsIcons/ItemFrame" + qualityName(item->mQuality));
    }
    page->getChild("PathText")->setText("Path: " + getSkillPathText());
    page->getChild("SkillsText")->setText("Skills: " + getSkillListText());
    page->getChild("BioText")->setText("\"" + profile.mBio + "\"");
    std::vector<std::string> likes(profile.mLikes, profile.mLikes + PROFILE_LIST_SIZE);
    std::vector<std::string> dislikes(profile.mDislikes, profile.mDislikes + PROFILE_LIST_SIZE);
    page->getChild("LikesText")->setText("Likes: " + joinProfileList(likes));
    page->getChild("DislikesText")->setText("Dislikes: " + joinProfileList(dislikes));
    // Remarks that match the parts of the picture, only for the composed picture
    std::string quirks;
    if(appearanceImage != nullptr)
    {
        quirks = DungeonbookQuirkLogic::formatRemarks(getCreatureAppearanceRemarks(getName(), mAppearance));
    }
    page->getChild("QuirksText")->setVisible(!quirks.empty());
    page->getChild("QuirksText")->setText(quirks);

    // Health is shown as the same stage the creature overlay uses, the client has no exact value
    CEGUI::ProgressBar* healthBar = static_cast<CEGUI::ProgressBar*>(page->getChild("HealthBar"));
    healthBar->setProgress(1.0f - static_cast<float>(mOverlayHealthValue) /
        static_cast<float>(NB_OVERLAY_HEALTH_VALUES - 1));
    page->getChild("HealthLabel")->setText("Health");
    CEGUI::ProgressBar* experienceBar = static_cast<CEGUI::ProgressBar*>(page->getChild("ExperienceBar"));
    bool showExperience = isAllied && hasProgressInformation();
    experienceBar->setVisible(showExperience);
    page->getChild("ExperienceLabel")->setVisible(showExperience);
    page->getChild("ExperienceLabel")->setText("XP");
    if(showExperience)
        experienceBar->setProgress(static_cast<float>(getExperienceProgress()));

    Gui& gui = ODFrameListener::getSingleton().getModeManager()->getGui();
    CEGUI::Window* friendsLabel = page->getChild("FriendsLabel");
    CEGUI::Window* foeLabel = page->getChild("FoeLabel");
    CEGUI::Window* friendLinks[PROFILE_MAX_FRIENDS] = {page->getChild("FriendLink0"), page->getChild("FriendLink1")};
    CEGUI::Window* foeLink = page->getChild("FoeLink");
    CEGUI::Window* statusText = page->getChild("StatusText");
    CEGUI::Window* latestText = page->getChild("LatestText");
    CEGUI::Window* relationsText = page->getChild("RelationsText");
    relationsText->setVisible(showRelations);
    friendsLabel->setVisible(isAllied);
    foeLabel->setVisible(isAllied);
    for(CEGUI::Window* friendLink : friendLinks)
        friendLink->setVisible(false);
    foeLink->setVisible(false);
    statusText->setVisible(isAllied);
    latestText->setVisible(isAllied);

    // The buffs and debuffs row: only for the creatures of our own side and only while an effect is active
    CEGUI::Window* effectsText = page->getChild("EffectsText");
    const std::string effects = getProfileEffectsText(mRelaxTurns, mHangoverTurns);
    effectsText->setText(effects);
    effectsText->setVisible(isOwn && !effects.empty());
    if(!isAllied)
        return gui.layoutCreatureProfilePage(page);

    // The friends only change when a creature is added, removed or changes seat, so they are
    // computed again only when the roster version of the post log changed
    social::SocialProfileCache::FriendsAndFoe relationFriends;
    const social::SocialProfileCache::FriendsAndFoe* cachedFriends = nullptr;
    if(showRelations)
    {
        // The real friends and the worst enemy replace the ones derived from the names
        relationFriends.mFriends = relations.mClose;
        if(!relations.mAgainst.empty())
            relationFriends.mFoe = relations.mAgainst[0];
        cachedFriends = &relationFriends;

        // The web: everybody the creature has a friendship or a grudge with
        std::string web = "Close: ";
        for(std::size_t i = 0; i < relations.mClose.size(); ++i)
            web += (i > 0 ? ", " : "") + relations.mTierText[relations.mClose[i]];
        if(relations.mClose.empty())
            web += "nobody yet";
        web += "\nAgainst: ";
        for(std::size_t i = 0; i < relations.mAgainst.size(); ++i)
            web += (i > 0 ? ", " : "") + relations.mTierText[relations.mAgainst[i]];
        if(relations.mAgainst.empty())
            web += "nobody";
        relationsText->setText(web);
    }
    else
    {
        uint32_t rosterVersion = social::PostLog::getSingleton().getRosterVersion();
        cachedFriends = cache.findFriendsAndFoe(getName(), rosterVersion);
        if(cachedFriends == nullptr)
        {
            social::SocialProfileCache::FriendsAndFoe computed;
            computed.mRosterVersion = rosterVersion;
            findFriendsAndFoe(getName(), getGameMap()->getCreaturesBySeat(localSeat), computed.mFriends, computed.mFoe);
            cache.storeFriendsAndFoe(getName(), computed);
            cachedFriends = cache.findFriendsAndFoe(getName(), rosterVersion);
        }
    }
    if(cachedFriends == nullptr)
        return gui.layoutCreatureProfilePage(page);
    // Each name is a button of its own, so no name is cut off; the label shares the first line with the first name
    std::size_t nbFriendLinks = 0;
    for(std::size_t i = 0; (i < cachedFriends->mFriends.size()) && (nbFriendLinks < PROFILE_MAX_FRIENDS); ++i)
    {
        std::string friendName = getProfileNameOfCreature(getGameMap(), cachedFriends->mFriends[i]);
        if(friendName.empty())
            continue;

        friendLinks[nbFriendLinks]->setText(friendName);
        friendLinks[nbFriendLinks]->setUserString("Creature", cachedFriends->mFriends[i]);
        friendLinks[nbFriendLinks]->setVisible(true);
        ++nbFriendLinks;
    }
    friendsLabel->setText(nbFriendLinks > 0 ? "Friends:" : "Friends: none yet");

    std::string foeName = cachedFriends->mFoe.empty() ? std::string() :
        getProfileNameOfCreature(getGameMap(), cachedFriends->mFoe);
    if(foeName.empty())
    {
        foeLabel->setText("Foe: none");
    }
    else
    {
        foeLabel->setText("Foe:");
        foeLink->setText(foeName);
        foeLink->setUserString("Creature", cachedFriends->mFoe);
        foeLink->setVisible(true);
    }

    std::string moodLine = social::SocialGenerator::moodLine(cache.getData(),
        getName(), definition->getClassName(), definition->isWorker(),
        getProfileMoodState(getOverlayMoodValue(), mMoodValue));
    std::string status = "Status";
    if(mMoodValue != CreatureMoodLevel::Unknown)
        status += " (" + getProfileMoodState(0, mMoodValue) + ")";
    statusText->setText(status + ": " + (moodLine.empty() ? std::string("...") : moodLine));

    std::string latestLine = SocialWindow::describeLatestPost(getName(), getGameMap()->getTurnNumber());
    latestText->setText(latestLine.empty() ? std::string("Latest: nothing posted yet") : latestLine);
    return gui.layoutCreatureProfilePage(page);
}

std::string Creature::getRelationshipTooltip()
{
    GameMap* gameMap = getGameMap();
    Player* localPlayer = gameMap->getLocalPlayer();
    if(getIsOnServerMap() || !gameMap->isRelationshipsEnabled() || (gameMap->getCreatureRelationships() == nullptr)
       || (localPlayer == nullptr) || !getSeat()->isAlliedSeat(localPlayer->getSeat()) || isInPrison())
        return std::string();

    ProfileRelations relations;
    collectProfileRelations(gameMap, *gameMap->getCreatureRelationships(), getName(), relations);
    std::string line;
    if(!relations.mClose.empty())
        line += "Closest: " + relations.mTierText[relations.mClose[0]];
    if(!relations.mAgainst.empty())
    {
        if(!line.empty())
            line += " - ";
        line += "Against: " + relations.mTierText[relations.mAgainst[0]];
    }
    return line;
}

//! \brief Builds the creature stats, including its current infirmary discharge target.
//! \brief Returns the unmasked server-side statistics for existing internal callers.
std::string Creature::getStatsText()
{
    return getStatsText(getSeat());
}

//! \brief Builds statistics while masking new private item fields for foreign viewing seats.
std::string Creature::getStatsText(const Seat* viewer)
{
    // The creatures are not refreshed at each turn so this information is relevant in the server
    // GameMap only
    const std::string formatTitleOn = "[font='MedievalSharp-10'][colour='FFF2C860']";
    const std::string formatTitleOff = "[font='MedievalSharp-8'][colour='FFE8DCC0']";
    const bool showPrivateItems = viewer == getSeat();

    std::stringstream tempSS;
    tempSS << formatTitleOn << "Characteristics" << formatTitleOff << std::endl;
    if(getDefinition()->isChampion())
        tempSS << "Level: " << CHAMPION_CROWN_MARKUP << std::endl;
    else
        tempSS << "Level: " << getLevel() << std::endl;
    tempSS << "Strength / Dexterity / Life / Mana: " << formatDisplayNumber(getStrength()) << " / "
        << formatDisplayNumber(getDexterity()) << " / " << formatDisplayNumber(getLife()) << " / "
        << formatDisplayNumber(getMana()) << std::endl;
    tempSS << "Critical chance: " << formatFixedNumber(getCritChance()) << " %" << std::endl;
    tempSS << "Mana: " << formatDisplayNumber(getCurrentMana()) << " / " << formatDisplayNumber(getMaxMana())
        << std::endl;
    tempSS << "Equipment: ";
    for(std::size_t index = 0; index < mEquipment.size(); ++index)
    {
        if(index != 0)
            tempSS << " / ";
        const ItemInstance* item = (showPrivateItems || index < VISIBLE_ITEM_HAND_SLOTS) ?
            mEquipment[index].get() : nullptr;
        tempSS << getItemSlotDisplayText(item, getGameMap()) << formatTitleOff;
    }
    tempSS << std::endl << "Potions: ";
    for(std::size_t index = 0; index < mPotionSlots.size(); ++index)
    {
        if(index != 0)
            tempSS << " / ";
        tempSS << getItemSlotDisplayText(showPrivateItems ? mPotionSlots[index].get() : nullptr, getGameMap())
            << formatTitleOff;
    }
    tempSS << std::endl << "Inventory: ";
    for(std::size_t index = 0; index < mInventory.size(); ++index)
    {
        if(index != 0)
            tempSS << " / ";
        tempSS << getItemSlotDisplayText(showPrivateItems ? mInventory[index].get() : nullptr, getGameMap())
            << formatTitleOff;
    }
    tempSS << std::endl;
    tempSS << "Path: " << getSkillPathText() << std::endl;
    tempSS << "Skills: " << getSkillListText() << std::endl;
    tempSS << "Experience: " << mExp << std::endl;
    tempSS << "HP: " << getHP() << " / " << mMaxHP << std::endl;
    tempSS << "Gold: " << mGoldCarried << std::endl;
    for(Room* room : getGameMap()->getRoomsByTypeAndSeat(RoomType::infirmary, getSeat()))
    {
        RoomInfirmary* infirmary = static_cast<RoomInfirmary*>(room);
        const RoomInfirmary::PatientInfo* patient = infirmary->getPatient(*this);
        if(patient != nullptr && patient->creature == this)
        {
            tempSS << "Infirmary: " << formatFixedNumber(getHP() * 100.0 / getMaxHp()) << " % -> "
                << infirmary->getDischargeThreshold() << " %" << std::endl;
            break;
        }
    }
    if (!getDefinition()->isWorker())
    {
        tempSS << "Wakefulness: " << mWakefulness << std::endl;
        tempSS << "Hunger: " << mHunger << std::endl;
        tempSS << "Thirst: " << mThirst << std::endl;
        tempSS << "Drunk: " << mDrunk << std::endl;
        tempSS << "Hangover: " << mHangoverTurns << std::endl;
        tempSS << "Urge: " << mUrge << std::endl;
        tempSS << "Dirt: " << mCreatureDirt << std::endl;
    }
    tempSS << "Move speed (G/W/L): " << getMoveSpeedGround() << " / "
        << getMoveSpeedWater() << " / " << getMoveSpeedLava() << std::endl;
    tempSS << "Weapons:" << std::endl;
    if(mWeaponL == nullptr)
        tempSS << " - Left: none" << std::endl;
    else
        tempSS << " - Left: " << mWeaponL->getName() << " | Damage (P/M/E): " << mWeaponL->getPhysicalDamage()
               << " / " << mWeaponL->getMagicalDamage() << " / " << mWeaponL->getElementDamage() << std::endl;
    if(mWeaponR == nullptr)
        tempSS << " - Right: none" << std::endl;
    else
        tempSS << " - Right: " << mWeaponR->getName() << " | Damage (P/M/E): " << mWeaponR->getPhysicalDamage()
               << " / " << mWeaponR->getMagicalDamage() << " / " << mWeaponR->getElementDamage() << std::endl;
    tempSS << "Defense (P/M/E): " << getPhysicalDefense() << " / " << getMagicalDefense() << " / " << getElementDefense() << std::endl;
    if (getDefinition()->isWorker())
    {
        tempSS << "Dig rate: " << getDigRate() << std::endl;
        tempSS << "Dance rate: " << getClaimRate() << std::endl;
    }

    tempSS << formatTitleOn << "\nDebugging information" << formatTitleOff << std::endl;
    tempSS << "Seat and team IDs: " << getSeat()->getId() << " / " << getSeat()->getTeamId() << std::endl;
    tempSS << "Position: " << Helper::toString(getPosition()) << std::endl;
    tempSS << "Actions:";
    for(const std::unique_ptr<CreatureAction>& ca : mActions)
    {
        tempSS << " " << CreatureAction::toString(ca.get()->getType());
    }
    tempSS << std::endl;   
    // The window has a fixed size, so only the next destinations are listed
    const uint32_t maxDestinations = 4;
    tempSS << "Destinations (" << mWalkQueue.size() << "):";
    uint32_t nbDestinations = 0;
    for(const Ogre::Vector2& dest : mWalkQueue)
    {
        if(nbDestinations >= maxDestinations)
        {
            tempSS << " ...";
            break;
        }
        tempSS << " " << Helper::toString(dest);
        ++nbDestinations;
    }
    tempSS << std::endl;
    tempSS << "Mood: " << CreatureMood::toString(mMoodValue) << std::endl;
    tempSS << "Mood points: " << Helper::toString(mMoodPoints) << std::endl;
    return tempSS.str();
}

double Creature::getPitDamageFactor(GameEntity* attacker)
{
    // Fights between creatures inside an arena only hurt a fraction of normal combat
    if((attacker == nullptr) || (attacker->getObjectType() != GameEntityType::creature))
        return 1.0;

    Tile* tileVictim = getPositionTile();
    Tile* tileAttacker = attacker->getPositionTile();
    if((tileVictim == nullptr) || (tileAttacker == nullptr) ||
       (tileVictim->getCoveringRoom() == nullptr) || (tileAttacker->getCoveringRoom() == nullptr))
        return 1.0;

    if((tileVictim->getCoveringRoom()->getType() != RoomType::arena) ||
       (tileAttacker->getCoveringRoom()->getType() != RoomType::arena))
        return 1.0;

    return ConfigManager::getSingleton().getRoomConfigDouble("ArenaDamageTakenPercent");
}

bool Creature::canHaveRelationships() const
{
    bool optionOnServerMap = getIsOnServerMap() && getGameMap()->isRelationshipsEnabled();
    if(!optionOnServerMap)
        return false;

    Seat* seat = getSeat();
    bool hasSeat = (seat != nullptr);
    return relationshipsAllowed(optionOnServerMap, hasSeat, hasSeat && seat->isRogueSeat(),
        hasSeat && (seat->getFaction() == "Hero"), getDefinition()->isWorker(), isInPrison());
}

double Creature::getRelationshipCombatModifier() const
{
    if(!canHaveRelationships())
        return 0.0;

    GameMap* gameMap = getGameMap();
    int64_t turn = gameMap->getTurnNumber();
    if(mCombatModifierTurn == turn)
        return mCombatModifier;

    mCombatModifierTurn = turn;
    mCombatModifier = 0.0;
    // Only creatures that fight get a bonus or a penalty
    Tile* myTile = getPositionTile();
    if((myTile == nullptr) || !isAlive() || !isActionInList(CreatureActionType::fight))
        return 0.0;

    CreatureRelationships* relationships = gameMap->getCreatureRelationships();
    double radius = relationships->getSettings().mCombatRadiusTiles;
    std::vector<std::pair<std::string, int32_t> > partners;
    relationships->getPartners(getName(), partners);
    std::vector<std::string> nearbyFighters;
    for(size_t i = 0; i < partners.size(); ++i)
    {
        Creature* partner = gameMap->getCreature(partners[i].first);
        if((partner == nullptr) || (partner->getSeat() != getSeat()) || !partner->isAlive() || partner->isKo()
           || !partner->getIsOnMap() || !partner->isActionInList(CreatureActionType::fight))
        {
            continue;
        }

        Tile* partnerTile = partner->getPositionTile();
        if(partnerTile == nullptr)
            continue;

        double dx = static_cast<double>(partnerTile->getX() - myTile->getX());
        double dy = static_cast<double>(partnerTile->getY() - myTile->getY());
        if((dx * dx + dy * dy) > (radius * radius))
            continue;

        nearbyFighters.push_back(partner->getName());
    }

    mCombatModifier = relationships->combatModifier(getName(), nearbyFighters);
    return mCombatModifier;
}

int32_t Creature::getRelationshipMood() const
{
    if(!canHaveRelationships())
        return 0;

    return getGameMap()->getCreatureRelationships()->moodModifier(getName()) + mRelationshipTempMood;
}

void Creature::addRelationshipMood(int32_t points)
{
    if(!canHaveRelationships() || (points == 0))
        return;

    int32_t maxMood = getGameMap()->getCreatureRelationships()->getSettings().mTempMoodMax;
    mRelationshipTempMood = std::max(-maxMood, std::min(maxMood, mRelationshipTempMood + points));
    // The mood is computed again soon
    mMoodCooldownTurns = 0;
}

void Creature::reportDeathToFriends(GameEntity* killer)
{
    if(!canHaveRelationships())
        return;

    GameMap* gameMap = getGameMap();
    CreatureRelationships* relationships = gameMap->getCreatureRelationships();
    const RelationshipSettings& settings = relationships->getSettings();
    int64_t turn = gameMap->getTurnNumber();
    std::vector<std::string> friends;
    relationships->getFriends(getName(), friends);
    for(size_t i = 0; i < friends.size(); ++i)
    {
        Creature* mourner = gameMap->getCreature(friends[i]);
        if((mourner == nullptr) || (mourner == this) || (mourner->getSeat() != getSeat()) || !mourner->isAlive()
           || !mourner->canHaveRelationships())
        {
            continue;
        }

        // The partner grieves more than a friend
        int32_t penalty = relationships->isLovers(getName(), mourner->getName()) ?
            settings.mPartnerGriefMoodPenalty : settings.mGriefMoodPenalty;
        mourner->addRelationshipMood(-penalty);
        if((killer != nullptr) && (killer->getSeat() != nullptr) && (killer->getSeat() != getSeat()))
        {
            mourner->mRageUntilTurn = turn + settings.mGriefRageTurns;
            mourner->mRageSeatId = killer->getSeat()->getId();
        }
    }
}

bool Creature::hasFriendDoing(CreatureActionType action, double maxTiles, bool useHomeTile) const
{
    Tile* myTile = useHomeTile ? getHomeTile() : getPositionTile();
    if(myTile == nullptr)
        return false;

    std::vector<std::string> friends;
    getGameMap()->getCreatureRelationships()->getFriends(getName(), friends);
    for(size_t i = 0; i < friends.size(); ++i)
    {
        Creature* friendCreature = getGameMap()->getCreature(friends[i]);
        if((friendCreature == nullptr) || (friendCreature->getSeat() != getSeat()) || !friendCreature->isAlive()
           || friendCreature->isKo() || !friendCreature->getIsOnMap() || !friendCreature->canHaveRelationships()
           || !friendCreature->isActionInList(action))
        {
            continue;
        }

        Tile* friendTile = useHomeTile ? friendCreature->getHomeTile() : friendCreature->getPositionTile();
        // A sleeping friend lies in its bed
        if((friendTile == nullptr) || (useHomeTile && (friendCreature->getPositionTile() != friendTile)))
            continue;

        double dx = static_cast<double>(friendTile->getX() - myTile->getX());
        double dy = static_cast<double>(friendTile->getY() - myTile->getY());
        if((dx * dx + dy * dy) <= (maxTiles * maxTiles))
            return true;
    }

    return false;
}

void Creature::reportSlapToFriends()
{
    if(!canHaveRelationships())
        return;

    CreatureRelationships* relationships = getGameMap()->getCreatureRelationships();
    int32_t penalty = relationships->getSettings().mSlapFriendsMoodPenalty;
    // Only the friends that can see the slapped creature care
    std::vector<GameEntity*> seers = getGameMap()->getVisibleCreatures(getVisibleTiles(), getSeat(), false);
    for(GameEntity* seer : seers)
    {
        if((seer == this) || (seer->getObjectType() != GameEntityType::creature))
            continue;

        Creature* friendCreature = static_cast<Creature*>(seer);
        if((friendCreature->getSeat() == getSeat()) && friendCreature->isAlive()
           && relationships->isFriend(getName(), friendCreature->getName()))
        {
            friendCreature->addRelationshipMood(-penalty);
        }
    }
}

void Creature::reportSleepingNextToFriends()
{
    if(!canHaveRelationships())
        return;

    const RelationshipSettings& settings = getGameMap()->getCreatureRelationships()->getSettings();
    if(hasFriendDoing(CreatureActionType::sleep, static_cast<double>(settings.mNeighbourBedTiles), true))
        addRelationshipMood(settings.mSleepNextToFriendMood);
}

void Creature::reportEatingWithFriends()
{
    if(!canHaveRelationships())
        return;

    const RelationshipSettings& settings = getGameMap()->getCreatureRelationships()->getSettings();
    if(hasFriendDoing(CreatureActionType::eatChicken, static_cast<double>(settings.mEatTogetherTiles), false))
        addRelationshipMood(settings.mEatTogetherMood);
}

void Creature::reportLeavingToBestFriend()
{
    if(!canHaveRelationships())
        return;

    CreatureRelationships* relationships = getGameMap()->getCreatureRelationships();
    // The partner comes first, then the best friend
    std::string bestFriend = relationships->getPartner(getName());
    bool isPartner = !bestFriend.empty();
    if(!isPartner)
        bestFriend = relationships->getBestFriend(getName());
    if(bestFriend.empty())
        return;

    Creature* friendCreature = getGameMap()->getCreature(bestFriend);
    if((friendCreature == nullptr) || (friendCreature->getSeat() != getSeat()) || !friendCreature->isAlive()
       || friendCreature->isKo() || !friendCreature->getIsOnMap() || friendCreature->isPossessed()
       || !friendCreature->canHaveRelationships()
       || friendCreature->isActionInList(CreatureActionType::leaveDungeon))
    {
        return;
    }

    int32_t chance = isPartner ? relationships->getSettings().mLeavePartnerChancePercent :
        relationships->getSettings().mLeaveTogetherChancePercent;
    // The chance is in percent: a roll from 0 to 99 below it succeeds
    const int32_t maxPercentRoll = 99;
    if(Random::Int(0, maxPercentRoll) >= chance)
        return;

    OD_LOG_INF("creature=" + friendCreature->getName() + " leaves its dungeon together with its " +
        (isPartner ? "partner " : "best friend ") + getName());
    friendCreature->leaveDungeon();
}

double Creature::getRelationshipRageFactor(const Seat* victimSeat) const
{
    if((mRageUntilTurn <= 0) || (victimSeat == nullptr) || (victimSeat->getId() != mRageSeatId)
       || !canHaveRelationships())
    {
        return 1.0;
    }

    if(getGameMap()->getTurnNumber() >= mRageUntilTurn)
        return 1.0;

    return 1.0 + static_cast<double>(getGameMap()->getCreatureRelationships()->getSettings().mGriefRageBonusPercent) / 100.0;
}

bool Creature::canStartBrawl() const
{
    if(!canHaveRelationships())
        return false;

    BrawlCandidateState state;
    state.mAllowed = true;
    state.mOnMap = getIsOnMap();
    state.mAlive = isAlive();
    state.mKo = isKo();
    state.mPossessed = isPossessed();
    state.mBrawling = isBrawling();
    state.mHasTile = (getPositionTile() != nullptr);
    state.mFighting = isActionInList(CreatureActionType::fight) || isActionInList(CreatureActionType::fightFriendly);
    Room* room = state.mHasTile ? getPositionTile()->getCoveringRoom() : nullptr;
    state.mInArenaOrCasino = (room != nullptr) && ((room->getType() == RoomType::arena) || (room->getType() == RoomType::casino));
    state.mHp = getHP();
    state.mMaxHp = mMaxHP;
    return ::canStartBrawl(state, getGameMap()->getCreatureRelationships()->getSettings());
}

void Creature::startBrawl(Creature& opponent)
{
    if(!canStartBrawl() || !opponent.canStartBrawl())
        return;

    int64_t turn = getGameMap()->getTurnNumber();
    mBrawlOpponent = opponent.getName();
    mBrawlStartTurn = turn;
    opponent.mBrawlOpponent = getName();
    opponent.mBrawlStartTurn = turn;

    // Both fight to knock the other one out, the fight never kills
    Creature* creatures[2] = {this, &opponent};
    Creature* targets[2] = {&opponent, this};
    for(int i = 0; i < 2; ++i)
    {
        creatures[i]->clearDestinations(EntityAnimation::idle_anim, true, true);
        creatures[i]->clearActionQueue();
        creatures[i]->pushAction(Utils::make_unique<CreatureActionFightFriendly>(*creatures[i], targets[i], true,
            std::vector<Tile*>(), false));
    }
}

void Creature::updateBrawl()
{
    if(mBrawlOpponent.empty())
        return;

    Creature* opponent = getGameMap()->getCreature(mBrawlOpponent);
    CreatureRelationships* relationships = getGameMap()->getCreatureRelationships();
    if((opponent == nullptr) || (relationships == nullptr) || (opponent->mBrawlOpponent != getName()))
    {
        // The opponent is gone (or has already stopped): nothing to end for it
        mBrawlOpponent.clear();
        return;
    }

    BrawlFighterState own;
    own.mAlive = isAlive();
    own.mKo = isKo();
    own.mPossessed = isPossessed();
    own.mHp = getHP();
    own.mMaxHp = mMaxHP;
    BrawlFighterState other;
    other.mAlive = opponent->isAlive();
    other.mKo = opponent->isKo();
    other.mPossessed = opponent->isPossessed();
    other.mHp = opponent->getHP();
    other.mMaxHp = opponent->mMaxHP;
    if(shouldStopBrawl(own, other, getGameMap()->getTurnNumber() - mBrawlStartTurn,
        isActionInList(CreatureActionType::fightFriendly), relationships->getSettings()))
    {
        endBrawl();
    }
}

void Creature::endBrawl()
{
    if(mBrawlOpponent.empty())
        return;

    std::string opponentName = mBrawlOpponent;
    mBrawlOpponent.clear();
    Creature* opponent = getGameMap()->getCreature(opponentName);
    CreatureRelationships* relationships = getGameMap()->getCreatureRelationships();

    Creature* creatures[2] = {this, nullptr};
    if((opponent != nullptr) && (opponent->mBrawlOpponent == getName()))
    {
        opponent->mBrawlOpponent.clear();
        creatures[1] = opponent;
    }

    for(int i = 0; i < 2; ++i)
    {
        Creature* creature = creatures[i];
        if((creature == nullptr) || !creature->isAlive())
            continue;

        // The fight stops (unless the creature already got something else to do), both stay angry
        if(creature->isActionInList(CreatureActionType::fightFriendly))
        {
            creature->clearDestinations(EntityAnimation::idle_anim, true, true);
            creature->clearActionQueue();
        }
        creature->makeUnhappy();
    }

    if(relationships != nullptr)
    {
        relationships->changeValue(getName(), opponentName, relationships->getSettings().mBrawlValueChange,
            getGameMap()->getTurnNumber());
    }
}

bool Creature::getRelationshipState(RelationshipCreatureState& state) const
{
    state = RelationshipCreatureState();
    if(!getIsOnServerMap() || !getGameMap()->isRelationshipsEnabled())
        return false;

    GameMap* gameMap = getGameMap();
    int64_t turn = gameMap->getTurnNumber();
    state.mName = getName();
    // The captors belong to creatures that are held prisoner, which cannot have relationships
    state.mCaptors = mCaptors;
    if(!canHaveRelationships())
        return !state.isEmpty();

    state.mGriefMood = mRelationshipTempMood;
    if(mRageUntilTurn > turn)
    {
        state.mRageTurnsLeft = mRageUntilTurn - turn;
        state.mRageSeatId = mRageSeatId;
    }

    if(!mBrawlOpponent.empty())
    {
        int64_t maxTurns = gameMap->getCreatureRelationships()->getSettings().mBrawlMaxTurns;
        state.mBrawlOpponent = mBrawlOpponent;
        state.mBrawlTurnsLeft = std::max<int64_t>(1, maxTurns - (turn - mBrawlStartTurn));
    }
    else if(!mBrawlResumeOpponent.empty())
    {
        // Saved again before the restored brawl could start
        state.mBrawlOpponent = mBrawlResumeOpponent;
        state.mBrawlTurnsLeft = std::max<int64_t>(1, mBrawlResumeTurnsLeft);
    }

    return !state.isEmpty();
}

void Creature::setRelationshipState(const RelationshipCreatureState& state)
{
    if(!getIsOnServerMap() || !getGameMap()->isRelationshipsEnabled())
        return;

    GameMap* gameMap = getGameMap();
    // Captors that are not around any more are ignored
    mCaptors.clear();
    for(size_t i = 0; i < state.mCaptors.size() && (mCaptors.size() < RelationshipCreatureState::MAX_CAPTORS); ++i)
    {
        if(gameMap->getCreature(state.mCaptors[i]) != nullptr)
            mCaptors.push_back(state.mCaptors[i]);
    }

    if(!canHaveRelationships())
        return;

    const RelationshipSettings& settings = gameMap->getCreatureRelationships()->getSettings();
    int64_t turn = gameMap->getTurnNumber();
    mRelationshipTempMood = std::max(-settings.mTempMoodMax, std::min(settings.mTempMoodMax, state.mGriefMood));
    if((state.mRageTurnsLeft > 0) && (state.mRageSeatId >= 0))
    {
        mRageUntilTurn = turn + state.mRageTurnsLeft;
        mRageSeatId = state.mRageSeatId;
    }

    // The fight itself is not saved: the brawl starts again once both creatures are able to fight
    if(!state.mBrawlOpponent.empty() && (state.mBrawlTurnsLeft > 0) && (state.mBrawlOpponent != getName()))
    {
        static const int64_t RESUME_WAIT_TURNS = 100;
        mBrawlResumeOpponent = state.mBrawlOpponent;
        mBrawlResumeTurnsLeft = std::min(state.mBrawlTurnsLeft, settings.mBrawlMaxTurns);
        mBrawlResumeGiveUpTurn = turn + RESUME_WAIT_TURNS;
    }
}

void Creature::resumeBrawl()
{
    if(mBrawlResumeOpponent.empty())
        return;

    GameMap* gameMap = getGameMap();
    int64_t turn = gameMap->getTurnNumber();
    Creature* opponent = gameMap->getCreature(mBrawlResumeOpponent);
    bool valid = (opponent != nullptr) && (opponent->mBrawlResumeOpponent == getName()) && canHaveRelationships()
        && opponent->canHaveRelationships() && (turn < mBrawlResumeGiveUpTurn);
    if(!valid)
    {
        // The opponent is gone, was not restored as well, or the creatures did not get ready in time
        mBrawlResumeOpponent.clear();
        return;
    }

    // Only one of the two starts the brawl
    if(getName() > opponent->getName())
        return;

    if(!canStartBrawl() || !opponent->canStartBrawl())
        return;

    int64_t turnsLeft = std::min(mBrawlResumeTurnsLeft, opponent->mBrawlResumeTurnsLeft);
    mBrawlResumeOpponent.clear();
    opponent->mBrawlResumeOpponent.clear();
    startBrawl(*opponent);
    if(isBrawling())
    {
        int64_t maxTurns = gameMap->getCreatureRelationships()->getSettings().mBrawlMaxTurns;
        mBrawlStartTurn = turn - std::max<int64_t>(0, maxTurns - turnsLeft);
        opponent->mBrawlStartTurn = mBrawlStartTurn;
    }
}

void Creature::reportRelationshipEvent(RelationshipEvent event, Creature& creatureA, Creature& creatureB)
{
    if(!relationshipEventAllowed(creatureA.canHaveRelationships(), creatureB.canHaveRelationships(),
        creatureA.getSeat() == creatureB.getSeat()))
    {
        return;
    }

    GameMap* gameMap = creatureA.getGameMap();
    gameMap->getCreatureRelationships()->onRelationshipEvent(event, creatureA.getName(), creatureB.getName(),
        gameMap->getTurnNumber(), creatureA.getDefinition()->getClassName(), creatureB.getDefinition()->getClassName());
}

void Creature::startConvertedRelationships()
{
    std::vector<std::string> captors;
    captors.swap(mCaptors);
    // The prison seat of the converted creature is only cleared later, so canHaveRelationships() cannot be used
    if(!getIsOnServerMap() || !getGameMap()->isRelationshipsEnabled() || (getSeat() == nullptr)
       || getSeat()->isRogueSeat() || getDefinition()->isWorker())
        return;

    GameMap* gameMap = getGameMap();
    std::vector<std::string> sameKeeper;
    for(size_t i = 0; i < captors.size(); ++i)
    {
        Creature* captor = gameMap->getCreature(captors[i]);
        if((captor != nullptr) && (captor->getSeat() == getSeat()) && captor->canHaveRelationships())
            sameKeeper.push_back(captors[i]);
    }
    gameMap->getCreatureRelationships()->startConverted(getName(), sameKeeper, gameMap->getTurnNumber());
}

void Creature::reportFightParticipants(Creature& killer)
{
    if(getDefinition()->isWorker() || !killer.canHaveRelationships() || (killer.getSeat() == getSeat()) || killer.getSeat()->isAlliedSeat(getSeat()))
        return;

    static const size_t MAX_PARTICIPANTS = 8;
    int64_t turn = getGameMap()->getTurnNumber();
    int64_t window = getGameMap()->getCreatureRelationships()->getSettings().mFightParticipantTurns;
    std::vector<Creature*> participants;
    participants.push_back(&killer);
    for(std::map<std::string, int64_t>::const_iterator it = mRecentAttackers.begin(); it != mRecentAttackers.end(); ++it)
    {
        if(participants.size() >= MAX_PARTICIPANTS)
            break;

        if((turn - it->second) > window)
            continue;

        Creature* participant = getGameMap()->getCreature(it->first);
        if((participant == nullptr) || (participant == &killer) || !participant->isAlive()
           || (participant->getSeat() != killer.getSeat()) || !participant->canHaveRelationships())
        {
            continue;
        }

        participants.push_back(participant);
    }
    mRecentAttackers.clear();

    for(size_t i = 0; i < participants.size(); ++i)
    {
        for(size_t j = i + 1; j < participants.size(); ++j)
            reportRelationshipEvent(RelationshipEvent::defeatedEnemiesTogether, *participants[i], *participants[j]);
    }
}

namespace
{
//! \brief Counts script events and records an observed spawn's actual temple tile when it is killed (server only).
void recordScriptEvent(const Creature& creature, const std::string& eventName)
{
    if(!creature.getIsOnServerMap())
        return;

    creature.getGameMap()->getLevelScript().recordEvent(creature.getName(), eventName);
    if(eventName == "killed")
    {
        creature.getGameMap()->getLevelScript().completeShotKill(creature.getName());
        int32_t templeSeat = -1;
        Tile* tile = creature.getPositionTile();
        if(tile != nullptr)
        {
            creature.getGameMap()->getLevelScript().observeCreatureDeath(creature.getName(), tile->getX(), tile->getY());
            Room* room = tile->getCoveringRoom();
            if(room != nullptr && room->getType() == RoomType::dungeonTemple && room->getSeat() != nullptr)
                templeSeat = room->getSeat()->getId();
        }
        creature.getGameMap()->getLevelScript().observeSpawnDeath(creature.getName(), templeSeat);
    }
}
} // namespace

//! \brief Tells whether damage comes from a blow (the attacker is a creature) or a shot (the attacker is a missile).
//! Traps, spells, rooms, burning and lava have no attacker of these kinds and leave no combat dirt.
//! \param attacker The entity that deals the damage, can be null.
static bool isHitByBlowOrShot(const GameEntity* attacker)
{
    if(attacker == nullptr)
        return false;

    return (attacker->getObjectType() == GameEntityType::creature) ||
           (attacker->getObjectType() == GameEntityType::missileObject);
}

//! \brief Adds the dirt of one landed blow or shot to a tile: ArenaDirtPerHit on an arena tile (so that a fight there
//! is not counted twice), CombatDirtPerHit anywhere else. The DirtFactor of the creatures is not used.
//! \param tile The tile the target stands on, can be null.
static void addHitDirt(Tile* tile)
{
    if(tile == nullptr)
        return;

    Room* room = tile->getCoveringRoom();
    if((room != nullptr) && (room->getType() == RoomType::arena))
        tile->addDirt(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("ArenaDirtPerHit", 0.0));
    else
        tile->addDirt(ConfigManager::getSingleton().getDirtConfigDouble("CombatDirtPerHit"));
}

double Creature::takeDamage(GameEntity* attacker, double absoluteDamage, double physicalDamage, double magicalDamage, double elementDamage,
        Tile *tileTakingDamage, bool ko)
{
    bool wasAlive = isAlive();
    bool wasKo = isKo();
    mNbTurnsWithoutBattle = 0;
    mFoughtSinceFightEnd = true;
    // The champion cannot be hurt
    if(getDefinition()->isChampion())
        return 0.0;

    // Remember who hurt us, to know who took part in the fight if we are defeated
    Creature* creatureAttacking = nullptr;
    if((attacker != nullptr) && (attacker->getObjectType() == GameEntityType::creature))
        creatureAttacking = static_cast<Creature*>(attacker);
    if((creatureAttacking != nullptr) && getIsOnServerMap() && getGameMap()->isRelationshipsEnabled()
       && (creatureAttacking != this) && creatureAttacking->canHaveRelationships())
    {
        int64_t turn = getGameMap()->getTurnNumber();
        int64_t window = getGameMap()->getCreatureRelationships()->getSettings().mFightParticipantTurns;
        std::map<std::string, int64_t>::iterator itAttacker = mRecentAttackers.begin();
        while(itAttacker != mRecentAttackers.end())
        {
            if((turn - itAttacker->second) > window)
                itAttacker = mRecentAttackers.erase(itAttacker);
            else
                ++itAttacker;
        }
        mRecentAttackers[creatureAttacking->getName()] = turn;
    }
    physicalDamage = std::max(physicalDamage - getPhysicalDefense(), 0.0);
    magicalDamage = std::max(magicalDamage - getMagicalDefense(), 0.0);
    elementDamage = std::max(elementDamage - getElementDefense(), 0.0);
    double totalDamage = (absoluteDamage + physicalDamage + magicalDamage + elementDamage) * getPitDamageFactor(attacker);
    // A creature that grieves for a friend hits harder against the side that killed it
    if(creatureAttacking != nullptr)
        totalDamage *= creatureAttacking->getRelationshipRageFactor(getSeat());
    double damageDone = std::min(mHp, totalDamage);
    mHp -= damageDone;
    if(getIsOnServerMap() && damageDone > 0.0)
        ItemEffects::onDamageDealt(attacker, *this, damageDone);
    // A blow or shot that lands dirties the floor where its target stands
    if(wasAlive && (damageDone > 0.0) && getIsOnServerMap() && isHitByBlowOrShot(attacker))
    {
        Tile* hitTile = (tileTakingDamage != nullptr) ? tileTakingDamage : getPositionTile();
        addHitDirt(hitTile);
    }
    if(wasAlive && (damageDone > 0.0))
    {
        recordScriptEvent(*this, "attacked");
        MissileObject* shot = attacker != nullptr && attacker->getObjectType() == GameEntityType::missileObject ?
            static_cast<MissileObject*>(attacker) : nullptr;
        Seat* attackingSeat = creatureAttacking != nullptr ? creatureAttacking->getSeat() : nullptr;
        if(attacker != nullptr && attacker->getObjectType() == GameEntityType::missileObject &&
           static_cast<MissileObject*>(attacker)->isCreatureShot())
            attackingSeat = attacker->getSeat();
        if(getIsOnServerMap() && attackingSeat != nullptr && getSeat() != nullptr && getPositionTile() != nullptr &&
           !attackingSeat->isAlliedSeat(getSeat()))
            getGameMap()->getLevelScript().observeRegionAttack(attackingSeat->getId(),
                getSeat()->getId(), getPositionTile()->getX(), getPositionTile()->getY());
        if(getIsOnServerMap() && getGameMap()->getLevelScript().hasShotObservers())
        {
            LevelScript& script = getGameMap()->getLevelScript();
            const bool ownShot = shot != nullptr && shot->isCreatureShot() && attackingSeat != nullptr &&
                getSeat() != nullptr && !attackingSeat->isAlliedSeat(getSeat());
            if(mHp <= 0)
                script.observeFatalShot(getName(), ownShot ? attackingSeat->getId() : -1);
            if(ownShot && shot->isPossessedShot())
                script.recordEvent("Seat" + std::to_string(attackingSeat->getId()), "possessedshot");
        }
    }

    if(mHp <= 0)
    {
        interruptGhostHunt();
        // A possessed creature is not knocked out, it dies and the keeper loses mana
        if(isPossessed())
        {
            if(wasAlive && (getSeat() != nullptr))
            {
                double manaLoss = ConfigManager::getSingleton().getSpellConfigDouble("PossessDeathManaLoss");
                getSeat()->addMana(-manaLoss);
            }
        }
        // If the attacking entity is a creature and its seat is configured to KO creatures
        // instead of killing, we KO
        else if(ko && !getDefinition()->isWorker())
        {
            mHp = 1.0;
            recordScriptEvent(*this, "incapacitated");
            mKoTurnCounter = -ConfigManager::getSingleton().getNbTurnsKoCreatureAttacked() *
                ItemEffects::remainingFactor(*this, "QuickRise");
            OD_LOG_INF("creature=" + getName() + " has been KO by " + attacker->getName());
            dropItems(false);
            dropCarriedEquipment();

            // Enemies that knock this creature out are remembered in case it is converted later
            static const size_t MAX_CAPTORS = 8;
            if((creatureAttacking != nullptr) && (creatureAttacking->getSeat() != getSeat()) && (mCaptors.size() < MAX_CAPTORS)
               && getIsOnServerMap() && getGameMap()->isRelationshipsEnabled() && creatureAttacking->canHaveRelationships()
               && (std::find(mCaptors.begin(), mCaptors.end(), creatureAttacking->getName()) == mCaptors.end()))
            {
                mCaptors.push_back(creatureAttacking->getName());
            }

            // The loser of a fight in the arena gets a worse relationship with the winner
            if(!wasKo && (creatureAttacking != nullptr) && (getPositionTile() != nullptr)
               && (creatureAttacking->getPositionTile() != nullptr)
               && (getPositionTile()->getCoveringRoom() != nullptr)
               && (creatureAttacking->getPositionTile()->getCoveringRoom() != nullptr)
               && (getPositionTile()->getCoveringRoom()->getType() == RoomType::arena)
               && (creatureAttacking->getPositionTile()->getCoveringRoom()->getType() == RoomType::arena))
            {
                reportRelationshipEvent(RelationshipEvent::arenaLoss, *this, *creatureAttacking);
            }
        }
    }

    // Being knocked out dirties the creature at once; the end of this fight then adds nothing
    if(!wasKo && getIsOnServerMap() && (isKoTemp() || isKoDeath()))
    {
        increaseCreatureDirt(ConfigManager::getSingleton().getDirtConfigDouble("CreatureDirtPerKo"));
        mDirtKoThisFight = true;
    }

    computeCreatureOverlayHealthValue();
    computeCreatureOverlayMoodValue();

    if(!isAlive())
    {
        // The killing blow counts once for the debriefing (a KO does not get here)
        if(wasAlive && (attacker != nullptr) && (attacker->getSeat() != nullptr))
            attacker->getSeat()->recordCreatureKill(getSeat());
        if(wasAlive && (getSeat() != nullptr))
            ++getSeat()->getStatistics().mCreaturesLost;
        if(wasAlive && (creatureAttacking != nullptr) && getIsOnServerMap() && getGameMap()->isRelationshipsEnabled())
            reportFightParticipants(*creatureAttacking);
        if(wasAlive && getIsOnServerMap() && getGameMap()->isRelationshipsEnabled())
            reportDeathToFriends(attacker);

        if(wasAlive)
        {
            recordScriptEvent(*this, "killed");
            recordScriptEvent(*this, "incapacitated");
        }
        fireEntityDead();
    }

    if(!getIsOnServerMap())
        return damageDone;

    Player* player = getGameMap()->getPlayerBySeat(getSeat());
    if (player == nullptr)
        return damageDone;

    // If we are a worker attacked by a worker, we fight. Otherwise, we flee (if it is a fighter, a trap,
    // or whatever)
    if(!getDefinition()->isWorker())
        return damageDone;

    bool shouldFlee = true;
    if((attacker != nullptr) &&
       (attacker->getObjectType() == GameEntityType::creature))
    {
        Creature* creatureAttacking = static_cast<Creature*>(attacker);
        if(creatureAttacking->getDefinition()->isWorker())
        {
            // We do not flee because of this attack
            shouldFlee = false;
        }
    }

    if(shouldFlee)
    {
        flee();
        return damageDone;
    }
    return damageDone;
}

//! \brief Adds earned experience with the worn Trainer bonus.
void Creature::receiveExp(double experience)
{
    if (!std::isfinite(experience) || experience < 0 || mLevel >= MAX_LEVEL)
        return;

    mExp += experience * (1.0 + getItemEffect("Trainer") / 100.0);
    mNeedFireRefresh = true;
}

namespace
{
//! \brief Tells whether the cooldown of the skill shrinks with the creature level: the melee attack and the
//! ranged attacks (missile, guided bolt, grenade). Support skills and other spells keep their cooldown.
bool isLevelScaledAttack(const CreatureSkill& skill)
{
    if(dynamic_cast<const CreatureSkillMeleeFight*>(&skill) != nullptr)
        return true;

    const std::string& name = skill.getSkillName();
    return (name == "MissileLaunch") || (name == "GuidedBolt") || (name == "Grenade");
}
}

//! \brief Gets the larger skill or weapon cooldown for melee, with level scaling for attacks. The cd% passives
//! shorten the cooldown of the attack lines.
double Creature::getAppliedCooldownNbTurns(const CreatureSkill& skill) const
{
    uint32_t baseCooldown = skill.getCooldownNbTurns();
    if(dynamic_cast<const CreatureSkillMeleeFight*>(&skill) != nullptr)
    {
        // Melee recovery keeps the larger skill or held-weapon cooldown.
        const Weapon* weapons[2] = {mWeaponL, mWeaponR};
        uint32_t weaponCooldown = 0;
        for(const Weapon* weapon : weapons)
        {
            if(weapon == nullptr)
                continue;

            weaponCooldown = std::max(weaponCooldown, weapon->getCooldownNbTurns());
        }

        if(weaponCooldown != 0)
            baseCooldown = std::max(baseCooldown, weaponCooldown);
    }

    if(!isLevelScaledAttack(skill))
        return baseCooldown;

    // The cd% passives shorten the cooldown of the attack lines, to at least one turn
    double cooldown = CreatureProgression::cooldownAtLevel(baseCooldown, getLevel());
    const double cooldownPassive = getSkillPassive("cd%");
    if(cooldownPassive > 0.0 && cooldown > 0.0)
        cooldown = std::max(1.0, cooldown * (1.0 - cooldownPassive / 100.0));
    return cooldown;
}

void Creature::useAttack(CreatureSkillData& skillData, GameEntity& entityAttack,
        Tile& tileAttack, bool ko, bool notifyPlayerIfHit)
{
    // Keep ranged skills visually distinct, including shots at adjacent targets.
    const Ogre::Vector3& pos = getPosition();
    const Ogre::Vector3 target = entityAttack.getObjectType() == GameEntityType::creature ?
        entityAttack.getPosition() : Ogre::Vector3(tileAttack.getX(), tileAttack.getY(), 0);
    Ogre::Vector3 walkDirection(target.x - pos.x, target.y - pos.y, 0);
    walkDirection.normalise();
    fireAttackTurn(entityAttack.getName(), walkDirection);
    const bool ranged = skillData.mSkill->getRangeMax(this, &entityAttack) > 1.0;
    setAnimationState(ranged ? EntityAnimation::ranged_attack_anim :
        EntityAnimation::combat_attack_anim, false, walkDirection, true);
    fireCreatureSound(CreatureSound::Attack);
    setNbTurnsWithoutBattle(0);
    mFoughtSinceFightEnd = true;

    // Calculate how much damage we do.
    Tile* myTile = getPositionTile();
    float range = Pathfinding::distanceTile(*myTile, tileAttack);

    // The mana is paid when the shot or skill starts
    payManaFor(*skillData.mSkill);

    // We use the skill
    skillData.mSkill->tryUseFight(*getGameMap(), this, range,
        &entityAttack, &tileAttack, ko, notifyPlayerIfHit);
    // The new timers are added, so the remainder of the last turn carries over (fractions are kept)
    skillData.mWarmup += skillData.mSkill->getWarmupNbTurns();
    skillData.mCooldown += getAppliedCooldownNbTurns(*skillData.mSkill);

    // Both timers count down together; either can postpone the next attack.
    mAttackRecoveryDuration = std::max(static_cast<double>(skillData.mWarmup), skillData.mCooldown);
    mAttackRecoveryTurns = mAttackRecoveryDuration;
    ++mAttackRecoverySerial;
    mNeedFireRefresh = true;

    // Fighting is tiring
    decreaseWakefulness(0.5);
    // but gives experience; a dirty arena teaches less, and so does a hangover, while a relaxed creature learns more
    Room* attackRoom = (myTile == nullptr) ? nullptr : myTile->getCoveringRoom();
    if((attackRoom != nullptr) && (attackRoom->getType() == RoomType::arena))
        receiveExp(1.5 * attackRoom->getDirtOutputFactor() * getHangoverWorkFactor() * getRelaxWorkFactor());
    else
        receiveExp(1.5);
}

//! \brief Finds an exact queued action, with specialized room work included in ordinary room-use queries.
bool Creature::isActionInList(CreatureActionType action) const
{
    for (const std::unique_ptr<CreatureAction>& ca : mActions)
    {
        if (ca.get()->getType() == action ||
            (action == CreatureActionType::useRoom && CreatureAction::isRoomWorkAction(ca->getType())))
            return true;
    }
    return false;
}

void Creature::clearActionQueue()
{
    interruptGhostHunt();
    mActions.clear();
}

bool Creature::hasActionBeenTried(CreatureActionType actionType) const
{
    if(std::find(mActionTry.begin(), mActionTry.end(), actionType) == mActionTry.end())
        return false;

    return true;
}

void Creature::pushAction(std::unique_ptr<CreatureAction>&& action)
{
    CreatureActionType actionType = action.get()->getType();
    if(std::find(mActionTry.begin(), mActionTry.end(), actionType) == mActionTry.end())
    {
        mActionTry.push_back(actionType);
    }

    // A fight or a flight on top of a toilet use gives the seat back at once
    if((actionType == CreatureActionType::fight) || (actionType == CreatureActionType::fightFriendly) ||
       (actionType == CreatureActionType::flee))
    {
        for(std::unique_ptr<CreatureAction>& lower : mActions)
        {
            if(lower->getType() == CreatureActionType::useToilet)
                static_cast<CreatureActionUseToilet*>(lower.get())->interrupt();
        }
    }

    mActions.emplace_back(std::move(action));
}

void Creature::popAction()
{
    if(mActions.empty())
    {
        OD_LOG_ERR("name=" + getName() + ", trying to pop empty action list");
        return;
    }

    mActions.pop_back();
}

bool Creature::isSandboxHeroFor(const Seat* seat) const
{
    if(!getGameMap()->isSandbox())
        return false;

    if(seat == nullptr)
        return false;

    if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
        return false;

    return SandboxMode::isHeroSeat(getSeat()) && !SandboxMode::isHeroSeat(seat);
}

bool Creature::tryPickup(Seat* seat)
{
    if(!getIsOnMap())
        return false;

    // Cannot pick up dead creatures
    if (!getGameMap()->isInEditorMode() && !isAlive())
        return false;

    if(!getGameMap()->isInEditorMode() && (mSeatPrison == nullptr) && !getSeat()->canOwnedCreatureBePickedUpBy(seat) &&
       !isSandboxHeroFor(seat))
    {
        return false;
    }

    if(!getGameMap()->isInEditorMode() && (mSeatPrison != nullptr) && !mSeatPrison->canOwnedCreatureBePickedUpBy(seat))
        return false;

    // KO creatures cannot be picked up
    if(isKo())
        return false;

    // A creature controlled by a player cannot be picked up
    if(isPossessed())
        return false;

    // The champion cannot be held in the hand
    if(getDefinition()->isChampion())
        return false;

    return true;
}

void Creature::pickup()
{
    interruptGhostHunt();
    if(getIsOnServerMap())
        LevelScriptRunner::dropCarriedStone(*this);

    // Stop the creature walking and set it off the map to prevent the AI from running on it.
    removeEntityFromPositionTile();
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    mActivity = CreatureActivity();

    if(!getIsOnServerMap())
        return;

    if(getHasVisualDebuggingEntities())
        computeVisualDebugEntities();

    mIsInHand = true;
    if(getSeat() != nullptr)
        ++getSeat()->getStatistics().mCreaturesPickedUp;

    recordScriptEvent(*this, "pickedup");

    fireCreatureSound(CreatureSound::Pickup);
}

int32_t Creature::getNbRecentSlaps(int32_t nbTurns) const
{
    int64_t turnNumber = getGameMap()->getTurnNumber();
    int32_t nbSlaps = 0;
    for(int64_t slapTurn : mSlapTurns)
    {
        if(turnNumber - slapTurn <= nbTurns)
            ++nbSlaps;
    }

    return nbSlaps;
}

bool Creature::canGoThroughTile(Tile* tile) const
{
    if(tile == nullptr)
        return false;

    return getMoveSpeed(tile) > 0.0;
}

bool Creature::tryDrop(Seat* seat, Tile* tile)
{
    // check whether the tile is a ground tile ...
    if(tile->isFullTile())
        return false;

    // In editor mode, we allow creatures to be dropped anywhere they can walk
    if(getGameMap()->isInEditorMode() && canGoThroughTile(tile))
        return true;

    // we cannot drop a creature on a tile we don't see
    if(!seat->hasVisionOnTile(tile))
        return false;

    // In the sandbox, the heroes taken from the toolbox can be dropped on any ground the seat sees
    if(isSandboxHeroFor(seat) && canGoThroughTile(tile))
        return true;

    // If it is a worker, he can be dropped on dirt
    if (getDefinition()->isWorker() && (tile->getTileVisual() == TileVisual::dirtGround || tile->getTileVisual() == TileVisual::goldGround))
        return true;


    if((tile != nullptr) &&
       (tile->getCoveringRoom() != nullptr))
    {
        Room* room = tile->getCoveringRoom();
        if(room->getType() == RoomType::arena)
            return room->hasOpenCreatureSpot(this);
    }

    
    // Every creature can be dropped on allied claimed tiles
    if(tile->isClaimedForSeat(seat))
        return true;



    return false;
}

void Creature::drop(const Ogre::Vector3& v)
{
    interruptGhostHunt();
    if(getIsOnServerMap())
        getGameMap()->getLevelScript().clearFatalShot(getName());
    setPosition(v);
    if(!getIsOnServerMap())
    {
        mDropCooldown = 2;
        updateHexenHenMesh();
        return;
    }

    if(getHasVisualDebuggingEntities())
        computeVisualDebugEntities();

    fireCreatureSound(CreatureSound::Drop);

    mIsInHand = false;
    if(getSeat() != nullptr)
        ++getSeat()->getStatistics().mCreaturesDropped;

    // The creature is temporary KO
    mKoTurnCounter = mDefinition->getTurnsStunDropped();
    computeCreatureOverlayMoodValue();

    // Action queue should be empty but it shouldn't hurt
    clearActionQueue();

    // In editor mode, we do not check for forced actions
    if(getGameMap()->isInEditorMode())
        return;

    if(mDefinition->isWorker())
    {
        // If a worker is dropped, he will search in the tile he is and in the 4 neighboor tiles.
        // 1 - If the tile he is in a treasury and he is carrying gold, he should deposit it
        // 2 - if one of the 4 neighboor tiles is marked, he will dig
        // 3 - if there is a carryable entity where it is dropped, it should try to carry it
        // 4 - if the the tile he is in is not claimed and one of the neigbboor tiles is claimed, he will claim
        // 5 - if the the tile he is in is claimed and one of the neigbboor tiles is not claimed, he will claim
        // 6 - If the tile he is in is claimed and one of the neigbboor tiles is a not claimed wall, he will claim
        Tile* position = getPositionTile();
        Seat* seat = getSeat();
        Tile* tileMarkedDig = nullptr;
        Tile* tileMarkedDigPos = nullptr;
        Tile* tileToClaim = nullptr;
        Tile* tileWallNotClaimed = nullptr;
        for (Tile* tile : position->getAllNeighbors())
        {
            if(tileMarkedDig == nullptr &&
                tile->getMarkedForDigging(getGameMap()->getPlayerBySeat(seat))
                )
            {
                // Check if there is room for digging
                std::vector<Tile*> tiles;
                tile->canWorkerDig(*this, tiles);
                // We search for the closest neighbor tile (may be not the position
                // tile if the player drops several workers at the same tile)
                float distBest = -1;
                for (Tile* neigh : tiles)
                {
                    float dist = Pathfinding::squaredDistanceTile(*position, *neigh);
                    if((distBest != -1) && (distBest <= dist))
                        continue;

                    distBest = dist;
                    tileMarkedDig = tile;
                    tileMarkedDigPos = neigh;
                }
            }
            else if(tileToClaim == nullptr &&
                tile->isClaimedForSeat(seat) &&
                position->isGroundClaimable(seat)
                )
            {
                tileToClaim = position;
            }
            else if(tileToClaim == nullptr &&
                position->isClaimedForSeat(seat) &&
                tile->isGroundClaimable(seat)
                )
            {
                tileToClaim = tile;
            }
            else if(tileWallNotClaimed == nullptr &&
                position->isClaimedForSeat(seat) &&
                tile->isWallClaimable(seat)
                )
            {
                tileWallNotClaimed = tile;
            }
        }

        // We try to deposit gold if we are on a room while carrying gold
        if((mGoldCarried > 0) && (mDigRate > 0.0) &&
           (position->getCoveringRoom() != nullptr))
        {
            double deposited = position->getCoveringRoom()->depositGold(mGoldCarried, position);
            if(deposited > 0)
            {
                mGoldCarried -= deposited;
                return;
            }
        }

        std::vector<GameEntity*> carryable;
        position->fillWithCarryableEntities(this, carryable);

        // Now, we can decide
        if((tileMarkedDig != nullptr) && (tileMarkedDigPos != nullptr) && (mDigRate > 0.0))
        {
            pushAction(Utils::make_unique<CreatureActionSearchTileToDig>(*this, true));
            pushAction(Utils::make_unique<CreatureActionDigTile>(*this, *tileMarkedDig, *tileMarkedDigPos));
            return;
        }

        if(!carryable.empty())
        {
            // We look for the most important entity to carry
            GameEntity* entityToCarry = carryable[0];
            for(GameEntity* entity : carryable)
            {
                if(entity->getEntityCarryType(this) <= entityToCarry->getEntityCarryType(this))
                    continue;

                entityToCarry = entity;
            }

            pushAction(Utils::make_unique<CreatureActionGrabEntity>(*this, *entityToCarry));
            return;
        }

        if((tileToClaim != nullptr) && (getClaimRate() > 0.0))
        {
            pushAction(Utils::make_unique<CreatureActionSearchGroundTileToClaim>(*this, true));
            pushAction(Utils::make_unique<CreatureActionClaimGroundTile>(*this, *tileToClaim));
            return;
        }

        if((tileWallNotClaimed != nullptr) && (getClaimRate() > 0.0))
        {
            pushAction(Utils::make_unique<CreatureActionSearchWallTileToClaim>(*this, true));
            pushAction(Utils::make_unique<CreatureActionClaimWallTile>(*this, *tileWallNotClaimed));
            return;
        }

        // We couldn't find why we were dropped here. Let's behave as usual
        return;
    }

    // Fighters
    // If we are dropped on a tile with a building, we notify it so that it
    // can do some special actions
    Tile* tile = getPositionTile();
    if((tile != nullptr) &&
       (tile->getCoveringBuilding() != nullptr))
    {
        Building* building = tile->getCoveringBuilding();
        building->creatureDropped(*this);
        return;
    }
}

bool Creature::resizeMeshAfterDrop()
{
    RenderManager::getSingleton().rrScaleCreature(*this);
    return false;
}


bool Creature::wallDigPath(Tile* wallTile, Tile* nTile, uint32_t slot, std::vector<Ogre::Vector2>& path)
{
    if(nTile == nullptr || wallTile == nullptr || getPositionTile() == nullptr || slot >= 3)
        return false;

    const Ogre::Vector2 facing = wallTile->getPosition2d() - nTile->getPosition2d();
    const Ogre::Vector2 sideways(-facing.y, facing.x);
    // All three standing centers stay inside the same floor tile, including narrow corridors.
    const float offset = slot == 0 ? 0.0f : (slot == 1 ? -1.0f / 3.0f : 1.0f / 3.0f);
    const Ogre::Vector2 point = nTile->getPosition2d() + facing * 0.2f + sideways * offset;
    Tile* destination = getGameMap()->getTile(Helper::round(point.x), Helper::round(point.y));
    if(destination == nullptr || !canGoThroughTile(destination) ||
        !getGameMap()->pathExists(this, getPositionTile(), destination))
        return false;
    const std::list<Tile*> tiles = getGameMap()->path(this, destination);
    tileToVector2(tiles, path, true, 0.0f);
    path.push_back(point);
    RoomObjectNavigation::refine(*this, path);
    if(!RoomObjectPath::clearPoint(RoomObjectNavigation::bodyObstacles(*this), point, facing) ||
        path.empty() || path.back() != point ||
        RoomObjectNavigation::blocked(*this, path))
    {
        path.clear();
        return false;
    }
    return true;
}

bool Creature::parkToWallTile(Tile* wallTile, Tile* nTile)
{
    const int slot = wallTile == nullptr || nTile == nullptr ? -1 : wallTile->getWorkerDiggingSlot(*this, *nTile);
    if(slot >= 0)
    {
        std::vector<Ogre::Vector2> path;
        if(!wallDigPath(wallTile, nTile, static_cast<uint32_t>(slot), path))
            return false;
        setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
        pushAction(Utils::make_unique<CreatureActionParkToTile>(*this));
        return true;
    }
    if(nTile == nullptr || wallTile == nullptr )
        return false;

    Tile *posTile = getPositionTile();
    if(posTile == nullptr)
        return false;

    Ogre::Vector2 parkingPoint;
    // Stay well in front of the wall: the dig animation reaches forward, and 0.4 left only a tenth of a tile
    // to the edge, so the worker stood half inside the block
    static const double parkingShare = 0.2;
    parkingPoint = (wallTile->getPosition2d() - nTile->getPosition2d())*parkingShare + nTile->getPosition2d() ;

    
    std::list<Tile*> result = getGameMap()->path(this, nTile);

    std::vector<Ogre::Vector2> path;
    tileToVector2(result, path, true, 0.0);
    
    path.push_back(parkingPoint);
    
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path,false);

    pushAction(Utils::make_unique<CreatureActionParkToTile>(*this));    
    return true;
}

bool Creature::setDestination(Tile* tile)
{
    if(tile == nullptr)
        return false;

    Tile *posTile = getPositionTile();
    if(posTile == nullptr)
        return false;

    std::list<Tile*> result = getGameMap()->path(this, tile);

    std::vector<Ogre::Vector2> path;
    tileToVector2(result, path, true, 0.0);
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path,true);
    if(!isMoving() && posTile != tile)
    {
        if(path.empty())
        {
            OD_LOG_INF("creature=" + getName() + " has no tile path from " + Tile::displayAsString(posTile)
                + " to " + Tile::displayAsString(tile));
            return false;
        }

        // The tile path exists but the refinement around room objects found no route
        // (for example because the tile center is covered by an object). We walk the
        // tile path as it is instead of failing the whole action.
        OD_LOG_INF("creature=" + getName() + " walks the unrefined tile path from " + Tile::displayAsString(posTile)
            + " to " + Tile::displayAsString(tile));
        setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true, true);
        if(!isMoving())
            return false;
    }
    pushAction(Utils::make_unique<CreatureActionWalkToTile>(*this));
    return true;
}

void Creature::checkWalkPathIsStillValid()
{
    if(mWalkQueue.empty())
        return;

    bool isPathBlocked = false;
    for(const Ogre::Vector2& step : mWalkQueue)
    {
        Tile* tile = getGameMap()->getTile(Helper::round(step.x), Helper::round(step.y));
        if(tile == nullptr)
            continue;

        if(canGoThroughTile(tile))
            continue;

        // A building that does not let the creature through (closed door, prison) is meant to stop it
        if(tile->getCoveringBuilding() != nullptr)
            continue;

        isPathBlocked = true;
        break;
    }

    if(!isPathBlocked)
        return;

    const Ogre::Vector2& lastStep = mWalkQueue.back();
    Tile* destination = getGameMap()->getTile(Helper::round(lastStep.x), Helper::round(lastStep.y));

    OD_LOG_INF("creature=" + getName() + " cannot walk its path anymore, destination="
        + Tile::displayAsString(destination));

    // Stop where we are rather than walk into what is now lava or water
    clearDestinations(EntityAnimation::idle_anim, true, true);

    if((destination == nullptr) || !canGoThroughTile(destination))
        return;

    std::list<Tile*> result = getGameMap()->path(this, destination);
    if(result.size() <= 1)
        return;

    std::vector<Ogre::Vector2> path;
    tileToVector2(result, path, true, 0.0);
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true);
}

void Creature::applyLavaDamage()
{
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return;

    if(myTile->getTileVisual() != TileVisual::lavaGround)
        return;

    if(myTile->getCoveringBuilding() != nullptr)
        return;

    if(getMoveSpeedLava() > 0.0)
        return;

    double lavaDamagePerSecond = ConfigManager::getSingleton().getLavaDamagePerSecond();
    takeDamage(nullptr, lavaDamagePerSecond / ODApplication::turnsPerSecond, 0.0, 0.0, 0.0, myTile, false);
}

bool Creature::wanderRandomly(const std::string& animationState)
{
    // We pick randomly a visible tile far away (at the end of visible tiles)
    if(mTilesWithinSightRadius.empty())
        return false;

    // Add reachable tiles only before searching for one of them
    std::vector<Tile*> reachableTiles;
    for (Tile* tile: mTilesWithinSightRadius)
    {
        // Only tiles the creature can enter are valid destinations (see handleIdleAction)
        if (canGoThroughTile(tile) && getGameMap()->pathExists(this, getPositionTile(), tile))
            reachableTiles.push_back(tile);
    }

    if (reachableTiles.empty())
        return false;

    // A random walking target must be a tile with a free standing point, not one covered by furniture
    RoomObjectNavigation::keepTilesWithStandingPosition(*this, reachableTiles);
    Tile* tileDestination = reachableTiles[Random::Uint(0, reachableTiles.size() - 1)];
    setDestination(tileDestination);
    return false;
}

bool Creature::isAttackable(Tile* tile, Seat* seat) const
{
    if(mHp <= 0.0)
        return false;

    // KO Creature to death creatures are not a threat and cannot be attacked. However, temporary KO can be
    if(mKoTurnCounter < 0)
        return false;

    // Creatures in prison are not a treat and cannot be attacked
    if(mSeatPrison != nullptr)
        return false;

    return true;
}

//! \brief Preserves living patient priorities and refuses workers, decaying or consumed bodies.
EntityCarryType Creature::getEntityCarryType(Creature* carrier)
{
    // Workers cannot be carried to crypt/prison
    if(getDefinition()->isWorker())
        return EntityCarryType::notCarryable;

    // A creature knocked out to death is carried to a prison when it is an enemy. A creature of the seat of the
    // carrier is not carried: it is pulled to its own bed (same priority as before), and without an own bed it is
    // not touched and dies where it lies
    if(mKoTurnCounter < 0)
    {
        if((carrier != nullptr) && (carrier->getSeat() == getSeat()))
            return (isKoToDeathForBedPull() || RoomInfirmary::wouldAccept(*this)) ? EntityCarryType::koCreature : EntityCarryType::notCarryable;

        return EntityCarryType::koCreature;
    }

    // Only an intact, unconsumed body can still be carried.
    if(getHP() <= 0.0)
        return (mDecayTurns < 0.0 && mDeathCounter != std::numeric_limits<unsigned int>::max()) ?
            EntityCarryType::corpse : EntityCarryType::notCarryable;

    // A hurt creature of the carrier's seat close enough is pulled to its bed (the worker takes it by the legs,
    // see CreatureActionCarryEntity: it is not carried, but it takes the place of a carried thing in the search)
    if((carrier != nullptr) && (carrier->getSeat() == getSeat()) && getIsOnServerMap() &&
       isWoundedForBedCarry())
    {
        Tile* myTile = getPositionTile();
        Tile* carrierTile = carrier->getPositionTile();
        double radius = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedCarryRadius", WOUNDED_CARRY_RADIUS_DEFAULT);
        if((myTile == nullptr) || (carrierTile == nullptr) ||
           (Pathfinding::squaredDistanceTile(*myTile, *carrierTile) > (radius * radius)))
        {
            return EntityCarryType::notCarryable;
        }

        // The priority against the other things a worker can carry is configurable:
        // 0 = lowest, 1 = like gold, 2 = like a creature knocked out to death
        int32_t priority = static_cast<int32_t>(ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedCarryPriority", WOUNDED_CARRY_PRIORITY_DEFAULT));
        if(priority <= 0)
            return EntityCarryType::woundedCreature;
        if(priority == 1)
            return EntityCarryType::gold;
        return EntityCarryType::koCreature;
    }

    return EntityCarryType::notCarryable;
}

bool Creature::isWoundedForBedCarry() const
{
    if(isActionInList(CreatureActionType::infirmaryRest))
        return false;

    if(!getIsOnServerMap() || !getIsOnMap() || !isAlive() || mIsBeingDragged || mIsInHand ||
       isPossessed() || isInPrison() || getDefinition()->isWorker() || getDefinition()->isChampion())
    {
        return false;
    }

    ConfigManager& config = ConfigManager::getSingleton();
    // 0 percent switches the whole behaviour off
    double hpPercent = config.getRoomConfigDoubleOrDefault("DormitoryWoundedCarryHpPercent", WOUNDED_CARRY_HP_PERCENT_DEFAULT);
    if((hpPercent <= 0.0) || (getMaxHp() <= 0.0) || ((getHP() * PERCENT_FACTOR) >= (getMaxHp() * hpPercent)))
        return false;

    // A creature knocked out for a while may be carried too, unless the config says no
    if((mKoTurnCounter != 0) && (config.getRoomConfigDoubleOrDefault("DormitoryWoundedCarryTempKo", WOUNDED_CARRY_TEMP_KO_DEFAULT) <= 0.0))
        return false;

    // Creatures knocked out to death are handled by isKoToDeathForBedPull
    if(mKoTurnCounter < 0)
        return false;

    if(getGameMap()->getTurnNumber() < mWoundedCarryNextTurn)
        return false;

    // It only goes to its own bed in a dormitory of its seat, and not when it already lies in it
    if(!hasOwnBedInDormitory())
        return false;

    Tile* myTile = getPositionTile();
    if((myTile == nullptr) || (myTile == mHomeTile))
        return false;

    // No fight, flight or call to war going on
    if(isActionInList(CreatureActionType::fight) || isActionInList(CreatureActionType::fightFriendly) ||
       isActionInList(CreatureActionType::flee) || isActionInList(CreatureActionType::goCallToWar) ||
       isActionInList(CreatureActionType::leaveDungeon))
    {
        return false;
    }

    double enemyRadius = config.getRoomConfigDoubleOrDefault("DormitoryWoundedCarryEnemyRadius", WOUNDED_CARRY_ENEMY_RADIUS_DEFAULT);
    return !isHostileNear(enemyRadius);
}

bool Creature::hasOwnBedInDormitory() const
{
    return (mHomeTile != nullptr) && (mHomeTile->getCoveringRoom() != nullptr) &&
        (mHomeTile->getCoveringRoom()->getType() == RoomType::dormitory) &&
        (mHomeTile->getCoveringRoom()->getSeat() == getSeat());
}

bool Creature::isKoToDeathForBedPull() const
{
    if(!getIsOnServerMap() || !getIsOnMap() || !isAlive() || (mKoTurnCounter >= 0) || mIsBeingDragged || mIsInHand ||
       isPossessed() || isInPrison() || getDefinition()->isWorker())
    {
        return false;
    }

    // Only to its own bed: without one it is not picked up, not moved and dies where it lies. The percent of
    // health and the fights do not matter here, the counter to death is running. Only the pause after a pull
    // that ended counts (DormitoryWoundedKoDeathCooldown, set in notifyDragEnd): the counter goes on meanwhile
    if(getGameMap()->getTurnNumber() < mWoundedCarryNextTurn)
        return false;

    if(!hasOwnBedInDormitory())
        return false;

    double enemyRadius = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedCarryEnemyRadius", WOUNDED_CARRY_ENEMY_RADIUS_DEFAULT);
    return !isHostileNear(enemyRadius);
}

bool Creature::isHostileNear(double radius) const
{
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return false;

    double squaredRadius = radius * radius;
    const std::vector<Creature*>& creatures = getGameMap()->getCreatures();
    for(Creature* other : creatures)
    {
        if((other == this) || !other->isAlive() || !other->getIsOnMap() || other->isKo())
            continue;

        // Workers are no threat
        if(other->getDefinition()->isWorker())
            continue;

        if(getSeat()->isAlliedSeat(other->getSeat()))
            continue;

        Tile* otherTile = other->getPositionTile();
        if(otherTile == nullptr)
            continue;

        if(Pathfinding::squaredDistanceTile(*myTile, *otherTile) <= squaredRadius)
            return true;
    }
    return false;
}

//! \brief Pauses corpse time while the worker carries the creature.
void Creature::notifyEntityCarryOn(Creature* carrier)
{
    mIsCarried = true;
    mCorpseCarrierName = carrier->getName();
    removeEntityFromPositionTile();
}

//! \brief Resumes corpse time at the worker delivery or interruption position.
void Creature::notifyEntityCarryOff(const Ogre::Vector3& position)
{
    mIsCarried = false;
    mCorpseCarrierName.clear();
    mPosition = position;
    addEntityToPositionTile();
}

void Creature::notifyDragStart(double pullerDirtFactor)
{
    mIsBeingDragged = true;
    mDragDirtFactor = pullerDirtFactor;

    // A hurt creature stops what it did, it lies on the ground and the worker pulls it (one knocked out to death
    // included: its counter goes on running). It stays on the map (it is not carried): the walk paths the worker
    // gives it move it.
    if(getIsOnServerMap())
    {
        clearDestinations(EntityAnimation::idle_anim, true, true);
        clearActionQueue();
    }
}

void Creature::notifyDragEnd()
{
    if(!mIsBeingDragged)
        return;

    mIsBeingDragged = false;
    mDragDirtFactor = 1.0;
    if(!getIsOnServerMap())
        return;

    // The pause before it can be pulled again, whatever the end of the drag was
    // (a creature knocked out to death has its own, usually longer, pause)
    double cooldown = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedCarryCooldown", WOUNDED_CARRY_COOLDOWN_DEFAULT);
    if(mKoTurnCounter < 0)
        cooldown = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("DormitoryWoundedKoDeathCooldown", 150.0);
    mWoundedCarryNextTurn = getGameMap()->getTurnNumber() + static_cast<int64_t>(std::max(0.0, cooldown));
}

bool Creature::setDragDestination(Tile* tile)
{
    if(tile == nullptr)
        return false;

    Tile* posTile = getPositionTile();
    if(posTile == nullptr)
        return false;

    std::list<Tile*> result = getGameMap()->path(this, tile);

    std::vector<Ogre::Vector2> path;
    tileToVector2(result, path, true, 0.0);
    setWalkPath(EntityAnimation::drag_anim, EntityAnimation::idle_anim, true, true, path, true);
    return isMoving() || (posTile == tile);
}

void Creature::carryEntity(GameEntity* carriedEntity)
{
    if(!getIsOnServerMap())
        return;

    OD_ASSERT_TRUE(carriedEntity != nullptr);
    OD_ASSERT_TRUE(mCarriedEntity == nullptr);
    mCarriedEntity = nullptr;
    if(carriedEntity == nullptr)
        return;

    // We remove the carried entity from the clients gamemaps as well as the carrier
    // and we send the carrier creation message (that will embed the carried)
    carriedEntity->fireRemoveEntityToSeatsWithVision();
    // We only notify seats that already had vision. We copy the seats with vision list
    // because fireRemoveEntityToSeatsWithVision will empty it.
    std::vector<Seat*> seatsWithVision = mSeatsWithVisionNotified;
    // We remove ourself and send the creation
    fireRemoveEntityToSeatsWithVision();
    mCarriedEntity = carriedEntity;
    notifySeatsWithVision(seatsWithVision);
}

void Creature::releaseCarriedEntity()
{
    if(!getIsOnServerMap())
        return;

    GameEntity* carriedEntity = mCarriedEntity;
    mCarriedEntity = nullptr;
    if(carriedEntity == nullptr)
    {
        OD_LOG_ERR("name=" + getName());
        return;
    }

    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr)
            continue;
        if(!seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::releaseCarriedEntity, seat->getPlayer());
        serverNotification->mPacket << getName() << carriedEntity->getObjectType();
        serverNotification->mPacket << carriedEntity->getName();
        serverNotification->mPacket << mPosition;
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

bool Creature::canSlap(Seat* seat)
{
    Tile* tile = getPositionTile();
    if(tile == nullptr)
    {
        OD_LOG_ERR("entityName=" + getName());
        return false;
    }

    if(mDropCooldown > 0)
        return false;

    if(getGameMap()->isInEditorMode())
        return true;

    if(getHP() <= 0.0)
        return false;

    // A creature controlled by a player cannot be slapped
    if(isPossessed())
        return false;

    // If the creature is in prison, it can be slapped by the jail owner only
    if(mSeatPrison != nullptr)
        return (mSeatPrison == seat);

    // Only the owning player can slap a creature
    if(getSeat() != seat)
        return false;

    return true;
}

void Creature::slap()
{
    if(!getIsOnServerMap())
        return;

    fireCreatureSound(CreatureSound::Slap);

    // In editor mode, we remove the creature
    if(getGameMap()->isInEditorMode())
    {
        removeFromGameMap();
        deleteYourself();
        return;
    }

    // A slap sends the champion away
    if(getDefinition()->isChampion())
    {
        dismissChampion();
        return;
    }

    // A slap stops a brawl
    if(!mBrawlOpponent.empty())
        endBrawl();
    mBrawlResumeOpponent.clear();

    if(getSeat() != nullptr)
        ++getSeat()->getStatistics().mCreaturesSlapped;

    recordScriptEvent(*this, "slapped");

    CreatureEffectSlap* effect = new CreatureEffectSlap(
        ConfigManager::getSingleton().getSlapEffectDuration(), "");
    addCreatureEffect(effect);

    // We remember the slap to compute the mood. Only the latest ones are kept
    mSlapTurns.push_back(getGameMap()->getTurnNumber());
    if(mSlapTurns.size() > 10)
        mSlapTurns.erase(mSlapTurns.begin());

    // The friends that see the slap are upset
    reportSlapToFriends();

    mHp -= mMaxHP * ConfigManager::getSingleton().getSlapDamagePercent() / 100.0;
    computeCreatureOverlayHealthValue();
}

void Creature::fireAddEntity(Seat* seat, bool async, NodeType nt )
{
    if(async)
    {
        ServerNotification serverNotification(
            ServerNotificationType::addEntity, seat->getPlayer());
        serverNotification.mPacket << nt;          
        exportHeadersToPacket(serverNotification.mPacket);
        exportToPacket(serverNotification.mPacket, seat);
        ODServer::getSingleton().sendAsyncMsg(serverNotification);

        if(mCarriedEntity != nullptr)
        {
            OD_LOG_ERR("Trying to fire add creature in async mode name=" + getName() + " while carrying " + mCarriedEntity->getName());
        }

        // The jump that is running is sent after the entity data (queued: the creature is on the client by then)
        if(isJumping())
            sendJumpNotificationTo(seat);
        return;
    }

    ServerNotification* serverNotification = new ServerNotification(
        ServerNotificationType::addEntity, seat->getPlayer());
    serverNotification->mPacket << nt;      
    exportHeadersToPacket(serverNotification->mPacket);
    exportToPacket(serverNotification->mPacket, seat);
    ODServer::getSingleton().queueServerNotification(serverNotification);

    // A seat that gains sight in the middle of a jump gets the running arc after the entity data
    if(isJumping())
        sendJumpNotificationTo(seat);

    if(mCarriedEntity != nullptr)
    {
        mCarriedEntity->addSeatWithVision(seat, false);

        serverNotification = new ServerNotification(
            ServerNotificationType::carryEntity, seat->getPlayer());
        serverNotification->mPacket << getName() << mCarriedEntity->getObjectType();
        serverNotification->mPacket << mCarriedEntity->getName();
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void Creature::fireRemoveEntity(Seat* seat,NodeType nt)
{
    // If we are carrying an entity, we release it first, then we can remove it and us
    if(mCarriedEntity != nullptr)
    {
        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::releaseCarriedEntity, seat->getPlayer());
        serverNotification->mPacket << getName() << mCarriedEntity->getObjectType();
        serverNotification->mPacket << mCarriedEntity->getName();
        serverNotification->mPacket << mPosition;
        ODServer::getSingleton().queueServerNotification(serverNotification);

        mCarriedEntity->removeSeatWithVision(seat);
    }

    const std::string& name = getName();
    ServerNotification *serverNotification = new ServerNotification(
        ServerNotificationType::removeEntity, seat->getPlayer());
    GameEntityType type = getObjectType();
    serverNotification->mPacket << type;
    serverNotification->mPacket << name;
    serverNotification->mPacket << NodeType::MTILES_NODE;
    ODServer::getSingleton().queueServerNotification(serverNotification);
}

void Creature::fireCreatureRefreshIfNeeded()
{
    const CreatureActivity activity = getActivity();
    if(!(mActivity == activity))
    {
        mActivity = activity;
        mNeedFireRefresh = true;
    }

    // The carried gold is sent with the update, only when the amount changed
    if(mGoldCarried != mGoldCarriedNotified)
    {
        mGoldCarriedNotified = mGoldCarried;
        mNeedFireRefresh = true;
    }

    if(!mNeedFireRefresh)
        return;

    mNeedFireRefresh = false;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr)
            continue;
        if(!seat->getPlayer()->getIsHuman())
            continue;

        const std::string& name = getName();
        ServerNotification *serverNotification = new ServerNotification(
            ServerNotificationType::entitiesRefresh, seat->getPlayer());
        uint32_t nbCreature = 1;
        serverNotification->mPacket << nbCreature;
        serverNotification->mPacket << GameEntityType::creature;
        serverNotification->mPacket << name;
        exportToPacketForUpdate(serverNotification->mPacket, seat);
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void Creature::fireChatMsgTookFee(int goldTaken)
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    std::string suffix;
    // We don't display the same message if we have taken all our fee or only a part of it
    if(getGoldFee() <= 0)
        suffix = " took its fee: " + Helper::toString(goldTaken);
    else
        suffix = " took " + Helper::toString(goldTaken) + " from its fee";

    getSeat()->getPlayer()->notifyCreatureEvent(*this, suffix);
}

void Creature::fireChatMsgLeftDungeon()
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    getSeat()->getPlayer()->notifyCreatureEvent(*this, " left your dungeon");
}

void Creature::fireChatMsgLeavingDungeon()
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    getSeat()->getPlayer()->notifyCreatureEvent(*this, " is leaving your dungeon");
}

void Creature::fireChatMsgBecameRogue()
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    getSeat()->getPlayer()->notifyCreatureEvent(*this, " is not under your control anymore !");
}

void Creature::fireChatMsgUnhappy()
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    getSeat()->getPlayer()->notifyCreatureEvent(*this, " is unhappy !");
}

void Creature::fireChatMsgFurious()
{
    if(getSeat()->getPlayer() == nullptr)
        return;
    if(!getSeat()->getPlayer()->getIsHuman())
        return;
    if(getSeat()->getPlayer()->getHasLost())
        return;

    getSeat()->getPlayer()->notifyCreatureEvent(*this, " is furious !");
}

//! \brief Resolves the definition and builds authoritative server stats while preserving received client summaries.
void Creature::setupDefinition(GameMap& dtc, const CreatureDefinition& defaultWorkerCreatureDefinition)
{
    bool setHpToStrHp = false;
    if(mDefinition == nullptr)
    {
        // If the classname corresponds to the default worker CreatureDefinition, we use
        // the dedicated class. The correct one will be set after the seat is initialized
        if(!mDefinitionString.empty() &&  mDefinitionString.compare(ConfigManager::DefaultWorkerCreatureDefinition) != 0)
        {
            mDefinition = dtc.getClassDescription(mDefinitionString);
        }
        else
        {
            // If we are in editor mode, we take the default worker class. Otherwise, we take
            // the default worker from the seat faction
            if(dtc.isInEditorMode() || !mSeat)
                mDefinition = &defaultWorkerCreatureDefinition;
            else
                mDefinition = getSeat()->getWorkerClassToSpawn();
        }

        if(mDefinition == nullptr)
        {
            OD_LOG_ERR("Definition=" + mDefinitionString);
            return;
        }

        // Non-thirsty types clear ordinary saved thirst; GhostRevival restores the explicitly required value afterwards.
        if(!mDefinition->hasThirst())
            mThirst = 0.0;
        if(mRevivalThirstFromSave)
        { mThirst=mSavedRevivalThirst;mRevivalThirstFromSave=false; }

        if(getIsOnServerMap())
        {
            setHpToStrHp = true;

            // name
            if (getName().compare("autoname") == 0)
            {
                std::string name = getGameMap()->nextUniqueNameCreature(mDefinition->getClassName());
                setName(name);
            }

            // Loaded creature: old saves and creatures spawned without a manifest get a stable appearance
            assignAppearance(false);
        }
    }

    if(getIsOnServerMap())
    {
        for(const CreatureSkill* skill : mDefinition->getCreatureSkills())
        {
            CreatureSkillData skillData(skill, getAppliedCooldownNbTurns(*skill), 0);
            mSkillData.push_back(skillData);
        }

        // The skill tree: personal seed, free rank of the pre-skill and the points the level has paid
        initSkillBuild();
    }

    if(getIsOnServerMap())
        buildStats();
    else
        resizePotionSlots();

    // Now, the max hp is known. If needed, we set it
    if(setHpToStrHp)
    {
        if(mHpString.compare("max") == 0)
            mHp = mMaxHP;
        else
            mHp = Helper::toDouble(mHpString);

        computeCreatureOverlayHealthValue();
        if(!isAlive() && mDeathCounter != 0)
        {
            const std::string& animation = mDecayTurns >= 0.0 ? EntityAnimation::rot_anim : EntityAnimation::die_anim;
            clearDestinations(animation, false, false);
            setAnimationState(animation, false, Ogre::Vector3::ZERO, false);
        }

        // The mana comes from the save, or the pool is full (old saves and creatures from a level file)
        if(mManaFromSave)
            mMana = std::min(mMana, getMaxMana());
        else
            mMana = getMaxMana();
        mManaRingStepNotified = manaRingStep(mMana, getMaxMana());
    }
}

void Creature::fireCreatureSound(CreatureSound sound)
{
    Tile* posTile = getPositionTile();
    if(posTile == nullptr)
        return;

    std::string soundFamily;
    switch(sound)
    {
        case CreatureSound::Pickup:
            soundFamily = getDefinition()->getSoundFamilyPickup();
            break;
        case CreatureSound::Drop:
            soundFamily = getDefinition()->getSoundFamilyDrop();
            break;
        case CreatureSound::Attack:
            soundFamily = getDefinition()->getSoundFamilyAttack();
            break;
        case CreatureSound::Die:
            soundFamily = getDefinition()->getSoundFamilyDie();
            break;
        case CreatureSound::Slap:
            soundFamily = getDefinition()->getSoundFamilySlap();
            break;
        case CreatureSound::Dig:
            soundFamily = "Default/Dig";
            break;
        case CreatureSound::Relieve:
            soundFamily = "Default/Relieve";
            break;
        case CreatureSound::Clean:
            soundFamily = "Default/Clean";
            break;
        default:
            OD_LOG_ERR("Wrong CreatureSound value=" + Helper::toString(static_cast<uint32_t>(sound)));
            return;
    }

    std::string soundComplete = "Creatures/" + soundFamily;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr)
            continue;
        if(!seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification *serverNotification = new ServerNotification(
            ServerNotificationType::playSpatialSound, seat->getPlayer());
        serverNotification->mPacket << soundComplete << posTile->getX() << posTile->getY();
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void Creature::fireCombatImpact(bool weaponClash, bool bodyDamage,
    const Ogre::Vector3& attackerPosition)
{
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* notification = new ServerNotification(
            ServerNotificationType::creatureCombatImpact, seat->getPlayer());
        notification->mPacket << getName() << weaponClash << bodyDamage
            << attackerPosition;
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

void Creature::fireChickenFeeding(const std::string& chickenName,
    const Ogre::Vector3& chickenPosition)
{
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* notification = new ServerNotification(
            ServerNotificationType::creatureChickenFeeding, seat->getPlayer());
        notification->mPacket << getName() << chickenName << chickenPosition;
        ODServer::getSingleton().queueServerNotification(notification);
    }
}

void Creature::fireCosmeticEvent(const CosmeticEvent& event, bool alliedOnly)
{
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;

        if(alliedOnly && !seat->isAlliedSeat(getSeat()))
            continue;

        ODServer::getSingleton().sendCosmeticEvent(seat->getPlayer(), event);
    }
}

void Creature::fireCosmeticEvent(int32_t type, int32_t value, int32_t value2, bool alliedOnly)
{
    CosmeticEvent event;
    event.mType = type;
    event.mSubject = getName();
    event.mValue = value;
    event.mValue2 = value2;
    fireCosmeticEvent(event, alliedOnly);
}

void Creature::fireAttackTurn(const std::string& targetName, const Ogre::Vector3& direction)
{
    if(!ConfigManager::getSingleton().getAttackTurnEvents())
        return;

    CosmeticEvent event(CosmeticEventType::attackTurn);
    event.mSubject = getName();
    event.mObject = targetName;
    event.mPosition = direction;
    fireCosmeticEvent(event, false);
}

void Creature::fireHitResult(const std::string& attackerName, double damageDone, double rawDamage, bool missile,
    bool critical)
{
    if(!ConfigManager::getSingleton().getHitEvents())
        return;

    // The share of the damage that got through the defense decides between a hit, a glancing blow and a blocked one;
    // a critical blow that did damage is reported as critical
    double share = (rawDamage > 0.0) ? damageDone / rawDamage : 0.0;
    share = std::max(0.0, std::min(1.0, share));
    CosmeticHitResult result = CosmeticHitResult::hit;
    if(damageDone <= 0.0)
        result = CosmeticHitResult::blocked;
    else if(critical)
        result = CosmeticHitResult::critical;
    else if(share < ConfigManager::getSingleton().getHitGlanceShare())
        result = CosmeticHitResult::glanced;

    // How hard it hit: the damage in per mille of the maximum health of this creature
    double maxHp = getMaxHp();
    double healthShare = (maxHp > 0.0) ? damageDone / maxHp : 0.0;
    healthShare = std::max(0.0, std::min(1.0, healthShare));

    CosmeticEvent event(CosmeticEventType::hitResult);
    event.mSubject = attackerName;
    event.mObject = getName();
    event.mText = missile ? "missile" : "melee";
    event.mValue = static_cast<int32_t>(result);
    event.mValue2 = static_cast<int32_t>(healthShare * 1000.0 + 0.5);
    event.mPosition = getPosition();
    fireCosmeticEvent(event, false);
}

//! \brief Reports a critical hit of this creature on a building or a wall; the event has no target creature, so the
//! client plays the feedback on this (the attacking) creature.
void Creature::fireCriticalOnStructure(const std::string& kind, const Ogre::Vector3& position)
{
    if(!ConfigManager::getSingleton().getHitEvents())
        return;

    CosmeticEvent event(CosmeticEventType::hitResult);
    event.mSubject = getName();
    event.mText = kind;
    event.mValue = static_cast<int32_t>(CosmeticHitResult::critical);
    event.mValue2 = 0;
    event.mPosition = position;
    fireCosmeticEvent(event, false);
}

//! \brief Reports a critical spell or area damage on this creature (no damage share, the damage follows by effect).
void Creature::fireCriticalSpell(const std::string& attackerName)
{
    if(!ConfigManager::getSingleton().getHitEvents())
        return;

    CosmeticEvent event(CosmeticEventType::hitResult);
    event.mSubject = attackerName;
    event.mObject = getName();
    event.mText = "spell";
    event.mValue = static_cast<int32_t>(CosmeticHitResult::critical);
    event.mValue2 = 0;
    event.mPosition = getPosition();
    fireCosmeticEvent(event, false);
}

//! \brief Sends the missed result for the selected attack kind.
void Creature::fireHitMissed(const std::string& attackerName, bool missile)
{
    if(!ConfigManager::getSingleton().getHitEvents())
        return;

    CosmeticEvent event(CosmeticEventType::hitResult);
    event.mSubject = attackerName;
    event.mObject = getName();
    event.mText = missile ? "missile" : "melee";
    event.mValue = static_cast<int32_t>(CosmeticHitResult::missed);
    event.mValue2 = 0;
    event.mPosition = getPosition();
    fireCosmeticEvent(event, false);
}

//! \brief Reports the single avoidance result for a landed blow or shot.
void Creature::fireHitDefended(const std::string& attackerName, DefenceChance::Outcome outcome, bool missile)
{
    if(!ConfigManager::getSingleton().getHitEvents())
        return;

    if(outcome == DefenceChance::none)
        return;

    CosmeticEvent event(CosmeticEventType::hitResult);
    event.mSubject = attackerName;
    event.mObject = getName();
    event.mText = missile ? "missile" : "melee";
    CosmeticHitResult result = CosmeticHitResult::dodged;
    if(outcome == DefenceChance::parried)
        result = CosmeticHitResult::parried;
    else if(outcome == DefenceChance::shieldBlocked)
        result = CosmeticHitResult::shieldBlocked;
    event.mValue = static_cast<int32_t>(result);
    event.mValue2 = 0;
    event.mPosition = getPosition();
    fireCosmeticEvent(event, false);
}

//! \brief Resolves hit chance against this defender, bypassing the roll for a possessed attacker.
bool Creature::rollAttackHit(double attackRating, uint32_t attackerLevel, bool possessed) const
{
    if(possessed)
        return true;
    return Random::Double(0.0, 100.0) < DefenceChance::hitChance(attackRating, getDefenseRating(),
        attackerLevel, getLevel());
}

//! \brief Rolls one configured avoidance kind; parry cannot stop missiles and block requires a shield. The avoid
//! passives add to the chance; a creature without avoidance kind dodges with their sum.
DefenceChance::Outcome Creature::rollMeleeDefence(bool missile) const
{
    ConfigManager& config = ConfigManager::getSingleton();
    if(!config.getMeleeDodgeParry())
        return DefenceChance::none;

    // Only a creature that can really move out of the way: alive, awake, on the map, not held or dragged and
    // not possessed by a keeper
    if(!getIsOnServerMap() || !getIsOnMap() || !isAlive() || isKo() || mIsInHand || mIsBeingDragged || isPossessed())
        return DefenceChance::none;

    const CreatureDefinition::Avoidance avoidance = getDefinition()->getAvoidance();
    // The avoid passives add to the avoidance chance; a creature without avoidance kind dodges with their sum
    const double avoidBonus = getSkillPassive("avoid") + (missile ? getItemEffect("Deflect") : 0.0);
    if((avoidance == CreatureDefinition::Avoidance::none && avoidBonus <= 0.0) ||
        (missile && avoidance == CreatureDefinition::Avoidance::parry))
        return DefenceChance::none;

    // Inspect held equipment for the selected avoidance kind; other creature types do not gain parry or block.
    bool hasShield = false;
    const Weapon* parryWeapons[2] = {nullptr, nullptr};
    const Weapon* weapons[2] = {getWeaponL(), getWeaponR()};
    for(uint32_t i = 0; i < 2; ++i)
    {
        if(weapons[i] == nullptr)
            continue;

        const std::string type = weapons[i]->getWeaponType();
        if(DefenceChance::isShieldType(type))
            hasShield = true;
        else if(DefenceChance::isParryWeaponType(type))
            parryWeapons[i] = weapons[i];
    }

    double chance = 0.0;
    DefenceChance::Outcome kind = DefenceChance::none;
    if(avoidance == CreatureDefinition::Avoidance::dodge)
    {
        kind = DefenceChance::dodged;
        chance = DefenceChance::dodgeChance(getLevel(), config.getDodgeBase(), config.getDodgePerLevel(), config.getDodgeMax());
    }
    else if(avoidance == CreatureDefinition::Avoidance::block && hasShield)
    {
        kind = DefenceChance::shieldBlocked;
        chance = DefenceChance::dodgeChance(getLevel(), config.getShieldBlockBase() + getItemEffect("Block"), config.getShieldBlockPerLevel(),
            config.getShieldBlockMax());
    }
    else if(avoidance == CreatureDefinition::Avoidance::none)
    {
        // Only the avoid passives give the creature a chance to dodge
        kind = DefenceChance::dodged;
    }
    else if(avoidance == CreatureDefinition::Avoidance::parry)
    {
        kind = DefenceChance::parried;
        // With two carried parry weapons, keep the larger resulting chance.
        for(uint32_t i = 0; i < 2; ++i)
        {
            if(parryWeapons[i] == nullptr)
                continue;
            chance = std::max(chance, DefenceChance::parryChance(getLevel(), true, parryWeapons[i]->getParryBase(),
                parryWeapons[i]->getParryPerLevel(), parryWeapons[i]->getParryMax()));
        }
    }
    if(kind != DefenceChance::none)
        chance += avoidBonus;
    // The selected avoidance kind uses exactly one server roll.
    return DefenceChance::decide(kind, chance, Random::Double(0.0, 100.0));
}

void Creature::fireImpatientIfNeeded()
{
    // The game counts a creature as frustrated from the turns its OutOfWork mood starts at. It is told then,
    // and again each time the mood has grown over its whole range.
    int32_t turnsMin = 10;
    int32_t repeat = 40;
    for(const CreatureMood* mood : getDefinition()->getCreatureMoods())
    {
        const CreatureMoodOutOfWork* outOfWork = dynamic_cast<const CreatureMoodOutOfWork*>(mood);
        if(outOfWork == nullptr)
            continue;

        turnsMin = outOfWork->getTurnsMin();
        repeat = std::max(1, outOfWork->getTurnsMax());
        break;
    }

    int32_t turns = getNbTurnsOutOfWork();
    if(turns < turnsMin || ((turns - turnsMin) % repeat) != 0)
        return;

    fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::impatient), turns, 0, true);
}

void Creature::fireArrivalEvent()
{
    Player* player = getSeat()->getPlayer();
    if(player == nullptr || !player->getIsHuman())
        return;

    // The creature has no vision yet and the portal belongs to the keeper, so the keeper is told directly.
    // Reading the mood only adds up the modifiers, it does not change the creature.
    int32_t points = CreatureMoodManager::computeCreatureMoodModifiers(*this);
    CosmeticEvent event(CosmeticEventType::portalArrival);
    event.mSubject = getName();
    event.mValue = static_cast<int32_t>(CreatureMoodManager::getCreatureMoodLevel(points));
    event.mValue2 = points;
    ODServer::getSingleton().sendCosmeticEvent(player, event);
}

void Creature::itsPayDay()
{
    // Rogue creatures do not have to be paid
    if(getSeat()->isRogueSeat())
        return;

    mGoldFee += mDefinition->getFee(getLevel());
}

void Creature::increaseHunger(double value)
{
    if(getSeat()->isRogueSeat())
        return;

    mHunger = std::min(100.0, mHunger + value);
}

//! \brief Lowers the hunger by val and raises the urge by UrgePerChicken.
void Creature::foodEaten(double val)
{
    mHunger -= val;
    if(mHunger < 0.0)
        mHunger = 0.0;

    increaseUrge(ConfigManager::getSingleton().getDirtConfigDouble("UrgePerChicken"));
}

//! \brief The creature took a drink: the thirst is 0, the urge rises and a beer adds drunkenness.
void Creature::drinkTaken(DrinkKind kind)
{
    ConfigManager& config = ConfigManager::getSingleton();
    mThirst = 0.0;
    if(kind == DrinkKind::beer)
    {
        increaseUrge(config.getTavernConfigDouble("UrgeFromBeer"));
        mDrunk = std::min(THIRST_STATE_MAX, mDrunk + config.getTavernConfigDouble("DrunkPerBeer"));
    }
    else
    {
        increaseUrge(config.getTavernConfigDouble("UrgeFromWater"));
    }
}

//! \brief Raises the thirst, limited to THIRST_STATE_MAX; rogue creatures have none. A creature of a human keeper that
//! is at the limit lets the keeper know when there is no tavern (the keeper limits the notices itself).
void Creature::increaseThirst(double value)
{
    if(getSeat()->isRogueSeat() || !mDefinition->hasThirst())
        return;

    mThirst = std::min(THIRST_STATE_MAX, mThirst + value);
    if((mThirst >= THIRST_STATE_MAX) && getIsOnServerMap() && (getSeat()->getPlayer() != nullptr))
        getSeat()->getPlayer()->notifyTavernEvent();
}

//! \brief Sets the thirst, limited to 0 - THIRST_STATE_MAX; a creature type that cannot get thirsty stays at 0.
void Creature::setThirst(double val)
{
    if(!mDefinition->hasThirst())
    {
        mThirst = 0.0;
        return;
    }
    mThirst = std::min(THIRST_STATE_MAX, std::max(0.0, val));
}

//! \brief Sets the drunkenness, limited to 0 - THIRST_STATE_MAX.
void Creature::setDrunk(double val)
{
    mDrunk = std::min(THIRST_STATE_MAX, std::max(0.0, val));
}

//! \brief Sets the turns a hangover still lasts, not below 0.
void Creature::setHangoverTurns(double turns)
{
    mHangoverTurns = std::max(0.0, turns);
}

//! \brief Sets the tavern mood and starts its timer again.
void Creature::addTavernMood(double points, double turns)
{
    mTavernMood = points;
    mTavernMoodTurns = std::max(0.0, turns);
}

//! \brief True if the drunkenness has reached StaggerAt.
bool Creature::isStaggering() const
{
    // A sober creature (nearly always) needs no look into the configuration
    if(mDrunk <= 0.0)
        return false;

    return mDrunk >= ConfigManager::getSingleton().getTavernConfigDouble("StaggerAt");
}

//! \brief Returns HangoverWorkFactor during a hangover, else 1.
double Creature::getHangoverWorkFactor() const
{
    if(mHangoverTurns <= 0.0)
        return 1.0;

    return ConfigManager::getSingleton().getTavernConfigDouble("HangoverWorkFactor");
}

//! \brief Raises the spa mood, limited to 0 .. SpaMoodMax.
void Creature::addSpaMood(double points)
{
    setSpaMood(mSpaMood + points);
}

//! \brief Sets the spa mood, limited to 0 .. SpaMoodMax.
void Creature::setSpaMood(double val)
{
    const double maxPoints = ConfigManager::getSingleton().getRoomConfigDouble("SpaMoodMax");
    mSpaMood = std::max(0.0, std::min(maxPoints, val));
}

//! \brief Sets the turns the relaxation still lasts, not below 0.
void Creature::setRelaxTurns(double turns)
{
    mRelaxTurns = std::max(0.0, turns);
}

//! \brief Returns SpaRelaxWorkFactor while the creature is relaxed, else 1.
double Creature::getRelaxWorkFactor() const
{
    if(mRelaxTurns <= 0.0)
        return 1.0;

    return ConfigManager::getSingleton().getRoomConfigDouble("SpaRelaxWorkFactor");
}

//! \brief Sets the number of tiles that still get mud, not below 0.
void Creature::setSpaMudTilesLeft(int32_t tiles)
{
    mSpaMudTilesLeft = std::max(0, tiles);
}

//! \brief True for a creature that is no worker, not in prison and not in the hand and either has a hangover or is
//! in a bad mood (Upset, Angry, Furious) with its relaxation run out.
bool Creature::wantsSpaBath() const
{
    if((mDefinition == nullptr) || mDefinition->isWorker() || mIsInHand || isInPrison() ||
       (getSeat() == nullptr) || getSeat()->isRogueSeat())
        return false;

    if(mHangoverTurns > 0.0)
        return true;

    if(mRelaxTurns > 0.0)
        return false;

    const CreatureMoodLevel mood = getMoodValue();
    return (mood == CreatureMoodLevel::Upset) || (mood == CreatureMoodLevel::Angry) || (mood == CreatureMoodLevel::Furious);
}

//! \brief Lets the spa mood fade by SpaMoodDecayPerTurn and counts the relaxation down by 1 per turn. The mood does not fade
//! while the creature sits in a bath (the bath lifts it exactly to SpaMoodMax).
void Creature::upkeepSpaState()
{
    if((mSpaMood <= 0.0) && (mRelaxTurns <= 0.0))
        return;

    if((mSpaMood > 0.0) && !mSpaBathing)
        mSpaMood = std::max(0.0, mSpaMood - ConfigManager::getSingleton().getRoomConfigDouble("SpaMoodDecayPerTurn"));

    if(mRelaxTurns > 0.0)
        mRelaxTurns = std::max(0.0, mRelaxTurns - 1.0);
}

//! \brief The point on the arc: a straight line from the start to the landing point with a parabola on the height
//! that reaches SpaJumpHeight half way.
Ogre::Vector3 Creature::jumpPosition(const Ogre::Vector3& from, const Ogre::Vector3& to, Ogre::Real progress)
{
    const Ogre::Real clamped = std::min(1.0f, std::max(0.0f, progress));
    Ogre::Vector3 position = from + (to - from) * clamped;
    const Ogre::Real height = static_cast<Ogre::Real>(ConfigManager::getSingleton().getRoomConfigDouble("SpaJumpHeight"));
    position.z += height * JUMP_ARC_FACTOR * clamped * (1.0f - clamped);
    return position;
}

//! \brief Starts the jump (the pattern of the hop of a rooster): remembers start and landing point, plays the Jump
//! clip and tells the clients.
void Creature::startJump(const Ogre::Vector3& target)
{
    const uint32_t turns = static_cast<uint32_t>(std::max(1.0,
        ConfigManager::getSingleton().getRoomConfigDouble("SpaJumpTurns")));
    mJumpFrom = getPosition();
    mJumpTo = target;
    mJumpTurns = turns;
    mJumpTurnsLeft = turns;
    mJumpElapsed = 0.0f;
    clearDestinations(EntityAnimation::jump_anim, false, false);
    sendJumpNotification();
}

//! \brief Ends the jump and puts a living creature on the floor again.
void Creature::cancelJump()
{
    if(mJumpTurnsLeft == 0)
        return;

    mJumpTurnsLeft = 0;
    if(!getIsOnServerMap() || !getIsOnMap() || !isAlive())
        return;

    const Ogre::Vector3 position = getPosition();
    if(position.z != 0.0f)
        setPosition(Ogre::Vector3(position.x, position.y, 0.0f));
}

//! \brief Moves the restarted jump to the saved turn and tells the clients where it is now.
void Creature::resumeJump(uint32_t turnsLeft)
{
    if((mJumpTurnsLeft == 0) || (turnsLeft == 0) || (turnsLeft >= mJumpTurns))
        return;

    mJumpTurnsLeft = turnsLeft;
    mJumpElapsed = static_cast<Ogre::Real>(mJumpTurns - mJumpTurnsLeft);
    setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
    sendJumpNotification();
}

//! \brief One step of the jump: the position on the arc after the turns that have passed.
void Creature::continueJump()
{
    if(mJumpTurnsLeft == 0)
        return;

    --mJumpTurnsLeft;
    mJumpElapsed = static_cast<Ogre::Real>(mJumpTurns - mJumpTurnsLeft);
    setPosition(jumpPosition(mJumpFrom, mJumpTo, mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns)));
}

//! \brief Takes over the arc that the server told and shows the Jump clip.
void Creature::startJumpFromServer(const Ogre::Vector3& from, const Ogre::Vector3& to, uint32_t turns, Ogre::Real elapsed)
{
    mJumpFrom = from;
    mJumpTo = to;
    mJumpTurns = std::max<uint32_t>(1, turns);
    mJumpElapsed = elapsed;
    mJumpTurnsLeft = 1;
    setAnimationState(EntityAnimation::jump_anim, false, Ogre::Vector3::ZERO, false);
    setPosition(jumpPosition(from, to, elapsed / static_cast<Ogre::Real>(mJumpTurns)));
    showJumpClipPhase();
}

//! \brief Puts the Jump clip at the phase of the arc, so a jump that is already running when the client learns of it
//! (loaded game, seat that gains sight) goes on in the middle of the clip instead of starting it again.
void Creature::showJumpClipPhase()
{
    if((getAnimationState() != nullptr) && (getAnimationState()->getAnimationName() == EntityAnimation::jump_anim))
        getAnimationState()->setTimePosition(static_cast<Ogre::Real>(JUMP_CLIP_SECONDS) * mJumpElapsed / static_cast<Ogre::Real>(mJumpTurns));
}

//! \brief Tells the human seats that see the creature about the jump that has just started (name, from, to, turns
//! and elapsed; the pattern of the rooster hop).
void Creature::sendJumpNotification()
{
    for(Seat* seat : mSeatsWithVisionNotified)
        sendJumpNotificationTo(seat);
}

//! \brief Tells one human seat about the jump that is running: name, from, to, turns and the turns passed so far.
void Creature::sendJumpNotificationTo(Seat* seat)
{
    if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
        return;

    ServerNotification* notification = new ServerNotification(
        ServerNotificationType::creatureJump, seat->getPlayer());
    notification->mPacket << getName() << mJumpFrom << mJumpTo << mJumpTurns << mJumpElapsed;
    ODServer::getSingleton().queueServerNotification(notification);
}

//! \brief Notes that the creature falls asleep drunk, so it wakes up with a hangover.
void Creature::sleepStarted()
{
    mHangoverPending = (mDrunk > 0.0) &&
        (mDrunk > ConfigManager::getSingleton().getTavernConfigDouble("HangoverAt"));
}

//! \brief Starts the hangover of a creature that slept drunk; a running hangover is not shortened.
void Creature::sleepEnded()
{
    if(!mHangoverPending)
        return;

    mHangoverPending = false;
    ConfigManager& config = ConfigManager::getSingleton();
    double hangoverTurns = config.getTavernConfigDouble("HangoverTurns");
    mHangoverTurns = std::max(mHangoverTurns, hangoverTurns);
    addTavernMood(config.getTavernConfigDouble("HangoverMood"), hangoverTurns);
}

//! \brief Sets the turns until the next leisure visit to a tavern (not below 0).
void Creature::setTavernCooldownTurns(int32_t turns)
{
    mTavernCooldownTurns = std::max(0, turns);
}

//! \brief The creature just left a tavern: no leisure visit for TavernLeisureCooldownTurns turns.
void Creature::startTavernCooldown()
{
    setTavernCooldownTurns(static_cast<int32_t>(ConfigManager::getSingleton().getRoomConfigDouble("TavernLeisureCooldownTurns")));
}

//! \brief Lets the drunkenness fall, resets the vomit mark when sober enough and counts down mood, hangover and the leisure cooldown.
void Creature::upkeepTavernState()
{
    if(mTavernCooldownTurns > 0)
        --mTavernCooldownTurns;

    // Nothing to count for a creature that never visited a tavern
    if((mDrunk <= 0.0) && !mVomited && (mTavernMoodTurns <= 0.0) && (mTavernMood == 0.0) && (mHangoverTurns <= 0.0))
        return;

    ConfigManager& config = ConfigManager::getSingleton();
    if(mDrunk > 0.0)
        mDrunk = std::max(0.0, mDrunk - config.getTavernConfigDouble("DrunkDecayPerTurn"));

    // The next drunk episode vomits again
    if(mVomited && (mDrunk < config.getTavernConfigDouble("VomitAt")))
        mVomited = false;

    // The tavern mood lasts for its turns, then it is gone
    if(mTavernMoodTurns > 0.0)
        mTavernMoodTurns -= 1.0;
    if(mTavernMoodTurns <= 0.0)
    {
        mTavernMoodTurns = 0.0;
        mTavernMood = 0.0;
    }

    if(mHangoverTurns > 0.0)
        mHangoverTurns = std::max(0.0, mHangoverTurns - 1.0);
}

//! \brief Hook for a later bathing room: the creature carries no dirt anymore.
void Creature::washed()
{
    mCreatureDirt = 0.0;
}

//! \brief Raises the urge, limited to NEED_MAX; rogue creatures have none.
void Creature::increaseUrge(double value)
{
    if(getSeat()->isRogueSeat())
        return;

    mUrge = std::min(NEED_MAX, mUrge + value);
}

//! \brief The creature relieves itself where it stands (see CreatureActionUseToilet).
void Creature::relieve()
{
    pushAction(Utils::make_unique<CreatureActionUseToilet>(*this, nullptr));
}

//! \brief Relieves the creature at the highest urge and lets it use a toilet seat it walks over from UrgeOnTheWay on.
void Creature::handleUrge()
{
    if(isActionInList(CreatureActionType::infirmaryRest) ||
        (isActionInList(CreatureActionType::sleep) && getHP() * 100.0 < getMaxHp() *
            ConfigManager::getSingleton().getRoomConfigDouble("DormitoryWoundedCarryHpPercent")))
        return;
    ConfigManager& config = ConfigManager::getSingleton();
    if(mDefinition->isWorker() || (mUrge < config.getDirtConfigDouble("UrgeOnTheWay")))
        return;

    Seat* seat = getSeat();
    if((seat == nullptr) || seat->isRogueSeat() || !getIsOnMap() || !isAlive())
        return;

    // Not while held in the hand, dragged, KO or controlled by a player: at the first turn after that
    if(mIsInHand || mIsBeingDragged || isKo() || isPossessed())
        return;

    // A creature on a toilet seat (or already relieving itself) is busy, and a fight comes first
    if(isActionInList(CreatureActionType::useToilet) || isActionInList(CreatureActionType::fight) ||
       isActionInList(CreatureActionType::fightFriendly))
        return;

    if(mUrge >= config.getDirtConfigDouble("UrgeRelieve"))
    {
        relieve();
        return;
    }

    // From UrgeOnTheWay on, a free toilet seat of a room the creature may use is used when the creature walks over it
    if(mActions.empty() || (mActions.back()->getType() != CreatureActionType::walkToTile))
        return;

    Tile* tile = getPositionTile();
    if(tile == nullptr)
        return;

    Room* room = tile->getCoveringRoom();
    if((room == nullptr) || (room->getType() != RoomType::toilet))
        return;

    RoomToilet* toilet = static_cast<RoomToilet*>(room);
    if(toilet->canBeUsedBy(*this) && toilet->isTileFree(tile, this))
        pushAction(Utils::make_unique<CreatureActionUseToilet>(*this, tile));
}

//! \brief Sets the urge, limited to 0 - NEED_MAX.
void Creature::setUrge(double val)
{
    mUrge = std::min(NEED_MAX, std::max(0.0, val));
}

//! \brief Raises the creature dirt, limited to NEED_MAX.
void Creature::increaseCreatureDirt(double value)
{
    mCreatureDirt = std::min(NEED_MAX, mCreatureDirt + value);
}

//! \brief Sets the creature dirt, limited to 0 - NEED_MAX.
void Creature::setCreatureDirt(double val)
{
    mCreatureDirt = std::min(NEED_MAX, std::max(0.0, val));
}

//! \brief Prison and torture make the creature filthy, otherwise the dirt it carries decays a little every turn.
void Creature::upkeepCreatureDirt()
{
    if(isInPrison() || mTorturedThisTurn)
        mCreatureDirt = NEED_MAX;

    if(mCreatureDirt <= 0.0)
        return;

    double decay = ConfigManager::getSingleton().getDirtConfigDouble("CreatureDirtDecayPerTurn");
    mCreatureDirt = std::max(0.0, mCreatureDirt - decay);
}

//! \brief Adds the trail dirt of this creature to the tile it entered: TrailDirtPerTile times DirtFactor for a load
//! carried or a pulled wounded creature (the DirtFactor of the worker that pulls it), plus the share of it that the creature dirt makes.
//! A creature that just left a mud bath also leaves its share of the mud on each of the next tiles outside a pool.
void Creature::dirtyEnteredTile(Tile* tile)
{
    if((tile == nullptr) || (mDefinition == nullptr))
        return;

    // A creature that left a mud bath carries mud out: each of the next SpaMudTrailTiles tiles outside a pool gets an
    // equal share of SpaDirtPerBath times the DirtFactor; the creature dirt itself does not change
    if((mSpaMudTilesLeft > 0) && !RoomSpa::isPoolTile(tile))
    {
        const ConfigManager& config = ConfigManager::getSingleton();
        tile->addDirt(config.getRoomConfigDouble("SpaDirtPerBath") / config.getRoomConfigDouble("SpaMudTrailTiles") *
            mDefinition->getDirtFactor());
        --mSpaMudTilesLeft;
    }

    if((mCarriedEntity == nullptr) && !mIsBeingDragged && (mCreatureDirt <= 0.0))
        return;

    double trailDirt = ConfigManager::getSingleton().getDirtConfigDouble("TrailDirtPerTile");
    double share = mCreatureDirt / CREATURE_DIRT_SHARE_DIVISOR;
    if((mCarriedEntity != nullptr) || mIsBeingDragged)
        share += 1.0;

    // A pulled creature leaves the trail of the worker that pulls it, so the DirtFactor of the puller counts
    double dirtFactor = mIsBeingDragged ? mDragDirtFactor : mDefinition->getDirtFactor();
    tile->addDirt(trailDirt * share * dirtFactor);
}

//! \brief A corpse adds CombatDirtPerHit to the tile it lies on every turn.
void Creature::dirtyTileByCorpse()
{
    Tile* tile = getPositionTile();
    if(tile == nullptr)
        return;

    tile->addDirt(ConfigManager::getSingleton().getDirtConfigDouble("CombatDirtPerHit"));
}

void Creature::decreaseWakefulness(double value)
{
    if(getSeat()->isRogueSeat())
        return;

    mWakefulness = std::max(0.0, mWakefulness - value);
}

//! \brief Applies the admission mood using the configured fee modifier and rested lifetime.
void Creature::setInfirmaryAdmissionMood(bool creaturePaid)
{
    mInfirmaryMood = 0.0;
    mInfirmaryMoodTurns = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryMoodDefaultTurns");
    for(const CreatureMood* mood : getDefinition()->getCreatureMoods())
    {
        const CreatureMoodFee* fee = dynamic_cast<const CreatureMoodFee*>(mood);
        if(fee != nullptr)
            mInfirmaryMood = ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryMoodWageShare") *
                fee->getMoodModifier() * (creaturePaid ? 1.0 : -1.0);
        const CreatureMoodRested* rested = dynamic_cast<const CreatureMoodRested*>(mood);
        if(rested != nullptr)
            mInfirmaryMoodTurns = rested->getTurnsMax();
    }
}

void Creature::addCasinoMood(double points)
{
    double maxPoints = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("CasinoMoodMax", 1500.0);
    mCasinoMood = std::max(-maxPoints, std::min(maxPoints, mCasinoMood + points));
}

void Creature::addPitMood(double points)
{
    double maxPoints = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("PitMoodMax", DEFAULT_PIT_MOOD_MAX);
    mPitMood = std::max(-maxPoints, std::min(maxPoints, mPitMood + points));
}

bool Creature::isGoodAligned() const
{
    const std::vector<std::string>& heroClasses = ConfigManager::getSingleton().getFactionSpawnPool("Hero");
    return std::find(heroClasses.begin(), heroClasses.end(), mDefinition->getClassName()) != heroClasses.end();
}

bool Creature::isHatedCompanyNear() const
{
    // Only creatures that have moods can be annoyed
    if(mDefinition->getCreatureMoods().empty() || !getIsOnMap() || !isAlive())
        return false;

    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return false;

    bool isGood = isGoodAligned();
    double radius = ConfigManager::getSingleton().getRoomConfigDoubleOrDefault("HatedCompanyRadius", DEFAULT_HATED_COMPANY_RADIUS);
    double squaredRadius = radius * radius;
    const std::vector<Creature*>& creatures = getGameMap()->getCreatures();
    for(Creature* other : creatures)
    {
        if((other == this) || !other->isAlive() || !other->getIsOnMap())
            continue;

        // Workers have no alignment
        if(other->getDefinition()->isWorker())
            continue;

        if(!getSeat()->isAlliedSeat(other->getSeat()))
            continue;

        if(other->isGoodAligned() == isGood)
            continue;

        Tile* otherTile = other->getPositionTile();
        if(otherTile == nullptr)
            continue;

        if(Pathfinding::squaredDistanceTile(*myTile, *otherTile) <= squaredRadius)
            return true;
    }
    return false;
}

void Creature::addPrayerRelief(int32_t relief, int32_t maxRelief)
{
    mPrayerRelief = std::min(mPrayerRelief + relief, maxRelief);
}

void Creature::removeAnnoyance()
{
    mNbTurnsInHand = 0;
    mNbTurnsOutOfWork = 0;
    mNbTurnsTortureMood = 0;
    mNbTurnsWithoutBattle = 0;
    mSlapTurns.clear();
    mSpecialMood = 0;
    // What is left (hunger, tiredness, wounds, unpaid wage) is cancelled for a while, it builds up again
    int32_t points = CreatureMoodManager::computeCreatureMoodModifiers(*this);
    mSpecialMood = std::max(0, -points);
    mMoodCooldownTurns = 0;
}

void Creature::makeUnhappy()
{
    mSpecialMood = 0;
    int32_t points = CreatureMoodManager::computeCreatureMoodModifiers(*this);
    // The middle of the angry level
    int32_t target = (ConfigManager::getSingleton().getCreatureMoodAngry()
        + ConfigManager::getSingleton().getCreatureMoodFurious()) / 2;
    int32_t wanted = target - ConfigManager::getSingleton().getCreatureBaseMood() - points;
    mSpecialMood = std::min(0, wanted);
    mMoodCooldownTurns = 0;
}

void Creature::computeMood()
{
    mMoodPoints = CreatureMoodManager::computeCreatureMoodModifiers(*this);

    CreatureMoodLevel oldMoodValue = mMoodValue;
    mMoodValue = CreatureMoodManager::getCreatureMoodLevel(mMoodPoints);
    if(mMoodValue == oldMoodValue)
        return;

    mNeedFireRefresh = true;

    fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::moodStage), static_cast<int32_t>(mMoodValue),
        static_cast<int32_t>(oldMoodValue), true);

    // The anger fell below the angry level while the relief of a prayer in the temple was working: calmed
    if((oldMoodValue >= CreatureMoodLevel::Angry) && (mMoodValue < CreatureMoodLevel::Angry) &&
       (mMoodValue != CreatureMoodLevel::Unknown) && (mPrayerRelief > 0))
    {
        fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::calmed), static_cast<int32_t>(mMoodValue),
            static_cast<int32_t>(oldMoodValue), true);
    }

    if((mMoodValue >= CreatureMoodLevel::Furious) &&
       (oldMoodValue < CreatureMoodLevel::Furious))
    {
        // We became unhappy
        fireChatMsgFurious();
    }
    else if((mMoodValue > CreatureMoodLevel::Neutral) &&
       (oldMoodValue <= CreatureMoodLevel::Neutral))
    {
        // We became unhappy
        fireChatMsgUnhappy();
    }
}

void Creature::computeCreatureOverlayHealthValue()
{
    if(!getIsOnServerMap())
        return;

    uint32_t value = 0;
    double hp = getHP();
    // Note that we make a special case for hp = 0 to avoid errors due to roundness
    if(hp <= 0)
    {
        value = NB_OVERLAY_HEALTH_VALUES - 1;
    }
    else
    {
        uint32_t nbSteps = NB_OVERLAY_HEALTH_VALUES - 2;
        double healthStep = getMaxHp() / static_cast<double>(nbSteps);
        double tmpHealth = getMaxHp();
        for(value = 0; value < nbSteps; ++value)
        {
            if(hp >= tmpHealth)
                break;

            tmpHealth -= healthStep;
        }
    }

    if(mOverlayHealthValue != value)
    {
        mOverlayHealthValue = value;
        mNeedFireRefresh = true;
    }
}

void Creature::computeCreatureOverlayMoodValue()
{
    if(!getIsOnServerMap())
        return;

    uint32_t value = 0;
    // The creature mood applies only if the creature is alive
    if(isAlive())
    {
        switch(mMoodValue)
        {
            case CreatureMoodLevel::Angry:
                value |= CreatureMoodValues::Angry;
                break;
            case CreatureMoodLevel::Furious:
                value |= CreatureMoodValues::Furious;
                break;
            default:
                break;
        }

        // We update the mood bit array according to actions in the list
        for (const std::unique_ptr<CreatureAction>& ca : mActions)
            value |= ca.get()->updateMoodModifier();

        if(mKoTurnCounter < 0)
            value |= CreatureMoodValues::KoDeath;
        else if(mKoTurnCounter > 0)
            value |= CreatureMoodValues::KoTemp;

        if(isHungry())
            value |= CreatureMoodValues::Hungry;

        if(isTired())
            value |= CreatureMoodValues::Tired;

        if(mSeatPrison != nullptr)
            value |= CreatureMoodValues::InJail;
    }

    if(mOverlayMoodValue != value)
    {
        mOverlayMoodValue = value;
        mNeedFireRefresh = true;
    }
}

//! \brief Adds an effect to the creature. A strength, speed or defense effect of a source that already has a running
//! effect only refreshes the running one.
void Creature::addCreatureEffect(CreatureEffect* effect)
{
    if(effect->getEffectName() == EFFECT_NAME_SPEED || effect->getEffectName() == "Frozen")
        effect->startEffect(*this);
    // A strength, speed or defense effect that a running effect of the same source already provides only refreshes the
    // running one: the same skill or spell cast again does not stack
    if(isStackingEffect(*effect))
    {
        const std::string refreshKey = effectRefreshKey(*effect);
        for(EntityParticleEffect* entityEffect : mEntityParticleEffects)
        {
            if(entityEffect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
                continue;

            CreatureParticleEffect* running = static_cast<CreatureParticleEffect*>(entityEffect);
            if(running->mEffect->getEffectName() != effect->getEffectName() ||
               running->mEffect->getNbTurnsEffect() == 0.0 || effectRefreshKey(*running->mEffect) != refreshKey)
            {
                continue;
            }

            running->mEffect->mNbTurnsEffect = effect->getNbTurnsEffect();
            running->mNbTurnsEffect = static_cast<int32_t>(std::ceil(effect->getNbTurnsEffect()));
            delete effect;
            mNeedFireRefresh = true;
            return;
        }
    }

    std::string effectName = nextParticleSystemsName();

    OD_LOG_INF("Added CreatureEffect name=" + effectName + " on creature=" + getName());

    CreatureParticleEffect* particleEffect = new CreatureParticleEffect(*this, effectName, effect->getParticleEffectScript(),
        static_cast<int32_t>(std::ceil(effect->getNbTurnsEffect())), effect);
    mEntityParticleEffects.push_back(particleEffect);

    mNeedFireRefresh = true;
}

void Creature::addParticleEffect(const std::string& effectScript, int32_t nbTurns)
{
    EntityParticleEffect* effect = new EntityParticleEffect(
        nextParticleSystemsName(), effectScript, nbTurns);
    mEntityParticleEffects.push_back(effect);
}

bool Creature::removeCreatureEffect(CreatureEffect* effectForDeletion)
{
    mNeedFireRefresh = false;
    for(std::vector<EntityParticleEffect*>::iterator it =  mEntityParticleEffects.begin(); it != mEntityParticleEffects.end(); ++it)
    {
        CreatureParticleEffect* effect = static_cast<CreatureParticleEffect*>(*it);
        if(effect->mEffect == effectForDeletion)
        {
            effect->mNbTurnsEffect = 0 ;
            effect->mEffect->mNbTurnsEffect = 0 ;
            mNeedFireRefresh = true;
            return true;
        }
        
    }
    return false;
}

bool Creature::isDefector() const
{
    for(const EntityParticleEffect* effect : mEntityParticleEffects)
    {
        if(effect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        const CreatureParticleEffect* creatureEffect = static_cast<const CreatureParticleEffect*>(effect);
        if((creatureEffect->mEffect->getEffectName() == "Defector") &&
           (creatureEffect->mEffect->getNbTurnsEffect() > 0))
        {
            return true;
        }
    }

    return false;
}

bool Creature::isHexenHen() const
{
    if(!getIsOnServerMap())
        return mIsHexenHen;

    for(const EntityParticleEffect* effect : mEntityParticleEffects)
    {
        if(effect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        const CreatureParticleEffect* creatureEffect = static_cast<const CreatureParticleEffect*>(effect);
        if((creatureEffect->mEffect->getEffectName() == "HexenHen") &&
           (creatureEffect->mEffect->getNbTurnsEffect() > 0))
        {
            return true;
        }
    }

    return false;
}

bool Creature::isFrozen() const
{
    if(!getIsOnServerMap())
        return false;

    for(const EntityParticleEffect* effect : mEntityParticleEffects)
    {
        if(effect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        const CreatureParticleEffect* creatureEffect = static_cast<const CreatureParticleEffect*>(effect);
        if((creatureEffect->mEffect->getEffectName() == "Frozen") &&
           (creatureEffect->mEffect->getNbTurnsEffect() > 0))
        {
            return true;
        }
    }

    return false;
}

bool Creature::isInvisible() const
{
    if(!getIsOnServerMap())
        return false;

    for(const EntityParticleEffect* effect : mEntityParticleEffects)
    {
        if(effect->getEntityParticleEffectType() != EntityParticleEffectType::creature)
            continue;

        const CreatureParticleEffect* creatureEffect = static_cast<const CreatureParticleEffect*>(effect);
        if((creatureEffect->mEffect->getEffectName() == "Invisible") &&
           (creatureEffect->mEffect->getNbTurnsEffect() > 0))
        {
            return true;
        }
    }

    return false;
}

const std::string& Creature::getCurrentMeshName() const
{
    static const std::string chickenMeshName = "Chicken.mesh";
    if(isHexenHen())
        return chickenMeshName;

    return getDefinition()->getMeshName();
}

void Creature::updateHexenHenMesh()
{
    if(getIsOnServerMap() || !isMeshExisting() || !getIsOnMap())
        return;

    if(mHexenHenMeshShown == mIsHexenHen)
        return;

    destroyMeshWeapons();
    mHexenHenMeshShown = mIsHexenHen;
    RenderManager::getSingleton().rrChangeCreatureMesh(this);
    createMeshWeapons();
    RenderManager::getSingleton().rrScaleCreature(*this);
}

void Creature::handleHexenHenUpkeep()
{
    if(!mActions.empty())
    {
        clearActionQueue();
        clearDestinations(EntityAnimation::idle_anim, true, true);
    }

    if(isMoving())
        return;

    if(Random::Int(0, 3) != 0)
        return;

    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return;

    Tile* destTile = getGameMap()->getTile(myTile->getX() + Random::Int(-2, 2), myTile->getY() + Random::Int(-2, 2));
    // The wandering target must be a tile with a free standing point, not one covered by furniture
    if((destTile == nullptr) || (destTile == myTile) || !canGoThroughTile(destTile) ||
       !RoomObjectNavigation::hasStandingPosition(*this, *destTile))
        return;

    std::list<Tile*> tempPath = getGameMap()->path(this, destTile);
    if(tempPath.empty())
        return;

    std::vector<Ogre::Vector2> path;
    tileToVector2(tempPath, path, true, 0.0);
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true);
}

bool Creature::isHurt() const
{
    //On server side, we test HP
    if(getIsOnServerMap())
        return getHP() < getMaxHp();

    // On client side, we test overlay value. 0 represents full health
    return mOverlayHealthValue > 0;
}

bool Creature::isKo() const
{
    if(getIsOnServerMap())
        return mKoTurnCounter != 0;

    // On client side, we test mood overlay value
    return (mOverlayMoodValue & CreatureMoodValues::KoDeathOrTemp) != 0;
}

bool Creature::isKoDeath() const
{
    if(getIsOnServerMap())
        return mKoTurnCounter < 0;

    // On client side, we test mood overlay value
    return (mOverlayMoodValue & CreatureMoodValues::KoDeath) != 0;
}

bool Creature::isKoTemp() const
{
    if(getIsOnServerMap())
        return mKoTurnCounter > 0;

    // On client side, we test mood overlay value
    return (mOverlayMoodValue & CreatureMoodValues::KoTemp) != 0;
}

bool Creature::isInPrison() const
{
    return mSeatPrison != nullptr;
}

void Creature::correctEntityMovePosition(Ogre::Vector2& position)
{
    static const double offset = 0.3;
    if(position.x > 0)
        position.x += Random::Double(-offset, offset);

    if(position.y > 0)
        position.y += Random::Double(-offset, offset);

    // if(position.z > 0)
    //     position.z += Random::Double(-offset, offset);
}

void Creature::checkWalkPathValid(bool includeWalkDistortion)
{
    bool stop = false;
    for(const Ogre::Vector2& dest : mWalkQueue)
    {
        Tile* tile = getGameMap()->getTile(Helper::round(dest.x), Helper::round(dest.y));
        if(tile == nullptr)
        {
            stop = true;
            break;
        }

        if(!canGoThroughTile(tile))
        {
            stop = true;
            break;
        }
    }

    if(!stop && getIsOnServerMap())
        stop = RoomObjectNavigation::blocked(*this,
            std::vector<Ogre::Vector2>(mWalkQueue.begin(), mWalkQueue.end()), includeWalkDistortion);

    if(!stop)
        return;

    // There is an unpassable tile in our way. We stop what we are doing
    clearDestinations(EntityAnimation::idle_anim, true, true);
}

//! \brief Reports the one-upkeep interval after a worker step; action scheduling remains unchanged.
void Creature::recordWorkerStepRecovery()
{
    mAttackRecoveryDuration = 1;
    mAttackRecoveryTurns = mAttackRecoveryDuration;
    ++mAttackRecoverySerial;
    mNeedFireRefresh = true;
}

void Creature::setJobCooldown(int val)
{
    // If the creature has been slapped, its cooldown is decreased
    if(hasSlapEffect())
        val = Helper::round(static_cast<float>(val) * 0.8f);

    mJobCooldown = val;
    mJobCooldownDuration = static_cast<uint32_t>(std::max(0, val));
    if(val > 0)
        ++mAttackRecoverySerial;
    mNeedFireRefresh = true;
}

bool Creature::isTired() const
{
    if(getIsOnServerMap())
        return mWakefulness <= ConfigManager::getSingleton().getTiredWakefulness();

    return (mOverlayMoodValue & CreatureMoodValues::Tired) != 0;
}

bool Creature::isHungry() const
{
    if(getIsOnServerMap())
        return mHunger >= 80.0;

    return (mOverlayMoodValue & CreatureMoodValues::Hungry) != 0;
}

//! \brief Ends knockout state and permits one item drop in the next fight.
void Creature::resetKoTurns()
{
    if(getIsOnServerMap())
        getGameMap()->getLevelScript().clearFatalShot(getName());
    mKoTurnCounter = 0;
    mKoDroppedThisFight = false;
    mNeedFireRefresh = true;
}

void Creature::knockOutToDeath()
{
    if(mKoTurnCounter < 0)
        return;

    mKoTurnCounter = -ConfigManager::getSingleton().getNbTurnsKoCreatureAttacked() *
        ItemEffects::remainingFactor(*this, "QuickRise");
    OD_LOG_INF("creature=" + getName() + " has been knocked out");
    dropCarriedEquipment();
    computeCreatureOverlayMoodValue();
    mNeedFireRefresh = true;
}

//! \brief Stuns a living creature for the resisted duration without replacing a longer stun.
void Creature::stun(int32_t nbTurns)
{
    if(!isAlive() || (nbTurns <= 0) || (mKoTurnCounter < 0))
        return;

    const double resisted = nbTurns * ItemEffects::remainingFactor(*this, "ThickSkull") *
        ItemEffects::remainingFactor(*this, "Steadfast");
    mKoTurnCounter = std::max(mKoTurnCounter, resisted);
    computeCreatureOverlayMoodValue();
    clearActionQueue();
    mNeedFireRefresh = true;
}

void Creature::setInJail(Room* prison)
{
    if(prison == nullptr)
    {
        if(mSeatPrison == nullptr)
            return;

        mSeatPrison = nullptr;
        mNeedFireRefresh = true;
        return;
    }

    // Creature is set in prison
    if(mSeatPrison == prison->getSeat())
        return;

    mSeatPrison = prison->getSeat();
    mNeedFireRefresh = true;
}

double Creature::getThreat() const
{
    // Threat multiplier in percent for the levels 1 to 10. Above level 10 the last
    // step of the table (100 percent per level) is continued.
    static const double THREAT_PERCENT_BY_LEVEL[10] = {100.0, 125.0, 150.0, 175.0, 200.0, 225.0, 250.0, 300.0, 400.0, 500.0};
    unsigned int level = (mLevel < 1) ? 1 : mLevel;
    double percent;
    if(level <= 10)
        percent = THREAT_PERCENT_BY_LEVEL[level - 1];
    else
        percent = THREAT_PERCENT_BY_LEVEL[9] + 100.0 * static_cast<double>(level - 10);

    return mHp * percent / 100.0;
}

bool Creature::isDangerous(const Creature* creature, int distance) const
{
    if(getDefinition()->isWorker())
        return false;

    if(isHexenHen())
        return false;

    return true;
}

void Creature::clientUpkeep()
{
    MovableGameEntity::clientUpkeep();
    if(mDropCooldown > 0)
        --mDropCooldown;
}

//! \brief Sets the speed modifier of the effects and recomputes the move speeds (the move% passives included).
void Creature::setMoveSpeedModifier(double modifier)
{
    mSpeedModifier = modifier;

    mGroundSpeed = mDefinition->getMoveSpeedGround();
    mWaterSpeed = mDefinition->getMoveSpeedWater();
    mLavaSpeed  = mDefinition->getMoveSpeedLava();

    double multiplier = mLevel - 1;
    if (multiplier > 0.0)
    {
        mGroundSpeed += mDefinition->getGroundSpeedPerLevel() * multiplier;
        mWaterSpeed += mDefinition->getWaterSpeedPerLevel() * multiplier;
        mLavaSpeed += mDefinition->getLavaSpeedPerLevel() * multiplier;
    }

    // The move% passives raise every speed
    const double speedFactor = mSpeedModifier * (1.0 + getSkillPassive("move%") / 100.0);
    mGroundSpeed *= speedFactor;
    mWaterSpeed *= speedFactor;
    mLavaSpeed *= speedFactor;
    mNeedFireRefresh = true;
}

void Creature::clearMoveSpeedModifier()
{
    setMoveSpeedModifier(1.0);
}

//! \brief Adds temporary defense bonuses to the same natural combat curves used by stat creation.
void Creature::setDefenseModifier(double phy, double mag, double ele)
{
    mPhysicalDefense = CreatureProgression::combatStat(mDefinition->getPhysicalDefense(),
        mDefinition->getPhysicalDefPerLevel(), mLevel, CreatureProgression::damageMultiplier);
    mMagicalDefense = CreatureProgression::combatStat(mDefinition->getMagicalDefense(),
        mDefinition->getMagicalDefPerLevel(), mLevel, CreatureProgression::damageMultiplier);
    mElementDefense = CreatureProgression::combatStat(mDefinition->getElementDefense(),
        mDefinition->getElementDefPerLevel(), mLevel, CreatureProgression::damageMultiplier);

    mPhysicalDefense += phy;
    mMagicalDefense += mag;
    mElementDefense += ele;

    // Improve the stats to the current level through the natural combat curves above.

    mNeedFireRefresh = true;
}

void Creature::clearDefenseModifier()
{
    setDefenseModifier(0.0, 0.0, 0.0);
}

void Creature::setStrengthModifier(double modifier)
{
    mModifierStrength = modifier;
    // Since strength is not used on client side, no need to send it
}

void Creature::clearStrengthModifier()
{
    setStrengthModifier(1.0);
}

bool Creature::isWarmup() const
{
    for(const CreatureSkillData& skillData : mSkillData)
    {
        if(skillData.mWarmup > 0.0)
            return true;
    }

    return false;
}

void Creature::fight()
{
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    bool ko = getSeat()->getKoCreatures();
    pushAction(Utils::make_unique<CreatureActionFight>(*this, nullptr, ko, true));
}

void Creature::fightCreature(Creature& creature, bool ko, bool notifyPlayerIfHit)
{
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionFight>(*this, &creature, ko, notifyPlayerIfHit));
}

void Creature::flee()
{
    recordScriptEvent(*this, "afraid");
    fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::scared), 0, 0, false);
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionFlee>(*this));
}

//! \brief Starts fear flight, optionally playing the ghost flinch before moving.
void Creature::fleeFromTile(Tile* fearTile, double nbTurns, bool scaredPose)
{
    // Fear breaks the possession of the creature
    if(isPossessed())
        endPossession();

    recordScriptEvent(*this, "afraid");
    fireCosmeticEvent(static_cast<int32_t>(CosmeticEventType::scared), 1, 0, false);
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionFlee>(*this, fearTile, nbTurns, scaredPose));
    if(scaredPose)
        setAnimationState("Scared", false, Ogre::Vector3::ZERO, false);
}

//! \brief Applies a resisted temporary stun while retaining fractional duration.
void Creature::stunForTurns(int32_t nbTurns)
{
    // Only living creatures that are not already KO can be stunned
    if(!isAlive() || (mKoTurnCounter != 0))
        return;

    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    mKoTurnCounter = nbTurns * ItemEffects::remainingFactor(*this, "ThickSkull") *
        ItemEffects::remainingFactor(*this, "Steadfast");
    computeCreatureOverlayMoodValue();
}

void Creature::sleep()
{
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionSleep>(*this));
}

void Creature::leaveDungeon()
{
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    pushAction(Utils::make_unique<CreatureActionLeaveDungeon>(*this));
}

void Creature::changeSeat(Seat* newSeat)
{
    OD_LOG_INF("creature=" + getName() + " changes side from seatId=" + Helper::toString(getSeat()->getId()) + " to seatId=" + Helper::toString(newSeat->getId()));
    OD_ASSERT_TRUE_MSG(getSeat() != newSeat, "creature=" + getName() + ", seatId=" + Helper::toString(newSeat->getId()));
    // A neutral creature that joins a keeper is claimed
    if(getSeat()->isRogueSeat() && !newSeat->isRogueSeat())
        recordScriptEvent(*this, "claimed");

    setSeat(newSeat);
    if(getGameMap()->isRelationshipsEnabled())
        getGameMap()->getCreatureRelationships()->removeCreature(getName());
    mMoodValue = CreatureMoodLevel::Neutral;
    mMoodPoints = 0;
    mPrayerRelief = 0;
    mSpecialMood = 0;
    mRelationshipTempMood = 0;
    mRageUntilTurn = 0;
    mBrawlResumeOpponent.clear();
    mWakefulness = 100;
    mHunger = 0;
    mThirst = 0.0;
    mTavernMood = 0.0;
    mTavernMoodTurns = 0.0;
    mDrunk = 0.0;
    mVomited = false;
    mHangoverTurns = 0.0;
    mTavernCooldownTurns = 0;
    mHangoverPending = false;
    mSpaMood = 0.0;
    mRelaxTurns = 0.0;
    mSpaMudTilesLeft = 0;
    mSpaBathing = false;
    mUrge = 0.0;
    mNbTurnsTorture = 0;
    mNbTurnsPrison = 0;
    mActiveSlapsCount = 0;
    mNbTurnsInHand = 0;
    mIsInHand = false;
    mNbTurnsOutOfWork = 0;
    mNbTurnsTortureMood = 0;
    mNbTurnsRested = 0;
    mNbTurnsHatedCompany = 0;
    mPitMood = 0.0;
    mTorturedThisTurn = false;
    mRestedThisTurn = false;
    mSlapTurns.clear();
    mCasinoMood = 0.0;
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
    mNeedFireRefresh = true;
    if (getHomeTile() != nullptr)
    {
        RoomDormitory* home = static_cast<RoomDormitory*>(getHomeTile()->getCoveringBuilding());
        home->releaseTileForSleeping(getHomeTile(), this);
    }
}

void Creature::stopWalking()
{
    if(parkingBit)
        parkedBit = true;
    MovableGameEntity::stopWalking();
}

void Creature::teleportTo(Tile* tile)
{
    if((tile == nullptr) || !getIsOnServerMap() || !getIsOnMap())
        return;

    clearDestinations(EntityAnimation::idle_anim, true, true);

    Ogre::Vector3 dest = tile->getPosition();
    setPosition(dest);

    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr)
            continue;
        if(!seat->getPlayer()->getIsHuman())
            continue;

        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::entityTeleported, seat->getPlayer());
        serverNotification->mPacket << getName() << dest;
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }

    if(getHasVisualDebuggingEntities())
        computeVisualDebugEntities();
    mNeedFireRefresh = true;
}

Tile* Creature::getWalkDestinationTile() const
{
    if(mWalkQueue.empty())
        return nullptr;

    const Ogre::Vector2& destination = mWalkQueue.back();
    return getGameMap()->getTile(Helper::round(destination.x), Helper::round(destination.y));
}

//! \brief Reserves an intact dead body for Raise Dead and removes it on the next upkeep.
bool Creature::takeCorpse()
{
    if(!getIsOnServerMap() || !getIsOnMap() || isAlive() || getDefinition()->isWorker())
        return false;

    // The counter is 0 until death drops and notices have run; consumption is deferred safely.
    if(mDeathCounter == 0 || mDeathCounter == std::numeric_limits<unsigned int>::max() ||
       mDecayTurns >= 0.0 || mIsCarried)
        return false;

    mDeathCounter = std::numeric_limits<unsigned int>::max();
    return true;
}


//! \brief Restores a delivered crypt corpse's life and needs after freeing its grave reservation.
bool Creature::reviveFromCorpse(double hpShare)
{
    if(!getIsOnServerMap() || isAlive() || getDefinition()->isWorker() || mIsCarried ||
       mDeathCounter == 0 || mDeathCounter == std::numeric_limits<unsigned int>::max())
        return false;
    Tile* tile = getPositionTile();
    Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
    if(room == nullptr || room->getType() != RoomType::crypt || room->getSeat() != getSeat())
        return false;
    RoomCrypt* crypt = static_cast<RoomCrypt*>(room);
    if(crypt->getCorpseSpot(*this) == nullptr)
        return false;

    Spell::fireSpellEffect(*tile, "GhostRevive", "");
    crypt->removeCorpse(*this);
    clearActionQueue();
    mDeathCounter = 0;
    mCorpseTurns = 0.0;
    mDecayTurns = -1.0;
    mIsCarried = false;
    mCorpseCarrierName.clear();
    resetKoTurns();
    setHP(mMaxHP * hpShare);
    mHunger = 80.0;
    mWakefulness = ConfigManager::getSingleton().getTiredWakefulness();
    mThirst = 80.0;
    mGhostRevived = true;
    removeAnnoyance();
    computeMood();
    computeCreatureOverlayMoodValue();
    clearDestinations(EntityAnimation::idle_anim, true, true);
    setAnimationState(EntityAnimation::idle_anim, true, Ogre::Vector3::ZERO, false);
    mNeedFireRefresh = true;
    return true;
}


void Creature::showOutliner()
{
    RenderManager::getSingleton().rrAddOutliner(this);
}


void Creature::removeOutliner()
{
    RenderManager::getSingleton().rrRemoveOutliner(this);
}


void Creature::maxAmbient()
{

    RenderManager::getSingleton().rrIncreaseAmbient(this);

}

void Creature::normalizeAmbient()
{

    RenderManager::getSingleton().rrNormalizeAmbient(this);

}

namespace
{
//! \brief Computes where the possessed creature can walk from the given position in the given
//! direction (unit vector). Returns false if it cannot move at all in this direction.
bool computePossessedDestination(const Creature& creature, const Ogre::Vector2& position,
    const Ogre::Vector2& direction, Ogre::Vector2& destination)
{
    const Ogre::Real stepLength = 0.25f;
    const Ogre::Real maxLength = 2.0f;
    destination = position;
    for(Ogre::Real length = stepLength; length <= maxLength; length += stepLength)
    {
        Ogre::Vector2 next = position + direction * length;
        Tile* nextTile = creature.getGameMap()->getTile(Helper::round(next.x), Helper::round(next.y));
        if(!creature.canGoThroughTile(nextTile))
            break;

        destination = next;
    }

    return (destination != position);
}
}

void Creature::startPossession(Player& player)
{
    mPossessor = &player;
    mPossessionTurns = 0;
    player.setPossessedCreatureName(getName());

    // The creature stops what it is doing. Its actions are kept and will go on after the possession
    clearDestinations(EntityAnimation::idle_anim, true, true);
    pushAction(Utils::make_unique<CreatureActionPossessed>(*this));

    // Nearby fighting creatures of the player follow the possessed one
    formPossessionGroup();

    if(!player.getIsHuman())
        return;

    ServerNotification* serverNotification = new ServerNotification(
        ServerNotificationType::possessionStart, &player);
    const std::string& name = getName();
    serverNotification->mPacket << name;
    ODServer::getSingleton().queueServerNotification(serverNotification);
}

bool Creature::handleChampionUpkeep()
{
    ++mChampionTurns;

    // The cast price covers the first seconds (price divided by the drain per second). After that
    // the owner pays each turn the share of the drain per second and the champion leaves when the
    // mana cannot pay one second of it
    double price = ConfigManager::getSingleton().getSpellConfigDouble("SummonChampionPrice");
    double drainPerSecond = ConfigManager::getSingleton().getSpellConfigDouble("SummonChampionDrainPerSecond");
    if(drainPerSecond <= 0.0)
        return false;

    double freeSeconds = price / drainPerSecond;
    if(static_cast<double>(mChampionTurns) <= (freeSeconds * ODApplication::turnsPerSecond))
        return false;

    double drainPerTurn = drainPerSecond / ODApplication::turnsPerSecond;
    if((getSeat()->getMana() < drainPerSecond) || !getSeat()->takeMana(drainPerTurn))
    {
        dismissChampion();
        return true;
    }

    return false;
}

bool Creature::handleChampionIdle()
{
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return false;

    // Enemy creatures first, the nearest reachable one. The dungeon hearts of the enemies come after
    std::vector<std::pair<int, Tile*>> targets;
    for(Creature* creature : getGameMap()->getCreatures())
    {
        if(creature->getSeat()->isAlliedSeat(getSeat()) || !creature->isAlive() || !creature->getIsOnMap() ||
           creature->isInPrison())
        {
            continue;
        }

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        int distX = tile->getX() - myTile->getX();
        int distY = tile->getY() - myTile->getY();
        targets.push_back(std::make_pair(distX * distX + distY * distY, tile));
    }
    std::sort(targets.begin(), targets.end());

    std::vector<std::pair<int, Tile*>> heartTargets;
    for(Room* heart : getGameMap()->getRoomsByType(RoomType::dungeonTemple))
    {
        if(heart->getSeat()->isAlliedSeat(getSeat()))
            continue;

        std::vector<Tile*> heartTiles = heart->getCoveredTiles();
        if(heartTiles.empty())
            continue;

        int distX = heartTiles.front()->getX() - myTile->getX();
        int distY = heartTiles.front()->getY() - myTile->getY();
        heartTargets.push_back(std::make_pair(distX * distX + distY * distY, heartTiles.front()));
    }
    std::sort(heartTargets.begin(), heartTargets.end());
    targets.insert(targets.end(), heartTargets.begin(), heartTargets.end());

    // The path check is costly, so only the closest few targets are tried
    uint32_t nbTries = 0;
    for(const std::pair<int, Tile*>& target : targets)
    {
        if(nbTries >= MAX_PATH_CHECK_TARGET_TRIES)
            break;
        ++nbTries;

        if(!getGameMap()->pathExists(this, myTile, target.second))
            continue;

        if(setDestination(target.second))
            return true;
    }

    return false;
}

void Creature::dismissChampion()
{
    if(!getIsOnServerMap())
        return;

    OD_LOG_INF("The champion " + getName() + " leaves");
    if((getSeat()->getPlayer() != nullptr) && getSeat()->getPlayer()->getIsHuman() &&
       !getSeat()->getPlayer()->getHasLost())
    {
        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::chatServer, getSeat()->getPlayer());
        std::string msg = "The champion leaves your dungeon";
        serverNotification->mPacket << msg << EventShortNoticeType::aboutCreatures;
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }

    clearDestinations(EntityAnimation::idle_anim, true, true);
    removeFromGameMap();
    deleteYourself();
}

//! Tolerance that keeps an exact capacity such as 129 from being rounded down to 128 by floating point error.
static const double GOLD_CAPACITY_ROUNDING_EPSILON = 1e-9;

//! \brief Returns the gold the creature can carry before it has to haul it to a treasury. Every reader of the
//! capacity uses this function so that the capacity can depend on more than the definition. A creature with
//! MaxGoldCarryable above 0 carries MaxGoldCarryable x (1 + GoldCarryPerStrength x (Strength - start Strength))
//! x (1 + carry% / 100), rounded down.
int32_t Creature::getGoldCapacity() const
{
    const int32_t baseCapacity = mDefinition->getMaxGoldCarryable();
    if(baseCapacity <= 0)
        return baseCapacity;

    const double strengthGain = std::max(0.0, getStrength() - mDefinition->getStrength());
    const double strengthFactor = 1.0 + ConfigManager::getSingleton().getGoldCarryPerStrength() * strengthGain;
    const double carryFactor = 1.0 + getSkillPassive("carry%") / 100.0;
    const double capacity = static_cast<double>(baseCapacity) * strengthFactor * carryFactor;
    return static_cast<int32_t>(std::floor(capacity + GOLD_CAPACITY_ROUNDING_EPSILON));
}

//! \brief Applies signed gold proceeds or payments and retains the fractional balance.
//! \param gold Positive proceeds or a negative payment.
//! \return The whole part that was added to the carried gold.
int32_t Creature::addGoldCarriedFraction(double gold)
{
    mGoldRemainder += gold;
    double wholePart = std::floor(mGoldRemainder);
    mGoldRemainder -= wholePart;
    int32_t added = static_cast<int32_t>(wholePart);
    addGoldCarried(added);
    return added;
}

//! \brief Drops the carried gold above the capacity as a gold pile on the tile of the creature. Only creatures that
//! can carry gold (capacity above 0) are affected; thieves, wages and casino gold of other creatures stay untouched.
void Creature::dropExcessGold()
{
    int32_t capacity = getGoldCapacity();
    if((capacity <= 0) || (mGoldCarried <= capacity))
        return;

    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return;

    TreasuryObject* obj = new TreasuryObject(getGameMap(), mGoldCarried - capacity);
    mGoldCarried = capacity;
    Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(myTile->getX()),
                                static_cast<Ogre::Real>(myTile->getY()), 0.0f);
    obj->addToGameMap();
    obj->createMesh();
    obj->setPosition(spawnPosition);
}

void Creature::endPossession()
{
    if(mPossessor == nullptr)
        return;

    Player* player = mPossessor;
    mPossessor = nullptr;
    player->setPossessedCreatureName(std::string());
    // Whether the creature fell (dead, knocked out or gone), so the client does not have to guess it
    const bool lost = !isAlive() || isKo() || !getIsOnMap();
    endParticleEffectsByScript(POSSESSION_AURA_SCRIPT);
    // The aura is permanent on the clients and a refresh never removes an effect that is missing from it. The turn
    // deletes the ended effect before the refresh of the turn is built, so the clients are told now, while the effect
    // is still there with no turns left
    mNeedFireRefresh = true;
    fireCreatureRefreshIfNeeded();

    // The group does not follow anymore and goes back to its normal behaviour
    for(const std::string& memberName : mGroupMemberNames)
    {
        Creature* member = getGameMap()->getCreature(memberName);
        if((member != nullptr) && (member->mGroupLeaderName == getName()))
            member->leavePossessionGroup();
    }
    mGroupMemberNames.clear();

    for(std::vector<std::unique_ptr<CreatureAction>>::iterator it = mActions.begin(); it != mActions.end();)
    {
        if((*it)->getType() == CreatureActionType::possessed)
            it = mActions.erase(it);
        else
            ++it;
    }

    if(isAlive() && getIsOnMap())
        clearDestinations(EntityAnimation::idle_anim, true, true);

    if(!player->getIsHuman())
        return;

    ServerNotification* serverNotification = new ServerNotification(
        ServerNotificationType::possessionEnd, player);
    serverNotification->mPacket << lost;
    ODServer::getSingleton().queueServerNotification(serverNotification);
}

void Creature::formPossessionGroup()
{
    mGroupMemberNames.clear();

    uint32_t maxSize = ConfigManager::getSingleton().getSpellConfigUInt32("PossessGroupSize");
    int32_t radius = ConfigManager::getSingleton().getSpellConfigInt32("PossessGroupRadiusTiles");
    int32_t radiusSquared = radius * radius;
    Tile* myTile = getPositionTile();
    if((maxSize == 0) || (myTile == nullptr))
        return;

    std::vector<std::pair<int, Creature*>> candidates;
    for(Creature* creature : getGameMap()->getCreaturesBySeat(getSeat()))
    {
        if((creature == this) || creature->getDefinition()->isWorker() || !creature->isAlive() ||
           creature->isKo() || !creature->getIsOnMap() || creature->isInPrison() ||
           creature->isPossessed() || creature->isInPossessionGroup())
        {
            continue;
        }

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        int distance = Pathfinding::squaredDistanceTile(*tile, *myTile);
        if(distance > radiusSquared)
            continue;

        candidates.push_back(std::make_pair(distance, creature));
    }

    std::sort(candidates.begin(), candidates.end());
    for(const std::pair<int, Creature*>& candidate : candidates)
    {
        if(mGroupMemberNames.size() >= maxSize)
            break;

        candidate.second->joinPossessionGroup(getName());
        mGroupMemberNames.push_back(candidate.second->getName());
    }
}

void Creature::joinPossessionGroup(const std::string& leaderName)
{
    mGroupLeaderName = leaderName;

    // The creature leaves what it was doing. The group behaviour is handled when it is idle
    clearDestinations(EntityAnimation::idle_anim, true, true);
    clearActionQueue();
}

void Creature::leavePossessionGroup()
{
    mGroupLeaderName.clear();
}

bool Creature::followPossessionLeader()
{
    Creature* leader = getGameMap()->getCreature(mGroupLeaderName);
    if((leader == nullptr) || !leader->isPossessed() || !leader->getIsOnMap())
    {
        leavePossessionGroup();
        return false;
    }

    Tile* myTile = getPositionTile();
    Tile* leaderTile = leader->getPositionTile();
    if((myTile == nullptr) || (leaderTile == nullptr))
        return true;

    // The creature stays around the leader. If it is further than 3 tiles, it walks to him
    if(Pathfinding::squaredDistanceTile(*myTile, *leaderTile) <= POSSESSION_GROUP_MAX_SQUARED_DISTANCE)
        return true;

    if(!getGameMap()->pathExists(this, myTile, leaderTile))
        return true;

    std::list<Tile*> tempPath = getGameMap()->path(this, leaderTile);
    // The group does not stand on the leader
    for(int i = 0; (i < 2) && (tempPath.size() > 1); ++i)
        tempPath.pop_back();

    std::vector<Ogre::Vector2> path;
    tileToVector2(tempPath, path, true, 0.0);
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true);
    pushAction(Utils::make_unique<CreatureActionGoCallToWar>(*this));
    return true;
}

void Creature::possessedMove(const Ogre::Vector2& direction)
{
    if(!isPossessed() || !getIsOnMap() || isFrozen())
        return;

    Ogre::Vector2 position(mPosition.x, mPosition.y);
    Ogre::Vector2 destination = position;
    bool canMove = false;
    if(direction.squaredLength() > POSSESSION_MIN_DIRECTION_SQUARED_LENGTH)
    {
        Ogre::Vector2 dir = direction;
        dir.normalise();
        // If the creature is blocked, it tries to slide along the obstacle
        canMove = computePossessedDestination(*this, position, dir, destination);
        if(!canMove)
            canMove = computePossessedDestination(*this, position, Ogre::Vector2(dir.x, 0.0f), destination);
        if(!canMove)
            canMove = computePossessedDestination(*this, position, Ogre::Vector2(0.0f, dir.y), destination);
    }

    if(!canMove)
    {
        if(isMoving())
            clearDestinations(EntityAnimation::idle_anim, true, true);

        return;
    }

    std::vector<Ogre::Vector2> path;
    path.push_back(destination);
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, true);
}

namespace
{
//! \brief The attacks used with the left mouse button while possessing (melee and ranged).
//! The other skills of the creature are used with the number keys.
bool isPossessedBasicAttack(const CreatureSkill& skill)
{
    return (skill.getSkillName() == "Melee") || (skill.getSkillName() == "MissileLaunch");
}

//! \brief Tells whether a possessed creature can use the skill now: no cooldown (including a fraction of a
//! turn) and no warmup left, the skill is usable by the creature and the creature has the mana for it.
//! \param creature The possessed creature that wants to use the skill.
//! \param skillData The state of the skill (cooldown and warmup turns left).
bool isPossessedSkillReady(const Creature& creature, const CreatureSkillData& skillData)
{
    return (skillData.mCooldown <= 0.0) && (skillData.mWarmup <= 0.0) &&
        skillData.mSkill->canBeUsedBy(&creature) && creature.hasManaFor(*skillData.mSkill);
}
}

bool Creature::possessedFindTarget(const Ogre::Vector2& aim, const CreatureSkillData& skillData,
    GameEntity*& entityAttack, Tile*& tileAttack)
{
    entityAttack = nullptr;
    tileAttack = nullptr;
    Tile* myTile = getPositionTile();
    if(myTile == nullptr)
        return false;

    if(aim.squaredLength() < POSSESSION_MIN_AIM_SQUARED_LENGTH)
        return false;

    Ogre::Vector2 aimDir = aim;
    aimDir.normalise();

    // The target has to be in front of the creature (45 degrees to each side)
    const Ogre::Real minCos = 0.7f;
    bool bestIsCreature = false;
    Ogre::Real bestDist = 0.0f;
    for(GameEntity* entity : mVisibleEnemyObjects)
    {
        bool isCreature = (entity->getObjectType() == GameEntityType::creature);
        if(isCreature)
        {
            Creature* enemy = static_cast<Creature*>(entity);
            if(!enemy->isAlive())
                continue;

            // Workers attack workers only
            if(getDefinition()->isWorker() && !enemy->getDefinition()->isWorker())
                continue;
        }
        else if(getDefinition()->isWorker())
            continue;

        if(entity->getHP(nullptr) <= 0)
            continue;

        double skillRange = skillData.mSkill->getRangeMax(this, entity);
        if(skillRange <= 0.0)
            continue;

        for(Tile* tile : entity->getCoveredTiles())
        {
            if(!entity->isAttackable(tile, getSeat()))
                continue;

            // Same range check as in a normal fight
            int squaredDist = Pathfinding::squaredDistanceTile(*tile, *myTile);
            if(static_cast<double>(squaredDist) > (skillRange * skillRange))
                continue;

            Ogre::Vector2 toTile(tile->getX() - mPosition.x, tile->getY() - mPosition.y);
            Ogre::Real dist = toTile.length();
            if(dist > POSSESSION_AIM_MIN_DISTANCE)
            {
                toTile /= dist;
                if(toTile.dotProduct(aimDir) < minCos)
                    continue;
            }

            // Creatures are attacked before the other objects, then the closest one
            if((entityAttack != nullptr) && ((bestIsCreature && !isCreature) ||
               ((bestIsCreature == isCreature) && (dist >= bestDist))))
                continue;

            entityAttack = entity;
            tileAttack = tile;
            bestIsCreature = isCreature;
            bestDist = dist;
        }
    }

    return (entityAttack != nullptr);
}

void Creature::possessedAttack(const Ogre::Vector2& aim)
{
    if(!isPossessed() || !getIsOnMap() || !isAlive() || isKo() || isFrozen())
        return;

    // The melee attack is preferred. The ranged attack is used if no enemy is within melee range
    CreatureSkillData* bestSkill = nullptr;
    GameEntity* bestEntity = nullptr;
    Tile* bestTile = nullptr;
    double bestRange = 0.0;
    for(CreatureSkillData& skillData : mSkillData)
    {
        if(!isPossessedBasicAttack(*skillData.mSkill))
            continue;

        if(!isPossessedSkillReady(*this, skillData))
            continue;

        GameEntity* entity = nullptr;
        Tile* tile = nullptr;
        if(!possessedFindTarget(aim, skillData, entity, tile))
            continue;

        double range = skillData.mSkill->getRangeMax(this, entity);
        if((bestSkill != nullptr) && (range >= bestRange))
            continue;

        bestSkill = &skillData;
        bestEntity = entity;
        bestTile = tile;
        bestRange = range;
    }

    if(bestSkill == nullptr)
        return;

    useAttack(*bestSkill, *bestEntity, *bestTile, false, true);
}

void Creature::possessedUseSkill(uint32_t slot, const Ogre::Vector2& aim)
{
    if(!isPossessed() || !getIsOnMap() || !isAlive() || isKo() || isFrozen())
        return;

    uint32_t index = 0;
    for(CreatureSkillData& skillData : mSkillData)
    {
        if(isPossessedBasicAttack(*skillData.mSkill))
            continue;

        if(!skillData.mSkill->canBeUsedBy(this))
            continue;

        if(index != slot)
        {
            ++index;
            continue;
        }

        if(!isPossessedSkillReady(*this, skillData))
            return;

        // Skills without range (haste, heal, ...) are used on the creature itself
        if(skillData.mSkill->getRangeMax(this, this) <= 0.0)
        {
            if(!skillData.mSkill->tryUseSupport(*getGameMap(), this))
                return;

            // The mana is paid when the skill starts
            payManaFor(*skillData.mSkill);

            skillData.mCooldown += skillData.mSkill->getCooldownNbTurns();
            skillData.mWarmup += skillData.mSkill->getWarmupNbTurns();
            // Report a successful self-cast exactly as in normal creature control.
            mAttackRecoveryDuration = std::max(static_cast<double>(skillData.mWarmup), skillData.mCooldown);
            mAttackRecoveryTurns = mAttackRecoveryDuration;
            ++mAttackRecoverySerial;
            mNeedFireRefresh = true;
            return;
        }

        GameEntity* entity = nullptr;
        Tile* tile = nullptr;
        if(!possessedFindTarget(aim, skillData, entity, tile))
            return;

        useAttack(skillData, *entity, *tile, false, true);
        return;
    }
}

void Creature::interruptGhostHunt()
{
    if(!getIsOnServerMap()) return;
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
            static_cast<CreatureActionHuntGhost*>(action.get())->interrupt();
}

void Creature::refreshGhostHuntVisuals()
{
    bool backpack=false;std::string target,thrown;uint32_t boxMode=0;double turns=0.0;
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
        {
            CreatureActionHuntGhost* hunt=static_cast<CreatureActionHuntGhost*>(action.get());
            backpack=hunt->hasBackpack();target=hunt->getBeamTarget();boxMode=hunt->getBoxVisualState();
            thrown=hunt->getThrowGhostName();turns=hunt->getStepTurns();break;
        }
    if(backpack!=mGhostBackpack || target!=mGhostBeamTarget || boxMode!=mGhostBoxMode || thrown!=mGhostThrowTarget ||
       (boxMode==1 && turns!=mGhostThrowTurns))
    {
        mGhostBackpack=backpack;mGhostBeamTarget=target;mGhostBoxMode=boxMode;
        mGhostThrowTarget=thrown;mGhostThrowTurns=turns;mNeedFireRefresh=true;
    }
}

void Creature::upkeepGhostHunt()
{
    if(!getIsOnServerMap()) return;
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
        {
            CreatureActionHuntGhost* hunt=static_cast<CreatureActionHuntGhost*>(action.get());
            hunt->upkeep();
        }
}

void Creature::restoreGhostHunt()
{
    if(!getIsOnServerMap() || !mGhostHuntLoaded) return;
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
            static_cast<CreatureActionHuntGhost*>(action.get())->restore();
    mGhostHuntLoaded=false;
}

void Creature::clearGhostHuntVisuals()
{
    if(getIsOnServerMap()) return;
    Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
    if(!mGhostShrinkTarget.empty())
    {
        GhostEntity* ghost=static_cast<GhostEntity*>(getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity,mGhostShrinkTarget));
        if(ghost!=nullptr) ghost->setCaptureProgress(0.0);
        mGhostShrinkTarget.clear();
    }
    if(mGhostBoxNode!=nullptr)
    {
        while(mGhostBoxNode->numAttachedObjects()>0)
        {
            Ogre::MovableObject* object=mGhostBoxNode->getAttachedObject(static_cast<unsigned short>(0));
            mGhostBoxNode->detachObject(object);scene->destroyMovableObject(object);
        }
        scene->destroySceneNode(mGhostBoxNode);mGhostBoxNode=nullptr;
    }
    if(mGhostBeamSound!=0) { SoundEffectsManager::getSingleton().stopSpatialLoop(mGhostBeamSound);mGhostBeamSound=0; }
    if(mGhostBeamSparks!=nullptr) { scene->destroyParticleSystem(mGhostBeamSparks);mGhostBeamSparks=nullptr; }
    if(mGhostSparkNode!=nullptr) { scene->destroySceneNode(mGhostSparkNode);mGhostSparkNode=nullptr; }
    if(mGhostBeamChain!=nullptr) { scene->destroyBillboardChain(mGhostBeamChain);mGhostBeamChain=nullptr; }
    if(mGhostBeamNode!=nullptr) { scene->destroySceneNode(mGhostBeamNode);mGhostBeamNode=nullptr; }
    if(mGhostBackpackNode!=nullptr)
    {
        while(mGhostBackpackNode->numAttachedObjects()>0)
        {
            Ogre::MovableObject* object=mGhostBackpackNode->getAttachedObject(static_cast<unsigned short>(0));
            mGhostBackpackNode->detachObject(object);scene->destroyMovableObject(object);
        }
        scene->destroySceneNode(mGhostBackpackNode);mGhostBackpackNode=nullptr;
    }
}

//! \brief Keeps hunter equipment creature-scaled and starts capture effects at its authored nozzle.
void Creature::updateGhostHuntVisuals(double seconds)
{
    if(getIsOnServerMap() || getEntityNode()==nullptr) return;
    if(!mGhostBackpack) { clearGhostHuntVisuals();return; }
    Ogre::SceneManager* scene=RenderManager::getSingleton().getSceneManager();
    if(mGhostBackpackNode==nullptr)
    {
        Ogre::Entity* pack=scene->createEntity(getName()+"_GhostBackpack","GhostBackpack.mesh");
        pack->setQueryFlags(0);pack->setCastShadows(true);
        Ogre::Entity* creatureEntity=scene->getEntity(getOgreNamePrefix()+getName());
        const Ogre::Real creatureHeight=creatureEntity->getBoundingBox().getSize().z;
        mGhostBackpackNode=getEntityNode()->createChildSceneNode(getName()+"_GhostPackNode",Ogre::Vector3(0.0f,-0.3f,0.5f*creatureHeight));
        mGhostBackpackNode->attachObject(pack);
    }
    // The fitted Capture nozzle cap from the authored GhostBackpack mesh, in pack-local coordinates.
    const Ogre::Vector3 nozzlePosition=mGhostBackpackNode->convertLocalToWorldPosition(
        Ogre::Vector3(0.153606342f, 0.103960392f, 0.239335642f));
    if(!mGhostShrinkTarget.empty() && mGhostShrinkTarget!=mGhostThrowTarget)
    {
        GhostEntity* previous=static_cast<GhostEntity*>(getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity,mGhostShrinkTarget));
        if(previous!=nullptr) previous->setCaptureProgress(0.0);
        mGhostShrinkTarget.clear();
    }
    if(mGhostBoxMode!=0 && mGhostBoxNode==nullptr)
    {
        Ogre::Entity* box=scene->createEntity(getName()+"_HeldGhostBox","GhostBox.mesh");
        box->setQueryFlags(0);
        mGhostBoxNode=scene->getRootSceneNode()->createChildSceneNode(getName()+"_HeldGhostBoxNode");mGhostBoxNode->attachObject(box);
    }
    if(mGhostBoxNode!=nullptr)
    {
        mGhostBoxNode->setVisible(mGhostBoxMode!=0);
        const Ogre::Vector3 start=getPosition()+getWalkDirection()*0.35f+Ogre::Vector3(0.0f,0.0f,0.65f);
        Ogre::Vector3 position=start;
        if(mGhostBoxMode==1)
        {
            GhostEntity* ghost=static_cast<GhostEntity*>(getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity,mGhostThrowTarget));
            if(ghost!=nullptr)
            {
                mGhostThrowClientTurns+=seconds*ODApplication::turnsPerSecond*getGameMap()->getGameSpeedFactor();
                const double duration=ConfigManager::getSingleton().getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond;
                const float progress=static_cast<float>(std::min(1.0,mGhostThrowClientTurns/duration));
                position=start+(ghost->getPosition()-start)*progress;
                position.z+=4.0f*progress*(1.0f-progress)*0.5f;
                ghost->setCaptureProgress(progress);mGhostShrinkTarget=mGhostThrowTarget;
            }
        }
        mGhostBoxNode->setPosition(position);
    }
    GameEntity* target=getGameMap()->getEntityFromTypeAndName(GameEntityType::ghostEntity,mGhostBeamTarget);
    if(target==nullptr || mGhostBeamTarget.empty())
    {
        if(mGhostBeamSound!=0) { SoundEffectsManager::getSingleton().stopSpatialLoop(mGhostBeamSound);mGhostBeamSound=0; }
        if(mGhostBeamSparks!=nullptr) { scene->destroyParticleSystem(mGhostBeamSparks);mGhostBeamSparks=nullptr; }
        if(mGhostSparkNode!=nullptr) { scene->destroySceneNode(mGhostSparkNode);mGhostSparkNode=nullptr; }
        if(mGhostBeamChain!=nullptr) { scene->destroyBillboardChain(mGhostBeamChain);mGhostBeamChain=nullptr; }
        if(mGhostBeamNode!=nullptr) { scene->destroySceneNode(mGhostBeamNode);mGhostBeamNode=nullptr; }
        return;
    }
    if(mGhostBeamChain==nullptr)
    {
        mGhostBeamChain=scene->createBillboardChain(getName()+"_GhostBeam");
        mGhostBeamChain->setNumberOfChains(3);mGhostBeamChain->setMaxChainElements(9);
        mGhostBeamChain->setMaterialName("GhostBeam");mGhostBeamChain->setCastShadows(false);mGhostBeamChain->setQueryFlags(0);
        mGhostBeamNode=scene->getRootSceneNode()->createChildSceneNode(getName()+"_GhostBeamNode");mGhostBeamNode->attachObject(mGhostBeamChain);
        mGhostBeamSparks=scene->createParticleSystem(getName()+"_GhostBeamSparks","GhostBeam");
        mGhostBeamSparks->setQueryFlags(0);
        mGhostSparkNode=mGhostBeamNode->createChildSceneNode(getName()+"_GhostSparkNode");mGhostSparkNode->attachObject(mGhostBeamSparks);
        mGhostBeamSample=0.1;
        mGhostBeamSound=SoundEffectsManager::getSingleton().startSpatialLoop("Rooms/GhostRoom/Beam",getPosition().x,getPosition().y);
    }
    SoundEffectsManager::getSingleton().setSpatialLoopPosition(mGhostBeamSound,getPosition().x,getPosition().y);
    if(mGhostSparkNode!=nullptr) mGhostSparkNode->setPosition(nozzlePosition);
    mGhostBeamSample+=seconds;
    if(mGhostBeamSample<0.1) return;
    mGhostBeamSample=std::fmod(mGhostBeamSample,0.1);
    const Ogre::Vector3 start=nozzlePosition;
    const Ogre::Vector3 end=target->getPosition()+Ogre::Vector3(0.0f,0.0f,0.4f);
    for(size_t chain=0;chain<3;++chain)
    {
        mGhostBeamChain->clearChain(chain);
        for(size_t i=0;i<9;++i)
        {
            const float fraction=static_cast<float>(i)/8.0f;
            Ogre::Vector3 point=start+(end-start)*fraction;
            if(i!=0 && i!=8) point+=Ogre::Vector3(Random::Double(-0.08,0.08),Random::Double(-0.08,0.08),Random::Double(-0.08,0.08));
            mGhostBeamChain->addChainElement(chain,Ogre::BillboardChain::Element(point,0.025f,fraction,Ogre::ColourValue(0.55f,1.0f,0.65f,1.0f),Ogre::Quaternion::IDENTITY));
        }
    }
}

void Creature::transferGhostHuntRoom(const std::string& previous, const std::string& current, bool hook, bool empty)
{
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
            static_cast<CreatureActionHuntGhost*>(action.get())->transferRoom(previous,current,hook,empty);
}

void Creature::restoreGhostHuntLayout()
{
    if(!getIsOnServerMap() || !mGhostHuntLoaded) return;
    for(const std::unique_ptr<CreatureAction>& action : mActions)
        if(action->getType()==CreatureActionType::huntGhost)
            static_cast<CreatureActionHuntGhost*>(action.get())->restoreLayout();
}
