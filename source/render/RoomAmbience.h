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

#ifndef ROOMAMBIENCE_H
#define ROOMAMBIENCE_H

#include "render/RoomAmbienceConfig.h"

#include <OgrePrerequisites.h>
#include <OgreQuaternion.h>
#include <OgreSingleton.h>
#include <OgreVector3.h>

#include <cstdint>
#include <map>
#include <random>
#include <set>
#include <string>
#include <vector>

class GameMap;
class Tile;

/*! \brief Cosmetic life in the rooms (dust, glow, sparks, moving objects), client side only.
 *
 * Nothing here is known to the server or saved: the effects are derived from what the client map
 * already shows (room tiles, the objects in the rooms, creatures standing close, things that appear
 * or vanish). Which effect belongs to which room or object is read from config/roomAmbience.cfg.
 * Only what is in view and close to the camera is animated, and the number of particle systems and
 * moving objects is limited. The option "Room ambience" (full / reduced / off) switches the amount.
 */
class RoomAmbience : public Ogre::Singleton<RoomAmbience>
{
public:
    enum class Mode
    {
        //! Everything is shown
        full,
        //! Few effects, no more than a handful of particle systems, shorter distance
        reduced,
        //! Nothing is shown
        off
    };

    RoomAmbience(GameMap* gameMap, const std::string& configPath);
    ~RoomAmbience();

    //! \brief Called every frame while the game is running
    void update(Ogre::Real timeSinceLastFrame);

    //! \brief Removes every running effect and puts the moved objects back
    void stopAll();

    void setMode(Mode mode);
    inline Mode getMode() const
    { return mMode; }
    static Mode modeFromString(const std::string& text);
    static std::string modeToString(Mode mode);

    bool reloadConfig();
    inline const RoomAmbienceConfig& getConfig() const
    { return mConfig; }

    //! \brief Shows the one-shot effects of the given event at the given place.
    //! forced ignores the chance, the view test and the mode "reduced". visualName is the tile visual
    //! (room) the event is about; empty = the one of the tile at the position. Returns the number of effects started
    uint32_t triggerEvent(const std::string& eventName, const Ogre::Vector3& position, bool forced,
        const std::string& visualName = std::string());

    //! rief A trap or door effect sent by the server (ServerNotificationType::trapEffect): kind is a
    //! TrapEffectKind, typeName the type of the trap or door, fraction the health left of a door.
    //! Shows the events TrapFired, TrapLinked, DoorHit, DoorHurt (health at half or less) or DoorWrecked
    //! at the tile; the type name is matched like a tile visual in "Match" of the event effects.
    void notifyTrapEffect(int32_t kind, int32_t tileX, int32_t tileY, const std::string& typeName, float fraction);

    inline uint32_t getNbParticleSystems() const
    { return static_cast<uint32_t>(mEmitters.size() + mOneShots.size()); }
    inline uint32_t getNbMovedObjects() const
    { return static_cast<uint32_t>(mMotionNodes.size()); }

private:
    struct Emitter
    {
        Emitter() :
            mEffect(0), mNode(nullptr), mSystem(nullptr), mFade(-1.0), mBaseWidth(1.0), mBaseHeight(1.0),
            mPhase(0.0), mSeen(false)
        {}

        uint32_t mEffect;
        Ogre::SceneNode* mNode;
        Ogre::ParticleSystem* mSystem;
        //! Seconds since the emitter was told to stop, negative while it is running
        double mFade;
        double mBaseWidth;
        double mBaseHeight;
        double mPhase;
        bool mSeen;
    };

    struct OneShot
    {
        OneShot() :
            mNode(nullptr), mSystem(nullptr), mLife(0.0)
        {}

        Ogre::SceneNode* mNode;
        Ogre::ParticleSystem* mSystem;
        double mLife;
    };

    struct MotionInstance
    {
        MotionInstance() :
            mEffect(0), mPhase(0.0), mIntensity(0.0), mWanted(false)
        {}

        uint32_t mEffect;
        double mPhase;
        double mIntensity;
        bool mWanted;
    };

    //! \brief An object that is moved, with what is needed to put it back
    struct MotionNode
    {
        MotionNode() :
            mMovesPosition(false), mMovesOrientation(false), mMovesScale(false),
            mBasePosition(Ogre::Vector3::ZERO), mBaseScale(Ogre::Vector3::UNIT_SCALE), mClock(0.0), mSeen(false)
        {}

        std::string mNodeName;
        //! Which parts of the node are driven by the motions (put back only these)
        bool mMovesPosition;
        bool mMovesOrientation;
        bool mMovesScale;
        Ogre::Quaternion mBaseOrientation;
        Ogre::Vector3 mBasePosition;
        Ogre::Vector3 mBaseScale;
        double mClock;
        bool mSeen;
        std::vector<MotionInstance> mMotions;
    };

    //! \brief A place where an effect could be shown, found by the scan
    struct Candidate
    {
        Candidate() :
            mEffect(0), mPosition(Ogre::Vector3::ZERO), mDistance(0.0), mPriority(0), mActive(false)
        {}

        uint32_t mEffect;
        //! Name of the entity (objects) or the tile (tiles)
        std::string mTarget;
        //! Name of the scene node to move when the target is not an entity (bridge of a tile)
        std::string mNodeName;
        Ogre::Vector3 mPosition;
        double mDistance;
        int32_t mPriority;
        bool mActive;
    };

    struct BusyInfo
    {
        BusyInfo() :
            mLastBusy(0.0), mLastTouched(0.0)
        {}

        double mLastBusy;
        double mLastTouched;
    };

    void buildIndex();
    void scan();
    void scanObjects(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition);
    void scanTiles(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition, const Ogre::Vector3& lookPoint);
    void scanEntityEvents(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition);
    void reconcile();
    void playClips();
    void updateEmitters(double timeSinceLastFrame);
    void updateOneShots(double timeSinceLastFrame);
    void updateMotions(double timeSinceLastFrame);
    void destroyEmitter(Emitter& emitter);
    void restoreMotionNode(MotionNode& motionNode);

    bool isCreatureNear(double x, double y, double radius) const;
    //! \brief Updates and returns the state "no creature for a while" of a target
    bool isIdleLongEnough(const std::string& key, bool busy, double after);
    double getDistanceLimit(const AmbienceEffect& effect) const;
    bool isEffectUsable(const AmbienceEffect& effect) const;
    bool createParticleSystem(const std::string& system, const Ogre::Vector3& position, const std::string& baseName,
        Ogre::SceneNode*& node, Ogre::ParticleSystem*& particleSystem);
    const std::vector<uint32_t>& getObjectEffects(const std::string& meshName, const std::string& kind);
    std::vector<uint32_t> getBridgeEffects(Tile* tile) const;
    bool isVisibleNear(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition, const Ogre::Vector3& position,
        double radius, double limit) const;

    GameMap* mGameMap;
    std::string mConfigPath;
    RoomAmbienceConfig mConfig;
    Mode mMode;
    double mClock;
    double mScanTimer;
    double mPruneTimer;
    uint32_t mUniqueNumber;
    //! Names of missing particle systems already reported
    std::set<std::string> mMissingSystems;

    //! Effects per tile visual (indexed by the TileVisual value), per mesh name (memo) and per event
    std::vector<std::vector<uint32_t> > mTileEffects;
    std::map<std::string, std::vector<uint32_t> > mObjectEffectsMemo;
    std::map<std::string, std::vector<uint32_t> > mEventEffects;
    //! Effects of bridge tiles, per bridge mesh and per tile visual (lavaGround, waterGround)
    std::map<std::string, std::vector<uint32_t> > mBridgeEffects;
    std::vector<uint32_t> mNoEffects;
    std::vector<uint32_t> mObjectWildcardEffects;
    double mScanRadius;

    std::map<std::string, Emitter> mEmitters;
    std::vector<OneShot> mOneShots;
    std::map<std::string, MotionNode> mMotionNodes;
    std::map<std::string, BusyInfo> mBusy;
    std::map<std::string, double> mLastEventTime;
    //! Time until which a door (key "x,y" of its tile) counts as hit, for the effects "When Hit"
    std::map<std::string, double> mHitUntil;

    //! Positions of the creatures on the map at the last scan
    std::vector<Ogre::Vector3> mCreaturePositions;
    std::vector<Candidate> mParticleCandidates;
    std::vector<Candidate> mMotionCandidates;
    std::vector<Candidate> mClipCandidates;
    //! Time at which an object plays its next clip (kind clip)
    std::map<std::string, double> mClipTimers;
    //! Dice of its own, so the game random sequence is untouched
    std::mt19937 mRandom;

    //! Tile visual seen at the last scan per tile (255 = never seen), used to find rooms built or sold
    std::vector<uint8_t> mSeenVisual;
    int32_t mSeenSizeX;
    int32_t mSeenSizeY;
    uint32_t mEventsThisScan;

    struct EntitySnapshot
    {
        EntitySnapshot() :
            mType(0), mPosition(Ogre::Vector3::ZERO), mGeneration(0)
        {}

        uint32_t mType;
        Ogre::Vector3 mPosition;
        uint32_t mGeneration;
    };
    std::map<std::string, EntitySnapshot> mKnownEntities;
    uint32_t mGeneration;
    bool mEntitiesInitialized;
};

#endif // ROOMAMBIENCE_H
