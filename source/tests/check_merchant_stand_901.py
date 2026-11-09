"""Owner decision 901 (1): the merchant walked to a wall, vanished there and showed up elsewhere. No compiler, no game.

Causes found by reading
  rig offset      Merchant.mesh is modelled at the front corner of a sales table, (+0.64, -0.76) from its origin (STAND in
                  the asset notes). The node turns with the figure and the server walks the origin over the tile centres of
                  tables and shelves, so the figure appeared up to 0.76 tiles inside the wall below the shelf. The mesh and
                  textures stay untouched: RenderManager hangs the entity on a child node that cancels the offset.
  furniture route the route led over the tile centres of the tables and the wall shelves (solid furniture), his tile was
                  taken as the stop; now he walks over free floor tiles only and stands beside the stop
  teleport        the fallback setPosition went to the central (table) tile; now to a free tile beside the first table

One check per fault; call (from the repository root): python source/tests/check_merchant_stand_901.py
"""
import re, sys, pathlib

root = pathlib.Path(__file__).resolve().parents[2]
fails = []

def text(rel):
    return (root / rel).read_text(encoding="utf-8", errors="replace")

render = text("source/render/RenderManager.cpp")
ent = text("source/entities/MerchantEntity.cpp")
room = text("source/rooms/RoomMerchant.cpp")
room_h = text("source/rooms/RoomMerchant.h")

# rig offset cancelled by a child node, same numbers as the asset notes, mesh untouched
if not re.search(r"MERCHANT_RIG_OFFSET_X = 0\.64f", render) or not re.search(r"MERCHANT_RIG_OFFSET_Y = -0\.76f", render):
    fails.append("rig offset: the offset constants 0.64, -0.76 are missing in RenderManager.cpp")
create = render.split("void RenderManager::rrCreateRenderedMovableEntity")[1].split("renderedMovableEntity->setParentSceneNode")[0]
if not re.search(r'meshName == "Merchant".{0,700}createChildSceneNode.{0,200}setPosition\(-MERCHANT_RIG_OFFSET_X, -MERCHANT_RIG_OFFSET_Y', create, re.S):
    fails.append("rig offset: the Merchant figure is not hung on a child node that cancels the offset")
destroy = render.split("void RenderManager::rrDestroyRenderedMovableEntity")[1].split("destroySceneNode(node)")[0]
if "detachFromParent()" not in destroy or '"_figure"' not in destroy:
    fails.append("rig offset: the figure node is not destroyed with the entity")

# free tiles only
if "isFurnitureTile(next)" not in ent or "isFullTile()" not in ent:
    fails.append("route: the walk may lead over furniture or full tiles")
if "getStandTileBeside" not in room or "isFurnitureTile" not in room_h:
    fails.append("stand tile: RoomMerchant has no free stand tile beside a stop")
stand = room.split("Tile* RoomMerchant::getStandTileBeside")[1].split("\n}\n")[0]
if "isFullTile()" not in stand or "getCoveringRoom() == this" not in stand or "!isFurnitureTile(next)" not in stand:
    fails.append("stand tile: it must be a free floor tile of the room")
if "setPosition(mCentralActiveSpotTiles" in room or "getStandTileBeside(mCentralActiveSpotTiles.front())" not in room:
    fails.append("spawn: the merchant must start beside the first table")

# never vanish: the teleport goes to a stand tile; the walk is checked to be reachable before it starts
if "getStandTileBeside(home->getSalesTables().front())" not in ent:
    fails.append("teleport: the fallback must use a free stand tile")
if "previous.find(next) != previous.end() && next != start" not in ent:
    fails.append("route: the stand tile must be reachable on free tiles")
if "removeFromGameMap" in ent.split("void MerchantEntity::doUpkeep")[1].split("mDealTurns > 0.0")[0] and \
        "RoomMerchant::getForSeat(*getGameMap(), getSeat()) == nullptr" not in ent:
    fails.append("vanish: the figure is removed without the room being gone")

if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
print("OK check_merchant_stand_901")
