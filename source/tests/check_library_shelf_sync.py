"""Check shelf placement packet ordering and shelf-only consumption without compiling."""
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def read(relative):
    """Read a production source independently of the caller's working directory."""
    return (REPO / relative).read_text(encoding="utf-8")


def function(text, signature):
    """Extract one complete production function for scoped assertions."""
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def ordered(text, *fragments):
    """Require each protocol operation once in the specified order."""
    previous = -1
    for fragment in fragments:
        assert text.count(fragment) == 1, fragment
        current = text.index(fragment)
        assert current > previous, fragment
        previous = current


def main():
    """Check release, replacement snapshot, visibility and delayed removal wiring."""
    library = read("source/rooms/RoomLibrary.cpp")
    delivery = function(library, "void RoomLibrary::notifyCarryingStateChanged(")
    ordered(delivery, "!carriedEntity->getIsOnMap()", "!hasCarryEntitySpot(carriedEntity)",
            "const bool reached =", "if(!reached)",
            "carriedEntity->fireRemoveEntityToSeatsWithVision();",
            "carriedEntity->setSeat(getSeat());",
            "carriedEntity->setPosition(Ogre::Vector3(shelf->getPosition().x - 0.12f * std::sin(angle),\n"
            "        shelf->getPosition().y + 0.12f * std::cos(angle), shelf->getPosition().z + 1.51358f));",
            "static_cast<ItemBagEntity*>(carriedEntity)->markResearchBookShelved();",
            "carriedEntity->notifySeatsWithVision(tile->getSeatsWithVision());")
    assert "takeItem" not in delivery and "mSkillPoints" not in delivery
    destructor = function(read("source/creatureaction/CreatureActionCarryEntity.cpp"),
                          "CreatureActionCarryEntity::~CreatureActionCarryEntity(")
    ordered(destructor, "notifyEntityCarryOff(pos)", "mCreature.releaseCarriedEntity();",
            "mBuildingDest->notifyCarryingStateChanged(")
    entity = read("source/entities/GameEntity.cpp")
    removal = function(entity, "void GameEntity::fireRemoveEntityToSeatsWithVision(")
    ordered(removal, "fireRemoveEntity(seat,gameMap->getNodeType());", "mSeatsWithVisionNotified.clear();")
    visibility = function(entity, "void GameEntity::notifySeatsWithVision(")
    assert "fireAddEntity(seat, false ,nt);" in visibility
    snapshot = function(entity, "void GameEntity::exportToPacket(")
    ordered(snapshot, "os << seatId;", "os << mName;", "os << mMeshName;", "os << mPosition;")
    rendered = read("source/entities/RenderedMovableEntity.cpp")
    addition = function(rendered, "void RenderedMovableEntity::fireAddEntity(")
    assert "exportToPacket(serverNotification->mPacket, seat);" in addition
    assert "queueServerNotification(serverNotification);" in addition
    bag = read("source/entities/ItemBagEntity.cpp")
    assert "mItem->exportToPacket(packet);" in function(bag, "void ItemBagEntity::exportToPacket(")
    opening = function(library, "bool RoomLibrary::openResearchBook(")
    ordered(opening, 'shelf->getMeshName() != "Bookshelf"', "tile->getEntitiesInTile()",
            "!entity->getIsOnMap() || entity->isCarryLocked()", "GhostItem::researchBook",
            "!bag->isResearchBookShelved()",
            "mSkillPoints +=", "bag->takeItem();", "bag->removeFromGameMap();", "return true;")
    assert "openResearchBook();" in function(library, "bool RoomLibrary::useRoom(")
    assert "openResearchBook" not in function(library, "void RoomLibrary::doUpkeep(")
    assert "isBookshelfTile(tile)" in function(bag, "EntityCarryType ItemBagEntity::getEntityCarryType(")
    assert "isResearchBookShelved() &&" in function(bag, "EntityCarryType ItemBagEntity::getEntityCarryType(")
    for signature in ("void ItemBagEntity::pickup(", "void ItemBagEntity::drop(",
                      "void ItemBagEntity::notifyEntityCarryOn(", "void ItemBagEntity::notifyEntityCarryOff("):
        assert "mResearchBookShelved = false;" in function(bag, signature)
    assert 'stream << "ShelvedResearchBook ";' in function(bag, "void ItemBagEntity::exportToStream(")
    assert 'mResearchBookShelved = id == "ShelvedResearchBook";' in function(bag, "bool ItemBagEntity::importFromStream(")
    assert "packet << mResearchBookShelved;" in function(bag, "void ItemBagEntity::exportToPacket(")
    assert "packet >> mResearchBookShelved;" in function(bag, "void ItemBagEntity::importFromPacket(")
    print("library shelf synchronization: OK (non-compiling source checks)")


if __name__ == "__main__":
    main()
