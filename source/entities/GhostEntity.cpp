#include "entities/GhostEntity.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "creatureaction/CreatureActionType.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ODPacket.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "social/PostLog.h"
#include "utils/ConfigManager.h"
#include "utils/LogManager.h"
#include "utils/Random.h"
#include "ODApplication.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <map>
#include <queue>
#include <sstream>

namespace
{
    //! \brief Returns the stable saved name of a ghost phase.
    const char* stateName(GhostState state)
    {
        static const char* names[] = {"rising", "floating", "beamed", "boxed", "dissolving"};
        return names[static_cast<uint32_t>(state)];
    }
    //! \brief Reads a stable saved phase name and rejects invalid records.
    bool readState(const std::string& name, GhostState& state)
    {
        for(uint32_t i = 0; i <= static_cast<uint32_t>(GhostState::dissolving); ++i)
            if(name == stateName(static_cast<GhostState>(i)))
            {
                state = static_cast<GhostState>(i);
                return true;
            }
        return false;
    }
}

GhostEntity::GhostEntity(GameMap* map) :
    RenderedMovableEntity(map, "Ghost", "", 0.0, false, 0.45f),
    mLevel(1),
    mLifeLeft(ConfigManager::getSingleton().getGhostLifetimeSeconds() * ODApplication::turnsPerSecond),
    mState(GhostState::rising), mStateTurns(0.0),
    mHowlTurns(Random::Double(ConfigManager::getSingleton().getRoomConfigDouble("GhostHowlMinSeconds"),
        ConfigManager::getSingleton().getRoomConfigDouble("GhostHowlMaxSeconds")) * ODApplication::turnsPerSecond)
{
}

GhostEntity::GhostEntity(GameMap* map, const Creature& corpse) : GhostEntity(map)
{
    mClassName = corpse.getDefinition()->getClassName();
    mCreatureName = corpse.getName();
    mLevel = corpse.getLevel();
    setSeat(corpse.getSeat());
    setMeshName(corpse.getDefinition()->getMeshName());
    mPosition = corpse.getPosition();
    mPosition.z = 0.0f;
    mPrevAnimationState = EntityAnimation::idle_anim;
    mPrevAnimationStateLoop = true;
    mEntityParticleEffects.push_back(new EntityParticleEffect(nextParticleSystemsName(), "GhostRise",
        static_cast<int32_t>(std::ceil(ConfigManager::getSingleton().getRoomConfigDouble("GhostRiseSeconds") * ODApplication::turnsPerSecond))));
}

GhostEntity::~GhostEntity()
{
    for(EntityParticleEffect* effect : mEntityParticleEffects)
        delete effect;
    mEntityParticleEffects.clear();
}

void GhostEntity::addToGameMap(GameMap* map)
{
    RenderedMovableEntity::addToGameMap(map);
    if(getIsOnServerMap() && !mWalkQueue.empty())
    {
        const std::vector<Ogre::Vector2> path(mWalkQueue.begin(), mWalkQueue.end());
        setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
    }
}

GameEntityType GhostEntity::getObjectType() const { return GameEntityType::ghostEntity; }
double GhostEntity::getMoveSpeed() const
{
    return ConfigManager::getSingleton().getGhostFloatSpeed() / ODApplication::turnsPerSecond;
}
double GhostEntity::getAnimationSpeedFactor() const
{
    return mPrevAnimationState == EntityAnimation::walk_anim ? 0.5 / ODApplication::turnsPerSecond : 1.0;
}

void GhostEntity::setState(GhostState state)
{
    if(mState == state)
        return;
    mState = state;
    mStateTurns = 0.0;
    clearDestinations(EntityAnimation::idle_anim, true, true);
    if(state == GhostState::dissolving)
        mEntityParticleEffects.push_back(new EntityParticleEffect(nextParticleSystemsName(), "GhostDissolve",
            static_cast<int32_t>(std::ceil(ConfigManager::getSingleton().getRoomConfigDouble("GhostDissolveSeconds") * ODApplication::turnsPerSecond))));
    refresh();
}

void GhostEntity::teleport(const Ogre::Vector3& position)
{
    clearDestinations(EntityAnimation::idle_anim, true, true);
    setPosition(position);
    if(!getIsOnServerMap())
        return;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;
        ServerNotification* notice = new ServerNotification(ServerNotificationType::entityTeleported, seat->getPlayer());
        notice->mPacket << getName() << getPosition();
        ODServer::getSingleton().queueServerNotification(notice);
    }
}

void GhostEntity::setAssignedHunter(const std::string& name)
{
    mAssignedHunter = name;
    refresh();
}

void GhostEntity::doUpkeep()
{
    if(!getIsOnServerMap())
        return;
    for(std::vector<EntityParticleEffect*>::iterator it = mEntityParticleEffects.begin(); it != mEntityParticleEffects.end();)
    {
        EntityParticleEffect* effect = *it;
        --effect->mNbTurnsEffect;
        if(effect->mNbTurnsEffect <= 0)
        {
            delete effect;
            it = mEntityParticleEffects.erase(it);
        }
        else
            ++it;
    }
    if(mState == GhostState::dissolving)
    {
        if(mStateTurns >= ConfigManager::getSingleton().getRoomConfigDouble("GhostDissolveSeconds") * ODApplication::turnsPerSecond)
        {
            removeFromGameMap();
            deleteYourself();
        }
        return;
    }
    if(mState == GhostState::boxed)
        return;
    mLifeLeft = std::max(0.0, mLifeLeft - 1.0);
    if(mLifeLeft <= 0.0)
    {
        setState(GhostState::dissolving);
        return;
    }
    if(mState == GhostState::rising && mStateTurns >= ConfigManager::getSingleton().getRoomConfigDouble("GhostRiseSeconds") * ODApplication::turnsPerSecond)
        setState(GhostState::floating);
    if(mState == GhostState::floating || mState == GhostState::beamed)
        scareCreatures();
    if(mState == GhostState::floating)
    {
        if(!isMoving())
            wander();
        mHowlTurns -= 1.0;
        Tile* tile = getPositionTile();
        if(mHowlTurns <= 0.0 && tile != nullptr)
        {
            for(Seat* seat : mSeatsWithVisionNotified)
            {
                if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
                    continue;
                ServerNotification* notice = new ServerNotification(ServerNotificationType::playSpatialSound, seat->getPlayer());
                notice->mPacket << std::string("Ghost/Howl") << tile->getX() << tile->getY();
                ODServer::getSingleton().queueServerNotification(notice);
            }
            mHowlTurns = Random::Double(ConfigManager::getSingleton().getRoomConfigDouble("GhostHowlMinSeconds"),
                ConfigManager::getSingleton().getRoomConfigDouble("GhostHowlMaxSeconds")) * ODApplication::turnsPerSecond;
        }
    }
    refresh();
}

void GhostEntity::update(Ogre::Real elapsed)
{
    if(getIsOnServerMap() && !mWalkQueue.empty())
    {
        const Ogre::Vector2& next = mWalkQueue.front();
        Tile* tile = getGameMap()->getTile(static_cast<int>(next.x), static_cast<int>(next.y));
        if(tile == nullptr || tile->isFullTile())
            clearDestinations(EntityAnimation::idle_anim, true, true);
    }
    RenderedMovableEntity::update(elapsed);
    if(mState != GhostState::boxed)
        mStateTurns += elapsed * ODApplication::turnsPerSecond *
            (getIsOnServerMap() ? 1.0 : getGameMap()->getGameSpeedFactor());
    if(!getIsOnServerMap())
        updateLook();
}

void GhostEntity::wander()
{
    Tile* start = getPositionTile();
    if(start == nullptr)
        return;
    const int radius = static_cast<int>(ConfigManager::getSingleton().getGhostWanderRadius());
    std::map<Tile*, Tile*> parent;
    std::queue<Tile*> pending;
    std::vector<Tile*> candidates;
    parent[start] = nullptr;
    pending.push(start);
    while(!pending.empty())
    {
        Tile* tile = pending.front();
        pending.pop();
        for(int dx = -1; dx <= 1; ++dx)
            for(int dy = -1; dy <= 1; ++dy)
            {
                if(dx == 0 && dy == 0)
                    continue;
                Tile* next = getGameMap()->getTile(tile->getX() + dx, tile->getY() + dy);
                if(next == nullptr || next->isFullTile() || parent.count(next) != 0)
                    continue;
                // Diagonal flight cannot cut through the corner of a solid wall.
                Tile* sideX = getGameMap()->getTile(tile->getX() + dx, tile->getY());
                Tile* sideY = getGameMap()->getTile(tile->getX(), tile->getY() + dy);
                if(dx != 0 && dy != 0 && (sideX->isFullTile() || sideY->isFullTile()))
                    continue;
                parent[next] = tile;
                pending.push(next);
                if(std::max(std::abs(next->getX() - start->getX()), std::abs(next->getY() - start->getY())) <= radius)
                    candidates.push_back(next);
            }
    }
    if(candidates.empty())
        return;
    Tile* target = candidates[Random::Uint(0, static_cast<unsigned int>(candidates.size() - 1))];
    std::vector<Ogre::Vector2> path;
    for(Tile* tile = target; tile != start; tile = parent[tile])
        path.push_back(Ogre::Vector2(tile->getX(), tile->getY()));
    std::reverse(path.begin(), path.end());
    setWalkPath(EntityAnimation::walk_anim, EntityAnimation::idle_anim, true, true, path, false, true);
}

void GhostEntity::scareCreatures()
{
    for(std::set<std::string>::iterator it = mScaredCreatures.begin(); it != mScaredCreatures.end();)
    {
        Creature* creature = getGameMap()->getCreature(*it);
        if(creature == nullptr || !creature->isActionInList(CreatureActionType::flee))
            it = mScaredCreatures.erase(it);
        else
            ++it;
    }
    Tile* origin = getPositionTile();
    if(origin == nullptr)
        return;
    const std::vector<Tile*> visible = getGameMap()->visibleTiles(origin->getX(), origin->getY(),
        ConfigManager::getSingleton().getTrapConfigUInt32("FearRadius"));
    for(Creature* creature : getGameMap()->getCreatures())
    {
        if(!creature->isAlive() || creature->isKo() || !creature->getIsOnMap() || creature->isInPrison() ||
            creature->getDefinition()->isWorker() || !creature->getDefinition()->isAfraidOfGhosts() ||
            creature->isActionInList(CreatureActionType::flee) || mScaredCreatures.count(creature->getName()) != 0 ||
            std::find(visible.begin(), visible.end(), creature->getPositionTile()) == visible.end())
            continue;
        creature->fleeFromTile(origin, ConfigManager::getSingleton().getTrapConfigDouble("FearDurationTurns"), true);
        mScaredCreatures.insert(creature->getName());
        social::PostLog::getSingleton().addPost(getGameMap()->getTurnNumber(), creature->getName(),
            creature->getDefinition()->getClassName(), false, social::PostCategory::GhostScared, 0);
    }
}

void GhostEntity::refresh()
{
    if(!getIsOnServerMap())
        return;
    for(Seat* seat : mSeatsWithVisionNotified)
    {
        if(seat->getPlayer() == nullptr || !seat->getPlayer()->getIsHuman())
            continue;
        ServerNotification* notice = new ServerNotification(ServerNotificationType::entitiesRefresh, seat->getPlayer());
        notice->mPacket << uint32_t(1) << getObjectType() << getName();
        exportToPacketForUpdate(notice->mPacket, seat);
        ODServer::getSingleton().queueServerNotification(notice);
    }
}

void GhostEntity::updateLook()
{
    Ogre::SceneNode* node = getEntityNode();
    if(node == nullptr)
        return;
    const double duration = ConfigManager::getSingleton().getRoomConfigDouble(
        mState == GhostState::dissolving ? "GhostDissolveSeconds" : "GhostRiseSeconds");
    const double progress = std::min(1.0, mStateTurns / (duration * ODApplication::turnsPerSecond));
    float alpha = 0.45f;
    float height = 0.3f;
    if(mState == GhostState::rising)
    {
        alpha *= static_cast<float>(progress);
        height *= static_cast<float>(progress);
    }
    else if(mState == GhostState::dissolving)
        alpha *= static_cast<float>(1.0 - progress);
    else if(mState == GhostState::boxed)
        alpha = 0.0f;
    node->setVisible(mState != GhostState::boxed);
    node->setPosition(mPosition + Ogre::Vector3(0, 0, height));
    setMeshOpacity(alpha);
}

void GhostEntity::createMeshLocal(NodeType type)
{
    RenderedMovableEntity::createMeshLocal(type);
    if(!getIsOnServerMap())
    {
        const double levelSteps = static_cast<double>(std::max(1u, std::min(MAX_LEVEL, mLevel)) - 1u);
        const Ogre::Real scale = static_cast<Ogre::Real>(1.0 + ConfigManager::getSingleton().getCreatureLevelGrowthMax() *
            levelSteps / static_cast<double>(MAX_LEVEL - 1u));
        getEntityNode()->setScale(Ogre::Vector3::UNIT_SCALE * scale);
        updateLook();
    }
}

void GhostEntity::exportToPacket(ODPacket& packet, const Seat* seat) const
{
    RenderedMovableEntity::exportToPacket(packet, seat);
    packet << mClassName << mCreatureName << mLevel << mLifeLeft << static_cast<uint32_t>(mState)
        << mAssignedHunter << mStateTurns << mHowlTurns;
}

void GhostEntity::importFromPacket(ODPacket& packet)
{
    RenderedMovableEntity::importFromPacket(packet);
    uint32_t state;
    OD_ASSERT_TRUE(packet >> mClassName >> mCreatureName >> mLevel >> mLifeLeft >> state
        >> mAssignedHunter >> mStateTurns >> mHowlTurns);
    mState = static_cast<GhostState>(state);
}

void GhostEntity::exportToPacketForUpdate(ODPacket& packet, Seat* seat)
{
    GameEntity::exportToPacketForUpdate(packet, seat);
    packet << mLifeLeft << static_cast<uint32_t>(mState) << mAssignedHunter << mStateTurns;
}

void GhostEntity::updateFromPacket(ODPacket& packet)
{
    GameEntity::updateFromPacket(packet);
    uint32_t state;
    OD_ASSERT_TRUE(packet >> mLifeLeft >> state >> mAssignedHunter >> mStateTurns);
    mState = static_cast<GhostState>(state);
    updateLook();
}

void GhostEntity::exportToStream(std::ostream& stream) const
{
    const std::streamsize precision = stream.precision();
    stream << std::setprecision(std::numeric_limits<double>::max_digits10);
    stream << getSeat()->getId() << '\t' << getName() << '\t' << mClassName << '\t' << mCreatureName << '\t'
        << mPosition.x << '\t' << mPosition.y << '\t' << mLevel << '\t' << mLifeLeft << '\t'
        << stateName(mState) << '\t' << (mAssignedHunter.empty() ? "none" : mAssignedHunter);
    stream << " [GhostRuntime] " << mStateTurns << ' ' << mHowlTurns << ' ' << mScaredCreatures.size();
    for(const std::string& name : mScaredCreatures)
        stream << ' ' << name;
    stream << ' ' << mWalkQueue.size();
    for(const Ogre::Vector2& point : mWalkQueue)
        stream << ' ' << point.x << ' ' << point.y;
    stream << " [/GhostRuntime]";
    stream.precision(precision);
}

bool GhostEntity::importFromStream(std::istream& stream)
{
    int seatId;
    std::string state;
    if(!(stream >> seatId >> mName >> mClassName >> mCreatureName >> mPosition.x >> mPosition.y
        >> mLevel >> mLifeLeft >> state >> mAssignedHunter) || !readState(state, mState))
        return false;
    setSeat(getGameMap()->getSeatById(seatId));
    const CreatureDefinition* definition = getGameMap()->getClassDescription(mClassName);
    if(getSeat() == nullptr || definition == nullptr)
        return false;
    setMeshName(definition->getMeshName());
    mPosition.z = 0.0f;
    if(mAssignedHunter == "none")
        mAssignedHunter.clear();
    std::string tag;
    if(stream >> tag)
    {
        if(tag != "[GhostRuntime]")
            return false;
        uint32_t count;
        if(!(stream >> mStateTurns >> mHowlTurns >> count))
            return false;
        for(uint32_t i = 0; i < count; ++i)
        {
            std::string name;
            if(!(stream >> name))
                return false;
            mScaredCreatures.insert(name);
        }
        if(!(stream >> count))
            return false;
        for(uint32_t i = 0; i < count; ++i)
        {
            Ogre::Vector2 point;
            if(!(stream >> point.x >> point.y))
                return false;
            mWalkQueue.push_back(point);
        }
        if(!(stream >> tag) || tag != "[/GhostRuntime]")
            return false;
    }
    else
        stream.clear();
    mPrevAnimationState = mWalkQueue.empty() ? EntityAnimation::idle_anim : EntityAnimation::walk_anim;
    mPrevAnimationStateLoop = true;
    if(mState == GhostState::rising || mState == GhostState::dissolving)
    {
        const double duration = ConfigManager::getSingleton().getRoomConfigDouble(
            mState == GhostState::rising ? "GhostRiseSeconds" : "GhostDissolveSeconds") * ODApplication::turnsPerSecond;
        mEntityParticleEffects.push_back(new EntityParticleEffect(nextParticleSystemsName(),
            mState == GhostState::rising ? "GhostRise" : "GhostDissolve",
            static_cast<int32_t>(std::ceil(std::max(0.0, duration - mStateTurns)))));
    }
    return true;
}

GhostEntity* GhostEntity::loadFromStream(GameMap* map, std::istream& stream)
{
    GhostEntity* ghost = new GhostEntity(map);
    if(!ghost->importFromStream(stream))
    {
        OD_LOG_ERR("Invalid ghost record");
        delete ghost;
        return nullptr;
    }
    return ghost;
}

GhostEntity* GhostEntity::loadFromPacket(GameMap* map, ODPacket& packet)
{
    GhostEntity* ghost = new GhostEntity(map);
    ghost->importFromPacket(packet);
    return ghost;
}
