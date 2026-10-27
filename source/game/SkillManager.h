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

#ifndef RESEARCHMANAGER_H
#define RESEARCHMANAGER_H

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

class Skill;

enum class SkillType;
enum class RoomType;
enum class SpellType;
enum class TrapType;

class GameEditorModeBase;
class GameMode;
class GameMap;
class PlayerSelection;
class Seat;

namespace CEGUI
{
class Window;
};

//! \brief Each skill is in one of these families
enum class SkillFamily
{
    rooms,
    traps,
    spells,
    keeper,
    nb
};

//! \brief The tab of the research tree window a skill stands in
enum class SkillTab
{
    rooms,
    traps,
    spells,
    nb
};

//! \brief The effect names of the [ResearchEffects] block of skills.cfg; the second part of a line key
//! (see SkillManager::getResearchValue)
namespace ResearchEffect
{
    static const std::string GoldPerTile = "GoldPerTile";
    static const std::string SleepRecovery = "SleepRecovery";
    static const std::string LayInterval = "LayInterval";
    static const std::string Capacity = "Capacity";
    static const std::string PointsPerWork = "PointsPerWork";
    static const std::string XpPerHit = "XpPerHit";
    static const std::string WakefulnessPerDuty = "WakefulnessPerDuty";
    static const std::string Fee = "Fee";
    static const std::string Mood = "Mood";
    static const std::string LevelCap = "LevelCap";
    static const std::string SkeletonLevel = "SkeletonLevel";
    static const std::string RotTime = "RotTime";
    static const std::string ClaimResistance = "ClaimResistance";
    static const std::string ConversionSpeed = "ConversionSpeed";
    static const std::string PrayerMana = "PrayerMana";
    static const std::string CreatureLimit = "CreatureLimit";
    static const std::string Damage = "Damage";
    static const std::string Reload = "Reload";
    static const std::string Duration = "Duration";
    static const std::string AuraRadius = "AuraRadius";
    static const std::string Radius = "Radius";
    static const std::string HP = "HP";
    static const std::string HeartHP = "HeartHP";
    static const std::string HeartHeal = "HeartHeal";
    static const std::string HeartMana = "HeartMana";
    static const std::string Price = "Price";
    static const std::string HealPerTurn = "HealPerTurn";
    static const std::string Speed = "Speed";
    static const std::string Bonus = "Bonus";
    static const std::string Factor = "Factor";
    static const std::string Lifetime = "Lifetime";
    static const std::string ManaPerSecond = "ManaPerSecond";
    static const std::string Gold = "Gold";
    static const std::string PortalCooldown = "PortalCooldown";
    //! \brief Scales the configured herb growth time.
    static const std::string GrowTime = "GrowTime";
    //! \brief Scales the configured potion brewing time.
    static const std::string BrewTime = "BrewTime";
    //! \brief Scales the configured workshop item-box opening effort.
    static const std::string CrackTime = "CrackTime";
}

//! \brief Local class that will be used to store Skill data and link it to the gui
class SkillDef;

class SkillManager
{
public:
    //! \brief Builds the research tree: every room, trap, door and spell skill with the skills it depends on.
    SkillManager();
    virtual ~SkillManager();

    //! \brief Checks if the given room is available for the given seat. This check
    //! should be done on server side to avoid cheating
    static bool isRoomAvailable(RoomType type, const Seat* seat);

    //! \brief Checks if the given spell is available for the given seat. This check
    //! should be done on server side to avoid cheating
    static bool isSpellAvailable(SpellType type, const Seat* seat);

    //! \brief True for a spell that the seat cannot cast because it lost its library
    //! (an enemy took it over), even though the spell was researched.
    static bool isLockedByLostLibrary(SkillType type, const Seat* seat);

    //! \brief Checks if the given trap is available for the given trap. This check
    //! should be done on server side to avoid cheating
    static bool isTrapAvailable(TrapType type, const Seat* seat);

    //! \brief Checks if the given seat has already researched all the allowed skills
    static bool isAllSkillsDoneForSeat(const Seat* seat);

    //! \brief Builds randomly a pending skill list for the given seat. Note that the
    //! given pending vector may not be empty. In this case, it will be filled by the
    //! not already selected skills. The list is built step by step: each step picks at random
    //! one of the entries the seat may research next (parents and tab gates of levels 2 and 3
    //! checked with the entries chosen so far) until none is left.
    //! Note that this function will only use the seat for knowing already done or not allowed
    //! skills, not the currently pending ones. If they are to be used, skills should
    //! be initialized with them
    static void buildRandomPendingSkillsForSeat(std::vector<SkillType>& skills,
        const Seat* seat);

    static const Skill* getSkill(SkillType resType);

    //! \brief The tab of the research tree window the skill stands in
    static SkillTab getSkillTab(SkillType resType);

    //! \brief The tier (row 1 to 4, top to bottom) of the skill in its tab
    static uint32_t getSkillTier(SkillType resType);

    //! \brief The title of a tab of the research tree window
    static const std::string& getTabTitle(SkillTab tab);

    //! \brief The path of the research button of the skill inside SkillTreeWindow/Skills
    static std::string getTreeButtonPath(SkillType resType);

    //! \brief Fills skills with the entries of the tab in tree order (tier I to IV, within a tier from left to right).
    //! The reward skills have no entry in the tree.
    static void listTabSkills(SkillTab tab, std::vector<SkillType>& skills);

    //! \brief The base value changed by the [ResearchEffects] line of skills.cfg for the given skill and effect, at the
    //! given research level. Level 0 (not researched) and a skill/effect pair without a line return base unchanged.
    //! \param type The researched skill
    //! \param level The research level of the skill (0 to 3)
    //! \param base The value of the room, trap, door or spell in its own config file
    //! \param effect The effect name, one of the ResearchEffect constants
    static double getResearchValue(SkillType type, uint32_t level, double base, const std::string& effect);
    //! \brief Same as above with the research level the seat has for the skill (0 when the seat is null)
    static double getResearchValue(const Seat* seat, SkillType type, double base, const std::string& effect);
    //! \brief The tooltip text of the skill at the given level: one line "<effect text>: <value>" for every
    //! [ResearchEffects] line of the skill, with the real values of the config files
    static std::string getResearchDescription(SkillType type, uint32_t level);

    //! \brief Lists all the skills and calls the given function for each one with parameters:
    //! - Gui skill button name
    //! - Gui use button name
    //! - Gui skill button progressbar name
    //! - The corresponding skill type
    static void listAllSkills(const std::function<void(const std::string&, const std::string&,
        const std::string&, SkillType)>& func);

    //! \brief Lists all the room skills and calls the given function for each one with parameters:
    //! - The room type
    //! - Gui use button name
    static void listAllRooms(const std::function<void(RoomType, const std::string&)>& func);

    //! \brief Lists all the skills and calls the given function for each one with parameters:
    //! - SpellType
    //! - Gui use button progressbar name
    static void listAllSpellsProgressBars(const std::function<void(SpellType spellType, const std::string&)>& func);

    static void connectSkills(GameMode* mode, CEGUI::Window* rootWindow);

    static void connectGuiButtons(GameEditorModeBase* mode, CEGUI::Window* rootWindow, PlayerSelection& playerSelection);

    //! Append the current cost of the hovered action-bar button to its tooltip. Does nothing for other windows.
    static void updateCostTooltip(GameMap* gameMap, CEGUI::Window* rootWindow, CEGUI::Window* hoveredWindow);

    //! Return the action-bar button corresponding to the current room, trap or spell.
    static std::string getSelectedButton(const PlayerSelection& playerSelection);

private:
    //! \brief Allowed skills
    std::vector<const SkillDef*> mSkills;

    //! \brief The skills of each tab (SkillTab) in tree order: tier I to IV, within a tier from left to right
    std::vector<std::vector<SkillType>> mTabSkills;

    //! \brief Allows to map each family room/trap/spell to the corresponding SkillType
    std::vector<std::vector<SkillType>> mSkillsFamily;
};

#endif // RESEARCHMANAGER_H
