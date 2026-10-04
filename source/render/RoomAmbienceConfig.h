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

#ifndef ROOMAMBIENCECONFIG_H
#define ROOMAMBIENCECONFIG_H

#include <OgreVector3.h>

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <vector>

//! \brief What an ambience effect is attached to
enum class AmbienceTarget
{
    //! A rendered object (bookshelf, anvil, ...), found by its mesh name
    object,
    //! A room tile, found by its tile visual name (libraryRoom, ...)
    tile,
    //! A one-shot effect at the place where something happened (room built, research done, ...)
    event
};

//! \brief When a looping effect is shown
enum class AmbienceWhen
{
    always,
    //! A creature is close to the target
    occupied,
    //! No creature was close to the target for the time given in mAfter
    empty,
    //! The target (a door) took a hit a moment ago
    hit,
    //! The target (a door) is closed, which is what a lock by the keeper does
    locked,
    //! The target (a trap) reloads or is empty, as the server reported it
    reloading,
    //! The target (a trap) is loaded and ready, the opposite of reloading
    ready,
    //! The target (the dungeon heart of the local keeper) has less health than the fraction given in mBelow
    lowHealth
};

enum class AmbienceKind
{
    //! A particle system (also used as glow, with a flicker)
    particle,
    //! A procedural movement of the object node
    motion,
    //! Now and then a clip of the object's own mesh (a chicken scratching)
    clip,
    //! A short shake of the view (events only): Amount = strength in world units, Speed = shakes per second,
    //! Duration in seconds, MaxDistance = distance of the event from the middle of the view beyond which it is not felt
    shake,
    //! A particle system that stays on the floor for Duration seconds (events only); the oldest mark is removed
    //! when there are more than MaxMarks
    mark,
    //! A sound of the family given by Family: played at the event, or now and then (Every) at an object
    sound,
    //! A mesh (Mesh) that rolls Amount tiles in Duration seconds from the place of an event, spinning at Speed degrees
    //! per second, with the particle system System as a trail and EndSystem where it breaks up (events only)
    roll,
    //! Slowly turns an object (a cannon) toward creatures within Amount tiles and back to where it stood when none
    //! is near, at Speed degrees per second (objects only)
    turn
};

enum class AmbienceMotion
{
    //! Slow rocking around an axis
    sway,
    //! Rocking that swells and fades (hits on a dummy, a creaking beam)
    wobble,
    //! Turning around the vertical axis
    spin,
    //! Moving up and down
    bob,
    //! Growing and shrinking
    pulse,
    //! Uneven brightness-like scaling
    flicker
};

//! \brief One effect read from the room ambience configuration
struct AmbienceEffect
{
    AmbienceEffect() :
        mTarget(AmbienceTarget::object),
        mWhen(AmbienceWhen::always),
        mKind(AmbienceKind::particle),
        mMotion(AmbienceMotion::sway),
        mAfter(30.0),
        mOffset(Ogre::Vector3::ZERO),
        mAxis(Ogre::Vector3::UNIT_X),
        mAmount(1.0),
        mSpeed(1.0),
        mFlicker(0.0),
        mDuration(3.0),
        mDelay(0.0),
        mBelow(0.35),
        mEvery(10.0),
        mChance(1.0),
        mSpacing(1),
        mMaxDistance(28.0),
        mPriority(5),
        mReduced(false),
        mNeedWall(false)
    {}

    std::string mName;
    AmbienceTarget mTarget;
    //! Mesh names (object, with * as first or last character as wildcard) or tile visual names (tile, event)
    std::vector<std::string> mMatch;
    AmbienceWhen mWhen;
    //! Event name (target event)
    std::string mEvent;
    AmbienceKind mKind;
    //! Particle system template (kind particle)
    std::string mSystem;
    //! Mesh of a rolling object and particle system where it breaks up (kind roll)
    std::string mMesh;
    std::string mEndSystem;
    //! Clips to choose from (kind clip)
    std::vector<std::string> mClips;
    AmbienceMotion mMotion;
    //! Seconds without a creature before an empty room effect starts
    double mAfter;
    Ogre::Vector3 mOffset;
    Ogre::Vector3 mAxis;
    //! Degrees (sway, wobble), units (bob), fraction (pulse, flicker)
    double mAmount;
    //! Cycles per second (degrees per second for spin)
    double mSpeed;
    //! Size change of the particle billboards, 0 = steady
    double mFlicker;
    //! Seconds a one-shot effect is kept
    double mDuration;
    //! Sound family, as in the folders below sounds/Spatial (kind sound)
    std::string mFamily;
    //! Seconds after the event until the sound is played (kind sound, events only)
    double mDelay;
    //! Health fraction (0 to 1) under which a lowHealth effect runs
    double mBelow;
    //! Average seconds between two clips (kind clip)
    double mEvery;
    //! Chance that an event effect is shown
    double mChance;
    //! Tile targets: only every n-th tile gets the effect
    uint32_t mSpacing;
    double mMaxDistance;
    //! Higher priority effects are served first when the budget is used up
    int32_t mPriority;
    //! Kept in the mode "reduced"
    bool mReduced;
    //! Tile targets: only tiles beside a wall
    bool mNeedWall;
};

/*! \brief Settings and effects of config/roomAmbience.cfg
 *
 * The file has the root tag [RoomAmbience] with a [Settings] block, an [Effects] block with
 * [Effect] entries and optional "Include <file>" lines (same folder, a missing file is skipped).
 */
class RoomAmbienceConfig
{
public:
    RoomAmbienceConfig();

    //! \brief Reads the file, replacing what was loaded before. Returns false if it could not be used
    bool load(const std::string& fileName);

    const std::vector<AmbienceEffect>& getEffects() const
    { return mEffects; }

    double getScanInterval() const
    { return mScanInterval; }
    uint32_t getMaxParticles(bool reduced) const
    { return reduced ? mMaxParticlesReduced : mMaxParticles; }
    uint32_t getMaxMotions() const
    { return mMaxMotions; }
    uint32_t getMaxOneShots() const
    { return mMaxOneShots; }
    uint32_t getMaxMarks() const
    { return mMaxMarks; }
    double getOccupiedRadius() const
    { return mOccupiedRadius; }
    double getReducedDistanceFactor() const
    { return mReducedDistanceFactor; }

    static bool whenFromString(const std::string& text, AmbienceWhen& when);
    static bool motionFromString(const std::string& text, AmbienceMotion& motion);

private:
    bool loadFile(const std::string& fileName, bool included);
    bool loadSettings(std::istream& file);
    bool loadEffects(std::istream& file);
    bool loadEffect(std::istream& file);

    std::vector<AmbienceEffect> mEffects;
    double mScanInterval;
    uint32_t mMaxParticles;
    uint32_t mMaxParticlesReduced;
    uint32_t mMaxMotions;
    uint32_t mMaxOneShots;
    uint32_t mMaxMarks;
    double mOccupiedRadius;
    double mReducedDistanceFactor;
};

#endif // ROOMAMBIENCECONFIG_H
