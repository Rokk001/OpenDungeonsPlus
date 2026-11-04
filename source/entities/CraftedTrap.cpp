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

#include "entities/CraftedTrap.h"

#include "entities/Creature.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "network/ODPacket.h"
#include "gamemap/GameMap.h"
#include "traps/Trap.h"
#include "traps/TrapManager.h"
#include "traps/TrapType.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"
#include "utils/Random.h"

#include <iostream>
#include <sstream>
#include <string>
#include <vector>

CraftedTrap::CraftedTrap(GameMap* gameMap, const std::string& workshopName, TrapType trapType) :
    RenderedMovableEntity(gameMap, workshopName, TrapManager::getMeshFromTrapType(trapType), 0.0f, false),
    mTrapType(trapType)
{
}

CraftedTrap::CraftedTrap(GameMap* gameMap) :
    RenderedMovableEntity(gameMap)
{
}

GameEntityType CraftedTrap::getObjectType() const
{
    return GameEntityType::craftedTrap;
}

void CraftedTrap::notifyEntityCarryOn(Creature* carrier)
{
    removeEntityFromPositionTile();
    setSeat(carrier->getSeat());
}

void CraftedTrap::notifyEntityCarryOff(const Ogre::Vector3& position)
{
    mPosition = position;
    addEntityToPositionTile();
}

//! \brief Reads a crafted trap from a saved line; a line that cannot be read gives no trap.
CraftedTrap* CraftedTrap::getCraftedTrapFromStream(GameMap* gameMap, std::istream& is)
{
    CraftedTrap* obj = new CraftedTrap(gameMap);
    if(!obj->importFromStream(is))
    {
        OD_LOG_ERR("Invalid crafted trap record");
        delete obj;
        return nullptr;
    }
    return obj;
}

CraftedTrap* CraftedTrap::getCraftedTrapFromPacket(GameMap* gameMap, ODPacket& is)
{
    CraftedTrap* obj = new CraftedTrap(gameMap);
    obj->importFromPacket(is);
    return obj;
}

//! \brief Writes the entity fields, the trap type and the position, every field followed by its own tab.
void CraftedTrap::exportToStream(std::ostream& os) const
{
    RenderedMovableEntity::exportToStream(os);
    os << mTrapType << "\t" << mPosition.x << "\t" << mPosition.y << "\t" << mPosition.z << "\t";
}

//! \brief Reads the trap type and the position. Saves of older builds have no tab between the trap type and the
//! x position, so both are written as one number (type 1 and x 63 as 163): it is split again with the x position
//! that the entity fields hold.
bool CraftedTrap::importFromStream(std::istream& is)
{
    if(!RenderedMovableEntity::importFromStream(is))
        return false;

    const Ogre::Real headX = mPosition.x;
    std::vector<std::string> fields;
    std::string field;
    while(is >> field)
        fields.push_back(field);
    is.clear();

    std::string typeText;
    std::string xText;
    if(fields.size() >= 4)
    {
        typeText = fields[0];
        xText = fields[1];
        fields.erase(fields.begin(), fields.begin() + 2);
    }
    else if(fields.size() == 3)
    {
        // The written form of the head x position tells where the type ends
        std::ostringstream head;
        head << headX;
        const std::string headText = head.str();
        const std::string& glued = fields[0];
        if((glued.size() > headText.size()) && (glued.compare(glued.size() - headText.size(), headText.size(), headText) == 0))
        {
            typeText = glued.substr(0, glued.size() - headText.size());
            xText = headText;
        }
        else
        {
            // The position changed since: take the type as the one or two digits that leave a number behind
            const size_t typeDigits = (glued.size() > 2) ? 2 : 1;
            typeText = glued.substr(0, typeDigits);
            xText = glued.substr(typeDigits);
        }
        fields.erase(fields.begin());
    }
    else
        return false;

    std::istringstream typeStream(typeText);
    uint32_t typeNumber = 0;
    if(!(typeStream >> typeNumber) || !typeStream.eof() ||
       (typeNumber == static_cast<uint32_t>(TrapType::nullTrapType)) ||
       (typeNumber >= static_cast<uint32_t>(TrapType::nbTraps)))
        return false;

    std::istringstream positionStream(xText + " " + fields[0] + " " + fields[1]);
    Ogre::Vector3 position;
    if(!(positionStream >> position.x >> position.y >> position.z))
        return false;

    mTrapType = static_cast<TrapType>(typeNumber);
    mPosition = position;

    return true;
}

std::string CraftedTrap::getCraftedTrapStreamFormat()
{
    std::string format = RenderedMovableEntity::getRenderedMovableEntityStreamFormat();
    if(!format.empty())
        format += "\t";

    format += "trapType\tPosX\tPosY\tPosZ";

    return format;
}
