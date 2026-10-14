/*!
 *  \file   RenderManager.h
 *  \date   26 March 2011
 *  \author oln
 *  \brief  handles the render requests
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

#ifndef RENDERMANAGER_H
#define RENDERMANAGER_H

#include <set>

#include <string>
#include <map>
#include <OgreSingleton.h>
#include <OgreMath.h>
#include <OgreSkeleton.h>
#include <OgreDefaultDebugDrawer.h>
#include <cstdint>
#include "entities/GameEntity.h"
#include "render/TreasuryCreatureRules.h"
#include "render/TreasuryGoldBatch.h"
#include "rooms/HatcheryNestField.h"
#include <OgreVector2.h>

class DraggableTileContainer;
class GameMap;
class Building;
class BuildingObject;
class ChickenEntity;
class Seat;
class Tile;
class Room;
class GameEntity;
class MovableGameEntity;
class MapLight;
class Creature;
class Player;
class RenderedMovableEntity;
class RockLava;
class Weapon;

namespace Ogre
{
class AnimationState;
class Entity;
class ManualObject;
class OverlaySystem;
class SceneManager;
class SceneNode;
class ParticleSystem;

namespace RTShader {
    class ShaderGenerator;
}
} //End namespace Ogre


//! \brief Renders entities and advances their visual poses independently of interface animation time.
class RenderManager: public Ogre::Singleton<RenderManager>, Ogre::RenderTargetListener
{
public:
    RenderManager(Ogre::OverlaySystem* overlaySystem);
    ~RenderManager();

    Ogre::Light* mHandLight;
    
    static const uint8_t OD_RENDER_QUEUE_ID_GUI;

    inline Ogre::SceneManager* getSceneManager() const
    { return mSceneManager; }

    //! \brief Node that holds the world lights (hidden while the minimap is rendered)
    inline Ogre::SceneNode* getLightSceneNode() const
    { return mLightSceneNode; }

    //! True if the last melee blow shown for the creature was struck with its left hand (only a creature with an
    //! attack weapon in each hand strikes with the left; false for every other creature and before any blow)
    bool isLastBlowLeftHanded(const Creature* creature) const;

    //! \brief True during logical sleep and its visible transition back to standing.
    bool rrIsCreatureSleeping(const Creature* creature) const;

    //! \brief Loop through the render requests in the queue and process them
    //! Advances hand animations in real time and world animations in unpaused game time.
    void updateRenderAnimations(Ogre::Real timeSinceLastFrame);

    void setPosition(Ogre::Camera* obj, const Ogre::Vector3& vec);
    
    void setOrientation(Ogre::Camera* obj, const Ogre::Quaternion& q);

    Ogre::Vector3 getPosition(Ogre::Camera* obj);

    Ogre::Quaternion getOrientation(Ogre::Camera* obj);

    // Called before a render is called to the render target
    void preRenderTargetUpdate(const Ogre::RenderTargetEvent& evt);
    void setup();
    void handleSchemeNotFound(Ogre::MaterialPtr material);
    
    //! \brief Initialize the renderer when a new game (Game or Editor) is launched
    void initGameRenderer(GameMap* gameMap);
    void stopGameRenderer(GameMap*);

    //! \brief starts the compositor compositorName.
    void triggerCompositor(const std::string& compositorName);

    //! \brief setup the scene
    void createScene(Ogre::Viewport*);

    //! \brief Sets the viewport whose camera positions the keeper hand, after the camera viewport moved to a new window
    void setViewport(Ogre::Viewport* viewport)
    { mViewport = viewport; }

    //! \brief Sets/Updates the overall world lighting value with given factor.
    void setWorldAmbientLightingFactor(float lightFactor);

    //! \brief Switches the dynamic texture shadows on or off.
    //! Updates the scene manager's shadow technique, the generated-shader shadow receiver and the
    //! shadowingEnabled constant of every loaded material that declares it.
    void setDynamicShadowsEnabled(bool enabled);

    //! \brief Set the entity's opacity
    void setEntityOpacity(Ogre::Entity* ent, float opacity);

    //! Beware this should be called on client side only (not from the server thread)
    //! moveCursor allows to move the cursor on GUI
    //!  moveWorldCoords sends the world coords where the map light is
    void moveCursor(float relX, float relY);
    //! \brief Returns the screen area covered by the hand cursor, in relative screen coordinates (0 to 1).
    //! If the hand is hidden, the area is the empty rectangle at the given cursor position.
    Ogre::FloatRect getHandCursorBounds(float relX, float relY) const;
    void moveWorldCoords(Ogre::Real x, Ogre::Real y);
    void entitySlapped();

    //! \brief The server said that the keeper owning the heart or portal room is rich (keeperWealth event): the
    //! gold dust shows over it while its tile is in view of the local keeper, tier 0 removes it
    void noteKeeperWealth(const std::string& roomName, int seatId, int tier);

    static const Ogre::Real BLENDER_UNITS_PER_OGRE_UNIT;
    static const Ogre::Real KEEPER_HAND_WORLD_Z;
    static const Ogre::Real DRAGGABLE_NODE_HEIGHT;
    
    //! Debug function to be used for dev only. Beware, it should not be called from the server thread
    static std::string consoleListAnimationsForMesh(const std::string& meshName);

    //! Functions needed to create Fog texture dynamically ( in the program run )

    void saveTexture(Ogre::TexturePtr texture, const std::string& filename);
    Ogre::TexturePtr createPerlinTexture();
    Ogre::TexturePtr createAlphaChannelForTexture(Ogre::TexturePtr m_texture);
    Ogre::TexturePtr copyTexture(Ogre::TexturePtr oldTexture);
    void setupFogMaterial(Ogre::TexturePtr myTexture);
    void cleanUp();
    
    //Render request functions
    //! \brief Refreshes earth geometry and the delayed enemy fog while keeping never-seen ground cloud-free.
    void rrRefreshTile(Tile& tile, GameMap& draggableTileContainer, const Player& localPlayer, NodeType nt = NodeType::MTILES_NODE);
    void rrCreateTile(Tile& tile, GameMap& dtc, const Player& localPlayer, NodeType nt = NodeType::MTILES_NODE);
    //! \brief Destroys tile render objects and clears its delayed fog cloud reference.
    void rrDestroyTile(Tile& tile, NodeType nt = NodeType::MTILES_NODE);
    void rrTemporalMarkTile(Tile* curTile);
    void rrDetachEntity(GameEntity* curEntity, bool really_do = true);
    void rrAttachEntity(GameEntity* curEntity);
    void rrCreateRenderedMovableEntity(RenderedMovableEntity* curRenderedMovableEntity, NodeType nt = NodeType::MTILES_NODE);
    void rrDestroyRenderedMovableEntity(RenderedMovableEntity* curRenderedMovableEntity, NodeType nt = NodeType::MTILES_NODE);
    void rrUpdateEntityOpacity(RenderedMovableEntity* entity);
    void rrCreateCreature(Creature* curCreature);
    void rrDestroyCreature(Creature* curCreature);
    //! Shows, resizes or removes the sack of a thief according to the gold it carries (as sent by the server)
    void rrRefreshCreatureGoldSack(Creature* creature);
    //! The "Treasury detail" option changed: every pile, floor gold heap and thief sack is drawn again for the new
    //! setting (the piles and heaps a few per frame, see updateTreasuryRebuild)
    void rrTreasuryDetailChanged();
    //! \brief Replaces the mesh of an already rendered creature by its current mesh (for example the chicken mesh of a
    //! creature hit by Hexen Hen), keeping the running animation if the new mesh has it.
    //! \param curCreature The creature whose mesh changed.
    void rrChangeCreatureMesh(Creature* curCreature);
    void rrOrientEntityToward(MovableGameEntity* gameEntity, const Ogre::Vector3& direction);

    //! \brief Like rrOrientEntityToward but a creature turns in a short smooth movement (clients, before a blow).
    //! Returns how many seconds the strike clip should wait for the turn (0 = start at once). With a turn that the
    //! server announced (rrNoteAttackTurn) the turn runs with the configured angular speed and the clip waits for it,
    //! but at most the configured delay; without one the turn takes a short fixed time and the clip starts at once.
    Ogre::Real rrOrientEntityTowardSmoothly(MovableGameEntity* gameEntity, const Ogre::Vector3& direction);
    //! \brief The server announced that the creature turns to a target before its next blow (event attackTurn). The
    //! announcement is used by the next blow of that creature and then forgotten.
    void rrNoteAttackTurn(const std::string& creatureName, const Ogre::Vector3& direction);
    //! \brief Takes the announced direction of the creature (and forgets it). False if none was announced.
    bool rrTakeAttackTurn(const std::string& creatureName, Ogre::Vector3& direction);
    void rrPitchAroundAxis(RenderedMovableEntity* gameEntity, Ogre::Degree dd);
    void rrScaleCreature(Creature& creature);
    //! Where a weapon model sits on a skeleton: the bone, the offset on it and the rotation of the model
    struct WeaponMount
    {
        std::string mBoneName;
        Ogre::Vector3 mOffset;
        Ogre::Quaternion mRotation;
    };
    //! Finds the bone of the given hand ("L" or "R") for a weapon mesh. Returns false if the skeleton has none.
    //! A crossbow in the right hand of a skeleton that has no Weapon_L bone (the shape of the aim pose is the
    //! one of a bow in the left hand) is mounted on the left hand bone with the offset and roll of the bow grip.
    static bool getWeaponMount(const Ogre::Skeleton* skeleton, const std::string& hand,
        const std::string& meshName, WeaponMount& mount);
    //! \brief Attaches the weapon model to the weapon bone of the creature for the given hand ("L" or "R").
    //! A weapon with the mesh name "none" is already drawn by the creature model and attaches nothing.
    void rrCreateWeapon(Creature* curCreature, const Weapon* curWeapon, const std::string& hand);
    void rrDestroyWeapon(Creature* curCreature, const Weapon* curWeapon, const std::string& hand);
    //! \brief A worker whose model has no pick of its own and no weapon in the right hand carries a pickaxe model
    void rrCreateWorkerTool(Creature* curCreature);
    void rrDestroyWorkerTool(Creature* curCreature);
    void rrCreateMapLight(MapLight* curMapLight, bool displayVisual);
    void rrDestroyMapLight(MapLight* curMapLight);
    void rrDestroyMapLightVisualIndicator(MapLight* curMapLight);
    void rrPickUpEntity(GameEntity* curEntity, Player* localPlayer);
    void rrDropHand(GameEntity* curEntity, Player* localPlayer);
    void rrRotateHand(Player* localPlayer);
    //! \brief Shows the first held creature in the hand (enabled) or leaves it with the other held
    //! entities. localPlayer may be nullptr, in which case only the flag changes.
    void rrEnableHeldCreatureDisplay(bool enabled, Player* localPlayer);
    bool isKeeperHandVisible() const { return mHandKeeperHandVisibility == 0; }
    //! \brief Where the keeper's hand is in the world (the light that follows it). False if there is no hand yet
    bool getKeeperHandPosition(Ogre::Vector3& position) const;
    void rrAddOutliner(Creature* creature);
    void rrRemoveOutliner(Creature* creature);
    void rrIncreaseAmbient(Creature* creature);
    void rrNormalizeAmbient(Creature* creature);
    void rrCreateCreatureVisualDebug(Creature* curCreature, Tile* curTile);
    void rrDestroyCreatureVisualDebug(Creature* curCreature, Tile* curTile);
    void rrCreateSeatVisionVisualDebug(int seatId, Tile* tile);
    void rrDestroySeatVisionVisualDebug(int seatId, Tile* tile);
    //! \brief Plays the given animation on the entity of an animated object; a walking carrier uses the
    //! carrying walk clip when its skeleton has one. Does nothing for entities that are missing or have no skeleton.
    //! \param loop True if the animation is repeated.
    void rrSetObjectAnimationState(MovableGameEntity* curAnimatedObject, const std::string& animation, bool loop);
    //! True when the skeleton of the entity has a clip of that name (false without skeleton or entity)
    //! (entityFound tells whether the entity is drawn, an answer for an entity that is not can change later)
    bool rrHasObjectClip(MovableGameEntity* animatedObject, const std::string& clip, bool& entityFound);
    void rrMoveEntity(GameEntity* entity, const Ogre::Vector3& position);
    //! A worker poured gold onto the treasury tile (x, y): coins fall onto the top of the pile
    void rrTreasuryDeposit(GameMap* gameMap, int x, int y);
    void rrMoveMapLightFlicker(MapLight* mapLight, const Ogre::Vector3& position);
    //! \brief Attaches the carried entity to the carrier, resting on the highest point of the carrier. A carrier
    //! that is already walking switches to the carrying walk clip.
    void rrCarryEntity(Creature* carrier, GameEntity* carried);
    //! \brief Detaches the carried entity from the carrier. A carrier that is still walking switches back
    //! to the plain walk clip.
    void rrReleaseCarriedEntity(Creature* carrier, GameEntity* carried);
    Ogre::ParticleSystem* rrEntityAddParticleEffect(GameEntity* entity, const std::string& particleName,
        const std::string& particleScript);
    void rrEntityRemoveParticleEffect(GameEntity* entity, Ogre::ParticleSystem* particleSystem);
    void rrToggleHandSelectorVisibility();
    //! Selects the hand pose; digging takes precedence over building, building over pointing.
    void rrSetHandPose(bool pointing, bool digging, bool building = false);
    //! Plays the one-shot hammer strike used when a build request is accepted.
    void rrPlayBuildAnimation();
    //! Starts a random idle hand effect; returns false if the hand is hidden, holding or busy.
    bool rrPlayIdleHandAnimation();
    //! Returns true while one of the idle hand effects is the current hand animation.
    bool rrIsIdleHandAnimationPlaying() const;
    //! Stops a running idle hand effect and returns the hand to its contextual pose.
    void rrCancelIdleHandAnimation();
    //! \brief Plays the pickaxe swing once, then returns to the current pose.
    void rrPlayDigAnimation();
    //! \brief Draws tile previews with equally thick filled borders for construction and digging.
    void rrDrawTilePreview(const std::vector<Tile*>& tiles, const Ogre::ColourValue& colour, bool construction = false, bool digging = false, bool singleRectangle = false);
    //! \brief Starts a short particle burst on each of the given tiles. The bursts remove
    //! themselves after a fixed time. Null entries are skipped.
    void rrCreateRoomConstructionEffect(const std::vector<Tile*>& tiles);

    //! \brief Creates a free-standing particle effect that stays until rrDestroyFreeParticleEffect().
    //! \param colour If not null, the colour of every emitter of the script is set to it.
    void rrCreateFreeParticleEffect(const std::string& effectName, const std::string& particleScript,
        const Ogre::Vector3& position, const Ogre::ColourValue* colour);
    void rrMoveFreeParticleEffect(const std::string& effectName, const Ogre::Vector3& position);
    void rrDestroyFreeParticleEffect(const std::string& effectName);
    //! Client-only copy of the dungeon heart for the defeat sequence (the server has already removed the
    //! real heart object), placed like the real one: critical-tier heart mesh (with the temple's pedestal) on the floor, no turn, scale 1.
    //! Its materials are clones, so that its core can glow without changing other hearts.
    void rrCreateDefeatHeart(const Ogre::Vector3& position);
    //! Moves and scales the copy; glow 0 is its normal look, 1 the hottest red
    void rrUpdateDefeatHeart(const Ogre::Vector3& position, Ogre::Real scale, Ogre::Real glow);
    void rrDestroyDefeatHeart();
    //! Creates count rubble pieces of the burst heart (a small procedural shard mesh with the heart's
    //! own shell material), one scene node each, hidden until they are first moved
    void rrCreateDefeatRubble(size_t count);
    //! Places rubble piece index; rotation holds the degrees around the x, y and z axes
    void rrMoveDefeatRubblePiece(size_t index, const Ogre::Vector3& position, const Ogre::Vector3& rotation,
        const Ogre::Vector3& scale);
    void rrDestroyDefeatRubble();
    void rrCreateCreatureCombatImpact(Creature* creature, bool weaponClash,
        bool bodyDamage, const Ogre::Vector3& attackerPosition);
    //! \brief Attaches the chicken that a creature starts to eat to its feeding animation.
    void rrSetFeedingChicken(Creature* creature, MovableGameEntity* chicken,
        const Ogre::Vector3& position);

    //! \brief Hatchery animals: scale, tint and procedural motion by kind and pose
    void rrCreateChickenLook(ChickenEntity* chicken);
    //! \brief Gives the entity back to the node of the animal and removes the look (accessories, fight links).
    void rrDestroyChickenLook(ChickenEntity* chicken);
    //! \brief The kind of the animal changed (chick grown up): new scale and tint.
    void rrUpdateChickenLook(ChickenEntity* chicken);
    //! \brief The egg hatched: shell pieces fly.
    void rrChickenHatched(ChickenEntity* chicken);
    //! \brief An egg was trampled at the position: shell pieces and yolk fly, a few feathers of a startled hen.
    void rrEggTrampled(const Ogre::Vector3& position);
    //! The server-selected rooster/hen pair of the mounting pose.
    void rrChickenMount(ChickenEntity* rooster, ChickenEntity* hen);
    //! \brief Two roosters fight (phase as in ServerNotificationType::chickenFight): while they brawl, feather
    //! clouds fly between them at the configured interval, when it is over a last cloud flies.
    void rrChickenFight(ChickenEntity* first, ChickenEntity* second, uint32_t phase);
    //! \brief The server sent the nest places and the places of the loose feathers of a hatchery (by room name); the
    //! nests are drawn at the places, the feathers show while the hatchery is empty.
    void rrSetHatcheryNests(const std::string& roomName, const std::vector<HatcheryNestField::Place>& places,
        const std::vector<HatcheryNestField::Place>& feathers);
    //! \brief The server set a pose (see ChickenPose.h), an empty pose is the normal walking and idling.
    void rrSetChickenPose(ChickenEntity* chicken, const std::string& pose);
    //! \brief Decor of a coop of the hatchery (the straw nests and the loose feathers lie scattered over the hatchery, see updateNestFields)
    void rrCreateCoopDecor(BuildingObject* coop);
    //! \brief Removes the nest and the feathers next to the coop.
    void rrDestroyCoopDecor(BuildingObject* coop);
    //! \brief Makes the procedural meshes of the hatchery (egg in straw, comb, tail, feathers) if needed
    void rrEnsureChickenMesh(const std::string& meshName);

    //! \brief Toggles the creatures text overlay
    void rrSetCreaturesTextOverlay(GameMap& gameMap, bool value);

    //! \brief Toggles the creatures text overlay
    void rrTemporaryDisplayCreaturesTextOverlay(Creature* creature, Ogre::Real timeToDisplay);

    //! \brief Returns the name of a copy of the given material that is tinted with the given colour.
    //! The copy is created on the first request and reused afterwards.
    std::string rrBuildTintedMaterial(const std::string& materialNameBase,
        const Ogre::ColourValue& color);

    //! \brief Does requested stuff for rendering in the minimap. Each time the minimap is rendered, this function will be
    //! called once before rendering is done with postRender = false and once when it is rendered with postRender = true.
    //! That allows to hide stuff that we don't want to display in the minimap
    void rrMinimapRendering(bool postRender, bool keepWorldLighting = false);

    Ogre::Light* addPointLightMenu(const std::string& name, const Ogre::Vector3& pos,
        const Ogre::ColourValue& diffuse, const Ogre::ColourValue& specular, Ogre::Real attenuationRange,
        Ogre::Real attenuationConstant, Ogre::Real attenuationLinear, Ogre::Real attenuationQuadratic);
    void removePointLightMenu(Ogre::Light* light);
    Ogre::Entity* addEntityMenu(const std::string& meshName, const std::string& entityName,
        const Ogre::Vector3& pos);
    void removeEntityMenu(Ogre::Entity* ent);
    Ogre::AnimationState* setMenuEntityAnimation(const std::string& entityName, const std::string& animation, bool loop);
    //! \brief Called to update the given animation with the given time. Returns true if animation ended and
    //! false otherwise
    bool updateMenuEntityAnimation(Ogre::AnimationState* animState, Ogre::Real timeSinceLastFrame);
    //! \brief Returns the scene node related to the given entity name
    Ogre::SceneNode* getMenuEntityNode(const std::string& entityName);
    const Ogre::Vector3& getMenuEntityPosition(Ogre::SceneNode* node);
    void updateMenuEntityPosition(Ogre::SceneNode* node, const Ogre::Vector3& pos);
    void orientMenuEntityPosition(Ogre::SceneNode* node, const Ogre::Vector3& direction);
    Ogre::ParticleSystem* addEntityParticleEffectMenu(Ogre::SceneNode* node,
        const std::string& particleName, const std::string& particleScript);
    void removeEntityParticleEffectMenu(Ogre::SceneNode* node,
        Ogre::ParticleSystem* particleSystem);
    Ogre::ParticleSystem* addEntityParticleEffectBoneMenu(const std::string& entityName,
        const std::string& boneName, const std::string& particleName, const std::string& particleScript);
    void removeEntityParticleEffectBoneMenu(const std::string& entityName,
        Ogre::ParticleSystem* particleSystem);
    Ogre::Quaternion getNodeOrientation(Ogre::SceneNode* node);
    Ogre::Viewport* getViewport(){return mViewport;}
    void setProgressiveNodeOrientation(Ogre::SceneNode* node, Ogre::Real progress,
        const Ogre::Quaternion& angleSrc, const Ogre::Quaternion& angleDest);
    void setScaleMenuEntity(Ogre::SceneNode* node, const Ogre::Vector3& absSize);
    const Ogre::Vector3& getMenuEntityScale(Ogre::SceneNode* node);

    Ogre::RenderTarget* mRenderTarget;
    bool m_ZPrePassEnabled;
    
private:
    Ogre::InstanceManager* mInstanceManagerDirt;
    Ogre::InstanceManager* mInstanceManagerMarkedFog;
    Ogre::InstanceManager* mInstanceManagerCloud;
        
    Ogre::DefaultDebugDrawer ddd;

    // Ogre::TexturePtr perlinFog;
    
    //! \brief Correctly places entities in hand next to the keeper hand
    void changeRenderQueueRecursive(Ogre::SceneNode* node, uint8_t renderQueueId);


    template<typename Manager> bool removeIfExists(std::string, std::string);
    //! \brief Correctly places entities in hand next to the keeper hand
    void rrOrderHand(Player* localPlayer);
    //! \brief Places the held creature in the grip of the hand.
    void rrUpdateHeldCreature();

    //! \brief Colorize the material with the corresponding team id color.
    //! \note If the material (wall tiles only) is marked for digging, a yellow color is added
    //! to the given color. Tiles that were discovered but are out of sight are not darkened.
    //! \returns The new material name according to the current colorization.
    std::string colourizeMaterial(const std::string& materialName, const Seat* seat, bool markedForDigging, bool playerHasVision);

    //! \brief Colorize an entity with the team corresponding color.
    //! \Note: if the entity is marked for digging (wall tiles only), then a yellow color
    //! is added to the current colorization.
    void colourizeEntity(Ogre::Entity* ent, const Seat* seat, bool markedForDigging, bool playerHasVision);

    //! \brief Maintain local illumination for the visible room tiles around a tile.
    //! \param removing true when the tile is being destroyed and must not count as a lit room tile.
    void rrRefreshRoomLight(const Tile& tile, bool removing = false);

    //! \brief Makes the material be transparent with the given opacity (0.0f - 1.0f)
    //! \returns The new material name according to the current opacity.
    std::string setMaterialOpacity(const std::string& materialName, float opacity);

    //! \brief Disables all animations of the given entity and starts the given one
    Ogre::AnimationState* setEntityAnimation(Ogre::Entity* ent, const std::string& animation, bool loop);

    //! \brief The main scene manager reference. Don't delete it.
    Ogre::SceneManager* mSceneManager;

    //! \brief Reference to the Ogre sub scene nodes. Don't delete them.
    Ogre::SceneNode* mDraggableSceneNode;
    Ogre::SceneNode* mTileSceneNode;
    Ogre::SceneNode* mRoomSceneNode;
    Ogre::SceneNode* mCreatureSceneNode;
    Ogre::SceneNode* mLightSceneNode;
    Ogre::SceneNode* mMainMenuSceneNode;

    Ogre::AnimationState* mHandAnimationState;
    //! \brief Animation of the hand that is wanted: Idle, Point, Dig or Hold.
    std::string mHandPose = "Idle";
    //! \brief Pickaxe attached to the hand while digging.
    Ogre::ManualObject* mHandPickaxe = nullptr;
    //! Hammer shown in the hand while building; hidden otherwise.
    Ogre::Entity* mHandHammer = nullptr;
    //! Dynamic prop (watch or yo-yo) drawn on the hand during an idle hand effect.
    Ogre::ManualObject* mHandIdleProp = nullptr;
    //! Centre of the hammer's striking face in mesh space; the hand is aligned so it sits on the pointer.
    Ogre::Vector3 mHammerStrikePoint = Ogre::Vector3::ZERO;
    //! \brief Outline of the tiles the current action would affect.
    Ogre::ManualObject* mTilePreview = nullptr;

    //! \brief Short particle effect shown at a creature that was hit.
    struct CreatureCombatImpactEffect
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::ParticleSystem* mParticleSystem;
        //! Seconds until the effect is destroyed.
        Ogre::Real mRemainingTime;
    };
    std::vector<CreatureCombatImpactEffect> mCreatureCombatImpactEffects;

    //! \brief Running hit reaction of a creature; it is played on top of the current animation.
    struct CreatureCombatReaction
    {
        Creature* mCreature;
        Ogre::Entity* mEntity;
        Ogre::AnimationState* mAnimation;
        //! Blend mode of the skeleton to restore when the reaction ends.
        Ogre::SkeletonAnimationBlendMode mPreviousBlendMode;
    };
    std::vector<CreatureCombatReaction> mCreatureCombatReactions;
    //! Counter that makes the names of the combat impact scene objects unique.
    uint64_t mCreatureCombatEffectNumber = 0;
    //! Index of the next attack variant to play, per creature, so that attacks alternate.
    std::map<Creature*, uint32_t> mCreatureAttackVariants;
    //! Blows struck by a creature with a weapon in each hand, to alternate left and right (client side only)
    std::map<Creature*, uint32_t> mCreatureAttackSides;
    //! The side of the blow shown last per creature (true: left hand), for the weapon trail
    std::map<const Creature*, bool> mCreatureLastBlowLeft;

    //! A smooth turn of a creature towards its target before a blow (cosmetic, ends by itself)
    struct CreatureTurn
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::Quaternion mFrom;
        Ogre::Quaternion mTo;
        Ogre::Quaternion mLast;
        Ogre::Real mElapsed;
        Ogre::Real mDuration;
    };
    std::vector<CreatureTurn> mCreatureTurns;
    //! Turns announced by the server (event attackTurn): creature name -> direction to the target
    std::map<std::string, Ogre::Vector3> mAttackTurnNotes;
    void updateCreatureTurns(Ogre::Real timeSinceLastFrame);

    //! A small body variant of a death (falls back, sinks aside) laid over the Die clip on the creature node
    //! (cosmetic, chosen from the creature name, ends by itself and leaves the final pose)
    struct CreatureDeathVariant
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::Quaternion mBaseOrientation;
        Ogre::Vector3 mBasePosition;
        Ogre::Quaternion mLastOrientation;
        Ogre::Vector3 mLastPosition;
        int mVariant;
        Ogre::Real mElapsed;
        Ogre::Real mDuration;
    };
    std::vector<CreatureDeathVariant> mCreatureDeathVariants;
    void updateCreatureDeathVariants(Ogre::Real timeSinceLastFrame);
    void startCreatureDeathVariant(Creature* creature, Ogre::Entity* entity);

    //! \brief How a creature eats a chicken; chosen from its mesh and selects the generated movement.
    enum class CreatureFeedingStyle
    {
        peck,
        lunge,
        heavy,
        humanoid,
        magical,
        coil
    };

    //! \brief Rest pose of a bone that is moved by hand while a creature reaches for the chicken.
    struct CreatureFeedingBone
    {
        Ogre::Bone* mBone;
        Ogre::Vector3 mPosition;
        Ogre::Quaternion mOrientation;
        //! Whether the bone was manually controlled before the feeding, to restore it afterwards.
        bool mWasManual;
        //! Bone whose movement this bone copies (second rig of a mesh), or null.
        Ogre::Bone* mDriver = nullptr;
        Ogre::Vector3 mScale = Ogre::Vector3::UNIT_SCALE;
    };
    //! \brief Arm or leg of a creature that reaches for the chicken with its hands.
    struct CreatureFeedingLimb
    {
        Ogre::Bone* mUpper;
        Ogre::Bone* mLower;
        //! Hand or foot.
        Ogre::Bone* mTip;
        //! Point that has to reach the target, in the space of the lower bone.
        Ogre::Vector3 mTipOffset;
        //! World position of that point before the feeding.
        Ogre::Vector3 mRestTip;
        //! Offset from the tip bone to where the chicken is grasped, in the space of the tip bone.
        Ogre::Vector3 mGripOffset = Ogre::Vector3::ZERO;
    };
    //! \brief State of a creature that is eating a chicken.
    struct CreatureFeedingAnimation
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        Ogre::Vector3 mBasePosition;
        Ogre::Quaternion mBaseOrientation;
        Ogre::Vector3 mBaseScale;
        //! Seconds since the feeding started.
        Ogre::Real mElapsed;
        CreatureFeedingStyle mStyle;
        Ogre::AnimationState* mAnimation;
        Ogre::SceneNode* mChickenNode;
        Ogre::Entity* mChickenEntity;
        Ogre::Vector3 mChickenStart;
        Ogre::Vector3 mChickenScale;
        //! Bone that carries the mouth, or null.
        Ogre::Bone* mHead;
        //! Number of feather bursts shown so far.
        unsigned int mFeatherBursts;
        std::vector<CreatureFeedingBone> mReachBones;
        std::vector<Ogre::Bone*> mRoots;
        Ogre::Bone* mSpine = nullptr;
        CreatureFeedingLimb mArms[2] = {};
        CreatureFeedingLimb mLegs[2] = {};
        //! The eaten animal is a rooster: its feathers have the colours of the rooster
        bool mRoosterFeathers = false;
        Ogre::Bone* mJaw = nullptr;
        Ogre::Real mMouthForward = 0.0f;
        Ogre::Quaternion mChickenOrientation = Ogre::Quaternion::IDENTITY;
    };
    std::vector<CreatureFeedingAnimation> mCreatureFeedingAnimations;

    //! \brief Short feather particle effect shown while a chicken is eaten.
    struct ChickenFeatherEffect
    {
        Ogre::SceneNode* mNode;
        Ogre::ParticleSystem* mParticleSystem;
        Ogre::Real mRemainingTime;
    };
    std::vector<ChickenFeatherEffect> mChickenFeatherEffects;
    //! Counter that makes the names of the feeding scene objects unique.
    uint64_t mChickenFeatherEffectNumber = 0;

    //! \brief Per animal state of the look: the child node that carries scale and motion, the pose and its timers,
    //! the rooster accessories and the fight link.
    struct ChickenLook
    {
        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        std::vector<Ogre::Entity*> mAccessories;
        std::string mPose;
        Ogre::Real mTime;
        Ogre::Real mPoseTime;
        Ogre::Real mPhase;
        int mFeatherBursts;
        //! The feathers of the coop exit are still to fly (they fly when the animal walks through the door)
        bool mEmergeFeathersPending;
        //! The door of the coop still has to swing again when the animal reaches it
        bool mCoopDoorReplayPending;
        //! The animal walks out of the coop (the flags above end when it stops)
        bool mCoopExitWalking;
        //! The rooster this one fights (set by the server event), the first of the two makes the feather clouds
        ChickenEntity* mFightPartner;
        bool mFightLeader;
        Ogre::Real mFightTimer;
        //! The hen the rooster climbs on while he mounts (set when the pose starts, null when none is near)
        ChickenEntity* mMountPartner;
        //! How far the hen is ducked down under the rooster (0 to 1), set by the rooster every frame
        Ogre::Real mMountCrouch;
        //! The clip phase of the rooster while he mounts: 1 climbing on, 2 treading, 3 climbing down (0 when not mounting)
        int mMountPhase;
        //! The egg lies in a nest: its own straw is hidden, the nest has straw
        bool mNestEgg;
    };
    std::map<ChickenEntity*, ChickenLook> mChickenLooks;

    //! \brief Nest and loose feathers next to a coop, with the timer of the door shake.
    struct CoopDecor
    {
        Ogre::SceneNode* mNode;
        Ogre::Real mShake;
        //! The door clip of the coop mesh, null for the old coop mesh (the coop shakes then)
        Ogre::AnimationState* mDoor;
    };
    std::map<BuildingObject*, CoopDecor> mCoopDecors;
    //! The nest places the server sent, by room name (the clients compute nothing). mVersion counts the messages.
    struct ServerNests
    {
        ServerNests() :
            mVersion(0)
        {}

        std::vector<HatcheryNestField::Place> mPlaces;
        std::vector<HatcheryNestField::Place> mFeathers;
        uint32_t mVersion;
    };
    std::map<std::string, ServerNests> mServerNests;
    //! The straw nests of one hatchery (one entity each, at the places the server sent). mKey is the version of
    //! the places they were made for.
    struct NestField
    {
        std::vector<Ogre::SceneNode*> mNodes;
        std::vector<Ogre::Entity*> mEntities;
        //! The loose feathers (shown while the hatchery is empty), at the places the server sent
        std::vector<Ogre::SceneNode*> mFeatherNodes;
        std::vector<Ogre::Entity*> mFeatherEntities;
        uint32_t mKey;
    };
    std::map<std::string, NestField> mNestFields;
    //! Draws server-provided nests by room name; clients have no Room objects. Nests remain visible
    //! on visible hatchery floor tiles regardless of animals or coop presence.
    void updateNestFields();
    void destroyNestField(NestField& field);
    Ogre::Real mCoopDecorTimer = 0.0f;
    uint64_t mChickenLookNumber = 0;

    //! \brief Keeps bed alignment and reversible sleep-entry/wake pose state for one creature.
    struct CreatureSleepAnimation
    {
        Creature* mCreature;
        Ogre::Entity* mEntity;
        Ogre::SceneNode* mNode;
        Ogre::Vector3 mBaseScale;
        Ogre::AnimationState* mAnimation;
        //! Seconds since the creature started to lie down.
        Ogre::Real mElapsed;
        //! True if the mesh has its own sleep entry animation, false if one is generated.
        bool mNativeEntry;
        //! Position and orientation of the node before sleeping and when lying in the bed.
        Ogre::Vector3 mBasePosition, mRestPosition;
        Ogre::Quaternion mBaseOrientation, mRestOrientation;
        //! Waking reverses the entry unless the model supplies its own Sleep_End clip.
        bool mWaking;
        bool mReverseWake;
        //! Entry-clip time at interruption, so waking never jumps to a fully settled pose first.
        Ogre::Real mWakeStartTime;
        //! Breathing scale at the start of waking, blended back to the standing scale.
        Ogre::Vector3 mWakeScale;
        //! Frozen sleep pose used briefly while entering a different native wake clip.
        Ogre::AnimationState* mWakeFromAnimation;
    };
    std::vector<CreatureSleepAnimation> mCreatureSleepAnimations;
    //! Creatures that are currently lifted onto low furniture.
    std::set<Creature*> mSteppingCreatures;

    //! The kinds of treasury effect; each has a budget per room of its own
    enum class TreasuryEffectKind
    {
        splash,
        dust,
        ambient
    };
    struct TreasuryEffect
    {
        std::string mName;
        Ogre::Real mRemaining;
        const void* mRoomKey;
        TreasuryEffectKind mKind;
    };
    std::vector<TreasuryEffect> mTreasuryEffects;
    TreasuryCreatureRules::SplashBudget mTreasurySplashBudget;
    //! Gold dust puffs over full treasuries use the same effect list with a budget of their own
    TreasuryCreatureRules::SplashBudget mTreasuryDustBudget;
    //! Sparkles, sliding coins and rolling coins on rich piles, also with a budget of their own
    TreasuryCreatureRules::SplashBudget mTreasuryAmbientBudget;
    Ogre::Real mTreasuryDustTimer = 0.0f;
    size_t mTreasuryDustCursor = 0;
    size_t mTreasuryPortalDustCursor = 0;
    //! Rich keepers other than the local one: name of the heart or portal room -> seconds the news of the server
    //! still counts. The server only tells the seats that see the tile, so this holds nothing about hidden buildings.
    std::map<std::string, Ogre::Real> mForeignWealth;
    //! Set while a game is shown; the portal dust looks up the portals of the local keeper there and the sacks of the
    //! thieves look up the creatures of the game there
    GameMap* mGameMap = nullptr;
    Ogre::Real mTreasuryAmbientTimer = 0.0f;
    size_t mTreasuryAmbientCursor = 0;

    //! The gold piles of this client (also the classic stacks that are drawn as piles) with the node type they were
    //! created for and whether they use the reduced mesh because they are far from the camera. The level of detail
    //! switches piles by creating their mesh again; the option change does the same for all of them.
    struct TreasuryPileInfo
    {
        NodeType mNodeType;
        bool mFar;
    };
    std::map<RenderedMovableEntity*, TreasuryPileInfo> mTreasuryPiles;
    //! While a pile is created again for the level of detail: 1 reduced, 0 full (-1 when not, the distance decides)
    int mTreasuryPileFarOverride = -1;
    //! Piles (true) and floor gold heaps (false) waiting to be drawn again after the detail option changed
    std::vector<std::pair<RenderedMovableEntity*, bool> > mTreasuryRebuildQueue;
    size_t mTreasuryRebuildIndex = 0;
    Ogre::Real mTreasuryLodTimer = 0.0f;

    //! A pile that grows or sinks: its node settles to the new height over a short time
    struct TreasuryPileSettle
    {
        std::string mEntityName;
        Ogre::SceneNode* mNode;
        Ogre::Real mElapsed;
        float mFrom;
        bool mTaken;
        //! True when the taken pile does not dip as a whole but shows a local dent (see TreasuryPileDent)
        bool mLocalDent;
    };
    std::vector<TreasuryPileSettle> mTreasuryPileSettles;
    //! The dent where gold was taken: while it lasts a dynamic copy of the pile is drawn in place of its entity
    //! (the entity is detached from its node and does not take part in the room batch), and given back afterwards
    struct TreasuryPileDent
    {
        std::string mEntityName;
        std::string mOgreName;
        Ogre::SceneNode* mNode;
        Ogre::Entity* mEntity;
        Ogre::ManualObject* mObject;
        std::string mMeshName;
        float mU;
        float mV;
        Ogre::Real mElapsed;
    };
    std::vector<TreasuryPileDent> mTreasuryPileDents;
    int mTreasuryDentNumber = 0;
    //! The settled piles of a treasury are drawn as one batch per room
    TreasuryGoldBatch mTreasuryBatch;

    //! An object standing in the gold of a treasury, drawn partly buried: only its node is lifted by mCurrent
    struct TreasuryBuriedObject
    {
        float mHeight;
        float mCurrent;
        float mTarget;
    };
    std::map<RenderedMovableEntity*, TreasuryBuriedObject> mTreasuryBuriedObjects;

    //! A thief carrying gold shows a sack of coins, its size follows the amount the server sends
    struct TreasuryThiefSack
    {
        Creature* mCreature;
        std::string mSackName;
        std::string mSackMesh;
    };
    std::vector<TreasuryThiefSack> mTreasuryThiefSacks;

    //! Names of the warm lights over rich treasuries (one per patch of tiles) that have a light at the moment
    std::set<std::string> mTreasuryGlowLights;
    //! Every patch of tiles with glow, by light name; only the ones near the camera and within the limits of
    //! their room and of the game get a light (see applyTreasuryGlowLights)
    struct TreasuryGlowPatch
    {
        float mStrength;
        float mX;
        float mY;
        const void* mRoom;
    };
    std::map<std::string, TreasuryGlowPatch> mTreasuryGlowPatches;
    bool mTreasuryGlowDirty = false;
    Ogre::Real mTreasuryGlowTimer = 0.0f;
    //! Where a creature last splashed coins, to space the splashes along its way
    std::map<Creature*, Ogre::Vector2> mTreasuryLastSplash;
    int mTreasuryEffectNumber = 0;

    //! A worker pouring its gold out on top of a pile (procedural climb and tilt of the render node)
    struct TreasuryPour
    {
        Creature* mCreature;
        Ogre::Real mElapsed;
        int mLevel;
        float mRise;
        Ogre::Quaternion mTilt;
        //! Skeleton clips of the worker (climb and pour); null when the mesh has none (procedural motion)
        Ogre::Entity* mEntity;
        Ogre::AnimationState* mClip;
        int mPhase;
    };
    std::vector<TreasuryPour> mTreasuryPours;

    //! \brief A creature falling from the hand to the ground. When the drop animation is
    //! requested for the creature, it lies down at the end (by its own animation, or by
    //! rotating the node to mLieOrientation at mLiePosition if mUseFallbackLie is set).
    struct CreatureDropAnimation
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::Vector3 mStart;
        Ogre::Vector3 mEnd;
        Ogre::Quaternion mStartOrientation;
        Ogre::Quaternion mLieOrientation;
        Ogre::Vector3 mLiePosition;
        Ogre::Real mElapsed;
        bool mLieOnGround;
        bool mUseFallbackLie;
    };
    //! Drops that are currently falling, updated every frame.
    std::vector<CreatureDropAnimation> mCreatureDropAnimations;

    //! \brief The standing orientation and height of a creature that was rotated to lie
    //! on the ground, kept to restore it when it gets up or is picked up.
    struct CreatureGroundPose
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::Quaternion mStandingOrientation;
        Ogre::Real mStandingZ;
    };
    //! Creatures that currently lie on the ground by a rotated node.
    std::vector<CreatureGroundPose> mCreatureGroundPoses;

    //! \brief A creature getting up after a drop. It either plays its "Die" animation
    //! backwards (mAnimationState) or, if mUseFallback is set, blends the node back to
    //! the end orientation and position.
    struct CreatureGetUpAnimation
    {
        Creature* mCreature;
        Ogre::SceneNode* mNode;
        Ogre::AnimationState* mAnimationState;
        Ogre::Quaternion mStartOrientation;
        Ogre::Quaternion mEndOrientation;
        Ogre::Vector3 mStartPosition;
        Ogre::Vector3 mEndPosition;
        Ogre::Real mElapsed;
        bool mUseFallback;
    };
    //! Creatures that are currently getting up, updated every frame.
    std::vector<CreatureGetUpAnimation> mCreatureGetUpAnimations;

    //! \brief Stops the drop and get-up animations of the creature and puts it back in
    //! its standing pose.
    void cancelCreatureDropAnimation(Creature* creature);
    //! \brief Stops the get-up animation of the creature and moves it to its final pose.
    void cancelCreatureGetUpAnimation(Creature* creature);
    //! \brief Starts the get-up animation of a creature that lies on the ground.
    void startCreatureGetUpAnimation(Creature* creature);
    //! \brief Restores the standing pose of a creature that was rotated to lie down.
    void restoreCreatureGroundPose(Creature* creature);
    //! \brief Plays the animation the creature shows while it lies on the ground.
    void setCreatureDropGroundAnimation(Creature* creature);
    //! \brief One running room construction burst: the scene node and particle system
    //! created for a tile, and the time left until they are destroyed.
    struct RoomConstructionEffect
    {
        std::string mNodeName;
        std::string mParticleName;
        Ogre::Real mRemainingTime;
    };
    //! Bursts that are currently running, updated every frame.
    std::vector<RoomConstructionEffect> mRoomConstructionEffects;
    //! Counter that makes the scene node and particle system names of each burst unique.
    uint64_t mRoomConstructionEffectNumber = 0;

    //! \brief Destroys the combat effects and reactions of the given creature, or of all creatures if null.
    void clearCreatureCombatEffects(Creature* creature = nullptr);
    //! \brief Starts the feeding animation; the chicken is added later by rrSetFeedingChicken().
    void startCreatureFeedingAnimation(Creature* creature, Ogre::Entity* entity);
    //! \brief Finds the arms, legs and spine of the creature and takes over their bones; creatures
    //! without a complete rig keep the plain feeding animation.
    void prepareCreatureFeedingReach(CreatureFeedingAnimation& feeding);
    //! \brief Poses the body of the feeding creature for one frame of the meal.
    //! \param progress Progress of the whole meal from 0 to 1.
    //! \param reach How far the arms reach for the chicken (0 to 1).
    //! \param lift How far the chicken is lifted from the ground to the hold position (0 to 1); the crouch shrinks with it.
    //! \param release How far the hands let go of the chicken (0 to 1).
    //! \param dip How far the head dips towards the chicken during a bite (0 to 1).
    //! \param biteLean Extra forward lean of the spine in degrees during a bite.
    //! \return The middle between the two hands where the chicken is gripped.
    Ogre::Vector3 updateCreatureFeedingReach(CreatureFeedingAnimation& feeding, Ogre::Real progress,
        Ogre::Real reach, Ogre::Real lift, Ogre::Real release, Ogre::Real dip, Ogre::Real biteLean);
    //! \brief Gets the position of the mouth of the feeding creature in the space of its node.
    //! \param height Height of the creature mesh.
    //! \param chickenHeight Height of the chicken, used to keep the chicken in front of the jaws.
    //! \param withoutHands True when the chicken is taken into the mouth instead of held in the hands.
    Ogre::Vector3 getCreatureFeedingMouth(const CreatureFeedingAnimation& feeding, Ogre::Real height,
        Ogre::Real chickenHeight, bool withoutHands) const;
    void cancelCreatureFeedingAnimation(Creature* creature = nullptr);
    //! \brief Starts a short feather (or egg shell) particle effect at the position.
    //! \param position World position of the effect.
    //! \param particleName Name of the particle template to use.
    void createChickenFeatherEffect(const Ogre::Vector3& position, const std::string& particleName = "ChickenFeathers");
    //! True when the animal is in the scene, in the view of the camera and plays the clip (feathers only fly for that).
    bool chickenClipVisible(ChickenEntity* chicken, const std::string& clip) const;
    //! \brief Moves every animal look (pose motion, fight clouds) and the coop decor for the elapsed time.
    //! \param timeSinceLastFrame Seconds since the last frame.
    void updateChickenLooks(Ogre::Real timeSinceLastFrame);
    //! \brief Sets scale, tint and rooster accessories of the animal for its current kind.
    void applyChickenKindLook(ChickenEntity* chicken);
    //! \brief Forgets all animal looks and coop decors without touching the scene.
    void clearChickenLooks();
    void clearChickenFeatherEffects();
    //! \brief Starts an authored or generated sleep-entry pose and stores its standing transform.
    void startCreatureSleepAnimation(Creature* creature, Ogre::Entity* entity);
    //! \brief Starts a cosmetic wake transition only when this creature has a stored sleep pose.
    bool startCreatureWakeAnimation(Creature* creature, Ogre::Entity* entity);
    //! \brief Finds the nearest bed and computes where the creature has to lie on it.
    void fitCreatureToBed(CreatureSleepAnimation& sleeping);
    //! \brief Restores the standing transform and removes any retained native wake blend.
    void cancelCreatureSleepAnimation(Creature* creature = nullptr);
    //! \brief Lifts the creature while it walks over low furniture, such as a nest, and lowers it again
    //! afterwards.
    void updateCreatureStep(Creature* creature);
    //! \brief The creatures on the tile follow the gold of its pile (a pile was created or removed there).
    void refreshCreaturesOnTile(Tile* tile);
    //! \brief A creature walked on deep gold: splashes coins and clinks after every step of the given length.
    void treasuryCreatureStep(Creature* creature, const Ogre::Vector3& position, float surfaceHeight, int level);
    //! \brief Starts an effect of the given kind at the position, when it is in view and its room still has a place
    //! in the budget of the kind. Returns whether the effect was started.
    bool createTreasuryEffect(const void* roomKey, const std::string& script, const Ogre::Vector3& position,
        TreasuryEffectKind kind = TreasuryEffectKind::splash);
    //! \brief Now and then starts gold dust over a full pile in view, over the portals and over the heart of the
    //! local keeper when it is rich.
    void updateTreasuryDust(Ogre::Real timeSinceLastFrame);
    //! \brief Starts a puff of gold dust over a portal of the local keeper when the keeper is rich.
    void startTreasuryPortalDust();
    //! \brief Starts a puff of gold dust over the dungeon heart of the local keeper when the keeper is rich.
    void startTreasuryHeartDust();
    void startForeignWealthDust();
    //! \brief Now and then starts sliding coins or a sparkle on a rich pile in view.
    void updateTreasuryAmbient(Ogre::Real timeSinceLastFrame);
    //! \brief A pile of a tile was created with another level than before: it settles to its new height, and a taken
    //! pile gets a dent and throws coins.
    void startTreasuryPileChange(Ogre::SceneNode* node, const std::string& entityName, Tile* tile, int oldLevel,
        int newLevel, Ogre::Entity* entity, const std::string& pileMeshName);
    //! \brief Lets the local dents of the piles that lose gold form and fill up again.
    void updateTreasuryDents(Ogre::Real timeSinceLastFrame);
    //! Distance of a point to the camera in tiles (0 without a camera)
    float getTreasuryCameraDistance(const Ogre::Vector3& position) const;
    //! \brief Switches piles between the full and the reduced mesh by their distance to the camera.
    void updateTreasuryLod(Ogre::Real timeSinceLastFrame);
    //! \brief Draws a few of the piles and heaps queued by rrTreasuryDetailChanged again.
    void updateTreasuryRebuild();
    //! Ends the dent of the pile: its entity is drawn again, the dynamic copy is destroyed
    void finishTreasuryDent(const std::string& entityName);
    //! \brief Lets the piles that grow or sink settle to their new height.
    void updateTreasuryPileSettles(Ogre::Real timeSinceLastFrame);
    //! \brief Ends the settling of the pile at once (the entity of the pile goes away).
    void cancelTreasuryPileSettle(const std::string& entityName);
    //! \brief True while the pile of that entity settles to a new height.
    bool isTreasuryPileSettling(const std::string& entityName) const;
    //! \brief Lists an object (or gold) standing in the gold of a treasury; it is drawn partly buried.
    void registerBuriedObject(RenderedMovableEntity* entity, float objectHeight);
    //! \brief The pile of the tile changed: the objects standing on it follow its new height.
    void refreshBuriedObjectsOnTile(Tile* tile);
    //! \brief Lets the objects standing in the gold sink or rise smoothly to their depth.
    void updateTreasuryBuriedObjects(Ogre::Real timeSinceLastFrame);
    //! \brief The height by which the node of the object is lifted so that it stands partly buried in the gold of
    //! its tile (0 when it is not listed or is carried). With settleAtOnce the object takes that height at once.
    float getBuriedLift(RenderedMovableEntity* entity, bool settleAtOnce);
    //! \brief Removes the sack that a thief carries on its back (nothing happens when it has none).
    void removeTreasuryThiefSack(Creature* creature);
    void refreshTreasuryGlow(int x, int y);
    void updateTreasuryGlow(Ogre::Real timeSinceLastFrame);
    void applyTreasuryGlowLights();
    void setTreasuryGlowLight(const std::string& name, const TreasuryGlowPatch& patch);
    void destroyTreasuryGlowLight(const std::string& name);
    //! \brief Ends the effects whose time is over and gives their places back to the budget of their room.
    void updateTreasuryEffects(Ogre::Real timeSinceLastFrame);
    //! \brief The worker standing on the tile climbs the pile and tips its gold out (only what is in view).
    void startTreasuryPour(Tile* tile, int level);
    //! \brief Moves the pouring workers (clips or procedural climb and tilt).
    void updateTreasuryPours(Ogre::Real timeSinceLastFrame);
    //! \brief Ends the pour of the creature (of every creature when none is given) and straightens it up.
    void cancelTreasuryPour(Creature* creature);
    //! \brief The extra height of the pouring worker above the gold of its tile (0 when it does not pour).
    float getTreasuryPourRise(Creature* creature) const;
    //! \brief Forgets the effects, the piles, the buried objects, the sacks and the glow lights and destroys the draw
    //! batches (the scene is cleared or destroyed).
    void clearTreasuryEffects();
    //! \brief Puts the given creature, or all lifted creatures if null, back on the floor.
    void cancelCreatureStep(Creature* creature = nullptr);
    //! \brief Destroys all running room construction bursts.
    void clearRoomConstructionEffects();
    //! \brief Destroys the particle system and the scene node of one burst. Names that
    //! no longer exist in the scene are ignored.
    void destroyRoomConstructionEffect(const RoomConstructionEffect& effect);
    //! Removes the fly swarm of a rotting corpse and puts the original materials back on its entity
    void clearCreatureDecay(Creature* creature);
    //! For each rotting corpse, the original materials of its sub-entities; while a corpse is listed here its
    //! entity uses private cloned materials whose corpseDecay value is driven by the animation progress
    std::map<Creature*, std::vector<Ogre::MaterialPtr>> mCreatureDecayMaterials;


    Ogre::TexturePtr m_texture;

    Ogre::Viewport* mViewport;
    Ogre::RTShader::ShaderGenerator* mShaderGenerator;

    //! For the keeper hand
    Ogre::SceneNode* mHandKeeperNode;
    //! \brief Node in the hand holding the creature that is shown.
    Ogre::SceneNode* mHeldCreatureGrip = nullptr;
    //! \brief Node holding the other held creatures, which are not shown.
    Ogre::SceneNode* mHeldCreatureStorage = nullptr;
    bool mHeldCreatureDisplayEnabled = false;
    Ogre::SceneNode* mDummyNode;
    Ogre::SceneNode* mHandLightNode;
    Ogre::SceneNode* mHandLightNode2;
    Ogre::Camera* mShadowCam;

    // As a workaround for some issues, we create dummy entities too small to be seen
    // and attach them to the keeper hand. This vector allows to keep a track and delete
    // them/recreate when loading a new game
    std::vector<Ogre::SceneNode*> mDummyEntities;

    //! \brief True if the creatures are currently displaying their text overlay
    bool mCreatureTextOverlayDisplayed;

    //! Bit array to allow to display tile hand (= 0) or not (!= 0)
    uint32_t mHandKeeperHandVisibility;
};

#endif // RENDERMANAGER_H
