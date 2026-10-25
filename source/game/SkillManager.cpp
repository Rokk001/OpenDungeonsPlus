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

#include "game/SkillManager.h"

#include "game/Skill.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "modes/GameEditorModeBase.h"
#include "modes/GameMode.h"
#include "render/Gui.h"
#include "rooms/RoomType.h"
#include "rooms/RoomManager.h"
#include "spells/SpellSummonWorker.h"
#include "spells/SpellManager.h"
#include "spells/SpellType.h"
#include "traps/TrapManager.h"
#include "traps/TrapType.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <CEGUI/Window.h>
#include <CEGUI/widgets/PushButton.h>
#include <algorithm>
#include <cmath>
#include <functional>
#include <map>
#include <utility>

namespace
{
//! \brief Functor to select skills from gui
class SkillSelector
{
public:
    SkillSelector(SkillType type, GameMode& gameMode):
        mType(type),
        mGameMode(gameMode)
    {
    }

    bool operator()(const CEGUI::EventArgs& e)
    {
        if(!mGameMode.skillButtonTreeClicked(mType))
            return true;

        mGameMode.refreshGuiSkill(true);
        return true;
    }
    SkillType mType;
    GameMode& mGameMode;
};

SkillManager& getSkillManager()
{
    static SkillManager manager;
    return manager;
}

//! \brief Path prefix of the research buttons of the Rooms tab inside SkillTreeWindow/Skills
static const std::string TREE_PREFIX_ROOMS = "SkillTabs/Rooms/";
//! \brief Path prefix of the research buttons of the Traps and doors tab inside SkillTreeWindow/Skills
static const std::string TREE_PREFIX_TRAPS = "SkillTabs/Traps/";
//! \brief Path prefix of the research buttons of the Spells tab inside SkillTreeWindow/Skills
static const std::string TREE_PREFIX_SPELLS = "SkillTabs/Spells/";

//! \brief Titles of the tabs of the research tree window
static const std::string TAB_TITLE_ROOMS = "Rooms";
static const std::string TAB_TITLE_TRAPS = "Traps and doors";
static const std::string TAB_TITLE_SPELLS = "Spells";

//! \brief Tooltip titles of the keeper skills
static const std::string KEEPER_TITLE_DOMINION = "Dominion";
static const std::string KEEPER_TITLE_HEART_FORTITUDE = "Heart Fortitude";
static const std::string KEEPER_TITLE_HEART_MENDING = "Heart Mending";
static const std::string KEEPER_TITLE_MANA_FLOW = "Mana Flow";

//! \brief Parent list of a skill without parents
static const std::vector<SkillType> NO_PARENTS;

//! \brief The tab of the research tree window that belongs to a path prefix of its buttons
//! \param skillFamily The path prefix, one of the TREE_PREFIX constants
SkillTab getTabOfPrefix(const std::string& skillFamily)
{
    if(skillFamily == TREE_PREFIX_TRAPS)
        return SkillTab::traps;
    if(skillFamily == TREE_PREFIX_SPELLS)
        return SkillTab::spells;
    return SkillTab::rooms;
}
}

//! \brief Class used to gather information about the skill with the corresponding
//! skill and use gui buttons
class SkillDef
{
public:
    //! \brief Creates the definition of a research entry.
    //! \param skillFamily The path prefix of the research button in the tree window, one of the TREE_PREFIX constants (it names the tab)
    //! \param buttonName The name of the research button
    //! \param skill The skill of the entry
    //! \param tier The row of the entry in its tab (1 at the top to 4 at the bottom)
    SkillDef(const std::string& skillFamily, const std::string& buttonName, const Skill* skill, uint32_t tier) :
        mSkillFamily(skillFamily),
        mButtonName(buttonName),
        mSkill(skill),
        mTier(tier),
        mTab(getTabOfPrefix(skillFamily))
    {
    }

    virtual ~SkillDef()
    {}

    const std::string mSkillFamily;
    const std::string mButtonName;
    const Skill* mSkill;
    //! \brief The row of the entry in its tab (1 at the top to 4 at the bottom)
    const uint32_t mTier;
    //! \brief The tab of the tree window the entry stands in
    const SkillTab mTab;

    virtual SkillFamily getSkillFamily() const = 0;

    //! Short cost description shown in the button tooltip, or an empty string if there is none.
    virtual std::string getCostText(GameMap* gameMap) const = 0;

    virtual const std::string& getTooltipTitle() const = 0;

    virtual void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection) const = 0;

    virtual const std::string& getGuiPath() const = 0;

    virtual void mapSkill(std::vector<std::vector<SkillType>>& skillsFamily) const = 0;
};

class SkillDefRoom : public SkillDef
{
public:
    //! \brief Creates the entry of a room skill, see SkillDef for the parameters
    SkillDefRoom(const std::string& skillFamily, const std::string& buttonName, const Skill* skill, uint32_t tier,
            RoomType roomType) :
        SkillDef(skillFamily, buttonName, skill, tier),
        mRoomType(roomType)
    {
    }

    SkillFamily getSkillFamily() const override
    { return SkillFamily::rooms; }

    const std::string& getTooltipTitle() const override
    { return RoomManager::getRoomReadableName(mRoomType); }

    std::string getCostText(GameMap* gameMap) const override
    { return Helper::toString(RoomManager::costPerTile(mRoomType)) + " gold per tile"; }

    void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection) const override
    {
        mode->addEventConnection(
            rootWindow->getChild(getGuiPath() + mButtonName)->subscribeEvent(
              CEGUI::PushButton::EventClicked,
              CEGUI::Event::Subscriber(RoomSelector(mRoomType, playerSelection))
            )
        );
    }

    const std::string& getGuiPath() const override
    {
        static const std::string guiPath = "MainTabControl/Rooms/";
        return guiPath;
    }

    void mapSkill(std::vector<std::vector<SkillType>>& skillsFamily) const override
    {
        uint32_t index = static_cast<uint32_t>(SkillFamily::rooms);
        std::vector<SkillType>& family = skillsFamily[index];
        index = static_cast<uint32_t>(mRoomType);
        if(index >= family.size())
        {
            OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
            return;
        }
        family[index] = mSkill->getType();
    }

    RoomType mRoomType;
};

class SkillDefTrap : public SkillDef
{
public:
    //! \brief Creates the entry of a trap skill, see SkillDef for the parameters
    SkillDefTrap(const std::string& skillFamily, const std::string& buttonName, const Skill* skill, uint32_t tier,
            TrapType trapType) :
        SkillDef(skillFamily, buttonName, skill, tier),
        mTrapType(trapType)
    {
    }

    SkillFamily getSkillFamily() const override
    { return SkillFamily::traps; }

    const std::string& getTooltipTitle() const override
    { return TrapManager::getTrapReadableName(mTrapType); }

    std::string getCostText(GameMap* gameMap) const override
    { return Helper::toString(TrapManager::costPerTile(mTrapType)) + " gold per tile"; }

    void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection) const override
    {
        mode->addEventConnection(
            rootWindow->getChild(getGuiPath() + mButtonName)->subscribeEvent(
              CEGUI::PushButton::EventClicked,
              CEGUI::Event::Subscriber(TrapSelector(mTrapType, playerSelection))
            )
        );
    }

    const std::string& getGuiPath() const override
    {
        static const std::string guiPath = "MainTabControl/Traps/";
        return guiPath;
    }

    void mapSkill(std::vector<std::vector<SkillType>>& skillsFamily) const override
    {
        uint32_t index = static_cast<uint32_t>(SkillFamily::traps);
        std::vector<SkillType>& family = skillsFamily[index];
        index = static_cast<uint32_t>(mTrapType);
        if(index >= family.size())
        {
            OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
            return;
        }
        family[index] = mSkill->getType();
    }

    TrapType mTrapType;
};

class SkillDefSpell : public SkillDef
{
public:
    //! \brief Creates the entry of a spell skill, see SkillDef for the parameters
    SkillDefSpell(const std::string& skillFamily, const std::string& buttonName, const Skill* skill, uint32_t tier,
            SpellType spellType) :
        SkillDef(skillFamily, buttonName, skill, tier),
        mSpellType(spellType)
    {
    }

    SkillFamily getSkillFamily() const override
    { return SkillFamily::spells; }

    const std::string& getTooltipTitle() const override
    { return SpellManager::getSpellReadableName(mSpellType); }

    std::string getCostText(GameMap* gameMap) const override
    {
        if(mSpellType == SpellType::summonWorker)
            return Helper::toString(SpellSummonWorker::getNextWorkerPriceForPlayer(gameMap,
                gameMap->getLocalPlayer())) + " mana for next worker";

        const char* key = nullptr;
        switch(mSpellType)
        {
            case SpellType::callToWar: key = "CallToWarPrice"; break;
            case SpellType::creatureHeal: key = "CreatureHealPrice"; break;
            case SpellType::creatureExplosion: key = "CreatureExplosionPrice"; break;
            case SpellType::creatureHaste: key = "CreatureHastePrice"; break;
            case SpellType::creatureDefense: key = "CreatureDefensePrice"; break;
            case SpellType::creatureSlow: key = "CreatureSlowPrice"; break;
            case SpellType::creatureStrength: key = "CreatureStrengthPrice"; break;
            case SpellType::creatureWeak: key = "CreatureWeakPrice"; break;
            case SpellType::eyeEvil: key = "EyeEvilPrice"; break;
            case SpellType::createGold: key = "CreateGoldPrice"; break;
            case SpellType::lightning: key = "LightningPrice"; break;
            case SpellType::tremor: key = "TremorPrice"; break;
            case SpellType::defector: key = "DefectorPrice"; break;
            case SpellType::hexenHen: key = "HexenHenPrice"; break;
            case SpellType::inferno: key = "InfernoPrice"; break;
            case SpellType::possess: key = "PossessPrice"; break;
            case SpellType::summonChampion: key = "SummonChampionPrice"; break;
            default: return "";
        }
        const std::string unit = (mSpellType == SpellType::callToWar || mSpellType == SpellType::eyeEvil ||
            mSpellType == SpellType::createGold || mSpellType == SpellType::lightning ||
            mSpellType == SpellType::tremor || mSpellType == SpellType::defector ||
            mSpellType == SpellType::hexenHen || mSpellType == SpellType::inferno ||
            mSpellType == SpellType::possess || mSpellType == SpellType::summonChampion) ?
            " mana" : " mana per creature";
        return Helper::toString(ConfigManager::getSingleton().getSpellConfigInt32(key)) + unit;
    }

    void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection) const override
    {
        mode->addEventConnection(
            rootWindow->getChild(getGuiPath() + mButtonName)->subscribeEvent(
              CEGUI::PushButton::EventClicked,
              CEGUI::Event::Subscriber(SpellSelector(mSpellType, playerSelection))
            )
        );
    }

    const std::string& getGuiPath() const override
    {
        static const std::string guiPath = "MainTabControl/Spells/";
        return guiPath;
    }

    void mapSkill(std::vector<std::vector<SkillType>>& skillsFamily) const override
    {
        uint32_t index = static_cast<uint32_t>(SkillFamily::spells);
        std::vector<SkillType>& family = skillsFamily[index];
        index = static_cast<uint32_t>(mSpellType);
        if(index >= family.size())
        {
            OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
            return;
        }
        family[index] = mSkill->getType();
    }

    SpellType mSpellType;
};

//! \brief A keeper skill: it changes the keeper (creature limit, dungeon heart, mana), so it has no room, trap or spell,
//! no cast button and no action bar button. Only its research button in the tree window exists.
class SkillDefKeeper : public SkillDef
{
public:
    //! \brief Creates the entry of a keeper skill, see SkillDef for the parameters
    SkillDefKeeper(const std::string& skillFamily, const std::string& buttonName, const Skill* skill, uint32_t tier) :
        SkillDef(skillFamily, buttonName, skill, tier)
    {
    }

    //! \brief A keeper skill belongs to no room, trap or spell family
    SkillFamily getSkillFamily() const override
    { return SkillFamily::keeper; }

    //! \brief The name of the keeper skill
    const std::string& getTooltipTitle() const override
    {
        switch(mSkill->getType())
        {
            case SkillType::keeperDominion:
                return KEEPER_TITLE_DOMINION;
            case SkillType::keeperHeartFortitude:
                return KEEPER_TITLE_HEART_FORTITUDE;
            case SkillType::keeperHeartMending:
                return KEEPER_TITLE_HEART_MENDING;
            default:
                return KEEPER_TITLE_MANA_FLOW;
        }
    }

    //! \brief A keeper skill has no cost to build or cast
    std::string getCostText(GameMap* gameMap) const override
    { return ""; }

    //! \brief A keeper skill has no action bar button to connect
    void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection) const override
    {
    }

    //! \brief A keeper skill has no action bar button, so its gui path is empty
    const std::string& getGuiPath() const override
    {
        static const std::string guiPath;
        return guiPath;
    }

    //! \brief A keeper skill is not mapped to a room, trap or spell
    void mapSkill(std::vector<std::vector<SkillType>>& skillsFamily) const override
    {
    }
};

//! \brief Creates the Skill of the given type with its parents. The cost and the free level one come from skills.cfg.
//! \param skills The entries registered so far; the parents must be among them
//! \param type The type of the new skill
//! \param parentTypes The parents of the skill
//! \return The new skill
static Skill* createSkill(const std::vector<const SkillDef*>& skills, SkillType type,
        const std::vector<SkillType>& parentTypes)
{
    std::vector<const Skill*> parents;
    for(SkillType parentType : parentTypes)
    {
        const SkillDef* parent = skills[static_cast<uint32_t>(parentType)];
        if(parent == nullptr)
        {
            OD_LOG_ERR("Parent not registered yet: " + Skills::toString(parentType) + " for " + Skills::toString(type));
            continue;
        }
        parents.push_back(parent->mSkill);
    }

    const std::string name = Skills::toString(type);
    const ConfigManager& config = ConfigManager::getSingleton();
    return new Skill(type, config.getSkillPoints(name), parents, config.isSkillFreeLevelOne(name));
}

//! \brief Enters a skill definition into the lookup tables of the skill manager
//! \param def The definition to enter
//! \param skills The definitions by skill type
//! \param skillsFamily The skill of each room, trap and spell
//! \param tabSkills The skills of each tab in tree order
static void registerSkillDef(SkillDef* def, std::vector<const SkillDef*>& skills,
        std::vector<std::vector<SkillType>>& skillsFamily, std::vector<std::vector<SkillType>>& tabSkills)
{
    def->mapSkill(skillsFamily);
    skills[static_cast<uint32_t>(def->mSkill->getType())] = def;
    if(!Skills::isRewardSkill(def->mSkill->getType()))
        tabSkills[static_cast<uint32_t>(def->mTab)].push_back(def->mSkill->getType());
}

//! \brief Registers the research tree with the room, trap, spell and keeper unlocks.
SkillManager::SkillManager() :
    mSkills(static_cast<uint32_t>(SkillType::countSkill)),
    mTabSkills(static_cast<uint32_t>(SkillTab::nb)),
    mSkillsFamily(static_cast<uint32_t>(SkillFamily::nb))
{
    for (uint32_t i = 0; i < static_cast<uint32_t>(SkillFamily::nb); ++i)
    {
        std::vector<SkillType>& family = mSkillsFamily.at(i);
        SkillFamily resFamily = static_cast<SkillFamily>(i);
        switch(resFamily)
        {
            case SkillFamily::rooms:
                family = std::vector<SkillType>(static_cast<uint32_t>(RoomType::nbRooms), SkillType::nullSkillType);
                break;
            case SkillFamily::traps:
                family = std::vector<SkillType>(static_cast<uint32_t>(TrapType::nbTraps), SkillType::nullSkillType);
                break;
            case SkillFamily::spells:
                family = std::vector<SkillType>(static_cast<uint32_t>(SpellType::nbSpells), SkillType::nullSkillType);
                break;
            case SkillFamily::keeper:
                // The keeper skills have no room, trap or spell to map
                break;
            default:
                OD_LOG_ERR("Wrong enum value=" + Helper::toString(static_cast<uint32_t>(resFamily)) + ", size=" + Helper::toString(static_cast<uint32_t>(SkillFamily::nb)));
                break;
        }
    }

    // We build the skill tree. Every entry names its tab (path prefix), its tier (row) and its parents; an entry is
    // registered after its parents. Within a tier, the entries stand from left to right in registration order.
    SkillDef* def;
    Skill* skill;

    // Rooms tab, tier I
    skill = createSkill(mSkills, SkillType::roomTreasury, NO_PARENTS);
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "TreasuryButton", skill, 1, RoomType::treasury);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomDormitory, NO_PARENTS);
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "DormitoryButton", skill, 1, RoomType::dormitory);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomHatchery, NO_PARENTS);
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "HatcheryButton", skill, 1, RoomType::hatchery);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomLibrary, NO_PARENTS);
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "LibraryButton", skill, 1, RoomType::library);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Rooms tab, tier II
    skill = createSkill(mSkills, SkillType::roomTrainingHall, std::vector<SkillType>{SkillType::roomTreasury});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "TrainingHallButton", skill, 2, RoomType::trainingHall);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomWorkshop, std::vector<SkillType>{SkillType::roomTreasury});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "WorkshopButton", skill, 2, RoomType::workshop);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomBridgeWooden, std::vector<SkillType>{SkillType::roomTreasury});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "WoodenBridgeButton", skill, 2, RoomType::bridgeWooden);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomGuardRoom, std::vector<SkillType>{SkillType::roomDormitory});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "GuardRoomButton", skill, 2, RoomType::guardRoom);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomCasino, std::vector<SkillType>{SkillType::roomTreasury});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "CasinoButton", skill, 2, RoomType::casino);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomToilet, std::vector<SkillType>{SkillType::roomDormitory});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "ToiletButton", skill, 2, RoomType::toilet);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Rooms tab, tier III
    skill = createSkill(mSkills, SkillType::roomArena, std::vector<SkillType>{SkillType::roomTrainingHall});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "ArenaButton", skill, 3, RoomType::arena);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomPrison, std::vector<SkillType>{SkillType::roomGuardRoom});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "PrisonButton", skill, 3, RoomType::prison);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomCrypt, std::vector<SkillType>{SkillType::roomLibrary});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "CryptButton", skill, 3, RoomType::crypt);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomBridgeStone, std::vector<SkillType>{SkillType::roomBridgeWooden});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "StoneBridgeButton", skill, 3, RoomType::bridgeStone);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    skill = createSkill(mSkills, SkillType::roomInfirmary, std::vector<SkillType>{SkillType::roomGuardRoom});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "InfirmaryButton", skill, 3, RoomType::infirmary);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Rooms tab, tier IV
    skill = createSkill(mSkills, SkillType::roomTorture, std::vector<SkillType>{SkillType::roomPrison});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "TortureButton", skill, 4, RoomType::torture);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::roomTemple, std::vector<SkillType>{SkillType::roomCrypt});
    def = new SkillDefRoom(TREE_PREFIX_ROOMS, "PrayerTempleButton", skill, 4, RoomType::temple);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::keeperDominion, std::vector<SkillType>{SkillType::roomArena});
    def = new SkillDefKeeper(TREE_PREFIX_ROOMS, "DominionButton", skill, 4);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Traps tab, tier I
    skill = createSkill(mSkills, SkillType::trapDoorWooden, std::vector<SkillType>{SkillType::roomWorkshop});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "WoodenDoorTrapButton", skill, 1, TrapType::doorWooden);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapSpike, std::vector<SkillType>{SkillType::roomWorkshop});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "SpikeTrapButton", skill, 1, TrapType::spike);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapCannon, std::vector<SkillType>{SkillType::roomWorkshop});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "CannonButton", skill, 1, TrapType::cannon);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapAlarm, std::vector<SkillType>{SkillType::roomWorkshop});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "AlarmTrapButton", skill, 1, TrapType::alarm);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Traps tab, tier II
    skill = createSkill(mSkills, SkillType::trapDoorIronbound, std::vector<SkillType>{SkillType::trapDoorWooden});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "IronboundDoorTrapButton", skill, 2, TrapType::doorIronbound);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapDoorBarricade, std::vector<SkillType>{SkillType::trapDoorWooden});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "BarricadeTrapButton", skill, 2, TrapType::doorBarricade);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapGas, std::vector<SkillType>{SkillType::trapSpike});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "GasTrapButton", skill, 2, TrapType::gas);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapBoulder, std::vector<SkillType>{SkillType::trapSpike});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "BoulderTrapButton", skill, 2, TrapType::boulder);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapWatchBanner, std::vector<SkillType>{SkillType::trapAlarm, SkillType::roomGuardRoom});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "WatchBannerTrapButton", skill, 2, TrapType::watchBanner);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapFear, std::vector<SkillType>{SkillType::trapAlarm});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "FearTrapButton", skill, 2, TrapType::fear);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Traps tab, tier III
    skill = createSkill(mSkills, SkillType::trapDoorSteel, std::vector<SkillType>{SkillType::trapDoorIronbound});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "SteelDoorTrapButton", skill, 3, TrapType::doorSteel);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapDoorSecret, std::vector<SkillType>{SkillType::trapDoorIronbound});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "SecretDoorTrapButton", skill, 3, TrapType::doorSecret);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapLightning, std::vector<SkillType>{SkillType::trapCannon});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "LightningTrapButton", skill, 3, TrapType::lightning);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapTrigger, std::vector<SkillType>{SkillType::trapAlarm});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "TriggerTrapButton", skill, 3, TrapType::trigger);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapFireburst, std::vector<SkillType>{SkillType::trapGas});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "FireburstTrapButton", skill, 3, TrapType::fireburst);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Traps tab, tier IV
    skill = createSkill(mSkills, SkillType::trapDoorRuned, std::vector<SkillType>{SkillType::trapDoorSteel});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "RunedDoorTrapButton", skill, 4, TrapType::doorRuned);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::trapFreeze, std::vector<SkillType>{SkillType::trapLightning});
    def = new SkillDefTrap(TREE_PREFIX_TRAPS, "FreezeTrapButton", skill, 4, TrapType::freeze);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::keeperHeartFortitude, std::vector<SkillType>{SkillType::trapDoorSteel});
    def = new SkillDefKeeper(TREE_PREFIX_TRAPS, "HeartFortitudeButton", skill, 4);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::keeperHeartMending, std::vector<SkillType>{SkillType::keeperHeartFortitude});
    def = new SkillDefKeeper(TREE_PREFIX_TRAPS, "HeartMendingButton", skill, 4);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Spells tab, tier I
    skill = createSkill(mSkills, SkillType::spellSummonWorker, NO_PARENTS);
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "SummonWorkerButton", skill, 1, SpellType::summonWorker);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreatureHeal, std::vector<SkillType>{SkillType::roomLibrary});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureHealButton", skill, 1, SpellType::creatureHeal);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreatureHaste, std::vector<SkillType>{SkillType::roomLibrary});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureHasteButton", skill, 1, SpellType::creatureHaste);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellEyeEvil, std::vector<SkillType>{SkillType::roomLibrary});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "SpellEyeEvilButton", skill, 1, SpellType::eyeEvil);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Spells tab, tier II
    skill = createSkill(mSkills, SkillType::spellCreatureDefense, std::vector<SkillType>{SkillType::spellCreatureHeal});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureDefenseButton", skill, 2, SpellType::creatureDefense);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreatureStrength, std::vector<SkillType>{SkillType::spellCreatureHaste});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureStrengthButton", skill, 2, SpellType::creatureStrength);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCallToWar, std::vector<SkillType>{SkillType::spellCreatureHaste});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CallToWarButton", skill, 2, SpellType::callToWar);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreatureSlow, std::vector<SkillType>{SkillType::spellEyeEvil});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureSlowButton", skill, 2, SpellType::creatureSlow);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellLightning, std::vector<SkillType>{SkillType::spellEyeEvil});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "LightningButton", skill, 2, SpellType::lightning);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Spells tab, tier III
    skill = createSkill(mSkills, SkillType::spellCreatureWeak, std::vector<SkillType>{SkillType::spellCreatureSlow});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureWeakButton", skill, 3, SpellType::creatureWeak);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreatureExplosion, std::vector<SkillType>{SkillType::spellLightning});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreatureExplosionButton", skill, 3, SpellType::creatureExplosion);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellPossess, std::vector<SkillType>{SkillType::spellEyeEvil});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "PossessButton", skill, 3, SpellType::possess);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellCreateGold, std::vector<SkillType>{SkillType::roomTreasury});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "CreateGoldButton", skill, 3, SpellType::createGold);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Spells tab, tier IV
    skill = createSkill(mSkills, SkillType::spellTremor, std::vector<SkillType>{SkillType::spellCreatureExplosion});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "TremorButton", skill, 4, SpellType::tremor);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellInferno, std::vector<SkillType>{SkillType::spellCreatureExplosion});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "InfernoButton", skill, 4, SpellType::inferno);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellDefector, std::vector<SkillType>{SkillType::spellPossess});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "DefectorButton", skill, 4, SpellType::defector);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::spellHexenHen, std::vector<SkillType>{SkillType::spellCreatureWeak});
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "HexenHenButton", skill, 4, SpellType::hexenHen);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
    skill = createSkill(mSkills, SkillType::keeperManaFlow, std::vector<SkillType>{SkillType::roomTemple});
    def = new SkillDefKeeper(TREE_PREFIX_SPELLS, "ManaFlowButton", skill, 4);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);

    // Not researchable: the campaign Heartstone unlocks it. It has no parent, no cost and no node in the skill tree window
    skill = new Skill(SkillType::spellSummonChampion, 0, std::vector<const Skill*>());
    def = new SkillDefSpell(TREE_PREFIX_SPELLS, "SummonChampionButton", skill, 4, SpellType::summonChampion);
    registerSkillDef(def, mSkills, mSkillsFamily, mTabSkills);
}

SkillManager::~SkillManager()
{
    for(const SkillDef* skill : mSkills)
    {
        if(skill == nullptr)
            continue;

        delete skill->mSkill;
        delete skill;
    }
    mSkills.clear();
}

bool SkillManager::isRoomAvailable(RoomType type, const Seat* seat)
{
    uint32_t index = static_cast<uint32_t>(SkillFamily::rooms);
    std::vector<SkillType>& family = getSkillManager().mSkillsFamily[index];
    index = static_cast<uint32_t>(type);
    if(index >= family.size())
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
        return false;
    }
    SkillType resType = family.at(index);
    return seat->isSkillDone(resType);
}

bool SkillManager::isSpellAvailable(SpellType type, const Seat* seat)
{
    uint32_t index = static_cast<uint32_t>(SkillFamily::spells);
    std::vector<SkillType>& family = getSkillManager().mSkillsFamily[index];
    index = static_cast<uint32_t>(type);
    if(index >= family.size())
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
        return false;
    }
    SkillType resType = family.at(index);
    // The spells researched in a library cannot be cast while that library is lost.
    // Summoning a worker needs no research in the game this one follows, so it stays.
    // Reward skills (Summon champion) are unlocked by a Heartstone, not researched, so they stay too.
    if(seat->isLibraryLost() && (type != SpellType::summonWorker) && !Skills::isRewardSkill(resType))
        return false;

    return seat->isSkillDone(resType);
}

bool SkillManager::isLockedByLostLibrary(SkillType type, const Seat* seat)
{
    if(!seat->isLibraryLost() || (type == SkillType::spellSummonWorker) || Skills::isRewardSkill(type))
        return false;

    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if((skill != nullptr) && (skill->mSkill->getType() == type))
            return skill->getSkillFamily() == SkillFamily::spells;
    }

    return false;
}

bool SkillManager::isTrapAvailable(TrapType type, const Seat* seat)
{
    uint32_t index = static_cast<uint32_t>(SkillFamily::traps);
    std::vector<SkillType>& family = getSkillManager().mSkillsFamily[index];
    index = static_cast<uint32_t>(type);
    if(index >= family.size())
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(family.size()));
        return false;
    }
    SkillType resType = family.at(index);
    return seat->isSkillDone(resType);
}

bool SkillManager::isAllSkillsDoneForSeat(const Seat* seat)
{
    if(seat->isSkilling())
        return false;

    // Something is left to research if any entry can reach its next level (parents, tab gates and the
    // allowed list are checked by the seat)
    const std::vector<std::pair<SkillType, int>> nothingQueued;
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr)
            continue;
        if(Skills::isRewardSkill(skill->mSkill->getType()))
            continue;
        const uint32_t level = seat->getSkillLevel(skill->mSkill->getType());
        if(level >= 3)
            continue;
        if(!seat->canResearchLevel(skill->mSkill->getType(), static_cast<int>(level) + 1, nothingQueued))
            continue;
        return false;
    }
    return true;
}

const Skill* SkillManager::getSkill(SkillType resType)
{
    uint32_t index = static_cast<uint32_t>(resType);
    if(index >= getSkillManager().mSkills.size())
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(getSkillManager().mSkills.size()));
        return nullptr;
    }

    const SkillDef* skill = getSkillManager().mSkills[index];
    if(skill == nullptr)
    {
        OD_LOG_ERR("null skill index=" + Helper::toString(index));
        return nullptr;
    }
    return skill->mSkill;
}

SkillTab SkillManager::getSkillTab(SkillType resType)
{
    const uint32_t index = static_cast<uint32_t>(resType);
    if(index >= getSkillManager().mSkills.size() || getSkillManager().mSkills[index] == nullptr)
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index));
        return SkillTab::rooms;
    }

    return getSkillManager().mSkills[index]->mTab;
}

uint32_t SkillManager::getSkillTier(SkillType resType)
{
    const uint32_t index = static_cast<uint32_t>(resType);
    if(index >= getSkillManager().mSkills.size() || getSkillManager().mSkills[index] == nullptr)
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index));
        return 1;
    }

    return getSkillManager().mSkills[index]->mTier;
}

const std::string& SkillManager::getTabTitle(SkillTab tab)
{
    switch(tab)
    {
        case SkillTab::traps:
            return TAB_TITLE_TRAPS;
        case SkillTab::spells:
            return TAB_TITLE_SPELLS;
        default:
            return TAB_TITLE_ROOMS;
    }
}

std::string SkillManager::getTreeButtonPath(SkillType resType)
{
    const uint32_t index = static_cast<uint32_t>(resType);
    if(index >= getSkillManager().mSkills.size() || getSkillManager().mSkills[index] == nullptr)
    {
        OD_LOG_ERR("wrong index=" + Helper::toString(index));
        return "";
    }

    const SkillDef* skill = getSkillManager().mSkills[index];
    return skill->mSkillFamily + skill->mButtonName;
}

void SkillManager::listTabSkills(SkillTab tab, std::vector<SkillType>& skills)
{
    skills = getSkillManager().mTabSkills.at(static_cast<uint32_t>(tab));
}

double SkillManager::getResearchValue(const Seat* seat, SkillType type, double base, const std::string& effect)
{
    return getResearchValue(type, seat == nullptr ? 0 : seat->getSkillLevel(type), base, effect);
}

double SkillManager::getResearchValue(SkillType type, uint32_t level, double base, const std::string& effect)
{
    // A skill that is not researched changes nothing
    if(level == 0)
        return base;

    const ConfigManager::ResearchEffectLine* line = ConfigManager::getSingleton().getResearchEffect(
        Skills::toString(type), effect);
    if(line == nullptr)
        return base;

    const uint32_t maxLevel = ConfigManager::RESEARCH_LEVELS;
    const double value = line->mValues[std::min(level, maxLevel) - 1];
    switch(line->mMode)
    {
        case ConfigManager::ResearchEffectMode::add:
            return base + value;
        case ConfigManager::ResearchEffectMode::dev:
            return 1.0 + (base - 1.0) * value;
        default:
            return base * value;
    }
}

namespace
{
//! \brief The config file a base value of a research effect is read from
enum class ResearchBaseSource
{
    //! rooms.cfg
    rooms,
    //! rooms.cfg, the base is one divided by the value (chickens per tile from tiles per chicken)
    roomsInverse,
    //! traps.cfg
    traps,
    //! spells.cfg
    spells,
    //! global.cfg MaxCreaturesPerSeatDefault
    creatureLimit,
    //! No config value: the effect is a factor that starts at one
    factor
};

//! \brief Where the tooltip finds the base value of one research effect of a skill
struct ResearchBase
{
    SkillType mType;
    const char* mEffect;
    ResearchBaseSource mSource;
    //! Config key of the base value (the largest value when mKeyMin is set), empty for a factor
    const char* mKey;
    //! Config key of the smallest value of a range, empty when the effect is a single value
    const char* mKeyMin;
};

//! \brief The base value of every research effect of skills.cfg, as the code of the room, trap, door or spell reads it
static const ResearchBase RESEARCH_BASES[] =
{
    {SkillType::roomTreasury, "GoldPerTile", ResearchBaseSource::rooms, "TreasuryGoldPerTile", ""},
    {SkillType::roomDormitory, "SleepRecovery", ResearchBaseSource::rooms, "DormitoryWakefulnessPerTurn", ""},
    {SkillType::roomHatchery, "LayInterval", ResearchBaseSource::rooms, "HatcheryChickenSpawnRate", ""},
    {SkillType::roomHatchery, "Capacity", ResearchBaseSource::roomsInverse, "HatcheryTilesPerChicken", ""},
    {SkillType::roomLibrary, "PointsPerWork", ResearchBaseSource::rooms, "LibraryPointsPerWork", ""},
    {SkillType::roomTrainingHall, "XpPerHit", ResearchBaseSource::rooms, "TrainHallXpPerAttack", ""},
    {SkillType::roomWorkshop, "PointsPerWork", ResearchBaseSource::rooms, "WorkshopPointsPerWork", ""},
    {SkillType::roomGuardRoom, "WakefulnessPerDuty", ResearchBaseSource::rooms, "GuardRoomWakefulnessPerDuty", ""},
    {SkillType::roomCasino, "Fee", ResearchBaseSource::rooms, "CasinoFee", ""},
    {SkillType::roomCasino, "Mood", ResearchBaseSource::rooms, "CasinoMoodSmiles", ""},
    {SkillType::roomArena, "LevelCap", ResearchBaseSource::rooms, "ArenaMaxTrainingLevel", ""},
    {SkillType::roomPrison, "Capacity", ResearchBaseSource::factor, "", ""},
    {SkillType::roomPrison, "SkeletonLevel", ResearchBaseSource::rooms, "PrisonSkeletonBaseLevel", ""},
    {SkillType::roomInfirmary, "HealTime", ResearchBaseSource::rooms, "InfirmaryFullHealSeconds", ""},
    {SkillType::roomCrypt, "RotTime", ResearchBaseSource::rooms, "CryptRotNbTurns", ""},
    {SkillType::roomBridgeWooden, "ClaimResistance", ResearchBaseSource::factor, "", ""},
    {SkillType::roomBridgeStone, "ClaimResistance", ResearchBaseSource::factor, "", ""},
    {SkillType::roomTorture, "ConversionSpeed", ResearchBaseSource::factor, "", ""},
    {SkillType::roomTemple, "PrayerMana", ResearchBaseSource::rooms, "TemplePrayerManaPerSecond", ""},
    {SkillType::keeperDominion, "CreatureLimit", ResearchBaseSource::creatureLimit, "", ""},
    {SkillType::trapCannon, "Damage", ResearchBaseSource::traps, "CannonDamagePerHitMax", "CannonDamagePerHitMin"},
    {SkillType::trapSpike, "Damage", ResearchBaseSource::traps, "SpikeDamagePerHitMax", "SpikeDamagePerHitMin"},
    {SkillType::trapBoulder, "Damage", ResearchBaseSource::traps, "BoulderDamagePerHitMax", "BoulderDamagePerHitMin"},
    {SkillType::trapGas, "Damage", ResearchBaseSource::traps, "GasDamagePerHitMax", "GasDamagePerHitMin"},
    {SkillType::trapLightning, "Damage", ResearchBaseSource::traps, "LightningDamagePerHitMax", "LightningDamagePerHitMin"},
    {SkillType::trapFireburst, "Damage", ResearchBaseSource::traps, "FireburstDamagePerHitMax", "FireburstDamagePerHitMin"},
    {SkillType::trapAlarm, "Reload", ResearchBaseSource::traps, "AlarmReloadTurns", ""},
    {SkillType::trapFear, "Duration", ResearchBaseSource::traps, "FearDurationTurns", ""},
    {SkillType::trapFreeze, "Duration", ResearchBaseSource::traps, "FreezeDurationTurns", ""},
    {SkillType::trapWatchBanner, "AuraRadius", ResearchBaseSource::traps, "WatchBannerAuraTiles", ""},
    {SkillType::trapTrigger, "Radius", ResearchBaseSource::traps, "TriggerRadius", ""},
    {SkillType::trapDoorWooden, "HP", ResearchBaseSource::traps, "WoodenDoorHP", ""},
    {SkillType::trapDoorIronbound, "HP", ResearchBaseSource::traps, "IronboundDoorHP", ""},
    {SkillType::trapDoorSteel, "HP", ResearchBaseSource::traps, "SteelDoorHP", ""},
    {SkillType::trapDoorBarricade, "HP", ResearchBaseSource::traps, "BarricadeDoorHP", ""},
    {SkillType::trapDoorSecret, "HP", ResearchBaseSource::traps, "SecretDoorHP", ""},
    {SkillType::trapDoorRuned, "HP", ResearchBaseSource::traps, "RunedDoorHP", ""},
    {SkillType::trapDoorRuned, "Damage", ResearchBaseSource::traps, "RunedDoorDamage", "RunedDoorDamageMin"},
    {SkillType::keeperHeartFortitude, "HeartHP", ResearchBaseSource::rooms, "DungeonHeartHP", ""},
    {SkillType::keeperHeartMending, "HeartHeal", ResearchBaseSource::rooms, "DungeonHeartHealPerSecond", ""},
    {SkillType::keeperManaFlow, "HeartMana", ResearchBaseSource::rooms, "DungeonHeartManaPerSecond", ""},
    {SkillType::spellSummonWorker, "Price", ResearchBaseSource::spells, "SummonWorkerBasePrice", ""},
    {SkillType::spellCreatureHeal, "HealPerTurn", ResearchBaseSource::spells, "CreatureHealValue", ""},
    {SkillType::spellCreatureHaste, "Speed", ResearchBaseSource::spells, "CreatureHasteValue", ""},
    {SkillType::spellEyeEvil, "Duration", ResearchBaseSource::spells, "EyeEvilNbTurns", ""},
    {SkillType::spellEyeEvil, "Radius", ResearchBaseSource::spells, "EyeEvilRadiusTiles", ""},
    {SkillType::spellCreatureDefense, "Bonus", ResearchBaseSource::spells, "CreatureDefenseValue", ""},
    {SkillType::spellCreatureStrength, "Factor", ResearchBaseSource::spells, "CreatureStrengthValue", ""},
    {SkillType::spellCreatureWeak, "Factor", ResearchBaseSource::spells, "CreatureWeakValue", ""},
    {SkillType::spellCreatureSlow, "Factor", ResearchBaseSource::spells, "CreatureSlowValue", ""},
    {SkillType::spellCallToWar, "Lifetime", ResearchBaseSource::spells, "CallToWarNbTurnsMax", ""},
    {SkillType::spellLightning, "Damage", ResearchBaseSource::spells, "LightningDamage", "LightningDamageMin"},
    {SkillType::spellCreatureExplosion, "Damage", ResearchBaseSource::spells, "CreatureExplosionValue", ""},
    {SkillType::spellTremor, "Damage", ResearchBaseSource::spells, "TremorDamage", "TremorDamageMin"},
    {SkillType::spellInferno, "Damage", ResearchBaseSource::spells, "InfernoDamagePerTurn", "InfernoDamagePerTurnMin"},
    {SkillType::spellPossess, "ManaPerSecond", ResearchBaseSource::factor, "", ""},
    {SkillType::spellDefector, "Duration", ResearchBaseSource::spells, "DefectorNbTurns", ""},
    {SkillType::spellHexenHen, "Duration", ResearchBaseSource::spells, "HexenHenNbTurns", ""},
    {SkillType::spellCreateGold, "Gold", ResearchBaseSource::spells, "CreateGoldValue", ""}
};

//! \brief Reads the base value a config key of the given source holds
//! \param source The config file of the key
//! \param key The config key; empty for a factor, which starts at one
//! \return The base value
static double readResearchBase(ResearchBaseSource source, const std::string& key)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    switch(source)
    {
        case ResearchBaseSource::rooms:
            return config.getRoomConfigDouble(key);
        case ResearchBaseSource::roomsInverse:
            return 1.0 / std::max(1.0, config.getRoomConfigDouble(key));
        case ResearchBaseSource::traps:
            return config.getTrapConfigDouble(key);
        case ResearchBaseSource::spells:
            return config.getSpellConfigDouble(key);
        case ResearchBaseSource::creatureLimit:
            return static_cast<double>(config.getMaxCreaturesPerSeatDefault());
        default:
            return 1.0;
    }
}

//! \brief The player visible text of an effect name of skills.cfg
//! \param effect The effect name, one of the ResearchEffect constants
//! \return The text in front of the value in a tooltip
static std::string getResearchEffectText(const std::string& effect)
{
    static std::map<std::string, std::string> texts;
    if(texts.empty())
    {
        texts[ResearchEffect::GoldPerTile] = "Storage per tile";
        texts[ResearchEffect::SleepRecovery] = "Sleep recovery";
        texts[ResearchEffect::LayInterval] = "Egg laying time";
        texts[ResearchEffect::Capacity] = "Capacity";
        texts[ResearchEffect::PointsPerWork] = "Points per work";
        texts[ResearchEffect::XpPerHit] = "Experience per hit";
        texts[ResearchEffect::WakefulnessPerDuty] = "Tiredness per duty turn";
        texts[ResearchEffect::Fee] = "Keeper fee";
        texts[ResearchEffect::Mood] = "Mood gain";
        texts[ResearchEffect::LevelCap] = "Level cap";
        texts[ResearchEffect::SkeletonLevel] = "Skeleton level";
        texts[ResearchEffect::HealTime] = "Healing time";
        texts[ResearchEffect::RotTime] = "Rot time";
        texts[ResearchEffect::ClaimResistance] = "Claim resistance";
        texts[ResearchEffect::ConversionSpeed] = "Conversion speed";
        texts[ResearchEffect::PrayerMana] = "Prayer mana";
        texts[ResearchEffect::CreatureLimit] = "Creature limit";
        texts[ResearchEffect::Damage] = "Damage";
        texts[ResearchEffect::Reload] = "Reload time";
        texts[ResearchEffect::Duration] = "Duration";
        texts[ResearchEffect::AuraRadius] = "Alarm radius";
        texts[ResearchEffect::Radius] = "Radius";
        texts[ResearchEffect::HP] = "Health";
        texts[ResearchEffect::HeartHP] = "Heart health";
        texts[ResearchEffect::HeartHeal] = "Heart healing per second";
        texts[ResearchEffect::HeartMana] = "Heart mana per second";
        texts[ResearchEffect::Price] = "Price";
        texts[ResearchEffect::HealPerTurn] = "Healing per turn";
        texts[ResearchEffect::Speed] = "Speed";
        texts[ResearchEffect::Bonus] = "Defense bonus";
        texts[ResearchEffect::Factor] = "Factor";
        texts[ResearchEffect::Lifetime] = "Duration";
        texts[ResearchEffect::ManaPerSecond] = "Mana per second";
        texts[ResearchEffect::Gold] = "Gold";
    }

    std::map<std::string, std::string>::const_iterator it = texts.find(effect);
    return (it == texts.end()) ? effect : it->second;
}

//! \brief The description sentence of a keeper skill, empty for every other skill
//! \param type The skill
static std::string getKeeperDescription(SkillType type)
{
    switch(type)
    {
        case SkillType::keeperDominion:
            return "More creatures in your dungeon.";
        case SkillType::keeperHeartFortitude:
            return "Your dungeon heart has more health.";
        case SkillType::keeperHeartMending:
            return "Your dungeon heart heals faster.";
        case SkillType::keeperManaFlow:
            return "Your dungeon heart gives more mana.";
        default:
            return "";
    }
}

//! \brief The value of a research effect for the tooltip: whole for the effects that are rounded in the game
//! \param effect The effect name
//! \param value The value after the research level was applied
//! \return The value as text
static std::string getResearchValueText(const std::string& effect, double value)
{
    if((effect == ResearchEffect::LevelCap) || (effect == ResearchEffect::AuraRadius))
        value = std::floor(value + 0.5);

    return Helper::toString(value);
}
}

std::string SkillManager::getResearchDescription(SkillType type, uint32_t level)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    std::string description = getKeeperDescription(type);
    std::vector<std::pair<std::string, ConfigManager::ResearchEffectLine> > lines;
    config.getResearchEffects(Skills::toString(type), lines);
    for(const std::pair<std::string, ConfigManager::ResearchEffectLine>& line : lines)
    {
        const ResearchBase* researchBase = nullptr;
        for(const ResearchBase& candidate : RESEARCH_BASES)
        {
            if((candidate.mType == type) && (line.first == candidate.mEffect))
            {
                researchBase = &candidate;
                break;
            }
        }
        if(researchBase == nullptr)
        {
            OD_LOG_ERR("No base value for the research effect " + line.first + " of skill=" + Skills::toString(type));
            continue;
        }

        std::string value = getResearchValueText(line.first, getResearchValue(type, level,
            readResearchBase(researchBase->mSource, researchBase->mKey), line.first));
        // A range (damage) shows the smallest and the largest value
        if(researchBase->mKeyMin[0] != '\0')
        {
            value = getResearchValueText(line.first, getResearchValue(type, level,
                readResearchBase(researchBase->mSource, researchBase->mKeyMin), line.first)) + "-" + value;
        }

        if(!description.empty())
            description += "\n";
        description += getResearchEffectText(line.first) + ": " + value;
    }

    // The champion is not researched and has no effect line: it keeps its text
    if(type == SkillType::spellSummonChampion)
    {
        description = "Summons one champion that cannot be hurt and charges at the enemies. Costs " +
            Helper::toString(config.getSpellConfigDouble("SummonChampionPrice")) + " mana, free for " +
            Helper::toString(config.getSpellConfigDouble("SummonChampionPrice") /
            config.getSpellConfigDouble("SummonChampionDrainPerSecond")) + " seconds, then " +
            Helper::toString(config.getSpellConfigDouble("SummonChampionDrainPerSecond")) +
            " mana per second. Unlocked by the complete Heartstone.";
    }
    return description;
}

void SkillManager::buildRandomPendingSkillsForSeat(std::vector<SkillType>& skills,
        const Seat* seat)
{
    // The list grows step by step: each step picks at random one of the entries (with the next level of
    // each) that the seat may research after the entries chosen so far, until nothing is left
    std::vector<std::pair<SkillType, int>> queued = seat->getQueuedLevels(skills);
    while(true)
    {
        std::vector<SkillType> candidates;
        for(const SkillDef* skill : getSkillManager().mSkills)
        {
            if(skill == nullptr)
                continue;

            SkillType resType = skill->mSkill->getType();
            if(Skills::isRewardSkill(resType))
                continue;
            // We do not consider skills already pending or at their last level
            const uint32_t level = seat->getSkillLevel(resType);
            if(level >= 3 || std::find(skills.begin(), skills.end(), resType) != skills.end())
                continue;

            if(!seat->canResearchLevel(resType, static_cast<int>(level) + 1, queued))
                continue;

            candidates.push_back(resType);
        }

        if(candidates.empty())
            break;

        const SkillType picked = candidates[Random::Uint(0, static_cast<unsigned int>(candidates.size()) - 1)];
        skills.push_back(picked);
        queued.push_back(std::make_pair(picked, static_cast<int>(seat->getSkillLevel(picked)) + 1));
    }
}

void SkillManager::listAllSkills(const std::function<void(const std::string&, const std::string&,
        const std::string&, SkillType)>& func)
{
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr)
            continue;

        // A skill without an action bar button (a keeper skill) has an empty cast button name
        const std::string castButtonName = skill->getGuiPath().empty() ? "" : skill->getGuiPath() + skill->mButtonName;
        func(skill->mSkillFamily + skill->mButtonName, castButtonName,
             skill->mSkillFamily + skill->mButtonName + "/" + skill->mButtonName + "ProgressBar",
             skill->mSkill->getType());
    }
}

void SkillManager::listAllSpellsProgressBars(const std::function<void(SpellType spellType, const std::string&)>& func)
{
    std::vector<const SkillDef*>& skills = getSkillManager().mSkills;
    uint32_t index = static_cast<uint32_t>(SkillFamily::spells);
    std::vector<SkillType>& family = getSkillManager().mSkillsFamily.at(index);
    uint32_t nbSpells = static_cast<uint32_t>(SpellType::nbSpells);
    for(uint32_t i = 0; i < nbSpells; ++i)
    {
        if(i >= family.size())
        {
            OD_LOG_ERR("wrong index=" + Helper::toString(i) + ", size=" + Helper::toString(family.size()));
            return;
        }

        SkillType resType = family[i];
        if(resType == SkillType::nullSkillType)
            continue;

        index = static_cast<uint32_t>(resType);
        if(index >= skills.size())
        {
            OD_LOG_ERR("wrong index=" + Helper::toString(index) + ", size=" + Helper::toString(getSkillManager().mSkills.size()));
            continue;
        }

        const SkillDef* skill = skills[index];
        if(skill == nullptr)
        {
            OD_LOG_ERR("null skill index=" + Helper::toString(index));
            continue;
        }

        SpellType spellType = static_cast<SpellType>(i);
        func(spellType, skill->getGuiPath() + skill->mButtonName + "/" + skill->mButtonName + "ProgressBar");
    }
}

void SkillManager::connectSkills(GameMode* mode, CEGUI::Window* rootWindow)
{
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr)
            continue;

        mode->addEventConnection(
            rootWindow->getChild("SkillTreeWindow/Skills/" + skill->mSkillFamily + skill->mButtonName)->subscribeEvent(
              CEGUI::PushButton::EventClicked,
              CEGUI::Event::Subscriber(SkillSelector(skill->mSkill->getType(), *mode))
            )
        );
    }
}

void SkillManager::connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection)
{
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr)
            continue;

        skill->connectGuiButtons(mode, rootWindow, playerSelection);
    }
}

void SkillManager::updateCostTooltip(GameMap* gameMap, CEGUI::Window* rootWindow, CEGUI::Window* hoveredWindow)
{
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr || skill->getGuiPath().empty() || hoveredWindow->getName() != skill->mButtonName ||
            hoveredWindow != rootWindow->getChild(skill->getGuiPath() + skill->mButtonName))
            continue;

        if(!hoveredWindow->isUserStringDefined("CostBaseDescription"))
            hoveredWindow->setUserString("CostBaseDescription", hoveredWindow->getTooltipText());
        const std::string cost = skill->getCostText(gameMap);
        const CEGUI::String text = hoveredWindow->getUserString("CostBaseDescription") +
            (cost.empty() ? "" : " (" + cost + ")");
        hoveredWindow->setUserString(Gui::USER_STRING_CONTEXT_HELP, text);
        if(hoveredWindow->getTooltipText() != skill->getTooltipTitle())
            hoveredWindow->setTooltipText(skill->getTooltipTitle());
        return;
    }
}

std::string SkillManager::getSelectedButton(const PlayerSelection& playerSelection)
{
    SkillFamily family = SkillFamily::nb;
    uint32_t type = 0;
    switch(playerSelection.getCurrentAction())
    {
        case SelectedAction::buildRoom:
            family = SkillFamily::rooms;
            type = static_cast<uint32_t>(playerSelection.getNewRoomType());
            break;
        case SelectedAction::buildTrap:
            family = SkillFamily::traps;
            type = static_cast<uint32_t>(playerSelection.getNewTrapType());
            break;
        case SelectedAction::castSpell:
            family = SkillFamily::spells;
            type = static_cast<uint32_t>(playerSelection.getNewSpellType());
            break;
        case SelectedAction::destroyRoom:
            return Gui::BUTTON_DESTROY_ROOM;
        case SelectedAction::destroyTrap:
            return Gui::BUTTON_DESTROY_TRAP;
        case SelectedAction::queryEntity:
            return "QueryButton";
        case SelectedAction::sellBuilding:
            return "SellButton";
        default:
            return "";
    }

    const std::vector<SkillType>& skills = getSkillManager().mSkillsFamily.at(static_cast<uint32_t>(family));
    if(type >= skills.size() || skills[type] == SkillType::nullSkillType)
        return "";
    const SkillDef* skill = getSkillManager().mSkills.at(static_cast<uint32_t>(skills[type]));
    return skill->getGuiPath() + skill->mButtonName;
}

void SkillManager::listAllRooms(const std::function<void(RoomType, const std::string&)>& func)
{
    for(const SkillDef* skill : getSkillManager().mSkills)
    {
        if(skill == nullptr || skill->getSkillFamily() != SkillFamily::rooms)
            continue;

        const SkillDefRoom* room = static_cast<const SkillDefRoom*>(skill);
        func(room->mRoomType, room->getGuiPath() + room->mButtonName);
    }
}
