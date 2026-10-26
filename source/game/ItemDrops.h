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
}

#endif
