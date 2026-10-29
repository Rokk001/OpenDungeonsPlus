/*!
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

#include "ai/KeeperAI.h"
#include "ai/KeeperAIType.h"
#include "ai/AiActions.h"
#include "ai/AiRooms.h"
#include "ai/AiEconomy.h"
#include "ai/AiResearch.h"

#include "creatureaction/CreatureAction.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/SkillManager.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomType.h"
#include "spells/Spell.h"
#include "spells/SpellCallToWar.h"
#include "spells/SpellType.h"
#include "spells/SpellSummonWorker.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <algorithm>
#include <functional>
#include <vector>

// Contains the rooms the AI will try to build. It will try to build them in the given order
// (the compiled room plan, equal to the [RoomPlan] section of ai.cfg; the treasury is planned twice)
static const std::vector<RoomType> wantedBuildings = {
    RoomType::treasury,
    RoomType::dormitory,
    RoomType::hatchery,
    RoomType::tavern,
    RoomType::library,
    RoomType::trainingHall,
    RoomType::workshop,
    RoomType::casino,
    RoomType::toilet,
    RoomType::treasury,
    RoomType::merchant,
    RoomType::guardRoom,
    RoomType::herbGarden,
    RoomType::arena,
    RoomType::prison,
    RoomType::alchemyLab,
    RoomType::infirmary,
    RoomType::ghostRoom,
    RoomType::spa,
    RoomType::crypt,
    RoomType::temple,
    RoomType::torture
};

//! \brief The names of the entries of wantedBuildings in the [RoomPlan] section of ai.cfg (the name-to-room map)
static const std::vector<std::string> wantedBuildingKeys = {
    "treasury", "dormitory", "hatchery", "tavern", "library", "training", "workshop", "casino", "toilet", "treasury2",
    "merchant", "guard", "herbgarden", "arena", "prison", "alchemy", "infirmary", "ghostroom", "spa", "crypt",
    "temple", "torture"
};

//! \brief The tiles of each entry of wantedBuildings (the compiled tiles of the [RoomPlan] section of ai.cfg)
static const std::vector<uint32_t> wantedBuildingTiles = {
    9, 25, 25, 16, 25, 25, 25, 16, 9, 25, 16, 9, 9, 25, 16, 9, 16, 16, 16, 16, 25, 16
};

// LEGACY-AI
//! Interim normal settings for the legacy paths while their replacements are being implemented.
static const int NORMAL_COOLDOWN_DEFENSE_MIN = 0;
static const int NORMAL_COOLDOWN_DEFENSE_MAX = 5;
static const int NORMAL_COOLDOWN_SAVE_WOUNDED_MIN = 0;
static const int NORMAL_COOLDOWN_SAVE_WOUNDED_MAX = 5;
static const int NORMAL_REACTION_PERCENT = 100;
static const int NORMAL_MIN_HP_PERCENT_TO_FIGHT = 20;
static const int NORMAL_MIN_FIGHTERS_TO_ATTACK = 11;
static const int NORMAL_MIN_CREATURE_LEVEL = 4;



//! \brief Creates a keeper whose mind reads the selected level's configured values.
KeeperAI::KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type) :
    BaseAI(gameMap, player),
    mReactionPercent(NORMAL_REACTION_PERCENT),
    mType(type),
    mSettings(ConfigManager::getSingleton().getAiLevel(type)),
    mMind(gameMap, player, mSettings),
    mEvents(*this),
    mMinHpPercentToFight(NORMAL_MIN_HP_PERCENT_TO_FIGHT),
    mMinFightersToAttack(NORMAL_MIN_FIGHTERS_TO_ATTACK),
    mMinCreatureLevel(NORMAL_MIN_CREATURE_LEVEL),
    mIsAttacking(false),
    mNbFightersAtAttackStart(0),
    mCooldownAttack(0),
    mCooldownDefense(0),
    mCooldownDefenseMin(NORMAL_COOLDOWN_DEFENSE_MIN),
    mCooldownDefenseMax(NORMAL_COOLDOWN_DEFENSE_MAX),
    mCooldownSaveWoundedCreatures(0),
    mCooldownSaveWoundedCreaturesMin(NORMAL_COOLDOWN_SAVE_WOUNDED_MIN),
    mCooldownSaveWoundedCreaturesMax(NORMAL_COOLDOWN_SAVE_WOUNDED_MAX)
{
    ACTS::bind(*this);
    mEvents.bind();
    // The war rows react to their events after the shared reaction delay
    std::function<void(const AiEvent&)> warHandler = std::bind(&KeeperAI::handleWarEvent, this, std::placeholders::_1);
    mMind.onEvent("J01", std::vector<AiEventType>(1, AiEventType::Fight), warHandler);
    mMind.onEvent("J05", std::vector<AiEventType>(1, AiEventType::HeartCritical), warHandler);
    mMind.onEvent("J07", std::vector<AiEventType>(1, AiEventType::EnemyOut), warHandler);
    mMind.onEvent("J08", std::vector<AiEventType>(1, AiEventType::FightOver), warHandler);
    mMind.onEvent("K08", std::vector<AiEventType>(1, AiEventType::EnemyTrapEmpty), warHandler);
    std::function<void(std::vector<AiMath::AiStateLine>&)> warSaver = std::bind(&KeeperAI::saveWarRows, this, std::placeholders::_1);
    mMind.onSave(warSaver);
    ECON::bind(*this);
    ROOMS::bind(*this);
    RES::bind(*this);
}

int KeeperAI::scaledCooldown(int min, int max) const
{
    return Random::Int((min * mReactionPercent) / 100, (max * mReactionPercent) / 100);
}

//! \brief Advances the shared mind and the paths still waiting for their owner packages.
bool KeeperAI::doTurn(double timeSinceLastTurn)
{
    // If we have no dungeon temple, we are dead
    if(getDungeonTemple() == nullptr)
        return false;
    mMind.doTurn(timeSinceLastTurn);
    runWar();
    return true;
}

//! \brief Returns the common scheduler to the action and decision owners.
Mind& KeeperAI::getMind()
{
    return mMind;
}

//! \brief Retains raw symptom timing and forwards each game notice to the shared reaction queue.
void KeeperAI::notifyEvent(const AiEvent& event)
{
    mEvents.notify(event);
    mMind.enqueue(event);
}

//! \brief Returns the configured level values used by the decision functions.
const AiSettings& KeeperAI::getSettings() const
{
    return mSettings;
}

//! \brief Saves the complete shared mind inside the seat's AIState block.
void KeeperAI::exportState(std::ostream& os) const
{
    mMind.exportState(os);
}

//! \brief Restores the complete shared mind from the saved block contents.
bool KeeperAI::importState(const std::vector<std::string>& lines)
{
    bool restored = mMind.importState(lines);
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::importRows(env, mMind.savedRows());
    return restored;
}

//! \brief Appends the war and sighting lines to the saved AI state of the mind.
void KeeperAI::saveWarRows(std::vector<AiMath::AiStateLine>& lines)
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::exportRows(env, lines);
}

//! \brief Runs the polled parts of the war (plan step, tunnel probe, assault steps, enemy edges) once per turn.
void KeeperAI::runWar()
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::doTurn(env);
}

//! \brief Hands an event of the war rows to the war module after the reaction delay of the Mind.
void KeeperAI::handleWarEvent(const AiEvent& event)
{
    WAR::Env env = {*this, mMind, mGameMap, mPlayer, mSettings, mWar, mMind.now()};
    WAR::onEvent(env, event);
}

//! \brief The room plan from ai.cfg mapped to room types, or the compiled plan when ai.cfg has none.
std::vector<std::pair<RoomType, uint32_t>> KeeperAI::getRoomPlan()
{
    std::vector<std::pair<RoomType, uint32_t>> plan;
    const std::vector<std::pair<std::string, uint32_t>>& configPlan = ConfigManager::getSingleton().getAiRoomPlan();
    if(configPlan.empty())
    {
        for(uint32_t i = 0; i < wantedBuildings.size(); ++i)
            plan.push_back(std::make_pair(wantedBuildings[i], wantedBuildingTiles[i]));
        return plan;
    }

    for(const std::pair<std::string, uint32_t>& entry : configPlan)
    {
        std::vector<std::string>::const_iterator it = std::find(wantedBuildingKeys.begin(), wantedBuildingKeys.end(), entry.first);
        if(it == wantedBuildingKeys.end())
        {
            OD_LOG_ERR("Unknown room in the AI room plan=" + entry.first);
            continue;
        }
        plan.push_back(std::make_pair(wantedBuildings[it - wantedBuildingKeys.begin()], entry.second));
    }
    return plan;
}

//! \brief Forwards the ghost room's product decision to its configured room rule.
void KeeperAI::updateGhostRoomSettings(Seat& seat)
{
    Player* player = seat.getPlayer();
    if(player == nullptr || player->getIsHuman() || seat.getGameMap() == nullptr)
        return;
    KeeperAI* ai = dynamic_cast<KeeperAI*>(seat.getGameMap()->getAI(*player));
    if(ai != nullptr)
        ROOMS::ghostProduct(*ai);
}

//! \brief Scores known room squares around the selected placement origin.
bool KeeperAI::findRoomPosition(Tile* start, int32_t size, bool walls, int32_t& x, int32_t& y)
{
    return findBestPlaceForRoom(start, mPlayer.getSeat(), size, walls, x, y);
}
