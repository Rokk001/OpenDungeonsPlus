"""Static guards for direct own-creature sight; does not compile or start the game."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# Isolate one production function without executing C++.
def function(path, signature):
    source = (ROOT / path).read_text(encoding="utf-8")
    block = source[source.index(signature):]
    return block[:block.index("\n}\n")]


creature = function("source/entities/Creature.cpp", "void Creature::computeVisibleTiles()")
for guard in ("getHP() <= 0.0", "isKo()", "mSeatPrison != nullptr", "!getIsOnMap()"):
    assert creature.index(guard) < creature.index("notifyOwnCreatureVision(tile)")
assert creature.index("updateTilesInSight();") < creature.index("for(Tile* tile : mVisibleTiles)")
assert "getSeat()->notifyOwnCreatureVision(tile);" in creature
owner = function("source/game/Seat.cpp", "void Seat::notifyOwnCreatureVision(")
assert "mOwnCreatureSightAgeTurns = 0" in owner
assert "mTilesStates[tile].mOwnCreatureSightAgeTurns" in owner
for signature in ("void Seat::applyRevealedTiles()", "void Seat::notifyVisionOnTile("):
    assert "mOwnCreatureSightAgeTurns" not in function("source/game/Seat.cpp", signature)
print("Direct owner sight excludes KO, dead, jailed, carried, allied and scripted vision sources: PASS (static only)")

advance = function("source/game/Seat.cpp", "void Seat::clearTilesWithVision()")
assert "++p.second.mOwnCreatureSightAgeTurns" in advance
assert "p.second.mOwnCreatureSightAgeTurns >= 0" in advance
save = function("source/game/Seat.cpp", "bool Seat::exportSeatToStream(")
load = function("source/game/Seat.cpp", "bool Seat::importSeatFromStream(")
assert "[OwnCreatureSightAges]" in save and "[OwnCreatureSightAges]" in load
assert "state.mOwnCreatureSightAgeTurns = age;" in load
assert "age < 0" in load
assert "mOwnCreatureSightAgeTurns = p.second.mOwnCreatureSightAgeTurns" in function("source/game/Seat.cpp", "void Seat::initSeat()")
print("Own-creature sight ages advance on simulation passes and preserve their age through optional save records: PASS (static only)")

# Seat records load before tile dimensions exist; tile lookup validates coordinates during initialization.
init = function("source/game/Seat.cpp", "void Seat::initSeat()")
assert init.index("if(tile == nullptr)") < init.index("mOwnCreatureSightAgeTurns = p.second.mOwnCreatureSightAgeTurns")
assert "getMapSizeX()" not in load[load.index('if(str == "[OwnCreatureSightAges]")'):]
