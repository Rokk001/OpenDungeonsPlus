#ifndef CREATUREEFFECTBLEED_H
#define CREATUREEFFECTBLEED_H

#include "creatureeffect/CreatureEffect.h"

//! \brief Applies the absolute damage of a bleeding wound over five turns.
class CreatureEffectBleed : public CreatureEffect
{
public:
    //! \brief Creates a five-turn wound from the total damage and its attacker's name.
    CreatureEffectBleed(double damage, const std::string& attackerName);
    //! \brief Creates a wound to read from a saved stream.
    CreatureEffectBleed();
    //! \brief Returns the registered effect name.
    const std::string& getEffectName() const override;
    //! \brief Writes the remaining duration, damage per turn and attacker.
    void exportToStream(std::ostream& os) const override;
    //! \brief Reads the remaining duration, damage per turn and attacker.
    bool importFromStream(std::istream& is) override;

protected:
    //! \brief Deals one turn's share of absolute damage to the living target.
    void applyEffect(Creature& creature) override;

private:
    //! \brief Absolute damage inflicted in each complete turn.
    double mDamagePerTurn;
    //! \brief Name used to retain kill attribution while the attacker exists.
    std::string mAttackerName;
};

#endif // CREATUREEFFECTBLEED_H
