"""Follow one ectoplasm per apparatus through the item flow without compiling (GHOST-APPARATUS-PLAN G1 to G5).

For the mana still, the ghost press and the soul forge one ectoplasm comes out of the cauldron, is picked up, stamped with
the chosen apparatus, carried to that apparatus, taken in at once by the idle apparatus or left lying in front of the busy
one as a real item until it is taken in (decision 813), worked and turned into its product, which then goes to the room
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
        self.apparatus = {kind: {"pending": 0, "working": False, "turns": 0.0, "crystal": 0, "state": None,
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

    # Step 4: put down in front of the apparatus; the idle apparatus takes it in at once, at a busy one it stays lying on
    # the stand tile as a real item (decision 813). An interrupted carry leaves it at the interruption position.
    def put_down(self, item, at=None):
        drop = body(ROOM, "void RoomGhostRoom::notifyCarryingStateChanged(")
        has(drop, "delivery", "const int32_t target=bag->getItem()->mGhostTarget;",
            "Apparatus& apparatus=mApparatuses[static_cast<uint32_t>(kind)];",
            "if(!apparatus.working)\n    {\n        takeInEctoplasm(apparatus,*bag,ConfigManager::getSingleton().getRoomConfigDouble(\"GhostApparatusTurns\"));\n        return;\n    }",
            "bag->getItem()->mGhostTarget=static_cast<int32_t>(kind);\n    bag->setSeat(getSeat());\n}")
        guard = "if(!isApparatusUnlocked(*getSeat(),kind) || apparatus.tile==nullptr || apparatus.stand==nullptr ||\n       tile!=apparatus.stand || carrier->getSeat()!=getSeat()) return;"
        has(drop, "arrival before acceptance", guard)
        assert drop.index(guard) < drop.index("takeInEctoplasm(") < drop.index("bag->setSeat(getSeat());")
        item["carried"] = False
        kind = NAMES[item["target"]]
        item["at"] = at if at is not None else self.apparatus[kind]["stand"] if self.unlocked(kind) else "floor"
        if not self.unlocked(kind) or item["at"] != self.apparatus[kind]["stand"]:
            self.floor.append(item)
            return
        if not self.apparatus[kind]["working"]:
            self.take_in(kind)
            return
        self.floor.append(item)

    # The idle apparatus takes one ectoplasm item in and starts its work time
    def take_in(self, kind):
        has(body(ROOM, "void RoomGhostRoom::takeInEctoplasm("), "take in", "bag.takeItem();",
            "bag.removeFromGameMap();bag.deleteYourself();", "apparatus.working=true;apparatus.workTurns+=turns;")
        apparatus = self.apparatus[kind]
        apparatus["working"] = True
        apparatus["turns"] += TURNS

    # The ectoplasm items waiting in front of the apparatus, in the order they were put down
    def waiting(self, kind):
        has(body(ROOM, "bool RoomGhostRoom::isWaitingEctoplasm("), "waiting item",
            "bag.getPositionTile()==apparatus.stand", "isApparatusUnlocked(*getSeat(),kind);")
        return [item for item in self.floor if item.get("ghost") == "ectoplasm" and item.get("at") == self.apparatus[kind]["stand"]
            and item.get("target") == KINDS[kind] and self.unlocked(kind)]

    # A worker carries a lying item only if it is not waiting in front of its apparatus
    def carryable(self, item):
        has(body(read("source/entities/ItemBagEntity.cpp"), "EntityCarryType ItemBagEntity::getEntityCarryType("), "waiting stays",
            "static_cast<RoomGhostRoom*>(storage)->isWaitingEctoplasm(*this))\n        return EntityCarryType::notCarryable;")
        return not any(item in self.waiting(kind) for kind in KINDS)

    # The first upkeep after loading an old save lays its waiting count out as items in front of the apparatus
    def lay_out(self):
        has(body(ROOM, "void RoomGhostRoom::layOutPendingEctoplasm("), "old save count",
            "item->mGhostTarget=static_cast<int32_t>(index);", "apparatus.pendingEctoplasm=0;")
        for kind, apparatus in self.apparatus.items():
            for _ in range(apparatus["pending"]):
                self.floor.append({"ghost": "ectoplasm", "target": KINDS[kind], "carried": False, "at": apparatus["stand"]})
            apparatus["pending"] = 0

    # Step 5: one upkeep of the apparatuses; returns the products of this turn
    def upkeep(self):
        has(body(ROOM, "void RoomGhostRoom::doUpkeep("), "lay out first", "    layOutPendingEctoplasm();\n    workApparatuses();")
        self.lay_out()
        work = body(ROOM, "void RoomGhostRoom::workApparatuses(")
        has(work, "work", "if(!apparatus.working)\n            {\n                ItemBagEntity* waiting=findWaitingEctoplasm(kind);",
            "if(waiting!=nullptr) takeInEctoplasm(apparatus,*waiting,turns);",
            "apparatus.workTurns-=1.0;", "if(apparatus.workTurns<=0.0)", "apparatus.working=false;\n                    finishEctoplasm(kind);",
            "const std::string state=!unlocked?\"Locked\":apparatus.working?\"Working\":\"Idle\";",
            "apparatus.object->setAnimationState(state,true);")
        products = []
        for kind, apparatus in self.apparatus.items():
            unlocked = self.unlocked(kind)
            if unlocked:
                waiting = self.waiting(kind)
                if not apparatus["working"] and waiting:
                    self.floor.remove(waiting[0])
                    self.take_in(kind)
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

    # Ectoplasm held by the apparatus when the room goes (G2); waiting ectoplasm already lies on the floor as items
    def held(self, kind):
        has(body(ROOM, "void RoomGhostRoom::dropHeldEctoplasm("), "nothing is lost",
            "const uint32_t count=apparatus.pendingEctoplasm+(apparatus.working?1:0)+apparatus.crystalEctoplasm;")
        apparatus = self.apparatus[kind]
        return apparatus["pending"] + (1 if apparatus["working"] else 0) + apparatus["crystal"]

    # The room is sold, destroyed or taken over: held ectoplasm falls, waiting items stay as normal floor items
    def lose(self):
        for kind in KINDS:
            for _ in range(self.held(kind)):
                self.floor.append({"ghost": "ectoplasm", "target": -1, "carried": False, "at": "floor"})
            self.apparatus[kind].update(pending=0, working=False, turns=0.0, crystal=0)
        for item in self.floor:
            if item.get("ghost") == "ectoplasm":
                item["at"] = "floor"


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
    assert room.apparatus[kind]["working"] and item not in room.floor, (kind, "the idle apparatus takes it in at once")
    assert all(not room.apparatus[other]["working"] and not room.waiting(other) for other in others), (kind, "no other apparatus gets it")
    assert room.held(kind) == 1, (kind, "the ectoplasm in the apparatus is held")
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
        for index in range(int(PER_CRYSTAL) - 1):
            extra = room.cauldron()
            assert room.pick_up(extra) == "stand-of-crystal"
            room.put_down(extra)
            # The first goes in at once, the others lie in front of the busy forge as items
            assert len(room.waiting(kind)) == index and room.held(kind) == 2, (kind, index, "waiting as items")
        for _ in range(1000):
            products = room.upkeep()
            if products:
                break
        assert room.held(kind) == 0 and not room.waiting(kind), (kind, "the crystal used every forged ectoplasm")
    else:
        assert turn == work_turns, (kind, "product after the work time", turn, work_turns)
        assert room.held(kind) == 0 and room.apparatus[kind]["state"] == "Idle", (kind, "idle again")
    assert len(products) == 1 and products[0]["ghost"] == product_item, (kind, products)
    assert all(room.apparatus[other]["state"] == ("Idle" if room.unlocked(other) else "Locked") for other in others)
    target, kind_of_gain, amount = use(products[0])
    assert (target, kind_of_gain) == (product_room, gain) and amount > 0, (kind, target, kind_of_gain, amount)
    print(f"{kind}: ectoplasm -> {mesh} -> {product_item if product_item != 'none' else 'SoulCrystal'} -> {target}: ok")


# Decision 813: ectoplasm for a busy apparatus waits as real items lying in front of it, which workers leave lying, and is
# taken in one after the other with the work time of each; nothing is lost when the room goes.
def busy():
    turns_each = math.ceil(TURNS)
    for kind in ("mana", "research", "crystal"):
        room = Room(unlock_level(kind), kind)
        items = [room.cauldron() for _ in range(3)]
        for item in items:
            assert room.pick_up(item) == "stand-of-" + kind
            room.put_down(item)
        assert room.apparatus[kind]["working"] and room.waiting(kind) == items[1:], (kind, "two lie in front of it")
        assert all(item in room.floor and item["at"] == "stand-of-" + kind for item in items[1:]), (kind, "real floor items")
        assert not any(room.carryable(item) for item in items[1:]), (kind, "workers leave waiting items lying")
        # A new choice does not move ectoplasm that already waits
        room.chosen = "mana" if kind != "mana" else "research"
        assert room.waiting(kind) == items[1:], (kind, "waiting items keep their apparatus")
        room.chosen = kind
        taken = []
        for turn in range(1, 40):
            before = len(room.waiting(kind))
            room.upkeep()
            if len(room.waiting(kind)) < before:
                taken.append(turn)
        # Taken in one after the other, each as soon as the previous one is done: 5.5 turns each, carried fractions
        assert taken == [turns_each + 1, math.ceil(2 * TURNS) + 1], (kind, taken)
        assert not room.waiting(kind) and room.held(kind) == (3 % int(PER_CRYSTAL) if kind == "crystal" else 0), (kind, room.held(kind))
    # The room goes while items wait: the running one falls, the waiting ones stay on the floor as normal items
    room = Room(1, "mana")
    items = [room.cauldron() for _ in range(3)]
    for item in items:
        room.pick_up(item)
        room.put_down(item)
    ectoplasm_before = sum(1 for item in room.floor if item.get("ghost") == "ectoplasm") + room.held("mana")
    room.lose()
    ectoplasm_after = sum(1 for item in room.floor if item.get("ghost") == "ectoplasm")
    assert ectoplasm_before == ectoplasm_after == 3, (ectoplasm_before, ectoplasm_after)
    assert all(room.carryable(item) for item in room.floor), "after the loss they are normal items again"
    print("busy apparatus: ectoplasm waits as items in front of it: ok")


# Interrupted carries stay recoverable inside and outside the room, including at the wrong apparatus.
def interrupted():
    carry = read("source/creatureaction/CreatureActionCarryEntity.cpp")
    destructor = body(carry, "CreatureActionCarryEntity::~CreatureActionCarryEntity(")
    has(destructor, "release interrupted cargo", "mEntityToCarry->setCarryLock(mCreature, false);",
        "mEntityToCarry->notifyEntityCarryOff(pos);", "mCreature.releaseCarriedEntity();",
        "mBuildingDest->notifyCarryingStateChanged(")
    assert destructor.index("notifyEntityCarryOff(pos)") < destructor.index("notifyCarryingStateChanged(")
    walking = body(carry, "bool CreatureActionCarryEntity::handleCarryEntity(")
    failed_path = body(walking, "if(!creature.setDestination(tileDest))")
    has(failed_path, "failed path ends carry", "creature.popAction();", "return false;")
    bag = read("source/entities/ItemBagEntity.cpp")
    has(body(bag, "void ItemBagEntity::notifyEntityCarryOff("), "drop at actual interruption position",
        "setPosition(position); addEntityToPositionTile();")
    has(body(ROOM, "bool RoomGhostRoom::isWaitingEctoplasm("), "wrong stand remains recoverable",
        "const GhostProduct kind=static_cast<GhostProduct>(item->mGhostTarget);",
        "const Apparatus& apparatus=mApparatuses[static_cast<uint32_t>(kind)];",
        "bag.getPositionTile()==apparatus.stand")
    for kind in ("mana", "research", "crystal"):
        for busy_apparatus in (False, True):
            for position in ("outside-room", "room-entry", "stand-of-" + next(other for other in KINDS if other != kind)):
                room = Room(3, kind)
                if busy_apparatus:
                    first = room.cauldron()
                    room.pick_up(first)
                    room.put_down(first)
                item = room.cauldron()
                assert room.pick_up(item) == "stand-of-" + kind
                held_before = room.held(kind)
                turns_before = room.apparatus[kind]["turns"]
                room.put_down(item, at=position)
                assert item in room.floor and item["at"] == position and not item["carried"]
                assert room.held(kind) == held_before and room.apparatus[kind]["turns"] == turns_before
                assert not room.waiting(kind) and room.carryable(item), (kind, position, "recoverable after interruption")
                room.upkeep()
                assert item in room.floor and room.carryable(item), (kind, position, "upkeep cannot accept remotely")
                # Retry the interrupted delivery and reach its selected stand.
                assert room.pick_up(item) == "stand-of-" + kind
                room.put_down(item)
                if busy_apparatus:
                    assert room.waiting(kind) == [item] and not room.carryable(item)
                    for _ in range(20):
                        room.upkeep()
                    assert item not in room.floor and not room.waiting(kind)
                else:
                    assert item not in room.floor and room.apparatus[kind]["working"]
    print("interrupted carries: no remote acceptance, recoverable until stand delivery: ok")


# An old save with a waiting count: the first upkeep lays the count out as items in front of the apparatus.
def old_save():
    room = Room(1, "mana")
    room.apparatus["mana"]["pending"] = 4
    assert room.held("mana") == 4, "the count is held until it is laid out"
    room.upkeep()
    assert room.apparatus["mana"]["pending"] == 0 and room.apparatus["mana"]["working"], "laid out, one taken in at once"
    assert len(room.waiting("mana")) == 3 and room.held("mana") == 1, "three lie in front of the mana still"
    finished = 0
    for _ in range(100):
        finished += len(room.upkeep())
    assert finished == 4 and not room.waiting("mana") and room.held("mana") == 0, finished
    print("old save waiting count becomes floor items: ok")


# A locked apparatus takes no ectoplasm: the choice falls back to the mana still and nothing waits at the locked one.
def locked():
    for kind in ("research", "crystal"):
        room = Room(unlock_level(kind) - 1, kind)
        assert room.chosen_apparatus() == "mana", kind
        assert room.apparatus[kind]["state"] is None
        item = room.cauldron()
        assert room.pick_up(item) == "stand-of-mana", kind
        room.put_down(item)
        assert not room.apparatus[kind]["working"] and not room.waiting(kind) and room.apparatus["mana"]["working"], kind
        room.upkeep()
        assert room.apparatus[kind]["state"] == "Locked" and room.apparatus["mana"]["state"] == "Working", kind
    print("locked apparatus takes no ectoplasm: ok")


# Run the normal flows, busy queues, interrupted deliveries and save compatibility scenarios.
def main():
    assert set(KINDS) == {"mana", "research", "crystal"}, KINDS
    for kind in ("mana", "research", "crystal"):
        follow(kind)
    busy()
    interrupted()
    old_save()
    locked()
    print("ghost apparatus flow: ok")


if __name__ == "__main__":
    main()
