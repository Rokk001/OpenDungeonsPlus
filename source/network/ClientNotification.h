/*!
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

#ifndef CLIENTNOTIFICATION_H
#define CLIENTNOTIFICATION_H

#include "network/ODPacket.h"

enum class ClientNotificationType
{
    // Communication with server
    hello,
    levelOK, // Tells the server the level loading was ok.
    setNick,
    readyForSeatConfiguration,
    // Messages that should be sent only by the client side of the server
    // (where the game configuration is done)
    seatConfigurationSet,
    seatConfigurationRefresh,

    chat,

    // Notification in game
    askEntityPickUp,
    askHandDrop,
    askMarkTiles,
    askBuildRoom,
    askSellRoomTiles,
    askBuildTrap,
    askSellTrapTiles,
    ackNewTurn,
    askCreatureInfos,
    askTileInfos,
    askPickupWorker,
    askPickupFighter,
    askSlapEntity,
    askCastSpell,
    askSetSkillTree,
    askSetPlayerSettings,

    askSaveMap,
    askExecuteConsoleCommand,
    notifyTileRevealed,
    
    //  Editor
    createAllEntities,
    editorAskChangeTile,
    editorAskChangeTiles,
    editorAskCreateDraggableTileContainer,    
    editorAskDeleteDraggableTileContainer,
    editorAskMoveDeltaDraggableTileContainer,
    editorAskSetRoundedPositionDraggableTileContainer,
    editorAskCopyRoom,
    editorAskBuildRoom,
    editorAskCopyTrap,
    editorAskBuildTrap,
    editorAskBuildTrapWithActivation,
    editorAskDestroyRoomTiles,
    editorAskDestroyTrapTiles,
    editorAskRevealTiles,
    editorAskRevealRooms,
    editorAskRevealTraps,
    editorCreateWorker,
    editorCreateFighter,
    editorAskCreateMapLight,
    editorSetCreatureLevel,
    editorAskPortalWaveData,
    editorSetPortalWaveData,

    // Append new messages to preserve existing network and replay identifiers.
    changeNick,
    askHandDropAll,

    askTrapProductionQueue,
    askMoveTrapProductionOrder,

    //! \brief Asks for the payout level of the casino on a tile and optionally sets it
    askCasinoPayout,

    //! \brief Editor: creates a special gift box on a tile
    editorCreateGiftBox,

    // Sandbox mode
    askSandboxTakeHero,
    askSandboxInvasion,
    //! Possession: the direction the possessed creature should walk (Vector2, zero to stop)
    askPossessMove,
    //! Possession: the player wants to leave the possessed creature
    askPossessExit,
    //! Possession: left click attack, the direction the creature looks at (Vector2)
    askPossessAttack,
    //! Possession: use the creature skill of the given slot (uint32_t, 0 to 3) in the given direction (Vector2)
    askPossessSkill,
    //! Editor: change or list the region markers of the level script:
    //! + int32_t operation (0 list, 1 set, 2 remove), string name, 4 int32_t (corners, set only).
    //! The server always answers with editorRegionData.
    editorRegionEdit
};

ODPacket& operator<<(ODPacket& os, const ClientNotificationType& nt);
ODPacket& operator>>(ODPacket& is, ClientNotificationType& nt);

/*! \brief A data structure used to pass messages to the clientNotificationProcessor thread.
 *
 */
class ClientNotification
{
    friend class ODClient;

public:
    ClientNotification(ClientNotificationType type);
    virtual ~ClientNotification()
    {}

    ODPacket mPacket;

    static std::string typeString(ClientNotificationType type);

private:
    ClientNotificationType mType;
};

#endif // CLIENTNOTIFICATION_H
