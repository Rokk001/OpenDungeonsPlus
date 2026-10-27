#include "creatureaction/CreatureActionHuntGhost.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GhostEntity.h"
#include "entities/GhostBoxEntity.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Seat.h"
#include "game/Player.h"
#include "game/SkillType.h"
#include "game/SkillManager.h"
#include "gamemap/GameMap.h"
#include "rooms/RoomGhostRoom.h"
#include "rooms/RoomCrypt.h"
#include "network/ODServer.h"
#include "network/ServerNotification.h"
#include "social/PostLog.h"
#include "utils/ConfigManager.h"
#include "utils/MakeUnique.h"
#include "ODApplication.h"
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <limits>
#include <tuple>

namespace
{
//! \brief Returns an existing ghost by its stable entity name.
GhostEntity* ghostNamed(GameMap& map, const std::string& name)
{ return static_cast<GhostEntity*>(map.getEntityFromTypeAndName(GameEntityType::ghostEntity,name)); }
//! \brief Returns a room by its stable name, retaining type and owner checks at the caller.
RoomGhostRoom* roomNamed(GameMap& map, const std::string& name)
{
    for(Room* room : map.getRoomsByType(RoomType::ghostRoom))
        if(room->getName()==name) return static_cast<RoomGhostRoom*>(room);
    return nullptr;
}
//! \brief Returns true only for an unassigned eligible ghost or closed lying box on own territory.
bool eligible(GameEntity& entity, const Seat& seat)
{
    Tile* tile=entity.getPositionTile();
    if(tile==nullptr || !tile->isClaimedForSeat(&seat)) return false;
    if(entity.getObjectType()==GameEntityType::ghostEntity)
    {
        GhostEntity& ghost=static_cast<GhostEntity&>(entity);
        return ghost.getState()==GhostState::floating && ghost.getAssignedHunter().empty();
    }
    if(entity.getObjectType()==GameEntityType::ghostBoxEntity)
        return static_cast<GhostBoxEntity&>(entity).getAssignedHunter().empty();
    return false;
}
//! \brief Computes a real tile path length, including both endpoints, or an unreachable sentinel.
size_t pathLength(GameMap& map, Creature& hunter, Tile* from, Tile* to)
{
    if(from==nullptr || to==nullptr) return std::numeric_limits<size_t>::max();
    const std::list<Tile*> path=map.path(from,to,&hunter,hunter.getSeat());
    return path.empty()?std::numeric_limits<size_t>::max():path.size();
}
}

CreatureActionHuntGhost::CreatureActionHuntGhost(Creature& creature, const std::string& target) :
    CreatureAction(creature),mTarget(target),mLastPosition(creature.getPosition())
{}
CreatureActionHuntGhost::~CreatureActionHuntGhost()
{ interrupt(); }
std::function<bool()> CreatureActionHuntGhost::action()
{ return std::bind(&CreatureActionHuntGhost::handleHunt,this); }

void CreatureActionHuntGhost::playSound(GameMap& map, Tile& tile, const std::string& family)
{
    for(Seat* seat : map.getSeats())
    {
        if(seat->getPlayer()==nullptr || !seat->getPlayer()->getIsHuman() || !seat->hasVisionOnTile(&tile)) continue;
        ServerNotification* notice=new ServerNotification(ServerNotificationType::playSpatialSound,seat->getPlayer());
        notice->mPacket << family << tile.getX() << tile.getY();
        ODServer::getSingleton().queueServerNotification(notice);
    }
}

RoomGhostRoom* CreatureActionHuntGhost::hookRoom() const
{
    RoomGhostRoom* room=roomNamed(*mCreature.getGameMap(),mHookRoom);
    return room!=nullptr && room->getSeat()==mCreature.getSeat()?room:nullptr;
}

double CreatureActionHuntGhost::researched(const std::string& key,const std::string& effect) const
{ return SkillManager::getResearchValue(mCreature.getSeat(),SkillType::roomGhostRoom,ConfigManager::getSingleton().getRoomConfigDouble(key),effect); }

void CreatureActionHuntGhost::releaseTarget()
{
    GameMap& map=*mCreature.getGameMap();
    GhostEntity* ghost=ghostNamed(map,mTarget);
    if(ghost!=nullptr && ghost->getAssignedHunter()==mCreature.getName())
    {
        ghost->setAssignedHunter("");
        if(ghost->getState()==GhostState::beamed) ghost->setState(GhostState::floating);
    }
    GhostBoxEntity* box=static_cast<GhostBoxEntity*>(map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mTarget));
    if(box!=nullptr && box->getAssignedHunter()==mCreature.getName()) box->setAssignedHunter("");
    mTarget.clear();mBeamTarget.clear();
}

void CreatureActionHuntGhost::interrupt()
{
    if(mInterrupted) return;
    mInterrupted=true;
    if(!mCreature.getIsOnServerMap()) return;
    releaseTarget();
    if(mCreature.getIsOnMap()) mLastPosition=mCreature.getPosition();
    if(!mGhosts.empty())
    {
        GhostBoxEntity* box=new GhostBoxEntity(mCreature.getGameMap(),mGhosts);
        box->setSeat(mCreature.getSeat());box->setPosition(mLastPosition);box->addToGameMap();box->createMesh();
        mGhosts.clear();
    }
    for(Room* room : mCreature.getGameMap()->getRoomsByType(RoomType::ghostRoom))
        static_cast<RoomGhostRoom*>(room)->releaseHunter(mCreature);
    mEquipped=false;mCreature.refreshGhostHuntVisuals();
}

bool CreatureActionHuntGhost::moveTo(Tile* tile)
{
    if(tile==nullptr) return false;
    if(mCreature.getPositionTile()==tile && !mCreature.isMoving()) return true;
    if(mCreature.isMoving() && mDestination==tile) return true;
    const std::list<Tile*> route=mCreature.getGameMap()->path(&mCreature,tile);
    if(route.empty()) return false;
    std::vector<Ogre::Vector2> path;
    Creature::tileToVector2(route,path,true,0.0f);
    mCreature.setWalkPath(EntityAnimation::walk_anim,EntityAnimation::idle_anim,true,true,path,true);
    mDestination=tile;
    return mCreature.isMoving() || mCreature.getPositionTile()==tile;
}

void CreatureActionHuntGhost::upkeep()
{
    if(mInterrupted) return;
    if(mCreature.getIsOnMap()) mLastPosition=mCreature.getPosition();
    if(!mCreature.isAlive() || mCreature.isKo() || !mCreature.getIsOnMap() ||
       mCreature.getGameMap()->getRoomsByTypeAndSeat(RoomType::ghostRoom,mCreature.getSeat()).empty())
    { interrupt();return; }
    ConfigManager& config=ConfigManager::getSingleton();
    const double xp=SkillManager::getResearchValue(mCreature.getSeat(),SkillType::roomTrainingHall,config.getRoomConfigDouble("TrainHallXpPerAttack"),"XpPerHit") /
        ((config.getRoomConfigDouble("TrainHallCooldownHitMin")+config.getRoomConfigDouble("TrainHallCooldownHitMax"))/2.0+1.0);
    mCreature.receiveExp(xp);
    mRepathTurns+=1.0;
}

bool CreatureActionHuntGhost::nextTarget()
{
    releaseTarget();
    GameMap& map=*mCreature.getGameMap();
    GameEntity* best=nullptr;size_t distance=std::numeric_limits<size_t>::max();
    for(RenderedMovableEntity* entity : map.getRenderedMovableEntities())
    {
        if(!eligible(*entity,*mCreature.getSeat())) continue;
        if(!mGhosts.empty() && entity->getObjectType()==GameEntityType::ghostBoxEntity) continue;
        const size_t length=pathLength(map,mCreature,mCreature.getPositionTile(),entity->getPositionTile());
        if(length<distance) { best=entity;distance=length; }
    }
    if(best==nullptr) return false;
    mTarget=best->getName();
    if(best->getObjectType()==GameEntityType::ghostEntity) static_cast<GhostEntity*>(best)->setAssignedHunter(mCreature.getName());
    else static_cast<GhostBoxEntity*>(best)->setAssignedHunter(mCreature.getName());
    for(Room* room : map.getRoomsByTypeAndSeat(RoomType::ghostRoom,mCreature.getSeat()))
        if(room->getCentralTile()!=nullptr) playSound(map,*room->getCentralTile(),"Rooms/GhostRoom/Bell");
    mRepathTurns=ConfigManager::getSingleton().getRoomConfigDouble("GhostRepathTurns");
    return true;
}

bool CreatureActionHuntGhost::selectRevival()
{
    if(!mCreature.getSeat()->getGhostRevive()) return false;
    for(const std::string& name : mReviveGhosts)
    {
        GhostEntity* ghost=ghostNamed(*mCreature.getGameMap(),name);
        if(ghost==nullptr) continue;
        Creature* corpse=mCreature.getGameMap()->getCreature(ghost->getCreatureName());
        if(corpse==nullptr || corpse->isAlive() || corpse->getSeat()!=mCreature.getSeat() || corpse->getPositionTile()==nullptr ||
           mCreature.getSeat()->getMana()<researched("GhostReviveMana","RevivePrice")) continue;
        Room* room=corpse->getPositionTile()->getCoveringRoom();
        if(room==nullptr || room->getType()!=RoomType::crypt || room->getSeat()!=mCreature.getSeat() ||
           static_cast<RoomCrypt*>(room)->getCorpseSpot(*corpse)==nullptr) continue;
        mReviveTarget=name;mDestination=nullptr;return true;
    }
    return false;
}

bool CreatureActionHuntGhost::handleHunt()
{
    if(mInterrupted) { mCreature.popAction();return false; }
    GameMap& map=*mCreature.getGameMap();
    ConfigManager& config=ConfigManager::getSingleton();
    RoomGhostRoom* room=hookRoom();
    if(mState!=0 && room==nullptr) { interrupt();mCreature.popAction();return false; }
    if(mState==0)
    {
        if(room==nullptr)
        {
            size_t distance=std::numeric_limits<size_t>::max();
            for(Room* candidate : map.getRoomsByTypeAndSeat(RoomType::ghostRoom,mCreature.getSeat()))
            {
                RoomGhostRoom* ghostRoom=static_cast<RoomGhostRoom*>(candidate);
                Tile* hook=ghostRoom->reserveHook(mCreature);
                if(hook==nullptr) continue;
                const size_t length=pathLength(map,mCreature,mCreature.getPositionTile(),hook);
                if(length<distance)
                {
                    if(room!=nullptr) room->releaseHunter(mCreature);
                    room=ghostRoom;mHookX=hook->getX();mHookY=hook->getY();distance=length;
                }
                else ghostRoom->releaseHunter(mCreature);
            }
            if(room==nullptr) { interrupt();mCreature.popAction();return false; }
            mHookRoom=room->getName();
        }
        Tile* hook=map.getTile(mHookX,mHookY);
        if(!moveTo(hook)) { interrupt();return false; }
        if(mCreature.isMoving()) return false;
        room->equipHook(mCreature,true);mEquipped=true;mState=1;mDestination=nullptr;
        mCreature.refreshGhostHuntVisuals();return false;
    }
    if(mState==1)
    {
        GhostEntity* ghost=ghostNamed(map,mTarget);
        GhostBoxEntity* box=static_cast<GhostBoxEntity*>(map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mTarget));
        GameEntity* target=ghost!=nullptr?static_cast<GameEntity*>(ghost):static_cast<GameEntity*>(box);
        if(target==nullptr || target->getPositionTile()==nullptr || !target->getPositionTile()->isClaimedForSeat(mCreature.getSeat()) ||
           (ghost!=nullptr && ghost->getState()!=GhostState::floating))
        {
            if(nextTarget()) return false;
            mState=5;return false;
        }
        Tile* own=mCreature.getPositionTile();Tile* there=target->getPositionTile();
        const int range=static_cast<int>(researched("GhostBeamRange","BeamRange"));
        if(box!=nullptr && own==there && !mCreature.isMoving()) { mState=8;mTurns=0.0;return false; }
        if(ghost!=nullptr && own!=nullptr && std::max(std::abs(own->getX()-there->getX()),std::abs(own->getY()-there->getY()))<=range)
        {
            mCreature.clearDestinations(EntityAnimation::beam_anim,true,false);
            mCreature.setAnimationState(EntityAnimation::beam_anim,true,ghost->getPosition()-mCreature.getPosition(),false);
            ghost->setState(GhostState::beamed);mState=2;mBeamTarget=mTarget;mTurns=0.0;
            mCreature.refreshGhostHuntVisuals();return false;
        }
        if(!mCreature.isMoving() || mRepathTurns>=config.getRoomConfigDouble("GhostRepathTurns"))
        {
            mDestination=nullptr;mRepathTurns=0.0;
            // Stand outside the ghost tile at a reachable beam endpoint.
            std::vector<Tile*> destinations;
            if(box!=nullptr) destinations.push_back(there);
            else for(int y=-range;y<=range;++y) for(int x=-range;x<=range;++x)
            {
                Tile* tile=map.getTile(there->getX()+x,there->getY()+y);
                if(tile!=nullptr && tile->isClaimedForSeat(mCreature.getSeat()) && tile!=there) destinations.push_back(tile);
            }
            Tile* chosen=nullptr;map.findBestPath(&mCreature,own,destinations,chosen);
            if(chosen==nullptr || !moveTo(chosen)) { releaseTarget();mState=5; }
        }
        return false;
    }
    if(mState==2 || mState==3)
    {
        GhostEntity* ghost=ghostNamed(map,mTarget);
        if(ghost==nullptr || ghost->getState()==GhostState::dissolving)
        { releaseTarget();mState=4;return false; }
        mTurns+=1.0;
        const double efficiency=mCreature.getDefinition()->getRoomAffinity(RoomType::ghostRoom).getEfficiency();
        if(mState==2)
        {
            const double duration=researched("GhostBeamTurns","CatchTime")/efficiency;
            if(mTurns<duration) return false;
            mTurns-=duration;mState=3;mBeamTarget.clear();
            mCreature.setAnimationState(EntityAnimation::throw_anim,false,ghost->getPosition()-mCreature.getPosition(),true);
            mCreature.refreshGhostHuntVisuals();
        }
        const double duration=config.getRoomConfigDouble("GhostBoxThrowSeconds")*ODApplication::turnsPerSecond;
        if(mTurns<duration) return false;
        mTurns-=duration;ghost->setState(GhostState::boxed);ghost->setAssignedHunter("");mGhosts.push_back(ghost->getName());
        if(ghost->getSeat()==mCreature.getSeat() && mCreature.getSeat()->getGhostRevive() &&
           mCreature.getSeat()->getMana()>=researched("GhostReviveMana","RevivePrice"))
        {
            Creature* corpse=map.getCreature(ghost->getCreatureName());
            if(corpse!=nullptr && !corpse->isAlive() && corpse->getPositionTile()!=nullptr)
            {
                Room* crypt=corpse->getPositionTile()->getCoveringRoom();
                if(crypt!=nullptr && crypt->getType()==RoomType::crypt && crypt->getSeat()==mCreature.getSeat() &&
                   static_cast<RoomCrypt*>(crypt)->getCorpseSpot(*corpse)!=nullptr) mReviveGhosts.push_back(ghost->getName());
            }
        }
        playSound(map,*ghost->getPositionTile(),"Rooms/GhostRoom/BoxSnap");
        social::PostLog::getSingleton().addPost(map.getTurnNumber(),mCreature.getName(),mCreature.getDefinition()->getClassName(),false,social::PostCategory::GhostHunted,0);
        mTarget.clear();mState=4;return false;
    }
    if(mState==8)
    {
        GhostBoxEntity* box=static_cast<GhostBoxEntity*>(map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,mTarget));
        if(box!=nullptr)
        {
            mGhosts=box->takeGhostNames();box->removeFromGameMap();box->deleteYourself();
            // Picked-up boxes keep their full contents, independent of current capacity.
            for(const std::string& name : mGhosts)
            {
                GhostEntity* ghost=ghostNamed(map,name);
                if(ghost!=nullptr && ghost->getSeat()==mCreature.getSeat() && mCreature.getSeat()->getGhostRevive() &&
                   mCreature.getSeat()->getMana()>=researched("GhostReviveMana","RevivePrice")) mReviveGhosts.push_back(name);
            }
        }
        mTarget.clear();mState=4;return false;
    }
    if(mState==4)
    {
        if(static_cast<double>(mGhosts.size())<researched("GhostBoxCapacity","BoxCapacity") && nextTarget()) { mState=1;return false; }
        mState=5;return false;
    }
    if(mState==5)
    {
        if(mReviveTarget.empty() && !selectRevival()) { mState=6;mDestination=nullptr;return false; }
        GhostEntity* ghost=ghostNamed(map,mReviveTarget);
        Creature* corpse=ghost==nullptr?nullptr:map.getCreature(ghost->getCreatureName());
        Room* crypt=corpse==nullptr || corpse->getPositionTile()==nullptr?nullptr:corpse->getPositionTile()->getCoveringRoom();
        bool valid=corpse!=nullptr && !corpse->isAlive() && corpse->getSeat()==mCreature.getSeat() && crypt!=nullptr &&
            crypt->getType()==RoomType::crypt && crypt->getSeat()==mCreature.getSeat() &&
            static_cast<RoomCrypt*>(crypt)->getCorpseSpot(*corpse)!=nullptr && mCreature.getSeat()->getGhostRevive() &&
            mCreature.getSeat()->getMana()>=researched("GhostReviveMana","RevivePrice");
        Tile* destination=valid?corpse->getPositionTile():nullptr;
        if(valid && mCreature.getPositionTile()!=destination)
        {
            if(moveTo(destination)) return false;
            valid=false;
        }
        if(valid && !mCreature.isMoving())
        {
            const double price=researched("GhostReviveMana","RevivePrice");
            if(corpse->reviveFromCorpse(config.getRoomConfigDouble("GhostReviveHpShare")))
            {
                mCreature.getSeat()->takeMana(price);
                mGhosts.erase(std::remove(mGhosts.begin(),mGhosts.end(),mReviveTarget),mGhosts.end());
                ghost->removeFromGameMap();ghost->deleteYourself();
            }
        }
        mReviveGhosts.erase(std::remove(mReviveGhosts.begin(),mReviveGhosts.end(),mReviveTarget),mReviveGhosts.end());
        mReviveTarget.clear();mDestination=nullptr;return false;
    }
    if(mState==6)
    {
        if(mGhosts.empty()) { mState=7;mDestination=nullptr;return false; }
        if(mDestination==nullptr)
        {
            size_t distance=std::numeric_limits<size_t>::max();RoomGhostRoom* nearest=nullptr;Tile* stand=nullptr;
            for(Room* candidate : map.getRoomsByTypeAndSeat(RoomType::ghostRoom,mCreature.getSeat()))
            {
                RoomGhostRoom* other=static_cast<RoomGhostRoom*>(candidate);Tile* spot=other->reserveCauldron(mCreature);
                if(spot==nullptr) continue;
                const size_t length=pathLength(map,mCreature,mCreature.getPositionTile(),spot);
                if(length<distance) { if(nearest!=nullptr) nearest->releaseCauldron(mCreature);nearest=other;stand=spot;distance=length; }
                else other->releaseCauldron(mCreature);
            }
            if(nearest==nullptr) return false;
            mEmptyRoom=nearest->getName();mDestination=stand;
            moveTo(stand);mTurns=0.0;
        }
        if(mCreature.isMoving()) return false;
        RoomGhostRoom* empty=roomNamed(map,mEmptyRoom);
        if(empty==nullptr || empty->getSeat()!=mCreature.getSeat()) { interrupt();return false; }
        mCreature.setAnimationState(EntityAnimation::empty_anim,true,Ogre::Vector3::ZERO,false);
        mTurns+=1.0;
        const double duration=config.getRoomConfigDouble("GhostEmptyTurns")/mCreature.getDefinition()->getRoomAffinity(RoomType::ghostRoom).getEfficiency();
        while(!mGhosts.empty() && mTurns>=duration)
        {
            mTurns-=duration;GhostEntity* ghost=ghostNamed(map,mGhosts.front());
            if(ghost!=nullptr) empty->emptyGhost(mCreature,*ghost);
            mGhosts.erase(mGhosts.begin());
        }
        if(mGhosts.empty()) { empty->releaseCauldron(mCreature);mDestination=nullptr;mState=7; }
        return false;
    }
    if(mState==7)
    {
        Tile* hook=map.getTile(mHookX,mHookY);
        if(!moveTo(hook)) { interrupt();return false; }
        if(mCreature.isMoving()) return false;
        mGhosts.clear();interrupt();mCreature.popAction();return false;
    }
    return false;
}

void CreatureActionHuntGhost::assignHunters(GameMap& map, Seat& seat)
{
    const std::vector<Room*> rooms=map.getRoomsByTypeAndSeat(RoomType::ghostRoom,&seat);
    size_t backpacks=0,active=0;
    for(Room* room : rooms) backpacks+=static_cast<RoomGhostRoom*>(room)->getBackpackCount();
    std::vector<Creature*> hunters;
    for(Creature* creature : map.getCreaturesBySeat(&seat))
    {
        if(creature->isActionInList(CreatureActionType::huntGhost)) { ++active;continue; }
        if(!creature->isAlive() || creature->isKo() || !creature->getIsOnMap() || creature->getSeatPrison()!=nullptr ||
           creature->getDefinition()->isWorker() || creature->isActionInList(CreatureActionType::fight) ||
           creature->isActionInList(CreatureActionType::fightFriendly) || creature->isActionInList(CreatureActionType::flee)) continue;
        for(const CreatureRoomAffinity& affinity : creature->getDefinition()->getRoomAffinity())
            if(affinity.getRoomType()==RoomType::ghostRoom && affinity.getEfficiency()>0.0) { hunters.push_back(creature);break; }
    }
    typedef std::tuple<size_t,std::string,GameEntity*> Target;
    std::vector<Target> targets;
    for(RenderedMovableEntity* entity : map.getRenderedMovableEntities())
    {
        if(!eligible(*entity,seat)) continue;
        size_t distance=std::numeric_limits<size_t>::max();
        for(Creature* hunter : hunters) for(Room* room : rooms) for(Tile* tile : room->getCoveredTiles())
            distance=std::min(distance,pathLength(map,*hunter,tile,entity->getPositionTile()));
        if(distance!=std::numeric_limits<size_t>::max()) targets.push_back(Target(distance,entity->getName(),entity));
    }
    std::sort(targets.begin(),targets.end());
    for(const Target& target : targets)
    {
        if(active>=backpacks || hunters.empty()) break;
        GameEntity* entity=std::get<2>(target);
        Creature* nearest=nullptr;size_t distance=std::numeric_limits<size_t>::max();
        for(Creature* hunter : hunters)
        {
            const size_t length=pathLength(map,*hunter,hunter->getPositionTile(),entity->getPositionTile());
            if(length<distance) { nearest=hunter;distance=length; }
        }
        if(nearest==nullptr) continue;
        nearest->clearActionQueue();nearest->clearDestinations(EntityAnimation::idle_anim,true,true);
        if(entity->getObjectType()==GameEntityType::ghostEntity) static_cast<GhostEntity*>(entity)->setAssignedHunter(nearest->getName());
        else static_cast<GhostBoxEntity*>(entity)->setAssignedHunter(nearest->getName());
        nearest->pushAction(Utils::make_unique<CreatureActionHuntGhost>(*nearest,entity->getName()));
        for(Room* room : rooms) if(room->getCentralTile()!=nullptr) playSound(map,*room->getCentralTile(),"Rooms/GhostRoom/Bell");
        ++active;hunters.erase(std::remove(hunters.begin(),hunters.end(),nearest),hunters.end());
    }
}

void CreatureActionHuntGhost::exportToStream(std::ostream& stream) const
{
    stream << " [GhostHunt] " << mState << ' ' << (mTarget.empty()?"none":mTarget) << ' '
        << (mHookRoom.empty()?"none":mHookRoom) << ' ' << mHookX << ' ' << mHookY << ' ' << mTurns << ' ' << mGhosts.size();
    for(const std::string& ghost : mGhosts) stream << ' ' << ghost;
    stream << " [/GhostHunt] [GhostHuntRuntime] " << mEquipped << ' ' << mRepathTurns << ' ' << mReviveGhosts.size();
    for(const std::string& ghost : mReviveGhosts) stream << ' ' << ghost;
    stream << ' ' << (mReviveTarget.empty()?"none":mReviveTarget) << ' ' << (mEmptyRoom.empty()?"none":mEmptyRoom)
        << ' ' << (mDestination==nullptr?-1:mDestination->getX()) << ' ' << (mDestination==nullptr?-1:mDestination->getY())
        << ' ' << mCreature.getWalkQueue().size();
    for(const Ogre::Vector2& point : mCreature.getWalkQueue()) stream << ' ' << point.x << ' ' << point.y;
    stream << " [/GhostHuntRuntime]";
}

bool CreatureActionHuntGhost::importFromStream(std::istream& stream)
{
    size_t count=0;std::string close;
    if(!(stream>>mState>>mTarget>>mHookRoom>>mHookX>>mHookY>>mTurns>>count) || mState>8 || !std::isfinite(mTurns) || mTurns<0.0) return false;
    while(count-->0) { std::string ghost;if(!(stream>>ghost)) return false;mGhosts.push_back(ghost); }
    if(!(stream>>close) || close!="[/GhostHunt]") return false;
    if(mTarget=="none") mTarget.clear();if(mHookRoom=="none") mHookRoom.clear();
    const std::streampos position=stream.tellg();
    if(stream>>close)
    {
        if(close!="[GhostHuntRuntime]") { stream.seekg(position);mRestoring=true;return true; }
        int x=-1,y=-1;
        if(!(stream>>mEquipped>>mRepathTurns>>count)) return false;
        while(count-->0) { std::string ghost;if(!(stream>>ghost)) return false;mReviveGhosts.push_back(ghost); }
        if(!(stream>>mReviveTarget>>mEmptyRoom>>x>>y>>count)) return false;
        mDestination=mCreature.getGameMap()->getTile(x,y);
        while(count-->0) { Ogre::Vector2 point;if(!(stream>>point.x>>point.y)) return false;mLoadedPath.push_back(point); }
        if(!(stream>>close) || close!="[/GhostHuntRuntime]") return false;
        if(mReviveTarget=="none") mReviveTarget.clear();if(mEmptyRoom=="none") mEmptyRoom.clear();
    }
    else stream.clear();
    mRestoring=true;return true;
}

void CreatureActionHuntGhost::restore()
{
    if(!mRestoring) return;
    mRestoring=false;
    RoomGhostRoom* room=hookRoom();
    if(room==nullptr && mState!=0) { interrupt();return; }
    if(room!=nullptr) { room->restoreHunter(mCreature,mCreature.getGameMap()->getTile(mHookX,mHookY),mEquipped); }
    if(mState==6)
    {
        RoomGhostRoom* empty=roomNamed(*mCreature.getGameMap(),mEmptyRoom);
        if(empty!=nullptr && mDestination!=nullptr) empty->restoreCauldron(mCreature,mDestination);
    }
    if(!mLoadedPath.empty())
        mCreature.setWalkPath(EntityAnimation::walk_anim,EntityAnimation::idle_anim,true,true,mLoadedPath,false,true);
    if(mState==2) mBeamTarget=mTarget;
    mCreature.refreshGhostHuntVisuals();
}
