/*!
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

#ifndef KEEPERAITYPE_H
#define KEEPERAITYPE_H

#include <string>
#include <array>

enum class KeeperAIType
{
   easy,
   normal,
   hard,
   medium,
   hell,
   nbAI              // Must be the last in this enum
};

namespace KeeperAITypes
{
    //! \brief Returns the levels in the order shown to players.
    static const std::array<KeeperAIType, 5> displayOrder = {{ KeeperAIType::easy, KeeperAIType::medium, KeeperAIType::normal, KeeperAIType::hard, KeeperAIType::hell }};

    //! \brief Returns the stable name for an AI level without logging.
    inline const std::string& nameOf(KeeperAIType type)
    {
        static const std::string names[] = {"easy", "normal", "hard", "medium", "hell", "Wrong value"};
        const unsigned int index = static_cast<unsigned int>(type);
        return names[index < 5 ? index : 5];
    }

    KeeperAIType fromString(const std::string& type);
    const std::string& toString(KeeperAIType type);
    const std::string& toDisplayableString(KeeperAIType type);
}


#endif // KEEPERAITYPE_H
