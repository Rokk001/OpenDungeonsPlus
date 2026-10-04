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
    //! A creature was close at some time while the target was in view and none has been for mAfter seconds (a bed after the sleeper left)
    vacated
};

enum class AmbienceKind
{
    //! A particle system (also used as glow, with a flicker)
    particle,
    //! A procedural movement of the object node
    motion,
    //! Now and then a clip of the object's own mesh (a chicken scratching)
    clip,
    //! A small static decoration mesh placed on a tile (a weapon rack, a banner), with an optional motion
    model
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
        mEvery(10.0),
        mChance(1.0),
        mSpacing(1),
        mMaxDistance(28.0),
        mPriority(5),
        mReduced(false),
        mNeedWall(false),
        mWallSide(false),
        mHeartRate(false)
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
    //! Mesh file of the decoration (kind model), looking along the Y axis; it is turned away from the wall
    std::string mMesh;
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
    //! Tile targets: moved to the edge of the tile that touches a wall (implies mNeedWall)
    bool mWallSide;
    //! The speed follows the beat of the player's dungeon heart (faster when it is hurt)
    bool mHeartRate;
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
    double mOccupiedRadius;
    double mReducedDistanceFactor;
};

#endif // ROOMAMBIENCECONFIG_H
