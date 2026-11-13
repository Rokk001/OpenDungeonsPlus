"""Compile production shelf delivery, book opening and floor carry rules with controlled services."""
from pathlib import Path
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[2]


def read(path):
    """Read production text without depending on the caller's working directory."""
    return (REPO / path).read_text(encoding="utf-8")


def function(text, signature):
    """Extract an unchanged brace-delimited production function."""
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


PRELUDE = r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#define OD_LOG_ERR(message) ((void)0)
#define OD_LOG_INF(message) ((void)0)
#define OD_ASSERT_TRUE(result) check(bool(result), "carry invariant")
//! \brief Fails the probe with the independently specified expectation.
void check(bool result, const char* message)
{ if(!result) throw std::runtime_error(message); }
namespace Ogre
{
typedef float Real;
//! \brief Supplies the coordinates used by production delivery calls.
struct Vector2
{
    float x, y;
    Vector2(float a=0, float b=0):x(a),y(b) {}
    static const Vector2 ZERO;
};
const Vector2 Vector2::ZERO;
//! \brief Supplies the coordinates of a placed book.
struct Vector3
{
    float x, y, z;
    Vector3(float a=0, float b=0, float c=0):x(a),y(b),z(c) {}
};
}
namespace EntityAnimation { const int walk_anim=1, idle_anim=2, die_anim=3; }
enum class GameEntityType { itemBagEntity, missileObject, room, other };
enum class RoomType { library, treasury, ghostRoom, merchant, alchemyLab, crypt, dormitory,
    dungeonTemple, infirmary, prison, workshop };
enum class GhostItem { none, researchBook, ectoplasm, manaCrystal };
enum class EntityCarryType { notCarryable, itemBag };
enum class MissileObjectType { stone, other };
struct Room;
struct Seat {};
//! \brief Holds one tile's room and book occupancy.
struct Tile
{
    Room* room=nullptr;
    int x=0, y=0;
    std::vector<class GameEntity*> entities;
    std::vector<Seat*> visibleSeats;
    //! \brief Returns the viewers of this tile, independent of the worker's tile.
    const std::vector<Seat*>& getSeatsWithVision() { return visibleSeats; }
    Room* getCoveringRoom() { return room; }
    Ogre::Vector2 getPosition2d() { return Ogre::Vector2(float(x),float(y)); }
    std::vector<class GameEntity*> getEntitiesInTile() { return entities; }
};
//! \brief Supplies live placement and removal services for the extracted rules.
struct GameEntity
{
    GameEntityType type=GameEntityType::other;
    Tile* tile=nullptr;
    Seat* seat=nullptr;
    bool onMap=true, locked=false, removed=false, deleted=false;
    Ogre::Vector3 position;
    int visibilityRemovals=0, visibilityAdds=0;
    Ogre::Vector3 clientPosition;
    Seat* clientSeat=nullptr;
    std::vector<Seat*> clientViewers;
    //! \brief Records removal of the old client placement.
    void fireRemoveEntityToSeatsWithVision() { ++visibilityRemovals; }
    //! \brief Records the full snapshot and its destination viewers.
    void notifySeatsWithVision(const std::vector<Seat*>& seats)
    { ++visibilityAdds; clientPosition=position; clientSeat=seat; clientViewers=seats; }
    GameEntityType getObjectType() { return type; }
    bool getIsOnMap() { return onMap; }
    bool isCarryLocked() { return locked; }
    bool getCarryLock(class Creature&) { return locked; }
    Tile* getPositionTile() { return tile; }
    void setSeat(Seat* value) { seat=value; }
    void setPosition(const Ogre::Vector3& value);
    //! \brief Removes occupancy and marks picked-up cargo off-map like the production base entity.
    void removeEntityFromPositionTile()
    {
        if(!onMap) return;
        onMap=false;
        tile->entities.erase(std::remove(tile->entities.begin(),tile->entities.end(),this),tile->entities.end());
    }
    //! \brief Restores map membership only when cargo is released onto the ground.
    void addEntityToPositionTile()
    {
        if(onMap) return;
        onMap=true;
        tile->entities.push_back(this);
    }
    void removeFromGameMap() { onMap=false; removed=true; }
    void deleteYourself() { deleted=true; }
    //! \brief Supplies listener and release operations used by the production carry destructor.
    void removeGameEntityListener(void*) {}
    void setCarryLock(class Creature&,bool value) { locked=value; }
    virtual void notifyEntityCarryOff(const Ogre::Vector3& value) { setPosition(value); }
};
//! \brief Represents shelf furniture position and wall rotation independently of the book.
struct BuildingObject
{
    std::string mesh;
    Ogre::Vector3 position;
    Ogre::Real rotation=0;
    Ogre::Real getRotationAngle() { return rotation; }
    const std::string& getMeshName() { return mesh; }
    Ogre::Vector3 getPosition() { return position; }
};
//! \brief Exposes a fixed research reward and idle delay.
struct ConfigManager
{
    static ConfigManager& getSingleton() { static ConfigManager instance; return instance; }
    double getRoomConfigDouble(const std::string& key)
    { check(key=="GhostEctoplasmResearchPoints","reward key"); return 100.0; }
    double getItemSetting(const std::string&,const std::string&) { return 20.0; }
};
//! \brief Supplies base placement, pickup and serialization without replacing the bag's delivery-state format.
struct RenderedMovableEntity : GameEntity
{
    void pickup() { removeEntityFromPositionTile(); }
    //! \brief Restores map occupancy after a keeper's drop.
    void drop(const Ogre::Vector3& value) { setPosition(value); addEntityToPositionTile(); }
    void exportToStream(std::ostream& stream) const
    { stream << position.x << ' ' << position.y << ' ' << position.z << ' '; }
    bool importFromStream(std::istream& stream)
    { return bool(stream >> position.x >> position.y >> position.z); }
};
//! \brief Supplies the room's shelf lookup and destination checks.
struct Room : GameEntity
{
    Room() { GameEntity::type=GameEntityType::room; }
    RoomType type=RoomType::library;
    Seat* seat=nullptr;
    Tile* shelfTile=nullptr;
    BuildingObject* object=nullptr;
    int released=0;
    Creature* lastCarrier=nullptr;
    GameEntity* lastCargo=nullptr;
    int callbacks=0;
    virtual bool hasCarryEntitySpot(GameEntity*) { return false; }
    //! \brief Records the destructor's callback contract for destinations outside the library.
    virtual void notifyCarryingStateChanged(class Creature* carrier,GameEntity* cargo)
    { lastCarrier=carrier; lastCargo=cargo; ++callbacks; }
    RoomType getType() { return type; }
    Seat* getSeat() { return seat; }
protected:
    //! \brief Keeps furniture lookup protected as in the real Building API.
    BuildingObject* getBuildingObjectFromTile(Tile* tile) { return tile==shelfTile ? object : nullptr; }
public:
    void releaseInteractionPosition(class Creature*) { ++released; }
};
std::vector<Tile*> world;
//! \brief Updates occupancy using nearest tile coordinates when a book moves onto an offset shelf.
void GameEntity::setPosition(const Ogre::Vector3& value)
{
    const bool wasOnMap=onMap;
    if(wasOnMap) removeEntityFromPositionTile();
    position=value;
    for(Tile* candidate : world)
        if(candidate->x==int(std::round(value.x)) && candidate->y==int(std::round(value.y))) tile=candidate;
    if(wasOnMap) addEntityToPositionTile();
}
//! \brief Holds a worker's route, attached cargo and action effects for the production carry methods.
struct Creature : GameEntity
{
    Seat* seat=nullptr;
    Tile* tile=nullptr;
    bool routeAllowed=true, atShelf=false;
    int popped=0, walked=0, pushed=0, destinations=0;
    GameEntity* mCarriedEntity=nullptr;
    std::vector<Seat*> mSeatsWithVisionNotified;
    //! \brief Enables authoritative attachment in the extracted production carry method.
    bool getIsOnServerMap() { return true; }
    //! \brief Executes the production worker attachment and visibility lifecycle.
    void carryEntity(GameEntity*);
    Seat* getSeat() { return seat; }
    Tile* getPositionTile() { return tile; }
    std::string getName() { return "worker"; }
    Ogre::Vector3 getPosition() { return Ogre::Vector3(); }
    void popAction() { ++popped; }
    bool setDestination(Tile*) { ++destinations; return true; }
    void setWalkPath(int,int,bool,bool,const std::vector<Ogre::Vector2>&,bool,bool) { ++walked; }
    void pushAction(std::unique_ptr<class CreatureActionWalkToTile>) { ++pushed; }
    //! \brief Supplies drag-only cleanup while recording ordinary cargo detachment.
    int cargoReleases=0;
    //! \brief Detaches the worker's cargo when the production action releases it.
    void releaseCarriedEntity() { ++cargoReleases; mCarriedEntity=nullptr; }
    void clearDestinations(int,bool,bool) {}
    void notifyCorpseDragEnd() {}
    void notifyDragEnd() {}
};
//! \brief Supplies a typed walking action for the unchanged production call.
struct CreatureActionWalkToTile { CreatureActionWalkToTile(Creature&) {} };
namespace Utils
{
//! \brief Constructs the production walking action.
template<class T> std::unique_ptr<T> make_unique(Creature& creature)
{ return std::unique_ptr<T>(new T(creature)); }
}
namespace RoomObjectNavigation
{
//! \brief Controls route availability and arrival without replacing the delivery decision.
bool workApproach(Creature& worker,const BuildingObject&,const Ogre::Vector2&,
    const Ogre::Vector2&,std::vector<Ogre::Vector2>& path)
{
    path.clear();
    if(!worker.routeAllowed) return false;
    if(!worker.atShelf) path.push_back(Ogre::Vector2(2,0));
    return true;
}
}
//! \brief Supplies irrelevant merchant and missile branches of the production carry handler.
enum class MerchantApproach { failed, walking, ready };
struct RoomMerchant : Room
{ MerchantApproach approachTable(Creature&,Tile*) { return MerchantApproach::failed; } };
struct MissileObject : GameEntity
{ MissileObjectType getMissileType() { return MissileObjectType::other; } };
struct MissileStone : MissileObject { void completeDelivery(Creature&) {} };
struct RoomGhostRoom : Room { bool isWaitingEctoplasm(GameEntity&) { return false; } };
//! \brief Supplies the item instance fields consulted by production bag rules.
struct ItemInstance
{
    GhostItem mGhostItem=GhostItem::researchBook;
    bool mMerchantGoods=false, mSoulCrystal=false;
    //! \brief Keeps the item payload independent of the bag's optional shelf marker.
    void exportToStream(std::ostream& stream) const { stream << "TestBook " << int(mGhostItem); }
    bool importFromStream(std::istream& stream,const std::string& id)
    { int kind=0; if(id!="TestBook" || !(stream >> kind)) return false; mGhostItem=GhostItem(kind); return true; }
};
enum class Quality { common, rare, epic };
//! \brief Supplies unused random-token services while exercising production bag loading.
struct GameMap
{
    bool isInEditorMode() { return true; }
    std::unique_ptr<ItemInstance> rollItem(Quality) { return std::unique_ptr<ItemInstance>(new ItemInstance); }
    void registerEpic(const ItemInstance&) {}
};
namespace Random { double Double(double,double) { return 1.0; } }
namespace ItemDrops
{
std::unique_ptr<ItemInstance> randomGhostProduct(double)
{ return std::unique_ptr<ItemInstance>(new ItemInstance); }
}
//! \brief Exposes the unchanged bag carry predicate and transfer operation.
struct ItemBagEntity : RenderedMovableEntity
{
    std::unique_ptr<ItemInstance> mItem;
    uint32_t mIdleTurns=0;
    bool mResearchBookShelved=false;
    ItemBagEntity():mItem(new ItemInstance) { type=GameEntityType::itemBagEntity; }
    ItemInstance* getItem() { return mItem.get(); }
    std::unique_ptr<ItemInstance> takeItem() { return std::move(mItem); }
    bool isWantedByUseRoom(Creature&) { return false; }
    EntityCarryType getEntityCarryType(Creature*);
    bool isResearchBookShelved() const;
    void markResearchBookShelved();
    void pickup();
    void drop(const Ogre::Vector3&);
    void notifyEntityCarryOn(Creature*);
    void notifyEntityCarryOff(const Ogre::Vector3&) override;
    void exportToStream(std::ostream&) const;
    bool importFromStream(std::istream&);
    GameMap* getGameMap() { static GameMap map; return &map; }
    static std::string getSpecialMesh(const ItemInstance&) { return "Grimoire"; }
    void setMeshName(const std::string&) {}
};
//! \brief Exposes production library functions and retained research for bounded assertions.
struct RoomLibrary : Room
{
    std::vector<Tile*> mCoveredTiles;
    double mSkillPoints=0;
    Tile* bookshelfTile();
    bool hasCarryEntitySpot(GameEntity*) override;
    Tile* askSpotForCarriedEntity(GameEntity*);
    void notifyCarryingStateChanged(Creature*,GameEntity*) override;
    bool isBookshelfTile(Tile*);
    bool getBookshelfApproach(Creature&,Tile*,std::vector<Ogre::Vector2>&);
    bool openResearchBook();
};
struct CreatureActionCarryEntity
{
    Creature& mCreature;
    GameEntity* mEntityToCarry;
    Room* mBuildingDest;
    bool mIsDrag=false, mExternalDrag=false, mCorpseDrag=false, mDelivered=false;
    //! \brief Supplies transport state while retaining the production handler and destructor.
    CreatureActionCarryEntity(Creature& worker,GameEntity* cargo,Room* destination):
        mCreature(worker),mEntityToCarry(cargo),mBuildingDest(destination) {}
    ~CreatureActionCarryEntity();
    bool handleCarryEntity(Creature&,GameEntity*,Tile*);
};
'''

CASES = r'''
//! \brief Checks pickup, off-map transport, floor recovery, rotated shelf placement and single-use rewards.
int main()
{
    Seat owner, enemy;
    RoomLibrary library;
    library.seat=&owner;
    Tile floor, shelf;
    floor.room=&library; shelf.room=&library; shelf.x=3;
    floor.visibleSeats={&owner}; shelf.visibleSeats={&owner,&enemy};
    world={&floor,&shelf}; library.mCoveredTiles=world;
    BuildingObject furniture;
    furniture.mesh="Bookshelf"; furniture.position=Ogre::Vector3(3,0,0);
    library.shelfTile=&shelf;
    Creature worker; worker.seat=&owner; worker.tile=&floor;
    CreatureActionCarryEntity carry(worker,nullptr,&library);
    ItemBagEntity book; book.tile=&floor; floor.entities.push_back(&book);

    check(!library.hasCarryEntitySpot(&book),"shelfless library refuses delivery");
    check(library.askSpotForCarriedEntity(&book)==nullptr,"no floor fallback");
    check(!library.openResearchBook(),"shelfless floor book survives research");
    check(book.getEntityCarryType(&worker)==EntityCarryType::itemBag,"floor book can leave shelfless library");
    library.object=&furniture;
    check(library.askSpotForCarriedEntity(&book)==&shelf,"actual shelf selected");
    check(!library.openResearchBook(),"library floor book is not opened");
    check(book.getEntityCarryType(&worker)==EntityCarryType::itemBag,"floor book remains carryable with shelves");

    // A shelf tile alone must never stand in for successful delivery, even after interruption.
    book.setPosition(Ogre::Vector3(3,0,0));
    check(!library.openResearchBook(),"floor book on shelf tile cannot grant research");
    check(book.getEntityCarryType(&worker)==EntityCarryType::itemBag,"floor book on shelf tile is recoverable");
    library.notifyCarryingStateChanged(&worker,&book);
    check(!book.isResearchBookShelved() && !library.openResearchBook(),"interrupted carry on shelf tile stays floor cargo");
    book.setPosition(Ogre::Vector3(0,0,0));

    // Interrupt after walking has reached the approach, before the carry handler can complete.
    book.locked=true;
    {
        CreatureActionCarryEntity interrupted(worker,&book,&library);
        interrupted.handleCarryEntity(worker,&book,&shelf);
        check(!interrupted.mDelivered && worker.walked==1,"walking has not completed shelf delivery");
        worker.atShelf=true;
    }
    check(!book.isResearchBookShelved() && book.getItem()!=nullptr && book.tile==&floor &&
        !book.locked && worker.cargoReleases==1,"interrupted approach releases recoverable floor cargo");
    check(!library.openResearchBook() && library.mSkillPoints==0 &&
        book.getEntityCarryType(&worker)==EntityCarryType::itemBag,
        "interrupted approach never grants research and can be carried again");
    check(book.visibilityRemovals==0 && book.visibilityAdds==0 && library.released==2,
        "interrupted approach cancels interaction without a shelf snapshot");
    // A failed approach cannot become successful just because the worker later reaches it.
    worker.routeAllowed=false;
    {
        CreatureActionCarryEntity blocked(worker,&book,&library);
        blocked.handleCarryEntity(worker,&book,&shelf);
        worker.routeAllowed=true;
    }
    check(!book.isResearchBookShelved() && !library.openResearchBook(),
        "failed approach cannot be reclassified as completed during destruction");
    library.object=nullptr;
    {
        CreatureActionCarryEntity missingShelf(worker,&book,&library);
        missingShelf.handleCarryEntity(worker,&book,&shelf);
        library.object=&furniture;
    }
    check(!book.isResearchBookShelved() && !library.openResearchBook(),
        "missing shelf cannot be reclassified as completed during destruction");
    {
        CreatureActionCarryEntity released(worker,nullptr,&library);
    }
    check(!book.isResearchBookShelved() && book.getItem()!=nullptr,
        "already released cargo stays untouched at the approach");
    worker.atShelf=false;
    worker.walked=0; worker.pushed=0; worker.popped=0;
    carry.handleCarryEntity(worker,&book,&shelf);
    check(worker.walked==1 && worker.pushed==1 && worker.popped==0,"shelf delivery queues furniture approach");
    check(worker.destinations==0,"worker does not walk directly into shelf tile");
    library.notifyCarryingStateChanged(&worker,&book);
    check(book.tile==&floor && book.getItem()!=nullptr,"interrupted delivery leaves book on floor");
    worker.routeAllowed=false;
    carry.handleCarryEntity(worker,&book,&shelf);
    library.notifyCarryingStateChanged(&worker,&book);
    check(worker.popped==1 && book.tile==&floor,"blocked shelf preserves book");
    worker.routeAllowed=true; worker.atShelf=true;
    worker.seat=&enemy;
    library.notifyCarryingStateChanged(&worker,&book);
    check(book.tile==&floor,"foreign worker cannot deliver");
    worker.seat=&owner;
    {
        CreatureActionCarryEntity completed(worker,&book,&library);
        completed.handleCarryEntity(worker,&book,&shelf);
        check(completed.mDelivered,"successful carry records completion before action removal");
    }
    check(book.tile==&shelf && floor.entities.empty() && shelf.entities.size()==1,"delivery updates occupancy onto shelf");
    check(book.seat==&owner && book.getItem()!=nullptr && library.mSkillPoints==0,"delivery claims book without reward");
    check(book.visibilityRemovals==1 && book.visibilityAdds==1,"only successful delivery refreshes client placement");
    check(std::abs(book.position.x-3.0f)<0.00001f && std::abs(book.position.y-0.12f)<0.00001f &&
        std::abs(book.position.z-1.51358f)<0.00001f,"server book rests on top shelf rather than floor");
    check(std::abs(book.clientPosition.x-3.0f)<0.00001f && std::abs(book.clientPosition.y-0.12f)<0.00001f &&
        std::abs(book.clientPosition.z-1.51358f)<0.00001f &&
        book.clientSeat==&owner,"client snapshot contains shelf coordinates and owner");
    check(book.clientViewers==shelf.visibleSeats,"snapshot reaches shelf viewers rather than only floor viewers");
    check(book.getEntityCarryType(&worker)==EntityCarryType::notCarryable,"shelved book waits for researcher");

    std::stringstream saved;
    book.exportToStream(saved);
    ItemBagEntity restored;
    check(restored.importFromStream(saved) && restored.isResearchBookShelved(),"confirmed delivery survives save/load");
    check(std::abs(restored.position.z-1.51358f)<0.00001f,"save/load retains shelf elevation");
    // Keeper pickup/drop and worker carry/release must revoke delivery before any later shelf visit.
    book.pickup();
    check(!book.isResearchBookShelved(),"keeper pickup revokes shelf delivery");
    book.drop(Ogre::Vector3(3,0,0));
    check(!library.openResearchBook() && book.getEntityCarryType(&worker)==EntityCarryType::itemBag,
        "keeper floor drop on shelf tile remains recoverable");
    library.notifyCarryingStateChanged(&worker,&book);
    book.notifyEntityCarryOn(&worker);
    check(!book.isResearchBookShelved(),"worker pickup revokes shelf delivery");
    book.notifyEntityCarryOff(Ogre::Vector3(3,0,0));
    check(!library.openResearchBook() && book.getEntityCarryType(&worker)==EntityCarryType::itemBag,
        "worker floor release on shelf tile remains recoverable");
    std::stringstream floorSave;
    book.exportToStream(floorSave);
    check(restored.importFromStream(floorSave) && !restored.isResearchBookShelved(),"floor save clears previous loaded delivery");
    std::stringstream legacy("3 0 0 TestBook 1");
    check(restored.importFromStream(legacy) && !restored.isResearchBookShelved(),"legacy unmarked floor book is recoverable");
    library.notifyCarryingStateChanged(&worker,&book);
    book.locked=true;
    check(!library.openResearchBook(),"reserved book cannot be consumed");
    book.locked=false; book.onMap=false;
    check(!library.openResearchBook(),"off-map book cannot be consumed");
    book.onMap=true;
    ItemBagEntity second; second.tile=&shelf; shelf.entities.push_back(&second);
    check(library.openResearchBook(),"researcher opens delivered book");
    check(book.deleted && book.removed && book.getItem()==nullptr,"opened book removed completely");
    check(library.mSkillPoints==100.0 && second.getItem()!=nullptr,"one book per work cycle");
    check(!library.openResearchBook() && library.mSkillPoints==100.0,"undelivered second book waits for delivery");
    library.notifyCarryingStateChanged(&worker,&second);
    check(library.mSkillPoints==100.0,"second delivery still defers reward");
    check(library.openResearchBook() && library.mSkillPoints==200.0,"next work cycle opens delivered second book");
    check(!library.openResearchBook() && library.mSkillPoints==200.0,"no repeated reward");

    // Every other destination keeps its previous non-null carrier, including trap callbacks.
    const RoomType destinations[]={RoomType::treasury,RoomType::ghostRoom,RoomType::merchant,
        RoomType::alchemyLab,RoomType::crypt,RoomType::dormitory,RoomType::dungeonTemple,
        RoomType::infirmary,RoomType::prison,RoomType::workshop};
    GameEntity callbackCargo; callbackCargo.tile=&floor;
    for(RoomType type : destinations)
    {
        Room destination; destination.type=type;
        {
            CreatureActionCarryEntity interrupted(worker,&callbackCargo,&destination);
        }
        check(destination.callbacks==1 && destination.lastCarrier==&worker && destination.lastCargo==&callbackCargo,
            "ordinary non-library callback preserves carrier and cargo");
    }
    Room trap; trap.GameEntity::type=GameEntityType::other;
    {
        CreatureActionCarryEntity interrupted(worker,&callbackCargo,&trap);
    }
    check(trap.lastCarrier==&worker && trap.lastCargo==&callbackCargo,"trap callback retains required carrier");
    Room external; external.type=RoomType::crypt;
    {
        CreatureActionCarryEntity interrupted(worker,&callbackCargo,&external);
        interrupted.mExternalDrag=true;
    }
    check(external.callbacks==1 && external.lastCarrier==nullptr,"external drag cancellation remains null");
    {
        CreatureActionCarryEntity completed(worker,&callbackCargo,&external);
        completed.mExternalDrag=true; completed.mDelivered=true;
    }
    check(external.callbacks==2 && external.lastCarrier==&worker,"completed external delivery retains carrier");
    callbackCargo.removeEntityFromPositionTile();

    // Fixed world positions for the four wall orientations, independently specified.
    const float rotations[4]={0.0f,90.0f,180.0f,270.0f};
    const float expectedX[4]={3.0f,2.88f,3.0f,3.12f};
    const float expectedY[4]={0.12f,0.0f,-0.12f,0.0f};
    for(int orientation=0; orientation<4; ++orientation)
    {
        ItemBagEntity rotatedBook;
        rotatedBook.tile=&floor; floor.entities.push_back(&rotatedBook);
        furniture.rotation=rotations[orientation];
        // A raised fixture also verifies that support height is relative to the furniture.
        furniture.position.z=0.25f;
        library.notifyCarryingStateChanged(&worker,&rotatedBook);
        check(rotatedBook.tile==&shelf,"rotated offset retains shelf tile occupancy");
        check(std::abs(rotatedBook.position.x-expectedX[orientation])<0.00001f &&
            std::abs(rotatedBook.position.y-expectedY[orientation])<0.00001f &&
            std::abs(rotatedBook.position.z-1.76358f)<0.00001f,"fixed rotated server placement");
        check(std::abs(rotatedBook.clientPosition.x-expectedX[orientation])<0.00001f &&
            std::abs(rotatedBook.clientPosition.y-expectedY[orientation])<0.00001f &&
            std::abs(rotatedBook.clientPosition.z-1.76358f)<0.00001f &&
            rotatedBook.clientSeat==&owner && rotatedBook.clientViewers==shelf.visibleSeats,
            "fixed rotated client snapshot");
        check(rotatedBook.visibilityRemovals==1 && rotatedBook.visibilityAdds==1 &&
            rotatedBook.getItem()!=nullptr && library.mSkillPoints==200.0,"placement preserves visibility and delayed reward");
        check(library.openResearchBook() && rotatedBook.deleted && library.mSkillPoints==300.0,
            "rotated shelf book grants exactly one research reward");
        library.mSkillPoints=200.0;
    }

    ItemBagEntity floorBook; floorBook.tile=&floor; floor.entities.push_back(&floorBook);
    furniture.mesh="Bookcase";
    check(!library.hasCarryEntitySpot(&floorBook) && !library.openResearchBook(),"workstation bookcase is not a shelf");
    check(floorBook.getEntityCarryType(&worker)==EntityCarryType::itemBag,"workstation floor books can be moved");
    furniture.mesh="Bookshelf"; floorBook.mItem->mGhostItem=GhostItem::manaCrystal;
    check(!library.hasCarryEntitySpot(&floorBook),"shelf accepts research books only");

    std::stringstream savedAgain(saved.str());
    check(restored.importFromStream(savedAgain),"shelved record reloads after legacy record");
    restored.tile=&shelf; shelf.entities.push_back(&restored);
    check(restored.getEntityCarryType(&worker)==EntityCarryType::notCarryable && library.mSkillPoints==200.0,
        "loaded delivered book waits for researcher without awarding points on load");
    check(library.openResearchBook() && restored.deleted && library.mSkillPoints==300.0,
        "researcher opens loaded delivered book exactly once");
    ItemBagEntity loadedFloor;
    std::stringstream floorAgain(floorSave.str());
    check(loadedFloor.importFromStream(floorAgain),"floor record reloads");
    loadedFloor.tile=&shelf; shelf.entities.push_back(&loadedFloor);
    check(!library.openResearchBook() && loadedFloor.getEntityCarryType(&worker)==EntityCarryType::itemBag,
        "loaded floor book on bookshelf tile still requires delivery");
    loadedFloor.removeEntityFromPositionTile();
    ItemBagEntity invalid;
    std::stringstream wrongKind("3 0 0 ShelvedResearchBook TestBook 3");
    check(!invalid.importFromStream(wrongKind),"shelf marker cannot turn another product into a shelved book");
    std::stringstream truncated("3 0 0 ShelvedResearchBook");
    check(!invalid.importFromStream(truncated),"truncated shelf record fails loading");

    // Run actual bag pickup and worker attachment before navigation, completion and interruption.
    furniture.mesh="Bookshelf"; furniture.rotation=0; furniture.position.z=0;
    worker.routeAllowed=true; worker.seat=&owner; worker.atShelf=false;
    library.mSkillPoints=0;
    ItemBagEntity carriedBook; carriedBook.tile=&floor; floor.entities.push_back(&carriedBook);
    carriedBook.markResearchBookShelved();
    carriedBook.setCarryLock(worker,true);
    carriedBook.notifyEntityCarryOn(&worker);
    worker.carryEntity(&carriedBook);
    check(!carriedBook.getIsOnMap() && !carriedBook.isResearchBookShelved() &&
        worker.mCarriedEntity==&carriedBook &&
        std::find(floor.entities.begin(),floor.entities.end(),&carriedBook)==floor.entities.end(),
        "production pickup attaches off-map cargo and revokes shelf state");
    const int walksBefore=worker.walked;
    {
        CreatureActionCarryEntity delivery(worker,&carriedBook,&library);
        delivery.handleCarryEntity(worker,&carriedBook,&shelf);
        check(!delivery.mDelivered && worker.walked==walksBefore+1 && !carriedBook.getIsOnMap(),
            "off-map carried book walks to shelf without early completion");
        worker.atShelf=true;
        delivery.handleCarryEntity(worker,&carriedBook,&shelf);
        check(delivery.mDelivered && !carriedBook.getIsOnMap() && library.mSkillPoints==0,
            "off-map cargo completes only at shelf approach and has no pickup reward");
    }
    check(worker.mCarriedEntity==nullptr && carriedBook.getIsOnMap() && !carriedBook.locked &&
        carriedBook.tile==&shelf && carriedBook.isResearchBookShelved(),
        "release restores map occupancy before library confirms shelf delivery");
    check(carriedBook.visibilityRemovals==2 && carriedBook.visibilityAdds==1 &&
        carriedBook.clientPosition.z==carriedBook.position.z && carriedBook.position.z==1.51358f,
        "pickup removes old snapshot and successful release publishes shelf placement");
    check(library.openResearchBook() && library.mSkillPoints==100 && carriedBook.deleted,
        "researcher consumes the normally picked-up book exactly once");
    check(!library.openResearchBook() && library.mSkillPoints==100,"carried book cannot reward twice");

    ItemBagEntity interruptedBook; interruptedBook.tile=&floor; floor.entities.push_back(&interruptedBook);
    interruptedBook.setCarryLock(worker,true);
    interruptedBook.notifyEntityCarryOn(&worker);
    worker.carryEntity(&interruptedBook);
    worker.atShelf=false;
    {
        CreatureActionCarryEntity interrupted(worker,&interruptedBook,&library);
        interrupted.handleCarryEntity(worker,&interruptedBook,&shelf);
        check(!interrupted.mDelivered && !interruptedBook.getIsOnMap(),"walking pickup remains off-map");
        worker.atShelf=true;
    }
    check(worker.mCarriedEntity==nullptr && interruptedBook.getIsOnMap() && !interruptedBook.locked &&
        interruptedBook.tile==&floor && !interruptedBook.isResearchBookShelved() &&
        interruptedBook.getEntityCarryType(&worker)==EntityCarryType::itemBag,
        "interrupted production pickup releases recoverable floor cargo even at shelf approach");
    check(!library.openResearchBook() && library.mSkillPoints==100 && interruptedBook.visibilityAdds==0,
        "interrupted pickup cannot publish shelf placement or grant research");
    std::cout << "library shelf delivery: OK\n";
}
'''


def main():
    """Exercise production pickup, off-map carry, completion, interruption and researcher-only rewards."""
    library = read("source/rooms/RoomLibrary.cpp")
    carry = read("source/creatureaction/CreatureActionCarryEntity.cpp")
    constructor = function(carry, "CreatureActionCarryEntity::CreatureActionCarryEntity(Creature& creature, GameEntity& entityToCarry, Building&")
    assert constructor.index("mEntityToCarry->notifyEntityCarryOn(&mCreature);") < constructor.index(
        "mCreature.carryEntity(mEntityToCarry);")
    entity = read("source/entities/GameEntity.cpp")
    assert "setIsOnMap(false);" in function(entity, "void GameEntity::removeEntityFromPositionTile(")
    assert "setIsOnMap(true);" in function(entity, "void GameEntity::addEntityToPositionTile(")
    assert '#include "utils/MakeUnique.h"' in carry
    bag = read("source/entities/ItemBagEntity.cpp")
    use = function(library, "bool RoomLibrary::useRoom(")
    assert use.index("if(!approach.empty())") < use.index("openResearchBook();")
    assert use.index("openResearchBook();") < use.index("getSeat()->addSkillPoints(wholePoints)")
    assert "openResearchBook" not in function(library, "void RoomLibrary::doUpkeep(")
    header = read("source/rooms/RoomLibrary.h")
    assert "bool openResearchBook();" in header[header.index("private:"):]
    grab = function(read("source/creatureaction/CreatureActionGrabEntity.cpp"),
                    "bool CreatureActionGrabEntity::handleGrabEntity(")
    assert "tile = building->askSpotForCarriedEntity(entityToCarry);" in grab
    destructor = function(carry, "CreatureActionCarryEntity::~CreatureActionCarryEntity(")
    assert destructor.index("notifyEntityCarryOff(pos)") < destructor.index("notifyCarryingStateChanged(")
    assert "this, std::ref(mCreature), mEntityToCarry, mTileDest" in function(
        carry, "std::function<bool()> CreatureActionCarryEntity::action(")
    code = PRELUDE
    for signature in ("Tile* RoomLibrary::bookshelfTile(", "bool RoomLibrary::hasCarryEntitySpot(",
                      "bool RoomLibrary::isBookshelfTile(", "bool RoomLibrary::getBookshelfApproach(",
                      "Tile* RoomLibrary::askSpotForCarriedEntity(",
                      "void RoomLibrary::notifyCarryingStateChanged(", "bool RoomLibrary::openResearchBook("):
        code += function(library, signature) + "\n"
    code += function(bag, "EntityCarryType ItemBagEntity::getEntityCarryType(") + "\n"
    bag_header = read("source/entities/ItemBagEntity.h")
    for signature, qualified in (("bool isResearchBookShelved()", "bool ItemBagEntity::isResearchBookShelved()"),
                                 ("void markResearchBookShelved()", "void ItemBagEntity::markResearchBookShelved()")):
        code += function(bag_header, signature).replace(signature, qualified, 1) + "\n"
    for signature in ("void ItemBagEntity::pickup(", "void ItemBagEntity::drop(",
                      "void ItemBagEntity::notifyEntityCarryOn(", "void ItemBagEntity::notifyEntityCarryOff(",
                      "void ItemBagEntity::exportToStream(", "bool ItemBagEntity::importFromStream("):
        code += function(bag, signature) + "\n"
    code += function(carry, "CreatureActionCarryEntity::~CreatureActionCarryEntity(") + "\n"
    code += function(read("source/entities/Creature.cpp"), "void Creature::carryEntity(") + "\n"
    code += function(carry, "bool CreatureActionCarryEntity::handleCarryEntity(") + "\n" + CASES
    with tempfile.TemporaryDirectory(prefix="library-shelf-") as directory:
        work = Path(directory)
        source, binary = work / "check.cpp", work / "check.exe"
        source.write_text(code, encoding="utf-8")
        subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++14", str(source), "/Fe:" + str(binary)],
                       cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=180)
        subprocess.run([str(binary)], cwd=work, check=True, stdin=subprocess.DEVNULL, timeout=60)


if __name__ == "__main__":
    main()
