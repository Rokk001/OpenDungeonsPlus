#ifndef ROOM_MANAGER_NAVIGATION_H
#define ROOM_MANAGER_NAVIGATION_H

#include "rooms/RoomType.h"
#include <array>
#include <cstddef>
#include <cstdint>

//! \brief Keeps the Room Manager selection and ownership independent of GUI visibility.
class RoomManagerNavigation
{
public:
    //! \brief Starts closed with no owned room types.
    RoomManagerNavigation() : mCounts{{0, 0, 0, 0, 0, 0, 0, 0}},
        mSelected(RoomType::nullRoomType), mOpen(false)
    {
    }

    //! \brief Returns the fixed room-type order used by the list and ownership snapshots.
    static const std::array<RoomType, 8>& order()
    {
        static const std::array<RoomType, 8> types = {{RoomType::ghostRoom, RoomType::merchant,
            RoomType::tavern, RoomType::spa, RoomType::infirmary, RoomType::alchemyLab,
            RoomType::casino, RoomType::workshop}};
        return types;
    }

    //! \brief Updates ownership, repairing a lost selection or closing an empty manager.
    void updateOwned(const std::array<uint32_t, 8>& counts)
    {
        mCounts = counts;
        if(listedCount() == 0)
            close();
        else if(mOpen && !owned(mSelected))
            openFirst();
    }

    //! \brief Opens on the first owned type, or stays closed when no type is owned.
    void openFirst()
    {
        close();
        for(std::size_t index = 0; index < order().size(); ++index)
        {
            if(mCounts[index] == 0)
                continue;
            mSelected = order()[index];
            mOpen = true;
            return;
        }
    }

    //! \brief Toggles an owned shortcut target while leaving an unowned target unchanged.
    void toggleType(RoomType type)
    {
        if(!owned(type))
            return;
        if(mOpen && mSelected == type)
            close();
        else
            selectType(type);
    }

    //! \brief Selects an owned row and opens its page without toggling it closed.
    void selectType(RoomType type)
    {
        if(!owned(type))
            return;
        mSelected = type;
        mOpen = true;
    }

    //! \brief Closes the manager and discards its selection for the next opening.
    void close()
    {
        mOpen = false;
        mSelected = RoomType::nullRoomType;
    }

    //! \brief Reports whether the manager has an open owned page.
    bool isOpen() const { return mOpen; }

    //! \brief Returns the selected type, or nullRoomType while closed.
    RoomType selected() const { return mSelected; }

    //! \brief Checks whether a managed room type has at least one owned room.
    bool owned(RoomType type) const
    {
        for(std::size_t index = 0; index < order().size(); ++index)
            if(order()[index] == type)
                return mCounts[index] > 0;
        return false;
    }

    //! \brief Counts listed types rather than the number of room instances.
    std::size_t listedCount() const
    {
        std::size_t count = 0;
        for(uint32_t rooms : mCounts)
            if(rooms > 0)
                ++count;
        return count;
    }

private:
    std::array<uint32_t, 8> mCounts;
    RoomType mSelected;
    bool mOpen;
};

#endif
