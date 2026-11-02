#ifndef AIITEMS_H
#define AIITEMS_H

class KeeperAI;
struct AiEvent;

namespace ITEMS
{
//! \brief Records catalogue rows without a keeper command.
void classNRows(KeeperAI& ai);
//! \brief Uses held specials when their capacity, mood or combat condition applies; flags describe the current trigger.
void useStoredSpecial(KeeperAI& ai, const AiEvent& event, bool fightSession, bool periodicLook, bool afterSpell);
//! \brief Buys the highest-priced affordable gift for the strongest fighter on claimed ground.
void buyForStrongest(KeeperAI& ai);
}

#endif // AIITEMS_H
