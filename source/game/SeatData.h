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

#ifndef SEATDATA_H
#define SEATDATA_H


#include <Ogre.h>
#include <OgreColourValue.h>
#include <string>
#include <vector>
#include <cstdint>

class ODPacket;

enum class SkillType;
enum class RoomType;

//! \brief Base class for Seat that only embeds the data for the seat used through the network. It allows to use unit tests without having
//! to bring Seat dependencies (basically, the whole game)
class SeatData
{
public:
    // Constructors
    //! \brief Creates seat data with the configured default discharge threshold.
    SeatData();

    inline void setId(int id)
    { mId = id; }

    inline int getId() const
    { return mId; }

    inline int getTeamId() const
    { return mTeamId; }

    inline unsigned int getNumClaimedTiles() const
    { return mNumClaimedTiles; }

    inline void setNumClaimedTiles(const unsigned int& num)
    { mNumClaimedTiles = num; }

    inline void incrementNumClaimedTiles()
    { ++mNumClaimedTiles; }

    void setTeamId(int teamId);

    inline const std::vector<int>& getAvailableTeamIds() const
    { return mAvailableTeamIds; }

    inline const std::string& getFaction() const
    { return mFaction; }

    inline void setFaction(const std::string& faction)
    { mFaction = faction; }

    inline void setColorId(const std::string& colorId)
    { mColorId = colorId; }

    inline const std::string& getColorId() const
    { return mColorId; }

    //! \brief Returns stored gold, including fractional admission payments.
    inline double getGold() const
    { return mGold; }

    inline int getGoldMax() const
    { return mGoldMax; }

    inline double getMana() const
    { return mMana; }

    //! \brief Returns the admission payer; AI keepers always pay themselves.
    int32_t getInfirmaryPayer() const { return mPlayerType == "AI" ? 0 : mInfirmaryPayer; }
    //! \brief Selects keeper (0) or creature (1) admission payment.
    void setInfirmaryPayer(int32_t payer) { if(payer == 0 || payer == 1) mInfirmaryPayer = payer; }
    //! \brief Returns the discharge health percentage.
    int32_t getInfirmaryThreshold() const { return mInfirmaryThreshold; }
    //! \brief Accepts discharge percentages from 40 to 100 in steps of ten.
    void setInfirmaryThreshold(int32_t threshold);
    //! \brief Reports whether treatments may spend mana.
    bool getInfirmaryHealOn() const { return mInfirmaryHealOn; }
    //! \brief Enables or pauses healing for this keeper.
    void setInfirmaryHealOn(bool healOn) { mInfirmaryHealOn = healOn; }

    inline double getManaDelta() const
    { return mManaDelta; }

    inline double getManaIncomePerSecond() const
    { return mManaIncomePerSecond; }

    inline double getManaUpkeepPerSecond() const
    { return mManaUpkeepPerSecond; }

    //! \brief The one-off mana taken (spells, trap shots, possession, ...) averaged over the last second, shown on the HUD.
    inline double getManaOneOffPerSecond() const
    { return mManaOneOffPerSecond; }

    inline int getNumCreaturesFighters() const
    { return mNumCreaturesFighters; }

    inline int getNumCreaturesFightersMax() const
    { return mNumCreaturesFightersMax; }

    inline int getNumCreaturesWorkers() const
    { return mNumCreaturesWorkers; }

    uint32_t getNbRooms(RoomType roomType) const;

    //! \brief True when the seat once had a library and has none left, for example
    //! because an enemy took it over. The spells researched there cannot be used
    //! until a library is owned again.
    bool isLibraryLost() const;

    //! \brief Number of stored special boxes of the given gift box type (as an integer), the
    //! boxes a worker carried to the dungeon heart. Each one is used with a button.
    uint32_t getNbStoredSpecials(uint32_t giftBoxType) const;

    inline const std::string& getPlayerType() const
    { return mPlayerType; }

    inline void setPlayerType(const std::string& playerType)
    { mPlayerType = playerType; }

    inline const std::vector<SkillType>& getSkillNotAllowed() const
    { return mSkillNotAllowed; }

    //! \brief functions to transfer Seat data through network. Note that they should not be overriden as
    //! unit tests use them to get the data from the Seat (without having to take Seat and all its dependencies)
    bool importFromPacket(ODPacket& is);
    void exportToPacket(ODPacket& os) const;
    //! \brief Reads changing seat state and the three infirmary settings.
    bool importFromPacketForUpdate(ODPacket& is);
    //! \brief Sends changing seat state followed by the three infirmary settings.
    void exportToPacketForUpdate(ODPacket& os) const;

    static std::string displayAsString(const SeatData* seat);

protected:
    //! \brief The seat id. Allows to identify this seat. Must be unique per level file.
    int mId;

    //! \brief The team id of the player sitting in this seat.
    int mTeamId;

    //! \brief The type of player (can be Human or AI).
    std::string mPlayerType;

    //! \brief The name of the faction that this seat is playing as (can be Keeper or Hero).
    std::string mFaction;

    //! \brief The amount of 'keeper mana' the player has.
    double mMana;

    //! \brief The amount of 'keeper mana' the player gains/loses per turn, updated in GameMap::doTurn().
    double mManaDelta;

    //! \brief The mana income per second (heart plus tiles), updated in GameMap::doTurn().
    double mManaIncomePerSecond;

    //! \brief The mana upkeep per second of all the workers, updated in GameMap::doTurn().
    double mManaUpkeepPerSecond;

    //! \brief The one-off mana taken (spells, trap shots, possession, ...) averaged over the
    //! last second, updated in GameMap::doTurn().
    double mManaOneOffPerSecond;

    //! \brief The starting camera location (in tile coordinates) of this seat.
    int mStartingX;
    int mStartingY;

    //! \brief The number of living creatures fighters under this seat's control
    int mNumCreaturesFighters;
    int mNumCreaturesFightersMax;
    int mNumCreaturesWorkers;

    //! \brief The actual color that this color index translates into.
    std::string mColorId;

    //! \brief Team ids this seat can use defined in the level file.
    std::vector<int> mAvailableTeamIds;

    //! \brief How many tiles have been claimed by this seat, updated in GameMap::doTurn().
    unsigned int mNumClaimedTiles;

    bool mHasGoalsChanged;

    //! \brief The total amount of gold coins in the keeper's treasury and in the dungeon heart.
    double mGold;

    //! \brief Admission payer, discharge health and healing switch shared by all infirmaries.
    int32_t mInfirmaryPayer;
    int32_t mInfirmaryThreshold;
    bool mInfirmaryHealOn;

    //! \brief The total amount of gold coins that the keeper treasuries can have.
    int mGoldMax;

    //! \brief The number of rooms the player owns (room index being room type).
    //! Useful to display the first free tile on client side for example
    std::vector<uint32_t> mNbRooms;

    //! \brief True once the seat has owned a library. Set on server side, sent to the clients
    //! with the other changing data.
    bool mHadLibrary;

    //! \brief Stored special boxes, indexed by gift box type. Set on server side, sent to the
    //! clients with the other changing data.
    std::vector<uint32_t> mStoredSpecials;

    //! \brief Skills not allowed. Used on server side only
    std::vector<SkillType> mSkillNotAllowed;

    //! \brief Progress for current skill. Allows to display the progressbar on the client side
    SkillType mCurrentSkillType;
    float mCurrentSkillProgress;
};

#endif // SEATDATA_H
