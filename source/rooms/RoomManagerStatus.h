#ifndef ROOMMANAGERSTATUS_H
#define ROOMMANAGERSTATUS_H

#include "rooms/RoomType.h"
#include <array>
#include <cstdint>

//! \brief Owner-only room availability indicators, ordered by increasing urgency.
enum class RoomManagerDot : uint32_t { none = 0, green = 1, yellow = 2, red = 3 };

//! \brief One room type's owned room count and current aggregate status.
struct RoomManagerEntry
{
    //! \brief Creates an absent room type with its initial status.
    RoomManagerEntry(RoomType roomType, RoomManagerDot status = RoomManagerDot::green) :
        type(roomType), count(0), dot(status) {}
    RoomType type;
    uint32_t count;
    RoomManagerDot dot;
};

//! \brief Returns all managed types in their fixed navigation order.
inline std::array<RoomManagerEntry, 8> emptyRoomManagerEntries()
{
    return {{RoomManagerEntry(RoomType::ghostRoom), RoomManagerEntry(RoomType::merchant, RoomManagerDot::none),
        RoomManagerEntry(RoomType::tavern), RoomManagerEntry(RoomType::spa), RoomManagerEntry(RoomType::infirmary),
        RoomManagerEntry(RoomType::alchemyLab), RoomManagerEntry(RoomType::casino), RoomManagerEntry(RoomType::workshop)}};
}

//! \brief Resolves a lab without consuming stock or treating a paused reserved batch as idle.
inline RoomManagerDot labRoomManagerDot(bool full, bool brewing, bool nextPotion)
{
    if(full || (!brewing && !nextPotion)) return RoomManagerDot::red;
    if(brewing && !nextPotion) return RoomManagerDot::yellow;
    return RoomManagerDot::green;
}

//! \brief Resolves output congestion only for a workshop with work and physical work places.
inline RoomManagerDot workshopRoomManagerDot(bool working, uint32_t places, uint32_t finished)
{
    return working && places > 0 && finished >= places ? RoomManagerDot::red : RoomManagerDot::green;
}

//! \brief Chooses red before yellow before green, ignoring absent rows and the merchant.
inline RoomManagerDot roomManagerButtonDot(const std::array<RoomManagerEntry, 8>& entries)
{
    RoomManagerDot result = RoomManagerDot::green;
    for(const RoomManagerEntry& entry : entries)
        if(entry.count > 0 && static_cast<uint32_t>(entry.dot) > static_cast<uint32_t>(result)) result = entry.dot;
    return result;
}

#endif
