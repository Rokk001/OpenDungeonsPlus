#include "creatureeffect/CreatureEffectBleed.h"

#include "creatureeffect/CreatureEffectManager.h"
#include "entities/Creature.h"
#include "gamemap/GameMap.h"

#include <ostream>

namespace
{
static const std::string BLEED_NAME = "Bleed";
static const double BLEED_TURNS = 5.0;

//! \brief Creates bleeding wounds when saved effects are loaded.
class CreatureEffectBleedFactory : public CreatureEffectFactory
{
    //! \brief Creates a wound for stream import.
    CreatureEffect* createCreatureEffect() const override
    { return new CreatureEffectBleed; }
    //! \brief Returns the factory's effect name.
    const std::string& getCreatureEffectName() const override
    { return BLEED_NAME; }
};

static CreatureEffectRegister reg(new CreatureEffectBleedFactory);
}

//! \brief Spreads a landed blow's additional damage evenly over five turns.
CreatureEffectBleed::CreatureEffectBleed(double damage, const std::string& attackerName) :
    CreatureEffect(BLEED_TURNS, ""),
    mDamagePerTurn(damage / BLEED_TURNS),
    mAttackerName(attackerName)
{
    setSourceId("item:Bleed");
}

//! \brief Initialises an empty saved wound.
CreatureEffectBleed::CreatureEffectBleed() :
    CreatureEffect(),
    mDamagePerTurn(0.0)
{
    setSourceId("item:Bleed");
}

//! \brief Returns the factory name of this wound.
const std::string& CreatureEffectBleed::getEffectName() const
{ return BLEED_NAME; }

//! \brief Deals only the active fraction of the last turn's damage.
void CreatureEffectBleed::applyEffect(Creature& creature)
{
    if(!creature.isAlive() || creature.getPositionTile() == nullptr)
        return;
    Creature* attacker = creature.getGameMap()->getCreature(mAttackerName);
    creature.takeDamage(attacker, mDamagePerTurn * getTurnFraction(),
        0.0, 0.0, 0.0, creature.getPositionTile(), false);
}

//! \brief Saves the wound and the source needed for damage attribution.
void CreatureEffectBleed::exportToStream(std::ostream& os) const
{
    CreatureEffect::exportToStream(os);
    os << '\t' << mDamagePerTurn << '\t' << (mAttackerName.empty() ? "none" : mAttackerName);
}

//! \brief Loads a complete wound without changing it on a truncated record.
bool CreatureEffectBleed::importFromStream(std::istream& is)
{
    if(!CreatureEffect::importFromStream(is))
        return false;
    double damage = 0.0;
    std::string attacker;
    if(!(is >> damage >> attacker) || damage < 0.0)
        return false;
    mDamagePerTurn = damage;
    mAttackerName = attacker == "none" ? "" : attacker;
    return true;
}
