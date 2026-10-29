#ifndef AIECONOMY_H
#define AIECONOMY_H

class KeeperAI;

namespace ECON
{
//! \brief Keeps the single wage-reserve draw of the current payday cycle.
struct EconomyState
{
    double reserveSlipAt = -1.0;
    double reserveUntil = -1.0;
    bool restored = false;
};
//! \brief Registers economy looks, symptoms and persistent reserve draws.
void bind(KeeperAI& ai);
//! \brief Returns next payday's wages plus wages still owed.
double wageBill(KeeperAI& ai);
//! \brief Refills the known mining queue nearest an own treasury.
void digQueueWatch(KeeperAI& ai);
//! \brief Opens known ground when no adjacent land remains to claim.
void claimWatch(KeeperAI& ai);
//! \brief Summons a worker when the configured mana and income permit it.
void summonWatch(KeeperAI& ai);
//! \brief Checks the common purchase margin and current wage reserve.
bool walletGate(KeeperAI& ai, double cost);
//! \brief Creates gold for the wage bill, or spends surplus mana when requested.
void castCreateGold(KeeperAI& ai, bool surplus = false);
//! \brief Adds treasury capacity after the two planned treasuries exist.
void goldCapacityWatch(KeeperAI& ai);
//! \brief Spends excess mana on the first useful economy spell.
void manaCapWatch(KeeperAI& ai);
//! \brief Sells redundant room blocks and traps away from entrances.
void sellObsolete(KeeperAI& ai);
}

#endif
