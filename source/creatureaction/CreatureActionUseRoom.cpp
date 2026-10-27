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

#include "creatureaction/CreatureActionUseRoom.h"

#include "creatureaction/CreatureActionGetFee.h"
#include "creatureaction/CreatureActionSearchFood.h"
#include "creatureaction/CreatureActionSearchToilet.h"
#include "creatureaction/CreatureActionSearchDrink.h"
#include "creatureaction/CreatureActionSearchJob.h"
#include "creatureaction/CreatureActionSleep.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "rooms/RoomTavern.h"
#include "utils/Helper.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/MakeUnique.h"
#include "utils/Random.h"

//! \brief Starts a room visit and records whether it is meant to improve mood.
CreatureActionUseRoom::CreatureActionUseRoom(Creature& creature, Room& room, bool forced, bool moodRoom) :
    CreatureAction(creature),
    mRoom(&room),
    mForced(forced),
    mMoodRoom(moodRoom)
{
    mRoom->addGameEntityListener(this);
    if(!mRoom->addCreatureUsingRoom(&mCreature))
    {
        OD_LOG_ERR("creature=" + mCreature.getName() + ", cannot work in room=" + mRoom->getName());
    }
    else
    {
        OD_LOG_INF("creature=" + mCreature.getName() + " starts using room=" + mRoom->getName());
    }
}

CreatureActionUseRoom::~CreatureActionUseRoom()
{
    OD_LOG_INF("creature=" + mCreature.getName() + " stops using room=" + (mRoom != nullptr ? mRoom->getName() : std::string("unknown")));
    if(mRoom != nullptr)
    {
        mRoom->removeGameEntityListener(this);
        mRoom->removeCreatureUsingRoom(&mCreature);
    }
}

void CreatureActionUseRoom::changeRoom(Room& room)
{
    if(mRoom != nullptr)
        mRoom->removeGameEntityListener(this);

    mRoom = &room;
    mRoom->addGameEntityListener(this);
}

//! \brief Returns the room action with its mood-visit state.
std::function<bool()> CreatureActionUseRoom::action()
{
    return std::bind(&CreatureActionUseRoom::handleJob,
        std::ref(mCreature), mRoom, mForced, mMoodRoom);
}

//! \brief Runs room use while responding to mood and urgent needs.
bool CreatureActionUseRoom::handleJob(Creature& creature, Room* room, bool forced, bool moodRoom)
{
    // Current creature tile position
    Tile* myTile = creature.getPositionTile();
    if (myTile == nullptr)
    {
        creature.popAction();
        return false;
    }

    // If the room is not available, we stop working
    if(room == nullptr)
    {
        creature.popAction();
        return true;
    }

    const bool servingNeed = room->getType() == RoomType::hatchery ||
        (room->getType() == RoomType::tavern && static_cast<RoomTavern*>(room)->isGuestDrinking(creature));
    if(creature.needInterrupt(servingNeed))
    {
        creature.popAction();
        if(creature.getUrge() >= ConfigManager::getSingleton().getDirtConfigDouble("UrgeSeek"))
            creature.pushAction(Utils::make_unique<CreatureActionSearchToilet>(creature));
        else if(creature.isHungry())
            creature.pushAction(Utils::make_unique<CreatureActionSearchFood>(creature, false));
        else
            creature.pushAction(Utils::make_unique<CreatureActionSearchDrink>(creature, false));
        return true;
    }

    if(!creature.decreaseJobCooldown())
        return false;

    if(moodRoom && creature.getMoodValue() <= CreatureMoodLevel::Neutral)
    {
        creature.popAction();
        return true;
    }

    // If we are working in the room, we check that our status (mood/hungry/sleepy)
    // allows us to work
    const RoomType roomType = room->getType();
    const bool pleasure = roomType == RoomType::casino || roomType == RoomType::tavern ||
        roomType == RoomType::spa || roomType == RoomType::temple;
    if(!pleasure && room->shouldNotUseIfBadMood(creature, forced))
    {
        if(creature.getMoodValue() >= CreatureMoodLevel::Upset ||
           creature.getMissedWages() >= ConfigManager::getSingleton().getUnpaidWagesStopWork())
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSearchJob>(creature, false));
            return true;
        }
    }

    // We check if we are on a room tile. If not, we will go to one
    if(myTile->getCoveringRoom() != room)
    {
        Tile* dest = room->getCoveredTile(0);
        if(dest == nullptr)
        {
            // No tile to go to !
            OD_LOG_ERR("creature=" + creature.getName() + ", room=" + room->getName());
            creature.popAction();
            return true;
        }

        if(!creature.setDestination(dest))
        {
            creature.popAction();
            return false;
        }

        return true;
    }

    // If we are tired/hungry, we go to bed/eat unless we are forced to work
    if((room->shouldStopUseIfHungrySleepy(creature, forced)) &&
       (!creature.hasSlapEffect()))
    {
        // The creature should look for gold after payday if the keeper is not broke
        if((creature.getGoldFee() > 0) &&
           (!creature.hasActionBeenTried(CreatureActionType::getFee)) &&
           (creature.getSeat()->getGold() > 0))
        {
            creature.pushAction(Utils::make_unique<CreatureActionGetFee>(creature));
            return true;
        }

        if (creature.isTired())
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
            return true;
        }

        // If we are hungry, we look for food
        if (creature.isHungry())
        {
            creature.popAction();
            creature.pushAction(Utils::make_unique<CreatureActionSearchFood>(creature, false));
            return true;
        }
    }

    return room->useRoom(creature, forced);
}

std::string CreatureActionUseRoom::getListenerName() const
{
    return toString(getType()) + ", creature=" + mCreature.getName();
}

bool CreatureActionUseRoom::notifyDead(GameEntity* entity)
{
    if(entity == mRoom)
    {
        OD_LOG_INF("creature=" + mCreature.getName() + " removed from dead room=" + mRoom->getName());
        mRoom->removeCreatureUsingRoom(&mCreature);
        mRoom = nullptr;
        return false;
    }
    return true;
}

bool CreatureActionUseRoom::notifyRemovedFromGameMap(GameEntity* entity)
{
    if(entity == mRoom)
    {
        OD_LOG_INF("creature=" + mCreature.getName() + " removed from removed from gamemap room=" + mRoom->getName());
        mRoom->removeCreatureUsingRoom(&mCreature);
        mRoom = nullptr;
        return false;
    }
    return true;
}

bool CreatureActionUseRoom::notifyPickedUp(GameEntity* entity)
{
    // That should not happen since we are listening to a room
    OD_LOG_ERR(toString(getType()) + ", creature=" + mCreature.getName() + ", entity=" + entity->getName());
    return true;
}

bool CreatureActionUseRoom::notifyDropped(GameEntity* entity)
{
    // That should not happen since we are listening to a room
    OD_LOG_ERR(toString(getType()) + ", creature=" + mCreature.getName() + ", entity=" + entity->getName());
    return true;
}
