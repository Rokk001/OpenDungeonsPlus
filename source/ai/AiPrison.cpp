#include "ai/AiPrison.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/AiSettings.h"
#include "ai/KeeperAI.h"
#include "entities/Creature.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"
#include "ODApplication.h"

#include <algorithm>
#include <set>

namespace
{
//! \brief Orders prisoners by descending level.
bool higherLevel(const Creature* left, const Creature* right)
{
    return left->getLevel() > right->getLevel();
}

//! \brief Orders prisoners by the time they have already spent in prison.
bool older(const Creature* left, const Creature* right)
{
    return left->getNbTurnsPrison() > right->getNbTurnsPrison();
}
}

//! \brief Handles the prison look or age event; the game alone handles portal filling and conversion results.
void PRIS::tortureStep(KeeperAI& ai, State& state)
{
    // AI row D10
    // AI row G02
    // AI row G04
    Seat* seat = ai.getControlledPlayer().getSeat();
    const std::vector<Room*> rooms = ai.getGameMap().getRoomsByTypeAndSeat(RoomType::torture, seat);
    if(rooms.empty())
        return;
    const double age = ConfigManager::getSingleton().getAiConfigDouble("PrisonWaitMinutes") *
        60.0 * ODApplication::turnsPerSecond;
    std::vector<Creature*> prisoners;
    for(Creature* creature : ai.getGameMap().getCreatures())
        if(creature->getSeatPrison() == seat && creature->isInPrison() && creature->isAlive() &&
           !creature->isKo() && creature->getIsOnMap() && creature->getNbTurnsPrison() >= age &&
           state.triedPrisoners.count(creature->getName()) == 0)
            prisoners.push_back(creature);
    const bool wrongOrder = ai.getMind().slip("G04");
    std::sort(prisoners.begin(), prisoners.end(), wrongOrder ? older : higherLevel);
    for(Creature* prisoner : prisoners)
    {
        Tile* destination = nullptr;
        for(Room* room : rooms)
        {
            if(!room->hasOpenCreatureSpot(prisoner))
                continue;
            for(Tile* tile : room->getCoveredTiles())
                if(tile->isClaimedForSeat(seat) && !tile->isFullTile())
                {
                    destination = tile;
                    break;
                }
            if(destination != nullptr)
                break;
        }
        if(destination == nullptr)
            continue;
        state.triedPrisoners.insert(prisoner->getName());
        const ConfigManager& config = ConfigManager::getSingleton();
        const ConfigManager::AiRowClass* row = config.getAiRowClass("G02");
        if(row == nullptr)
            continue;
        // Each prisoner gets an independent one-time draw; Mind::slip caches one draw per whole event.
        const double probability = AiMath::mistakeProbability(config.getAiConfigDouble("MistakeBaseUnfamiliar"),
            row->mMultiplier, ai.getSettings().mistakeMultiplier, config.getAiConfigDouble("MistakeMin"),
            config.getAiConfigDouble("MistakeMax"));
        if(Random::Double(0.0, 1.0) >= probability)
            ACTS::moveCreature(ai, prisoner, destination);
    }
}

//! \brief Exports the one-time prisoner decisions without choosing conversion or skeleton outcomes.
std::vector<std::string> PRIS::exportDraws(const State& state)
{
    std::vector<std::string> lines;
    for(const std::string& prisoner : state.triedPrisoners)
        lines.push_back("G02 tried " + prisoner);
    return lines;
}

//! \brief Restores one prisoner decision for a loaded seat.
void PRIS::importDraw(State& state, const std::string& name, const std::string& value)
{
    if(name == "tried")
        state.triedPrisoners.insert(value);
}
