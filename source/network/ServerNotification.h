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

#ifndef SERVERNOTIFICATION_H
#define SERVERNOTIFICATION_H

#include "network/ODPacket.h"

#include <string>
#include <Ogre.h>

class Tile;
class Creature;
class MovableGameEntity;
class Player;

enum class ServerNotificationType
{
    // Negotiation for multiplayer
    loadLevel, // Tells the client to load the level: + string LevelFilename
    pickNick,
    addPlayers,
    removePlayers,
    startGameMode,
    newMap,
    addClass,
    clientAccepted,
    clientRejected,
    seatConfigurationRefresh,

    
    playerConfigChange,

    chat,
    chatServer,

    turnStarted,

    animatedObjectSetWalkPath,
    setObjectAnimationState,
    entityPickedUp,
    entityDropped,
    entityTeleported,
    entitySlapped,

    playerFighting, // Tells the player he is under attack or attacking
    playerNoMoreFighting, // Tells the player he is no longer under attack or attacking

    addEntity,
    removeEntity,
    entitiesRefresh,
    orientEntity,
    refreshPlayerSeat,
    setEntityOpacity,
    notifyCreatureInfo,
    notifyTileInfo,
    refreshCreatureVisDebug,
    restoreEverVisitedTiles,

    refreshSeatVisDebug,

    playSpatialSound, // Makes the client play a sound at tile coordinates.
    playRelativeSound, // Makes the client play a sound.

    pingCreateAllEntities,
    pingCreateDraggableTileContainer,
    pingDeleteDraggableTileContainer,
    pingEditorAskSetRoundedPositionDraggableTileContainer,
    markTiles,
    refreshTiles,
    refreshVisibleTiles,
    revealTiles,
    revealTraps,
    carryEntity,
    releaseCarriedEntity,

    skillTree,
    skillsDone,

    setPlayerSettings,

    setSpellCooldown,

    playerEvents,
    
    displayText,

    //! \brief Answer to the editor asking what the waves of a wave portal are
    editorPortalWaveData,

    exit,

    // Sent only to clients that negotiated live nickname changes.
    playerNickChanged,

    // Owner-only aggregate counts, sent only after creature-panel negotiation.
    creaturePanel,

    // Presentation-only burst for successfully built or sold gameplay room tiles.
    roomConstructionEffect,

    // Presentation-only creature melee impact.
    creatureCombatImpact,

    // Presentation-only consumption of an authoritative chicken.
    creatureChickenFeeding,

    // Owner-only reply to a production query or reorder request.
    trapProductionQueue,

    //! The team of a seat changed (an alliance of a level script): + int32_t seatId, int32_t teamId
    seatTeam,
    //! Score and room timer of a sandbox level: + int32_t score, int32_t target (0: none), string name of the
    //! next room that becomes available (empty: none), int32_t seconds until it, uint32_t number of bonus
    //! objectives, then per bonus: string text, int32_t points, bool awarded.
    sandboxStatus,
    //! The score of a sandbox realm reached its target: + string name of the realm, string level file of the
    //! next realm (empty: none), string text.
    sandboxRealmComplete,

    // Owner-only start of the defeat sequence for a defeated human player:
    // + int32_t conquerorSeatId (-1 if unknown), int32_t heartTileX, int32_t heartTileY (-1/-1 if unknown).
    // Appended last so that no existing numeric value changes.
    playerDefeated,

    // Owner-only debriefing counters, sent right after playerDefeated:
    // + int32_t elapsedSeconds, bool levelWon, int32_t seatCount, then per seat:
    // int32_t seatId and 6 uint32_t (keepers defeated, creatures killed, heroes destroyed,
    // rooms captured, items made, creatures converted).
    // Appended last so that no existing numeric value changes.
    levelStatistics,

    // Owner-only dungeon heart health for the ring of the top-left badge:
    // + float healthFraction (0 to 1, heart health / maximum heart health), bool underAttack.
    // Sent to a human owner when the fraction changed by at least one percentage point, when the
    // heart is destroyed, and once when the game starts or is loaded.
    // Appended last so that no existing numeric value changes.
    heartHealth,

    //! \brief Answer to askCasinoPayout: tile and payout level of the casino on it
    // Appended last so that no existing numeric value changes.
    casinoPayout,
    //! The player now possesses the creature: + string creatureName
    possessionStart,
    //! The player no longer possesses a creature
    possessionEnd,
    //! Answer to editorRegionEdit, all the region markers of the level script:
    //! + uint32_t count, then per region: string name and 4 int32_t (the corners).
    editorRegionData,
    //! A short cosmetic note that something happened (a mood change, a full treasury, a blow, a missile
    //! launch): + a CosmeticEvent (see network/CosmeticEvent.h). Only sent to clients that negotiated
    //! cosmetic events; an older client never gets it. Inserted before creatureAppearance; trapEffect
    //! and timeLimit stay the last values.
    cosmeticEvent,
    //! The server assigned a Dungeonbook appearance to a creature after it spawned (the portrait manifest
    //! was not available before): + string creature name, string appearance token. Sent once to the
    //! human players that see the creature; clients that see it later get it with the creature data.
    //! Inserted before relationshipTier; trapEffect and timeLimit stay the last values.
    creatureAppearance,
    //! Owner-only tier of a creature pair that changed (or the current tier, sent once when a
    //! client joins or a game is loaded): + string creatureA, string creatureB, int32_t tier
    //! (RelationshipTier), bool replay (true: replay of the current tier, no Dungeonbook post).
    //! Only sent when the creature relationships option is on.
    relationshipTier,
    //! A hatchery animal changed its kind (egg hatched, chick grew up): + string name, uint32_t kind
    //! (ChickenKind). Sent to the human players that see it, only when the kind changes.
    chickenKindChanged,
    //! Two roosters of one hatchery fight: + string first rooster, string second rooster, uint32_t phase
    //! (0 = the fight starts, 1 = it is over and the first rooster won, 2 = it was called off). The server draws
    //! the winner. Sent to the human players that see the first rooster, only when the phase changes.
    chickenFight,
    //! Presentation-only effect of a trap or door, sent to the human seats that see the tile:
    //! + int32_t kind (TrapEffectKind), int32_t tileX, int32_t tileY, string type name of the trap or door
    //! (e.g. Alarm, DoorSteel), float health fraction (0 to 1, doors only, else 1).
    //! Inserted before timeLimit, which stays the last value.
    trapEffect,
    //! The time left until the level is lost: + int32_t seconds (-1: there is no time limit)
    timeLimit
};

ODPacket& operator<<(ODPacket& os, const ServerNotificationType& nt);
ODPacket& operator>>(ODPacket& is, ServerNotificationType& nt);

//! \brief A data structure used to send messages to the clients
class ServerNotification
{
    friend class ODServer;

    public:
        /*! \brief Creates a message to be sent to concernedPlayer. If concernedPlayer is null, the message will be sent to
         *         every connected player.
         */
        ServerNotification(ServerNotificationType type, Player* concernedPlayer);
        virtual ~ServerNotification()
        {}

        ODPacket mPacket;

        static std::string typeString(ServerNotificationType type);

    private:
        ServerNotificationType mType;
        Player *mConcernedPlayer;
};

#endif // SERVERNOTIFICATION_H
