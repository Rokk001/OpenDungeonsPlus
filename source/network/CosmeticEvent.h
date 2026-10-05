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

#ifndef COSMETICEVENT_H
#define COSMETICEVENT_H

#include "network/ODPacket.h"

#include <cstdint>
#include <string>

#include <Ogre.h>

/*! \brief Kinds of cosmetic events. A cosmetic event is a short note from the server to a client
 *  that something happened which can be shown (an icon, a pose, a particle effect). It never
 *  changes the game and the game never depends on it: the clients only show it.
 *  The numbers are part of the network format. Never reorder or reuse them, only append.
 *  The fields of CosmeticEvent used by each kind are described next to the kind.
 */
enum class CosmeticEventType : int32_t
{
    //! The mood level of a creature changed. mSubject creature, mValue new CreatureMoodLevel,
    //! mValue2 old CreatureMoodLevel. Sent for the creatures of the receiving keeper and of its allies.
    moodStage = 0,
    //! The creature starts to flee out of fear. mSubject creature, mValue 0: it is outmatched or weak,
    //! 1: a fear trap scared it.
    scared = 1,
    //! The creature wanted to work for some time and found no job (the same count that lowers its mood).
    //! mSubject creature, mValue number of turns without a job. Sent for the creatures of the receiving
    //! keeper and of its allies.
    impatient = 2,
    //! A treasury just became full. mObject name of the room, mPosition the tile of the last deposit,
    //! mValue gold stored, mValue2 gold capacity.
    treasuryFull = 3,
    //! The gold a worker carries on its body changed. mSubject worker, mValue gold now (0: none),
    //! mValue2 the most the worker can carry.
    carriedGold = 4,
    //! A melee blow hit a creature. mSubject attacker, mObject target, mValue 0: the blow did its
    //! damage, 1: only a small part of it got through (glancing), 2: no damage at all (blocked or
    //! absorbed), mValue2 share of the damage that got through in per mille (0 to 1000),
    //! mPosition position of the target. This only reports what the damage calculation gave; the
    //! game has no random miss.
    meleeResult = 5,
    //! A creature launched a missile. mSubject shooter, mObject name of the missile entity, mText mesh
    //! of the missile (empty: a magic missile without a mesh), mValue and mValue2 tile x and y of the
    //! target, mPosition where the missile starts.
    missileLaunch = 6,
    //! A worker dug a tile away. mSubject worker, mValue the TileType the tile had before,
    //! mPosition the tile.
    digFinished = 7,
    //! A creature of the keeper arrived through a portal. mSubject creature, mValue the CreatureMoodLevel
    //! the creature would have, mValue2 its mood points. Can arrive before the creature itself.
    portalArrival = 8,
    //! A chicken of a hatchery hopped away from a hungry creature that came to eat it. mSubject chicken,
    //! mObject the creature, mPosition where the chicken was. The hop itself is the normal chicken movement.
    chickenFlee = 9,
    //! A creature that had prayed in a temple is no longer angry: its mood level fell from angry or worse to
    //! upset or better while the relief of the prayer was still working. mSubject creature, mValue new
    //! CreatureMoodLevel, mValue2 old CreatureMoodLevel. Sent for the creatures of the receiving keeper and of
    //! its allies.
    calmed = 10,
    //! Whether a creature has a bed (a home tile in a dormitory). mSubject creature, mValue 1: it has one,
    //! 0: it has none. Sent when this changes and, for a creature without a bed, now and then again, so that a
    //! keeper who only sees the creature later learns it too. Only the creatures of the receiving keeper and of
    //! its allies.
    bedStatus = 11,
    //! The health of a dungeon heart is now at a new step. mValue seat id of the heart, mValue2 the step
    //! (0: destroyed, the number of steps: unhurt), mText the number of steps as a decimal text,
    //! mPosition the position of the heart. Sent for the heart of every seat that the receiving keeper
    //! sees (its own and its allies' always) when the step changes and again when a heart comes into
    //! view, so that the beat of a foreign heart can follow its health. Only coarse steps are sent, never
    //! the exact health. Older clients skip the kind.
    heartHealthStage = 12,
    //! How full the grain on the floor of a hatchery is. mObject name of the hatchery, mValue the level of a
    //! full tile (the most), mValue2 how many seconds the list stays valid (a keeper that is not told again
    //! after that treats the grain as full), mText the tiles that are not full as "x,y,level;x,y,level;..."
    //! (a tile that is not in the list is full; an empty text: all full), mPosition the first tile of the room.
    //! Sent to the keepers that see a tile of the hatchery when the grain changed and now and then again while a
    //! tile is not full. Only shows the grain decals; the game never depends on it.
    hatcheryGrain = 13,
    //! A room has just changed hands (a takeover by workers or any other change of its owner). Sent once per room
    //! when the owner changes, never per tile or per worker. mObject name of the room type (the readable
    //! name), mText name of the room that was lost, mValue seat id of the new owner, mValue2 number of tiles
    //! (squares) that changed hands, mPosition one tile of the room (the one nearest its middle). Sent to the
    //! keepers that see a tile of the room and to the old and the new owner. Only ends the dancing of the
    //! workers that took the room; the game never depends on it.
    roomTakeover = 14,
    //! (15 is kept free: another branch uses it for the result of a casino game. When both are merged,
    //! isKnownType has to accept 0 to 9, 10 to 14, 15 and 16, and the tests that list the kinds need both.)
    //! What a blow or a shot of a creature really did to a creature, told when the damage was calculated (melee)
    //! or when the missile arrived (shot). mSubject attacker, mObject target, mValue the CosmeticHitResult,
    //! mValue2 the damage that was done in per mille of the maximum health of the target (0 to 1000, the base of
    //! a strong hit), mText "melee" or "missile", mPosition position of the target. Sent for the target to the
    //! keepers that see it. This only reports what the game decided or calculated; the possible results are
    //! those of CosmeticHitResult. For a melee blow the kind meleeResult follows it with
    //! the old fields, for clients that do not know this kind. Older clients skip the kind, an older server
    //! sends none.
    hitResult = 16
};

//! \brief The result in mValue of the event hitResult
enum class CosmeticHitResult : int32_t
{
    //! The blow or shot did its damage
    hit = 0,
    //! Only a small part of the damage got through (armor or resistance took the rest)
    glanced = 1,
    //! No damage at all got through (armor or resistance took all of it)
    blocked = 2,
    //! A shot ended without hurting the creature it was aimed at (it hit a wall or flew on, the creature moved
    //! away). Melee blows never give this result.
    missed = 3,
    //! A melee blow was dodged: the defender got out of the way, no damage (decided by the server before the damage)
    dodged = 4,
    //! A melee blow was parried with a weapon: no damage (decided by the server before the damage). Clients that
    //! do not know the value 4 or 5 show nothing for it; the older kind meleeResult follows and tells them "no damage".
    parried = 5
};

//! \brief The data of one cosmetic event. Every kind uses the same layout on the wire, so a
//! receiver always skips a kind it does not know without losing its place in the packet.
struct CosmeticEvent
{
    CosmeticEvent() :
        mType(-1),
        mValue(0),
        mValue2(0),
        mPosition(Ogre::Vector3::ZERO)
    {}

    CosmeticEvent(CosmeticEventType type) :
        mType(static_cast<int32_t>(type)),
        mValue(0),
        mValue2(0),
        mPosition(Ogre::Vector3::ZERO)
    {}

    //! \brief True if this build knows what the kind means
    bool isKnownType() const;

    bool is(CosmeticEventType type) const
    { return mType == static_cast<int32_t>(type); }

    //! \brief Name of the kind for the log, "unknown" for a kind this build does not know
    std::string typeString() const;

    //! Raw number of the kind (see CosmeticEventType), kept as a number so that a kind of a newer
    //! build survives reading
    int32_t mType;
    std::string mSubject;
    std::string mObject;
    std::string mText;
    int32_t mValue;
    int32_t mValue2;
    Ogre::Vector3 mPosition;
};

//! \brief Writes the event: int32 kind, string subject, string object, string text, int32 value,
//! int32 value2, Vector3 position.
ODPacket& operator<<(ODPacket& os, const CosmeticEvent& event);
//! \brief Reads the event. The packet is in error state if it was too short.
ODPacket& operator>>(ODPacket& is, CosmeticEvent& event);

#endif // COSMETICEVENT_H
