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
    lowHealth,
    //! A creature was close at some time while the target was in view and none has been for mAfter seconds (a bed after the sleeper left)
    vacated,
    //! A creature that sleeps is close to the target (a bed with a sleeper in it)
    sleeping
};

//! \brief What an ambience effect does when it is shown
enum class AmbienceKind
{
    //! A particle system (also used as glow, with a flicker)
    particle,
    //! A procedural movement of the object node
    motion,
    //! Now and then a clip of the object's own mesh (a chicken scratching)
    clip,
    //! A small static decoration mesh placed on a tile (a weapon rack, a banner), with an optional motion
    model,
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
    turn,
    //! A mesh (Mesh) that is stretched from the point From to the target for a moment and flickers: a lightning bolt
    //! (events only). Amount = width, Speed = flickers per second, Duration in seconds
    beam,
    //! An object (Mesh and/or particle system System as trail) that flies from From to the target in Duration seconds
    //! on an arc of height Amount (events only); Land = event raised at the target when it arrives
    projectile,
    //! Events only: plays a clip of Clips once on the creature the event is about (the stretch of a creature that woke);
    //! nothing happens when the creature has no such clip
    creatureClip
};

//! \brief How an effect of the kind motion moves the node of its object
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
    //! \brief Creates an effect with the defaults that the configuration file may override
    AmbienceEffect() :
        mTarget(AmbienceTarget::object),
        mWhen(AmbienceWhen::always),
        mKind(AmbienceKind::particle),
        mLoop(false),
        mMotion(AmbienceMotion::sway),
        mAfter(30.0),
        mOffset(Ogre::Vector3::ZERO),
        mAxis(Ogre::Vector3::UNIT_X),
        mAmount(1.0),
        mSpeed(1.0),
        mFlicker(0.0),
        mDuration(3.0),
        mFrom(Ogre::Vector3(0.0f, 0.0f, 8.0f)),
        mDelay(0.0),
        mBelow(0.35),
        mEvery(10.0),
        mChance(1.0),
        mSpacing(1),
        mGrainMin(0),
        mMaxDistance(28.0),
        mPriority(5),
        mReduced(false),
        mNeedWall(false),
        mWallSide(false),
        mHeartRate(false),
        mOwnerOnly(false)
    {}

    //! Name of the effect, used in the log
    std::string mName;
    //! What the effect is attached to (an object, a tile or an event)
    AmbienceTarget mTarget;
    //! Mesh names (object, with * as first or last character as wildcard) or tile visual names (tile, event)
    std::vector<std::string> mMatch;
    //! When a looping effect is shown
    AmbienceWhen mWhen;
    //! Event name (target event)
    std::string mEvent;
    //! What the effect does (a particle system, a motion or a clip)
    AmbienceKind mKind;
    //! Particle system template (kind particle)
    std::string mSystem;
    //! Mesh name without extension (kinds roll, beam and projectile), mesh file of the decoration looking along the
    //! Y axis (kind model, it is turned away from the wall) and particle system where a rolling object breaks up
    //! (kind roll)
    std::string mMesh;
    std::string mEndSystem;
    //! Clips to choose from (kind clip)
    std::vector<std::string> mClips;
    //! Event clips: mesh names (* as first or last character as wildcard) of the objects that play the clip, the nearest
    //! one within Amount tiles of the event is used
    std::vector<std::string> mObjects;
    //! Object clips: the clip runs in a loop as long as the condition holds (and stops at its last pose when it ends)
    bool mLoop;
    //! How the object is moved (kind motion)
    AmbienceMotion mMotion;
    //! Seconds without a creature before an empty room effect starts
    double mAfter;
    //! Added to the position of the target
    Ogre::Vector3 mOffset;
    //! Axis a motion works around or along
    Ogre::Vector3 mAxis;
    //! Degrees (sway, wobble), units (bob), fraction (pulse, flicker)
    double mAmount;
    //! Cycles per second (degrees per second for spin)
    double mSpeed;
    //! Size change of the particle billboards, 0 = steady
    double mFlicker;
    //! Seconds a one-shot effect is kept
    double mDuration;
    //! Event raised at the target when a projectile arrives
    std::string mLand;
    //! Where a beam or projectile starts, relative to the target
    Ogre::Vector3 mFrom;
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
    //! Tile targets: only shown while the grain level of the tile (hatchery floor) is at least this (0 = always)
    uint32_t mGrainMin;
    //! Distance to the camera up to which the effect runs
    double mMaxDistance;
    //! Higher priority effects are served first when the budget is used up
    int32_t mPriority;
    //! Kept in the mode "reduced"
    bool mReduced;
    //! Tile targets: only tiles beside a wall
    bool mNeedWall;
    //! Tile targets: moved to the edge of the tile that touches a wall (implies mNeedWall)
    bool mWallSide;
    //! The speed follows the beat of the player's dungeon heart (faster when it is hurt)
    bool mHeartRate;
    //! Object targets: shown only to the keeper the object belongs to (the glint of a secret door must not give it away)
    bool mOwnerOnly;
    //! Sound family played when an event effect starts (only in the mode "full")
    std::string mSound;
};

/*! \brief Settings and effects of config/roomAmbience.cfg
 *
 * The file has the root tag [RoomAmbience] with a [Settings] block, an [Effects] block with
 * [Effect] entries and optional "Include <file>" lines (same folder, a missing file is skipped).
 */
class RoomAmbienceConfig
{
public:
    //! \brief Creates an empty configuration with the default limits
    RoomAmbienceConfig();

    //! \brief Reads the file, replacing what was loaded before. Returns false if it could not be used
    bool load(const std::string& fileName);

    //! \brief The effects read from the file and its includes, in file order
    const std::vector<AmbienceEffect>& getEffects() const
    { return mEffects; }

    //! \brief Seconds between two scans of the visible rooms and objects
    double getScanInterval() const
    { return mScanInterval; }
    //! \brief The most looping particle systems that may run at once (the lower limit in the mode reduced)
    uint32_t getMaxParticles(bool reduced) const
    { return reduced ? mMaxParticlesReduced : mMaxParticles; }
    //! \brief The most objects that may be moved by motions at once
    uint32_t getMaxMotions() const
    { return mMaxMotions; }
    //! \brief The most one-shot particle systems that may run at once
    uint32_t getMaxOneShots() const
    { return mMaxOneShots; }
    uint32_t getMaxFlights() const
    { return mMaxFlights; }
    uint32_t getMaxMarks() const
    { return mMaxMarks; }
    //! \brief Distance in tiles within which a creature counts as close to an object or tile
    double getOccupiedRadius() const
    { return mOccupiedRadius; }
    //! \brief Factor that shortens the view distance of every effect in the mode reduced
    double getReducedDistanceFactor() const
    { return mReducedDistanceFactor; }

    //! \brief Reads the name of a "When" condition; returns false for an unknown name
    static bool whenFromString(const std::string& text, AmbienceWhen& when);
    //! \brief Reads the name of a motion; returns false for an unknown name
    static bool motionFromString(const std::string& text, AmbienceMotion& motion);

private:
    //! \brief Reads one file; included is true for a file named by an "Include" line (a missing one is skipped)
    bool loadFile(const std::string& fileName, bool included);
    //! \brief Reads the [Settings] block
    bool loadSettings(std::istream& file);
    //! \brief Reads the [Effects] block, one [Effect] entry after the other
    bool loadEffects(std::istream& file);
    //! \brief Reads one [Effect] entry and adds it to mEffects
    bool loadEffect(std::istream& file);

    //! The effects read from the file and its includes, in file order
    std::vector<AmbienceEffect> mEffects;
    //! Seconds between two scans
    double mScanInterval;
    //! Most looping particle systems that may run at once
    uint32_t mMaxParticles;
    //! The same limit in the mode reduced
    uint32_t mMaxParticlesReduced;
    //! Most objects that may be moved at once
    uint32_t mMaxMotions;
    //! Most one-shot particle systems that may run at once
    uint32_t mMaxOneShots;
    uint32_t mMaxMarks;
    uint32_t mMaxFlights;
    //! Distance in tiles within which a creature counts as close
    double mOccupiedRadius;
    //! Factor that shortens the view distance in the mode reduced
    double mReducedDistanceFactor;
};

#endif // ROOMAMBIENCECONFIG_H
