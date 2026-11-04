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

#ifndef CREATUREMOODPLEASURE_H
#define CREATUREMOODPLEASURE_H

#include <string>

//! \brief The pleasure rooms. A visit to one of them gives at most PleasureVisitMax mood inside the room, then a
//! pleasure buff, and closes that room (and only that room) for the creature for a while.
enum class PleasureRoomKind
{
    spa = 0,
    tavern,
    casino,
    temple,
    arena
};

namespace CreatureMoodPleasure
{
    //! \brief The name of the lock of a pleasure room in the saved block of the room locks.
    //! \param kind The pleasure room.
    //! \return The name without spaces.
    inline std::string lockName(PleasureRoomKind kind)
    {
        switch(kind)
        {
            case PleasureRoomKind::spa:
                return "Spa";
            case PleasureRoomKind::tavern:
                return "Tavern";
            case PleasureRoomKind::casino:
                return "Casino";
            case PleasureRoomKind::temple:
                return "Temple";
            case PleasureRoomKind::arena:
                return "Arena";
        }
        return "Spa";
    }

    //! \brief The name of the mood effect (the pleasure buff) a visit to the given room starts. The spa buff is called
    //! Relaxed, the buff of every other pleasure room Pleasure.
    //! \param kind The pleasure room.
    //! \return The name of the effect without spaces.
    inline std::string buffName(PleasureRoomKind kind)
    {
        return (kind == PleasureRoomKind::spa) ? "Relaxed" : "Pleasure";
    }

    //! \brief True when the name is the name of a pleasure buff.
    //! \param name The name of a running mood effect.
    //! \return True for Relaxed and Pleasure.
    inline bool isBuffName(const std::string& name)
    {
        return (name == "Relaxed") || (name == "Pleasure");
    }
}

#endif // CREATUREMOODPLEASURE_H
