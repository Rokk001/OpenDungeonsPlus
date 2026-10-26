#ifndef POTIONDEFINITION_H
#define POTIONDEFINITION_H

#include <cstdint>
#include <iosfwd>
#include <map>
#include <string>
#include <vector>

class ODPacket;

//! \brief Brewing recipe and effect of one consumable potion.
class PotionDefinition
{
public:
    //! \brief Creates an empty recipe ready to be loaded.
    PotionDefinition() : mValue(0.0), mDuration(0.0), mLevelMin(1), mBrewSeconds(0.0), mPrice(0.0) {}
    //! \brief Reads the contents of one Potion block.
    bool importFromStream(std::istream& stream);
    //! \brief Returns the unique potion id.
    const std::string& getId() const { return mId; }
    //! \brief Returns the player-facing potion name.
    const std::string& getDisplay() const { return mDisplay; }
    //! \brief Returns Small, Medium, Large or Single.
    const std::string& getSize() const { return mSize; }
    //! \brief Returns the effect kind to apply when drinking.
    const std::string& getKind() const { return mKind; }
    //! \brief Returns the effect amount or multiplier.
    double getValue() const { return mValue; }
    //! \brief Returns the duration in seconds, zero for instant effects.
    double getDuration() const { return mDuration; }
    //! \brief Returns the minimum level required to use the potion.
    uint32_t getLevelMin() const { return mLevelMin; }
    //! \brief Returns the consumed herb bundle counts.
    const std::map<std::string, uint32_t>& getHerbs() const { return mHerbs; }
    //! \brief Returns the unmodified brewing duration in seconds.
    double getBrewSeconds() const { return mBrewSeconds; }
    //! \brief Returns the merchant's base price.
    double getPrice() const { return mPrice; }
    //! \brief Returns the image entry name.
    const std::string& getImage() const { return mImage; }
    //! \brief Writes the recipe as a complete Potion block.
    void exportToStream(std::ostream& stream) const;
    //! \brief Transfers the complete recipe to a connecting client.
    void exportToPacket(ODPacket& packet) const;
    //! \brief Reads a complete recipe from a network packet.
    bool importFromPacket(ODPacket& packet);

private:
    //! \brief Identity, player-visible name, bottle size and effect kind.
    std::string mId, mDisplay, mSize, mKind;
    //! \brief Effect value and its duration in seconds, preserving fractional values.
    double mValue, mDuration;
    //! \brief Minimum level allowed to drink this size of potion.
    uint32_t mLevelMin;
    //! \brief Herb bundle counts consumed when brewing starts.
    std::map<std::string, uint32_t> mHerbs;
    //! \brief Base brewing time in seconds and merchant price.
    double mBrewSeconds, mPrice;
    //! \brief Image entry used by the potion atlas.
    std::string mImage;
};

//! \brief Growth parameters and appearance of a harvestable herb.
struct HerbDefinition
{
    //! \brief Creates an empty herb definition.
    HerbDefinition() : mGrowSeconds(0.0), mStages(0) {}
    //! \brief Reads the contents of one Herb block.
    bool importFromStream(std::istream& stream);
    //! \brief Writes the complete growth definition.
    void exportToStream(std::ostream& stream) const;
    //! \brief Herb identity, player-visible name and hexadecimal colour.
    std::string mId, mDisplay, mColour;
    //! \brief Growth duration in seconds before research multipliers.
    double mGrowSeconds;
    //! \brief Research gate, or none when available from the start.
    std::string mResearch;
    //! \brief Number of growth meshes defined for the herb.
    uint32_t mStages;
};

#endif
