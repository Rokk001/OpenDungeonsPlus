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

# Delayed fog is a separate presentation state; ordinary visibility is not extended.
notify = function("source/game/Seat.cpp", "void Seat::sendVisibleTiles()")
assert "std::ceil(30.0 * ODApplication::turnsPerSecond)" in notify
assert "knownOwner != this && !isAlliedSeat(knownOwner)" in notify
assert "!knownOwner->isRogueSeat()" in notify
assert "if(enemyFog != p.second.mEnemyFogNotified)" in notify
assert notify.index("fogChanges.push_back") < notify.index("if(p.second.mVisionTurnCurrent == p.second.mVisionTurnLast)")
assert "ServerNotificationType::enemyTerritoryFog, getPlayer()" in notify
client = (ROOT / "source/network/ODClient.cpp").read_text(encoding="utf-8")
packet = client[client.index("case ServerNotificationType::enemyTerritoryFog:"):client.index("case ServerNotificationType::refreshTiles:")]
assert "tile->setEnemyTerritoryFog(fogged)" in packet
assert "setLocalPlayerHasVision" not in packet and "setEverVisible" not in packet
assert "tile->refreshMesh(NodeType::MTILES_NODE, gameMap)" in packet
print("Thirty-second enemy-only fog changes reach only the owning client without extending real sight: PASS (static only)")

render = function("source/render/RenderManager.cpp", "void RenderManager::rrRefreshTile(")
cloud = render[render.index("// Only previously discovered enemy territory receives") :]
assert "if(tile.getEverVisible() && tileMeshNode != nullptr)" in cloud
assert "tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() == nullptr" in cloud
assert '!tile.getEnemyTerritoryFog() && tile.getFogOfWarCloud() != nullptr' in cloud
assert 'tile.setFogOfWarCloud(nullptr)' in cloud
print("Previously explored enemy clouds follow authoritative fog changes without covering never-seen earth: PASS (static only)")

# Legacy grace is gated by absence of the entire optional section, not by an individual missing tile age.
assert 'mHasSavedOwnCreatureSightAges = true;' in load[load.index('if(str == "[OwnCreatureSightAges]")'):]
legacy = init[init.index('// Legacy saves have no sight ages:'):]
legacy = legacy[:legacy.index('mTilesStates[tile].mOwnCreatureSightAgeTurns')]
assert '!mHasSavedOwnCreatureSightAges &&' in legacy
assert 'everVisitedFlagPool[tile->getX()][tile->getY()][mId]' in legacy
assert 'p.second.mOwnCreatureSightAgeTurns = 0;' in legacy
assert init.rfind('mHasSavedOwnCreatureSightAges = true;') > init.index('getPlayer()->markTilesForDigging')
assert 'os << "[OwnCreatureSightAges]\\n";' in save
assert 'os << "[/OwnCreatureSightAges]\\n";' in save
print("Old saves get one initial grace period only; current and repeated loads retain saved ages: PASS (static only)")
