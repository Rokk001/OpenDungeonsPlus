#ifndef ITEMINSTANCE_H
#define ITEMINSTANCE_H

#include "entities/ItemDefinition.h"

#include <memory>

class GameMap;

//! \brief The ghost room goods that travel as items; the level crystal is the soul crystal (mSoulCrystal).
enum class GhostItem : uint32_t { none = 0, ectoplasm = 1, manaCrystal = 2, researchBook = 3 };

//! \brief A rolled item, potion or soul crystal owned by its current holder.
class ItemInstance
{
public:
    //! \brief Creates an empty instance with no ownership flags or Epic registration.
    ItemInstance() : mQuality(Quality::poor), mEpicSerial(0), mMerchantGoods(false), mGifted(false), mSoulCrystal(false),
        mGhostItem(GhostItem::none), mGhostTarget(-1) {}
    //! \brief Rolls the ordered bonuses of a definition using the server random generator.
    static std::unique_ptr<ItemInstance> create(const ItemDefinition& definition, Quality quality);
    //! \brief Creates the catalogue Poor item for an equipment slot.
    static std::unique_ptr<ItemInstance> createPoor(const std::string& slot);
    //! \brief Creates one unstacked potion.
    static std::unique_ptr<ItemInstance> createPotion(const std::string& id);
    //! \brief Creates a bonus-free soul crystal for an inventory slot.
    static std::unique_ptr<ItemInstance> createSoulCrystal();
    //! \brief Creates one ghost room good (ectoplasm, mana crystal or research book) without bonuses.
    static std::unique_ptr<ItemInstance> createGhostItem(GhostItem kind);
    //! \brief True for ectoplasm, mana crystals, research books and level (soul) crystals.
    bool isGhostGood() const { return mSoulCrystal || mGhostItem != GhostItem::none; }
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
    std::string getDisplayName(const GameMap* map = nullptr) const;
    //! \brief Returns the base merchant price, including rolled bonus count pricing.
    double getPrice(const GameMap* map = nullptr) const;
    //! \brief Returns the minimum required level.
    uint32_t getLevelMin(const GameMap* map = nullptr) const;
    //! \brief Returns the ItemImages entry for this instance.
    std::string getImageName() const;
    //! \brief Builds the shared quality-coloured name, bonus and effect tooltip.
    std::string describe(const GameMap* map = nullptr) const;

    //! \brief Catalogue id of the item line, or the potion id for a consumable.
    std::string mDefinitionId;
    //! \brief Rolled equipment quality; potions carry the neutral Poor value.
    Quality mQuality;
    //! \brief Rolled bonus kind and amount pairs, in catalogue order.
    std::vector<std::pair<std::string, double>> mBonuses;
    //! \brief Fixed special effects and their values.
    std::vector<std::pair<std::string, double>> mEffects;
    //! \brief Map-wide Epic serial, zero for all other qualities.
    uint32_t mEpicSerial;
    //! \brief True while this instance belongs to merchant stock or sealed fallen goods.
    bool mMerchantGoods;
    //! \brief Records the keeper's gift provenance for reactions and handling.
    bool mGifted;
    //! \brief Nonempty only for a potion instance; potion instances have no rolled bonuses.
    std::string mPotionId;
    //! \brief Identifies a soul crystal independently of equipment quality.
    bool mSoulCrystal;
    //! \brief The ghost room good this instance is, none for every other item.
    GhostItem mGhostItem;
    //! \brief For ectoplasm: the apparatus (GhostProduct value) chosen when a worker picked it up, -1 if none.
    int32_t mGhostTarget;
};

#endif
