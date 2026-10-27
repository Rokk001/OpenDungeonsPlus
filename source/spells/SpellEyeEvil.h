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

#ifndef SPELLEYEEVIL_H
#define SPELLEYEEVIL_H

#include "spells/Spell.h"
#include "spells/SpellType.h"

class GameMap;
class InputCommand;
class InputManager;

//! \brief Reveals an area through a researched spell or an exact unmodified ghost reveal.
class SpellEyeEvil : public Spell
{
public:
    //! \brief Creates the ordinary eye with its configured base duration.
    SpellEyeEvil(GameMap* gameMap);
    virtual ~SpellEyeEvil();

    SpellType getSpellType() const override
    { return SpellType::eyeEvil; }

    //! \brief Reveals the researched radius or the persisted free-reveal radius.
    void computeVisibleTiles() override;
    //! \brief Advances the lifetime while retaining the exact free-reveal remainder for saving.
    void doUpkeep() override;
    //! \brief Creates a free eye with base radius and the supplied unmodified duration.
    static SpellEyeEvil* spawnFree(GameMap* map, Seat* seat, Tile* tile, int32_t turns);
    //! \brief Saves the ordinary placement and optional free-reveal continuation.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Restores the optional free-reveal mode without consuming a following record.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends the free-reveal mode and remaining lifetime with the eye.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Restores the complete eye packet.
    void importFromPacket(ODPacket& packet) override;

    static void checkSpellCast(GameMap* gameMap, const InputManager& inputManager, InputCommand& inputCommand);
    static bool castSpell(GameMap* gameMap, Player* player, ODPacket& packet);

    //! \brief Loads a valid eye record, including optional free-reveal continuation.
    static Spell* getSpellFromStream(GameMap* gameMap, std::istream &is);
    static Spell* getSpellFromPacket(GameMap* gameMap, ODPacket &is);

    static const SpellType mSpellType;
private:
    bool mFreeMode;
    uint32_t mFreeRadius;
    int32_t mFreeTurns;
};

#endif // SPELLEYEEVIL_H
