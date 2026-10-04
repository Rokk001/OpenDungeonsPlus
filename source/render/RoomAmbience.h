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
class Seat;
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
    //! (room) the event is about; empty = the one of the tile at the position. noThrottle lets the same event
    //! start again within a tenth of a second (a spell cast on several creatures at once).
    //! Returns the number of effects started
    uint32_t triggerEvent(const std::string& eventName, const Ogre::Vector3& position, bool forced,
        const std::string& visualName = std::string(), bool noThrottle = false);

    //! \brief A trap or door effect sent by the server (ServerNotificationType::trapEffect): kind is a
    //! TrapEffectKind, typeName the type of the trap or door, fraction the health left of a door.
    //! Kinds reloading and ready only set the state for the effects "When Reloading" and "When Ready".
    //! Shows the events TrapFired, TrapLinked, DoorHit, DoorHurt (health at half or less) or DoorWrecked
    //! at the tile; the type name is matched like a tile visual in "Match" of the event effects.
    void notifyTrapEffect(int32_t kind, int32_t tileX, int32_t tileY, const std::string& typeName, float fraction);

    //! \brief Plays the sound of the family (a folder below sounds/Spatial) at the position
    void playSound(const std::string& family, const Ogre::Vector3& position);

    //! \brief Moves the camera by the current shake. Called just before the frame is rendered; clearShake()
    //! takes it away again after the frame, so nothing else ever sees the shaken camera.
    void applyShake();
    void clearShake();

    inline uint32_t getNbParticleSystems() const
    { return static_cast<uint32_t>(mEmitters.size() + mOneShots.size() + mMarks.size()); }
    inline uint32_t getNbMovedObjects() const
    { return static_cast<uint32_t>(mMotionNodes.size() + mTurrets.size()); }

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

    //! \brief The remains of a destroyed barricade, which plays the clip Collapse and then sinks into the floor
    struct Collapse
    {
        Collapse() :
            mNode(nullptr), mEntity(nullptr), mAge(0.0), mBaseHeight(0.0)
        {}

        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        double mAge;
        double mBaseHeight;
    };

    //! \brief A cannon (or another object of an effect of kind turn) that follows creatures in range with its barrel
    struct Turret
    {
        Turret() :
            mEffect(0), mPosition(Ogre::Vector3::ZERO), mRestFront(Ogre::Vector3::NEGATIVE_UNIT_Y), mSeat(nullptr),
            mGeneration(0)
        {}

        std::string mNodeName;
        uint32_t mEffect;
        Ogre::Vector3 mPosition;
        //! Direction (flat) the object looked in when it was first seen, where it turns back to
        Ogre::Vector3 mRestFront;
        Seat* mSeat;
        uint32_t mGeneration;
    };

    //! \brief A rolling object (kind roll) with its dust trail, which breaks up at the end of its way
    struct Roller
    {
        Roller() :
            mNode(nullptr), mEntity(nullptr), mTrailNode(nullptr), mTrail(nullptr), mEffect(0), mStart(Ogre::Vector3::ZERO),
            mDirection(Ogre::Vector3::UNIT_X), mAge(0.0)
        {}

        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        Ogre::SceneNode* mTrailNode;
        Ogre::ParticleSystem* mTrail;
        uint32_t mEffect;
        Ogre::Vector3 mStart;
        Ogre::Vector3 mDirection;
        double mAge;
    };

    //! \brief Where a creature was at the last scan and whose it is
    struct CreatureSpot
    {
        CreatureSpot() :
            mPosition(Ogre::Vector3::ZERO), mSeat(nullptr)
        {}

        Ogre::Vector3 mPosition;
        Seat* mSeat;
    };

    //! \brief A sound that waits for its time (Delay of an event effect)
    struct PendingSound
    {
        PendingSound() :
            mPosition(Ogre::Vector3::ZERO), mDue(0.0)
        {}

        std::string mFamily;
        Ogre::Vector3 mPosition;
        double mDue;
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
    void scanCreatureEvents();
    void reconcile();
    void playClips();
    void updateEmitters(double timeSinceLastFrame);
    void updateOneShots(std::vector<OneShot>& oneShots, double timeSinceLastFrame);
    void updatePendingSounds();
    //! \brief Lets a destroyed barricade (the door entity on the tile, which the server is about to remove)
    //! fall into a heap with the clip Collapse of its skeleton
    void startCollapse(int32_t tileX, int32_t tileY);
    void updateCollapses(double timeSinceLastFrame);
    void destroyCollapse(Collapse& collapse);
    //! \brief Lets the objects of effects of kind turn follow the creatures near them, or go back to rest
    void updateTurrets(double timeSinceLastFrame);
    void restoreTurret(const Turret& turret);
    //! \brief Starts a rolling object of the effect (kind roll) at the given place; true if it was started
    bool startRoll(const AmbienceEffect& effect, uint32_t effectIndex, const Ogre::Vector3& position);
    void updateRollers(double timeSinceLastFrame);
    //! \brief Ends a roller: the object goes; with leaveEffects its fragments and the last dust stay for a moment
    void finishRoller(Roller& roller, bool leaveEffects);
    void updateShake(double timeSinceLastFrame);
    //! \brief Starts a view shake of the effect (kind shake) for an event at the given place
    void startShake(const AmbienceEffect& effect, const Ogre::Vector3& position, const Ogre::Vector3& lookPoint);
    void updateMotions(double timeSinceLastFrame);
    void destroyEmitter(Emitter& emitter);
    void restoreMotionNode(MotionNode& motionNode);

    bool isCreatureNear(double x, double y, double radius) const;
    //! \brief True if the dungeon heart at the position belongs to the local keeper and its health fraction (as the
    //! heart badge shows it) is below the given value
    bool isLocalHeartBelow(const Ogre::Vector3& position, double below) const;
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
    //! Ground marks (kind mark), oldest first
    std::vector<OneShot> mMarks;
    std::map<std::string, MotionNode> mMotionNodes;
    //! Objects that follow creatures (kind turn), per entity name
    std::map<std::string, Turret> mTurrets;
    //! Time until which a trap (key "x,y" of its tile) keeps its turn, because the server aims it for a shot
    std::map<std::string, double> mTurretHoldUntil;
    std::vector<Roller> mRollers;
    std::vector<CreatureSpot> mCreatureSpots;
    std::map<std::string, BusyInfo> mBusy;
    std::map<std::string, double> mLastEventTime;
    //! View shake: seconds left and in total, strength in world units at the start, shakes per second, phase
    double mShakeTime;
    double mShakeTotal;
    double mShakeAmount;
    double mShakeSpeed;
    double mShakePhase;
    //! Offset the camera node was moved by in applyShake (zero when not applied)
    Ogre::Vector3 mShakeApplied;
    //! Time until which a door (key "x,y" of its tile) counts as hit, for the effects "When Hit"
    std::map<std::string, double> mHitUntil;
    //! Time until which a trap (key "x,y" of its tile) counts as reloading or empty, for the effects
    //! "When Reloading" and "When Ready"
    std::map<std::string, double> mReloadingUntil;
    //! Time until which a door (key "x,y" of its tile) counts as destroyed, so that it is not also reported as sold
    std::map<std::string, double> mWreckedUntil;
    std::vector<PendingSound> mPendingSounds;
    std::vector<Collapse> mCollapses;

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
    //! What was seen of a creature at the last scan (dormitory wake-up, enemy in a guard room, healing, casino game)
    struct CreatureSnapshot
    {
        CreatureSnapshot() :
            mHp(0.0), mSleeping(false), mAttacking(false), mEnemyInGuardRoom(false), mLastHealed(-100.0), mGeneration(0)
        {}

        double mHp;
        bool mSleeping;
        //! Plays the attack animation (the winner of a casino game)
        bool mAttacking;
        bool mEnemyInGuardRoom;
        double mLastHealed;
        uint32_t mGeneration;
    };
    std::map<std::string, CreatureSnapshot> mKnownCreatures;
    bool mCreaturesInitialized;
    std::map<std::string, EntitySnapshot> mKnownEntities;
    uint32_t mGeneration;
    bool mEntitiesInitialized;
};

#endif // ROOMAMBIENCE_H
