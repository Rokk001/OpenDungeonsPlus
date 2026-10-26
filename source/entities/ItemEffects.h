#ifndef ITEMEFFECTS_H
#define ITEMEFFECTS_H

#include <string>

class Creature;
class GameEntity;

//! \brief Names and mechanics shared by equipment effects and their combat hooks.
namespace ItemEffects
{
//! \brief Returns whether the id names an equipment effect.
bool exists(const std::string& id);
//! \brief Returns the player-visible name of an equipment effect, or the id when unknown.
std::string getName(const std::string& id);
//! \brief Returns the critical damage multiplier including Executioner.
double criticalMultiplier(const Creature& wearer);
//! \brief Returns the damage factor against buildings or creatures of a hero seat.
double targetDamageFactor(const Creature& wearer, const GameEntity& target);
//! \brief Applies landed-blow effects and melee retaliation using actual damage dealt.
//! \param retaliationPercent Target's Spiked and Spikes sum captured before damage can drop its items.
void onHit(Creature& attacker, Creature& target, double damage, bool melee, double retaliationPercent);
//! \brief Heals the attributed wearer through Lifeblood once for damage dealt to a creature.
void onDamageDealt(GameEntity* source, Creature& target, double damage);
//! \brief Returns the factor reducing a negative modifier by the wearer's Iron Will.
double moodModifier(const Creature& wearer, double points);
//! \brief Returns an item's multiplicative bonus expressed in percent.
double increaseFactor(const Creature& wearer, const std::string& id);
//! \brief Returns the remaining fraction after the named resistance, clamped at zero.
double remainingFactor(const Creature& wearer, const std::string& id);
}

#endif // ITEMEFFECTS_H
