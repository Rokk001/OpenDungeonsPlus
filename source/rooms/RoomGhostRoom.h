#ifndef ROOMGHOSTROOM_H
#define ROOMGHOSTROOM_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include <map>
#include <set>

class GhostEntity;

//! \brief Owns the deterministic cauldron floor and hunting equipment of a ghost room.
class RoomGhostRoom : public Room
{
public:
    //! \brief Holds one complete 2x2 cauldron and its current emptying hunter.
    struct Cauldron
    {
        Tile* anchor;
        Creature* hunter;
    };
    //! \brief Creates a room without cauldrons or reservations.
    RoomGhostRoom(GameMap* map);
    //! \brief Returns the appended ghost room type.
    RoomType getType() const override { return RoomType::ghostRoom; }
    //! \brief Rebuilds deterministic furniture while retaining occupied cauldrons.
    void updateActiveSpots(GameMap* map = nullptr) override;
    //! \brief Joins equipment layouts after the room floors join.
    void absorbRoom(Room* room) override;
    //! \brief Transfers intact equipment when the floor splits.
    void splitRoom(Room& room, const std::vector<Tile*>& tiles) override;
    //! \brief Ends a cauldron and its reservations before removing its floor.
    bool removeCoveredTile(Tile* tile) override;
    //! \brief Releases this room's hunters before a takeover.
    void changeOwner(Seat* seat) override;
    //! \brief Releases this room's hunters before it disappears.
    void removeFromGameMap(GameMap* map = nullptr) override;
    //! \brief Assigns available hunters to unclaimed targets on their keeper's territory.
    void doUpkeep() override;
    //! \brief Checks the selected tiles together with adjoining own ghost rooms before charging.
    static bool containsMinimumBlock(GameMap& map, Seat* seat, const std::vector<Tile*>& tiles);
    //! \brief Returns the current deterministic cauldron layout.
    const std::vector<Cauldron>& getCauldrons() const { return mCauldrons; }
    //! \brief Returns the number of backpacks supplied by this room.
    uint32_t getBackpackCount() const;
    //! \brief Returns the keeper's research-adjusted ghost levels per ectoplasm.
    static double getLevelsPerEctoplasm(const Seat& seat);
    //! \brief Reserves the nearest free equipment hook for a hunter.
    Tile* reserveHook(Creature& hunter);
    //! \brief Changes a reserved hook between its equipped and empty appearance.
    void equipHook(Creature& hunter, bool equipped);
    //! \brief Returns equipment and all cauldron reservations of a hunter.
    void releaseHunter(Creature& hunter);
    //! \brief Reserves a free reachable standing place beside an available cauldron.
    Tile* reserveCauldron(Creature& hunter);
    //! \brief Consumes one boxed ghost and produces complete ectoplasm units.
    void emptyGhost(Creature& hunter, GhostEntity& ghost);
protected:
    //! \brief Creates the ordered bell, backpack hooks and wall gauges.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Removes a wall decoration and its reservation.
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! \brief Rebuilds free cauldron positions in increasing y then x order.
    void layoutCauldrons();
    //! \brief Recreates furniture for the current cauldron layout.
    void createCauldronObjects();
    //! \brief Releases hunters assigned to this room before equipment is lost.
    void interruptHunters();
    std::vector<Cauldron> mCauldrons;
    std::map<Creature*, Tile*> mHooks;
    std::vector<Tile*> mHookTiles;
    std::vector<Tile*> mDecorationTiles;
    std::vector<BuildingObject*> mCauldronObjects;
    Tile* mBowl = nullptr;
    bool mLayingOut = false;
};
#endif
