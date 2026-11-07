"""Check the ghost room apparatus rules without compiling: item flow and unlock levels, work time, treasury rule,
hero chance and weights, item bag chance and saving (GHOST-APPARATUS-PLAN, decisions G1 to G9)."""
from pathlib import Path
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


# Read one numeric key of a config file.
def scalar(path, key):
    rows = re.findall(r"^\s*" + re.escape(key) + r"\s+([-+0-9.eE]+)\s*$", read(path), re.M)
    assert len(rows) == 1, (key, rows)
    return float(rows[0])


# Assert that every fragment occurs in the text, naming the rule it proves.
def has(text, rule, *fragments):
    for fragment in fragments:
        assert fragment in text, (rule, fragment)


def item_flow_and_unlocks():
    room = read("source/rooms/RoomGhostRoom.cpp")
    # G3: room research level 1 unlocks the mana still, 2 the ghost press, 3 the soul forge
    has(body(room, "uint32_t RoomGhostRoom::getUnlockLevel("), "unlock levels",
        "kind==GhostProduct::mana?1:kind==GhostProduct::research?2:3")
    has(body(room, "bool RoomGhostRoom::isApparatusUnlocked("), "unlock by room research",
        "seat.getSkillLevel(SkillType::roomGhostRoom)>=getUnlockLevel(kind)")
    has(body(room, "GhostProduct RoomGhostRoom::getChosenApparatus("), "locked choice is the mana still",
        "isApparatusUnlocked(seat,seat.getGhostProduct())?seat.getGhostProduct():GhostProduct::mana")
    # G1: the full ectoplasm comes out of the emptied cauldron as an item; the AI chooses before each one
    has(body(room, "void RoomGhostRoom::emptyGhost("), "emptied cauldron", "produceEctoplasm(*cauldron);")
    produce = body(room, "void RoomGhostRoom::produceEctoplasm(")
    has(produce, "ectoplasm item", "findDropTile(cauldron,0.5)", "KeeperAI::updateGhostRoomSettings(*seat);",
        "seat->setEctoplasmLevels(seat->getEctoplasmLevels()-getLevelsPerEctoplasm(*seat));",
        "ItemInstance::createGhostItem(GhostItem::ectoplasm)", "\"EctoplasmBurst\"", "Rooms/GhostRoom/PressHiss")
    assert "addMana" not in produce and "addSkillPoints" not in produce, "no product at once"
    # G1/G2: delivery to the apparatus chosen when the worker picked the ectoplasm up, without a queue limit
    spot = body(room, "bool RoomGhostRoom::hasCarryEntitySpot(")
    has(spot, "ectoplasm only for unlocked apparatus", "item->mGhostItem!=GhostItem::ectoplasm",
        "isApparatusUnlocked(*getSeat(),kind) && getApparatusStandTile(kind)!=nullptr")
    has(body(room, "GhostProduct RoomGhostRoom::getDeliveryTarget("), "carried ectoplasm keeps its apparatus",
        "carriedEntity.isCarryLocked() && item.mGhostTarget>=0", "return getChosenApparatus(*getSeat());")
    has(body(room, "void RoomGhostRoom::notifyCarryingStateChanged("), "delivery queues", "++apparatus.queue;",
        "bag->takeItem();")
    grab = read("source/creatureaction/CreatureActionGrabEntity.cpp")
    has(grab, "stamp at pick up and nearest apparatus",
        "bagItem->mGhostTarget = static_cast<int32_t>(RoomGhostRoom::getChosenApparatus(*creature.getSeat()));",
        "getApparatusStandTile(static_cast<GhostProduct>(bagItem->mGhostTarget))",
        "preferredRoom = ItemBagEntity::getUseRoomType(*bagItem);", "findBestPath(")
    # G5: the products and their ways
    finish = body(room, "void RoomGhostRoom::finishEctoplasm(")
    has(finish, "products", "kind==GhostProduct::mana?GhostItem::manaCrystal:GhostItem::researchBook",
        "getRoomConfigDouble(\"GhostEctoplasmPerCrystal\")", "ItemInstance::createSoulCrystal()", "findDropTile(tile,0.0)")
    use = body(read("source/entities/ItemBagEntity.cpp"), "RoomType ItemBagEntity::getUseRoomType(")
    has(use, "use rooms", "case GhostItem::ectoplasm: return RoomType::ghostRoom;",
        "case GhostItem::manaCrystal: return RoomType::dungeonTemple;", "case GhostItem::researchBook: return RoomType::library;",
        "default: return RoomType::merchant;")
    library = read("source/rooms/RoomLibrary.cpp")
    has(body(library, "bool RoomLibrary::useRoom("), "a researcher at work opens a book", "openResearchBook();")
    has(body(library, "bool RoomLibrary::openResearchBook("), "book points only when opened",
        "getRoomConfigDouble(\"GhostEctoplasmResearchPoints\")", "mSkillPoints +=")
    assert "addSkillPoints" not in body(library, "void RoomLibrary::notifyCarryingStateChanged("), "no points on delivery"
    temple = read("source/rooms/RoomDungeonTemple.cpp")
    has(body(temple, "void RoomDungeonTemple::notifyCarryingStateChanged("), "the worker breaks the mana crystal",
        "getSeat()->addMana(ConfigManager::getSingleton().getRoomConfigDouble(\"GhostEctoplasmMana\"));", "\"SoulCrystalBreak\"")
    # G7: every ghost good is an item bag, worker carry entry 5 "Items"
    jobs = read("source/game/WorkerJobs.cpp")
    assert re.search(r"case GameEntityType::itemBagEntity:\s*case GameEntityType::herbBundleEntity: return WorkerCarryEntry::items;", jobs)
    assert re.search(r"enum class WorkerCarryEntry : uint32_t \{ ownKnockedOut, enemyKnockedOut, corpse, gold, items,", read("source/game/WorkerJobs.h"))
    # G2: nothing is lost when the room goes
    has(room, "room loss", "void RoomGhostRoom::changeOwner(Seat* seat)\n{ interruptHunters(); dropHeldEctoplasm(nullptr);",
        "if(removed && mCoveredTiles.empty()) dropHeldEctoplasm(tile);")
    has(body(room, "void RoomGhostRoom::dropHeldEctoplasm("), "waiting, running and forged ectoplasm fall",
        "apparatus.queue+(apparatus.working?1:0)+apparatus.crystalEctoplasm", "GhostItem::ectoplasm")
    has(body(room, "void RoomGhostRoom::absorbRoom("), "joined rooms keep the ectoplasm",
        "mine.queue+=theirs.queue+(theirs.working?1:0);", "mine.crystalEctoplasm+=theirs.crystalEctoplasm;")
    # G10 (decision 793): one of each apparatus on a floor stand inside the room, outside door openings, every other tile reachable
    layout = body(room, "void RoomGhostRoom::layoutApparatuses(")
    has(layout, "placement", "for(int pass=0;pass<2 && chosen.size()<APPARATUS_COUNT;++pass)", "if(blocked.count(tile)!=0 || inOpening(tile)) continue;", "if(!keepsReachable(taken)) continue;",
        "GhostProduct::mana,GhostProduct::research,GhostProduct::crystal")
    # Only workers handle the goods: creatures never pick ectoplasm, mana crystals or books up
    has(read("source/creatureaction/CreatureActionPickupItem.cpp"), "worker goods", "if(item->mGhostItem != GhostItem::none)")
    print("item flow and unlock levels: ok")


def work_time():
    room = read("source/rooms/RoomGhostRoom.cpp")
    work = body(room, "void RoomGhostRoom::workApparatuses(")
    has(work, "work time", "getRoomConfigDouble(\"GhostApparatusTurns\")", "--apparatus.queue;apparatus.working=true;apparatus.workTurns+=turns;",
        "apparatus.workTurns-=1.0;", "if(apparatus.workTurns<=0.0)", "finishEctoplasm(kind);", "const bool unlocked=isApparatusUnlocked(*getSeat(),kind);",
        "\"Locked\"", "\"Working\"")
    has(room, "upkeep works every room", "    workApparatuses();")
    turns = scalar("config/rooms.cfg", "GhostApparatusTurns")
    assert turns == 5.5
    # The production rule, turn by turn: a queue of ectoplasm takes exactly 5.5 turns each on average
    queue, working, remaining, finished, finish_turns = 40, False, 0.0, 0, []
    for turn in range(1, 1000):
        if not working and queue > 0:
            queue, working, remaining = queue - 1, True, remaining + turns
        if working:
            remaining -= 1.0
            if remaining <= 0.0:
                working, finished = False, finished + 1
                finish_turns.append(turn)
    assert finished == 40 and queue == 0
    assert finish_turns[0] == 6 and finish_turns[-1] == 220, finish_turns[-1]
    assert abs(finish_turns[-1] / 40 - turns) < 1e-12
    print("work time: ok")


def treasury_rule():
    bag = read("source/entities/ItemBagEntity.cpp")
    carry = body(bag, "EntityCarryType ItemBagEntity::getEntityCarryType(")
    has(carry, "stored goods are fetched as soon as they can be used",
        "storage->getType() == RoomType::treasury)) && !isWantedByUseRoom(*carrier)",
        "mItem->mGhostItem == GhostItem::researchBook && storage != nullptr && storage->getType() == RoomType::library")
    has(body(bag, "bool ItemBagEntity::isWantedByUseRoom("), "use room test", "getRoomsByTypeAndSeat(getUseRoomType(*mItem), carrier.getSeat())",
        "room->hasCarryEntitySpot(this)", "pathExists(")
    treasury = body(read("source/rooms/RoomTreasury.cpp"), "bool RoomTreasury::hasCarryEntitySpot(")
    has(treasury, "treasury stores products, not ectoplasm", "item->mGhostItem == GhostItem::ectoplasm) return false;",
        "return getItemDeliveryTile(carriedEntity) != nullptr;")
    temple = read("source/rooms/RoomDungeonTemple.cpp")
    has(body(temple, "bool RoomDungeonTemple::canBreakManaCrystal("), "a mana crystal needs free mana for its whole value",
        "item->mGhostItem != GhostItem::manaCrystal",
        "config.getMaxManaPerSeat() - getSeat()->getMana() >= config.getRoomConfigDouble(\"GhostEctoplasmMana\")")
    has(body(temple, "bool RoomDungeonTemple::hasCarryEntitySpot("), "heart takes mana crystals",
        "case GameEntityType::itemBagEntity:\n            return canBreakManaCrystal(*carriedEntity);")
    has(body(read("source/rooms/RoomLibrary.cpp"), "bool RoomLibrary::hasCarryEntitySpot("), "a library takes every book",
        "item->mGhostItem == GhostItem::researchBook")
    has(body(read("source/rooms/RoomMerchant.cpp"), "bool RoomMerchant::hasCarryEntitySpot("), "the merchant takes the level crystal only",
        "item->mGhostItem == GhostItem::none")
    print("treasury rule: ok")


def hero_chance_and_weights():
    drops = read("source/game/ItemDrops.cpp")
    outfit = body(drops, "void ItemDrops::outfit(")
    has(outfit, "hero roll", "if(kind == \"hero\" && Random::Double(0.0, 1.0) < heroGhostProductChance(crystalChance))",
        "creature.setInventorySlot(slot, heroGhostProduct(Random::Double(0.0, 1.0)));\n                break;")
    assert "createSoulCrystal" not in outfit, "a hero carries one product, never an extra crystal"
    has(body(drops, "double ItemDrops::heroGhostProductChance("), "chance",
        "std::min(1.0, crystalChance * ConfigManager::getSingleton().getRoomConfigDouble(\"GhostHeroProductFactor\"))")
    has(body(drops, "std::unique_ptr<ItemInstance> ItemDrops::heroGhostProduct("), "weights",
        "\"GhostHeroProductWeightMana\"", "\"GhostHeroProductWeightBook\"", "\"GhostHeroProductWeightCrystal\"",
        "const double point = draw * (mana + book + crystal);", "if(point < mana) return ItemInstance::createGhostItem(GhostItem::manaCrystal);",
        "if(point < mana + book) return ItemInstance::createGhostItem(GhostItem::researchBook);", "return ItemInstance::createSoulCrystal();")
    weights = [scalar("config/rooms.cfg", key) for key in
        ("GhostHeroProductWeightMana", "GhostHeroProductWeightBook", "GhostHeroProductWeightCrystal")]
    costs = [1.0, 1.0, scalar("config/rooms.cfg", "GhostEctoplasmPerCrystal")]
    # Each weight is in inverse proportion to the ectoplasm cost
    assert all(abs(weight * cost - weights[0] * costs[0]) < 1e-12 for weight, cost in zip(weights, costs)), weights
    shares = [weight / sum(weights) for weight in weights]
    assert [round(share * 13, 12) for share in shares] == [6, 6, 1], shares
    average = sum(share * cost for share, cost in zip(shares, costs))
    factor = scalar("config/rooms.cfg", "GhostHeroProductFactor")
    assert abs(factor - costs[2] / average) < 1e-12 and abs(factor - 13 / 3) < 1e-12, factor
    print("hero chance and weights: ok")


def box_chance():
    bag = body(read("source/entities/ItemBagEntity.cpp"), "bool ItemBagEntity::importFromStream(")
    has(bag, "random bags", "const bool randomBag = id == \"RandomEpic\" || id == \"RandomRare\" || id == \"RandomCommon\";",
        "if(randomBag && !getGameMap()->isInEditorMode() &&",
        "Random::Double(0.0, 1.0) < ConfigManager::getSingleton().getRoomConfigDouble(\"GhostProductBoxChance\"))",
        "mItem = ItemDrops::randomGhostProduct(Random::Double(0.0, 1.0));")
    has(body(read("source/game/ItemDrops.cpp"), "std::unique_ptr<ItemInstance> ItemDrops::randomGhostProduct("), "equal picks",
        "if(draw < 1.0 / 3.0) return ItemInstance::createGhostItem(GhostItem::manaCrystal);",
        "if(draw < 2.0 / 3.0) return ItemInstance::createGhostItem(GhostItem::researchBook);", "return ItemInstance::createSoulCrystal();")
    assert "GhostProductBoxChance" not in read("source/giftboxes/GiftBoxItem.cpp"), "gift boxes keep their item"
    assert scalar("config/rooms.cfg", "GhostProductBoxChance") == 0.05
    print("box chance: ok")


def saving():
    room = read("source/rooms/RoomGhostRoom.cpp")
    export = body(room, "void RoomGhostRoom::exportToStream(")
    has(export, "apparatus record", "Room::exportToStream(os);", "os << \"GhostApparatus\" << std::setprecision(17);",
        "apparatus.queue << ' ' << apparatus.working << ' ' << apparatus.workTurns << ' ' << apparatus.crystalEctoplasm")
    imported = body(room, "bool RoomGhostRoom::importFromStream(")
    has(imported, "apparatus record and old saves", "if(!(is >> marker) || marker!=\"GhostApparatus\")", "is.clear();is.seekg(position);",
        "is >> apparatus.queue >> apparatus.working >> apparatus.workTurns >> apparatus.crystalEctoplasm")
    assert "Room::importRoomFromStream(*room,stream);" in room
    instance = read("source/entities/ItemInstance.cpp")
    has(body(instance, "void ItemInstance::exportToStream("), "item record", "<< \" GhostItem \" << static_cast<uint32_t>(mGhostItem) << ' ' << mGhostTarget;")
    has(body(instance, "bool ItemInstance::importFromStream("), "item record read", "else if(marker == \"GhostItem\")",
        "kind > static_cast<uint32_t>(GhostItem::researchBook)) return false;")
    has(body(instance, "void ItemInstance::exportToPacket("), "item packet", "<< std::string(\"GhostItem\") << static_cast<uint32_t>(mGhostItem) << mGhostTarget;")
    has(body(instance, "bool ItemInstance::importFromPacket("), "item packet read", "if(ghost >> marker && marker == \"GhostItem\")")
    seat = read("source/game/Seat.cpp")
    assert "os << \"[GhostRoom] \" << mEctoplasmLevels << ' ' << static_cast<uint32_t>(mGhostProduct)" in seat, "chosen apparatus saved"
    assert "GhostProduct mGhostProduct = GhostProduct::mana;" in read("source/game/SeatData.h"), "new game starts with the mana still"
    assert re.search(r"enum class GhostProduct : uint32_t \{ research = 0, mana = 1, crystal = 2 \};", read("source/game/SeatData.h")), "old saves map 1:1"
    upkeep = body(room, "void RoomGhostRoom::doUpkeep(")
    has(upkeep, "old saves", "if(getChosenApparatus(*getSeat())!=getSeat()->getGhostProduct()) getSeat()->setGhostProduct(GhostProduct::mana);",
        "if(!mCauldrons.empty()) produceEctoplasm(*mCauldrons.front().anchor);")
    assert upkeep.index("rooms.front()!=this) return;") < upkeep.index("produceEctoplasm"), "only the keeper's first ghost room converts"
    print("saving: ok")


def main():
    item_flow_and_unlocks()
    work_time()
    treasury_rule()
    hero_chance_and_weights()
    box_chance()
    saving()
    print("ghost apparatus: ok")


if __name__ == "__main__":
    main()
