#ifndef GIFTBOXITEM_H
#define GIFTBOXITEM_H

#include "entities/GiftBoxEntity.h"
#include "entities/ItemInstance.h"

//! \brief An item gift box that must be cracked at a researched workshop rather than consumed as a special.
class GiftBoxItem : public GiftBoxEntity
{
public:
    //! \brief Creates a box containing a fixed instance or a deferred random-quality request.
    GiftBoxItem(GameMap* map, const std::string& content);
    //! \brief Creates a box ready for saved-state import.
    explicit GiftBoxItem(GameMap* map);
    //! \brief Unregisters an untransferred fixed Epic when its box permanently disappears.
    ~GiftBoxItem() override;
    //! \brief Returns the quality gate used by workshop transport and cracking.
    Quality getItemQuality() const;
    //! \brief Returns whether this seat has the tools needed to crack this box.
    bool canCrack(const Seat& seat) const;
    //! \brief Returns the fixed item, or null while a random roll is deferred.
    const ItemInstance* getItem() const { return mItem.get(); }
    //! \brief Returns whether construction supplied a valid fixed item or deferred roll.
    bool hasContent() const { return mItem.get() != nullptr || !mRandomQuality.empty(); }
    //! \brief Resolves deferred content and transfers its instance without unregistering it.
    std::unique_ptr<ItemInstance> crack();
    //! \brief Keeps stored boxes carryable only when a workshop can now crack them.
    EntityCarryType getEntityCarryType(Creature* carrier) override;
protected:
    //! \brief Writes the box placement followed by its content.
    void exportToStream(std::ostream& stream) const override;
    //! \brief Loads a fixed instance or a deferred random-quality request.
    bool importFromStream(std::istream& stream) override;
    //! \brief Sends only quality after the ordinary box placement; its contents remain hidden.
    void exportToPacket(ODPacket& packet, const Seat* seat) const override;
    //! \brief Reads the client-only quality used for tinting the box.
    void importFromPacket(ODPacket& packet) override;
    //! \brief Creates the normal box mesh and tints it according to its sealed contents' quality.
    void createMeshLocal(NodeType type = NodeType::MTILES_NODE) override;
private:
    //! \brief The fixed contained item or unresolved random-quality token.
    std::unique_ptr<ItemInstance> mItem;
    std::string mRandomQuality;
    //! \brief The quality, without content identity, sent to a client.
    Quality mClientQuality = Quality::common;
};

#endif
