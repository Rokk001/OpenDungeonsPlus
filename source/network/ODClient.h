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

#ifndef ODCLIENT_H
#define ODCLIENT_H

#include "network/ODSocketClient.h"
#include "network/ClientNotification.h"
#include "game/HeartHealthRing.h"
#include "game/LevelStatistics.h"

#include <OgreSingleton.h>

#include <deque>
#include <map>
#include <string>
#include <vector>

class GameMap;
class ODPacket;
class ChatMessage;
class EventMessage;

class ODClient: public Ogre::Singleton<ODClient>,
    public ODSocketClient
{
    friend class Console;
 public:
    ODClient();
    ~ODClient();

    // CLIENT

    /*! \brief The function which monitors the clientNotificationQueue for new events and informs the server about them.
     *
     * This runs on the client side and acts as a "consumer" on the
     * clientNotificationQueue.  It takes an event out of the queue, determines
     * which clients need to be informed about that particular event, and
     * dispacthes TCP packets to inform the clients about the new information.
     */
    void processClientNotifications();

    //! \brief Connects to the server host:port
    bool connect(const std::string& host, const int port, uint32_t timeout, const std::string& outputReplayFilename) override;

    //! \brief Connects to the server host:port
    bool replay(const std::string& filename) override;

    //! \brief Adds a client notification to the client notification queue.
    void queueClientNotification(ClientNotification* n);

    //! \brief Asks the server to change the nickname of the local player. Does nothing if the nickname is
    //! unchanged, if not playing on a server, or if the server does not support live nickname changes.
    void requestNicknameChange(const std::string& nickname);

    /*! \brief Adds a client notification to the client notification queue.
     *  \param type The type of the notification
     *  \param args The arguments that are to be piped into the notification.
     */
    template<typename ...Args>
    void queueClientNotification(ClientNotificationType type, const Args&... args);

    /*! \brief Adds a client notification to the client notification queue.
     *  \param type The type of the notification
     */
    void queueClientNotification(ClientNotificationType type)
    {
        mClientNotificationQueue.emplace_back(new ClientNotification(type));
    }

    //! \brief Disconnect the client.
    //! \param keepReplay Tells whether to keep the new replay file.
    void disconnect(bool keepReplay = false) override;

    //! \brief Adds a client notification to the client notification queue.
    void notifyExit();

    const std::string& getLevelFilename() {return mLevelFilename;}

    inline bool getIsPlayerConfig() const
    { return mIsPlayerConfig; }

    //! @brief True once the debriefing counters of the lost level have been received
    inline bool hasLevelStatistics() const
    { return mHasLevelStatistics; }

    inline const LevelStatistics& getLevelStatistics() const
    { return mLevelStatistics; }

    //! \brief Seconds left until the level is lost, -1 if there is no time limit. A countdown that ends
    //! without a defeat has GameMap::TIME_LIMIT_COUNTDOWN_FLAG added.
    inline int32_t getTimeLimitSeconds() const
    { return mTimeLimitSeconds; }

    //! \brief Seconds left until the next hero wave of a level script, -1 if none is shown
    inline int32_t getWaveCountdownSeconds() const
    { return mWaveCountdownSeconds; }

    //! \brief What the heart health ring of the top-left badge has to show
    inline HeartHealthRing::BadgeState& getHeartBadge()
    { return mHeartBadge; }

    //! \brief Health fraction of the heart of a seat as the heartHealthStage events last told it (the
    //! upper end of the step), -1 if no step is known (event not negotiated, heart never seen)
    float getHeartStageFraction(int32_t seatId) const;

    //! \brief True while the heart of a seat counts as hit: its step just fell (glows ATTACK_GLOW_SECONDS)
    bool isHeartStageHit(int32_t seatId) const;

    //! \brief Frame update: lets the hit glow of the foreign hearts run out
    void updateHeartStageHits(float timeSinceLastFrame);

    //! \brief A bonus objective of a sandbox realm as the server last told it
    struct SandboxBonusStatus
    {
        std::string mText;
        int32_t mPoints = 0;
        bool mAwarded = false;
    };

    //! \brief Score and room timer of a sandbox level as the server last told it
    struct SandboxStatus
    {
        bool mIsReceived = false;
        int32_t mScore = 0;
        //! \brief 0 if the level has no target score
        int32_t mTarget = 0;
        //! \brief Name of the next room that becomes available, empty if there is none
        std::string mNextRoom;
        int32_t mSecondsLeft = 0;
        std::vector<SandboxBonusStatus> mBonuses;
    };

    //! \brief The score, room timer and bonus objectives of the sandbox as the server last told them
    inline const SandboxStatus& getSandboxStatus() const
    { return mSandboxStatus; }

    //! \brief True from the moment the server tells that the sandbox realm is complete, until the GUI took it
    inline bool hasSandboxRealmComplete() const
    { return mHasSandboxRealmComplete; }

    //! \brief The name of the realm that was completed, as the server told it
    inline const std::string& getSandboxRealmId() const
    { return mSandboxRealmId; }

    //! \brief The level file of the realm that follows the completed one, empty if there is none
    inline const std::string& getSandboxNextLevel() const
    { return mSandboxNextLevel; }

    //! \brief The text the server sends with the completion of the realm
    inline const std::string& getSandboxRealmText() const
    { return mSandboxRealmText; }

    //! \brief Marks the completion of the realm as taken by the GUI
    inline void clearSandboxRealmComplete()
    { mHasSandboxRealmComplete = false; }

    inline void pause()
    { mGameClock.pause(); }


    inline void resume()
    { mGameClock.start(); }

    
 protected:
    //! \brief Applies a server notification, including the saved campaign victory result; creature notices
    //! get the profile name shown on the creature card. For the carry and release notifications it also flags
    //! the carrier as carrying or not carrying on the client.
    //! Building-object replacement adds create the new mesh before releasing the old one in this handler.
    //! \return true if the notification was processed.
    bool processMessage(ServerNotificationType cmd, ODPacket& packetReceived) override;
    //! \brief Restores any loading presentation and reports the lost connection.
    void playerDisconnected() override;

 private:
    //! \brief Convenience function to send a game event.
    void addEventMessage(EventMessage* event);

    //! \brief Refreshes the player's goals + main data
    void refreshMainUI(const std::string& goalsString);

    std::string mTmpReceivedString;
    std::string mLevelFilename;

    std::deque<ClientNotification*> mClientNotificationQueue;

    // true if the server told us we are allowed to configure the game. False otherwise
    bool mIsPlayerConfig;

    // Debriefing counters sent by the server after playerDefeated
    bool mHasLevelStatistics;
    LevelStatistics mLevelStatistics;
    //! \brief Last time limit received with timeLimit, -1 when there is none
    int32_t mTimeLimitSeconds;
    //! \brief Last wave countdown received with timeLimit, -1 when none is shown
    int32_t mWaveCountdownSeconds;

    // Heart health received with heartHealth
    HeartHealthRing::BadgeState mHeartBadge;

    // Steps of the hearts received with the cosmetic event heartHealthStage: seat id -> fraction of the step
    std::map<int32_t, float> mHeartStageFractions;

    // Seconds the hit glow of the heart of a seat still lasts, set when its step falls: seat id -> seconds
    std::map<int32_t, float> mHeartStageHitRemaining;

    // Received with sandboxStatus and sandboxRealmComplete
    SandboxStatus mSandboxStatus;
    bool mHasSandboxRealmComplete;
    std::string mSandboxRealmId;
    std::string mSandboxNextLevel;
    std::string mSandboxRealmText;

};

template<typename ...Args>
void ODClient::queueClientNotification(ClientNotificationType type, const Args&... args)
{
    queueClientNotification(type);
    ODPacket::putInPacket(mClientNotificationQueue.back()->mPacket, args...);
}

#endif // ODCLIENT_H
