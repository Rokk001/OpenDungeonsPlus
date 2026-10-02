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

#include "gamemap/LevelScriptRunner.h"

#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Campaign.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "gamemap/LevelScript.h"
#include "goals/Goal.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "ODApplication.h"
#include "rooms/Room.h"
#include "rooms/RoomManager.h"
#include "rooms/RoomType.h"
#include "spells/Spell.h"
#include "spells/SpellCallToWar.h"
#include "spells/SpellType.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <algorithm>
#include <vector>

namespace
{

int64_t secondsToTurns(int64_t seconds)
{
    return static_cast<int64_t>(static_cast<double>(seconds) * ODApplication::turnsPerSecond);
}

bool isSeatMatching(const Creature* creature, int32_t seatId)
{
    if(seatId < 0)
        return true;

    return (creature->getSeat() != nullptr) && (creature->getSeat()->getId() == seatId);
}

bool isConditionMet(GameMap& gameMap, const LevelScript& script, const LevelScriptCondition& cond)
{
    switch(cond.mType)
    {
        case LevelScriptConditionType::time:
            return gameMap.getTurnNumber() >= secondsToTurns(cond.mNumber);
        case LevelScriptConditionType::region:
        {
            LevelScriptRegion area(cond.mName, cond.mX1, cond.mY1, cond.mX2, cond.mY2);
            if(!cond.mName.empty())
            {
                const LevelScriptRegion* region = script.getRegion(cond.mName);
                if(region == nullptr)
                {
                    OD_LOG_ERR("Level script: unknown region name=" + cond.mName);
                    return false;
                }
                area = *region;
            }
            for(Creature* creature : gameMap.getCreatures())
            {
                if(!creature->isAlive())
                    continue;

                if(!isSeatMatching(creature, cond.mSeatId))
                    continue;

                Tile* tile = creature->getPositionTile();
                if(tile == nullptr)
                    continue;

                if(area.contains(tile->getX(), tile->getY()))
                    return true;
            }
            return false;
        }
        case LevelScriptConditionType::creatures:
        {
            int64_t count = 0;
            for(Creature* creature : gameMap.getCreatures())
            {
                if(!creature->isAlive())
                    continue;

                if(isSeatMatching(creature, cond.mSeatId))
                    ++count;
            }
            if(cond.mAtLeast)
                return count >= cond.mNumber;

            return count <= cond.mNumber;
        }
        case LevelScriptConditionType::room:
        {
            Seat* seat = gameMap.getSeatById(cond.mSeatId);
            if(seat == nullptr)
                return false;

            RoomType roomType = RoomManager::getRoomTypeFromRoomName(cond.mName);
            if(roomType == RoomType::nullRoomType)
            {
                OD_LOG_ERR("Level script: unknown room name=" + cond.mName);
                return false;
            }
            return static_cast<int64_t>(seat->getNbRooms(roomType)) >= cond.mNumber;
        }
        case LevelScriptConditionType::goal:
        {
            Seat* seat = gameMap.getSeatById(cond.mSeatId);
            if(seat == nullptr)
                return false;

            for(unsigned int i = 0; i < seat->numCompletedGoals(); ++i)
            {
                if(seat->getCompletedGoal(i)->getName() == cond.mName)
                    return true;
            }
            return false;
        }
        case LevelScriptConditionType::flag:
            return script.getFlag(cond.mName) == cond.mNumber;
        case LevelScriptConditionType::gold:
        case LevelScriptConditionType::mana:
        case LevelScriptConditionType::kills:
        case LevelScriptConditionType::goldMined:
        {
            Seat* seat = gameMap.getSeatById(cond.mSeatId);
            if(seat == nullptr)
                return false;

            int64_t amount = 0;
            if(cond.mType == LevelScriptConditionType::gold)
                amount = static_cast<int64_t>(seat->getGold());
            else if(cond.mType == LevelScriptConditionType::mana)
                amount = static_cast<int64_t>(seat->getMana());
            else if(cond.mType == LevelScriptConditionType::kills)
                amount = static_cast<int64_t>(seat->getStatistics().mCreaturesKilled);
            else
                amount = static_cast<int64_t>(seat->getGoldMined());

            if(cond.mAtLeast)
                return amount >= cond.mNumber;

            return amount <= cond.mNumber;
        }
        case LevelScriptConditionType::claimed:
        {
            Seat* seat = gameMap.getSeatById(cond.mSeatId);
            const LevelScriptRegion* region = script.getRegion(cond.mName);
            if(seat == nullptr)
                return false;

            if(region == nullptr)
            {
                OD_LOG_ERR("Level script: unknown region name=" + cond.mName);
                return false;
            }

            int64_t numTiles = 0;
            int64_t numClaimed = 0;
            for(int32_t x = std::min(region->mX1, region->mX2); x <= std::max(region->mX1, region->mX2); ++x)
            {
                for(int32_t y = std::min(region->mY1, region->mY2); y <= std::max(region->mY1, region->mY2); ++y)
                {
                    Tile* tile = gameMap.getTile(x, y);
                    if(tile == nullptr)
                        continue;

                    ++numTiles;
                    if(tile->isClaimedForSeat(seat))
                        ++numClaimed;
                }
            }
            if(cond.mNumber < 0)
                return (numTiles > 0) && (numClaimed == numTiles);

            return numClaimed >= cond.mNumber;
        }
    }
    return false;
}

//! \brief The players an action is meant for: the player of the seat or, with seat -1,
//! every human player that did not lose.
std::vector<Player*> getTargetPlayers(GameMap& gameMap, int32_t seatId)
{
    std::vector<Player*> players;
    if(seatId >= 0)
    {
        Player* player = gameMap.getPlayerBySeatId(seatId);
        if((player != nullptr) && player->getIsHuman())
            players.push_back(player);

        return players;
    }

    for(Player* player : gameMap.getPlayers())
    {
        if(player->getIsHuman() && !player->getHasLost())
            players.push_back(player);
    }
    return players;
}

void sendMessage(GameMap& gameMap, int32_t seatId, const std::string& text)
{
    for(Player* player : getTargetPlayers(gameMap, seatId))
    {
        ServerNotification* serverNotification = new ServerNotification(
            ServerNotificationType::chatServer, player);
        serverNotification->mPacket << text << EventShortNoticeType::majorGameEvent;
        ODServer::getSingleton().queueServerNotification(serverNotification);
    }
}

void spawnCreatures(GameMap& gameMap, const LevelScriptAction& action)
{
    Seat* seat = gameMap.getSeatById(action.mSeatId);
    if(seat == nullptr)
    {
        OD_LOG_ERR("Level script: spawn on unknown seat id=" + Helper::toString(action.mSeatId));
        return;
    }

    Tile* tile = gameMap.getTile(action.mX, action.mY);
    if(tile == nullptr)
    {
        OD_LOG_ERR("Level script: spawn on unknown tile " + Helper::toString(action.mX) + "," + Helper::toString(action.mY));
        return;
    }

    Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()), static_cast<Ogre::Real>(tile->getY()), 0.0f);
    uint32_t maxCreatures = ConfigManager::getSingleton().getMaxCreaturesPerSeatAbsolute();
    uint32_t numCreatures = seat->getNumCreaturesFighters();
    // Same rule as the wave portals: only the absolute creature limit counts
    for(const std::pair<std::string, uint32_t>& p : action.mCreatures)
    {
        if(numCreatures >= maxCreatures)
            break;

        const CreatureDefinition* classToSpawn = gameMap.getClassDescription(p.first);
        if(classToSpawn == nullptr)
        {
            OD_LOG_ERR("Level script: wrong creature class=" + p.first);
            continue;
        }

        Creature* newCreature = new Creature(&gameMap, classToSpawn, seat, spawnPosition);
        newCreature->setLevel(p.second);
        newCreature->setHP(newCreature->getMaxHp());

        OD_LOG_INF("Level script spawns a creature class=" + classToSpawn->getClassName()
            + ", name=" + newCreature->getName() + ", seatId=" + Helper::toString(seat->getId()));

        newCreature->addToGameMap();
        newCreature->createMesh();
        newCreature->setPosition(newCreature->getPosition());
        ++numCreatures;
    }

    if(action.mTargetSeatId < 0)
        return;

    // As the wave portals do, the group is sent to the dungeon of the target seat with a call to war.
    // If there already is one, it is not replaced.
    for(Spell* spell : gameMap.getSpells())
    {
        if(spell->getSpellType() == SpellType::callToWar)
            return;
    }

    for(Room* room : gameMap.getRoomsByType(RoomType::dungeonTemple))
    {
        if(room->getSeat()->getId() != action.mTargetSeatId)
            continue;

        Tile* targetTile = room->getCentralTile();
        if(targetTile == nullptr)
            continue;

        SpellCallToWar* spell = new SpellCallToWar(&gameMap);
        spell->setSeat(seat);
        spell->addToGameMap();
        Ogre::Vector3 targetPosition(static_cast<Ogre::Real>(targetTile->getX()),
                                     static_cast<Ogre::Real>(targetTile->getY()),
                                     static_cast<Ogre::Real>(0.0));
        spell->createMesh();
        spell->setPosition(targetPosition);
        return;
    }
}

//! \brief The tiles of the region stay visible to the seat, as the tiles revealed by a
//! tortured creature do: they are shown once and then count as seen.
void revealRegion(GameMap& gameMap, const LevelScript& script, const LevelScriptAction& action)
{
    const LevelScriptRegion* region = script.getRegion(action.mText);
    if(region == nullptr)
    {
        OD_LOG_ERR("Level script: reveal of unknown region name=" + action.mText);
        return;
    }

    std::vector<Tile*> tiles;
    for(int32_t x = std::min(region->mX1, region->mX2); x <= std::max(region->mX1, region->mX2); ++x)
    {
        for(int32_t y = std::min(region->mY1, region->mY2); y <= std::max(region->mY1, region->mY2); ++y)
        {
            Tile* tile = gameMap.getTile(x, y);
            if(tile != nullptr)
                tiles.push_back(tile);
        }
    }

    for(Player* player : getTargetPlayers(gameMap, action.mSeatId))
        player->getSeat()->revealTiles(tiles, 1);
}

void runAction(GameMap& gameMap, LevelScript& script, const LevelScriptAction& action)
{
    switch(action.mType)
    {
        case LevelScriptActionType::message:
            sendMessage(gameMap, action.mSeatId, action.mText);
            break;
        case LevelScriptActionType::objective:
            sendMessage(gameMap, action.mSeatId, "Objective: " + action.mText);
            break;
        case LevelScriptActionType::spawn:
            spawnCreatures(gameMap, action);
            break;
        case LevelScriptActionType::gold:
        {
            for(Player* player : getTargetPlayers(gameMap, action.mSeatId))
                gameMap.addGoldToSeat(static_cast<int>(action.mNumber), player->getSeat()->getId());

            break;
        }
        case LevelScriptActionType::setFlag:
            script.setFlag(action.mText, action.mNumber);
            break;
        case LevelScriptActionType::addFlag:
            script.setFlag(action.mText, script.getFlag(action.mText) + action.mNumber);
            break;
        case LevelScriptActionType::win:
        {
            for(Player* player : getTargetPlayers(gameMap, action.mSeatId))
                gameMap.addWinningSeat(player->getSeat());

            break;
        }
        case LevelScriptActionType::lose:
        {
            for(Player* player : getTargetPlayers(gameMap, action.mSeatId))
                player->notifyNoMoreDungeonTemple();

            break;
        }
        case LevelScriptActionType::reveal:
            revealRegion(gameMap, script, action);
            break;
        case LevelScriptActionType::discoverLevel:
        {
            if(Campaign::getSingleton().discoverBonusLevel(action.mText))
                sendMessage(gameMap, -1, "You have found a hidden land. Go there when you have conquered this land.");

            break;
        }
    }
}

} // namespace

void LevelScriptRunner::doTurn(GameMap& gameMap)
{
    LevelScript& script = gameMap.getLevelScript();
    int64_t turn = gameMap.getTurnNumber();
    for(LevelScriptTrigger& trigger : script.getTriggers())
    {
        if(trigger.mTimesFired > 0)
        {
            if(!trigger.mRepeat)
                continue;

            if(turn < trigger.mLastFiredTurn + secondsToTurns(trigger.mCooldownSeconds))
                continue;
        }

        bool isMet = true;
        for(const LevelScriptCondition& cond : trigger.mConditions)
        {
            if(!isConditionMet(gameMap, script, cond))
            {
                isMet = false;
                break;
            }
        }

        if(!isMet)
            continue;

        OD_LOG_INF("Level script trigger fired: " + trigger.mName);
        ++trigger.mTimesFired;
        trigger.mLastFiredTurn = turn;
        for(const LevelScriptAction& action : trigger.mActions)
            runAction(gameMap, script, action);
    }
}
