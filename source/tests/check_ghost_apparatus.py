"""Check the ghost room apparatus rules without compiling: item flow and unlock levels, work time, treasury rule,
hero chance and weights, item bag chance and saving (GHOST-APPARATUS-PLAN, decisions G1 to G9; decision 813: waiting
ectoplasm lies as real items in front of the busy apparatus)."""
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
    # Decision 813 (G4 queue): an idle apparatus takes the delivered ectoplasm in at once; at a busy one it stays lying
    # in front of it as a real item, owned by the keeper and marked for that apparatus, never a saved waiting count
    delivery = body(room, "void RoomGhostRoom::notifyCarryingStateChanged(")
    has(delivery, "idle apparatus takes it in, busy one leaves it lying", "if(!apparatus.working)",
        "takeInEctoplasm(apparatus,*bag,ConfigManager::getSingleton().getRoomConfigDouble(\"GhostApparatusTurns\"));\n        return;",
        "bag->getItem()->mGhostTarget=static_cast<int32_t>(kind);\n    bag->setSeat(getSeat());")
    assert "queue" not in delivery and "takeItem" not in delivery and "deleteYourself" not in delivery, "a busy apparatus keeps no count"
    has(body(room, "void RoomGhostRoom::takeInEctoplasm("), "taking one item in",
        "bag.takeItem();", "bag.removeFromGameMap();bag.deleteYourself();", "apparatus.working=true;apparatus.workTurns+=turns;")
    waiting = body(room, "bool RoomGhostRoom::isWaitingEctoplasm(")
    has(waiting, "waiting item: own ectoplasm on the stand of the unlocked apparatus it was delivered to",
        "item->mGhostItem!=GhostItem::ectoplasm", "bag.getSeat()!=getSeat()",
        "item->mGhostTarget<0 || item->mGhostTarget>=static_cast<int32_t>(APPARATUS_COUNT)) return false;",
        "apparatus.tile!=nullptr && apparatus.stand!=nullptr && bag.getPositionTile()==apparatus.stand &&",
        "isApparatusUnlocked(*getSeat(),kind);")
    has(body(room, "ItemBagEntity* RoomGhostRoom::findWaitingEctoplasm("), "next waiting item in put down order",
        "Tile* stand=getApparatusStandTile(kind);", "for(GameEntity* entity : stand->getEntitiesInTile())",
        "entity->isCarryLocked()) continue;",
        "if(isWaitingEctoplasm(*bag) && bag->getItem()->mGhostTarget==static_cast<int32_t>(kind)) return bag;")
    has(body(read("source/entities/ItemBagEntity.cpp"), "EntityCarryType ItemBagEntity::getEntityCarryType("),
        "workers leave waiting ectoplasm lying",
        "if(inGhostRoom && mItem->mGhostItem == GhostItem::ectoplasm && static_cast<RoomGhostRoom*>(storage)->isWaitingEctoplasm(*this))\n        return EntityCarryType::notCarryable;")
    assert "apparatus.queue" not in room and "uint32_t queue" not in read("source/rooms/RoomGhostRoom.h"), "no waiting count left"
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
    # Waiting ectoplasm already lies on the floor as items and stays there as normal items once the room is sold,
    # destroyed or taken over (isWaitingEctoplasm then fails on the room or the keeper); pending, running and forged
    # ectoplasm fall as items
    has(body(room, "void RoomGhostRoom::dropHeldEctoplasm("), "pending, running and forged ectoplasm fall",
        "apparatus.pendingEctoplasm+(apparatus.working?1:0)+apparatus.crystalEctoplasm", "GhostItem::ectoplasm",
        "apparatus.pendingEctoplasm=0;apparatus.working=false;apparatus.workTurns=0.0;apparatus.crystalEctoplasm=0;")
    has(body(room, "void RoomGhostRoom::absorbRoom("), "joined rooms keep the ectoplasm",
        "mine.pendingEctoplasm+=theirs.pendingEctoplasm+(theirs.working?1:0);", "mine.crystalEctoplasm+=theirs.crystalEctoplasm;")
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
    has(work, "work time", "getRoomConfigDouble(\"GhostApparatusTurns\")",
        "if(!apparatus.working)\n            {\n                ItemBagEntity* waiting=findWaitingEctoplasm(kind);\n                if(waiting!=nullptr) takeInEctoplasm(apparatus,*waiting,turns);",
        "apparatus.workTurns-=1.0;", "if(apparatus.workTurns<=0.0)", "finishEctoplasm(kind);", "const bool unlocked=isApparatusUnlocked(*getSeat(),kind);",
        "\"Locked\"", "\"Working\"")
    has(room, "upkeep works every room", "    workApparatuses();")
    turns = scalar("config/rooms.cfg", "GhostApparatusTurns")
    assert turns == 5.5
    # The production rule, turn by turn: 40 ectoplasm delivered at once. The first goes in at once (the apparatus is
    # idle), the other 39 lie in front of it as items and are taken in one after the other; each takes exactly 5.5 turns
    # on average
    lying, working, remaining, finished, finish_turns = [], False, 0.0, 0, []
    for item in range(40):
        if not working:
            working, remaining = True, remaining + turns
        else:
            lying.append(item)
    assert len(lying) == 39
    for turn in range(1, 1000):
        before = len(lying)
        if not working and lying:
            lying.pop(0)
            working, remaining = True, remaining + turns
        if working:
            remaining -= 1.0
            if remaining <= 0.0:
                working, finished = False, finished + 1
                finish_turns.append(turn)
        assert before - len(lying) <= 1, (turn, "one item taken in at a time")
        if turn <= 6:
            assert len(lying) == 39, (turn, "the items stay lying while the apparatus is busy")
    assert finished == 40 and not lying
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
        "apparatus.pendingEctoplasm << ' ' << apparatus.working << ' ' << apparatus.workTurns << ' ' << apparatus.crystalEctoplasm")
    imported = body(room, "bool RoomGhostRoom::importFromStream(")
    has(imported, "apparatus record and old saves", "if(!(is >> marker) || marker!=\"GhostApparatus\")", "is.clear();is.seekg(position);",
        "is >> apparatus.pendingEctoplasm >> apparatus.working >> apparatus.workTurns >> apparatus.crystalEctoplasm")
    # Decision 813: the waiting count of an old save is read as pending ectoplasm and laid out as items in front of its
    # apparatus by the first upkeep, before the apparatus works; nothing is lost
    lay = body(room, "void RoomGhostRoom::layOutPendingEctoplasm(")
    has(lay, "old save count becomes floor items in front of the apparatus",
        "Tile* place=apparatus.stand!=nullptr?apparatus.stand:mCoveredTiles.empty()?nullptr:mCoveredTiles.front();",
        "for(uint32_t count=0;count<apparatus.pendingEctoplasm;++count)",
        "ItemInstance::createGhostItem(GhostItem::ectoplasm);", "item->mGhostTarget=static_cast<int32_t>(index);",
        "bag->setSeat(getSeat());", "bag->addToGameMap();bag->createMesh();", "apparatus.pendingEctoplasm=0;")
    spread = re.search(r"const float spread\[9\]\[2\]=\{(.*?)\};", lay, re.S).group(1)
    offsets = [tuple(float(value.strip().rstrip("f")) for value in pair.split(",")) for pair in re.findall(r"\{([^{}]*)\}", spread)]
    assert len(offsets) == 9 and len(set(offsets)) == 9, offsets
    assert all(abs(dx) < 0.5 and abs(dy) < 0.5 for dx, dy in offsets), "every laid out item stays on the stand tile"
    has(body(room, "void RoomGhostRoom::doUpkeep("), "laid out before the work", "    layOutPendingEctoplasm();\n    workApparatuses();")
    # Plan constraint 4: only a saved game without the apparatus record (an old save) marks its choice for conversion;
    # a level file (no record, saved turn 0) and a new save (record present) do not
    old_branch = imported[imported.index("marker!=\"GhostApparatus\")"):imported.index("return true;")]
    has(old_branch, "only an old saved game is marked", "mOldSaveChoice=getGameMap()->getSavedTurnNumber()>0;")
    assert imported.count("mOldSaveChoice") == 1, "a new save with the record never marks the choice"
    assert "bool mOldSaveChoice = false;" in read("source/rooms/RoomGhostRoom.h"), "rooms start unmarked"
    assert room.count("mOldSaveChoice") == 3, "the mark is set on load and read and cleared only in the upkeep"
    assert "Room::importRoomFromStream(*room,stream);" in room
    instance = read("source/entities/ItemInstance.cpp")
    has(body(instance, "void ItemInstance::exportToStream("), "item record", "<< \" GhostItem \" << static_cast<uint32_t>(mGhostItem) << ' ' << mGhostTarget;")
    has(body(instance, "bool ItemInstance::importFromStream("), "item record read", "else if(marker == \"GhostItem\")",
        "kind > static_cast<uint32_t>(GhostItem::researchBook)) return false;")
    has(body(instance, "void ItemInstance::exportToPacket("), "item packet", "<< std::string(\"GhostItem\") << static_cast<uint32_t>(mGhostItem) << mGhostTarget;")
    has(body(instance, "bool ItemInstance::importFromPacket("), "item packet read", "if(ghost >> marker && marker == \"GhostItem\")")
    seat = read("source/game/Seat.cpp")
    assert "os << \"[GhostRoom] \" << mEctoplasmLevels << ' ' << static_cast<uint32_t>(mGhostProduct)" in seat, "chosen apparatus saved"
    # Decision 800 replaces the G2 start rule: a new game starts on the ghost press (research points); while it is locked
    # the effective choice is the mana still, and the stored choice is kept so the press takes over once unlocked
    assert "GhostProduct mGhostProduct = GhostProduct::research;" in read("source/game/SeatData.h"), "new game starts on the ghost press"
    assert "GhostProduct mGhostProduct = GhostProduct::mana;" not in read("source/game/SeatData.h"), "old mana still start rule gone"
    assert re.search(r"enum class GhostProduct : uint32_t \{ research = 0, mana = 1, crystal = 2 \};", read("source/game/SeatData.h")), "old saves map 1:1"
    upkeep = body(room, "void RoomGhostRoom::doUpkeep(")
    has(upkeep, "new games and new saves keep a locked choice, it works as the mana still",
        "// A locked choice of a new game or a new save (the ghost press of a new game) is kept: getChosenApparatus uses the",
        "if(!mCauldrons.empty()) produceEctoplasm(*mCauldrons.front().anchor);")
    # Plan constraint 4: an old save whose stored choice is locked at the room research level becomes the mana still
    migration = upkeep[upkeep.index("if(mOldSaveChoice)"):]
    migration = migration[:migration.index("\n    }") + 6]
    has(migration, "old save locked choice becomes the mana still, once for the keeper",
        "for(Room* room : rooms) static_cast<RoomGhostRoom*>(room)->mOldSaveChoice=false;",
        "if(!isApparatusUnlocked(*getSeat(),getSeat()->getGhostProduct())) getSeat()->setGhostProduct(GhostProduct::mana);")
    assert upkeep.count("setGhostProduct(") == 1 and "setGhostProduct(" in migration, \
        "the upkeep overwrites the stored choice only in the old save conversion"
    assert upkeep.index("rooms.front()!=this) return;") < upkeep.index("if(mOldSaveChoice)") < upkeep.index("produceEctoplasm"), \
        "only the keeper's first ghost room converts, before it uses the choice"
    # Replay of the stored choice after the first upkeep: unlock level 1 mana still, 2 ghost press, 3 soul forge
    unlock = {"mana": 1, "research": 2, "crystal": 3}
    def stored_after(stored, level, old_save):
        return "mana" if old_save and level < unlock[stored] else stored
    assert [stored_after("crystal", level, True) for level in (1, 2, 3)] == ["mana", "mana", "crystal"]
    assert [stored_after("research", level, True) for level in (0, 1, 2, 3)] == ["mana", "mana", "research", "research"]
    assert [stored_after("research", level, False) for level in (0, 1, 2, 3)] == ["research"] * 4, "decision 800 kept"
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
