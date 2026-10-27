#include "rooms/RoomGhostRoom.h"
#include "ODApplication.h"
#include "rooms/RoomManager.h"
#include "creatureaction/CreatureActionHuntGhost.h"
#include "entities/BuildingObject.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GhostEntity.h"
#include "entities/GhostBoxEntity.h"
#include "entities/ItemBagEntity.h"
#include "entities/ItemInstance.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "game/SkillManager.h"
#include "game/SkillType.h"
#include "gamemap/GameMap.h"
#include "gamemap/RoomObjectBounds.h"
#include "network/ServerNotification.h"
#include "network/ODServer.h"
#include "spells/Spell.h"
#include "spells/SpellEyeEvil.h"
#include "ai/KeeperAI.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"
#include "utils/MakeUnique.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <set>

namespace
{
const std::string roomName = "GhostRoom";
const std::string readableName = "Ghost room";
//! \brief Orders tiles by increasing y, then x, independently of pointers.
bool tileOrder(Tile* a, Tile* b)
{ return std::make_pair(a->getY(),a->getX()) < std::make_pair(b->getY(),b->getX()); }
//! \brief Orders cauldrons by the same deterministic anchor order as the scan.
bool cauldronOrder(const RoomGhostRoom::Cauldron& a,const RoomGhostRoom::Cauldron& b)
{ return tileOrder(a.anchor,b.anchor); }
//! \brief Registers the ghost room and validates its joined floor before charging.
class RoomGhostRoomFactory : public RoomFactory
{
    //! \brief Returns the appended room type.
    RoomType getRoomType() const override { return RoomType::ghostRoom; }
    //! \brief Returns the matching appended tile visual.
    TileVisual getVisualType() const override { return TileVisual::ghostRoom; }
    //! \brief Returns the configuration name.
    const std::string& getName() const override { return roomName; }
    //! \brief Returns the player-facing room name.
    const std::string& getNameReadable() const override { return readableName; }
    //! \brief Reads the prescribed gold price per tile.
    int getCostPerTile() const override { return ConfigManager::getSingleton().getRoomConfigInt32("GhostRoomCostPerTile"); }
    //! \brief Previews the ordinary room selection.
    void checkBuildRoom(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefault(map,RoomType::ghostRoom,input,command); }
    //! \brief Reads the selection and validates the resulting room.
    bool buildRoom(GameMap* map, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles,map,player,packet)) return false;
        return buildRoomOnTiles(map,player,tiles);
    }
    //! \brief Builds only if the union with adjoining own rooms contains the minimum square.
    bool buildRoomOnTiles(GameMap* map, Player* player, const std::vector<Tile*>& tiles, bool noFee=false) const override
    {
        if(!RoomGhostRoom::containsMinimumBlock(*map,player->getSeat(),tiles))
        {
            ServerNotification* notice = new ServerNotification(ServerNotificationType::chatServer,player);
            notice->mPacket << std::string("A ghost room needs at least 4x4 tiles.") << EventShortNoticeType::genericGameInfo;
            ODServer::getSingleton().queueServerNotification(notice);
            return false;
        }
        if(!noFee && !map->withdrawFromTreasuries(static_cast<int32_t>(tiles.size())*getCostPerTile(),player->getSeat())) return false;
        return buildRoomDefault(map,new RoomGhostRoom(map),player->getSeat(),tiles);
    }
    //! \brief Previews editor tiles.
    void checkBuildRoomEditor(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefaultEditor(map,RoomType::ghostRoom,input,command); }
    //! \brief Builds editor furniture without a gold charge.
    bool buildRoomEditor(GameMap* map, ODPacket& packet) const override
    { return buildRoomDefaultEditor(map,new RoomGhostRoom(map),packet); }
    //! \brief Creates an empty room after a split.
    Room* createRoom(GameMap* map) const override { return new RoomGhostRoom(map); }
    //! \brief Loads the base room floor; furniture is recomputed.
    Room* getRoomFromStream(GameMap* map, std::istream& stream) const override
    {
        RoomGhostRoom* room = new RoomGhostRoom(map);
        Room::importRoomFromStream(*room,stream);
        return room;
    }
};
static RoomRegister registration(new RoomGhostRoomFactory);
}

RoomGhostRoom::RoomGhostRoom(GameMap* map) : Room(map)
{ setMeshName(roomName); }

bool RoomGhostRoom::containsMinimumBlock(GameMap& map, Seat* seat, const std::vector<Tile*>& tiles)
{
    std::set<Tile*> floor(tiles.begin(),tiles.end());
    std::vector<Tile*> pending(tiles);
    while(!pending.empty())
    {
        Tile* tile = pending.back(); pending.pop_back();
        for(Tile* neighbor : tile->getAllNeighbors())
        {
            Room* room = neighbor->getCoveringRoom();
            if(room == nullptr || room->getType()!=RoomType::ghostRoom || room->getSeat()!=seat) continue;
            for(Tile* joined : room->getCoveredTiles())
                if(floor.insert(joined).second) pending.push_back(joined);
        }
    }
    const int side = ConfigManager::getSingleton().getRoomConfigInt32("GhostRoomMinSide");
    for(Tile* tile : floor)
    {
        bool full = true;
        for(int y=0;y<side;++y) for(int x=0;x<side;++x)
            if(floor.count(map.getTile(tile->getX()+x,tile->getY()+y))==0) full=false;
        if(full) return true;
    }
    return false;
}

uint32_t RoomGhostRoom::getBackpackCount() const
{ return static_cast<uint32_t>(mCauldrons.size())*ConfigManager::getSingleton().getRoomConfigUInt32("GhostHuntersPerCauldron"); }

double RoomGhostRoom::getLevelsPerEctoplasm(const Seat& seat)
{ return SkillManager::getResearchValue(&seat,SkillType::roomGhostRoom,ConfigManager::getSingleton().getRoomConfigDouble("GhostLevelsPerEctoplasm"),"EctoplasmLevels"); }

void RoomGhostRoom::layoutCauldrons()
{
    std::set<Tile*> floor(mCoveredTiles.begin(),mCoveredTiles.end()), inner;
    for(Tile* tile : mCoveredTiles)
    {
        bool inside=true;
        for(int y=-1;y<=1;++y) for(int x=-1;x<=1;++x)
            if(floor.count(getGameMap()->getTile(tile->getX()+x,tile->getY()+y))==0) inside=false;
        if(inside) inner.insert(tile);
    }
    std::vector<Cauldron> retained;
    for(const Cauldron& cauldron : mCauldrons)
    {
        if(cauldron.hunter==nullptr) continue;
        bool intact=true;
        for(int y=0;y<2;++y) for(int x=0;x<2;++x)
            if(floor.count(getGameMap()->getTile(cauldron.anchor->getX()+x,cauldron.anchor->getY()+y))==0) intact=false;
        if(intact) retained.push_back(cauldron);
        else cauldron.hunter->interruptGhostHunt();
    }
    mCauldrons=retained;
    std::vector<Tile*> ordered(inner.begin(),inner.end());
    std::sort(ordered.begin(),ordered.end(),tileOrder);
    for(Tile* anchor : ordered)
    {
        bool valid=true;
        for(int y=0;y<2;++y) for(int x=0;x<2;++x)
            if(inner.count(getGameMap()->getTile(anchor->getX()+x,anchor->getY()+y))==0) valid=false;
        for(const Cauldron& placed : mCauldrons)
            if(std::abs(anchor->getX()-placed.anchor->getX())<=2 && std::abs(anchor->getY()-placed.anchor->getY())<=2) valid=false;
        if(valid) mCauldrons.push_back(Cauldron{anchor,nullptr});
    }
    std::sort(mCauldrons.begin(),mCauldrons.end(),cauldronOrder);
}

void RoomGhostRoom::createCauldronObjects()
{
    std::vector<BuildingObject*> oldCauldrons;
    for(const std::pair<Tile* const,BuildingObject*>& entry : getBuildingObjects())
        if(entry.second->getMeshName()=="GhostCauldron") oldCauldrons.push_back(entry.second);
    for(BuildingObject* object : oldCauldrons) removeBuildingObject(object);
    mCauldronObjects.clear();
    for(const Cauldron& cauldron : mCauldrons)
    {
        Tile* tile=cauldron.anchor;
        BuildingObject* object=new BuildingObject(getGameMap(),*this,"GhostCauldron",tile,
            tile->getX()+0.5f,tile->getY()+0.5f,0.0f,0.0f,false);
        object->setFurnitureScale(Ogre::Vector2(1.0f,1.0f));
        object->setGhostRoomState(getSeat()->getEctoplasmLevels()/getLevelsPerEctoplasm(*getSeat()),mAlarmTurns);
        addBuildingObject(tile,object); object->createMesh(); mCauldronObjects.push_back(object);
        if(cauldron.hunter!=nullptr)
        {
            std::map<Creature*,InteractionPosition>::iterator occupied=mInteractionPositions.find(cauldron.hunter);
            if(occupied!=mInteractionPositions.end()) occupied->second.object=object;
        }
    }
}

Tile* RoomGhostRoom::findCrystalDropTile(const Tile& cauldron) const
{
    Tile* best=nullptr;double distance=std::numeric_limits<double>::max();
    for(Tile* tile : mCoveredTiles)
    {
        // Tiles under any cauldron are never used; the bag itself is no obstacle, so every other floor tile keeps all passages free.
        bool underCauldron=false;
        for(const Cauldron& placed : mCauldrons)
            if(tile->getX()>=placed.anchor->getX() && tile->getX()<=placed.anchor->getX()+1 &&
               tile->getY()>=placed.anchor->getY() && tile->getY()<=placed.anchor->getY()+1) underCauldron=true;
        if(underCauldron) continue;
        const double dx=tile->getX()-(cauldron.getX()+0.5),dy=tile->getY()-(cauldron.getY()+0.5);
        const double squared=dx*dx+dy*dy;
        if(best==nullptr || squared<distance || (squared==distance && tileOrder(tile,best))) { best=tile;distance=squared; }
    }
    return best;
}

void RoomGhostRoom::updateActiveSpots(GameMap* map)
{
    if(!getIsOnServerMap() || mLayingOut) return;
    mLayingOut=true;
    layoutCauldrons();
    clearWallObjects();
    mDecorationTiles.clear();mHookTiles.clear();mHookObjects.clear();
    std::vector<Tile*> ordered=mCoveredTiles;
    std::sort(ordered.begin(),ordered.end(),tileOrder);
    typedef std::pair<Tile*,ActiveSpotPlace> Wall;
    std::vector<Wall> walls;
    for(Tile* tile : ordered)
    {
        const int dx[]={0,-1,1,0},dy[]={1,0,0,-1};
        for(int i=0;i<4;++i)
        {
            Tile* neighbor=getGameMap()->getTile(tile->getX()+dx[i],tile->getY()+dy[i]);
            if(neighbor==nullptr || !neighbor->isFullTile()) continue;
            walls.push_back(Wall(tile,i==0?activeSpotTop:i==1?activeSpotLeft:i==2?activeSpotRight:activeSpotBottom));
        }
    }
    // A free-standing room has no adjacent wall: bell, hooks and gauges then stand on racks along the open room edge.
    // They stay decoration (no obstacle), so every passage remains free, and the supply is not reduced.
    const bool rackEdge=walls.empty();
    if(rackEdge)
    {
        for(Tile* tile : ordered)
        {
            const int dx[]={0,-1,1,0},dy[]={1,0,0,-1};
            for(int i=0;i<4;++i)
            {
                Tile* neighbor=getGameMap()->getTile(tile->getX()+dx[i],tile->getY()+dy[i]);
                if(neighbor!=nullptr && neighbor->getCoveringRoom()==this) continue;
                walls.push_back(Wall(tile,i==0?activeSpotTop:i==1?activeSpotLeft:i==2?activeSpotRight:activeSpotBottom));
            }
        }
    }
    // Subdivide the wall faces (or room-edge rack faces) using the native mesh widths; decoration never overwrites a floor-object key.
    if(!walls.empty())
    {
        const size_t slots=std::max(walls.size(),static_cast<size_t>(getBackpackCount())+1);
        for(size_t slot=0;slot<slots;++slot)
        {
            const size_t wall=slot%walls.size(),part=slot/walls.size();
            const size_t parts=slots/walls.size()+(wall<slots%walls.size()?1:0);
            Tile* tile=walls[wall].first;ActiveSpotPlace place=walls[wall].second;
            BuildingObject* object=notifyActiveSpotCreated(place,tile);
            const double angle=object->getRotationAngle()*RoomObjectPath::degreesToRadians;
            const double gap=1.0/static_cast<double>(parts);
            const double along=-0.5+gap*(static_cast<double>(part)+0.5);
            double width=1.0,depth=0.0;
            for(const RoomObjectPath::MeshBounds& bounds : RoomObjectPath::meshBounds)
                if(object->getMeshName()==bounds.name) { width=bounds.maxX-bounds.minX;depth=bounds.maxY-bounds.minY;break; }
            const double forward=0.5-depth/2.0;
            object->setPosition(Ogre::Vector3(static_cast<float>(tile->getX()+std::cos(angle)*along-std::sin(angle)*forward),
                static_cast<float>(tile->getY()+std::sin(angle)*along+std::cos(angle)*forward),0.0f));
            object->setFurnitureScale(Ogre::Vector2(static_cast<float>(std::min(1.0,gap/width)),1.0f));
            object->addToGameMap(map);object->createMesh();mWallObjects.push_back(object);
            if(object->getMeshName()=="GhostHook") mHookObjects.push_back(object);
            if(rackEdge)
            {
                // The free-standing iron rack stands directly behind the item; it is walkable decoration, never an obstacle.
                const double behind=-depth/2.0+0.04;
                BuildingObject* rack=new BuildingObject(getGameMap(),*this,"GhostRack",tile,
                    object->getPosition().x-std::sin(angle)*behind,object->getPosition().y+std::cos(angle)*behind,0.0f,
                    object->getRotationAngle(),false);
                rack->setFurnitureScale(Ogre::Vector2(static_cast<float>(std::min(1.0,gap)),1.0f));
                rack->addToGameMap(map);rack->createMesh();mWallObjects.push_back(rack);
            }
        }
    }
    createCauldronObjects();
    std::vector<Creature*> hunters;
    for(const std::pair<Creature* const,Tile*>& hook : mHooks) hunters.push_back(hook.first);
    mHooks.clear();mHookSlots.clear();
    for(Creature* hunter : hunters) reserveHook(*hunter);
    for(Creature* hunter : hunters) equipHook(*hunter,hunter->hasGhostBackpack());
    mLayingOut=false;
}

BuildingObject* RoomGhostRoom::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    if(place==activeSpotCenter) return nullptr;
    std::string mesh=mDecorationTiles.empty()?"GhostBell":mHookTiles.size()<getBackpackCount()?"GhostHook":"GhostWallGauges";
    if(mesh=="GhostHook") mHookTiles.push_back(tile);
    mDecorationTiles.push_back(tile);
    const double rotation=place==activeSpotLeft?90.0:place==activeSpotRight?270.0:place==activeSpotBottom?180.0:0.0;
    return new BuildingObject(getGameMap(),*this,mesh,*tile,rotation,false,1.0f,mesh=="GhostWallGauges"?EntityAnimation::idle_anim:std::string(),true);
}

void RoomGhostRoom::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    if(place!=activeSpotCenter) removeBuildingObject(tile);
}

Tile* RoomGhostRoom::reserveHook(Creature& hunter)
{
    if(mHooks.count(&hunter)) return mHooks[&hunter];
    Tile* best=nullptr;size_t selected=0,distance=std::numeric_limits<size_t>::max();
    for(size_t index=0;index<mHookTiles.size();++index)
    {
        bool used=false;
        for(const std::pair<Creature* const,size_t>& hook : mHookSlots) if(hook.second==index) used=true;
        if(used) continue;
        const std::list<Tile*> path=getGameMap()->path(&hunter,mHookTiles[index]);
        if(!path.empty() && path.size()<distance) { best=mHookTiles[index];selected=index;distance=path.size(); }
    }
    if(best!=nullptr) { mHooks[&hunter]=best;mHookSlots[&hunter]=selected; }
    return best;
}

void RoomGhostRoom::equipHook(Creature& hunter,bool equipped)
{
    if(!mHookSlots.count(&hunter) || mHookSlots[&hunter]>=mHookObjects.size()) return;
    const size_t index=mHookSlots[&hunter];BuildingObject* old=mHookObjects[index];
    const std::string mesh=equipped?"GhostHookEmpty":"GhostHook";
    if(old->getMeshName()==mesh) return;
    Tile* tile=mHookTiles[index];
    BuildingObject* replacement=new BuildingObject(getGameMap(),*this,mesh,tile,
        old->getPosition().x,old->getPosition().y,old->getPosition().z,old->getRotationAngle(),false);
    replacement->setFurnitureScale(old->getFurnitureScale());
    replacement->addToGameMap();replacement->setPosition(replacement->getPosition());replacement->notifyReplacement(*old);
    for(BuildingObject*& object : mWallObjects) if(object==old) { object=replacement;break; }
    mHookObjects[index]=replacement;old->removeFromGameMap();old->deleteYourself();
}

void RoomGhostRoom::releaseHunter(Creature& hunter)
{
    equipHook(hunter,false);mHooks.erase(&hunter);mHookSlots.erase(&hunter);
    releaseCauldron(hunter);
}

Tile* RoomGhostRoom::reserveCauldron(Creature& hunter)
{
    for(Cauldron& cauldron : mCauldrons)
    {
        if(cauldron.hunter!=nullptr && cauldron.hunter!=&hunter) continue;
        Tile* best=nullptr;size_t distance=std::numeric_limits<size_t>::max();
        for(int y=-1;y<=2;++y) for(int x=-1;x<=2;++x)
        {
            if(x>=0 && x<2 && y>=0 && y<2) continue;
            Tile* tile=getGameMap()->getTile(cauldron.anchor->getX()+x,cauldron.anchor->getY()+y);
            if(tile==nullptr || tile->getCoveringRoom()!=this) continue;
            bool used=false;
            for(const std::pair<Creature* const,InteractionPosition>& spot : mInteractionPositions)
                if(spot.first!=&hunter && spot.second.position==Ogre::Vector2(tile->getX(),tile->getY())) used=true;
            if(used) continue;
            std::list<Tile*> path=getGameMap()->path(&hunter,tile);
            if(!path.empty() && path.size()<distance) { best=tile;distance=path.size(); }
        }
        if(best==nullptr) continue;
        cauldron.hunter=&hunter;
        reserveInteractionPosition(&hunter,InteractionPosition{getBuildingObjectFromTile(cauldron.anchor),Ogre::Vector2(best->getX(),best->getY()),Ogre::Vector2(cauldron.anchor->getX()-best->getX(),cauldron.anchor->getY()-best->getY())});
        return best;
    }
    return nullptr;
}

void RoomGhostRoom::interruptHunters()
{
    std::vector<Creature*> hunters;
    for(const std::pair<Creature* const,Tile*>& hook : mHooks) hunters.push_back(hook.first);
    for(const Cauldron& cauldron : mCauldrons)
        if(cauldron.hunter!=nullptr && std::find(hunters.begin(),hunters.end(),cauldron.hunter)==hunters.end()) hunters.push_back(cauldron.hunter);
    for(Creature* hunter : hunters) hunter->interruptGhostHunt();
}

void RoomGhostRoom::absorbRoom(Room* room)
{
    RoomGhostRoom* other=static_cast<RoomGhostRoom*>(room);
    mCauldrons.insert(mCauldrons.end(),other->mCauldrons.begin(),other->mCauldrons.end());
    for(Creature* hunter : getGameMap()->getCreaturesBySeat(getSeat()))
        hunter->transferGhostHuntRoom(other->getName(),getName(),true,true);
    mHooks.insert(other->mHooks.begin(),other->mHooks.end());
    mCauldronObjects.insert(mCauldronObjects.end(),other->mCauldronObjects.begin(),other->mCauldronObjects.end());
    mDecorationTiles.insert(mDecorationTiles.end(),other->mDecorationTiles.begin(),other->mDecorationTiles.end());
    mWallObjects.insert(mWallObjects.end(),other->mWallObjects.begin(),other->mWallObjects.end());
    other->mWallObjects.clear();other->mHookObjects.clear();other->mHookSlots.clear();
    other->mHooks.clear();other->mCauldrons.clear();other->mCauldronObjects.clear();other->mDecorationTiles.clear();
    Room::absorbRoom(room); updateActiveSpots();
}

void RoomGhostRoom::splitRoom(Room& room, const std::vector<Tile*>& tiles)
{
    RoomGhostRoom& other=static_cast<RoomGhostRoom&>(room);
    for(std::vector<Cauldron>::iterator it=mCauldrons.begin();it!=mCauldrons.end();)
    {
        bool complete=true;
        for(int y=0;y<2;++y) for(int x=0;x<2;++x)
            if(std::find(tiles.begin(),tiles.end(),getGameMap()->getTile(it->anchor->getX()+x,it->anchor->getY()+y))==tiles.end()) complete=false;
        if(complete)
        {
            other.mCauldrons.push_back(*it);
            if(it->hunter!=nullptr)
            {
                std::map<Creature*,InteractionPosition>::iterator standing=mInteractionPositions.find(it->hunter);
                if(standing!=mInteractionPositions.end())
                { other.mInteractionPositions.insert(*standing);mInteractionPositions.erase(standing); }
            }
            it=mCauldrons.erase(it);
        }
        else ++it;
    }
    for(std::map<Creature*,Tile*>::iterator it=mHooks.begin();it!=mHooks.end();)
    {
        if(std::find(tiles.begin(),tiles.end(),it->second)!=tiles.end())
        {
            other.mHooks.insert(*it);mHookSlots.erase(it->first);it->first->transferGhostHuntRoom(getName(),other.getName(),true,false);
            it=mHooks.erase(it);
        }
        else ++it;
    }
    for(const Cauldron& cauldron : other.mCauldrons)
        if(cauldron.hunter!=nullptr) cauldron.hunter->transferGhostHuntRoom(getName(),other.getName(),false,true);
    updateActiveSpots(); other.updateActiveSpots();
}

bool RoomGhostRoom::removeCoveredTile(Tile* tile)
{
    for(const Cauldron& cauldron : mCauldrons)
        if(tile->getX()>=cauldron.anchor->getX() && tile->getX()<=cauldron.anchor->getX()+1 &&
           tile->getY()>=cauldron.anchor->getY() && tile->getY()<=cauldron.anchor->getY()+1 && cauldron.hunter!=nullptr)
            cauldron.hunter->interruptGhostHunt();
    const bool removed=Room::removeCoveredTile(tile);
    updateActiveSpots();return removed;
}

void RoomGhostRoom::changeOwner(Seat* seat)
{ interruptHunters(); Room::changeOwner(seat); updateActiveSpots(); }

void RoomGhostRoom::removeFromGameMap(GameMap* map)
{ interruptHunters();clearWallObjects();Room::removeFromGameMap(map); }

void RoomGhostRoom::emptyGhost(Creature& hunter, GhostEntity& ghost)
{
    Tile* cauldron=nullptr;
    for(const Cauldron& spot : mCauldrons) if(spot.hunter==&hunter) cauldron=spot.anchor;
    if(cauldron==nullptr) return;
    Seat* seat=getSeat();
    if(ghost.getSeat()!=nullptr && !seat->isAlliedSeat(ghost.getSeat()))
    {
        std::vector<Tile*> unseen,all;
        for(int y=0;y<getGameMap()->getMapSizeY();++y) for(int x=0;x<getGameMap()->getMapSizeX();++x)
        {
            Tile* tile=getGameMap()->getTile(x,y);
            if(!tile->isClaimedForSeat(ghost.getSeat())) continue;
            all.push_back(tile);if(!seat->hasSeenTile(tile)) unseen.push_back(tile);
        }
        const std::vector<Tile*>& candidates=unseen.empty()?all:unseen;
        if(!candidates.empty()) SpellEyeEvil::spawnFree(getGameMap(),seat,candidates[Random::Uint(0,static_cast<uint32_t>(candidates.size()-1))],ConfigManager::getSingleton().getSpellConfigInt32("EyeEvilNbTurns"));
    }
    seat->setEctoplasmLevels(seat->getEctoplasmLevels()+ghost.getLevel());
    ghost.removeFromGameMap();ghost.deleteYourself();
    ConfigManager& config=ConfigManager::getSingleton();
    while(seat->getEctoplasmLevels()>=getLevelsPerEctoplasm(*seat))
    {
        KeeperAI::updateGhostRoomSettings(*seat);
        const bool crystal=seat->getGhostProduct()==GhostProduct::crystal;
        // A soul crystal costs several ectoplasm; the bar keeps its rest until enough levels are collected.
        const double cost=getLevelsPerEctoplasm(*seat)*(crystal?config.getRoomConfigDouble("GhostEctoplasmPerCrystal"):1.0);
        if(seat->getEctoplasmLevels()<cost) break;
        Tile* drop=crystal?findCrystalDropTile(*cauldron):nullptr;
        if(crystal && drop==nullptr) break;
        seat->setEctoplasmLevels(seat->getEctoplasmLevels()-cost);
        Spell::fireSpellEffect(*cauldron,"EctoplasmBurst","");
        CreatureActionHuntGhost::playSound(*getGameMap(),*cauldron,"Rooms/GhostRoom/PressHiss");
        if(seat->getGhostProduct()==GhostProduct::mana) seat->addMana(config.getRoomConfigDouble("GhostEctoplasmMana"));
        else if(seat->getGhostProduct()==GhostProduct::research) seat->addSkillPoints(config.getRoomConfigInt32("GhostEctoplasmResearchPoints"));
        else
        {
            // The finished crystal falls as a bag onto a free floor tile of the room.
            ItemBagEntity* bag=new ItemBagEntity(getGameMap(),ItemInstance::createSoulCrystal());
            bag->setSeat(seat);bag->setPosition(Ogre::Vector3(drop->getX(),drop->getY(),0.0f));
            bag->addToGameMap();bag->createMesh();
            CreatureActionHuntGhost::playSound(*getGameMap(),*drop,"Rooms/GhostRoom/CrystalRing");
        }
    }
}

void RoomGhostRoom::doUpkeep()
{
    Room::doUpkeep();
    mAlarmTurns=std::max(0.0,mAlarmTurns-1.0);
    const double fill=getSeat()->getEctoplasmLevels()/getLevelsPerEctoplasm(*getSeat());
    for(const std::pair<Tile* const,BuildingObject*>& entry : getBuildingObjects())
        entry.second->setGhostRoomState(entry.second->getMeshName()=="GhostCauldron"?fill:-1.0,mAlarmTurns);
    for(BuildingObject* object : mWallObjects) object->setGhostRoomState(-1.0,mAlarmTurns);
    const std::vector<Room*> rooms=getGameMap()->getRoomsByTypeAndSeat(RoomType::ghostRoom,getSeat());
    if(rooms.empty() || rooms.front()!=this) return;
    CreatureActionHuntGhost::assignHunters(*getGameMap(),*getSeat());
}

void RoomGhostRoom::restoreHunter(Creature& hunter,Tile* hook,bool equipped,size_t slot)
{
    if(slot<mHookTiles.size()) { mHooks[&hunter]=mHookTiles[slot];mHookSlots[&hunter]=slot; }
    else if(hook!=nullptr && hook->getCoveringRoom()==this) reserveHook(hunter);
    equipHook(hunter,equipped);
}

void RoomGhostRoom::restoreCauldron(Creature& hunter,Tile* standing,Tile* anchor,bool rebuild)
{
    if(standing==nullptr || anchor==nullptr) return;
    bool complete=true;
    for(int y=0;y<2;++y) for(int x=0;x<2;++x)
    {
        Tile* tile=getGameMap()->getTile(anchor->getX()+x,anchor->getY()+y);
        if(tile==nullptr || tile->getCoveringRoom()!=this) complete=false;
    }
    if(!complete) return;
    bool found=false;
    for(Cauldron& cauldron : mCauldrons)
        if(cauldron.anchor==anchor) { cauldron.hunter=&hunter;found=true;break; }
    if(!found) mCauldrons.push_back(Cauldron{anchor,&hunter});
    if(rebuild) updateActiveSpots();
    reserveInteractionPosition(&hunter,InteractionPosition{getBuildingObjectFromTile(anchor),Ogre::Vector2(standing->getX(),standing->getY()),Ogre::Vector2(anchor->getX()-standing->getX(),anchor->getY()-standing->getY())});
}

void RoomGhostRoom::ringBell()
{
    if(getCentralTile()!=nullptr) CreatureActionHuntGhost::playSound(*getGameMap(),*getCentralTile(),"Rooms/GhostRoom/Bell");
    mAlarmTurns=ConfigManager::getSingleton().getRoomConfigDouble("GhostBellSeconds")*ODApplication::turnsPerSecond;
    const double fill=getSeat()->getEctoplasmLevels()/getLevelsPerEctoplasm(*getSeat());
    for(const std::pair<Tile* const,BuildingObject*>& entry : getBuildingObjects())
        entry.second->setGhostRoomState(entry.second->getMeshName()=="GhostCauldron"?fill:-1.0,mAlarmTurns);
    for(BuildingObject* object : mWallObjects) object->setGhostRoomState(-1.0,mAlarmTurns);
}

Tile* RoomGhostRoom::getHunterCauldron(const Creature& hunter) const
{
    for(const Cauldron& cauldron : mCauldrons) if(cauldron.hunter==&hunter) return cauldron.anchor;
    return nullptr;
}

void RoomGhostRoom::releaseCauldron(Creature& hunter)
{
    for(Cauldron& cauldron : mCauldrons) if(cauldron.hunter==&hunter) cauldron.hunter=nullptr;
    releaseInteractionPosition(&hunter);
}

RoomGhostRoom::~RoomGhostRoom()
{ clearWallObjects(); }

void RoomGhostRoom::clearWallObjects()
{
    for(BuildingObject* object : mWallObjects)
        if(std::find(getGameMap()->getRenderedMovableEntities().begin(),getGameMap()->getRenderedMovableEntities().end(),object)!=getGameMap()->getRenderedMovableEntities().end())
        { object->removeFromGameMap();object->deleteYourself(); }
    mWallObjects.clear();mHookObjects.clear();
}

size_t RoomGhostRoom::getHunterHookSlot(const Creature& hunter) const
{
    std::map<Creature*,size_t>::const_iterator found=mHookSlots.find(const_cast<Creature*>(&hunter));
    return found==mHookSlots.end()?std::numeric_limits<size_t>::max():found->second;
}
