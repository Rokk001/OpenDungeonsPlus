#include "ai/AiCare.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/AiSettings.h"
#include "ai/KeeperAI.h"
#include "creatureaction/CreatureAction.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "rooms/Room.h"
#include "rooms/RoomType.h"
#include "utils/Random.h"
#include "utils/ConfigManager.h"
#include "ODApplication.h"
#include "spells/SpellType.h"

#include <OgreVector2.h>
#include <OgreVector3.h>

#include <algorithm>
#include <vector>

namespace
{
//! \brief Returns living own fighters the keeper can move without interrupting possession or captivity.
std::vector<Creature*> ownFighters(KeeperAI& ai)
{
    std::vector<Creature*> fighters;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
    {
        if(creature->isAlive() && !creature->isKo() && creature->getIsOnMap() &&
           !creature->isInContainment() && !creature->isPossessed() &&
           !creature->getDefinition()->isWorker() && !creature->getDefinition()->isChampion())
            fighters.push_back(creature);
    }
    return fighters;
}

//! \brief Tests the idle action list specified for hand placement into the training hall.
bool idle(const Creature& creature)
{
    const CreatureActionType busy[] = {CreatureActionType::useRoom, CreatureActionType::sleep,
        CreatureActionType::eatChicken, CreatureActionType::fight, CreatureActionType::flee,
        CreatureActionType::searchFood, CreatureActionType::findHome};
    for(CreatureActionType action : busy)
        if(creature.isActionInList(action))
            return false;
    return true;
}

//! \brief Orders fighters by the current HP times raw damage per second.
bool stronger(const Creature* left, const Creature* right)
{
    return left->getHP() * left->getRawDamagePerSecond() > right->getHP() * right->getRawDamagePerSecond();
}

//! \brief Finds an own room with space for this creature.
Room* availableRoom(KeeperAI& ai, Creature* creature, RoomType type)
{
    for(Room* room : ai.getGameMap().getRoomsByTypeAndSeat(type, ai.getControlledPlayer().getSeat()))
        if(room->hasOpenCreatureSpot(creature) && !room->getCoveredTiles().empty())
            return room;
    return nullptr;
}

//! \brief Schedules the human pickup and drop path onto claimed room ground.
void moveToRoom(KeeperAI& ai, Creature* creature, Room* room)
{
    if(room == nullptr)
        return;
    for(Tile* tile : room->getCoveredTiles())
        if(tile->isClaimedForSeat(ai.getControlledPlayer().getSeat()) && !tile->isFullTile())
        {
            ACTS::moveCreature(ai, creature, tile);
            return;
        }
}
}

//! \brief Starts a finite mistake episode using the same interval and symptom-delay distribution as the care model.
void CARE::slapWatch(KeeperAI& ai, SlapState& state)
{
    // AI row D04
    const double now = ai.getMind().now();
    for(Creature* creature : ownFighters(ai))
        if(creature->isBrawling())
            ACTS::slap(ai, creature);
    if(now < state.nextCheck || now < state.episodeUntil)
        return;
    ConfigManager& config = ConfigManager::getSingleton();
    state.nextCheck = now + config.getAiConfigDouble("SlapMistakePauseSeconds");
    if(ownFighters(ai).empty() || !ai.getMind().slip("D04"))
        return;
    const AiSettings& settings = ai.getSettings();
    const AiMath::DelayParams params = {settings.rho, settings.pi, settings.scanPeriod,
        config.getAiConfigDouble("SymptomScanFactor"), config.getAiConfigDouble("PeriodicMinDelay"),
        config.getAiConfigDouble("ActionLatencyMean"), config.getAiConfigDouble("ActionLatencySd")};
    const AiMath::Uniform01 uniform = std::bind(&Random::Double, 0.0, 1.0);
    const double delay = AiMath::reactionDelay(AiMath::ReactionKind::symptom, params, uniform);
    state.interval = config.getAiConfigDouble("SlapMistakeInterval" + std::to_string(Random::Int(1, 5)));
    state.episodeUntil = now + config.getAiConfigDouble("SlapMistakeDelayFactor") * delay +
        config.getAiConfigDouble("SlapMistakeBaseSeconds");
    state.nextSlap = now + state.interval;
}

//! \brief Applies one due round of a production mistake through the common legality and hand wrappers.
void CARE::slapEpisodeStep(KeeperAI& ai, SlapState& state)
{
    const double now = ai.getMind().now();
    if(now >= state.episodeUntil || now < state.nextSlap || state.interval <= 0.0)
        return;
    state.nextSlap = now + state.interval;
    for(Creature* creature : ownFighters(ai))
        ACTS::slap(ai, creature);
}

//! \brief Selects a defender only for a fight threatening the heart or treasury; D05 and E12 share one decision.
void CARE::possessDefender(KeeperAI& ai, const AiEvent& event)
{
    // AI row D05
    // AI row E12
    if(ai.getControlledPlayer().isPossessing())
        return;
    Room* room = event.tile == nullptr ? nullptr : event.tile->getCoveringRoom();
    if(event.type != AiEventType::HeartCritical &&
       (room == nullptr || (room->getType() != RoomType::dungeonTemple && room->getType() != RoomType::treasury) ||
        room->getSeat() != ai.getControlledPlayer().getSeat()))
        return;
    std::vector<Creature*> fighters = ownFighters(ai);
    if(fighters.empty())
        return;
    std::sort(fighters.begin(), fighters.end(), stronger);
    Creature* target = nullptr;
    if(ai.getMind().slip("D05"))
        target = fighters.back();
    else
        for(Creature* fighter : fighters)
        {
            Tile* tile = fighter->getPositionTile();
            Room* current = tile == nullptr ? nullptr : tile->getCoveringRoom();
            if(fighter->isActionInList(CreatureActionType::fight) ||
               (current != nullptr && (current == room ||
                (event.type == AiEventType::HeartCritical && current->getType() == RoomType::dungeonTemple))))
            {
                target = fighter;
                break;
            }
        }
    if(target != nullptr)
        ACTS::castSpell(ai, SpellType::possess, target);
}

//! \brief Uses the possessed creature's existing movement and attack checks and ends at the configured HP share.
void CARE::possessionStep(KeeperAI& ai, double& nextControl)
{
    Player& player = ai.getControlledPlayer();
    if(!player.isPossessing() || ai.getMind().now() < nextControl)
        return;
    Creature* creature = ai.getGameMap().getCreature(player.getPossessedCreatureName());
    if(creature == nullptr || creature->getPossessor() != &player)
        return;
    if(creature->getHP() < creature->getMaxHp() *
        ConfigManager::getSingleton().getAiConfigDouble("PossessLeaveHpShare"))
    {
        const std::string name = creature->getName();
        //! \brief Rechecks ownership before applying the human possession-exit command.
        const std::function<void()> leave = [&ai, name]()
        {
            Creature* controlled = ai.getGameMap().getCreature(name);
            if(controlled != nullptr && controlled->getPossessor() == &ai.getControlledPlayer())
                controlled->endPossession();
        };
        nextControl = ai.getMind().exec("possess", 1, ai.getMind().now(), "D05",
            creature->getPositionTile(), "exit:" + name, leave);
        return;
    }
    Creature* nearest = nullptr;
    double distance = 0.0;
    for(Creature* enemy : ai.getGameMap().getCreatures())
    {
        Tile* tile = enemy->getPositionTile();
        if(!enemy->isAlive() || enemy->getSeat() == nullptr || enemy->getSeat() == player.getSeat() ||
           player.getSeat()->isAlliedSeat(enemy->getSeat()) || tile == nullptr)
            continue;
        const std::vector<Seat*>& vision = tile->getSeatsWithVision();
        if(std::find(vision.begin(), vision.end(), player.getSeat()) == vision.end())
            continue;
        const double squared = (enemy->getPosition() - creature->getPosition()).squaredLength();
        if(nearest == nullptr || squared < distance)
        {
            nearest = enemy;
            distance = squared;
        }
    }
    if(nearest == nullptr)
    {
        creature->possessedMove(Ogre::Vector2::ZERO);
        return;
    }
    const std::string name = creature->getName();
    const std::string enemyName = nearest->getName();
    //! \brief Resolves current targets and vision again when the scheduled possession input executes.
    const std::function<void()> control = [&ai, name, enemyName]()
    {
        Creature* controlled = ai.getGameMap().getCreature(name);
        Creature* enemy = ai.getGameMap().getCreature(enemyName);
        if(controlled == nullptr || controlled->getPossessor() != &ai.getControlledPlayer() ||
           enemy == nullptr || !enemy->isAlive() || enemy->getPositionTile() == nullptr)
            return;
        const std::vector<Seat*>& vision = enemy->getPositionTile()->getSeatsWithVision();
        if(std::find(vision.begin(), vision.end(), ai.getControlledPlayer().getSeat()) == vision.end())
            return;
        const Ogre::Vector3 offset = enemy->getPosition() - controlled->getPosition();
        const Ogre::Vector2 aim(offset.x, offset.y);
        controlled->possessedMove(aim);
        controlled->possessedAttack(aim);
    };
    nextControl = ai.getMind().exec("possess", 1, ai.getMind().now(), "D05", nearest->getPositionTile(),
        "control:" + name + ":" + enemyName, control);
}

//! \brief Handles the idle-fighter part of the hand rally; combat and wounded moves belong to the war rows.
void CARE::idleToHall(KeeperAI& ai)
{
    // AI row D06
    std::vector<Creature*> fighters = ownFighters(ai);
    std::sort(fighters.begin(), fighters.end(), stronger);
    if(ai.getMind().slip("D06"))
    {
        for(size_t count = fighters.size(); count > 1; --count)
        {
            const size_t index = static_cast<size_t>(Random::Int(0, static_cast<int>(count) - 1));
            std::swap(fighters[count - 1], fighters[index]);
        }
    }
    for(Creature* creature : fighters)
        if(idle(*creature))
            moveToRoom(ai, creature, availableRoom(ai, creature, RoomType::trainingHall));
}

//! \brief Handles the creature-list look for capped training and lack of work.
void CARE::levelWatch(KeeperAI& ai)
{
    // AI row D08
    if(ai.getMind().slip("D08"))
        return;
    for(Creature* creature : ownFighters(ai))
    {
        bool capped = false;
        for(Room* hall : ai.getGameMap().getRoomsByTypeAndSeat(RoomType::trainingHall,
                ai.getControlledPlayer().getSeat()))
            if(!hall->hasOpenCreatureSpot(creature))
                capped = true;
        Room* destination = capped ? availableRoom(ai, creature, RoomType::arena) : nullptr;
        if(destination == nullptr && idle(*creature))
        {
            destination = availableRoom(ai, creature, RoomType::casino);
            if(destination == nullptr)
                destination = availableRoom(ai, creature, RoomType::temple);
        }
        moveToRoom(ai, creature, destination);
    }
}

//! \brief Handles one mood event, choosing the highest room affinity among rooms with a free place.
void CARE::moodRelief(KeeperAI& ai)
{
    // AI row D09
    if(ai.getMind().slip("D09"))
        return;
    const RoomType types[] = {RoomType::casino, RoomType::tavern, RoomType::spa, RoomType::temple};
    for(Creature* creature : ownFighters(ai))
    {
        if(creature->getMoodValue() < CreatureMoodLevel::Upset)
            continue;
        Room* best = nullptr;
        double likeness = 0.0;
        for(RoomType type : types)
        {
            Room* room = availableRoom(ai, creature, type);
            if(room == nullptr)
                continue;
            const double value = creature->getDefinition()->getRoomAffinity(type).getLikeness();
            if(best == nullptr || value > likeness)
            {
                best = room;
                likeness = value;
            }
        }
        moveToRoom(ai, creature, best);
    }
}

//! \brief Uses the specified cause priority and delegates the resulting row's own decision to the caller.
void CARE::moodPatrol(KeeperAI& ai, const std::function<void(const std::string&, Creature*)>& trigger)
{
    // AI row D07
    if(ai.getMind().slip("D07"))
        return;
    for(Creature* creature : ownFighters(ai))
    {
        if(creature->getMoodValue() < CreatureMoodLevel::Upset)
            continue;
        if(creature->isHungry())
            trigger("B03", creature);
        else if(creature->getHomeTile() == nullptr)
            trigger("B02", creature);
        else if(creature->getGoldFee() > 0.0)
            trigger("A05", creature);
        else
        {
            Tile* tile = creature->getPositionTile();
            Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
            if(room != nullptr && room->getDirtStage() == 3)
                trigger("B10", creature);
            else if(creature->isHurt())
                trigger("J08", creature);
            else if(idle(*creature))
                trigger("D06", creature);
        }
    }
}
