#include "ai/AiCare.h"

#include "ai/AiActions.h"
#include "ai/AiMind.h"
#include "ai/AiSettings.h"
#include "ai/AiEconomy.h"
#include "ai/AiItems.h"
#include "ai/AiRooms.h"
#include "ai/AiWar.h"
#include "ai/KeeperAI.h"
#include "creatureaction/CreatureAction.h"
#include "creaturemood/CreatureMood.h"
#include "entities/Creature.h"
#include "entities/GiftBoxEntity.h"
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
#include <iomanip>
#include <limits>
#include <set>
#include <sstream>
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

//! \brief Returns all living own creatures, workers and champions included, that the keeper can reach with the hand.
std::vector<Creature*> ownCreatures(KeeperAI& ai)
{
    std::vector<Creature*> creatures;
    for(Creature* creature : ai.getGameMap().getCreaturesBySeat(ai.getControlledPlayer().getSeat()))
    {
        if(creature->isAlive() && !creature->isKo() && creature->getIsOnMap() &&
           !creature->isInContainment() && !creature->isPossessed())
            creatures.push_back(creature);
    }
    return creatures;
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

//! \brief Writes persistent relative times without rounding their game-second values.
std::string careNumber(double value)
{
    std::ostringstream out;
    out << std::setprecision(std::numeric_limits<double>::max_digits10) << value;
    return out.str();
}

//! \brief Resolves current targets and vision again when a live or restored possession input executes.
void possessionInput(KeeperAI& ai, Tile*, const std::string& input)
{
    const std::size_t first = input.find(':');
    if(first == std::string::npos)
        return;
    const std::size_t second = input.find(':', first + 1);
    const std::string name = input.substr(first + 1, second == std::string::npos ? second : second - first - 1);
    Creature* controlled = ai.getGameMap().getCreature(name);
    if(controlled == nullptr || controlled->getPossessor() != &ai.getControlledPlayer())
        return;
    if(input.substr(0, first) == "exit")
    {
        controlled->endPossession();
        return;
    }
    Creature* enemy = second == std::string::npos ? nullptr : ai.getGameMap().getCreature(input.substr(second + 1));
    if(enemy == nullptr || !enemy->isAlive() || enemy->getPositionTile() == nullptr ||
       enemy->getSeat() == nullptr || ai.getControlledPlayer().getSeat()->isAlliedSeat(enemy->getSeat()))
        return;
    const std::vector<Seat*>& vision = enemy->getPositionTile()->getSeatsWithVision();
    if(std::find(vision.begin(), vision.end(), ai.getControlledPlayer().getSeat()) == vision.end())
        return;
    const Ogre::Vector3 offset = enemy->getPosition() - controlled->getPosition();
    const Ogre::Vector2 aim(offset.x, offset.y);
    controlled->possessedMove(aim);
    controlled->possessedAttack(aim);
}
}

//! \brief Binds only this owner's callbacks, leaving shared scheduler and action handlers intact.
CARE::Controller::Controller(KeeperAI& ai) : mAi(ai), mNextControl(0.0), mIdleAt(-1.0), mLoaded(false)
{
    Mind& mind = ai.getMind();
    const ConfigManager& config = ConfigManager::getSingleton();
    const double reference = config.getAiConfigDouble("ReferenceScanPeriod");
    mind.onLook("D04", config.getAiConfigDouble("LookFactorPlan"), std::bind(&Controller::planLook, this));
    mind.onLook("D06", config.getAiConfigDouble("LookFactorScan"), std::bind(&Controller::scanLook, this));
    mind.onLook("G02", config.getAiConfigDouble("LookPeriod60") / reference, std::bind(&Controller::prisonLook, this));
    mind.onLook("H04", config.getAiConfigDouble("LookPeriod600") / reference, std::bind(&Controller::itemsLook, this));
    // HeartCritical reaches D05 through WAR::heartGuard (J05), so one firing draws D05 once.
    mind.onEvent("D05", {AiEventType::Fight},
        std::bind(possessDefender, std::ref(ai), std::placeholders::_1));
    mind.onEvent("D06", {AiEventType::Fight, AiEventType::NoBed, AiEventType::NoFood},
        std::bind(&Controller::idle, this));
    const std::function<void(const std::string&, Creature*)> remedy =
        std::bind(&Controller::need, this, std::placeholders::_1, std::placeholders::_2);
    mind.onEvent("D07", {AiEventType::CreatureMood}, std::bind(moodPatrol, std::ref(ai), remedy));
    mind.onEvent("D09", {AiEventType::CreatureMood}, std::bind(moodRelief, std::ref(ai)));
    mind.onEvent("G02", {AiEventType::PrisonerAge}, std::bind(&Controller::prisonLook, this));
    mind.onEvent("H03", {AiEventType::SpecialStored, AiEventType::Fight, AiEventType::CreatureMood,
        AiEventType::Start, AiEventType::Launch}, std::bind(&Controller::event, this, std::placeholders::_1));
    mind.onPoll("L7Care", AiEventType::PrisonerAge, std::bind(&Controller::poll, this));
    mind.onAction("possess", "D05", std::bind(possessionInput, std::ref(ai),
        std::placeholders::_1, std::placeholders::_2));
    mind.onSave(std::bind(&Controller::save, this, std::placeholders::_1));
}

//! \brief Imports saved episode times and prisoner draws once, before a callback can change them.
void CARE::Controller::load()
{
    if(mLoaded)
        return;
    mLoaded = true;
    const double now = mAi.getMind().now();
    for(const AiMath::AiStateLine& line : mAi.getMind().savedRows())
    {
        if(line.tag != "draw" || line.tokens.size() != 3)
            continue;
        const std::vector<std::string>& tokens = line.tokens;
        if(tokens[0] == "G02")
            PRIS::importDraw(mPrison, tokens[1], tokens[2]);
        else if(tokens[0] == "D04" || tokens[0] == "D05")
        {
            double value = 0.0;
            std::istringstream input(tokens[2]);
            if(!(input >> value))
                continue;
            if(tokens[0] == "D05" && tokens[1] == "nextControl") mNextControl = now + value;
            else if(tokens[0] == "D04" && tokens[1] == "episodeUntil") mSlap.episodeUntil = now + value;
            else if(tokens[0] == "D04" && tokens[1] == "interval") mSlap.interval = value;
            else if(tokens[0] == "D04" && tokens[1] == "nextSlap") mSlap.nextSlap = now + value;
            else if(tokens[0] == "D04" && tokens[1] == "nextCheck") mSlap.nextCheck = now + value;
        }
    }
}

//! \brief Advances existing episodes at the shared poll rate without drawing another reaction or mistake.
bool CARE::Controller::poll()
{
    load();
    slapEpisodeStep(mAi, mSlap);
    possessionStep(mAi, mNextControl);
    // A raised cooldown is the own spell cast after which a held mana box fits again.
    Player& player = mAi.getControlledPlayer();
    const std::size_t count = static_cast<std::size_t>(SpellType::nbSpells);
    bool cast = false;
    if(mCooldowns.size() != count)
        mCooldowns.assign(count, 0);
    for(std::size_t i = 0; i < count; ++i)
    {
        const uint32_t cooldown = player.getSpellCooldownTurns(static_cast<SpellType>(i));
        cast = cast || cooldown > mCooldowns[i];
        mCooldowns[i] = cooldown;
    }
    if(cast && player.getSeat()->getNbStoredSpecials(static_cast<uint32_t>(GiftBoxType::mana)) > 0)
    {
        const AiEvent spell = {AiEventType::SpecialStored, nullptr, nullptr, -1, 0.0, mAi.getMind().now()};
        ITEMS::useStoredSpecial(mAi, spell, !mAi.getWarState().fightOverRaised, false, true);
    }
    return false;
}

//! \brief Runs D04 and D08 once each for their shared creature-list look.
void CARE::Controller::planLook()
{
    load();
    slapWatch(mAi, mSlap);
    levelWatch(mAi);
}

//! \brief Runs D06 and D07 once each inside the same periodic mistake scope.
void CARE::Controller::scanLook()
{
    load();
    idle();
    const std::function<void(const std::string&, Creature*)> remedy =
        std::bind(&Controller::need, this, std::placeholders::_1, std::placeholders::_2);
    moodPatrol(mAi, remedy);
}

//! \brief Shares one torture decision between the prison look and its age symptom.
void CARE::Controller::prisonLook()
{
    load();
    PRIS::tortureStep(mAi, mPrison);
}

//! \brief Evaluates the held-special and merchant rows at the configured long-look interval.
void CARE::Controller::itemsLook()
{
    load();
    const AiEvent look = {AiEventType::SpecialStored, nullptr, nullptr, -1, 0.0, mAi.getMind().now()};
    ITEMS::useStoredSpecial(mAi, look, !mAi.getWarState().fightOverRaised, true, false);
    ITEMS::buyForStrongest(mAi);
}

//! \brief Calls D07's real target row immediately, retaining its own mistake and the parent's reaction.
void CARE::Controller::need(const std::string& row, Creature* creature)
{
    if(row == "B03") ROOMS::hatcheryWatch(mAi);
    else if(row == "B02") ROOMS::bedWatch(mAi);
    else if(row == "A05") ECON::castCreateGold(mAi);
    else if(row == "B10") ROOMS::toiletWatch(mAi);
    else if(row == "D06") idle();
    else if(row == "J08")
    {
        WAR::Env env = {mAi, mAi.getMind(), mAi.getGameMap(), mAi.getControlledPlayer(),
            mAi.getSettings(), mAi.getWarState(), mAi.getMind().now()};
        WAR::restWounded(env, creature);
    }
}

//! \brief Runs D06's idle placement at most once per mind time, so its look and D07's remedy share one pass.
void CARE::Controller::idle()
{
    load();
    const double now = mAi.getMind().now();
    if(now == mIdleAt)
        return;
    mIdleAt = now;
    idleToHall(mAi);
}

//! \brief Uses already perceived combat, mood and assault events without adding a second delay.
void CARE::Controller::event(const AiEvent& event)
{
    load();
    ITEMS::useStoredSpecial(mAi, event,
        event.type == AiEventType::Fight || !mAi.getWarState().fightOverRaised, false, false);
}

//! \brief Replaces only L7-owned records and writes timers relative to the current mind clock.
void CARE::Controller::save(std::vector<AiMath::AiStateLine>& lines)
{
    load();
    for(std::vector<AiMath::AiStateLine>::iterator it = lines.begin(); it != lines.end();)
    {
        if(it->tag == "draw" && !it->tokens.empty() &&
           (it->tokens[0] == "D04" || it->tokens[0] == "D05" || it->tokens[0] == "G02"))
            it = lines.erase(it);
        else
            ++it;
    }
    const double now = mAi.getMind().now();
    lines.push_back({"draw", {"D04", "episodeUntil", careNumber(mSlap.episodeUntil - now)}});
    lines.push_back({"draw", {"D04", "interval", careNumber(mSlap.interval)}});
    lines.push_back({"draw", {"D04", "nextSlap", careNumber(mSlap.nextSlap - now)}});
    lines.push_back({"draw", {"D04", "nextCheck", careNumber(mSlap.nextCheck - now)}});
    lines.push_back({"draw", {"D05", "nextControl", careNumber(mNextControl - now)}});
    for(const std::string& prisoner : mPrison.triedPrisoners)
        lines.push_back({"draw", {"G02", "tried", prisoner}});
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
    const AiSettings& settings = ai.getSettings();
    const AiMath::DelayParams params = {settings.rho, settings.pi, settings.scanPeriod,
        config.getAiConfigDouble("SymptomScanFactor"), config.getAiConfigDouble("PeriodicMinDelay"),
        config.getAiConfigDouble("ActionLatencyMean"), config.getAiConfigDouble("ActionLatencySd")};
    const AiMath::Uniform01 uniform = std::bind(&Random::Double, 0.0, 1.0);
    // The pause is added to one more creature-list look interval, as in the care model.
    state.nextCheck = now + AiMath::lookInterval(config.getAiConfigDouble("LookFactorPlan"), params, uniform) +
        config.getAiConfigDouble("SlapMistakePauseSeconds");
    if(ownCreatures(ai).empty() || !ai.getMind().slip("D04"))
        return;
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
    for(Creature* creature : ownCreatures(ai))
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
    // Only the hall's level cap counts; an empty treasury or a full hall also closes its spots.
    const bool hasHall = !ai.getGameMap().getRoomsByTypeAndSeat(RoomType::trainingHall,
        ai.getControlledPlayer().getSeat()).empty();
    const uint32_t cap = ConfigManager::getSingleton().getRoomConfigUInt32("TrainHallMaxTrainingLevel");
    for(Creature* creature : ownFighters(ai))
    {
        const bool capped = hasHall && creature->getLevel() >= cap;
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
    for(Creature* creature : ownCreatures(ai))
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
    // The remedy rows act on the whole keeper, so each one is raised at most once per firing.
    std::set<std::string> raised;
    for(Creature* creature : ownCreatures(ai))
    {
        if(creature->getMoodValue() < CreatureMoodLevel::Upset)
            continue;
        // The mistake leaves only this creature unhandled at this firing.
        if(ai.getMind().slip("D07"))
            continue;
        std::string row;
        if(creature->isHungry())
            row = "B03";
        else if(creature->getHomeTile() == nullptr)
            row = "B02";
        else if(creature->getGoldFee() > 0.0)
            row = "A05";
        else
        {
            Tile* tile = creature->getPositionTile();
            Room* room = tile == nullptr ? nullptr : tile->getCoveringRoom();
            if(room != nullptr && room->getDirtStage() == 3)
                row = "B10";
            else if(creature->isHurt())
                row = "J08";
            else if(idle(*creature))
                row = "D06";
        }
        // J08 rests the named creature, so it is raised for each hurt creature.
        if(!row.empty() && (row == "J08" || raised.insert(row).second))
            trigger(row, creature);
    }
}
