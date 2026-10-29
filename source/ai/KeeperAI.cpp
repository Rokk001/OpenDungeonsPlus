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

//! \brief Range of turns between two checks of the attack state (before the reaction scaling)
static const int ATTACK_COOLDOWN_MIN = 20;
static const int ATTACK_COOLDOWN_MAX = 40;
//! \brief Range of turns the AI waits after retreating before it considers a new attack
static const int ATTACK_RETREAT_COOLDOWN_MIN = 200;
static const int ATTACK_RETREAT_COOLDOWN_MAX = 300;
//! \brief Range of turns the AI waits after ordering a way to the enemy dungeon to be dug
static const int ATTACK_DIG_COOLDOWN_MIN = 100;
static const int ATTACK_DIG_COOLDOWN_MAX = 200;
//! \brief The AI retreats when its fighters fall below 1 / this value of the number it started with
static const int ATTACK_RETREAT_DIVISOR = 2;


//! \brief Creates a keeper whose mind reads the selected level's configured values.
KeeperAI::KeeperAI(GameMap& gameMap, Player& player, KeeperAIType type) :
    BaseAI(gameMap, player),
    mReactionPercent(NORMAL_REACTION_PERCENT),
    mType(type),
    mSettings(ConfigManager::getSingleton().getAiLevel(type)),
    mMind(gameMap, player, mSettings),
    mMinHpPercentToFight(NORMAL_MIN_HP_PERCENT_TO_FIGHT),
    mMinFightersToAttack(NORMAL_MIN_FIGHTERS_TO_ATTACK),
    mMinCreatureLevel(NORMAL_MIN_CREATURE_LEVEL),
    mIsAttacking(false),
    mNbFightersAtAttackStart(0),
    mCooldownAttack(0),
    mCooldownDefense(0),
    mCooldownDefenseMin(NORMAL_COOLDOWN_DEFENSE_MIN),
    mCooldownDefenseMax(NORMAL_COOLDOWN_DEFENSE_MAX),
    mCooldownRepairRooms(0),
    mCooldownSaveWoundedCreatures(0),
    mCooldownSaveWoundedCreaturesMin(NORMAL_COOLDOWN_SAVE_WOUNDED_MIN),
    mCooldownSaveWoundedCreaturesMax(NORMAL_COOLDOWN_SAVE_WOUNDED_MAX)
{
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
    legacyWarTurn();
    return true;
}

//! \brief Returns the common scheduler to the action and decision owners.
Mind& KeeperAI::getMind()
{
    return mMind;
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
    return mMind.importState(lines);
}

//! \brief Preserves the original war paths until their owner supplies the new decisions.
void KeeperAI::legacyWarTurn()
{
    saveWoundedCreatures();
    handleDefense();
    handleAttack();
}

void KeeperAI::saveWoundedCreatures()
{
    if(mCooldownSaveWoundedCreatures > 0)
    {
        --mCooldownSaveWoundedCreatures;
        return;
    }
    mCooldownSaveWoundedCreatures = Random::Int(mCooldownSaveWoundedCreaturesMin, mCooldownSaveWoundedCreaturesMax);

    Tile* dungeonTempleTile = getDungeonTemple()->getCentralTile();
    if(dungeonTempleTile == nullptr)
    {
        OD_LOG_ERR("keeperAi=" + mPlayer.getNick());
        return;
    }

    Seat* seat = mPlayer.getSeat();
    std::vector<Creature*> creatures = mGameMap.getCreaturesBySeat(seat);
    for(Creature* creature : creatures)
    {
        // We take away fleeing creatures not too near our dungeon heart
        if(!creature->isActionInList(CreatureActionType::flee))
            continue;
        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        if((std::abs(dungeonTempleTile->getX() - tile->getX()) <= 5) &&
           (std::abs(dungeonTempleTile->getY() - tile->getY()) <= 5))
        {
            // We are too close from our dungeon heart to be picked up
            continue;
        }

        if(!creature->tryPickup(seat))
            continue;

        mPlayer.pickUpEntity(creature);

        mPlayer.dropHand(dungeonTempleTile);
    }
}

void KeeperAI::handleDefense()
{
    if(mCooldownDefense > 0)
    {
        --mCooldownDefense;
        return;
    }
    mCooldownDefense = Random::Int(mCooldownDefenseMin, mCooldownDefenseMax);

    Seat* seat = mPlayer.getSeat();
    // We drop creatures nearby owned or allied attacked creatures
    std::vector<Creature*> creatures = mGameMap.getCreaturesByAlliedSeat(seat);
    for(Creature* creature : creatures)
    {
        // We check if a creature is fighting near a claimed tile. If yes, we drop a creature nearby
        if(!creature->isActionInList(CreatureActionType::fight))
            continue;

        Tile* tile = creature->getPositionTile();
        if(tile == nullptr)
            continue;

        // We look for a healthy creature not already fighting
        Creature* creatureToDrop = nullptr;
        for(Creature* creature2 : mGameMap.getCreaturesBySeat(seat))
        {
            if(creature2->getDefinition()->isWorker())
                continue;
            if(creature2->getHP() < (creature2->getMaxHp() * mMinHpPercentToFight / 100.0))
                continue;
            if(creature2->isActionInList(CreatureActionType::fight))
                continue;
            if((creatureToDrop != nullptr) && (creatureToDrop->getLevel() >= creature2->getLevel()))
                continue;

            creatureToDrop = creature2;
        }
        if(creatureToDrop == nullptr)
            continue;

        if(!creatureToDrop->tryPickup(seat))
            continue;

        for(Tile* neigh : tile->getAllNeighbors())
        {
            if(creatureToDrop->tryDrop(seat, neigh))
            {
                mPlayer.pickUpEntity(creatureToDrop);
                mPlayer.dropHand(neigh);
                return;
            }
        }
    }
}

int KeeperAI::countHealthyFighters() const
{
    int nbFighters = 0;
    for(Creature* creature : mGameMap.getCreaturesBySeat(mPlayer.getSeat()))
    {
        if(creature->getDefinition()->isWorker())
            continue;
        if(creature->isKo())
            continue;
        if(creature->getHP() < (creature->getMaxHp() * mMinHpPercentToFight / 100.0))
            continue;

        ++nbFighters;
    }
    return nbFighters;
}

int KeeperAI::countWeakFighters() const
{
    int nbWeakFighters = 0;
    for(Creature* creature : mGameMap.getCreaturesBySeat(mPlayer.getSeat()))
    {
        if(creature->getDefinition()->isWorker())
            continue;
        if(creature->isKo())
            continue;
        if(creature->getHP() < (creature->getMaxHp() * mMinHpPercentToFight / 100.0))
            continue;
        if(static_cast<int>(creature->getLevel()) < mMinCreatureLevel)
            ++nbWeakFighters;
    }
    return nbWeakFighters;
}

Tile* KeeperAI::findEnemyTempleTile()
{
    Tile* central = getDungeonTemple()->getCentralTile();
    Tile* best = nullptr;
    int bestDistance = 0;
    for(Seat* seat : mGameMap.getSeats())
    {
        if(seat->isAlliedSeat(mPlayer.getSeat()))
            continue;

        for(Room* temple : mGameMap.getRoomsByTypeAndSeat(RoomType::dungeonTemple, seat))
        {
            Tile* tile = temple->getCentralTile();
            if(tile == nullptr)
                continue;

            int distance = std::abs(tile->getX() - central->getX()) + std::abs(tile->getY() - central->getY());
            if((best == nullptr) || (distance < bestDistance))
            {
                best = tile;
                bestDistance = distance;
            }
        }
    }
    return best;
}

void KeeperAI::removeBanners()
{
    for(Spell* banner : mGameMap.getSpellsBySeatAndType(mPlayer.getSeat(), SpellType::callToWar))
        banner->slap();
}

void KeeperAI::handleAttack()
{
    if(mMinFightersToAttack <= 0)
        return;

    if(mCooldownAttack > 0)
    {
        --mCooldownAttack;
        return;
    }
    mCooldownAttack = scaledCooldown(ATTACK_COOLDOWN_MIN, ATTACK_COOLDOWN_MAX);

    Seat* seat = mPlayer.getSeat();
    if(!SkillManager::isSpellAvailable(SpellType::callToWar, seat))
        return;

    int nbFighters = countHealthyFighters();
    Tile* enemyTile = findEnemyTempleTile();

    if(mIsAttacking)
    {
        // We retreat if the enemy is gone or we lost half of the fighters we started with
        if((enemyTile == nullptr) || ((nbFighters * ATTACK_RETREAT_DIVISOR) < mNbFightersAtAttackStart))
        {
            OD_LOG_INF("AI seatId=" + Helper::toString(seat->getId()) + " retreats, fighters=" + Helper::toString(nbFighters));
            removeBanners();
            mIsAttacking = false;
            mCooldownAttack = scaledCooldown(ATTACK_RETREAT_COOLDOWN_MIN, ATTACK_RETREAT_COOLDOWN_MAX);
            return;
        }

        // The banner expires after some time. We renew it if needed
        if(mGameMap.getSpellsBySeatAndType(seat, SpellType::callToWar).empty())
            SpellCallToWar::castSpellOnTile(&mGameMap, &mPlayer, enemyTile);

        return;
    }

    // The AI attacks with more creatures than the threshold, and waits while more
    // creatures than the minimum level number are below that level
    if((nbFighters <= mMinFightersToAttack) || (enemyTile == nullptr))
        return;

    int nbWeakFighters = countWeakFighters();
    if(nbWeakFighters > mMinCreatureLevel)
        return;

    // We need a walkable way to the enemy temple. If there is none, workers dig it first
    Tile* central = getDungeonTemple()->getCentralTile();
    Creature* fighter = nullptr;
    for(Creature* creature : mGameMap.getCreaturesBySeat(seat))
    {
        if(creature->getDefinition()->isWorker() || (creature->getPositionTile() == nullptr))
            continue;

        fighter = creature;
        break;
    }
    if(fighter == nullptr)
        return;

    if(!mGameMap.pathExists(fighter, fighter->getPositionTile(), enemyTile))
    {
        digWayToTile(central, enemyTile);
        mCooldownAttack = scaledCooldown(ATTACK_DIG_COOLDOWN_MIN, ATTACK_DIG_COOLDOWN_MAX);
        return;
    }

    if(!SpellCallToWar::castSpellOnTile(&mGameMap, &mPlayer, enemyTile))
        return;

    OD_LOG_INF("AI seatId=" + Helper::toString(seat->getId()) + " attacks with fighters=" + Helper::toString(nbFighters));
    mIsAttacking = true;
    mNbFightersAtAttackStart = nbFighters;
}

bool KeeperAI::repairRooms()
{
    if(mCooldownRepairRooms > 0)
    {
        --mCooldownRepairRooms;
        return false;
    }

    mCooldownRepairRooms = scaledCooldown(20, 60);

    Seat* seat = mPlayer.getSeat();
    for(Room* room : mGameMap.getRooms())
    {
        if(room->getSeat() != seat)
            continue;

        if(!room->canBeRepaired())
            continue;

        int goldRequired = room->getCostRepair();

        if(!mGameMap.withdrawFromTreasuries(goldRequired, mPlayer.getSeat()))
            return false;

        room->repairRoom();
        // We only repair one room at a time. Note that if we want to repair more than one room at a time, we should pay
        // attention to not modify the room list (if room absorbed in RoomManager::buildRoom) while iterating it
        break;
    }

    return false;
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
