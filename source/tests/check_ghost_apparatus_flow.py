"""Follow one ectoplasm per apparatus through the item flow without compiling (GHOST-APPARATUS-PLAN G1 to G5).

For the mana still, the ghost press and the soul forge one ectoplasm comes out of the cauldron, is picked up, stamped with
the chosen apparatus, carried to that apparatus, queued, worked and turned into its product, which then goes to the room
that uses it. Every step of the model below is pinned to the line of the game source it follows, and the values come from
the shipped config, so a change of the source or the config that breaks the way of one apparatus fails here."""
from pathlib import Path
import math
import re

repo = Path(__file__).resolve().parents[2]


# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")


# Return a complete brace-delimited body that starts at the signature.
def body(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


# Assert that every fragment occurs in the text, naming the step it pins.
def has(text, step, *fragments):
    for fragment in fragments:
        assert fragment in text, (step, fragment)


# Read one numeric key of a config file.
def scalar(path, key):
    rows = re.findall(r"^\s*" + re.escape(key) + r"\s+([-+0-9.eE]+)\s*$", read(path), re.M)
    assert len(rows) == 1, (key, rows)
    return float(rows[0])


# Evaluate a chain of "kind==GhostProduct::x?a:..." of the source for one kind.
def ternary(expression, kind):
    expression = expression.strip()
    if re.fullmatch(r"\d+", expression):
        return int(expression)
    step = re.match(r"kind==GhostProduct::(\w+)\?(\d+):(.*)$", expression)
    assert step, expression
    return int(step.group(2)) if step.group(1) == kind else ternary(step.group(3), kind)


ROOM = read("source/rooms/RoomGhostRoom.cpp")
KINDS = {name: int(value) for name, value in re.findall(r"(\w+)\s*=\s*(\d+)",
    re.search(r"enum class GhostProduct : uint32_t \{([^}]*)\};", read("source/game/SeatData.h")).group(1))}
NAMES = {value: name for name, value in KINDS.items()}
TURNS = scalar("config/rooms.cfg", "GhostApparatusTurns")
PER_CRYSTAL = scalar("config/rooms.cfg", "GhostEctoplasmPerCrystal")


def unlock_level(kind):
    rule = re.search(r"\{ return (.*); \}", body(ROOM, "uint32_t RoomGhostRoom::getUnlockLevel(")).group(1)
    return ternary(rule, kind)


def apparatus_mesh(kind):
    lookup = body(ROOM, "const std::string& RoomGhostRoom::getApparatusMesh(")
    meshes = [mesh.strip().strip('"') for mesh in re.search(r"meshes\[APPARATUS_COUNT\]=\{([^}]*)\};", lookup).group(1).split(",")]
    index = re.search(r"return meshes\[(.*)\];", lookup).group(1)
    return meshes[KINDS[kind] if index == "static_cast<uint32_t>(kind)" else ternary(index, kind)]


def use_rooms():
    switch = body(read("source/entities/ItemBagEntity.cpp"), "RoomType ItemBagEntity::getUseRoomType(")
    rooms = dict(re.findall(r"case GhostItem::(\w+): return RoomType::(\w+);", switch))
    rooms["none"] = re.search(r"default: return RoomType::(\w+);", switch).group(1)
    return rooms


# One ghost room of one keeper as the source runs it, one apparatus record per kind.
class Room:
    def __init__(self, level, chosen):
        self.level, self.chosen = level, chosen
        self.apparatus = {kind: {"queue": 0, "working": False, "turns": 0.0, "crystal": 0, "state": None,
            "stand": "stand-of-" + kind} for kind in KINDS}
        self.floor = []

    def unlocked(self, kind):
        has(body(ROOM, "bool RoomGhostRoom::isApparatusUnlocked("), "unlock by room research",
            "seat.getSkillLevel(SkillType::roomGhostRoom)>=getUnlockLevel(kind)")
        return self.level >= unlock_level(kind)

    def chosen_apparatus(self):
        has(body(ROOM, "GhostProduct RoomGhostRoom::getChosenApparatus("), "locked choice is the mana still",
            "isApparatusUnlocked(seat,seat.getGhostProduct())?seat.getGhostProduct():GhostProduct::mana")
        return self.chosen if self.unlocked(self.chosen) else "mana"

    # Step 1: the full ectoplasm comes out of the cauldron as an item without an apparatus
    def cauldron(self):
        has(body(ROOM, "void RoomGhostRoom::produceEctoplasm("), "cauldron", "spawnItem(*drop,ItemInstance::createGhostItem(GhostItem::ectoplasm),seat);")
        has(read("source/entities/ItemInstance.h"), "new item has no apparatus", "mGhostItem(GhostItem::none), mGhostTarget(-1) {}")
        item = {"ghost": "ectoplasm", "target": -1, "carried": False}
        self.floor.append(item)
        return item

    # Step 2: the worker picks it up; the item keeps the apparatus chosen now
    def pick_up(self, item):
        has(read("source/creatureaction/CreatureActionGrabEntity.cpp"), "stamp at pick up",
            "if(bagItem->mGhostItem == GhostItem::ectoplasm)\n            bagItem->mGhostTarget = static_cast<int32_t>(RoomGhostRoom::getChosenApparatus(*creature.getSeat()));",
            "preferredRoom = ItemBagEntity::getUseRoomType(*bagItem);",
            "tile = static_cast<RoomGhostRoom*>(building)->getApparatusStandTile(static_cast<GhostProduct>(bagItem->mGhostTarget));")
        item["target"] = KINDS[self.chosen_apparatus()]
        item["carried"] = True
        self.floor.remove(item)
        assert use_rooms()["ectoplasm"] == "ghostRoom"
        return self.carry_spot(item)

    # Step 3: the room offers the stand tile of exactly that apparatus
    def carry_spot(self, item):
        has(body(ROOM, "GhostProduct RoomGhostRoom::getDeliveryTarget("), "carried ectoplasm keeps its apparatus",
            "if(carriedEntity.isCarryLocked() && item.mGhostTarget>=0 && item.mGhostTarget<static_cast<int32_t>(APPARATUS_COUNT))\n        return static_cast<GhostProduct>(item.mGhostTarget);")
        has(body(ROOM, "bool RoomGhostRoom::hasCarryEntitySpot("), "only to an unlocked apparatus",
            "return isApparatusUnlocked(*getSeat(),kind) && getApparatusStandTile(kind)!=nullptr;")
        has(body(ROOM, "Tile* RoomGhostRoom::askSpotForCarriedEntity("), "stand tile",
            "return getApparatusStandTile(getDeliveryTarget(*carriedEntity,*static_cast<ItemBagEntity*>(carriedEntity)->getItem()));")
        has(body(ROOM, "Tile* RoomGhostRoom::getApparatusStandTile("), "stand tile per kind", "mApparatuses[static_cast<uint32_t>(kind)].stand")
        kind = NAMES[item["target"]] if item["carried"] and 0 <= item["target"] < len(KINDS) else self.chosen_apparatus()
        return self.apparatus[kind]["stand"] if self.unlocked(kind) else None

    # Step 4: put down in front of the apparatus, the ectoplasm joins its queue
    def put_down(self, item):
        drop = body(ROOM, "void RoomGhostRoom::notifyCarryingStateChanged(")
        has(drop, "delivery", "const int32_t target=bag->getItem()->mGhostTarget;",
            "Apparatus& apparatus=mApparatuses[static_cast<uint32_t>(kind)];", "bag->takeItem();", "++apparatus.queue;")
        item["carried"] = False
        kind = NAMES[item["target"]]
        if not self.unlocked(kind):
            self.floor.append(item)
            return
        self.apparatus[kind]["queue"] += 1

    # Step 5: one upkeep of the apparatuses; returns the products of this turn
    def upkeep(self):
        work = body(ROOM, "void RoomGhostRoom::workApparatuses(")
        has(work, "work", "if(!apparatus.working && apparatus.queue>0)", "--apparatus.queue;apparatus.working=true;apparatus.workTurns+=turns;",
            "apparatus.workTurns-=1.0;", "if(apparatus.workTurns<=0.0)", "apparatus.working=false;\n                    finishEctoplasm(kind);",
            "const std::string state=!unlocked?\"Locked\":apparatus.working?\"Working\":\"Idle\";",
            "apparatus.object->setAnimationState(state,true);")
        products = []
        for kind, apparatus in self.apparatus.items():
            unlocked = self.unlocked(kind)
            if unlocked:
                if not apparatus["working"] and apparatus["queue"] > 0:
                    apparatus["queue"] -= 1
                    apparatus["working"] = True
                    apparatus["turns"] += TURNS
                if apparatus["working"]:
                    apparatus["turns"] -= 1.0
                    if apparatus["turns"] <= 0.0:
                        apparatus["working"] = False
                        product = self.finish(kind)
                        if product:
                            products.append(product)
            apparatus["state"] = "Locked" if not unlocked else "Working" if apparatus["working"] else "Idle"
        return products

    # Step 6: the product of the apparatus
    def finish(self, kind):
        finish = body(ROOM, "void RoomGhostRoom::finishEctoplasm(")
        has(finish, "products", "++apparatus.crystalEctoplasm;",
            "if(apparatus.crystalEctoplasm<ConfigManager::getSingleton().getRoomConfigDouble(\"GhostEctoplasmPerCrystal\")) return;",
            "apparatus.crystalEctoplasm=0;\n        product=ItemInstance::createSoulCrystal();",
            "product=ItemInstance::createGhostItem(kind==GhostProduct::mana?GhostItem::manaCrystal:GhostItem::researchBook);",
            "spawnItem(drop==nullptr?tile:*drop,std::move(product),getSeat());")
        apparatus = self.apparatus[kind]
        if kind == "crystal":
            apparatus["crystal"] += 1
            if apparatus["crystal"] < PER_CRYSTAL:
                return None
            apparatus["crystal"] = 0
            product = {"ghost": "none", "soul": True}
        else:
            product = {"ghost": "manaCrystal" if kind == "mana" else "researchBook", "soul": False}
        self.floor.append(product)
        return product

    # Ectoplasm held by the apparatus when the room goes (G2)
    def held(self, kind):
        has(body(ROOM, "void RoomGhostRoom::dropHeldEctoplasm("), "nothing is lost",
            "const uint32_t count=apparatus.queue+(apparatus.working?1:0)+apparatus.crystalEctoplasm;")
        apparatus = self.apparatus[kind]
        return apparatus["queue"] + (1 if apparatus["working"] else 0) + apparatus["crystal"]


# Step 7: the room that takes the product and what it gives the keeper
def use(product):
    rooms = use_rooms()
    room = rooms[product["ghost"]]
    if product["ghost"] == "manaCrystal":
        temple = read("source/rooms/RoomDungeonTemple.cpp")
        has(body(temple, "bool RoomDungeonTemple::canBreakManaCrystal("), "heart takes the mana crystal", "item->mGhostItem != GhostItem::manaCrystal")
        has(body(temple, "void RoomDungeonTemple::notifyCarryingStateChanged("), "mana",
            "getSeat()->addMana(ConfigManager::getSingleton().getRoomConfigDouble(\"GhostEctoplasmMana\"));")
        return room, "mana", scalar("config/rooms.cfg", "GhostEctoplasmMana")
    if product["ghost"] == "researchBook":
        library = read("source/rooms/RoomLibrary.cpp")
        has(body(library, "bool RoomLibrary::hasCarryEntitySpot("), "library takes the book", "item->mGhostItem == GhostItem::researchBook")
        has(body(library, "bool RoomLibrary::openResearchBook("), "research points",
            "mSkillPoints += ConfigManager::getSingleton().getRoomConfigDouble(\"GhostEctoplasmResearchPoints\");")
        return room, "research", scalar("config/rooms.cfg", "GhostEctoplasmResearchPoints")
    has(body(read("source/entities/ItemInstance.cpp"), "std::unique_ptr<ItemInstance> ItemInstance::createSoulCrystal("), "level crystal",
        "item->mSoulCrystal = true;")
    assert "mGhostItem" not in body(read("source/entities/ItemInstance.cpp"), "std::unique_ptr<ItemInstance> ItemInstance::createSoulCrystal(")
    has(body(read("source/rooms/RoomMerchant.cpp"), "bool RoomMerchant::hasCarryEntitySpot("), "merchant takes the level crystal",
        "return item != nullptr && item->mGhostItem == GhostItem::none && getFreeTable(item) != nullptr;")
    return room, "level crystal", 1.0


EXPECTED = {
    "mana": ("ManaStill", "manaCrystal", "dungeonTemple", "mana"),
    "research": ("GhostPress", "researchBook", "library", "research"),
    "crystal": ("SoulForge", "none", "merchant", "level crystal"),
}


# Follow one ectoplasm through the apparatus of the kind, then the rest of a level crystal for the forge.
def follow(kind):
    mesh, product_item, product_room, gain = EXPECTED[kind]
    assert apparatus_mesh(kind) == mesh, (kind, "apparatus look", apparatus_mesh(kind), mesh)
    level = unlock_level(kind)
    assert level == {"mana": 1, "research": 2, "crystal": 3}[kind], (kind, level)
    room = Room(level, kind)
    others = [other for other in KINDS if other != kind]
    item = room.cauldron()
    assert item["target"] == -1 and item in room.floor
    spot = room.pick_up(item)
    assert item["target"] == KINDS[kind], (kind, "stamped apparatus", item["target"])
    assert spot == "stand-of-" + kind, (kind, "carried to its own apparatus", spot)
    # The keeper changes the choice while the worker walks: the carried ectoplasm keeps its apparatus
    room.chosen = "mana" if kind != "mana" else "research"
    assert room.carry_spot(item) == "stand-of-" + kind, (kind, "carried ectoplasm keeps its apparatus")
    room.chosen = kind
    room.put_down(item)
    assert room.apparatus[kind]["queue"] == 1 and item not in room.floor, (kind, "queued")
    assert all(room.apparatus[other]["queue"] == 0 for other in others), (kind, "no other apparatus gets it")
    assert room.held(kind) == 1, (kind, "the queued ectoplasm is held")
    finished, turn, products = None, 0, []
    while turn < 100 and not products:
        turn += 1
        products = room.upkeep()
        if not products and kind == "crystal" and room.apparatus[kind]["crystal"] == 1:
            finished = turn
            break
        if not products:
            assert room.apparatus[kind]["state"] == "Working", (kind, turn, "working while it makes the product")
            assert room.held(kind) == 1, (kind, turn, "held while working")
    work_turns = math.ceil(TURNS)
    if kind == "crystal":
        # One ectoplasm is forged into the level crystal; it stays held until the crystal is complete
        assert finished == work_turns and not products, (kind, finished, products)
        assert room.held(kind) == 1 and room.apparatus[kind]["state"] == "Idle", (kind, "forged ectoplasm held")
        for _ in range(int(PER_CRYSTAL) - 1):
            extra = room.cauldron()
            assert room.pick_up(extra) == "stand-of-crystal"
            room.put_down(extra)
        for _ in range(1000):
            products = room.upkeep()
            if products:
                break
        assert room.held(kind) == 0, (kind, "the crystal used every forged ectoplasm")
    else:
        assert turn == work_turns, (kind, "product after the work time", turn, work_turns)
        assert room.held(kind) == 0 and room.apparatus[kind]["state"] == "Idle", (kind, "idle again")
    assert len(products) == 1 and products[0]["ghost"] == product_item, (kind, products)
    assert all(room.apparatus[other]["state"] == ("Idle" if room.unlocked(other) else "Locked") for other in others)
    target, kind_of_gain, amount = use(products[0])
    assert (target, kind_of_gain) == (product_room, gain) and amount > 0, (kind, target, kind_of_gain, amount)
    print(f"{kind}: ectoplasm -> {mesh} -> {product_item if product_item != 'none' else 'SoulCrystal'} -> {target}: ok")


# A locked apparatus takes no ectoplasm: the choice falls back to the mana still and nothing is queued at the locked one.
def locked():
    for kind in ("research", "crystal"):
        room = Room(unlock_level(kind) - 1, kind)
        assert room.chosen_apparatus() == "mana", kind
        assert room.apparatus[kind]["state"] is None
        item = room.cauldron()
        assert room.pick_up(item) == "stand-of-mana", kind
        room.put_down(item)
        assert room.apparatus[kind]["queue"] == 0 and room.apparatus["mana"]["queue"] == 1, kind
        room.upkeep()
        assert room.apparatus[kind]["state"] == "Locked" and room.apparatus["mana"]["state"] == "Working", kind
    print("locked apparatus takes no ectoplasm: ok")


def main():
    assert set(KINDS) == {"mana", "research", "crystal"}, KINDS
    for kind in ("mana", "research", "crystal"):
        follow(kind)
    locked()
    print("ghost apparatus flow: ok")


if __name__ == "__main__":
    main()
