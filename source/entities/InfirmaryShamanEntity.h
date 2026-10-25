#ifndef INFIRMARYSHAMANENTITY_H
#define INFIRMARYSHAMANENTITY_H

#include "entities/RenderedMovableEntity.h"
#include <string>

class RoomInfirmary;

//! \brief A decorative room figure; never a fighter, patient or keeper-hand object.
class InfirmaryShamanEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates a shaman belonging to the named infirmary.
    InfirmaryShamanEntity(GameMap* map, const std::string& roomName);
    //! \brief Creates a client-side shaman before its packet is read.
    explicit InfirmaryShamanEntity(GameMap* map);
    //! \brief Identifies this decorative entity without creature behaviour.
    GameEntityType getObjectType() const override;
    //! \brief Walks between cots and occasionally performs a harmless pose beside a patient.
    void doUpkeep() override;
    //! \brief Returns the owning room name for clicking the figure.
    const std::string& getRoomName() const { return mRoomName; }
    //! \brief Retains the figure when two infirmaries join.
    void setRoomName(const std::string& roomName) { mRoomName = roomName; }
    //! \brief Appends the room association to the normal movable-entity packet.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Reads the room association of a visible shaman.
    void importFromPacket(ODPacket& packet) override;
    //! \brief Creates the figure received through the entity packet factory.
    static InfirmaryShamanEntity* getFromPacket(GameMap* map, ODPacket& packet);
private:
    //! \brief Converts the configured random second interval into turns without rounding.
    static double interval(const std::string& minimumKey, const std::string& maximumKey);
    //! \brief Walks over connected room tiles to a cot, passing through patients.
    bool walkToCot(RoomInfirmary& room);
    std::string mRoomName;
    double mWalkTurns;
    double mPoseTurns;
    double mPoseRemaining;
};
#endif
