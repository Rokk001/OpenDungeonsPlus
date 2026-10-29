#ifndef AIROOMS_H
#define AIROOMS_H

#include "rooms/RoomType.h"
#include <cstdint>
#include <vector>

class AiKnowledge;
class KeeperAI;
class Tile;

namespace ROOMS
{
//! \brief Keeps pending room placement and the first-room mistake with this keeper.
struct State
{
    RoomType pendingType = RoomType::nullRoomType;
    std::vector<Tile*> pendingTiles;
    int dormitoryFirst = -1;
    int hatcheryFirst = -1;
    Tile* breakthrough = nullptr;
    int bedPopulation = -1;
    double bedDue = -1.0;
    double foodDue = -1.0;
    bool restored = false;
};
//! \brief Binds this keeper's economy-room events and periodic looks.
void bind(KeeperAI& ai);
//! \brief Builds the next affordable researched entry in the configured room order.
void buildNext(KeeperAI& ai);
//! \brief Watches bed capacity and extends the dormitory.
void bedWatch(KeeperAI& ai);
//! \brief Watches food coverage and extends the hatchery.
void hatcheryWatch(KeeperAI& ai);
//! \brief Checks the tavern payer against the wage reserve.
void auditTavern(KeeperAI& ai);
//! \brief Chooses casino payout from treasury and creature mood.
void auditCasino(KeeperAI& ai);
//! \brief Starts the ordered room look when dirt is noticed.
void toiletWatch(KeeperAI& ai);
//! \brief Chooses the merchant mode and margin from creature mood.
void auditMerchant(KeeperAI& ai);
//! \brief Chooses the configured laboratory potion mode.
void auditLab(KeeperAI& ai);
//! \brief Checks the infirmary payer, discharge threshold and healing switch.
void auditInfirmary(KeeperAI& ai);
//! \brief Chooses ectoplasm product and revival from actual keeper resources.
void ghostProduct(KeeperAI& ai);
//! \brief Checks the spa payer against the wage reserve.
void auditSpa(KeeperAI& ai);
//! \brief Sacrifices a complete recipe of surplus creatures.
void templeSacrifice(KeeperAI& ai);
//! \brief Builds a bridge when a known route becomes sufficiently shorter.
void bridgeWatch(KeeperAI& ai);
//! \brief Returns a shortest known path length or -1 when unreachable.
int knownPathLength(const AiKnowledge& knowledge, Tile* from, Tile* to, bool waterLavaPassable);
//! \brief Restarts the strict room order after a room is lost.
void rebuildLost(KeeperAI& ai);
//! \brief Selects and prepares one room block, returning whether work is pending.
bool placeRoom(KeeperAI& ai, RoomType type, uint32_t tiles);
//! \brief Audits every room setting at the configured long look.
void auditSettings(KeeperAI& ai);
}

#endif // AIROOMS_H
