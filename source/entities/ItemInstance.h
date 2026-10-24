#ifndef ITEMINSTANCE_H
#define ITEMINSTANCE_H

#include "entities/ItemDefinition.h"

#include <memory>

//! \brief A rolled item or a single potion, owned by its current holder.
class ItemInstance
{
public:
    //! \brief Creates an empty instance with no ownership flags or Epic registration.
    ItemInstance() : mQuality(Quality::poor), mEpicSerial(0), mMerchantGoods(false), mGifted(false) {}
    //! \brief Rolls the ordered bonuses of a definition using the server random generator.
    static std::unique_ptr<ItemInstance> create(const ItemDefinition& definition, Quality quality);
    //! \brief Creates the catalogue Poor item for an equipment slot.
    static std::unique_ptr<ItemInstance> createPoor(const std::string& slot);
    //! \brief Creates one unstacked potion.
    static std::unique_ptr<ItemInstance> createPotion(const std::string& id);
    //! \brief Writes one complete instance line without a trailing newline.
    void exportToStream(std::ostream& stream) const;
    //! \brief Reads an instance without modifying the destination on a short or invalid line.
    //! \param firstId An already consumed definition id, or empty to read it from the stream.
    bool importFromStream(std::istream& stream, const std::string& firstId = std::string());
    //! \brief Writes the same fields as the save line using fixed-width counters.
    void exportToPacket(ODPacket& packet) const;
    //! \brief Reads a complete packet instance transactionally.
    bool importFromPacket(ODPacket& packet);
    //! \brief Returns the sum of one bonus kind on this instance.
    double getBonus(const std::string& kind) const;
    //! \brief Returns the sum of one special effect on this instance.
    double getEffect(const std::string& id) const;
    //! \brief Returns the catalogue name of the item or potion.
    std::string getDisplayName() const;
    //! \brief Returns the base merchant price, including rolled bonus count pricing.
    double getPrice() const;
    //! \brief Returns the minimum required level.
    uint32_t getLevelMin() const;
    //! \brief Returns the ItemImages entry for this instance.
    std::string getImageName() const;
    //! \brief Builds the shared quality-coloured name, bonus and effect tooltip.
    std::string describe() const;

    std::string mDefinitionId;
    Quality mQuality;
    std::vector<std::pair<std::string, double>> mBonuses;
    std::vector<std::pair<std::string, double>> mEffects;
    uint32_t mEpicSerial;
    bool mMerchantGoods;
    bool mGifted;
    std::string mPotionId;
};

#endif
