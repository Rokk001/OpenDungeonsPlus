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

#include "entities/Creature.h"
#include "entities/Tile.h"
#include "entities/TreasuryObject.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

#include <iostream>

// Proposed values, they need to be approved
static const uint32_t DEFAULT_AMOUNT_MANA = 50000;
static const uint32_t DEFAULT_AMOUNT_GOLD = 10000;
static const uint32_t DEFAULT_AMOUNT_REVEAL_TURNS = 90;
static const uint32_t DEFAULT_AMOUNT_LEVELS = 1;

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
        case GiftBoxType::revealMap:
            return DEFAULT_AMOUNT_REVEAL_TURNS;
        case GiftBoxType::levelUp:
            return DEFAULT_AMOUNT_LEVELS;
        case GiftBoxType::healAll:
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
            seat->addRevealMapTurns(mAmount);
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
        default:
            OD_LOG_ERR("Unexpected GiftBoxType=" + Helper::toString(static_cast<uint32_t>(getGiftBoxType())));
            break;
    }
}
