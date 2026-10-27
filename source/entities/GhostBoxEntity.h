#ifndef GHOSTBOXENTITY_H
#define GHOSTBOXENTITY_H

#include "entities/RenderedMovableEntity.h"
#include <vector>

//! \brief A lying closed capture box whose spirits are released after its saved opening delay.
class GhostBoxEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates an empty box for loading.
    explicit GhostBoxEntity(GameMap* map);
    //! \brief Creates a lying box owning the supplied boxed ghost identities.
    GhostBoxEntity(GameMap* map, const std::vector<std::string>& ghosts);
    //! \brief Returns the appended capture-box entity type.
    GameEntityType getObjectType() const override;
    //! \brief Keeps the keeper's hand from picking up a box or its spirits.
    bool tryPickup(Seat* seat) override { return false; }
    //! \brief Advances the exact opening counter and frees the spirits when it expires.
    void doUpkeep() override;
    //! \brief Rebinds contained spirits after all saved entities have been loaded.
    void restoreInitialEntityState() override;
    //! \brief Returns the identities currently owned by this box.
    const std::vector<std::string>& getGhostNames() const { return mGhostNames; }
    //! \brief Transfers the identities to a hunter without releasing their spirits.
    std::vector<std::string> takeGhostNames();
    //! \brief Returns the hunter reserving this lying box, or an empty name.
    const std::string& getAssignedHunter() const { return mAssignedHunter; }
    //! \brief Reserves this box for a hunter or clears its reservation.
    void setAssignedHunter(const std::string& hunter);
    //! \brief Returns the exact fractional time already spent lying closed.
    double getOpenTurns() const { return mOpenTurns; }
    //! \brief Saves the prescribed box record and its optional owner and reservation continuation.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Restores a complete box record without resolving spirits too early.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends placement, opening time, contents and reservation to a new observer.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Reads a complete client box representation.
    void importFromPacket(ODPacket& packet) override;
    //! \brief Sends the current closed-box continuation to observers.
    void exportToPacketForUpdate(ODPacket& packet, Seat* seat) override;
    //! \brief Applies the current closed-box continuation on a client.
    void updateFromPacket(ODPacket& packet) override;
    //! \brief Creates a box from one validated saved record.
    static GhostBoxEntity* loadFromStream(GameMap* map, std::istream& stream);
    //! \brief Creates a box from its entity creation packet.
    static GhostBoxEntity* loadFromPacket(GameMap* map, ODPacket& packet);
private:
    //! \brief Sends a box state change through the existing entity refresh notification.
    void refresh();
    std::vector<std::string> mGhostNames;
    std::string mAssignedHunter;
    double mOpenTurns;
};
#endif
