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

#ifndef GIFTBOXBONUS_H
#define GIFTBOXBONUS_H

#include "entities/GiftBoxEntity.h"

#include <string>
#include <iosfwd>

//! \brief A gift box giving one of the one-shot bonuses: extra mana, extra gold, a
//! temporary view of the whole map or a level for the creatures of the seat that brings
//! the box to its dungeon temple. The type is one of GiftBoxType::mana, gold, revealMap
//! and levelUp. The meaning of the amount depends on the type: mana points, gold coins,
//! number of turns the map stays revealed, number of levels given. The type healAll heals
//! every creature of the seat completely (the amount is not used). The types makeSafe, weakenWalls,
//! stunImps, makeHappy, makeUnhappy and killCreatures do not use the amount either, receiveImps uses it
//! as the number of imps.
class GiftBoxBonus: public GiftBoxEntity
{
public:
    GiftBoxBonus(GameMap* gameMap, const std::string& baseName, GiftBoxType type, uint32_t amount);
    GiftBoxBonus(GameMap* gameMap, GiftBoxType type);

    virtual void applyEffect() override;

    //! \brief The amount used when a box is placed in the editor
    static uint32_t getDefaultAmount(GiftBoxType type);

protected:
    virtual void exportToStream(std::ostream& os) const override;
    virtual bool importFromStream(std::istream& is) override;

private:
    uint32_t mAmount;
};

#endif // GIFTBOXBONUS_H
