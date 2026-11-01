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

#ifndef CREATUREACTIONUSEROOM_H
#define CREATUREACTIONUSEROOM_H

#include "creatureaction/CreatureAction.h"
#include "entities/GameEntity.h"

class Room;

class CreatureActionUseRoom : public CreatureAction, public GameEntityListener
{
public:
    //! \brief Starts room use, optionally to improve a bad mood.
    CreatureActionUseRoom(Creature& creature, Room& room, bool forced, bool moodRoom = false);
    virtual ~CreatureActionUseRoom();

    CreatureActionType getType() const override
    { return CreatureActionType::useRoom; }

    Room* getRoom() const
    { return mRoom; }

    //! \brief Moves the action to another room without leaving the old one through removeCreatureUsingRoom. The caller
    //! has already registered the creature with the new room (used when a room absorbs another one and keeps its users).
    //! \param room The room the creature goes on using.
    void changeRoom(Room& room);

    std::function<bool()> action() override;

    std::string getListenerName() const override;
    bool notifyDead(GameEntity* entity) override;
    bool notifyRemovedFromGameMap(GameEntity* entity) override;
    bool notifyPickedUp(GameEntity* entity) override;
    bool notifyDropped(GameEntity* entity) override;

    //! \brief Runs a room visit and its interruptions.
    static bool handleJob(Creature& creature, Room* room, bool forced, bool moodRoom);

private:
    Room* mRoom;
    bool mForced;
    bool mMoodRoom;
};

#endif // CREATUREACTIONUSEROOM_H
