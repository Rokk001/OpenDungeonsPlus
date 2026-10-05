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

#include "entities/GiftBoxEntity.h"

#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "network/ODPacket.h"
#include "game/Skill.h"
#include "gamemap/GameMap.h"
#include "giftboxes/GiftBoxBonus.h"
#include "giftboxes/GiftBoxSkill.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <iostream>

const std::string EMPTY_STRING;

GiftBoxEntity::GiftBoxEntity(GameMap* gameMap, const std::string& baseName, const std::string& meshName, GiftBoxType type) :
    RenderedMovableEntity(gameMap, baseName, meshName, 0.0f, false, 1.0f),
    mGiftBoxType(type)
{
}

GiftBoxEntity::GiftBoxEntity(GameMap* gameMap) :
    RenderedMovableEntity(gameMap),
    mGiftBoxType(GiftBoxType::nbTypes)
{
}

GiftBoxEntity::GiftBoxEntity(GameMap* gameMap, GiftBoxType type) :
    RenderedMovableEntity(gameMap),
    mGiftBoxType(type)
{
}

GameEntityType GiftBoxEntity::getObjectType() const
{
    return GameEntityType::giftBoxEntity;
}

void GiftBoxEntity::notifyEntityCarryOn(Creature* carrier)
{
    removeEntityFromPositionTile();
    setSeat(carrier->getSeat());
}

void GiftBoxEntity::notifyEntityCarryOff(const Ogre::Vector3& position)
{
    mPosition = position;
    addEntityToPositionTile();
}

bool GiftBoxEntity::tryPickup(Seat* seat)
{
    if(!getIsOnMap())
        return false;

    // We can pickup gift boxes only in editor mode
    return getGameMap()->isInEditorMode();
}

bool GiftBoxEntity::tryDrop(Seat* seat, Tile* tile)
{
    if(tile->isFullTile())
        return false;

    // In editor mode, we allow to drop a gift box in dirt, claimed, gold or rock tiles
    if(getGameMap()->isInEditorMode() &&
       (tile->getTileVisual() == TileVisual::dirtGround || tile->getTileVisual() == TileVisual::claimedGround ||
        tile->getTileVisual() == TileVisual::goldGround || tile->getTileVisual() == TileVisual::rockGround))
    {
        return true;
    }

    return false;
}

bool GiftBoxEntity::canSlap(Seat* seat)
{
    if(!getIsOnMap())
        return false;

    // In editor mode, we allow to slap a gift box to destroy it
    return getGameMap()->isInEditorMode();
}

void GiftBoxEntity::slap()
{
    if(!getIsOnServerMap())
        return;

    if(!getIsOnMap())
        return;

    if(!getGameMap()->isInEditorMode())
        return;

    removeFromGameMap();
    deleteYourself();
}

GiftBoxEntity* GiftBoxEntity::getGiftBoxEntityFromStream(GameMap* gameMap, std::istream& is)
{
    GiftBoxType type;
    is >> type;
    GiftBoxEntity* entity;
    switch(type)
    {
        case GiftBoxType::skill:
            entity = new GiftBoxSkill(gameMap);
            break;

        case GiftBoxType::mana:
        case GiftBoxType::gold:
        case GiftBoxType::revealMap:
        case GiftBoxType::levelUp:
        case GiftBoxType::healAll:
        case GiftBoxType::makeSafe:
        case GiftBoxType::weakenWalls:
        case GiftBoxType::stunImps:
        case GiftBoxType::receiveImps:
        case GiftBoxType::makeHappy:
        case GiftBoxType::makeUnhappy:
        case GiftBoxType::killCreatures:
            entity = new GiftBoxBonus(gameMap, type);
            break;

        default:
            OD_LOG_ERR("Unknown GiftBoxType=" + Helper::toString(static_cast<uint32_t>(type)));
            return nullptr;
    }

    entity->importFromStream(is);
    return entity;
}

GiftBoxEntity* GiftBoxEntity::getGiftBoxEntityFromPacket(GameMap* gameMap, ODPacket& is)
{
    // On client side, we always use a GiftBoxEntity because we don't want clients to know what the gift box is
    GiftBoxEntity* entity = new GiftBoxEntity(gameMap);
    entity->importFromPacket(is);
    return entity;
}

void GiftBoxEntity::exportHeadersToStream(std::ostream& os) const
{
    RenderedMovableEntity::exportHeadersToStream(os);
    os << mGiftBoxType << "\t";
}

std::string GiftBoxEntity::getGiftBoxEntityStreamFormat()
{
    std::string format = RenderedMovableEntity::getRenderedMovableEntityStreamFormat();
    if(!format.empty())
        format += "\t";

    format += "optionalData";

    return "GiftBoxType\t" + format;
}

std::ostream& operator<<(std::ostream& os, const GiftBoxType& type)
{
    os << static_cast<int32_t>(type);
    return os;
}

std::istream& operator>>(std::istream& is, GiftBoxType& type)
{
    int32_t tmp;
    OD_ASSERT_TRUE(is >> tmp);
    type = static_cast<GiftBoxType>(tmp);
    return is;
}
