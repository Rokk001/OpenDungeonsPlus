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

#ifndef ROOMAMBIENCEEXTRAS_H
#define ROOMAMBIENCEEXTRAS_H

#include <OgreVector3.h>

#include <cstdint>
#include <map>
#include <random>
#include <string>
#include <vector>

class Creature;
class GameMap;
class RoomAmbience;
class Seat;

/*! \brief Moments of the room ambience that are read from what the client already knows.
 *
 * Called by RoomAmbience after every scan. It only watches (health stage, seat, hunger, heart health of
 * the local player, objects on the map) and starts one-shot events of config/roomAmbienceDeferred.cfg:
 * TempleHealed (bell), ConvertedFlash, ChickenFlee, RoosterCrow and HeartHurt. It also gives the heart
 * rate to the effects marked "HeartRate". Nothing is sent, saved or changed in the game.
 */
class RoomAmbienceExtras
{
public:
    RoomAmbienceExtras();

    void scan(RoomAmbience& ambience, GameMap* gameMap, double clock, const Ogre::Vector3& cameraPosition);

    //! \brief Forgets what was seen (the next scan only learns, it starts no event)
    void reset();

private:
    struct CreatureSnapshot
    {
        CreatureSnapshot() :
            mHealth(0), mSeat(nullptr), mPrisoner(false), mLastEvent(-100.0), mGeneration(0)
        {}

        uint32_t mHealth;
        const Seat* mSeat;
        bool mPrisoner;
        double mLastEvent;
        uint32_t mGeneration;
    };

    void scanCreatures(RoomAmbience& ambience, GameMap* gameMap, double clock);
    void scanObjects(RoomAmbience& ambience, GameMap* gameMap, double clock, const Ogre::Vector3& cameraPosition);
    bool isTempleTile(GameMap* gameMap, const Ogre::Vector3& position) const;

    std::map<std::string, CreatureSnapshot> mCreatures;
    //! Positions of the creatures that are hungry at the last scan
    std::vector<Ogre::Vector3> mHungryPositions;
    //! Time at which a chicken was last startled, per chicken
    std::map<std::string, double> mChickenFlee;
    double mNextCrow;
    //! Time of the next beat flare of a hurt heart, per seat id
    std::map<int32_t, double> mNextHeartBeat;
    uint32_t mGeneration;
    bool mInitialized;
    std::mt19937 mRandom;
};

#endif // ROOMAMBIENCEEXTRAS_H
