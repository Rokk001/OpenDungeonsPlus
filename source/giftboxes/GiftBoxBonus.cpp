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

#include "giftboxes/GiftBoxBonus.h"

#include "ODApplication.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "entities/TreasuryObject.h"
#include "game/Seat.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <cmath>
#include <iostream>

// Proposed values, they need to be approved
static const uint32_t DEFAULT_AMOUNT_MANA = 50000;
static const uint32_t DEFAULT_AMOUNT_GOLD = 10000;
static const uint32_t DEFAULT_AMOUNT_LEVELS = 1;
static const uint32_t DEFAULT_AMOUNT_IMPS = 10;
//! Imps received with the upgraded Create Imp spell start at this level
static const uint32_t LEVEL_IMPS_UPGRADED = 4;
//! Skill level of the Create Imp spell from which it counts as upgraded
static const uint32_t SKILL_LEVEL_UPGRADED = 2;
//! Stun Imps: the enemy imps stay down for this many seconds
static const double STUN_IMPS_SECONDS = 5.0;

GiftBoxBonus::GiftBoxBonus(GameMap* gameMap, const std::string& baseName, GiftBoxType type, uint32_t amount) :
    GiftBoxEntity(gameMap, baseName, "MysteryBox", type),
    mAmount(amount)
{
    mPrevAnimationState = "Loop";
    mPrevAnimationStateLoop = true;
}

GiftBoxBonus::GiftBoxBonus(GameMap* gameMap, GiftBoxType type) :
    GiftBoxEntity(gameMap, type),
    mAmount(0)
{
}

uint32_t GiftBoxBonus::getDefaultAmount(GiftBoxType type)
{
    switch(type)
    {
        case GiftBoxType::mana:
            return DEFAULT_AMOUNT_MANA;
        case GiftBoxType::gold:
            return DEFAULT_AMOUNT_GOLD;
        case GiftBoxType::levelUp:
            return DEFAULT_AMOUNT_LEVELS;
        case GiftBoxType::receiveImps:
            return DEFAULT_AMOUNT_IMPS;
        case GiftBoxType::revealMap:
        case GiftBoxType::healAll:
        case GiftBoxType::makeSafe:
        case GiftBoxType::weakenWalls:
        case GiftBoxType::stunImps:
        case GiftBoxType::makeHappy:
        case GiftBoxType::makeUnhappy:
        case GiftBoxType::killCreatures:
            return 0;
        default:
            OD_LOG_ERR("Unexpected GiftBoxType=" + Helper::toString(static_cast<uint32_t>(type)));
            return 0;
    }
}

void GiftBoxBonus::exportToStream(std::ostream& os) const
{
    GiftBoxEntity::exportToStream(os);
    os << mAmount << "\t";
}

bool GiftBoxBonus::importFromStream(std::istream& is)
{
    if(!GiftBoxEntity::importFromStream(is))
        return false;
    if(!(is >> mAmount))
        return false;

    return true;
}

void GiftBoxBonus::applyEffect()
{
    Seat* seat = getSeat();
    if(seat == nullptr)
    {
        OD_LOG_ERR("null Seat for giftbox=" + getName() + " pos=" + Helper::toString(getPosition()));
        return;
    }

    switch(getGiftBoxType())
    {
        case GiftBoxType::mana:
        {
            getGameMap()->addManaToSeat(static_cast<int>(mAmount), seat->getId());
            break;
        }
        case GiftBoxType::gold:
        {
            // What the treasuries cannot hold is left on the ground where the box was
            int notStored = getGameMap()->addGoldToSeat(static_cast<int>(mAmount), seat->getId());
            Tile* tile = getPositionTile();
            if((notStored > 0) && (tile != nullptr))
            {
                TreasuryObject* obj = new TreasuryObject(getGameMap(), notStored);
                obj->addToGameMap();
                Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()),
                                            static_cast<Ogre::Real>(tile->getY()), 0.0f);
                obj->createMesh();
                obj->setPosition(spawnPosition);
            }
            break;
        }
        case GiftBoxType::revealMap:
        {
            seat->revealMapPermanently();
            break;
        }
        case GiftBoxType::levelUp:
        {
            std::vector<Creature*> creatures = getGameMap()->getCreaturesBySeat(seat);
            for(Creature* creature : creatures)
            {
                if(!creature->isAlive())
                    continue;

                creature->setLevel(creature->getLevel() + mAmount);
            }
            break;
        }
        case GiftBoxType::healAll:
        {
            std::vector<Creature*> creatures = getGameMap()->getCreaturesBySeat(seat);
            for(Creature* creature : creatures)
            {
                if(!creature->isAlive())
                    continue;

                creature->heal(creature->getMaxHp());
            }
            break;
        }
        case GiftBoxType::makeSafe:
        {
            // Every wall next to claimed ground of the seat that is not claimed yet becomes a reinforced wall
            for(int x = 0; x < getGameMap()->getMapSizeX(); ++x)
            {
                for(int y = 0; y < getGameMap()->getMapSizeY(); ++y)
                {
                    Tile* tile = getGameMap()->getTile(x, y);
                    if((tile == nullptr) || tile->isClaimed() || !tile->isWallClaimable(seat))
                        continue;

                    tile->claimTile(seat);
                }
            }
            break;
        }
        case GiftBoxType::weakenWalls:
        {
            // Reinforced enemy walls turn back to earth. Rooms, traps, doors and bridges are not affected
            for(int x = 0; x < getGameMap()->getMapSizeX(); ++x)
            {
                for(int y = 0; y < getGameMap()->getMapSizeY(); ++y)
                {
                    Tile* tile = getGameMap()->getTile(x, y);
                    if((tile == nullptr) || !tile->isFullTile() || !tile->isClaimed())
                        continue;

                    if(tile->getSeat()->isAlliedSeat(seat))
                        continue;

                    if((tile->getCoveringBuilding() != nullptr) || tile->getHasBridge())
                        continue;

                    tile->getSeat()->notifyTileClaimedByEnemy(tile);
                    tile->unclaimTile();
                }
            }
            break;
        }
        case GiftBoxType::stunImps:
        {
            int32_t nbTurns = static_cast<int32_t>(std::ceil(STUN_IMPS_SECONDS * ODApplication::turnsPerSecond));
            std::vector<Creature*> creatures = getGameMap()->getCreatures();
            for(Creature* creature : creatures)
            {
                if(!creature->isAlive() || !creature->getDefinition()->isWorker())
                    continue;

                if(creature->getSeat()->isAlliedSeat(seat))
                    continue;

                creature->stun(nbTurns);
            }
            break;
        }
        case GiftBoxType::receiveImps:
        {
            const CreatureDefinition* workerClass = seat->getWorkerClassToSpawn();
            Tile* tile = getPositionTile();
            if((workerClass == nullptr) || (tile == nullptr))
            {
                OD_LOG_ERR("No worker class or tile for giftbox=" + getName());
                break;
            }

            bool upgraded = (seat->getSkillLevel(SkillType::spellSummonWorker) >= SKILL_LEVEL_UPGRADED);
            for(uint32_t i = 0; i < mAmount; ++i)
            {
                Creature* newCreature = new Creature(getGameMap(), workerClass, seat);
                newCreature->addToGameMap();
                if(upgraded)
                    newCreature->setLevel(LEVEL_IMPS_UPGRADED);

                Ogre::Vector3 spawnPosition(static_cast<Ogre::Real>(tile->getX()),
                                            static_cast<Ogre::Real>(tile->getY()), 0.0f);
                newCreature->addParticleEffect("SummonWorker", 3);
                newCreature->createMesh();
                newCreature->setPosition(spawnPosition);
            }
            break;
        }
        case GiftBoxType::makeHappy:
        {
            std::vector<Creature*> creatures = getGameMap()->getCreaturesBySeat(seat);
            for(Creature* creature : creatures)
            {
                if(creature->isAlive())
                    creature->removeAnnoyance();
            }
            break;
        }
        case GiftBoxType::makeUnhappy:
        {
            std::vector<Creature*> creatures = getGameMap()->getCreatures();
            for(Creature* creature : creatures)
            {
                if(!creature->isAlive() || creature->getSeat()->isRogueSeat())
                    continue;

                if(creature->getSeat()->isAlliedSeat(seat))
                    continue;

                creature->makeUnhappy();
            }
            break;
        }
        case GiftBoxType::killCreatures:
        {
            // The reference lets the keeper pick the victim, here one visible enemy creature is chosen at random
            std::vector<Creature*> victims;
            std::vector<Creature*> creatures = getGameMap()->getCreatures();
            for(Creature* creature : creatures)
            {
                if(!creature->isAlive() || creature->getSeat()->isAlliedSeat(seat))
                    continue;

                Tile* pos = creature->getPositionTile();
                if((pos == nullptr) || !seat->hasVisionOnTile(pos))
                    continue;

                victims.push_back(creature);
            }
            if(victims.empty())
                break;

            Creature* victim = victims[Random::Int(0, static_cast<int>(victims.size()) - 1)];
            victim->takeDamage(nullptr, victim->getHP() + 1.0, 0.0, 0.0, 0.0, victim->getPositionTile(), false);
            break;
        }
        default:
            OD_LOG_ERR("Unexpected GiftBoxType=" + Helper::toString(static_cast<uint32_t>(getGiftBoxType())));
            break;
    }
}
