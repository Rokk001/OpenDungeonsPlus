#ifndef ROOMGHOSTROOM_H
#define ROOMGHOSTROOM_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "game/SeatData.h"
#include <array>
#include <map>
#include <memory>
#include <set>

class GhostEntity;
class ItemInstance;

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
    //! \brief One apparatus of the room. The index in the room is its GhostProduct value: research = ghost press,
    //! mana = mana still, crystal = soul forge.
    struct Apparatus
    {
        //! Floor tile at the room wall it stands on, null while the room has no place for it
        Tile* tile = nullptr;
        //! Floor tile where workers put down the ectoplasm for it
        Tile* stand = nullptr;
        //! Its furniture
        BuildingObject* object = nullptr;
        //! Ectoplasm waiting in front of it
        uint32_t queue = 0;
        //! True while it works on one ectoplasm
        bool working = false;
        //! Remaining work turns of that ectoplasm; a fraction below zero carries over to the next one
        double workTurns = 0.0;
        //! Soul forge: ectoplasm already put into the unfinished level crystal
        uint32_t crystalEctoplasm = 0;
        //! The shown state ("Working", "Locked" or "Idle")
        std::string shownState;
    };
    //! \brief Number of apparatuses in every ghost room.
    static const uint32_t APPARATUS_COUNT = 3;
    //! \brief Creates a room without cauldrons or reservations.
    RoomGhostRoom(GameMap* map);
    //! \brief Releases separately owned wall decorations before the room floor is destroyed.
    ~RoomGhostRoom() override;
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
    //! \brief Rings the alarm and starts its prescribed blinking interval.
    void ringBell();
    //! \brief Returns the stable current equipment slot of a hunter, or the absent sentinel.
    size_t getHunterHookSlot(const Creature& hunter) const;
    //! \brief Returns the exact cauldron anchor reserved by a hunter.
    Tile* getHunterCauldron(const Creature& hunter) const;
    //! \brief Reserves the nearest free equipment hook for a hunter.
    Tile* reserveHook(Creature& hunter);
    //! \brief Changes a reserved hook between its equipped and empty appearance.
    void equipHook(Creature& hunter, bool equipped);
    //! \brief Rebinds an exact saved equipment hook without selecting another tile.
    void restoreHunter(Creature& hunter, Tile* hook, bool equipped, size_t slot);
    //! \brief Rebinds the occupied cauldron next to the saved standing tile.
    void restoreCauldron(Creature& hunter, Tile* standing, Tile* anchor, bool rebuild=true);
    //! \brief Releases only the emptying place, retaining the hunter's backpack hook.
    void releaseCauldron(Creature& hunter);
    //! \brief Returns equipment and all cauldron reservations of a hunter.
    void releaseHunter(Creature& hunter);
    //! \brief Reserves a free reachable standing place beside an available cauldron.
    Tile* reserveCauldron(Creature& hunter);
    //! \brief Consumes one boxed ghost; every complete ectoplasm appears as an item next to that cauldron.
    void emptyGhost(Creature& hunter, GhostEntity& ghost);
    //! \brief The room research level that unlocks an apparatus: 1 mana still, 2 ghost press, 3 soul forge.
    static uint32_t getUnlockLevel(GhostProduct kind);
    //! \brief True when the keeper's room research has unlocked the apparatus.
    static bool isApparatusUnlocked(const Seat& seat, GhostProduct kind);
    //! \brief The keeper's chosen apparatus; a locked choice counts as the mana still.
    static GhostProduct getChosenApparatus(const Seat& seat);
    //! \brief The mesh of an apparatus (placeholder until its own model exists).
    static const std::string& getApparatusMesh(GhostProduct kind);
    //! \brief Returns one apparatus of this room.
    const Apparatus& getApparatus(GhostProduct kind) const { return mApparatuses[static_cast<uint32_t>(kind)]; }
    //! \brief The tile where workers put down ectoplasm for the apparatus, null if the room has none.
    Tile* getApparatusStandTile(GhostProduct kind) const;
    //! \brief Takes ectoplasm for an unlocked apparatus; ectoplasm queues there without limit.
    bool hasCarryEntitySpot(GameEntity* carriedEntity) override;
    //! \brief Directs the worker to the apparatus chosen when the ectoplasm was picked up.
    Tile* askSpotForCarriedEntity(GameEntity* carriedEntity) override;
    //! \brief Puts delivered ectoplasm into the queue of its apparatus.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* carriedEntity) override;
protected:
    //! \brief Saves the floor, then the queue, running work and level crystal progress of every apparatus.
    void exportToStream(std::ostream& os) const override;
    //! \brief Reads the floor and the apparatus state; old saves without it start with idle apparatuses.
    bool importFromStream(std::istream& is) override;
    //! \brief Creates the ordered bell and backpack hooks.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Removes a wall decoration and its reservation.
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! \brief Rebuilds free cauldron positions in increasing y then x order.
    void layoutCauldrons();
    //! \brief Recreates furniture for the current cauldron layout.
    void createCauldronObjects();
    //! \brief Returns the floor tile nearest to a cauldron or apparatus where an item falls, or nullptr if none is free.
    //! Tiles under cauldrons and apparatuses are never used.
    //! \param origin Anchor tile of the cauldron or tile of the apparatus.
    //! \param offset 0.5 for a 2x2 cauldron anchor (its centre), 0 for an apparatus tile.
    Tile* findDropTile(const Tile& origin, double offset) const;
    //! \brief Turns every complete ectoplasm of the keeper value into an item next to the cauldron.
    void produceEctoplasm(Tile& cauldron);
    //! \brief Places an item owned by the keeper on a floor tile.
    void spawnItem(Tile& tile, std::unique_ptr<ItemInstance> item, Seat* seat);
    //! \brief Places the three apparatuses on floor tiles at the room wall, keeping every other tile reachable.
    void layoutApparatuses();
    //! \brief Creates the apparatus furniture for the current layout.
    void createApparatusObjects(GameMap* map);
    //! \brief Advances the work of every apparatus by one turn.
    void workApparatuses();
    //! \brief Finishes one ectoplasm in an apparatus and lets its product fall next to it.
    void finishEctoplasm(GhostProduct kind);
    //! \brief Lets every waiting, running and forged ectoplasm fall to the floor as items; nothing is lost.
    //! \param tile The tile where they fall, or null for each apparatus's own place
    void dropHeldEctoplasm(Tile* tile);
    //! \brief The apparatus a delivered or carried ectoplasm goes to.
    GhostProduct getDeliveryTarget(const GameEntity& carriedEntity, const ItemInstance& item) const;
    //! \brief Releases hunters assigned to this room before equipment is lost.
    void interruptHunters();
    std::vector<Cauldron> mCauldrons;
    //! \brief Releases owned decorative entities without touching other room objects.
    void clearWallObjects();
    std::map<Creature*, Tile*> mHooks;
    std::map<Creature*, size_t> mHookSlots;
    std::vector<BuildingObject*> mWallObjects;
    std::vector<BuildingObject*> mHookObjects;
    std::vector<Tile*> mHookTiles;
    std::vector<Tile*> mDecorationTiles;
    std::vector<BuildingObject*> mCauldronObjects;
    bool mLayingOut = false;
    double mAlarmTurns = 0.0;
    std::array<Apparatus, APPARATUS_COUNT> mApparatuses;
};
#endif
