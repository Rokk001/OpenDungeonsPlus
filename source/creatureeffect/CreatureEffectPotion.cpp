#include "creatureeffect/CreatureEffectPotion.h"

#include "utils/ConfigManager.h"

#include "creatureeffect/CreatureEffectManager.h"
#include "entities/Creature.h"
#include "ODApplication.h"

#include <ostream>

namespace
{
static const std::string POTION_NAME = "Potion";
static const double PERCENT = 100.0;

//! \brief Restores potion effects through the regular effect factory.
class CreatureEffectPotionFactory : public CreatureEffectFactory
{
    //! \brief Creates an effect for stream import.
    CreatureEffect* createCreatureEffect() const override
    { return new CreatureEffectPotion; }
    //! \brief Returns the factory's effect name.
    const std::string& getCreatureEffectName() const override
    { return POTION_NAME; }
};

static CreatureEffectRegister reg(new CreatureEffectPotionFactory);
}

//! \brief Keeps potion kinds as separate refreshable sources.
CreatureEffectPotion::CreatureEffectPotion(double nbTurns, const std::string& kind, double value) :
    CreatureEffect(nbTurns, ""),
    mKind(kind),
    mValue(value)
{
    setSourceId("potion:" + mKind);
}

//! \brief Initialises a potion to read from a save.
CreatureEffectPotion::CreatureEffectPotion() :
    CreatureEffect(),
    mValue(0.0)
{}

//! \brief Returns the effect factory name.
const std::string& CreatureEffectPotion::getEffectName() const
{ return POTION_NAME; }

//! \brief Returns the kind that distinguishes timed potion buffs.
const std::string& CreatureEffectPotion::getKind() const
{ return mKind; }

//! \brief Installs the potion's contribution before the next creature action.
void CreatureEffectPotion::startEffect(Creature& creature)
{
    creature.setPotionContribution(this, mKind, mValue);
}

//! \brief Removes only this potion's reversible stat contribution.
void CreatureEffectPotion::releaseEffect(Creature& creature)
{
    creature.removePotionContribution(this);
}

//! \brief Heals per active turn while leaving other buffs in the creature's contribution map.
void CreatureEffectPotion::applyEffect(Creature& creature)
{
    if(!creature.isAlive())
        return;
    creature.setPotionContribution(this, mKind, mValue);
    if(mKind == "HealPerTenSeconds")
        creature.heal(mValue / PERCENT * creature.getMaxHp() * getTurnFraction()
            / (ConfigManager::getSingleton().getEquipmentConfigDoubleOrDefault("PotionRegenSeconds", 10.0) * ODApplication::turnsPerSecond));
}

//! \brief Saves the reversible potion contribution after the common effect fields.
void CreatureEffectPotion::exportToStream(std::ostream& os) const
{
    CreatureEffect::exportToStream(os);
    os << '\t' << mKind << '\t' << mValue;
}

//! \brief Restores a complete potion and its duration-refresh source.
bool CreatureEffectPotion::importFromStream(std::istream& is)
{
    if(!CreatureEffect::importFromStream(is))
        return false;
    std::string kind;
    double value = 0.0;
    if(!(is >> kind >> value))
        return false;
    mKind = kind;
    mValue = value;
    setSourceId("potion:" + mKind);
    return true;
}

//! \brief Applies the definition's instantaneous resource change to the drinker.
void CreatureEffectPotion::applyInstant(Creature& creature, const std::string& kind, double value)
{
    if(kind == "HealPercent")
        creature.heal(creature.getMaxHp() * value / PERCENT);
    else if(kind == "ManaPercent")
        creature.setCurrentMana(creature.getCurrentMana() + creature.getMaxMana() * value / PERCENT);
    else if(kind == "FullRestore")
    {
        creature.heal(creature.getMaxHp());
        creature.setCurrentMana(creature.getMaxMana());
    }
    else if(kind == "EndFreeze")
        creature.endFreeze();
}
