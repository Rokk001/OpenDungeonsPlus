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
#include "render/RoomAmbienceExtras.h"
#include "render/WallTorchView.h"

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
class MovableGameEntity;
class RenderedMovableEntity;
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
    //! owner is the seat the thing of the event belongs to: effects with OwnerOnly are only shown to the keeper of
    //! that seat (never when the owner is not given).
    //! creatureName is the creature the event is about (empty = none); only the effects of kind CreatureClip use it.
    //! Returns the number of effects started
    uint32_t triggerEvent(const std::string& eventName, const Ogre::Vector3& position, bool forced,
        const std::string& visualName = std::string(), bool noThrottle = false, const Seat* owner = nullptr,
        const std::string& creatureName = std::string());

    //! \brief The grain levels of a hatchery as the server told them (cosmetic event hatcheryGrain): maxLevel the
    //! level of a full tile, validSeconds how long the list may be trusted, text "x,y,level;..." the tiles that are
    //! not full. Effects with "GrainMin" follow the levels; a tile that lost grain since the last message shows
    //! the event GrainPecked.
    void notifyHatcheryGrain(const std::string& roomName, int32_t maxLevel, int32_t validSeconds, const std::string& text);

    //! \brief A trap or door effect sent by the server (ServerNotificationType::trapEffect): kind is a
    //! TrapEffectKind, typeName the type of the trap or door, fraction the health left of a door.
    //! Kinds reloading and ready only set the state for the effects "When Reloading" and "When Ready".
    //! Shows the events TrapFired, TrapLinked, DoorHit, DoorHurt (health at half or less) or DoorWrecked
    //! at the tile; the type name is matched like a tile visual in "Match" of the event effects.
    void notifyTrapEffect(int32_t kind, int32_t tileX, int32_t tileY, const std::string& typeName, float fraction);

    //! \brief Replaces the wall torches that are shown by the list the server sent. The client
    //! derives nothing; the torches are drawn as they are listed (see WallTorchView)
    void setWallTorchSpots(const std::vector<WallTorchSpot>& spots);

    //! \brief The local keeper has sent a spell cast: shows the event SpellFxHandCast at the place of the keeper's hand
    void noteHandCast(const Ogre::Vector3& handPosition);

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

    //! \brief Forgets the beat of all hearts (the extras tell them again after every scan)
    inline void clearHeartRates()
    { mHeartRates.clear(); }

    //! \brief Speed factor of the effects marked "HeartRate" that sit at the heart at position (1 = calm
    //! heart, more = hurt heart). Every heart beats on its own; effects far from all told hearts stay calm.
    inline void addHeartRate(const Ogre::Vector3& position, double factor)
    { mHeartRates.push_back(HeartRate(position, factor)); }

private:
    struct Emitter
    {
        Emitter() :
            mEffect(0), mNode(nullptr), mSystem(nullptr), mEntity(nullptr), mFade(-1.0), mBaseWidth(1.0),
            mBaseHeight(1.0), mPhase(0.0), mCycle(0.0), mSeen(false)
        {}

        uint32_t mEffect;
        Ogre::SceneNode* mNode;
        Ogre::ParticleSystem* mSystem;
        //! The decoration mesh of an effect of the kind model (no particle system then)
        Ogre::Entity* mEntity;
        Ogre::Quaternion mBaseOrientation;
        Ogre::Vector3 mBasePosition;
        //! Seconds since the emitter was told to stop, negative while it is running
        double mFade;
        double mBaseWidth;
        double mBaseHeight;
        double mPhase;
        //! Cycles of the flicker so far (only used by effects that follow the heart rate)
        double mCycle;
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

    //! \brief The remains of a destroyed door, which plays the clip Collapse (barricade) or Destroyed (every other
    //! door) and then sinks into the floor
    struct Collapse
    {
        Collapse() :
            mNode(nullptr), mEntity(nullptr), mAge(0.0), mBaseHeight(0.0)
        {}

        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        double mAge;
        double mBaseHeight;
        std::string mClip;
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

    //! \brief A bolt (kind beam) or a flying object (kind projectile) on its way to the target
    struct Flight
    {
        Flight() :
            mNode(nullptr), mEntity(nullptr), mTrailNode(nullptr), mTrailSystem(nullptr), mBeam(false),
            mStart(Ogre::Vector3::ZERO), mEnd(Ogre::Vector3::ZERO), mAge(0.0), mDuration(0.4), mWidth(1.0),
            mArc(0.0), mFlickerRate(20.0), mFlickerClock(0.0)
        {}

        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        Ogre::SceneNode* mTrailNode;
        Ogre::ParticleSystem* mTrailSystem;
        bool mBeam;
        Ogre::Vector3 mStart;
        Ogre::Vector3 mEnd;
        double mAge;
        double mDuration;
        double mWidth;
        double mArc;
        double mFlickerRate;
        double mFlickerClock;
        //! Event raised at the target on arrival (projectile)
        std::string mLand;
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
            mEffect(0), mPhase(0.0), mCycle(0.0), mIntensity(0.0), mWanted(false)
        {}

        uint32_t mEffect;
        double mPhase;
        //! Cycles of the motion so far (only used by effects that follow the heart rate)
        double mCycle;
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
            mEffect(0), mPosition(Ogre::Vector3::ZERO), mDistance(0.0), mPriority(0), mYaw(0.0), mActive(false)
        {}

        uint32_t mEffect;
        //! Name of the entity (objects) or the tile (tiles)
        std::string mTarget;
        //! Name of the scene node to move when the target is not an entity (bridge of a tile)
        std::string mNodeName;
        Ogre::Vector3 mPosition;
        double mDistance;
        int32_t mPriority;
        //! Degrees around the vertical axis (kind model): the decoration looks away from the wall
        double mYaw;
        bool mActive;
    };

    struct BusyInfo
    {
        BusyInfo() :
            mLastBusy(0.0), mLastTouched(0.0), mEverBusy(false)
        {}

        double mLastBusy;
        double mLastTouched;
        //! A creature was close at some time (used for "Vacated")
        bool mEverBusy;
    };

    void buildIndex();
    void scan();
    //! \brief Hands the torch list of the client map to mWallTorches when it has changed
    void syncWallTorches();
    void scanObjects(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition);
    void scanTiles(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition, const Ogre::Vector3& lookPoint);
    void scanEntityEvents(Ogre::Camera* camera, const Ogre::Vector3& cameraPosition);
    void scanCreatureEvents();
    //! \brief Raises HeartHit (and the state for "When Hit") when the health of the own dungeon heart, as the heart badge
    //! shows it, has gone down since the last scan
    void scanHeartHit();
    void reconcile();
    void playClips();
    void updateEmitters(double timeSinceLastFrame);
    void updateOneShots(std::vector<OneShot>& oneShots, double timeSinceLastFrame);
    void updatePendingSounds();
    //! \brief Lets a destroyed door (the door entity of the given type on the tile, which the server is about to
    //! remove) play the clip Collapse (barricade) or Destroyed (every other door) of its skeleton on a ghost copy
    void startCollapse(int32_t tileX, int32_t tileY, const std::string& typeName);
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
    //! \brief Starts a beam or a projectile (effect kinds beam and projectile) for an event at the given place
    void startFlight(const AmbienceEffect& effect, const Ogre::Vector3& position);
    void updateFlights(double timeSinceLastFrame);
    void destroyFlight(Flight& flight);
    //! \brief Starts a view shake of the effect (kind shake) for an event at the given place
    void startShake(const AmbienceEffect& effect, const Ogre::Vector3& position, const Ogre::Vector3& lookPoint);
    void updateMotions(double timeSinceLastFrame);
    void destroyEmitter(Emitter& emitter);
    bool createModel(const std::string& mesh, const Ogre::Vector3& position, double yaw, const std::string& baseName,
        Ogre::SceneNode*& node, Ogre::Entity*& entity);
    void moveModel(Emitter& emitter, const AmbienceEffect& effect, double timeSinceLastFrame);
    void restoreMotionNode(MotionNode& motionNode);

    bool isCreatureNear(double x, double y, double radius) const;
    //! \brief True if a creature that sleeps is within the radius of the point
    bool isSleeperNear(double x, double y, double radius) const;
    //! \brief True if the skeleton of the entity has the clip (remembered per mesh, so a missing clip costs nothing)
    bool hasClip(MovableGameEntity* entity, const std::string& clip);
    //! \brief Plays the clip of an event effect (kind clip) once on the nearest object of Object within Amount tiles of
    //! the position; false when there is none or it has no such clip
    bool playEventClip(const AmbienceEffect& effect, const Ogre::Vector3& position);
    //! \brief Plays the clip of an event effect (kind creatureClip) once on the creature; false when it is on its way,
    //! unknown or has no such clip
    bool playCreatureClip(const AmbienceEffect& effect, const std::string& creatureName);
    //! \brief Lets an object that loops the clip of the effect (kind clip with Loop) finish on the last pose of the clip,
    //! which is its pose at rest
    void stopLoopClip(RenderedMovableEntity* entity, const AmbienceEffect& effect);
    //! \brief True if the dungeon heart at the position belongs to the local keeper and its health fraction (as the
    //! heart badge shows it) is below the given value
    bool isLocalHeartBelow(const Ogre::Vector3& position, double below) const;
    //! \brief Updates and returns the state "no creature for a while" of a target
    bool isIdleLongEnough(const std::string& key, bool busy, double after);
    //! \brief The state "Empty" or "Vacated" of a target, depending on the effect
    bool isIdleState(const AmbienceEffect& effect, const std::string& key, bool busy);
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
    //! Names of missing particle systems and meshes already reported
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
    struct HeartRate
    {
        HeartRate(const Ogre::Vector3& position, double factor) :
            mPosition(position), mFactor(factor)
        {}

        Ogre::Vector3 mPosition;
        double mFactor;
    };

    //! \brief Beat factor of the heart nearest to position, 1 if there is none within a few tiles
    double getHeartRateFactor(const Ogre::Vector3& position) const;

    std::vector<HeartRate> mHeartRates;

    //! The grain of one hatchery as last told by the server
    struct GrainRoom
    {
        GrainRoom() :
            mMax(0), mExpire(0.0)
        {}

        //! Level of the tiles that are not full, by x * 65536 + y
        std::map<int64_t, int32_t> mLevels;
        int32_t mMax;
        //! Clock time after which the list is not trusted any more
        double mExpire;
    };

    //! \brief Grain level of the floor of a hatchery tile; 0 (no grain shown) while the server has not told the grain of its hatchery yet
    int32_t getGrainLevel(Tile* tile) const;

    std::map<std::string, GrainRoom> mGrainRooms;
    RoomAmbienceExtras mExtras;
    WallTorchView mWallTorches;
    //! Version of GameMap::getWallTorches() that was handed to mWallTorches last
    uint32_t mWallTorchesVersion;

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
    std::vector<Flight> mFlights;

    //! Positions of the creatures on the map at the last scan
    std::vector<Ogre::Vector3> mCreaturePositions;
    //! Positions of the creatures that sleep at the last scan
    std::vector<Ogre::Vector3> mSleeperPositions;
    std::vector<Candidate> mParticleCandidates;
    std::vector<Candidate> mMotionCandidates;
    std::vector<Candidate> mClipCandidates;
    //! Time at which an object plays its next clip (kind clip)
    std::map<std::string, double> mClipTimers;
    //! Time until which an object plays a clip of an event (a bed that wakes up) and must not be restarted by a looping clip
    std::map<std::string, double> mClipHoldUntil;
    //! Clips that a mesh has (key "mesh|clip"), so that the skeleton is asked only once
    std::map<std::string, bool> mClipKnown;
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
    //! What was seen of a creature at the last scan (dormitory wake-up, enemy in a guard room, healing)
    struct CreatureSnapshot
    {
        CreatureSnapshot() :
            mHp(0.0), mSleeping(false), mPrisoner(false), mSeat(nullptr), mEnemyInGuardRoom(false),
            mLastHealed(-100.0), mGeneration(0)
        {}

        double mHp;
        bool mSleeping;
        //! Is in jail (a prison or a torture chamber)
        bool mPrisoner;
        //! The seat the creature belonged to (a change in a torture chamber is a conversion)
        Seat* mSeat;
        bool mEnemyInGuardRoom;
        double mLastHealed;
        uint32_t mGeneration;
    };
    std::map<std::string, CreatureSnapshot> mKnownCreatures;
    bool mCreaturesInitialized;
    std::map<std::string, EntitySnapshot> mKnownEntities;
    uint32_t mGeneration;
    bool mEntitiesInitialized;
    //! Heart health (points) of the badge at the last scan, negative while unknown
    double mLastHeartHP;
};

#endif // ROOMAMBIENCE_H
