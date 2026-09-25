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

#ifndef DEFEATSEQUENCE_H
#define DEFEATSEQUENCE_H

#include <cstdint>

//! \brief Timings (seconds after the heart was destroyed) and look of the defeat sequence.
namespace DefeatSequenceSettings
{
    //! The heart explosion effect and its subtitle last until this time
    const float EXPLOSION_END = 15.0f;
    //! The red tint fades out between EXPLOSION_END and this time
    const float TINT_END = 15.5f;
    const float TINT_ALPHA = 0.35f;
    const float SWIRL_START = 15.5f;
    const float SWIRL_END = 18.5f;
    //! Distance in tiles the swirl travels away from the heart
    const float SWIRL_DISTANCE = 14.0f;
    const float FADE_START = 19.5f;
    const float FADE_END = 28.5f;
    const float SECOND_SUBTITLE_START = 20.5f;
    //! End of the part implemented here; the debriefing window takes over afterwards
    const float FINISH = 29.5f;
    //! Longest time step taken into account, so that a slow frame cannot skip a phase
    const float MAX_STEP = 0.25f;

    //! Low oblique camera used for the cut: height above the floor and pitch in degrees
    //! (0 looks straight down, like the game camera's default of 25)
    const float CAMERA_HEIGHT = 2.0f;
    const float CAMERA_PITCH = 68.0f;
}

//! \brief State and timeline of the defeat sequence.
//! Everything that depends on the elapsed time is a static function so that it can be checked
//! without a running game.
class DefeatSequence
{
public:
    enum class Phase
    {
        Inactive,
        Explosion,
        Swirl,
        Fade,
        Finished
    };

    DefeatSequence() :
        mStarted(false),
        mFinished(false),
        mElapsed(0.0f),
        mConquerorSeatId(-1),
        mHeartTileX(-1),
        mHeartTileY(-1)
    {
    }

    //! \brief Starts the sequence. Returns false (and changes nothing) if it was already started.
    bool start(int32_t conquerorSeatId, int32_t heartTileX, int32_t heartTileY)
    {
        if(mStarted)
            return false;
        mStarted = true;
        mConquerorSeatId = conquerorSeatId;
        mHeartTileX = heartTileX;
        mHeartTileY = heartTileY;
        return true;
    }

    //! \brief Advances the timeline. Returns true exactly once, on the step that reaches the end.
    bool advance(float elapsed)
    {
        if(!mStarted || mFinished)
            return false;
        if(elapsed > DefeatSequenceSettings::MAX_STEP)
            elapsed = DefeatSequenceSettings::MAX_STEP;
        if(elapsed > 0.0f)
            mElapsed += elapsed;
        if(mElapsed < DefeatSequenceSettings::FINISH)
            return false;
        mFinished = true;
        return true;
    }

    //! \brief True from the start on, also after the end: the screen stays black and input stays blocked.
    bool isStarted() const
    { return mStarted; }
    bool blocksInput() const
    { return mStarted; }
    bool isFinished() const
    { return mFinished; }
    float getElapsed() const
    { return mElapsed; }
    int32_t getConquerorSeatId() const
    { return mConquerorSeatId; }
    int32_t getHeartTileX() const
    { return mHeartTileX; }
    int32_t getHeartTileY() const
    { return mHeartTileY; }
    //! \brief The heart position is unknown when the server sent -1
    bool isHeartKnown() const
    { return mHeartTileX >= 0 && mHeartTileY >= 0; }
    //! \brief The swirl needs the seat colour of the conqueror; without a conqueror it is skipped
    bool isSwirlWanted() const
    { return mConquerorSeatId >= 0; }

    static Phase phaseAt(float t)
    {
        if(t < 0.0f)
            return Phase::Inactive;
        if(t < DefeatSequenceSettings::SWIRL_START)
            return Phase::Explosion;
        if(t < DefeatSequenceSettings::SWIRL_END)
            return Phase::Swirl;
        if(t < DefeatSequenceSettings::FINISH)
            return Phase::Fade;
        return Phase::Finished;
    }

    static bool isExplosionEffectActiveAt(float t)
    { return t >= 0.0f && t < DefeatSequenceSettings::EXPLOSION_END; }

    static bool isSwirlActiveAt(float t)
    { return t >= DefeatSequenceSettings::SWIRL_START && t < DefeatSequenceSettings::SWIRL_END; }

    //! \brief 0 when the swirl starts at the heart, 1 when it has arrived
    static float swirlProgressAt(float t)
    {
        if(t <= DefeatSequenceSettings::SWIRL_START)
            return 0.0f;
        if(t >= DefeatSequenceSettings::SWIRL_END)
            return 1.0f;
        return (t - DefeatSequenceSettings::SWIRL_START)
            / (DefeatSequenceSettings::SWIRL_END - DefeatSequenceSettings::SWIRL_START);
    }

    //! \brief Opacity of the red tint over the scene
    static float redTintAlphaAt(float t)
    {
        if(t < 0.0f || t >= DefeatSequenceSettings::TINT_END)
            return 0.0f;
        if(t < DefeatSequenceSettings::EXPLOSION_END)
            return DefeatSequenceSettings::TINT_ALPHA;
        return DefeatSequenceSettings::TINT_ALPHA
            * (1.0f - (t - DefeatSequenceSettings::EXPLOSION_END)
                / (DefeatSequenceSettings::TINT_END - DefeatSequenceSettings::EXPLOSION_END));
    }

    //! \brief Opacity of the black cover: 0 until FADE_START, rising linearly to 1 at FADE_END
    static float blackAlphaAt(float t)
    {
        if(t <= DefeatSequenceSettings::FADE_START)
            return 0.0f;
        if(t >= DefeatSequenceSettings::FADE_END)
            return 1.0f;
        return (t - DefeatSequenceSettings::FADE_START)
            / (DefeatSequenceSettings::FADE_END - DefeatSequenceSettings::FADE_START);
    }

    static bool isFirstSubtitleVisibleAt(float t)
    { return t >= 0.0f && t < DefeatSequenceSettings::EXPLOSION_END; }

    static bool isSecondSubtitleVisibleAt(float t)
    { return t >= DefeatSequenceSettings::SECOND_SUBTITLE_START; }

private:
    bool mStarted;
    bool mFinished;
    float mElapsed;
    int32_t mConquerorSeatId;
    int32_t mHeartTileX;
    int32_t mHeartTileY;
};

#endif // DEFEATSEQUENCE_H
