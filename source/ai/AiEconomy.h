#ifndef AIECONOMY_H
#define AIECONOMY_H

#include "rooms/RoomType.h"
#include <cstdint>
#include <vector>

class KeeperAI;
class Tile;

namespace ECON
{
//! \brief Records a successful room action independently of merged room objects.
struct RoomBlock
{
    RoomType type = RoomType::nullRoomType;
    uint32_t plannedTiles = 0;
    std::vector<Tile*> tiles;
};
//! \brief Keeps the single wage-reserve draw of the current payday cycle.
struct EconomyState
{
    double reserveSlipAt = -1.0;
    double reserveUntil = -1.0;
    bool restored = false;
    bool blocksRestored = false;
    std::vector<RoomBlock> roomBlocks;
};
//! \brief Records the tiles built by one successful room action in chronological order.
void recordRoomBlock(KeeperAI& ai, RoomType type, uint32_t plannedTiles, const std::vector<Tile*>& tiles);
//! \brief Forgets room tiles when they are removed or transferred to another keeper.
void forgetRoomTiles(KeeperAI& ai, const std::vector<Tile*>& tiles);
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
