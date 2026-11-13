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
#include <stdexcept>
#include <string>
#include <vector>
#define OD_LOG_ERR(message) ((void)0)
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
namespace EntityAnimation { const int walk_anim=1, idle_anim=2; }
enum class GameEntityType { itemBagEntity, missileObject, other };
enum class RoomType { library, treasury, ghostRoom, merchant };
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
    void removeEntityFromPositionTile()
    { tile->entities.erase(std::remove(tile->entities.begin(),tile->entities.end(),this),tile->entities.end()); }
    void removeFromGameMap() { onMap=false; removed=true; }
    void deleteYourself() { deleted=true; }
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
//! \brief Supplies the room's shelf lookup and destination checks.
struct Room
{
    RoomType type=RoomType::library;
    Seat* seat=nullptr;
    Tile* shelfTile=nullptr;
    BuildingObject* object=nullptr;
    int released=0;
    virtual bool hasCarryEntitySpot(GameEntity*) { return false; }
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
    removeEntityFromPositionTile(); position=value;
    for(Tile* candidate : world)
        if(candidate->x==int(std::round(value.x)) && candidate->y==int(std::round(value.y))) tile=candidate;
    tile->entities.push_back(this);
}
//! \brief Holds a worker's route and action effects for the carry handler.
struct Creature
{
    Seat* seat=nullptr;
    Tile* tile=nullptr;
    bool routeAllowed=true, atShelf=false;
    int popped=0, walked=0, pushed=0, destinations=0;
    Seat* getSeat() { return seat; }
    Tile* getPositionTile() { return tile; }
    std::string getName() { return "worker"; }
    Ogre::Vector3 getPosition() { return Ogre::Vector3(); }
    void popAction() { ++popped; }
    bool setDestination(Tile*) { ++destinations; return true; }
    void setWalkPath(int,int,bool,bool,const std::vector<Ogre::Vector2>&,bool,bool) { ++walked; }
    void pushAction(std::unique_ptr<class CreatureActionWalkToTile>) { ++pushed; }
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
{ GhostItem mGhostItem=GhostItem::researchBook; bool mMerchantGoods=false, mSoulCrystal=false; };
//! \brief Exposes the unchanged bag carry predicate and transfer operation.
struct ItemBagEntity : GameEntity
{
    std::unique_ptr<ItemInstance> mItem;
    uint32_t mIdleTurns=0;
    ItemBagEntity():mItem(new ItemInstance) { type=GameEntityType::itemBagEntity; }
    ItemInstance* getItem() { return mItem.get(); }
    std::unique_ptr<ItemInstance> takeItem() { return std::move(mItem); }
    bool isWantedByUseRoom(Creature&) { return false; }
    EntityCarryType getEntityCarryType(Creature*);
};
//! \brief Exposes production library functions and retained research for bounded assertions.
struct RoomLibrary : Room
{
    std::vector<Tile*> mCoveredTiles;
    double mSkillPoints=0;
    Tile* bookshelfTile();
    bool hasCarryEntitySpot(GameEntity*) override;
    Tile* askSpotForCarriedEntity(GameEntity*);
    void notifyCarryingStateChanged(Creature*,GameEntity*);
    bool isBookshelfTile(Tile*);
    bool getBookshelfApproach(Creature&,Tile*,std::vector<Ogre::Vector2>&);
    bool openResearchBook();
};
struct CreatureActionCarryEntity
{ static bool handleCarryEntity(Creature&,GameEntity*,Tile*); };
'''

CASES = r'''
//! \brief Checks floor recovery, navigation, fixed top-shelf placement in four orientations and single-use rewards.
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
    ItemBagEntity book; book.tile=&floor; floor.entities.push_back(&book);

    check(!library.hasCarryEntitySpot(&book),"shelfless library refuses delivery");
    check(library.askSpotForCarriedEntity(&book)==nullptr,"no floor fallback");
    check(!library.openResearchBook(),"shelfless floor book survives research");
    check(book.getEntityCarryType(&worker)==EntityCarryType::itemBag,"floor book can leave shelfless library");
    library.object=&furniture;
    check(library.askSpotForCarriedEntity(&book)==&shelf,"actual shelf selected");
    check(!library.openResearchBook(),"library floor book is not opened");
    check(book.getEntityCarryType(&worker)==EntityCarryType::itemBag,"floor book remains carryable with shelves");

    CreatureActionCarryEntity::handleCarryEntity(worker,&book,&shelf);
    check(worker.walked==1 && worker.pushed==1 && worker.popped==0,"shelf delivery queues furniture approach");
    check(worker.destinations==0,"worker does not walk directly into shelf tile");
    library.notifyCarryingStateChanged(&worker,&book);
    check(book.tile==&floor && book.getItem()!=nullptr,"interrupted delivery leaves book on floor");
    worker.routeAllowed=false;
    CreatureActionCarryEntity::handleCarryEntity(worker,&book,&shelf);
    library.notifyCarryingStateChanged(&worker,&book);
    check(worker.popped==1 && book.tile==&floor,"blocked shelf preserves book");
    worker.routeAllowed=true; worker.atShelf=true;
    worker.seat=&enemy;
    library.notifyCarryingStateChanged(&worker,&book);
    check(book.tile==&floor,"foreign worker cannot deliver");
    worker.seat=&owner;
    CreatureActionCarryEntity::handleCarryEntity(worker,&book,&shelf);
    library.notifyCarryingStateChanged(&worker,&book);
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
    book.locked=true;
    check(!library.openResearchBook(),"reserved book cannot be consumed");
    book.locked=false; book.onMap=false;
    check(!library.openResearchBook(),"off-map book cannot be consumed");
    book.onMap=true;
    ItemBagEntity second; second.tile=&shelf; shelf.entities.push_back(&second);
    check(library.openResearchBook(),"researcher opens delivered book");
    check(book.deleted && book.removed && book.getItem()==nullptr,"opened book removed completely");
    check(library.mSkillPoints==100.0 && second.getItem()!=nullptr,"one book per work cycle");
    check(library.openResearchBook() && library.mSkillPoints==200.0,"next work cycle opens second book");
    check(!library.openResearchBook() && library.mSkillPoints==200.0,"no repeated reward");

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
    std::cout << "library shelf delivery: OK\n";
}
'''


def main():
    """Run unchanged production rules and check their researcher-only call wiring."""
    library = read("source/rooms/RoomLibrary.cpp")
    carry = read("source/creatureaction/CreatureActionCarryEntity.cpp")
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
    code = PRELUDE
    for signature in ("Tile* RoomLibrary::bookshelfTile(", "bool RoomLibrary::hasCarryEntitySpot(",
                      "bool RoomLibrary::isBookshelfTile(", "bool RoomLibrary::getBookshelfApproach(",
                      "Tile* RoomLibrary::askSpotForCarriedEntity(",
                      "void RoomLibrary::notifyCarryingStateChanged(", "bool RoomLibrary::openResearchBook("):
        code += function(library, signature) + "\n"
    code += function(bag, "EntityCarryType ItemBagEntity::getEntityCarryType(") + "\n"
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
