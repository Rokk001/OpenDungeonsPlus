#ifndef CREATUREEFFECTPOTION_H
#define CREATUREEFFECTPOTION_H

#include "creatureeffect/CreatureEffect.h"

//! \brief Holds a timed potion contribution and removes only that contribution when it ends.
class CreatureEffectPotion : public CreatureEffect
{
public:
    //! \brief Creates a potion lasting nbTurns, with the definition's kind and value.
    CreatureEffectPotion(double nbTurns, const std::string& kind, double value);
    //! \brief Creates a potion effect for stream import.
    CreatureEffectPotion();
    //! \brief Returns the registered effect name.
    const std::string& getEffectName() const override;
    //! \brief Returns the potion kind, also used to distinguish duration refreshes.
    const std::string& getKind() const;
    //! \brief Installs the contribution immediately, including restored saved effects.
    void startEffect(Creature& creature) override;
    //! \brief Removes the contribution without disturbing other effects.
    void releaseEffect(Creature& creature) override;
    //! \brief Saves the duration, potion kind and value.
    void exportToStream(std::ostream& os) const override;
    //! \brief Reads a saved timed potion.
    bool importFromStream(std::istream& is) override;
    //! \brief Applies immediate healing, mana restoration or thawing from a consumed potion.
    static void applyInstant(Creature& creature, const std::string& kind, double value);

protected:
    //! \brief Maintains the contribution and applies the active share of regeneration.
    void applyEffect(Creature& creature) override;

private:
    //! \brief Kind from the potion definition, distinct for each refreshable buff.
    std::string mKind;
    //! \brief Factor or healing percentage from the potion definition.
    double mValue;
};

#endif // CREATUREEFFECTPOTION_H
