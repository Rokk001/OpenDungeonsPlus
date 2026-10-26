#ifndef HERBBUNDLEENTITY_H
#define HERBBUNDLEENTITY_H

#include "entities/RenderedMovableEntity.h"
#include <cstdint>
#include <string>

//! \brief One harvested bundle carried by workers to their seat's alchemy laboratory.
class HerbBundleEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates a harvested herb bundle containing the given number of recipe units.
    HerbBundleEntity(GameMap* map, const std::string& herb, uint32_t count = 1);
    //! \brief Creates an empty bundle for save or packet import.
    explicit HerbBundleEntity(GameMap* map);
    //! \brief Returns the bundle's appended entity type.
    GameEntityType getObjectType() const override;
    //! \brief Returns the herb recipe id, unchanged during carrying and looting.
    const std::string& getHerb() const { return mHerb; }
    //! \brief Returns the bundle's remaining recipe units.
    uint32_t getCount() const { return mCount; }
    //! \brief Transfers recipe units to laboratory storage.
    uint32_t take(uint32_t maximum);
    //! \brief Offers a ground bundle to workers of any seat, including enemy looters.
    EntityCarryType getEntityCarryType(Creature* carrier) override;
    //! \brief Removes a lifted bundle from its old floor tile.
    void notifyEntityCarryOn(Creature* carrier) override;
    //! \brief Places a released bundle on the destination floor.
    void notifyEntityCarryOff(const Ogre::Vector3& position) override;
    //! \brief Saves the identity and count after the existing movable entity fields.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Restores a complete saved bundle.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends the identity and count to clients that see the bundle.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Reads the client bundle data without adopting a truncated payload.
    void importFromPacket(ODPacket& packet) override;
protected:
    //! \brief Creates the original bundle mesh and applies the recipe herb's colour.
    void createMeshLocal(NodeType type = NodeType::MTILES_NODE) override;
private:
    //! \brief Definition id and recipe units owned by this loose bundle.
    std::string mHerb;
    uint32_t mCount;
};

#endif
