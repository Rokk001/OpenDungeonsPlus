#ifndef ITEMDEFINITION_H
#define ITEMDEFINITION_H

#include <array>
#include <cstdint>
#include <iosfwd>
#include <string>
#include <utility>
#include <vector>

class ODPacket;

//! \brief Quality shared by item definitions, instances and their visual presentation.
enum class Quality : int32_t { poor, common, rare, epic };

//! \brief Returns the spelling used in definition files and player displays.
const std::string& qualityName(Quality quality);
//! \brief Parses a quality name without accepting unknown qualities.
bool parseQuality(const std::string& name, Quality& quality);
//! \brief Writes a quality as an int32 value.
ODPacket& operator <<(ODPacket& packet, Quality quality);
//! \brief Reads a quality encoded as an int32 value.
ODPacket& operator >>(ODPacket& packet, Quality& quality);

//! \brief One ordered bonus and its inclusive roll range.
struct ItemBonusRange
{
    //! \brief Creates an empty roll range.
    ItemBonusRange() : mMinimum(0.0), mMaximum(0.0) {}
    std::string mKind;
    double mMinimum;
    double mMaximum;
};

//! \brief Values and ordered rolls belonging to one quality of an item line.
struct ItemQuality
{
    //! \brief Creates an unavailable quality until it is read from a definition.
    ItemQuality() : mAvailable(false), mLevelMin(1), mPrice(0.0), mPricePerBonus(0.0),
        mBonusMinimum(0), mBonusMaximum(0) {}
    bool mAvailable;
    std::string mDisplay;
    uint32_t mLevelMin;
    double mPrice;
    double mPricePerBonus;
    uint32_t mBonusMinimum;
    uint32_t mBonusMaximum;
    std::vector<ItemBonusRange> mBonuses;
    std::vector<std::pair<std::string, double>> mEffects;
};

//! \brief Immutable item line with an ordered bonus catalogue for each quality.
class ItemDefinition
{
public:
    //! \brief Reads the contents after an opening Item tag, returning null for invalid data.
    static ItemDefinition* load(std::stringstream& stream);
    //! \brief Returns the unique definition id.
    const std::string& getId() const { return mId; }
    //! \brief Returns the equipment slot named by the catalogue.
    const std::string& getSlot() const { return mSlot; }
    //! \brief Returns the skill path for which the line was made.
    const std::string& getPath() const { return mPath; }
    //! \brief Returns the group or the family marker.
    const std::string& getGroup() const { return mGroup; }
    //! \brief Returns the required spawn weapon type, or none.
    const std::string& getWeaponClass() const { return mWeaponClass; }
    //! \brief Returns the representative equipment used to preview a weapon line.
    const std::string& getPoorEquipment() const { return mPoorEquipment; }
    //! \brief Returns one quality's bonuses, price and presentation.
    const ItemQuality& getQuality(Quality quality) const;
    //! \brief Writes a complete definition block for network transfer.
    void exportToStream(std::ostream& stream) const;
    //! \brief Transfers a definition as its canonical textual block.
    void exportToPacket(ODPacket& packet) const;
    //! \brief Reads a network definition without adopting malformed data.
    static ItemDefinition* loadFromPacket(ODPacket& packet);

private:
    std::string mId;
    std::string mSlot;
    std::string mPath;
    std::string mGroup;
    std::string mWeaponClass;
    std::string mPoorEquipment;
    std::array<ItemQuality, 4> mQualities;
};

#endif
