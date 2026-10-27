#include "rooms/RoomGhostRoom.h"
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
#include "network/ServerNotification.h"
#include "network/ODServer.h"
#include "spells/Spell.h"
#include "spells/SpellEyeEvil.h"
#include "ai/KeeperAI.h"
#include "utils/ConfigManager.h"
#include "utils/Random.h"
#include "utils/MakeUnique.h"
#include <algorithm>
#include <limits>
#include <set>

namespace
{
const std::string roomName = "GhostRoom";
const std::string readableName = "Ghost room";
//! \brief Orders tiles by increasing y, then x, independently of pointers.
bool tileOrder(Tile* a, Tile* b)
{ return std::make_pair(a->getY(),a->getX()) < std::make_pair(b->getY(),b->getX()); }
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
}

void RoomGhostRoom::createCauldronObjects()
{
    std::vector<BuildingObject*> oldCauldrons;
    for(const std::pair<Tile* const,BuildingObject*>& entry : getBuildingObjects())
        if(entry.second->getMeshName()=="GhostCauldron" || entry.second->getMeshName()=="CrystalBowl") oldCauldrons.push_back(entry.second);
    for(BuildingObject* object : oldCauldrons) removeBuildingObject(object);
    mCauldronObjects.clear();
    mBowl=nullptr;
    std::set<Tile*> occupied;
    for(const Cauldron& cauldron : mCauldrons)
    {
        Tile* tile=cauldron.anchor;
        BuildingObject* object=new BuildingObject(getGameMap(),*this,"GhostCauldron",tile,
            tile->getX()+0.5f,tile->getY()+0.5f,0.0f,0.0f,false);
        object->setFurnitureScale(Ogre::Vector2(1.0f,1.0f));
        addBuildingObject(tile,object); object->createMesh(); mCauldronObjects.push_back(object);
        for(int y=0;y<2;++y) for(int x=0;x<2;++x) occupied.insert(getGameMap()->getTile(tile->getX()+x,tile->getY()+y));
    }
    if(mCauldrons.empty()) return;
    Tile* first=mCauldrons.front().anchor;
    std::vector<Tile*> candidates=mCoveredTiles;
    std::sort(candidates.begin(),candidates.end(),tileOrder);
    for(Tile* tile : candidates)
    {
        if(occupied.count(tile) || std::abs(tile->getX()-first->getX())>2 || std::abs(tile->getY()-first->getY())>2) continue;
        bool inner=true;
        for(int y=-1;y<=1;++y) for(int x=-1;x<=1;++x)
            if(std::find(mCoveredTiles.begin(),mCoveredTiles.end(),getGameMap()->getTile(tile->getX()+x,tile->getY()+y))==mCoveredTiles.end()) inner=false;
        if(!inner) continue;
        mBowl=tile;
        BuildingObject* bowl=new BuildingObject(getGameMap(),*this,"CrystalBowl",*tile,0.0f,false);
        addBuildingObject(tile,bowl); bowl->createMesh(); break;
    }
}

void RoomGhostRoom::updateActiveSpots(GameMap* map)
{
    if(!getIsOnServerMap() || mLayingOut) return;
    mLayingOut=true;
    layoutCauldrons();
    std::vector<BuildingObject*> decorations;
    for(const std::pair<Tile* const,BuildingObject*>& entry : getBuildingObjects())
        if(entry.second->getMeshName()!="GhostCauldron" && entry.second->getMeshName()!="CrystalBowl") decorations.push_back(entry.second);
    for(BuildingObject* object : decorations) removeBuildingObject(object);
    mDecorationTiles.clear();mHookTiles.clear();
    std::vector<Tile*> ordered=mCoveredTiles;
    std::sort(ordered.begin(),ordered.end(),tileOrder);
    // Use actual wall-adjacent edge tiles rather than the default 3x3 central-spot grid.
    for(Tile* tile : ordered)
    {
        const int dx[]={0,-1,1,0},dy[]={1,0,0,-1};
        for(int i=0;i<4;++i)
        {
            Tile* neighbor=getGameMap()->getTile(tile->getX()+dx[i],tile->getY()+dy[i]);
            if(neighbor==nullptr || !neighbor->isFullTile()) continue;
            ActiveSpotPlace place=i==0?activeSpotTop:i==1?activeSpotLeft:i==2?activeSpotRight:activeSpotBottom;
            BuildingObject* object=notifyActiveSpotCreated(place,tile);
            addBuildingObject(tile,object,map);object->createMesh();break;
        }
    }
    createCauldronObjects();
    for(const std::pair<Creature* const,Tile*>& hook : mHooks) equipHook(*hook.first,true);
    mLayingOut=false;
}

BuildingObject* RoomGhostRoom::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    if(place==activeSpotCenter) return nullptr;
    std::string mesh=mDecorationTiles.empty()?"GhostBell":mHookTiles.size()<getBackpackCount()?"GhostHook":"GhostWallGauges";
    if(mesh=="GhostHook") mHookTiles.push_back(tile);
    mDecorationTiles.push_back(tile);
    const double rotation=place==activeSpotLeft?90.0:place==activeSpotRight?270.0:place==activeSpotBottom?180.0:0.0;
    return new BuildingObject(getGameMap(),*this,mesh,*tile,rotation,false);
}

void RoomGhostRoom::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    if(place!=activeSpotCenter) removeBuildingObject(tile);
}

Tile* RoomGhostRoom::reserveHook(Creature& hunter)
{
    if(mHooks.count(&hunter)) return mHooks[&hunter];
    Tile* best=nullptr;size_t distance=std::numeric_limits<size_t>::max();
    for(Tile* tile : mHookTiles)
    {
        bool used=false;
        for(const std::pair<Creature* const,Tile*>& hook : mHooks) if(hook.second==tile) used=true;
        if(used) continue;
        std::list<Tile*> path=getGameMap()->path(&hunter,tile);
        if(!path.empty() && path.size()<distance) { best=tile;distance=path.size(); }
    }
    if(best!=nullptr) mHooks[&hunter]=best;
    return best;
}

void RoomGhostRoom::equipHook(Creature& hunter, bool equipped)
{
    if(!mHooks.count(&hunter)) return;
    Tile* tile=mHooks[&hunter];
    BuildingObject* old=getBuildingObjectFromTile(tile);
    if(old==nullptr) return;
    BuildingObject* replacement=new BuildingObject(getGameMap(),*this,equipped?"GhostHookEmpty":"GhostHook",tile,
        old->getPosition().x,old->getPosition().y,old->getPosition().z,old->getRotationAngle(),false);
    replaceBuildingObject(tile,replacement);
}

void RoomGhostRoom::releaseHunter(Creature& hunter)
{
    equipHook(hunter,false);mHooks.erase(&hunter);
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
    for(Creature* hunter : hunters) hunter->interruptGhostHunt();
}

void RoomGhostRoom::absorbRoom(Room* room)
{
    RoomGhostRoom* other=static_cast<RoomGhostRoom*>(room);
    mCauldrons.insert(mCauldrons.end(),other->mCauldrons.begin(),other->mCauldrons.end());
    mHooks.insert(other->mHooks.begin(),other->mHooks.end());
    mCauldronObjects.insert(mCauldronObjects.end(),other->mCauldronObjects.begin(),other->mCauldronObjects.end());
    mDecorationTiles.insert(mDecorationTiles.end(),other->mDecorationTiles.begin(),other->mDecorationTiles.end());
    other->mHooks.clear();other->mCauldrons.clear();other->mCauldronObjects.clear();other->mDecorationTiles.clear();other->mBowl=nullptr;
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
        if(complete) { other.mCauldrons.push_back(*it); it=mCauldrons.erase(it); } else ++it;
    }
    interruptHunters(); updateActiveSpots(); other.updateActiveSpots();
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
{ interruptHunters(); Room::removeFromGameMap(map); }

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
        seat->setEctoplasmLevels(seat->getEctoplasmLevels()-getLevelsPerEctoplasm(*seat));
        Spell::fireSpellEffect(*cauldron,"EctoplasmBurst","");
        CreatureActionHuntGhost::playSound(*getGameMap(),*cauldron,"Rooms/GhostRoom/PressHiss");
        if(seat->getGhostProduct()==GhostProduct::mana) seat->addMana(config.getRoomConfigDouble("GhostEctoplasmMana"));
        else if(seat->getGhostProduct()==GhostProduct::research) seat->addSkillPoints(config.getRoomConfigInt32("GhostEctoplasmResearchPoints"));
        else
        {
            Tile* bowl=mBowl==nullptr?cauldron:mBowl;
            ItemBagEntity* bag=new ItemBagEntity(getGameMap(),ItemInstance::createSoulCrystal());
            bag->setSeat(seat);bag->setPosition(Ogre::Vector3(bowl->getX(),bowl->getY(),0.0f));
            bag->addToGameMap();bag->createMesh();
            CreatureActionHuntGhost::playSound(*getGameMap(),*bowl,"Rooms/GhostRoom/CrystalRing");
        }
    }
}

void RoomGhostRoom::doUpkeep()
{
    Room::doUpkeep();
    const std::vector<Room*> rooms=getGameMap()->getRoomsByTypeAndSeat(RoomType::ghostRoom,getSeat());
    if(rooms.empty() || rooms.front()!=this) return;
    CreatureActionHuntGhost::assignHunters(*getGameMap(),*getSeat());
}

void RoomGhostRoom::restoreHunter(Creature& hunter, Tile* hook, bool equipped)
{
    if(hook==nullptr || hook->getCoveringRoom()!=this) return;
    mHooks[&hunter]=hook;equipHook(hunter,equipped);
}
void RoomGhostRoom::restoreCauldron(Creature& hunter, Tile* standing)
{
    for(Cauldron& cauldron : mCauldrons)
        if(standing!=nullptr && std::abs(standing->getX()-cauldron.anchor->getX())<=2 && std::abs(standing->getY()-cauldron.anchor->getY())<=2)
        { cauldron.hunter=&hunter;return; }
}

void RoomGhostRoom::releaseCauldron(Creature& hunter)
{
    for(Cauldron& cauldron : mCauldrons) if(cauldron.hunter==&hunter) cauldron.hunter=nullptr;
    releaseInteractionPosition(&hunter);
}
