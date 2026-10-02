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

#ifndef SPELLTREMOR_H
#define SPELLTREMOR_H

#include "spells/Spell.h"
#include "spells/SpellType.h"

class GameMap;
class InputCommand;
class InputManager;

//! brief Shakes the ground around the target tile. Enemy creatures in the area take damage and are knocked down,
//! claimed enemy tiles (not rooms, traps, doors or bridges) turn back to dirt.
class SpellTremor : public Spell
{
public:
    static void checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand);
    static bool castSpell(GameMap* gameMap, Player* player, ODPacket& packet);

    static Spell* getSpellFromStream(GameMap* gameMap, std::istream &is);
    static Spell* getSpellFromPacket(GameMap* gameMap, ODPacket &is);

    static const SpellType mSpellType;
};

#endif // SPELLTREMOR_H
