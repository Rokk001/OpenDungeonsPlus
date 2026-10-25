#ifndef ROOMINFIRMARY_H
#define ROOMINFIRMARY_H

#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include <map>
#include <string>
#include <vector>

class InfirmaryShamanEntity;

//! \brief A permanent cot layout and the patients treated on it.
class RoomInfirmary : public Room
{
public:
    //! \brief Describes one cot and its complete tile footprint.
    struct CotInfo
    {
        int size;
        int x;
        int y;
        int width;
        int height;
        double rotation;
        std::vector<Tile*> tiles;
    };
    //! \brief Keeps admission and reservation state without losing fractions or death time.
    struct PatientInfo
    {
        Creature* creature = nullptr;
        Creature* reservedBy = nullptr;
        std::string creatureName;
        std::string reservedByName;
        double admissionPaid = 0.0;
        int payer = 0;
        int32_t storedCounter = 0;
        bool manual = false;
    };
    //! \brief Creates an empty infirmary.
    RoomInfirmary(GameMap* gameMap);
    //! \brief Returns the room type.
    RoomType getType() const override { return RoomType::infirmary; }
    //! \brief Updates permanent furniture after the room shape changes.
    void updateActiveSpots(GameMap* gameMap = nullptr) override;
    //! \brief Transfers occupied cots before adjoining rooms join.
    void absorbRoom(Room* room) override;
    //! \brief Releases a patient whose cot loses a tile.
    bool removeCoveredTile(Tile* tile) override;
    //! \brief Stops treatments before ownership changes.
    void changeOwner(Seat* seat) override;
    //! \brief Releases patients before the room is removed.
    void removeFromGameMap(GameMap* gameMap = nullptr) override;
    //! \brief Checks defeat and interrupted reservations.
    void doUpkeep() override;
    //! \brief Rebinds saved patients and reserved carries after loading.
    void restoreInitialEntityState() override;
    //! \brief Reports whether a knockout has an available infirmary admission.
    static bool wouldAccept(const Creature& creature);
    //! \brief Reports whether an eligible creature can be delivered here.
    bool hasCarryEntitySpot(GameEntity* entity) override;
    //! \brief Finds or reserves the fitting cot for a carried creature.
    Tile* askSpotForCarriedEntity(GameEntity* entity) override;
    //! \brief Records which worker owns a cot reservation.
    Tile* reserveCot(Creature& creature, Creature& carrier);
    //! \brief Releases a worker reservation when carrying ends.
    void cancelReservation(Creature& carrier);
    //! \brief Admits a delivered creature or sends its carrier to its bed.
    void notifyCarryingStateChanged(Creature* carrier, GameEntity* entity) override;
    //! \brief Admits a manually dropped patient with keeper payment.
    void creatureDropped(Creature& creature) override;
    //! \brief Advances a resting patient and discharges it at the selected health.
    bool restPatient(Creature& creature);
    //! \brief Ends an interrupted treatment without refund.
    void releasePatient(Creature& creature);
    //! \brief Returns the admission for a creature, or null.
    PatientInfo* getPatient(Creature& creature);
    //! \brief Returns the permanent cot map.
    const std::map<size_t, CotInfo>& getCots() const { return mCots; }
    //! \brief Returns admissions and running reservations.
    const std::map<size_t, PatientInfo>& getPatients() const { return mPatients; }
    //! \brief Returns all cot footprint tiles.
    std::vector<Tile*> getCotTiles() const;
    //! \brief Returns occupied cot positions for the room figure.
    std::vector<Tile*> getPatientPositions() const;
    //! \brief Returns the instrument table or the first free floor tile.
    Tile* getShamanSpawnTile() const;
    //! \brief Checks payment without taking gold; manual admissions always use the keeper.
    bool canPayAdmission(const Creature& creature, bool manual) const;
    //! \brief Takes admission gold and returns the actual amount and payer.
    bool payAdmission(Creature& creature, bool manual, double& amount, int& payer);
    //! \brief Pays mana and heals one turn; returns whether any HP was healed.
    bool healPatient(Creature& creature);
    //! \brief Returns the keeper's discharge health percentage.
    int getDischargeThreshold() const;
    //! \brief Returns the matching cot size from the creature definition.
    static int cotSize(const Creature& creature);
    //! \brief Tests the minimum contiguous square required when building.
    static bool containsMinimumBlock(GameMap& map, Seat* seat, const std::vector<Tile*>& tiles);
    //! \brief Returns the one decorative room figure, if the room has a spawn tile.
    InfirmaryShamanEntity* getShaman() const { return mShaman; }
    //! \brief Plays the real rattle recording at the figure's current tile.
    void playShamanRattle(Tile& tile);
protected:
    //! \brief Saves the existing figure's exact room position.
    void exportShamanToStream(std::ostream& stream) const;
    //! \brief Reads an optional figure position, rewinding when the tag is absent.
    bool importShamanFromStream(std::istream& stream);
    //! \brief Saves the exact cot, admission and reservation state.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Reads optional cot, admission and reservation tags.
    bool importFromStream(std::istream& stream) override;
    //! \brief Creates wall furniture, leaving central spots for cots.
    BuildingObject* notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile) override;
    //! \brief Removes furniture without removing a cot on a central spot.
    void notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile) override;
private:
    //! \brief Recomputes free cots around every occupied or reserved cot.
    void layoutCots();
    //! \brief Creates the room object for a cot.
    void createCotObject(size_t id);
    //! \brief Places the patient and starts its rest action after payment.
    bool admit(size_t id, Creature& creature, bool manual);
    //! \brief Returns the first free matching cot, allowing manual drops to take reservations.
    size_t findCot(const Creature& creature, bool manual) const;
    //! \brief Releases one treatment back to its saved knockout countdown.
    void abandon(size_t id);
    //! \brief Releases all treatments and reservations on loss of the room.
    void abandonAll();
    //! \brief Creates or reassigns the single room figure after rebuilding or loading.
    void updateShaman();
    //! \brief Removes the figure when its room is actually removed.
    void removeShaman();
    InfirmaryShamanEntity* mShaman = nullptr;
    bool mHasLoadedShamanPosition = false;
    Ogre::Vector2 mLoadedShamanPosition = Ogre::Vector2::ZERO;
    std::map<size_t, CotInfo> mCots;
    std::map<size_t, PatientInfo> mPatients;
    std::map<size_t, BuildingObject*> mCotObjects;
    std::vector<Tile*> mAccessoryTiles;
    Tile* mInstrumentTable;
    size_t mNextCotId;
    bool mLayingOut;
    bool mLoadedCots;
};
#endif
