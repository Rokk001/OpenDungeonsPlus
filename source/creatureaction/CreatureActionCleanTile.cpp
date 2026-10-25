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

#include "creatureaction/CreatureActionCleanTile.h"

#include "entities/Creature.h"
#include "entities/DirtPileEntity.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "rooms/Room.h"
#include "utils/ConfigManager.h"
#include "utils/Helper.h"
#include "utils/LogManager.h"

CreatureActionCleanTile::CreatureActionCleanTile(Creature& creature, Tile& tileClean) :
    CreatureAction(creature),
    mTileClean(tileClean)
{
}

CreatureActionCleanTile::~CreatureActionCleanTile()
{
}

std::function<bool()> CreatureActionCleanTile::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionCleanTile::handleCleanTile,
        std::ref(mCreature), std::ref(mTileClean), getNbTurnsActive());
}

//! \brief Takes the cleaning work off the first thing that lies on the tile: pile, vomit, blood stain, floor dirt.
//! \param tile The tile that is cleaned.
//! \param cleanRate The cleaning work of this turn.
static void cleanTileStep(Tile& tile, double cleanRate)
{
    DirtPileEntity* pile = DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::pile);
    if(pile != nullptr)
    {
        // The entity may delete itself here, it is not used afterwards
        pile->cleanBy(cleanRate);
        return;
    }

    DirtPileEntity* vomit = DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::vomit);
    if(vomit != nullptr)
    {
        // Vomit is cleaned like a pile
        vomit->cleanBy(cleanRate);
        return;
    }

    DirtPileEntity* stain = DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::blood);
    if(stain != nullptr)
    {
        stain->cleanBy(cleanRate);
        return;
    }

    tile.cleanDirt(cleanRate);
}

//! \brief Tells whether nothing is left to clean on the tile.
static bool isTileClean(const Tile& tile)
{
    return (DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::pile) == nullptr) &&
        (DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::vomit) == nullptr) &&
        (DirtPileEntity::getEntityOnTile(&tile, DirtPileKind::blood) == nullptr) &&
        (tile.getDirt() <= 0.0);
}

bool CreatureActionCleanTile::handleCleanTile(Creature& creature, Tile& tileClean, int32_t nbTurns)
{
    Tile* myTile = creature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + creature.getName() + ", pos=" + Helper::toString(creature.getPosition()));
        creature.popAction();
        return true;
    }

    ConfigManager& config = ConfigManager::getSingleton();

    // Somebody else was faster, the tile changed hands or the worker has cleaned it long enough
    if((tileClean.getSeat() != creature.getSeat()) || isTileClean(tileClean) ||
       (nbTurns >= static_cast<int32_t>(config.getDirtConfigDouble("CleaningMaxTurnsPerTile"))))
    {
        creature.popAction();
        return true;
    }

    // We check if we are on the expected tile. If not, we go there
    if(myTile != &tileClean)
    {
        if(!creature.setDestination(&tileClean))
        {
            creature.popAction();
            return true;
        }

        return true;
    }

    // The scrubbing sound plays once when the worker starts cleaning a tile, not on every turn of the work
    if(creature.getAnimationStateName() != EntityAnimation::clean_anim)
        creature.fireCreatureSound(CreatureSound::Clean);

    creature.setAnimationState(EntityAnimation::clean_anim);
    // The cleaning work per turn: the claim rate of the worker as a share of the whole dirt range
    double cleanRate = creature.getClaimRate() * Tile::MAX_DIRT * config.getDirtConfigDouble("CleanRateFactor");
    cleanTileStep(tileClean, cleanRate);

    // Since we wiped a tile we are done for this turn
    return false;
}
