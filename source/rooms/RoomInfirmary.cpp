#include "rooms/RoomInfirmary.h"
#include "rooms/RoomManager.h"
#include "creatureaction/CreatureActionInfirmaryRest.h"
#include "creatureaction/CreatureActionSleep.h"
#include "creatureaction/CreatureActionCarryEntity.h"
#include "entities/BuildingObject.h"
#include "entities/InfirmaryShamanEntity.h"
#include "entities/Creature.h"
#include "entities/CreatureDefinition.h"
#include "entities/GameEntityType.h"
#include "entities/Tile.h"
#include "game/Player.h"
#include "game/Seat.h"
#include "gamemap/GameMap.h"
#include "network/ServerNotification.h"
#include "network/ODServer.h"
#include "utils/ConfigManager.h"
#include "utils/MakeUnique.h"
#include <algorithm>
#include <limits>
#include <queue>
#include <set>
#include <tuple>

namespace
{
const size_t noCot = std::numeric_limits<size_t>::max();
const std::string roomName = "Infirmary";
//! \brief Orders floor tiles independently of pointer addresses.
bool tileOrder(Tile* left, Tile* right)
{ return std::make_pair(left->getX(), left->getY()) < std::make_pair(right->getX(), right->getY()); }
//! \brief Builds infirmaries only when the joined floor contains the minimum square.
class RoomInfirmaryFactory : public RoomFactory
{
    //! \brief Returns the registered room type.
    RoomType getRoomType() const override { return RoomType::infirmary; }
    //! \brief Returns the floor visual.
    TileVisual getVisualType() const override { return TileVisual::infirmaryRoom; }
    //! \brief Returns the configuration name.
    const std::string& getName() const override { return roomName; }
    //! \brief Returns the player name.
    const std::string& getNameReadable() const override { return roomName; }
    //! \brief Returns the configured tile price.
    int getCostPerTile() const override { return ConfigManager::getSingleton().getRoomConfigInt32("InfirmaryCostPerTile"); }
    //! \brief Previews the normal build selection.
    void checkBuildRoom(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefault(map, RoomType::infirmary, input, command); }
    //! \brief Validates the floor before charging for a room.
    bool buildRoom(GameMap* map, Player* player, ODPacket& packet) const override
    {
        std::vector<Tile*> tiles;
        if(!getRoomTilesDefault(tiles, map, player, packet)) return false;
        return buildRoomOnTiles(map, player, tiles);
    }
    //! \brief Builds a validated square, including extensions of existing infirmaries.
    bool buildRoomOnTiles(GameMap* map, Player* player, const std::vector<Tile*>& tiles, bool noFee = false) const override
    {
        if(!RoomInfirmary::containsMinimumBlock(*map, player->getSeat(), tiles))
        {
            ServerNotification* notice = new ServerNotification(ServerNotificationType::chatServer, player);
            notice->mPacket << std::string("An infirmary needs at least 4x4 tiles.") << EventShortNoticeType::genericGameInfo;
            ODServer::getSingleton().queueServerNotification(notice);
            return false;
        }
        if(!noFee && !map->withdrawFromTreasuries(static_cast<int32_t>(tiles.size()) * getCostPerTile(), player->getSeat())) return false;
        return buildRoomDefault(map, new RoomInfirmary(map), player->getSeat(), tiles);
    }
    //! \brief Previews an editor room.
    void checkBuildRoomEditor(GameMap* map, const InputManager& input, InputCommand& command) const override
    { checkBuildRoomDefaultEditor(map, RoomType::infirmary, input, command); }
    //! \brief Imports editor tiles without a purchase.
    bool buildRoomEditor(GameMap* map, ODPacket& packet) const override
    { return buildRoomDefaultEditor(map, new RoomInfirmary(map), packet); }
    //! \brief Creates an empty room after a split.
    Room* createRoom(GameMap* map) const override { return new RoomInfirmary(map); }
    //! \brief Loads a saved room.
    Room* getRoomFromStream(GameMap* map, std::istream& stream) const override
    {
        RoomInfirmary* room = new RoomInfirmary(map);
        Room::importRoomFromStream(*room, stream);
        return room;
    }
};
static RoomRegister registration(new RoomInfirmaryFactory);
}

RoomInfirmary::RoomInfirmary(GameMap* map) : Room(map), mInstrumentTable(nullptr), mNextCotId(0), mLayingOut(false), mLoadedCots(false), mManaShortageNotified(false), mHealingTurn(-1), mHealingTurnFailed(false)
{ setMeshName("Infirmary"); }

bool RoomInfirmary::containsMinimumBlock(GameMap& map, Seat* seat, const std::vector<Tile*>& tiles)
{
    std::set<Tile*> floor(tiles.begin(), tiles.end());
    std::vector<Tile*> pending(tiles);
    while(!pending.empty())
    {
        Tile* tile = pending.back(); pending.pop_back();
        for(Tile* neighbor : tile->getAllNeighbors())
        {
            Room* room = neighbor->getCoveringRoom();
            if(room == nullptr || room->getSeat() != seat || room->getType() != RoomType::infirmary) continue;
            for(uint32_t i = 0; i < room->numCoveredTiles(); ++i)
            {
                Tile* joined = room->getCoveredTile(i);
                if(floor.insert(joined).second) pending.push_back(joined);
            }
        }
    }
    int side = ConfigManager::getSingleton().getRoomConfigInt32("InfirmaryMinRoomSide");
    for(Tile* tile : floor)
    {
        bool full = true;
        for(int x = 0; x < side; ++x)
            for(int y = 0; y < side; ++y)
                if(floor.count(map.getTile(tile->getX()+x, tile->getY()+y)) == 0) full = false;
        if(full) return true;
    }
    return false;
}

BuildingObject* RoomInfirmary::notifyActiveSpotCreated(ActiveSpotPlace place, Tile* tile)
{
    if(place == activeSpotCenter) return nullptr;
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
        if(mPatients.count(entry.first) && std::find(entry.second.tiles.begin(),entry.second.tiles.end(),tile)!=entry.second.tiles.end())
            return nullptr;
    const std::string meshes[] = {"MedicineCabinet", "InstrumentTable", "WashBasin", "HerbShelf"};
    size_t index = mAccessoryTiles.size();
    mAccessoryTiles.push_back(tile);
    if(index % 4 == 1 && mInstrumentTable == nullptr) mInstrumentTable = tile;
    double rotation = place == activeSpotLeft ? 90.0 : place == activeSpotRight ? 270.0 : place == activeSpotBottom ? 180.0 : 0.0;
    return new BuildingObject(getGameMap(), *this, meshes[index % 4], *tile, rotation, false);
}

void RoomInfirmary::notifyActiveSpotRemoved(ActiveSpotPlace place, Tile* tile)
{
    if(place == activeSpotCenter) return;
    mAccessoryTiles.erase(std::remove(mAccessoryTiles.begin(), mAccessoryTiles.end(), tile), mAccessoryTiles.end());
    if(mInstrumentTable == tile) mInstrumentTable = nullptr;
    Room::notifyActiveSpotRemoved(place, tile);
}

void RoomInfirmary::updateActiveSpots(GameMap* map)
{
    if(!getIsOnServerMap()) { Room::updateActiveSpots(map); return; }
    if(mLayingOut) return;
    mLayingOut = true;
    std::vector<size_t> emptyCots;
    if(!mLoadedCots)
        for(const std::pair<const size_t,CotInfo>& entry : mCots)
            if(mPatients.count(entry.first)==0) emptyCots.push_back(entry.first);
    for(size_t id : emptyCots)
    {
        if(mCotObjects.count(id)) { removeBuildingObject(mCotObjects[id]);mCotObjects.erase(id); }
        mCots.erase(id);
    }
    for(Tile* tile : mAccessoryTiles) removeBuildingObject(tile);
    mAccessoryTiles.clear();mInstrumentTable=nullptr;
    mLeftWallsActiveSpotTiles.clear();mRightWallsActiveSpotTiles.clear();mTopWallsActiveSpotTiles.clear();mBottomWallsActiveSpotTiles.clear();
    std::sort(mCoveredTiles.begin(), mCoveredTiles.end(), tileOrder);
    Room::updateActiveSpots(map);
    layoutCots();
    mLayingOut = false;
    updateShaman();
}

void RoomInfirmary::createCotObject(size_t id)
{
    CotInfo& cot = mCots[id];
    const std::string meshes[] = {"InfirmaryCotSmall", "InfirmaryCotMedium", "InfirmaryCotLarge"};
    Tile* tile = getGameMap()->getTile(cot.x,cot.y);
    BuildingObject* object = new BuildingObject(getGameMap(), *this, meshes[cot.size-1], tile,
        static_cast<Ogre::Real>(cot.x + (cot.width-1)*0.5), static_cast<Ogre::Real>(cot.y + (cot.height-1)*0.5), 0.0, cot.rotation, false);
    addBuildingObject(tile, object);
    object->createMesh();
    mCotObjects[id] = object;
}

void RoomInfirmary::layoutCots()
{
    typedef std::pair<int,int> Cell;
    std::set<Cell> floor, accessories, occupied, entrances;
    for(Tile* tile : mCoveredTiles) floor.insert(Cell(tile->getX(),tile->getY()));
    for(Tile* tile : mAccessoryTiles) accessories.insert(Cell(tile->getX(),tile->getY()));
    const int dx[] = {1,-1,0,0}, dy[] = {0,0,1,-1};
    for(Tile* tile : mCoveredTiles)
        for(int direction=0; direction<4; ++direction)
        {
            Tile* outside = getGameMap()->getTile(tile->getX()+dx[direction],tile->getY()+dy[direction]);
            if(outside != nullptr && !outside->isFullTile() && floor.count(Cell(outside->getX(),outside->getY())) == 0)
                entrances.insert(Cell(tile->getX(),tile->getY()));
        }
    std::vector<size_t> remove;
    int placed[] = {0,0,0};
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
    {
        if(mPatients.count(entry.first) == 0 && !mLoadedCots) { remove.push_back(entry.first); continue; }
        const CotInfo& cot = entry.second;
        for(int x=0;x<cot.width;++x) for(int y=0;y<cot.height;++y) occupied.insert(Cell(cot.x+x,cot.y+y));
        ++placed[cot.size-1];
    }
    for(size_t id : remove)
    {
        if(mCotObjects.count(id)) { removeBuildingObject(mCotObjects[id]); mCotObjects.erase(id); }
        mCots.erase(id);
    }
    if(mLoadedCots) { mLoadedCots=false; return; }
    if(entrances.empty()) return;
    std::map<Cell,int> distance;
    std::queue<Cell> queue;
    for(const Cell& cell : entrances) { distance[cell]=0; queue.push(cell); }
    while(!queue.empty())
    {
        Cell cell=queue.front(); queue.pop();
        for(int i=0;i<4;++i)
        {
            Cell next(cell.first+dx[i],cell.second+dy[i]);
            if(floor.count(next) && !distance.count(next)) { distance[next]=distance[cell]+1; queue.push(next); }
        }
    }
    int shares[] = {ConfigManager::getSingleton().getRoomConfigInt32("InfirmaryCotShareSmall"),ConfigManager::getSingleton().getRoomConfigInt32("InfirmaryCotShareMedium"),ConfigManager::getSingleton().getRoomConfigInt32("InfirmaryCotShareLarge")};
    bool closed[] = {false,false,false};
    while(!(closed[0] && closed[1] && closed[2]))
    {
        int kind=-1;
        for(int i=2;i>=0;--i)
            if(!closed[i] && (kind<0 || (placed[i]+1)*shares[kind] < (placed[kind]+1)*shares[i])) kind=i;
        typedef std::tuple<int,int,int,int,int> Candidate;
        std::vector<Candidate> candidates;
        for(const Cell& anchor : floor)
        {
            int variants=kind==1 ? 2 : 1;
            for(int orientation=0;orientation<variants;++orientation)
            {
                int width=kind==2 || orientation==1 ? 2 : 1;
                int height=kind==2 || (kind==1 && orientation==0) ? 2 : 1;
                bool valid=true; int nearest=std::numeric_limits<int>::max();
                for(int x=0;x<width;++x) for(int y=0;y<height;++y)
                {
                    Cell cell(anchor.first+x,anchor.second+y);
                    if(!floor.count(cell) || !distance.count(cell)) valid=false;
                    else nearest=std::min(nearest,distance[cell]);
                }
                if(valid) candidates.push_back(Candidate(-nearest,anchor.second,anchor.first,width,height));
            }
        }
        std::sort(candidates.begin(),candidates.end());
        bool found=false;
        for(const Candidate& candidate : candidates)
        {
            int x=std::get<2>(candidate), y=std::get<1>(candidate), width=std::get<3>(candidate),height=std::get<4>(candidate);
            std::set<Cell> cells,free=floor;
            bool valid=true;
            for(int a=0;a<width;++a) for(int b=0;b<height;++b)
            {
                Cell cell(x+a,y+b); cells.insert(cell);
                if(occupied.count(cell) || accessories.count(cell)) valid=false;
            }
            if(!valid) continue;
            for(const Cell& cell : occupied) free.erase(cell);
            for(const Cell& cell : cells) free.erase(cell);
            std::set<Cell> seen; std::queue<Cell> visit;
            for(const Cell& entry : entrances) if(free.count(entry)) { seen.insert(entry); visit.push(entry); }
            if(visit.empty()) continue;
            while(!visit.empty())
            {
                Cell cell=visit.front();visit.pop();
                for(int i=0;i<4;++i) { Cell next(cell.first+dx[i],cell.second+dy[i]); if(free.count(next) && seen.insert(next).second) visit.push(next); }
            }
            if(seen != free) continue;
            std::vector<std::set<Cell>> footprints(1,cells);
            for(const std::pair<const size_t,CotInfo>& entry : mCots)
            {
                std::set<Cell> footprint;
                for(Tile* tile : entry.second.tiles) footprint.insert(Cell(tile->getX(),tile->getY()));
                footprints.push_back(footprint);
            }
            for(const std::set<Cell>& footprint : footprints)
            {
                bool touches=false;
                for(const Cell& cell : footprint) for(int i=0;i<4;++i) if(free.count(Cell(cell.first+dx[i],cell.second+dy[i]))) touches=true;
                if(!touches) valid=false;
            }
            if(!valid) continue;
            CotInfo cot; cot.size=kind+1;cot.x=x;cot.y=y;cot.width=width;cot.height=height;cot.rotation=width>height ? 90.0 : 0.0;
            for(const Cell& cell : cells) cot.tiles.push_back(getGameMap()->getTile(cell.first,cell.second));
            size_t id=mNextCotId++;mCots[id]=cot;createCotObject(id);occupied.insert(cells.begin(),cells.end());++placed[kind];found=true;break;
        }
        if(!found) closed[kind]=true;
    }
}

int RoomInfirmary::cotSize(const Creature& creature)
{
    int area=creature.getDefinition()->getBedDim1()*creature.getDefinition()->getBedDim2();
    return area==4 ? 3 : area==2 ? 2 : 1;
}

size_t RoomInfirmary::findCot(const Creature& creature, bool manual) const
{
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
    {
        if(entry.second.size != cotSize(creature)) continue;
        std::map<size_t,PatientInfo>::const_iterator patient=mPatients.find(entry.first);
        if(patient==mPatients.end() || (manual && patient->second.creature==nullptr)) return entry.first;
        if(patient->second.creature==nullptr && patient->second.creatureName==creature.getName()) return entry.first;
    }
    return noCot;
}

bool RoomInfirmary::wouldAccept(const Creature& creature)
{
    for(Room* room : creature.getGameMap()->getRooms())
        if(room->getType()==RoomType::infirmary && static_cast<RoomInfirmary*>(room)->hasCarryEntitySpot(const_cast<Creature*>(&creature))) return true;
    return false;
}

bool RoomInfirmary::hasCarryEntitySpot(GameEntity* entity)
{
    if(entity==nullptr || entity->getObjectType()!=GameEntityType::creature || entity->getSeat()!=getSeat()) return false;
    Creature& creature=*static_cast<Creature*>(entity);
    return creature.isAlive() && creature.getKoTurnCounter()<0 && !creature.getDefinition()->isWorker() && !creature.getDefinition()->isChampion() &&
        !creature.isInPrison() && !getSeat()->isRogueSeat() && getSeat()->getFaction()!="Hero" && findCot(creature,false)!=noCot && canPayAdmission(creature,false);
}

Tile* RoomInfirmary::askSpotForCarriedEntity(GameEntity* entity)
{
    if(entity==nullptr || entity->getObjectType()!=GameEntityType::creature) return nullptr;
    Creature& creature=*static_cast<Creature*>(entity);
    for(const std::pair<const size_t,PatientInfo>& entry : mPatients)
        if(entry.second.creature==nullptr && entry.second.creatureName==creature.getName())
            return getGameMap()->getTile(mCots[entry.first].x,mCots[entry.first].y);
    return nullptr;
}

//! \brief Reuses a running carry's reservation before testing a new admission's payment.
Tile* RoomInfirmary::reserveCot(Creature& creature, Creature& carrier)
{
    // Saved room reservations resume before the server refills the saved treasury balance.
    for(const std::pair<const size_t,PatientInfo>& entry : mPatients)
        if(entry.second.creature==nullptr && entry.second.reservedBy==&carrier &&
            entry.second.creatureName==creature.getName() && creature.getKoTurnCounter()<0 &&
            creature.isAlive() && mCots.count(entry.first)!=0)
        {
            const CotInfo& cot=mCots.at(entry.first);
            return getGameMap()->getTile(cot.x,cot.y);
        }
    if(!hasCarryEntitySpot(&creature)) return nullptr;
    size_t id=findCot(creature,false);
    PatientInfo& patient=mPatients[id];
    patient.creatureName=creature.getName();patient.reservedBy=&carrier;patient.reservedByName=carrier.getName();
    return getGameMap()->getTile(mCots[id].x,mCots[id].y);
}

void RoomInfirmary::cancelReservation(Creature& carrier)
{
    for(std::map<size_t,PatientInfo>::iterator it=mPatients.begin();it!=mPatients.end();)
    {
        if(it->second.creature==nullptr && it->second.reservedBy==&carrier) it=mPatients.erase(it);
        else ++it;
    }
}

//! \brief Charges once, places an eligible patient on its cot and plays admission audio.
bool RoomInfirmary::admit(size_t id, Creature& creature, bool manual)
{
    double paid=0.0; int payer=0;
    if(!payAdmission(creature,manual,paid,payer)) return false;
    PatientInfo patient;
    patient.creature=&creature;patient.creatureName=creature.getName();patient.admissionPaid=paid;patient.payer=payer;patient.manual=manual;
    patient.storedCounter=manual ? ConfigManager::getSingleton().getNbTurnsKoCreatureAttacked() : -creature.getKoTurnCounter();
    if(patient.storedCounter<=0) patient.storedCounter=ConfigManager::getSingleton().getNbTurnsKoCreatureAttacked();
    mPatients[id]=patient;
    creature.resetKoTurns();
    creature.clearActionQueue();
    const CotInfo& cot=mCots[id];
    creature.setPosition(Ogre::Vector3(static_cast<Ogre::Real>(cot.x+(cot.width-1)*0.5),static_cast<Ogre::Real>(cot.y+(cot.height-1)*0.5),0.0));
    creature.clearDestinations(EntityAnimation::sleep_anim,false,false);
    creature.pushAction(Utils::make_unique<CreatureActionInfirmaryRest>(creature,*this));
    if(creature.getPositionTile()!=nullptr) creature.getPositionTile()->addDirt(
        ConfigManager::getSingleton().getRoomConfigDouble("InfirmaryDirtPerTreatment"));
    if(creature.getPositionTile()!=nullptr) fireRoomSound(*creature.getPositionTile(), "Infirmary/Admit");
    return true;
}

void RoomInfirmary::notifyCarryingStateChanged(Creature* carrier, GameEntity* entity)
{
    if(carrier==nullptr) return;
    size_t id=noCot;
    for(const std::pair<const size_t,PatientInfo>& entry : mPatients)
        if(entry.second.reservedBy==carrier) { id=entry.first;break; }
    bool arrival=id!=noCot && carrier->getPositionTile()==getGameMap()->getTile(mCots[id].x,mCots[id].y);
    if(arrival && entity!=nullptr && entity->getObjectType()==GameEntityType::creature &&
        mPatients[id].creatureName==entity->getName() && static_cast<Creature*>(entity)->isAlive() &&
        static_cast<Creature*>(entity)->getKoTurnCounter()<0 && admit(id,*static_cast<Creature*>(entity),false)) return;
    cancelReservation(*carrier);
}

void RoomInfirmary::creatureDropped(Creature& creature)
{
    bool eligible=creature.getSeat()==getSeat() && !getSeat()->isRogueSeat() && getSeat()->getFaction()!="Hero" && creature.isAlive() && !creature.getDefinition()->isWorker() &&
        !creature.getDefinition()->isChampion() && !creature.isInPrison() && creature.getHP()*100.0<creature.getMaxHp()*getDischargeThreshold();
    size_t id=eligible ? findCot(creature,true) : noCot;
    if(id!=noCot && admit(id,creature,true)) return;
    if(creature.getSeat()==getSeat() && creature.getHomeTile()!=nullptr) creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
}

RoomInfirmary::PatientInfo* RoomInfirmary::getPatient(Creature& creature)
{
    for(std::pair<const size_t,PatientInfo>& entry : mPatients) if(entry.second.creature==&creature) return &entry.second;
    return nullptr;
}

void RoomInfirmary::releasePatient(Creature& creature)
{
    for(std::map<size_t,PatientInfo>::iterator it=mPatients.begin();it!=mPatients.end();++it)
        if(it->second.creature==&creature) { mPatients.erase(it);return; }
}

//! \brief Keeps switched-off patients lying and otherwise discharges at the chosen health.
bool RoomInfirmary::restPatient(Creature& creature)
{
    if(getPatient(creature)==nullptr) return false;
    healPatient(creature);
    if(!getSeat()->getInfirmaryHealOn()) return true;
    if(creature.getHP()*100.0<creature.getMaxHp()*getDischargeThreshold()) return true;
    if(creature.getPositionTile()!=nullptr) fireRoomSound(*creature.getPositionTile(), "Infirmary/Discharge");
    releasePatient(creature);
    creature.popAction();
    if(creature.getHP()<creature.getMaxHp() && creature.getHomeTile()!=nullptr) creature.pushAction(Utils::make_unique<CreatureActionSleep>(creature));
    return false;
}

//! \brief Restores the exact stored knockout countdown when a cot treatment is lost.
void RoomInfirmary::abandon(size_t id)
{
    std::map<size_t,PatientInfo>::iterator it=mPatients.find(id);
    if(it==mPatients.end()) return;
    Creature* creature=it->second.creature;
    double counter=it->second.storedCounter;
    mPatients.erase(it);
    if(creature==nullptr) return;
    creature->clearActionQueue();
    creature->setKoTurnCounter(-counter);
    creature->clearDestinations(EntityAnimation::die_anim,false,false);
}

void RoomInfirmary::abandonAll()
{
    while(!mPatients.empty()) abandon(mPatients.begin()->first);
}

void RoomInfirmary::changeOwner(Seat* seat)
{
    abandonAll();Room::changeOwner(seat);
    updateShaman();
}

void RoomInfirmary::removeFromGameMap(GameMap* map)
{
    abandonAll();removeShaman();Room::removeFromGameMap(map);
}

bool RoomInfirmary::removeCoveredTile(Tile* tile)
{
    std::vector<size_t> removed;
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
        if(std::find(entry.second.tiles.begin(),entry.second.tiles.end(),tile)!=entry.second.tiles.end()) removed.push_back(entry.first);
    for(size_t id : removed)
    {
        abandon(id);
        if(mCotObjects.count(id)) { removeBuildingObject(mCotObjects[id]);mCotObjects.erase(id); }
        mCots.erase(id);
    }
    bool result=Room::removeCoveredTile(tile);
    return result;
}

void RoomInfirmary::absorbRoom(Room* room)
{
    RoomInfirmary* other=static_cast<RoomInfirmary*>(room);
    for(const std::pair<const size_t,CotInfo>& entry : other->mCots)
    {
        size_t id=mNextCotId++;mCots[id]=entry.second;
        if(other->mCotObjects.count(entry.first)) mCotObjects[id]=other->mCotObjects[entry.first];
        if(other->mPatients.count(entry.first))
        {
            PatientInfo patient=other->mPatients[entry.first];
            mPatients[id]=patient;
            if(patient.creature!=nullptr)
            {
                patient.creature->clearActionQueue();
                patient.creature->pushAction(Utils::make_unique<CreatureActionInfirmaryRest>(*patient.creature,*this));
            }
            if(patient.reservedBy!=nullptr)
                for(const std::unique_ptr<CreatureAction>& action : patient.reservedBy->getActions())
                    if(action->getType()==CreatureActionType::carryEntity)
                        static_cast<CreatureActionCarryEntity*>(action.get())->replaceDestination(*other,*this);
        }
    }
    mAccessoryTiles.insert(mAccessoryTiles.end(),other->mAccessoryTiles.begin(),other->mAccessoryTiles.end());
    other->mAccessoryTiles.clear();
    other->mPatients.clear();other->mCots.clear();other->mCotObjects.clear();
    if(mShaman == nullptr)
    {
        mShaman = other->mShaman;
        other->mShaman = nullptr;
    }
    else
        other->removeShaman();
    Room::absorbRoom(room);
    updateActiveSpots();
}

//! \brief Transfers intact cots and removes split furniture from its current infirmary.
void RoomInfirmary::splitRoom(Room& room, const std::vector<Tile*>& tiles)
{
    RoomInfirmary& target=static_cast<RoomInfirmary&>(room);
    std::vector<size_t> transferred;
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
    {
        bool all=true,any=false;
        for(Tile* tile : entry.second.tiles)
        {
            bool moved=std::find(tiles.begin(),tiles.end(),tile)!=tiles.end();
            all=all && moved;any=any || moved;
        }
        if(!any) continue;
        if(!all || target.getSeat()!=getSeat()) abandon(entry.first);
        if(!all && mCotObjects.count(entry.first))
        {
            BuildingObject* object=mCotObjects[entry.first];
            Tile* anchor=getGameMap()->getTile(entry.second.x,entry.second.y);
            RoomInfirmary* owner=static_cast<RoomInfirmary*>(anchor->getCoveringBuilding());
            owner->removeBuildingObject(object);
        }
        if(all)
        {
            size_t id=target.mNextCotId++;
            target.mCots[id]=entry.second;
            if(mCotObjects.count(entry.first)) target.mCotObjects[id]=mCotObjects[entry.first];
            if(mPatients.count(entry.first))
            {
                PatientInfo patient=mPatients[entry.first];
                target.mPatients[id]=patient;
                if(patient.creature!=nullptr)
                {
                    patient.creature->clearActionQueue();
                    patient.creature->pushAction(Utils::make_unique<CreatureActionInfirmaryRest>(*patient.creature,target));
                }
                if(patient.reservedBy!=nullptr)
                    for(const std::unique_ptr<CreatureAction>& action : patient.reservedBy->getActions())
                        if(action->getType()==CreatureActionType::carryEntity)
                            static_cast<CreatureActionCarryEntity*>(action.get())->replaceDestination(*this,target);
            }
        }
        transferred.push_back(entry.first);
    }
    for(size_t id : transferred) { mPatients.erase(id);mCots.erase(id);mCotObjects.erase(id); }
    for(std::vector<Tile*>::iterator it=mAccessoryTiles.begin();it!=mAccessoryTiles.end();)
    {
        if(std::find(tiles.begin(),tiles.end(),*it)==tiles.end()) { ++it;continue; }
        target.mAccessoryTiles.push_back(*it);
        if(mInstrumentTable==*it) mInstrumentTable=nullptr;
        it=mAccessoryTiles.erase(it);
    }
    if(mShaman != nullptr && std::find(tiles.begin(), tiles.end(), mShaman->getPositionTile()) != tiles.end())
    {
        if(target.mShaman == nullptr)
        {
            target.mShaman = mShaman;
            mShaman = nullptr;
        }
        else
            removeShaman();
        target.updateShaman();
    }

}

void RoomInfirmary::doUpkeep()
{
    Room::doUpkeep();
    updateShaman();
    if(getSeat()->getPlayer()!=nullptr && getSeat()->getPlayer()->getHasLost()) { abandonAll();return; }
    for(std::map<size_t,PatientInfo>::iterator it=mPatients.begin();it!=mPatients.end();)
    {
        PatientInfo& patient=it->second;
        if(patient.creature!=nullptr && (!patient.creature->isAlive() || !patient.creature->getIsOnMap() ||
            !patient.creature->isActionInList(CreatureActionType::infirmaryRest))) it=mPatients.erase(it);
        else if(patient.creature==nullptr && patient.reservedBy!=nullptr && !patient.reservedBy->isActionInList(CreatureActionType::carryEntity)) it=mPatients.erase(it);
        else ++it;
    }
}

std::vector<Tile*> RoomInfirmary::getCotTiles() const
{
    std::vector<Tile*> result;
    for(const std::pair<const size_t,CotInfo>& entry : mCots) result.insert(result.end(),entry.second.tiles.begin(),entry.second.tiles.end());
    return result;
}

std::vector<Tile*> RoomInfirmary::getPatientPositions() const
{
    std::vector<Tile*> result;
    for(const std::pair<const size_t,PatientInfo>& entry : mPatients)
        if(entry.second.creature!=nullptr) result.push_back(entry.second.creature->getPositionTile());
    return result;
}

Tile* RoomInfirmary::getShamanSpawnTile() const
{
    if(mInstrumentTable!=nullptr) return mInstrumentTable;
    std::vector<Tile*> cots=getCotTiles();Tile* best=nullptr;
    for(Tile* tile : mCoveredTiles)
        if(std::find(cots.begin(),cots.end(),tile)==cots.end() && (best==nullptr || std::make_pair(tile->getY(),tile->getX())<std::make_pair(best->getY(),best->getX()))) best=tile;
    return best;
}

//! \brief Restores paid patients and reestablishes incoming countdowns before reserving their carries.
void RoomInfirmary::restoreInitialEntityState()
{
    Room::restoreInitialEntityState();
    for(const std::pair<const size_t,CotInfo>& entry : mCots)
        if(mCotObjects.count(entry.first)==0) createCotObject(entry.first);
    std::map<size_t,PatientInfo> saved=mPatients;
    mPatients.clear();
    // Destructors may release a previous rest or carry; no iterator into live admissions survives that cleanup.
    for(const std::pair<const size_t,PatientInfo>& entry : saved)
    {
        const PatientInfo& patient=entry.second;
        Creature* creature=getGameMap()->getCreature(patient.creatureName);
        if(creature!=nullptr) creature->clearActionQueue();
        if(!patient.reservedByName.empty() && patient.reservedByName!="none")
        {
            Creature* carrier=getGameMap()->getCreature(patient.reservedByName);
            if(carrier!=nullptr) carrier->clearActionQueue();
        }
    }
    mPatients=saved;
    for(const std::pair<const size_t,PatientInfo>& entry : saved)
    {
        PatientInfo patient=entry.second;
        if(patient.reservedByName!="none" && !patient.reservedByName.empty())
        {
            patient.reservedBy=getGameMap()->getCreature(patient.reservedByName);
            Creature* carried=getGameMap()->getCreature(patient.creatureName);
            mPatients[entry.first]=patient;
            if(patient.reservedBy!=nullptr && carried!=nullptr)
            {
                carried->setKoTurnCounter(patient.storedCounter);
                patient.reservedBy->pushAction(Utils::make_unique<CreatureActionCarryEntity>(*patient.reservedBy,*carried,*this));
            }
        }
        else if(!patient.creatureName.empty() && patient.creatureName!="none")
        {
            patient.creature=getGameMap()->getCreature(patient.creatureName);
            mPatients[entry.first]=patient;
            if(patient.creature!=nullptr)
                patient.creature->pushAction(Utils::make_unique<CreatureActionInfirmaryRest>(*patient.creature,*this));
        }
    }
    updateShaman();
}
