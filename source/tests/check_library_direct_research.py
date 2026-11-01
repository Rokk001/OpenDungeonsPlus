"""Check direct library research and legacy book conversion wiring."""
from pathlib import Path

repo = Path(__file__).resolve().parents[2]
library = (repo / "source/rooms/RoomLibrary.cpp").read_text(encoding="utf-8")
temple = (repo / "source/rooms/RoomDungeonTemple.cpp").read_text(encoding="utf-8")
loader = (repo / "source/gamemap/MapHandler.cpp").read_text(encoding="utf-8")
config = (repo / "config/rooms.cfg").read_text(encoding="utf-8")

use = library[library.index("bool RoomLibrary::useRoom("):library.index("void RoomLibrary::exportToStream(")]
assert "new SkillEntity" not in use
assert "getSeat()->addSkillPoints(wholePoints)" in use
assert "mSkillPoints -= wholePoints" in use
assert 'std::setprecision(17) << mSkillPoints' in library and 'is >> mSkillPoints' in library
assert "LibrarySkillPointsBook" not in config and "LibrarySkillPointsBook" not in library
assert "checkIfAvailableSpot" not in library
assert "case GameEntityType::skillEntity:" not in temple
assert 'readGameEntity(gameMap, "SkillEntity", GameEntityType::skillEntity' in loader
assert 'legacyBook->getSeat()->addSkillPoints(legacyBook->getSkillPoints())' in loader
assert 'delete legacyBook' in loader
loaded = library[library.index("bool RoomLibrary::importFromStream("):]
assert "getSeat()->addSkillPoints(wholePoints)" in loaded
assert "mSkillPoints -= wholePoints" in loaded
print("CHECKS OK")
