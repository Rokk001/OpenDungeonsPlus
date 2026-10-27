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
    std::function<bool()> action() override;
    //! \brief Interrupts equipment and target ownership, using the last world position when held.
    void interrupt();
    //! \brief Advances a hunt without popping itself inside a destructor.
    bool handleHunt();
    //! \brief Saves every phase, fractional clock, boxed identity and remaining route.
    void exportToStream(std::ostream& stream) const;
    //! \brief Reads the hunt and optional exact route continuation.
    bool importFromStream(std::istream& stream);
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
    //! \brief Returns the active beam target name for the client presentation.
    const std::string& getBeamTarget() const { return mBeamTarget; }
private:
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
    double mTurns = 0.0;
    double mRepathTurns = 0.0;
    std::vector<std::string> mGhosts;
    std::vector<std::string> mReviveGhosts;
    std::string mReviveTarget;
    std::string mBeamTarget;
    std::string mEmptyRoom;
    Tile* mDestination = nullptr;
    Ogre::Vector3 mLastPosition;
    bool mEquipped = false;
    bool mInterrupted = false;
    bool mRestoring = false;
    std::vector<Ogre::Vector2> mLoadedPath;
};
#endif
