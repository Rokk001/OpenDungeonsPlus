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

#include "creaturemood/CreatureMoodDirt.h"

#include "creaturemood/CreatureMoodManager.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/DirtPileEntity.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"

#include <cmath>

static const std::string CreatureMoodDirtName = "Dirt";

namespace
{
//! \brief Factory that creates CreatureMoodDirt objects.
class CreatureMoodDirtFactory : public CreatureMoodFactory
{
    //! \brief Creates a new CreatureMoodDirt.
    CreatureMood* createCreatureMood() const override
    { return new CreatureMoodDirt; }

    //! \brief Returns the configuration name of this modifier.
    const std::string& getCreatureMoodName() const override
    {
        return CreatureMoodDirtName;
    }
};

// Register the factory
static CreatureMoodRegister reg(new CreatureMoodDirtFactory);

//! \brief Tells whether the creature can feel dirt: it needs a seat, and a free hero marching through the dungeon
//! has no mood (a captured one is a prisoner of the keeper and does).
//! \param creature The creature to check.
bool canFeelDirt(const Creature& creature)
{
    const Seat* seat = creature.getSeat();
    if(seat == nullptr)
        return false;

    if(creature.isInPrison() || creature.isInContainment())
        return true;

    return !seat->isRogueSeat() && (seat->getFaction() != "Hero");
}

//! \brief The mood of the dirt stage of the room the creature stands in (0 at stage 1 and in a crypt).
//! \param tile The tile the creature stands on.
double getRoomDirtMood(const Tile& tile)
{
    const Room* room = tile.getCoveringRoom();
    if((room == nullptr) || (room->getType() == RoomType::crypt))
        return 0.0;

    // Stage 1 is clean and gives no mood
    uint32_t stage = room->getDirtStage();
    if(stage <= 1)
        return 0.0;

    if(stage == 2)
        return ConfigManager::getSingleton().getDirtConfigDouble("DirtMoodStage2");

    return ConfigManager::getSingleton().getDirtConfigDouble("DirtMoodStage3");
}

//! \brief The mood of the dirt piles (not blood) within DirtPileRadius tiles (Chebyshev distance) of a tile.
//! \param gameMap The map the tile belongs to.
//! \param tile The tile the creature stands on.
double getPileMood(const GameMap& gameMap, const Tile& tile)
{
    const ConfigManager& config = ConfigManager::getSingleton();
    int radius = static_cast<int>(config.getDirtConfigDouble("DirtPileRadius"));
    double pileMood = config.getDirtConfigDouble("DirtPileMood");
    double mood = 0.0;
    for(int xx = tile.getX() - radius; xx <= tile.getX() + radius; ++xx)
    {
        for(int yy = tile.getY() - radius; yy <= tile.getY() + radius; ++yy)
        {
            const Tile* neighbour = gameMap.getTile(xx, yy);
            if(neighbour == nullptr)
                continue;

            if(DirtPileEntity::getEntityOnTile(neighbour, DirtPileKind::pile) != nullptr)
                mood += pileMood;
        }
    }
    return mood;
}
}

//! \brief Returns the name under which this modifier is registered.
const std::string& CreatureMoodDirt::getModifierName() const
{
    return CreatureMoodDirtName;
}

//! \brief Room dirt stage mood plus pile mood, both times the Cleanliness of the creature type.
int32_t CreatureMoodDirt::computeMood(const Creature& creature) const
{
    if(!canFeelDirt(creature))
        return 0;

    const Tile* tile = creature.getPositionTile();
    const GameMap* gameMap = creature.getGameMap();
    if((tile == nullptr) || (gameMap == nullptr))
        return 0;

    double mood = getRoomDirtMood(*tile) + getPileMood(*gameMap, *tile);
    mood *= creature.getDefinition()->getCleanliness();
    return static_cast<int32_t>(std::lround(mood));
}

//! \brief Returns a copy of this modifier.
CreatureMoodDirt* CreatureMoodDirt::clone() const
{
    return new CreatureMoodDirt(*this);
}
