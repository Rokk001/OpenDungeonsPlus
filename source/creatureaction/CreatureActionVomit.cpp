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

#include "creatureaction/CreatureActionVomit.h"

#include "entities/Creature.h"
#include "entities/DirtPileEntity.h"
#include "entities/Tile.h"
#include "gamemap/GameMap.h"
#include "network/CosmeticEvent.h"
#include "rooms/RoomTavern.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"

std::function<bool()> CreatureActionVomit::action() // allowed-lambda: signature required by CreatureAction
{
    return std::bind(&CreatureActionVomit::handleVomit, this);
}

bool CreatureActionVomit::handleVomit()
{
    Tile* myTile = mCreature.getPositionTile();
    if(myTile == nullptr)
    {
        OD_LOG_ERR("creature=" + mCreature.getName());
        mCreature.popAction();
        return true;
    }

    // First turn: stop where the creature stands and play the clip
    if(mTurnsLeft < 0)
    {
        mTurnsLeft = static_cast<int32_t>(ConfigManager::getSingleton().getTavernConfigDouble("DrinkTurns"));
        if(mCreature.isMoving())
            mCreature.clearDestinations(EntityAnimation::vomit_anim, true, false);
        mCreature.setAnimationState(EntityAnimation::vomit_anim, true, Ogre::Vector3::ZERO, false);
    }

    --mTurnsLeft;
    if(mTurnsLeft > 0)
        return false;

    // Done: the vomit stays on the floor until a worker cleans it
    DirtPileEntity::createOnTile(mCreature.getGameMap(), myTile, DirtPileKind::vomit, std::string());
    RoomTavern::sendTavernEvent(mCreature, static_cast<int32_t>(CosmeticTavernKind::vomit), nullptr);
    mCreature.setAnimationState(EntityAnimation::idle_anim, true);
    mCreature.popAction();
    return true;
}
