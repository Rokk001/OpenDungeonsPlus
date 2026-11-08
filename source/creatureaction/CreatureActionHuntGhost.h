#ifndef CREATUREACTIONHUNTGHOST_H
#define CREATUREACTIONHUNTGHOST_H
#include "creatureaction/CreatureAction.h"
#include <OgreVector3.h>
#include <vector>
#include <string>
class GameMap;
class Seat;
class Tile;
class RoomGhostRoom;
class GhostEntity;
//! \brief Performs one persistent equipment, capture, revival and emptying trip.
//! States: 0 to the hook, 1 to the target, 2 box throw, 3 beam pull, 4 next target, 5 revival, 6 emptying,
//! 7 back to the hook, 8 lying box pick up, 9 walk to the closed box under the caught ghost and take it in hand,
//! 10 the lying box snaps shut over the pulled-in ghost (after state 3, before state 9).
class CreatureActionHuntGhost : public CreatureAction
{
public:
    //! \brief Creates an assigned hunt or an empty action ready to import its saved state.
    CreatureActionHuntGhost(Creature& creature, const std::string& target=std::string());
    //! \brief Releases reservations and drops remaining ghosts without changing the action queue.
    ~CreatureActionHuntGhost() override;
    //! \brief Returns the appended hunting action type.
    CreatureActionType getType() const override { return CreatureActionType::huntGhost; }
    //! \brief Returns the safe action handler.
    std::function<bool()> action() override; // allowed-lambda: signature required by CreatureAction
    //! \brief Interrupts equipment and target ownership, using the last world position when held.
    void interrupt();
    //! \brief Advances a hunt without popping itself inside a destructor.
    bool handleHunt();
    //! \brief Saves every phase, fractional clock, boxed identity and remaining route.
    void exportToStream(std::ostream& stream) const;
    //! \brief Reads the hunt and optional exact route continuation.
    bool importFromStream(std::istream& stream);
    //! \brief Transfers saved equipment and emptying identities with the room floor.
    void transferRoom(const std::string& previous, const std::string& current, bool hook, bool empty);
    //! \brief Pins a saved occupied cauldron before any equipment slot is rebound.
    void restoreLayout();
    //! \brief Restores reserved equipment after all rooms and entities have loaded.
    void restore();
    //! \brief Awards the training hall's fractional experience once per active hunt turn.
    void upkeep();
    //! \brief Assigns shortest-room-path targets to nearest available eligible hunters.
    static void assignHunters(GameMap& map, Seat& seat);
    //! \brief Plays an existing spatial family without the spell sound prefix.
    static void playSound(GameMap& map, Tile& tile, const std::string& family);
    //! \brief Returns whether this hunt currently wears its backpack.
    bool hasBackpack() const { return mEquipped && !mInterrupted; }
    //! \brief Returns the visual box phase: 0 absent, 1 flying shut from the hand under the ghost, 2 held shut in the
    //! hunter's hand (from the hook until it is hung back, also while still empty), 3 lying on the floor under the ghost
    //! while it opens and the beam then pulls the ghost in, 4 lying under the ghost while it snaps shut with the bang,
    //! 5 put by hand into the delivery device beside the hunter at the cauldron, shut, while the ghost flows out of the
    //! device into the cauldron (decisions 845 and 865), 6 lying shut under the caught ghost until the hunter picks it
    //! up (decision 865: once shut it stays shut).
    uint32_t getBoxVisualState() const;
    //! \brief Returns the ghost under a box being thrown, pulled in, snapping shut or waiting to be picked up, or the
    //! ghost being transferred from the delivery device into the cauldron.
    std::string getThrowGhostName() const;
    //! \brief Returns the time of one transfer from the delivery device into the cauldron in turns (GhostTransferSeconds,
    //! decision 845; the same for every hunter, only the CatchTime research of the keeper shortens it).
    double getTransferTurns() const;
    //! \brief Returns the beam seconds of a hunter: GhostBeamSeconds times the CatchTime research factor of its keeper
    //! divided by its ghost room efficiency (decisions 855 and 857). Server and client use it alike.
    static double getBeamSeconds(const Creature& hunter);
    //! \brief Returns the beam pull duration in turns (getBeamSeconds) while the beam pulls the ghost into the box, else 0.
    double getCaptureTurns() const;
    //! \brief Returns the current exact fractional phase clock.
    double getStepTurns() const { return mTurns; }
    //! \brief Returns the active beam target name for the client presentation.
    const std::string& getBeamTarget() const { return mBeamTarget; }
private:
    //! \brief Returns whether the hunter stands at its reserved cauldron and transfers its ghosts (state 6 arrived).
    bool isTransferring() const;
    //! \brief Finds this hunt's still-owned equipment room by saved identity.
    RoomGhostRoom* hookRoom() const;
    //! \brief Walks an exact normal path without pushing a second creature action.
    bool moveTo(Tile* tile);
    //! \brief Reserves the next unassigned ghost or lying box in own territory.
    bool nextTarget();
    //! \brief Releases the current target, restoring a held ghost to floating.
    void releaseTarget();
    //! \brief Selects a valid paid revival candidate remembered at the catch.
    bool selectRevival();
    //! \brief Returns the research-adjusted value of a room key.
    double researched(const std::string& key, const std::string& effect) const;
    uint32_t mState = 0;
    std::string mTarget;
    std::string mHookRoom;
    int mHookX = 0;
    int mHookY = 0;
    size_t mHookSlot = 0;
    double mTurns = 0.0;
    double mRepathTurns = 0.0;
    int64_t mLastTimedTurn = -1;
    std::vector<std::string> mGhosts;
    std::vector<std::string> mReviveGhosts;
    std::string mReviveTarget;
    std::string mBeamTarget;
    std::string mEmptyRoom;
    Tile* mDestination = nullptr;
    Tile* mEmptyAnchor = nullptr;
    Ogre::Vector3 mLastPosition;
    bool mEquipped = false;
    bool mInterrupted = false;
    bool mRestoring = false;
    bool mRegistered = false;
    //! \brief True once the hunter has put the trap into the delivery device at the cauldron with the put-in motion
    //! (decision 865); runtime only, a loaded delivery derives it from its saved clock (restore).
    bool mPutIn = false;
    std::vector<Ogre::Vector2> mLoadedPath;
};
#endif
