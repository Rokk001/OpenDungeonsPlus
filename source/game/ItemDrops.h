#ifndef ITEMDROPS_H
#define ITEMDROPS_H

#include "entities/ItemInstance.h"

class Creature;
class Weapon;

//! \brief Uses the configured hero/portal probabilities without tuning their values.
namespace ItemDrops
{
//! \brief Outfits a newly spawned hero or portal creature, retaining unwanted items as carried junk.
void outfit(Creature& creature, const std::string& kind);
//! \brief Creates a Poor instance referring to the wearer's existing spawn equipment.
std::unique_ptr<ItemInstance> poorWeapon(const Weapon& weapon);
//! \brief Resolves fixed instance lines and the three random-quality level/editor choices.
std::unique_ptr<ItemInstance> resolve(GameMap& map, const std::string& content);
//! \brief The chance that a hero carries a ghost product: the soul crystal chance times GhostHeroProductFactor, at most 1.
double heroGhostProductChance(double crystalChance);
//! \brief Picks the ghost product a hero carries by the configured weights: mana crystal, research book, level crystal.
//! \param draw A uniform number in [0, 1)
std::unique_ptr<ItemInstance> heroGhostProduct(double draw);
//! \brief Picks one of the three ghost products with equal chance, for a random item bag.
//! \param draw A uniform number in [0, 1)
std::unique_ptr<ItemInstance> randomGhostProduct(double draw);
}

#endif
