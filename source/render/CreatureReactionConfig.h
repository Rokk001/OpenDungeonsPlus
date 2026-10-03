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

#ifndef CREATUREREACTIONCONFIG_H
#define CREATUREREACTIONCONFIG_H

#include <cstdint>
#include <map>
#include <string>
#include <vector>

//! \brief Priority of what a creature is doing or of a reaction. The lower the value, the
//! more important it is: a reaction only starts when its priority is lower than the one of
//! what the creature currently does, and a more important reaction replaces a running one.
enum class ReactionPriority
{
    death = 0,
    combat,
    held,
    event,
    work,
    mood,
    ambient,
    //! Not a reaction priority: the creature is only idling or walking
    none
};

//! \brief A short procedural movement of the creature model (cosmetic only)
struct ReactionMotion
{
    enum class Type
    {
        none,
        //! Jumps up and down
        hop,
        //! Trembles sideways
        shake,
        //! Squashes (or, with a negative amount, stretches) the model, like bending the knees
        squash,
        //! Turns around its vertical axis
        spin,
        //! Turns towards the camera, stays for a moment and turns back
        turn,
        //! Looks left and right (amount is the angle in degrees)
        look,
        //! Turns towards a point (a wall, a room, a neighbour, the place of an event), stays and turns back
        lookat,
        //! Sinks down (amount is the share of the height), stays and gets up again
        sit,
        //! Nods off (count nods, amount is their depth) and jumps up in the end
        startle
    };

    ReactionMotion() :
        mType(Type::none),
        mCount(1),
        mAmount(0.2),
        mDuration(0.0)
    {}

    Type mType;
    //! Number of hops, shakes, squashes or turns around
    uint32_t mCount;
    //! Height of a hop or width of a shake in world units, share of the size for a squash
    double mAmount;
    //! Time to do the whole motion, in seconds
    double mDuration;
};

//! \brief A particle effect put on the creature
struct ReactionEffect
{
    ReactionEffect() :
        mTime(2.0)
    {}

    std::string mName;
    double mTime;
};

//! \brief One way to show a reaction. A variant is shown in the highest tier that is available
//! for the creature: a clip of its own (tier C), else a clip that every creature of the mesh
//! has (tier B), always together with the emote, the particle effect and the motion (tier A).
struct ReactionVariant
{
    ReactionVariant() :
        mWeight(1.0),
        mClipSpeed(1.0),
        mFallbackSpeed(1.0),
        mFallbackStart(0.0),
        mFallbackEnd(1.0),
        mEmoteTime(2.0),
        mCooldown(-1.0),
        mProbability(-1.0),
        mRequiresSleepNeed(false),
        mRequiresWall(false),
        mRequiresNeighbour(false),
        mLateEmoteDelay(0.0),
        mLateEmoteTime(2.0)
    {}

    std::string mName;
    double mWeight;

    //! Tier C: clip made for this reaction. Empty if none
    std::string mClip;
    double mClipSpeed;

    //! Tier B: clip every creature of the mesh has. Played from mFallbackStart to mFallbackEnd
    //! (fractions of the clip length). Empty if none
    std::string mFallbackClip;
    double mFallbackSpeed;
    double mFallbackStart;
    double mFallbackEnd;

    //! Tier A: icon shown above the head and particle effects on the creature. Empty if none
    std::string mEmote;
    double mEmoteTime;
    std::vector<ReactionEffect> mEffects;
    ReactionMotion mMotion;

    //! Overrides of the values of the event, negative if the ones of the event are used
    double mCooldown;
    double mProbability;

    //! Creature definition names, groups and jobs the variant is allowed for. An empty list
    //! allows everything
    std::vector<std::string> mCreatures;
    std::vector<std::string> mGroups;
    std::vector<std::string> mJobs;

    //! Only for creature types that need to sleep (see CreatureReactions::creatureNeedsSleep)
    bool mRequiresSleepNeed;

    //! Only when a wall tile is next to the creature (the wall is where the motion 'lookat' and the props turn to)
    bool mRequiresWall;
    //! Only when another creature is close (the motion 'lookat' turns to it)
    bool mRequiresNeighbour;
    //! Name of a room type (for example Hatchery): only when the creature's seat has such a room, the
    //! motion 'lookat' turns to the closest tile of it. Empty if not used.
    std::string mLookAtRoom;

    //! A second icon that starts later in the reaction (nodding off, then startled). Empty if none.
    std::string mLateEmote;
    double mLateEmoteDelay;
    double mLateEmoteTime;
};

//! \brief A kind of reaction (what happened to the creature) with its variants
struct ReactionEvent
{
    ReactionEvent() :
        mPriority(ReactionPriority::event),
        mCooldown(10.0),
        mProbability(1.0),
        mGroupMax(3),
        mWhileWorking(false)
    {}

    std::string mName;
    ReactionPriority mPriority;
    //! Time in seconds before the same creature can show a reaction of this kind again
    double mCooldown;
    //! Chance that a trigger leads to a reaction
    double mProbability;
    //! Maximum number of creatures that react when a whole group is triggered
    uint32_t mGroupMax;
    //! The event decorates a long running work or sleep animation of the creature (sleeping, digging,
    //! claiming): that animation does not count as busy for this event, and no clip is put over it
    bool mWhileWorking;
    std::vector<ReactionVariant> mVariants;
};

//! \brief Named list of creature definitions. Used by variants to choose what fits a creature
struct ReactionGroup
{
    std::string mName;
    std::vector<std::string> mCreatures;
};

//! \brief Content of config/creatureReactions.cfg
class CreatureReactionConfig
{
public:
    CreatureReactionConfig();

    //! \brief Reads the file. Returns false (and keeps what could be read) if it is missing or
    //! malformed: the reactions are then simply not available.
    bool load(const std::string& fileName);

    const ReactionEvent* getEvent(const std::string& name) const;

    //! \brief Names of the groups the creature definition is in. If it is in none, the default
    //! group is returned.
    std::vector<std::string> getGroupsOf(const std::string& creatureName) const;

    static ReactionPriority priorityFromString(const std::string& text, bool& ok);
    static std::string priorityToString(ReactionPriority priority);

    inline const std::map<std::string, ReactionEvent>& getEvents() const
    { return mEvents; }

    inline uint32_t getMaxSimultaneous() const
    { return mMaxSimultaneous; }

    inline double getMaxCameraDistance() const
    { return mMaxCameraDistance; }

    inline double getGroupStaggerMin() const
    { return mGroupStaggerMin; }

    inline double getGroupStaggerMax() const
    { return mGroupStaggerMax; }

    //! Seconds between two looks at the moods of a few creatures
    inline double getMoodInterval() const
    { return mMoodInterval; }

    //! Number of creatures looked at in each of these looks
    inline uint32_t getMoodPerTick() const
    { return mMoodPerTick; }

    //! Chance (0 to 1) that a mood is shown on a creature that walks instead of standing
    inline double getMoodWalkingChance() const
    { return mMoodWalkingChance; }

    //! Seconds a creature has to stand idle until it is impatient
    inline double getImpatientAfter() const
    { return mImpatientAfter; }

    //! Seconds a creature stays proud after a victory or a level up
    inline double getProudSeconds() const
    { return mProudSeconds; }

private:
    bool loadSettings(std::istream& file);
    bool loadGroups(std::istream& file);
    bool loadEvents(std::istream& file);
    bool loadEvent(std::istream& file, ReactionEvent& event);
    bool loadVariant(std::istream& file, ReactionVariant& variant);

    uint32_t mMaxSimultaneous;
    double mMaxCameraDistance;
    double mGroupStaggerMin;
    double mGroupStaggerMax;
    double mMoodInterval;
    uint32_t mMoodPerTick;
    double mMoodWalkingChance;
    double mImpatientAfter;
    double mProudSeconds;
    std::string mDefaultGroup;
    std::vector<ReactionGroup> mGroups;
    std::map<std::string, ReactionEvent> mEvents;
};

#endif // CREATUREREACTIONCONFIG_H
