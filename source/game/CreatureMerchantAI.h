#ifndef CREATUREMERCHANTAI_H
#define CREATUREMERCHANTAI_H

class Creature;
class ItemBagEntity;
class Tile;

//! \brief Shared entry points for creature trading and keeper item gifts.
namespace CreatureMerchantAI
{
//! \brief Tries a sale then a purchase, each with the prescribed thirty-percent idle chance.
//! \return True when a trade action was pushed.
bool decideTrade(Creature& creature);
//! \brief Delivers a keeper gift, or leaves it waiting when its arena fight is running.
//! \return True if the bag was consumed by the recipient.
bool offerGift(ItemBagEntity& bag, Tile& tile);
//! \brief Offers the gifts left in a finished arena to its winning creature.
void collectArenaGifts(Creature& winner);
}

#endif // CREATUREMERCHANTAI_H
