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

#ifndef CREATUREACTIONFIGHT_H
#define CREATUREACTIONFIGHT_H

#include "creatureaction/CreatureAction.h"
#include "entities/GameEntity.h"

class GameEntity;

class CreatureActionFight : public CreatureAction, public GameEntityListener
{
public:
    CreatureActionFight(Creature& creature, GameEntity* entityAttack, bool koOpponent, bool notifyPlayerIfHit);
    virtual ~CreatureActionFight();

    CreatureActionType getType() const override
    { return CreatureActionType::fight; }

    std::function<bool()> action() override;

    std::string getListenerName() const override;
    bool notifyDead(GameEntity* entity) override;
    bool notifyRemovedFromGameMap(GameEntity* entity) override;
    bool notifyPickedUp(GameEntity* entity) override;
    bool notifyDropped(GameEntity* entity) override;

    //! \brief Attacks the given target (or, without one, the best visible enemy) or walks towards it.
    //! While a level test scenario runs, the chosen target is reported to it.
    //! \return true if the action was removed and the next action should run in the same turn.
    static bool handleFight(Creature& creature, GameEntity* entityAttack, bool koOpponent, bool notifyPlayerIfHit);

private:
    GameEntity* mEntityAttack;
    bool mKoOpponent;
    bool mNotifyPlayerIfHit;
};

#endif // CREATUREACTIONFIGHT_H
