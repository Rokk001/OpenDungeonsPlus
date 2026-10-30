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
#include <functional>
#include <set>
#include <vector>

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

//! \brief Picks up a prisoner if the current keeper rules still permit it.
void PRIS::pickup(KeeperAI& ai, Tile*, const std::string& name)
{
    Player& player = ai.getControlledPlayer();
    Creature* creature = ai.getGameMap().getCreature(name);
    if(creature != nullptr && creature->isAlive() && creature->isInPrison() &&
       creature->getSeatPrison() == player.getSeat() && creature->tryPickup(player.getSeat()))
        player.pickUpEntity(creature);
}

//! \brief Rechecks room capacity before dropping and allows retry after failure.
void PRIS::drop(KeeperAI& ai, State& state, Tile* tile, const std::string& name)
{
    Player& player = ai.getControlledPlayer();
    state.pendingPrisoners.erase(name);
    Creature* creature = ai.getGameMap().getCreature(name);
    if(creature == nullptr || tile == nullptr)
        return;
    Room* room = tile->getCoveringRoom();
    const unsigned int index = player.getHandIndex(GameEntityType::creature, name);
    if(room != nullptr && room->getType() == RoomType::torture && room->getSeat() == player.getSeat() &&
       room->hasOpenCreatureSpot(creature) && index < player.numObjectsInHand() && player.isDropHandPossible(tile, index))
        player.dropHand(tile, index);
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
        if(creature->isAlive() && !creature->isKo() &&
           ((creature->getSeatPrison() == seat && creature->isInPrison() && creature->getIsOnMap() &&
             (creature->getNbTurnsPrison() >= age || state.acceptedPrisoners.count(creature->getName()) != 0)) ||
            (state.acceptedPrisoners.count(creature->getName()) != 0 && ai.getControlledPlayer().getHandIndex(GameEntityType::creature, creature->getName()) <
                ai.getControlledPlayer().numObjectsInHand())) &&
           state.triedPrisoners.count(creature->getName()) == 0 && state.pendingPrisoners.count(creature->getName()) == 0)
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
        if(state.acceptedPrisoners.count(prisoner->getName()) == 0)
        {
            const ConfigManager& config = ConfigManager::getSingleton();
            const ConfigManager::AiRowClass* row = config.getAiRowClass("G02");
            if(row == nullptr)
                continue;
            // Each prisoner gets an independent one-time draw; Mind::slip caches one draw per whole event.
            const double probability = AiMath::mistakeProbability(config.getAiConfigDouble("MistakeBaseUnfamiliar"),
                row->mMultiplier, ai.getSettings().mistakeMultiplier, config.getAiConfigDouble("MistakeMin"),
                config.getAiConfigDouble("MistakeMax"));
            if(Random::Double(0.0, 1.0) < probability)
            {
                state.triedPrisoners.insert(prisoner->getName());
                continue;
            }
            state.acceptedPrisoners.insert(prisoner->getName());
        }
        if(destination == nullptr)
            continue;
        const std::string name = prisoner->getName();
        state.pendingPrisoners.insert(name);
        Mind& mind = ai.getMind();
        if(ai.getControlledPlayer().getHandIndex(GameEntityType::creature, name) >= ai.getControlledPlayer().numObjectsInHand())
            mind.exec("pickup", 1, mind.now(), "G02", nullptr, name,
                std::bind(&PRIS::pickup, std::ref(ai), static_cast<Tile*>(nullptr), name));
        mind.exec("drop", 1, mind.now(), "G02", destination, name,
            std::bind(&PRIS::drop, std::ref(ai), std::ref(state), destination, name));
    }
}

//! \brief Restores one prisoner decision for a loaded seat.
void PRIS::importDraw(State& state, const std::string& name, const std::string& value)
{
    if(name == "tried")
        state.triedPrisoners.insert(value);
    else if(name == "accepted")
        state.acceptedPrisoners.insert(value);
    else if(name == "pending")
        state.pendingPrisoners.insert(value);
}
