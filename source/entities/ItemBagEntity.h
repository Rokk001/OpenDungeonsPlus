#ifndef ITEMBAGENTITY_H
#define ITEMBAGENTITY_H

#include "entities/RenderedMovableEntity.h"
#include "entities/ItemInstance.h"

//! \brief One unstacked item or potion lying on the ground, held or carried by a worker.
class ItemBagEntity : public RenderedMovableEntity
{
public:
    //! \brief Creates a new bag and takes ownership of the contained instance.
    ItemBagEntity(GameMap* map, std::unique_ptr<ItemInstance> item);
    //! \brief Creates a bag ready to read from a save or network packet.
    explicit ItemBagEntity(GameMap* map);
    //! \brief Releases an Epic only when the contained instance permanently leaves the map.
    ~ItemBagEntity() override;
    //! \brief Returns the appended item-bag entity type.
    GameEntityType getObjectType() const override;
    //! \brief Returns the contained instance, or null after a completed ownership transfer.
    ItemInstance* getItem() { return mItem.get(); }
    //! \brief Returns the immutable contained instance.
    const ItemInstance* getItem() const { return mItem.get(); }
    //! \brief Transfers ownership without unregistering an Epic that remains on this map.
    std::unique_ptr<ItemInstance> takeItem();
    //! \brief Restores an unaccepted gift to this same bag without changing Epic ownership.
    void restoreItem(std::unique_ptr<ItemInstance> item) { mItem = std::move(item); }
    //! \brief Ages ground bags and claims treasury ownership; successful transfers remove consumed bags.
    void doUpkeep() override;
    //! \brief Allows the owning keeper to pick up visible bags except sealed merchant goods.
    bool tryPickup(Seat* seat) override;
    //! \brief Allows dropping onto any visible non-solid tile.
    bool tryDrop(Seat* seat, Tile* tile) override;
    //! \brief Places a dropped bag; Player offers its gift after notifying the drop to clients.
    void drop(const Ogre::Vector3& position) override;
    //! \brief Makes old ground bags carryable while leaving treasury storage in place unless a merchant wants it.
    EntityCarryType getEntityCarryType(Creature* carrier) override;
    //! \brief Removes a worker's carried bag from its previous tile.
    void notifyEntityCarryOn(Creature* carrier) override;
    //! \brief Places a delivered bag back on its destination tile.
    void notifyEntityCarryOff(const Ogre::Vector3& position) override;
    //! \brief Reads a fully owned bag from a level or save.
    static ItemBagEntity* loadFromStream(GameMap* map, std::istream& stream);
    //! \brief Reads a client bag from its entity packet.
    static ItemBagEntity* loadFromPacket(GameMap* map, ODPacket& packet);
    //! \brief Writes the base entity fields followed by the contained instance.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Reads one contained instance or a random-quality level token.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends the complete item so hover and keeper-hand views share its rolled values.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Receives the complete contained instance.
    void importFromPacket(ODPacket& packet) override;
protected:
    //! \brief Creates the bag mesh with its quality tint and optional merchant seal.
    void createMeshLocal(NodeType type = NodeType::MTILES_NODE) override;
private:
    //! \brief The owned instance and number of turns it has remained on the floor.
    std::unique_ptr<ItemInstance> mItem;
    uint32_t mIdleTurns;
};

#endif
