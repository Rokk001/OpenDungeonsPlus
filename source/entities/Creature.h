/*!
 * \file   Creature.h
 * \brief  Creature class
 *
 *  Copyright (C) 2011-2017  OpenDungeons Team
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

#ifndef CREATURE_H
#define CREATURE_H

#include "entities/MovableGameEntity.h"
#include "entities/CreatureActivity.h"
#include "entities/DefenceChance.h"
#include "eventsystem/CreatureMoved.h"
#include "eventsystem/Subject.h"
#include "game/CreatureAppearance.h"


#include <Ogre.h>
#include <Ogre.h>
#include <CEGUI/EventArgs.h>

#include <map>
#include <memory>
#include <string>

enum class RelationshipEvent;
struct RelationshipCreatureState;
class Building;
class Creature;
class CreatureAction;
class CreatureEffectDigTile;
class CreatureEffect;
class CreatureDefinition;
class CreatureOverlayStatus;
class CreatureSkill;
class DraggableTileContainer;
class GameMap;
class ODPacket;
class Player;
class Room;
class Weapon;

struct CosmeticEvent;

enum class CreatureActionType;
enum class CreatureMoodLevel;
enum class SkillType;

namespace CEGUI
{
class Window;
}

namespace social
{
enum class PostCategory : uint8_t;
struct CreatureSnapshot;
}

namespace Ogre
{
class ParticleSystem;
}

enum class CreatureSound
{
    Pickup,
    Drop,
    Attack,
    Die,
    Slap,
    Dig
};

class CreatureSkillData
{
public:
    CreatureSkillData(const CreatureSkill* skill, uint32_t cooldown, uint32_t warmup) :
        mSkill(skill),
        mCooldown(cooldown),
        mWarmup(warmup)
    {
    }

    const CreatureSkill* mSkill;
    uint32_t mCooldown;
    uint32_t mWarmup;
};

//! Class used on server side to link creature effects (spells, slap, ...) with particle effects
class CreatureParticleEffect : public EntityParticleEffect
{
public:
    CreatureParticleEffect(Creature& creature, const std::string& name, const std::string& script, int32_t nbTurnsEffect,
        CreatureEffect* effect);

    virtual ~CreatureParticleEffect();

    virtual EntityParticleEffectType getEntityParticleEffectType() const override
    { return EntityParticleEffectType::creature; }

    CreatureEffect* mEffect;
    Creature& mCreature;
};

/*! \class Creature Creature.h
 *  \brief Position, status, and AI state for a single game creature.
 *
 *  The creature class is the place where an individual creature's state is
 *  stored and manipulated.  The creature class is also used to store creature
 *  class descriptions, since a class decription is really just a subset of the
 *  overall creature information.  This is not really an optimal design and
 *  will probably be refined later but it works fine for now and the code
 *  affected by this change is relatively limited.
 */
class Creature: public MovableGameEntity, public Subject
{
    friend class ODClient;
public:
    
    bool parkingBit;
    
    bool parkedBit;
    
    CreatureEffectDigTile* mDiggingEffect;
    
    static const int32_t NB_TURNS_BEFORE_CHECKING_TASK;

    //! \brief Constructor for creatures. It generates an unique name
    Creature(GameMap* gameMap, const CreatureDefinition* definition, Seat* seat, Ogre::Vector3 position = Ogre::Vector3(0.0f,0.0f,0.0f));
    virtual ~Creature();

    static const uint32_t NB_OVERLAY_HEALTH_VALUES;

    virtual GameEntityType getObjectType() const override;

    virtual void addToGameMap(GameMap* gameMap = nullptr) override;
    virtual void removeFromGameMap(GameMap* gameMap = nullptr) override;

    bool canDisplayStatsWindow(Seat* seat) override
    { return true; }
    void createStatsWindow() override;
    void destroyStatsWindow();
    bool CloseStatsWindow(const CEGUI::EventArgs& /*e*/);
    void updateStatsWindow(const std::string& txt);
    bool ProfileTabClicked(const CEGUI::EventArgs& /*e*/);
    bool StatsTabClicked(const CEGUI::EventArgs& /*e*/);
    bool BookTabClicked(const CEGUI::EventArgs& /*e*/);
    //! \brief A friend or foe name of the card was clicked: opens the Dungeonbook with that creature.
    bool ProfileLinkClicked(const CEGUI::EventArgs& e);
    //! \brief Fills a profile page (gui/WindowCreatureProfilePage.layout) with the social profile of the
    //! creature. Used by the creature card and by the Dungeonbook. The names in the friends and foe rows are
    //! buttons (FriendLink0, FriendLink1, FoeLink) carrying the creature name in the user string "Creature"; the
    //! caller decides what a click does. Returns the bottom edge of the page content in design pixels.
    float fillProfilePage(CEGUI::Window* page);

    //! \brief Gender of the creature ("Female", "Male" or empty), derived from its name and class. Same
    //! value as the profile gender shown on the client, so it can be used on the server.
    std::string getGender() const;

    //! \brief Dungeonbook appearance (catalog id plus chosen option per slot). Chosen once on the server
    //! when the creature spawns (or derived from the name for old saves) and never changed afterwards.
    //! Empty for creatures without a catalog id or while no manifest exists.
    const CreatureAppearance& getAppearance() const
    { return mAppearance; }

    //! \brief Client side. Takes over the appearance the server sent in the creature message of
    //! ServerNotificationType::creatureAppearance. Ignored on the server.
    void setAppearanceFromServer(const CreatureAppearance& appearance);
    std::string getStatsText();

    //! \brief Client side. One line with the strongest friend and the worst enemy of a creature of the
    //! local player or its allies, e.g. "Closest: Name (friend) - Against: Name (nemesis)". Empty if the
    //! option is off, the creature belongs to somebody else or it has no relationships.
    std::string getRelationshipTooltip();

    //! \brief Get the level of the object
    inline unsigned int getLevel() const
    { return mLevel; }

    //! \brief Shown size of the creature relative to its base size: 1 at level 1, growing linearly with the level to
    //! 1 + CreatureLevelGrowthMax (global.cfg) at the highest level
    double getLevelScale() const;

    inline double getHP(Tile *tile) const override
    { return mHp; }

    bool isAlive() const;

    //! \brief Gets the maximum HP the creature can have currently
    inline double getMaxHp() const
    { return mMaxHP; }

    //! \brief Gets the maximum HP the creature can have currently
    inline double getHP() const
    { return mHp; }

    //! \brief Rough combat strength used for fear and target priority. It grows with
    //! the current health and the level.
    double getThreat() const;

    //! \brief Gets the current dig rate
    inline double getDigRate() const
    { return mDigRate; }

    //! \brief Gets the current claim rate
    inline double getClaimRate() const
    { return mClaimRate; }

    //! \brief Gets pointer to the Weapon in left hand
    inline const Weapon* getWeaponL() const
    { return mWeaponL; }

    //! \brief Gets pointer to the Weapon in right hand
    inline const Weapon* getWeaponR() const
    { return mWeaponR; }

    //! \brief Pointer to the creatures home tile, where its bed is located
    inline Tile* getHomeTile() const
    { return mHomeTile; }

    //! \brief Pointer to the creature type specification
    inline const CreatureDefinition* getDefinition() const
    { return mDefinition; }

    inline CreatureMoodLevel getMoodValue() const
    { return mMoodValue; }

    CreatureActivity getActivity() const;

    double getExperienceProgress() const;
    uint32_t getAttackRecoveryTurns() const { return mAttackRecoveryTurns; }
    uint32_t getAttackRecoveryDuration() const { return mAttackRecoveryDuration; }
    uint32_t getAttackRecoverySerial() const { return mAttackRecoverySerial; }
    bool hasProgressInformation() const { return mHasProgressInformation; }

    inline int32_t getNbTurnFurious() const
    { return mNbTurnFurious; }

    //! \brief Number of turns the creature has been held in the hand (decreases after being dropped)
    inline int32_t getNbTurnsInHand() const
    { return mNbTurnsInHand; }

    //! \brief Number of times the creature wanted to work but found no job (reset when it works)
    inline int32_t getNbTurnsOutOfWork() const
    { return mNbTurnsOutOfWork; }

    inline void increaseNbTurnsOutOfWork()
    { ++mNbTurnsOutOfWork; }

    inline void resetNbTurnsOutOfWork()
    { mNbTurnsOutOfWork = 0; }

    //! \brief Number of turns of torture still weighing on the mood (fades after the torture stops)
    inline int32_t getNbTurnsTortureMood() const
    { return mNbTurnsTortureMood; }

    //! \brief Number of turns of sleep in the lair still relieving the mood (fades after waking up)
    inline int32_t getNbTurnsRested() const
    { return mNbTurnsRested; }

    //! \brief Number of turns spent near a creature of the opposite alignment, fading after leaving it
    inline int32_t getNbTurnsHatedCompany() const
    { return mNbTurnsHatedCompany; }

    //! \brief Good creatures are the ones of the hero faction, all others are evil
    bool isGoodAligned() const;

    //! \brief True if a creature of the opposite alignment of an allied seat is close
    bool isHatedCompanyNear() const;

    //! \brief Mood points the arena gave to the creature (positive) or took from it (negative). Fades over time
    inline double getPitMood() const
    { return mPitMood; }

    //! \brief Changes the pit mood points. They are limited by the PitMoodMax room setting
    void addPitMood(double points);

    //! \brief Called on server side each turn the creature sleeps in its lair
    inline void markRested()
    { mRestedThisTurn = true; }

    //! \brief Number of slaps received during the last nbTurns turns
    int32_t getNbRecentSlaps(int32_t nbTurns) const;

    void setPosition(const Ogre::Vector3& v, GameMap *gameMap = nullptr ) override;

    //! \brief Gets the move speed on the current tile.
    virtual double getMoveSpeed() const override;

    //! \brief Gets the move speed on the current tile.
    double getMoveSpeed(Tile* tile) const;

    //! \brief Share of its normal speed a worker walks at while it pulls a hurt creature (from the room
    //! configuration, between 0.1 and 1)
    static double getDragWorkerSpeedFactor();

    //! \brief Gets the creature depending the terrain type.
    inline double getMoveSpeedGround() const
    { return mGroundSpeed; }
    inline double getMoveSpeedWater() const
    { return mWaterSpeed; }
    inline double getMoveSpeedLava() const
    { return mLavaSpeed; }

    inline int32_t getKoTurnCounter() const
    { return mKoTurnCounter; }

    //! \brief Updates the entity path, movement, and direction, and creature attack time
    //! \param timeSinceLastFrame the elapsed time since last displayed frame in seconds.
    virtual void update(Ogre::Real timeSinceLastFrame) override;

    bool parkToWallTile(Tile* wallTile, Tile* nTile);
    
    bool setDestination(Tile* tile);

    //! \brief Picks a destination far away in the visible tiles and goes there
    //! Returns true if a valid Tile was found. The creature will go there
    //! Returns false if no reachable Tile was found
    bool wanderRandomly(const std::string& animationState);

    void setHP(double nHP);

    void heal(double hp);

    inline void setHomeTile(Tile* ht)
    { mHomeTile = ht; }

    //! \brief Set the level of the creature
    void setLevel(unsigned int level);

    //! \brief Called when the creature dies or is KO to death. triggers death animation, stops
    //! the creature job and drops what it is carrying
    void dropCarriedEquipment();

    /*! \brief The main AI routine which decides what the creature will do and carries out that action.
     *
     * The doUpkeep routine is the heart of the Creature AI subsystem.  The other,
     * higher level, functions such as GameMap::doUpkeep() ultimately just call this
     * function to make the creatures act.
     *
     * The function begins in a pre-cognition phase which prepares the creature's
     * brain state for decision making.  This involves generating lists of known
     * about creatures, either through sight, hearing, keeper knowledge, etc, as
     * well as some other bookkeeping stuff.
     *
     * Next the function enters the cognition phase where the creature's current
     * state is examined and a decision is made about what to do.  The state of the
     * creature is in the form of a queue, which is really used more like a stack.
     * If the queue is empty,  the 'idle' action is used. It acts as a "last resort"
     * for when the creature completely runs out of things to do. Other actions such
     * as 'walkToTile' or 'job' can be pushed to  determine the what the creature
     * will do. Once the action is finished (because the creature is tired or there is
     * nothing related to do), the action will be popped and the previous one will be
     * used (if any - idle otherwise). This allows actions to be carried out recursively,
     * i.e. if a creature is trying to dig a tile and it is not nearby it can begin
     * walking toward the tile as a new action, and when it arrives at the tile it will
     * revert to the 'digTile' action.
     */
    void doUpkeep() override;

    //! \brief Computes the visible tiles and tags them to know which are visible
    void computeVisibleTiles();

    virtual bool isAttackable(Tile* tile, Seat* seat) const override;

    double getPhysicalDefense() const;
    double getMagicalDefense() const;
    double getElementDefense() const;

    //! \brief Check whether a creature has earned one level. If yes, handle leveling it up
    void checkLevelUp();

    //! \brief Updates the lists of tiles within sight radius.
    //! And the tiles the creature can "see" (removing the ones behind walls).
    void updateTilesInSight();

    //! \brief Loops over the visibleTiles and adds all enemy creatures in each tile to a list which it returns.
    std::vector<GameEntity*> getVisibleEnemyObjects();

    //! \brief Loops over objectsToCheck and returns a vector containing all the ones which can be reached via a valid path.
    std::vector<GameEntity*> getReachableAttackableObjects(const std::vector<GameEntity*> &objectsToCheck);

    //! \brief Loops over objectsToCheck and returns a vector containing all the creatures in the list.
    std::vector<GameEntity*> getCreaturesFromList(const std::vector<GameEntity*> &objectsToCheck, bool workersOnly);

    //! \brief Loops over the visibleTiles and adds all allied creatures in each tile to a list which it returns.
    std::vector<GameEntity*> getVisibleAlliedObjects();

    //! \brief Loops over the visibleTiles and returns any creatures in those tiles
    //! allied with the given seat (or if invert is true, does not allied)
    std::vector<GameEntity*> getVisibleForce(Seat* seat, bool invert);

    //! \brief Conform: GameEntity functions handling covered tiles
    std::vector<Tile*> getCoveredTiles() override;
    Tile* getCoveredTile(int index) override;
    uint32_t numCoveredTiles() const override;

    //! \brief Conform: AttackableObject - Deducts a given amount of HP from this creature.
    //! \brief Share of the damage taken from the attacker: reduced when both fight inside an arena
    double getPitDamageFactor(GameEntity* attacker);

    //! brief Server side. True if the creature can take part in relationships: the option is on,
    //! it belongs to a keeper (no hero, no neutral creature), is not a worker and not a prisoner.
    bool canHaveRelationships() const;

    //! brief Server side. Reports a relationship event between two creatures of the same keeper. Does
    //! nothing if the option is off or one of them cannot have relationships.
    static void reportRelationshipEvent(RelationshipEvent event, Creature& creatureA, Creature& creatureB);

    //! brief Server side. Called right after a prisoner was converted to a new keeper: the creatures
    //! of that keeper that captured it become its first (negative) relationships.
    void startConvertedRelationships();

    //! brief Server side. Called when this creature was defeated: every pair of creatures of the
    //! killer's keeper that hit it recently (and the killer itself) fought together.
    void reportFightParticipants(Creature& killer);

    //! Server side. Defense added (or taken away) because of the creatures that fight next to this
    //! one, 0 if the option is off. Added to all three defense values.
    double getRelationshipCombatModifier() const;

    //! Server side. Mood points from the hated creatures of the same keeper and from relationship
    //! events (grief, ...), 0 if the option is off.
    int32_t getRelationshipMood() const;

    //! Server side. Adds mood points (negative or positive) that fade again, does nothing if the
    //! creature cannot have relationships.
    void addRelationshipMood(int32_t points);

    //! Server side. Called when this creature died: its friends grieve, and get a rage against
    //! the side of the killer (may be nullptr).
    void reportDeathToFriends(GameEntity* killer);

    //! Server side. Called when this creature was slapped: its friends that see it lose mood.
    void reportSlapToFriends();

    //! Server side. Called while this creature sleeps in its bed: a friend sleeping in a bed close by
    //! raises its mood a little.
    void reportSleepingNextToFriends();

    //! Server side. Called when this creature eats: a friend that eats at the same time close by
    //! raises its mood a little.
    void reportEatingWithFriends();

    //! Server side. Called when this creature starts to leave the dungeon unhappy: its best friend
    //! may leave with it (chance from the settings).
    void reportLeavingToBestFriend();

    //! Server side. Factor for the damage this creature deals to a creature of victimSeat: more
    //! than 1.0 while it is enraged about the death of a friend killed by that side.
    double getRelationshipRageFactor(const Seat* victimSeat) const;

    //! Server side. True if the creature is part of a nemesis brawl.
    inline bool isBrawling() const
    { return !mBrawlOpponent.empty(); }

    //! Server side. Starts a brawl with the opponent: both fight to knock the other one out
    //! (never to kill) until updateBrawl ends it.
    void startBrawl(Creature& opponent);

    //! Server side. Checks the end conditions of the brawl (low health, interrupted, too long).
    void updateBrawl();

    //! Server side. Ends the brawl of this creature and of its opponent: both calm down but stay
    //! angry, and the relationship gets worse.
    void endBrawl();

    //! Server side. True if the creature can start a brawl now (idle, not in a fight and not hurt).
    bool canStartBrawl() const;

    //! Server side. Fills state with what has to be saved of the relationships of this creature
    //! (grief mood, rage, brawl). Returns false if there is nothing to save.
    bool getRelationshipState(RelationshipCreatureState& state) const;

    //! Server side. Restores what getRelationshipState saved. A saved brawl is only resumed
    //! when the opponent was restored too and both are able to fight again soon (see resumeBrawl).
    void setRelationshipState(const RelationshipCreatureState& state);

    //! Server side. Starts the brawl restored by setRelationshipState once both fighters can take
    //! part, gives up after a while.
    void resumeBrawl();
    double takeDamage(GameEntity* attacker, double absoluteDamage, double physicalDamage, double magicalDamage, double elementDamage,
        Tile *tileTakingDamage, bool ko) override;

    //! \brief Conform: AttackableObject - Adds experience to this creature.
    void receiveExp(double experience);

    //! \brief performs the given attack on the given target
    void useAttack(CreatureSkillData& skillData, GameEntity& entityAttack,
        Tile& tileAttack, bool ko, bool notifyPlayerIfHit);

    //! \brief Returns true if the given action is queued in the action list. False otherwise
    bool isActionInList(CreatureActionType action) const;

    //! \brief Clears the action queue, except for the Idle action at the end.
    void clearActionQueue();

    //! \brief Computes the tiles visible for the creature and sends a message to the clients to mark those tiles. This function
    //! should be called on server side only
    void computeVisualDebugEntities();

    //! \brief Displays a mesh on all of the tiles in the list. This function should be called on client side only
    void refreshVisualDebugEntities(const std::vector<Tile*>& tiles);

    //! \brief Sends a message to the clients to stop displaying the tiles this creature sees
    void stopComputeVisualDebugEntities();

    //! \brief Destroy the meshes created by createVisualDebuggingEntities(). This function should be called on client side only
    void destroyVisualDebugEntities();

    //! \brief An accessor to return whether or not the creature has OGRE entities for its visual debugging entities.
    inline bool getHasVisualDebuggingEntities() const
    { return mHasVisualDebuggingEntities; }

    inline CreatureOverlayStatus* getOverlayStatus() const
    { return mOverlayStatus; }

    inline void setOverlayStatus(CreatureOverlayStatus* overlayStatus)
    { mOverlayStatus = overlayStatus; }

    //! \brief Get the text format of creatures in level files (already spawned at startup).
    //! \returns A string describing the IO format the creatures need to have in file.
    static std::string getCreatureStreamFormat();

    //! \brief Get a creature from a stream
    static Creature* getCreatureFromStream(GameMap* gameMap, std::istream& is);
    //! \brief Get a creature from a packet
    static Creature* getCreatureFromPacket(GameMap* gameMap, ODPacket& is);
    //! \brief Checks if the creature can be picked up. If yes, this function does the needed
    //! to prepare for the pickup (removing creature from GameMap, changing states, ...).
    //! Returns true if the creature can be picked up
    bool tryPickup(Seat* seat) override;

    //! \brief In a sandbox level, the player can pick up and drop the heroes of the hero seat
    bool isSandboxHeroFor(const Seat* seat) const;
    void pickup() override;
    bool tryDrop(Seat* seat, Tile* tile) override;
    void drop(const Ogre::Vector3& v) override;
    bool resizeMeshAfterDrop() override;

    //! \brief sets the speed modifier (coef)
    void setMoveSpeedModifier(double modifier);
    void clearMoveSpeedModifier();

    //! \brief sets the defense modifier
    void setDefenseModifier(double phy, double mag, double ele);
    void clearDefenseModifier();

    //! \brief sets the strength modifier (coef)
    void setStrengthModifier(double modifier);
    void clearStrengthModifier();

    virtual double getAnimationSpeedFactor() const override
    { return mSpeedModifier; }

    //! \brief Walk clips keep up with the slower speed of tired and badly hurt creatures, hurt creatures breathe a little slower when standing (clients only)
    virtual double getClientPoseSpeedFactor() const override;

    //! \brief Clients only: blends the tile speed ratio of the walk clips (see mClientTileSpeedRatio)
    virtual void updateClientPose(double timeSinceLastFrame) override;

    //! \brief Speed of the tile under the creature divided by its ground speed (1 when unknown), client side, no tired or hurt factor
    double getTileSpeedRatio() const;

    inline void jobDone(double val)
    {
        mWakefulness -= val;
        if(mWakefulness < 0.0)
            mWakefulness = 0.0;
    }
    inline bool decreaseJobCooldown()
    {
        if(mJobCooldown <= 0)
            return true;

        --mJobCooldown;
        return false;
    }
    void setJobCooldown(int val);
    inline int getJobCooldown() const
    { return mJobCooldown; }

    inline void foodEaten(double val)
    {
        mHunger -= val;
        if(mHunger < 0.0)
            mHunger = 0.0;
    }

    //! \brief Sets the hunger (0 = full, 100 = starving), server side
    inline void setHunger(double val)
    {
        mHunger = val;
        if(mHunger < 0.0)
            mHunger = 0.0;
        else if(mHunger > 100.0)
            mHunger = 100.0;
    }

    //! \brief Tells whether the creature can go through the given tile.
    bool canGoThroughTile(Tile* tile) const;

    virtual EntityCarryType getEntityCarryType(Creature* carrier) override;
    virtual void notifyEntityCarryOn(Creature* carrier) override;
    virtual void notifyEntityCarryOff(const Ogre::Vector3& position) override;

    //! \brief Server side. True if the creature is hurt enough to be pulled to its bed by a worker:
    //! alive, own bed in a dormitory, not standing on it, hit points below the configured share,
    //! no fight or flight going on, no hostile creature close, not in jail, not possessed, not a
    //! worker or in the hand and not on cooldown after the last time. The worker and the distance
    //! are not considered here.
    bool isWoundedForBedCarry() const;

    //! \brief Server side. True if the creature is knocked out to death and a worker may pull it to its
    //! bed: alive, own bed in a dormitory of its seat, no hostile creature close, not in jail, not
    //! possessed, not a worker or in the hand. Without an own bed it is not moved at all.
    bool isKoToDeathForBedPull() const;

    //! \brief True if the creature owns a bed (home tile) in a dormitory of its seat
    bool hasOwnBedInDormitory() const;

    //! \brief Server side. True while a worker pulls this creature over the ground
    inline bool isBeingDragged() const
    { return mIsBeingDragged; }

    //! \brief Server side. A worker starts pulling this creature by the legs: it stops what it did, stays on the
    //! map and lies on the ground (clip dragged_anim). It moves with the paths the worker gives it.
    void notifyDragStart();

    //! \brief Server side. The worker stopped pulling (arrived, gave up, the creature died or was picked up):
    //! starts the pause before it can be pulled again
    void notifyDragEnd();

    //! \brief Server side. Walks the worker to the tile with the clip of a worker that pulls somebody (drag_anim)
    //! and without queuing a walk action, so the caller keeps its turn. Returns false if there is no way.
    bool setDragDestination(Tile* tile);

    //! \brief Server side. True if a living creature of a seat that is not allied is within the radius (tiles)
    bool isHostileNear(double radius) const;

    bool canSlap(Seat* seat) override;
    void slap() override;

    void fireCreatureSound(CreatureSound sound);
    void fireCombatImpact(bool weaponClash, bool bodyDamage,
        const Ogre::Vector3& attackerPosition);
    void fireChickenFeeding(const std::string& chickenName,
        const Ogre::Vector3& chickenPosition);

    //! \brief Sends a cosmetic event to the human players that see the creature (and negotiated cosmetic events).
    //! With alliedOnly, only to the keeper of the creature and its allies. It only reports, it changes nothing.
    void fireCosmeticEvent(const CosmeticEvent& event, bool alliedOnly);
    //! \brief Sends a cosmetic event of the given kind with this creature as subject
    void fireCosmeticEvent(int32_t type, int32_t value, int32_t value2, bool alliedOnly);
    //! \brief This creature was just hit by a blow or a shot of the attacker (cosmetic event hitResult). damageDone
    //! is what takeDamage returned and rawDamage the damage before the defense; missile tells a shot from a
    //! melee blow. Only reports what the damage calculation gave, it changes nothing.
    void fireHitResult(const std::string& attackerName, double damageDone, double rawDamage, bool missile);
    //! \brief A shot of the attacker that was aimed at this creature ended without hurting it (cosmetic event hitResult)
    void fireHitMissed(const std::string& attackerName);
    //! \brief Server: this creature is about to strike at the target in the given direction and turns to it first
    //! (cosmetic event attackTurn). Only reports, it changes nothing.
    void fireAttackTurn(const std::string& targetName, const Ogre::Vector3& direction);
    //! \brief Tells the keepers who see this creature that it dodged or parried a melee blow (hitResult)
    void fireHitDefended(const std::string& attackerName, DefenceChance::Outcome outcome);
    //! \brief Server only: rolls whether this creature dodges or parries a melee blow before its damage is
    //! calculated. Only a living, not knocked out creature on the map that nobody holds or drags, and that no
    //! keeper possesses, can defend itself. Gives DefenceChance::none if MeleeDodgeParry is off.
    DefenceChance::Outcome rollMeleeDefence() const;
    //! \brief The creature found no job again: tells the keeper when it has waited as long as the game
    //! counts as frustrated (cosmetic only)
    void fireImpatientIfNeeded();
    //! \brief The creature arrived through a portal: tells the keeper what mood it would have (cosmetic only)
    void fireArrivalEvent();

    void itsPayDay();

    inline const std::vector<Tile*>& getVisibleTiles() const
    { return mVisibleTiles; }

    inline const std::vector<Tile*>& getTilesWithinSightRadius() const
    { return mTilesWithinSightRadius; }

    inline const std::vector<GameEntity*>& getVisibleEnemyObjects() const
    { return mVisibleEnemyObjects; }

    inline const std::vector<GameEntity*>& getVisibleAlliedObjects() const
    { return mVisibleAlliedObjects; }

    inline const std::vector<GameEntity*>& getReachableAlliedObjects() const
    { return mReachableAlliedObjects; }

    inline const std::vector<std::unique_ptr<CreatureAction>>& getActions() const
    { return mActions; }

    inline double getWakefulness() const
    { return mWakefulness; }

    inline void increaseWakefulness(double value)
    {
        mWakefulness += value;
        if(mWakefulness > 100.0)
            mWakefulness = 100.0;
    }

    void decreaseWakefulness(double value);

    inline double getHunger() const
    { return mHunger; }

    inline int32_t getGoldFee() const
    { return mGoldFee; }

    void decreaseGoldFee(int32_t value)
    {
        mGoldFee -= value;
        if(mGoldFee < 0)
            mGoldFee = 0;
    }

    //! \brief Gold given by the player. It pays the whole wage owed until the next pay day
    //! (clearing the pay day annoyance). Never more than the wage owed is used and there is
    //! no credit. Returns the gold that was used, the rest is left to the caller.
    int32_t receiveTreat(int32_t gold)
    {
        int32_t used = (gold < mGoldFee) ? gold : mGoldFee;
        if(used <= 0)
            return 0;

        mGoldFee = 0;
        mMoodCooldownTurns = 0;
        return used;
    }

    inline int32_t getGoldCarried() const
    { return mGoldCarried; }

    inline void resetGoldCarried()
    { mGoldCarried = 0; }

    inline void addGoldCarried(int32_t gold)
    { mGoldCarried += gold; }

    inline uint32_t getOverlayHealthValue() const
    { return mOverlayHealthValue; }

    inline uint32_t getOverlayMoodValue() const
    { return mOverlayMoodValue; }

    //! \brief Called on the client when the creature was added to or is about to be removed
    //! from the game map, updates the roster version of the creature profiles and, for a
    //! creature of the local player, adds an arrival or a leaving/death post to the feed.
    void socialCreatureAdded();
    void socialCreatureRemoved();

    //! \brief Adds a post of this category to the feed if the creature belongs to the local player.
    void socialEvent(social::PostCategory category);

    inline int32_t getNbTurnsWithoutBattle() const
    { return mNbTurnsWithoutBattle; }

    inline void setNbTurnsWithoutBattle(int32_t nbTurnsWithoutBattle)
    { mNbTurnsWithoutBattle = nbTurnsWithoutBattle; }

    //! \brief Mood points the casino gave to the creature (positive) or took from it (negative). Fades over time
    inline double getCasinoMood() const
    { return mCasinoMood; }

    //! \brief Changes the casino mood points. They are limited by the CasinoMoodMax room setting
    void addCasinoMood(double points);

    inline GameEntity* getCarriedEntity() const
    { return mCarriedEntity; }

    //! \brief Client side only: true while the carry message of the server is in effect for this creature
    inline bool getClientCarrying() const
    { return mClientCarrying; }

    inline void setClientCarrying(bool carrying)
    { mClientCarrying = carrying; }

    void carryEntity(GameEntity* carriedEntity);

    void releaseCarriedEntity();

    bool hasActionBeenTried(CreatureActionType actionType) const;

    void pushAction(std::unique_ptr<CreatureAction>&& action);
    void popAction();

    void fireCreatureRefreshIfNeeded();

    void fireChatMsgTookFee(int goldTaken);
    void fireChatMsgLeftDungeon();
    void fireChatMsgLeavingDungeon();
    void fireChatMsgBecameRogue();
    void fireChatMsgUnhappy();
    void fireChatMsgFurious();

    //! \brief Load creature definition according to @mDefinitionString
    //! This should be called before createMesh. This was formerly in CreateMesh
    //! but is now split out since this is needed on the server, while the mesh isn't.
    //! This is normally called by the constructor, but creatures loaded from the map files
    //! use a different constructor, and this is then called by the gameMap when other details have been loaded.
    void setupDefinition(GameMap& dtc, const CreatureDefinition& defaultWorkerCreatureDefinition);

    //! \brief Server side. Chooses the Dungeonbook appearance: random on the first spawn (no duplicate among
    //! the creatures of the same seat), stable from the name for loaded creatures that have none, and
    //! replaces options that no longer exist. Does nothing without catalog id or manifest.
    void assignAppearance(bool firstSpawn);

    //! \brief Server side, called from doUpkeep while the creature has no appearance. Tries again every
    //! few turns (the manifest may be available now), and sends a new appearance once to the clients
    //! that already know the creature.
    void retryAppearance();

    //! Called on server side to add an effect (spell, slap, ...) to this creature
    void addCreatureEffect(CreatureEffect* effect);

    //! Called on server side to add a finite presentation-only particle effect.
    void addParticleEffect(const std::string& effectScript, int32_t nbTurns);

    bool removeCreatureEffect(CreatureEffect* effectForDeletion);

    //! \brief Returns true (server side) if the creature is temporarily converted by the Defector spell
    bool isDefector() const;

    //! \brief Returns true if the creature is temporarily turned into a chicken by the Hexen Hen spell. On server
    //! side, it is deduced from the active effect. On client side, from the state sent by the server
    bool isHexenHen() const;

    //! \brief Returns true (server side) if the creature is paralysed by the Freeze trap. A frozen creature
    //! can neither move nor fight
    bool isFrozen() const;

    //! \brief Returns true (server side) if the creature is made invisible by the Invisible skill.
    //! Enemy creatures do not target an invisible creature
    bool isInvisible() const;

    //! \brief Name of the mesh to display (the chicken mesh while the creature is a chicken)
    const std::string& getCurrentMeshName() const;

    //! \brief Called on server side to tell that something changed that needs to be sent to the clients
    void requestRefresh()
    { mNeedFireRefresh = true; }

    //! \brief Called on client side. Replaces the displayed mesh if the chicken state changed
    void updateHexenHenMesh();

    //!\brief Returns true if the creature has an active slap effect
    bool hasSlapEffect() const
    { return mActiveSlapsCount > 0; }

    void addActiveSlapCount()
    { ++mActiveSlapsCount; }

    void removeActiveSlapCount()
    { --mActiveSlapsCount; }

    virtual void correctEntityMovePosition(Ogre::Vector2& position) override;

    //! \brief Called on client side and server side. true if the creature is hurt and false
    //! if at max HP or above
    bool isHurt() const;

    //! \brief Called on client side and server side. true if the creature is ko and false if not
    bool isKo() const;
    bool isKoDeath() const;
    bool isKoTemp() const;

    //! \brief Called on client side and server side. true if the creature is in prison and false if not
    bool isInPrison() const;

    //! Checks if the creature current walk path is still valid. This will be called if tiles passability changes (for
    //! example if a door is closed)
    void checkWalkPathValid(bool includeWalkDistortion = false);

    bool isTired() const;

    //! \brief Share of its normal speed this creature walks at because it is badly hurt (1 = not slowed).
    //! Uses the health stage that server and clients both know, so both move it at the same speed
    double getLowHealthWalkFactor() const;

    //! \brief True if a creature with this health stage counts as badly hurt for walking (the stage test of
    //! getLowHealthWalkFactor, without the factor). The client shows the clip WalkHurt for it
    static bool isLowHealthWalkStage(uint32_t healthStage);

    //! \brief True if this creature is badly hurt for walking (see isLowHealthWalkStage)
    bool isLowHealthWalking() const
    { return isLowHealthWalkStage(mOverlayHealthValue); }

    bool isHungry() const;

    void resetKoTurns();

    //! \brief Knocks the creature out so that it can be carried away (used when
    //! the last enemy standing in an arena has won its fights)
    void knockOutToDeath();

    //! \brief Knocks the creature down for the given number of turns (server side). Does nothing if dead or KO.
    void stun(int32_t nbTurns);

    //! \brief Called when the creature is set in jail by dropping or brought by
    //! a worker. if prison is nullptr, the creature is freed
    void setInJail(Room* prison);

    inline Seat* getSeatPrison() const
    { return mSeatPrison; }

    inline bool isInContainment() const
    { return (mSeatPrison != nullptr); }

    //! \brief Mood relief the creature got from praying in a temple. It fades over time
    inline int32_t getPrayerRelief() const
    { return mPrayerRelief; }

    //! \brief Adds relief from praying, up to maxRelief
    void addPrayerRelief(int32_t relief, int32_t maxRelief);

    //! \brief Mood points given by a special (positive after Make Happy, negative after Make Unhappy).
    //! They fade towards 0 over time
    inline int32_t getSpecialMood() const
    { return mSpecialMood; }

    //! \brief Make Happy special: clears the annoyance the creature has gathered
    void removeAnnoyance();

    //! \brief Make Unhappy special: pushes the creature down to the angry mood level
    void makeUnhappy();

    inline int32_t getNbTurnsTorture() const
    { return mNbTurnsTorture; }

    inline void increaseTurnsTorture()
    {
        ++mNbTurnsTorture;
        mTorturedThisTurn = true;
    }

    inline int32_t getNbTurnsPrison() const
    { return mNbTurnsPrison; }

    inline void increaseTurnsPrison()
    { ++mNbTurnsPrison; }

    virtual bool isDangerous(const Creature* creature, int distance) const override;

    virtual void clientUpkeep() override;

    virtual void exportToPacketForUpdate(ODPacket& os, Seat* seat) override;
    virtual void updateFromPacket(ODPacket& is) override;

    //! \brief Called when an angry creature wants to attack a natural enemy
    void engageAlliedNaturalEnemy(Creature& attacker);

    inline double getModifierStrength() const
    { return mModifierStrength; }

    void fight();

    void fightCreature(Creature& creature, bool ko, bool notifyPlayerIfHit);

    void flee();

    //! \brief Makes the creature run away from fearTile for nbTurns turns (fear trap)
    void fleeFromTile(Tile* fearTile, int32_t nbTurns);

    //! \brief Stuns the creature for nbTurns turns (lightning trap). A stunned creature does nothing,
    //! like a creature that was just dropped.
    void stunForTurns(int32_t nbTurns);

    void sleep();

    void leaveDungeon();

    bool isWarmup() const;

    void computeCreatureOverlayHealthValue();

    //! \brief Search within listObjects the closest attackable one.
    //! If a target is found and can be attacked, returns true and
    //! attackedEntity, attackedTile will be set to the target closest tile and positionTile will
    //! be set to the best spot.
    //! If the creature should flee (ranged units attacked by melee), true is returned, positionTile is
    //! set to the tile where it should flee and attackedEntity = nullptr and attackedTile = nullptr
    //! If tilesFilter is empty, the creature will consider moving on visible tiles. If not, it will consider
    //! moving on the given tiles only
    //! If no suitable target is found, returns false
    bool searchBestTargetInList(const std::vector<GameEntity*>& listObjects, const std::vector<Tile*>& tilesFilter, GameEntity*& attackedEntity,
        Tile*& attackedTile, Tile*& positionTile, CreatureSkillData*& creatureSkillData);

    //! \brief Called when the creature changes seat (for example when it becomes rogue or after torture)
    void changeSeat(Seat* newSeat);

    void stopWalking();

    //! \brief Server side. Moves the creature to the given tile at once, without walking, and tells the
    //! players that see it. The creature stops walking, its actions are left as they are
    void teleportTo(Tile* tile);

    //! \brief Server side. Returns the tile the creature is walking to, nullptr if it does not walk
    Tile* getWalkDestinationTile() const;

    //! \brief Server side. Takes the dead body of this creature so it cannot be used again (Raise Dead).
    //! Returns false if the creature is not a body that is still lying on the map or if it is a worker
    bool takeCorpse();
    
    void showOutliner();

    void removeOutliner();

    void maxAmbient();

    void normalizeAmbient();

    //! Called on server side. True if a player controls this creature (possession)
    inline bool isPossessed() const
    { return mPossessor != nullptr; }

    inline Player* getPossessor() const
    { return mPossessor; }

    //! Called on server side. Puts the creature under the control of the given player. Its
    //! current actions are paused and replaced by the possessed action.
    void startPossession(Player& player);

    //! Called on server side. Counts one more turn of the current possession and returns the
    //! number of turns it has lasted so far.
    inline uint32_t nextPossessionTurn()
    { return ++mPossessionTurns; }

    //! Called on server side. Gives the creature back to the AI and tells the player
    //! the possession is over.
    void endPossession();

    //! Called on server side. Makes the possessed creature walk in the given direction (world
    //! x/y, does not need to be normalized). A zero vector makes it stop.
    void possessedMove(const Ogre::Vector2& direction);

    //! Called on server side. The left mouse button attack of the possessed creature: it uses
    //! its melee or ranged attack on the enemy in front of it (aim is the view direction on
    //! the ground plane). Same range, damage and cooldown as in a normal fight.
    void possessedAttack(const Ogre::Vector2& aim);

    //! Called on server side. Uses the creature skill (other than melee and ranged attack) of
    //! the given slot (0 is the first one the creature can use). Skills that need a target
    //! use the enemy in front of the creature.
    void possessedUseSkill(uint32_t slot, const Ogre::Vector2& aim);

    //! Called on server side. True if the creature follows a possessed leader (possession group)
    inline bool isInPossessionGroup() const
    { return !mGroupLeaderName.empty(); }

    //! Called on server side. Puts the creature in the possession group of the given leader.
    //! It leaves what it was doing and follows the leader until the group is released.
    void joinPossessionGroup(const std::string& leaderName);

    //! Called on server side. The creature leaves the possession group and goes back to its
    //! normal behaviour.
    void leavePossessionGroup();

protected:
    virtual void exportToPacket(ODPacket& os, const Seat* seat) const override;
    virtual void importFromPacket(ODPacket& is) override;
    virtual void exportToStream(std::ostream& os) const override;
    virtual bool importFromStream(std::istream& is) override;

    virtual void createMeshLocal(NodeType nt = NodeType::MTILES_NODE) override;
    virtual void destroyMeshLocal(NodeType nt = NodeType::MTILES_NODE) override;
    virtual void fireAddEntity(Seat* seat,  bool async, NodeType nt) override;
    virtual void fireRemoveEntity(Seat* seat,NodeType nt = NodeType::MTILES_NODE) override;
private:
    
    enum ForceAction
    {
        forcedActionNone,
        forcedActionSearchAction,
        forcedActionDigTile,
        forcedActionClaimTile,
        forcedActionClaimWallTile
    };

    void createMeshWeapons();
    void destroyMeshWeapons();

    //! \brief Constructor for sending creatures through network. It should not be used in game.
    Creature(GameMap* gameMap);

    //! \brief Natural physical and magical attack and defense (without equipment)
    double mPhysicalDefense;
    double mMagicalDefense;
    double mElementDefense;

    //! \brief Strength modifiers (can be changed by effects like spells)
    double mModifierStrength;

    //! \brief The weapon the creature is holding in its left hand or nullptr if none. It will be set by a pointer
    //! managed by the game map and thus, should not be deleted by the creature class
    const Weapon* mWeaponL;

    //! \brief The weapon the creature is holding in its right hand or nullptr if none. It will be set by a pointer
    //! managed by the game map and thus, should not be deleted by the creature class
    const Weapon* mWeaponR;

    //! \brief The creatures home tile (where its bed is located)
    Tile *mHomeTile;

    //! Class name of the creature. The CreatureDefinition will be set from this name
    //! when the creature will be initialized
    std::string     mDefinitionString;
    //! \brief Dungeonbook appearance, see getAppearance()
    CreatureAppearance mAppearance;
    //! \brief Server side. Upkeeps left until the next try to assign a missing appearance
    uint32_t mAppearanceRetryTurns = 0;
    //! True once the appearance was checked against a valid manifest (server). A creature loaded or spawned without
    //! a manifest is checked as soon as one exists, see retryAppearance.
    bool mAppearanceValidated = false;
    //! True if no catalog id exists for this creature (the plan: no appearance). It is not looked at again until the
    //! catalog generation of the registry changes.
    bool mAppearanceNoCatalog = false;
    uint32_t mAppearanceNoCatalogGeneration = 0;
    //! \brief Pointer to the struct holding the general type of the creature with its values
    const CreatureDefinition* mDefinition;

    bool            mHasVisualDebuggingEntities;
    double          mWakefulness;
    double          mHunger;

    //! \brief The level of the creature
    unsigned int    mLevel;

    //! \brief The creature stats
    std::string     mHpString;
    double          mHp;
    double          mMaxHP;
    double          mExp;
    double          mGroundSpeed;
    double          mWaterSpeed;
    double          mLavaSpeed;

    //! \brief Workers only
    double          mDigRate;
    double          mClaimRate;

    //! \brief Counter to let the creature stay some turns after its death
    unsigned int    mDeathCounter;
    //! \brief Server side. Turns since the champion was summoned (see handleChampionUpkeep), not saved
    uint32_t        mChampionTurns;
    int             mJobCooldown;

    //! \brief At pay day, mGoldFee will be set to the creature fee and decreased when the creature gets gold
    int32_t         mGoldFee;
    //! \brief Gold carried by the creature that will be dropped if it gets killed
    int32_t         mGoldCarried;
    //! \brief Server side: the amount of carried gold the clients were last told about
    int32_t         mGoldCarriedNotified;
    //! \brief Server side. The gold carried that the clients were told last (cosmetic events only, not saved)
    int32_t         mGoldCarriedCosmeticNotified;
    //! \brief Server side. Whether the clients were told that the creature has a bed: -1 not yet, 0 no, 1 yes
    //! (cosmetic events only, not saved)
    int32_t         mBedNotified;

    //! Skill type that will be dropped when the creature dies
    SkillType       mSkillTypeDropDeath;

    //! Weapon that will be dropped when the creature dies
    std::string     mWeaponDropDeath;

    //! \brief Shows the stats page (true) or the profile page (false) of the creature card.
    void showStatsPage(bool stats);
    //! \brief Fills the profile page of the creature card.
    void refreshProfilePage();

    //! \brief True if the creature belongs to the local player and the feed is running.
    bool isSocialFeedSource() const;
    void fillSocialSnapshot(social::CreatureSnapshot& snapshot) const;

    CEGUI::Window*  mStatsWindow;
    int32_t         mNbTurnsWithoutBattle;

    //! \brief Used on server side for the mood. Set by the casino, fades by CasinoMoodDecay per second
    double          mCasinoMood;

    //! \brief Every tiles within the creature sight radius, used for common actions.
    std::vector<Tile*>              mTilesWithinSightRadius;

    //! \brief Only visible tiles, not hidden for other tiles,
    //! used for actions linked to enemies.
    std::vector<Tile*>              mVisibleTiles;

    std::vector<GameEntity*>        mVisibleEnemyObjects;
    std::vector<GameEntity*>        mVisibleAlliedObjects;
    std::vector<GameEntity*>        mReachableAlliedObjects;
    std::vector<std::unique_ptr<CreatureAction>>    mActions;
    std::vector<Tile*>              mVisualDebugEntityTiles;

    //! \brief Contains the actions that have already been tested to avoid trying several times same action
    std::vector<CreatureActionType> mActionTry;

    GameEntity*                     mCarriedEntity;

    //! \brief Client side only: the creature carries something (set by the carry and release messages)
    bool                            mClientCarrying;

    //! \brief The mood do not have to be computed at every turn. This cooldown will
    //! count how many turns the creature should wait before computing it
    int32_t                         mMoodCooldownTurns;

    //! \brief Mood value. Depending on this value, the creature will be in bad mood and
    //! might attack allied creatures or refuse to work or to go to combat
    CreatureMoodLevel               mMoodValue;
    CreatureActivity                mActivity;
    //! \brief Mood points. Computed by the creature MoodModifiers. It is promoted to class variable for debug purposes and
    //! should not be used to check mood. If the mood is to be tested, mMoodValue should be used
    int32_t                         mMoodPoints;

    //! \brief Mood points gained by praying in a temple. They fade every turn
    int32_t                         mPrayerRelief;

    //! \brief Mood points set by the Make Happy and Make Unhappy specials. They fade towards 0 every turn
    int32_t                         mSpecialMood;

    //! \brief Counts turns the creature is furious. If it stays like this for too long, it will become rogue
    int32_t                         mNbTurnFurious;

    //! \brief Represents the life value displayed on client side. We do not notify each HP change
    //! to avoid too many communication. But when mOverlayHealthValue changes, we will
    uint32_t                        mOverlayHealthValue;

    //! \brief Represents the mood of the creature. It is a bit array
    uint32_t                        mOverlayMoodValue;

    //! \brief Clients only (cosmetic): ratio between the speed of the tile the creature walks on and its ground speed,
    //! blended over a short time when the tile changes, so that the walk clips keep up with the real ground speed. Negative
    //! while no walk clip plays (the next value is taken over without blending)
    double                          mClientTileSpeedRatio;

    //! Used by the renderer to save this entity's overlay. It is its responsibility
    //! to allocate/delete this pointer
    CreatureOverlayStatus*          mOverlayStatus;

    //! Used on server side to indicate if a change that needs to be notified to the clients happened (like changing
    //! level or HP)
    bool                            mNeedFireRefresh;

    //! \brief Used on client side. When a creature is dropped, this cooldown will be set to a value > 0
    //! and decreased at each turn. Until it is > 0, the creature cannot be slapped. That's to avoid
    //! slapping creatures to death when dropping many.
    //! Note that this is done on client side and not checked on server side because it is just to be
    //! player friendly
    uint32_t                        mDropCooldown;

    //! \brief Speed modifier that will apply to both animation speed and move speed. If
    //! 1.0, it will be default speed
    double                          mSpeedModifier;

    //! \brief Counter when the creature is KO. If = 0, the creature is not KO.
    //! If > 0, the creature is temporary KO (after being drooped for example). Each
    //! turn, the counter will decrease and the creature will wake up when the counter
    //! reaches 0.
    //! If < 0, the creature is KO to death. The counter will increase each turn and
    //! if it reaches 0, the creature will die.
    //! While KO to death, a worker pulls the creature over the ground to its own bed (it stays on
    //! the map, so the counter keeps running during the way) and the counter is reset to 0 when
    //! the creature reaches its bed.
    int32_t                         mKoTurnCounter;

    //! brief Creatures that recently hurt this creature (name and turn), used to find who took part
    //! in defeating it for the relationships. Only filled when the option is on.
    std::map<std::string, int64_t>  mRecentAttackers;

    //! Names of enemy creatures that knocked this creature out (captors for a later conversion), at most
    //! MAX_CAPTORS. Only filled when the option is on.
    std::vector<std::string>        mCaptors;

    //! Name of the creature this one brawls with (relationships), empty if there is no brawl
    std::string                     mBrawlOpponent;
    int64_t                         mBrawlStartTurn = 0;
    //! Brawl restored from a saved game: the opponent and the turns it may still last. Starts as
    //! soon as both creatures can fight (see resumeBrawl), empty if there is none.
    std::string                     mBrawlResumeOpponent;
    int64_t                         mBrawlResumeTurnsLeft = 0;
    int64_t                         mBrawlResumeGiveUpTurn = 0;

    //! Combat modifier of the relationships, computed at most once per turn
    mutable int64_t                 mCombatModifierTurn = -1;
    mutable double                  mCombatModifier = 0.0;

    //! Server side. True if a friend of the same keeper that is doing action is within maxTiles tiles,
    //! measured between the home tiles (sleeping) or the positions.
    bool hasFriendDoing(CreatureActionType action, double maxTiles, bool useHomeTile) const;

    //! Mood points from relationship events that fade each turn (relationships)
    int32_t                         mRelationshipTempMood = 0;
    //! Rage after the death of a friend: until which turn it lasts and the id of the seat it is against
    int64_t                         mRageUntilTurn = 0;
    int32_t                         mRageSeatId = -1;

    //! \brief If nullptr, the creature is not in prison. If not, it is in the prison of
    //! the given seat
    Seat*                           mSeatPrison;

    //! \brief allows to know how many turns a creature has been tortured
    int32_t                         mNbTurnsTorture;

    //! \brief allows to know how many turns a creature has been in prison
    int32_t                         mNbTurnsPrison;

    //! \brief Counts the number of active slaps affecting the creature
    uint32_t                        mActiveSlapsCount;

    //! \brief Used on server side for the mood. Turns spent in the hand (decreases when not held)
    int32_t                         mNbTurnsInHand;

    //! \brief Used on server side. True while the creature is held in the hand
    bool                            mIsInHand;

    //! \brief Used on server side. True while a worker pulls the creature to its bed (not saved: actions are not saved)
    bool                            mIsBeingDragged;

    //! \brief Used on server side. No worker pulls the creature to its bed again before this turn (not saved)
    int64_t                         mWoundedCarryNextTurn;

    //! \brief Used on server side for the mood. Failed job searches (reset when the creature works)
    int32_t                         mNbTurnsOutOfWork;

    //! \brief Used on server side for the mood. Turns of torture and of rest, growing while it lasts and fading afterwards
    int32_t                         mNbTurnsTortureMood;
    int32_t                         mNbTurnsRested;
    bool                            mTorturedThisTurn;
    bool                            mRestedThisTurn;

    //! \brief Used on server side for the mood. Turns spent near a creature of the opposite alignment
    int32_t                         mNbTurnsHatedCompany;

    //! \brief Used on server side for the mood. Set by the arena, fades by PitMoodDecay per second
    double                          mPitMood;

    //! \brief Used on server side for the mood. Turn numbers of the latest slaps
    std::vector<int64_t>            mSlapTurns;

    //! \brief Used on client side. True if the server told us that the creature is a chicken
    bool                            mIsHexenHen;

    //! \brief Used on client side. True if the mesh currently displayed is the chicken one
    bool                            mHexenHenMeshShown;

    //! \brief Skills the creature can use
    std::vector<CreatureSkillData> mSkillData;

    uint32_t mAttackRecoveryTurns = 0;
    uint32_t mAttackRecoveryDuration = 0;
    uint32_t mAttackRecoverySerial = 0;
    double mExperienceProgress = 0.0;
    bool mHasProgressInformation = false;
    //! \brief Used on server side. The player controlling the creature (possession), nullptr if none
    Player*                         mPossessor = nullptr;

    //! \brief Used on server side. Turns the current possession has lasted (the first seconds are free)
    uint32_t                        mPossessionTurns = 0;

    //! \brief Used on server side. The names of the creatures following this possessed creature
    std::vector<std::string>        mGroupMemberNames;

    //! \brief Used on server side. The name of the possessed creature this creature follows, empty if none
    std::string                     mGroupLeaderName;

    //! \brief Used on server side by the possession. Picks the nearby fighting creatures of the
    //! possessor and makes them follow this creature
    void formPossessionGroup();

    //! \brief Used on server side by the possession group. Makes the creature walk to the leader if
    //! it is too far away. Returns true if the creature has to wait for the leader (nothing else to do)
    bool followPossessionLeader();

    //! \brief Used on server side by the possession. Searches the enemy in front of the creature
    //! (view direction aim) the given skill can reach. Returns true if one is found.
    bool possessedFindTarget(const Ogre::Vector2& aim, const CreatureSkillData& skillData,
        GameEntity*& entityAttack, Tile*& tileAttack);

    //! \brief A sub-function called by doTurn()
    //! This one checks if there is something prioritary to do (like fighting). If it is the case,
    //! it should empty the action list before adding what to do.
    void decidePrioritaryAction();

    //! \brief A sub-function called by doTurn()
    //! While the seat's heart defence is on, the runners (the workers and the two cheap,
    //! fast scout creatures) drop their current job and run to the seat's fighters, or to
    //! the heart while it is damaged.
    void handleHeartDefence();

    //! \brief A sub-function called by doTurn()
    //! This functions will handle the creature idle action logic.
    //! \return true when another action should handled after that one.
    bool handleIdleAction();

    //! \brief Restores the creature's stats according to its current level
    void buildStats();

    void increaseHunger(double value);

    void computeMood();

    void exportMoodToPacket(ODPacket& os, const Seat* seat) const;
    void importMoodFromPacket(ODPacket& is);
    void exportActivityToPacket(ODPacket& os, const Seat* seat) const;
    void importActivityFromPacket(ODPacket& is);
    void exportProgressToPacket(ODPacket& os, const Seat* seat) const;
    void importProgressFromPacket(ODPacket& is);

    void computeCreatureOverlayMoodValue();

    //! \brief Called on server side each turn when the creature is a chicken. It only wanders around
    void handleHexenHenUpkeep();

    //! \brief Called on server side each turn for the champion. The cast price covers the first seconds, then the owner pays
    //! the mana drain per second. Returns true if the champion left because the mana cannot pay it
    bool handleChampionUpkeep();

    //! \brief Idle action of the champion: walks to the nearest reachable enemy creature, or to the nearest enemy dungeon heart.
    //! Returns true if a destination was set
    bool handleChampionIdle();

    //! \brief Removes the champion from the map (slap, or not enough mana)
    void dismissChampion();
};

#endif // CREATURE_H
