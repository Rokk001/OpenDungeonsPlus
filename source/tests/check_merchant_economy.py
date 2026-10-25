"""Compile actual merchant, inventory, gift and recipe branches against controlled world services.

This check compiles C++; feature windows with a compilation prohibition must not execute it.
The probe covers trade arithmetic, potion slots, gifts, brew choice and herb reservation through actual production code.
Automatic-drinking gates and room-remodelling persistence are separate production paths outside this probe's scope.
"""
import re
from item_probe_support import catalogue_fixture, creature_fixture, compile_and_run, function, source


def main():
    """Build a probe containing the real transactions, capacity, gift, cloning and brewing choice code."""
    merchant = source("source/rooms/RoomMerchant.cpp")
    header = source("source/rooms/RoomMerchant.h")
    lab = source("source/rooms/RoomAlchemyLab.cpp")
    handler = function(merchant, "bool RoomMerchant::handleRequest(")
    owner_requests = re.findall(r"if\(type == ClientNotificationType::(\w+)\)", handler)
    assert owner_requests == ["askMerchantWindow", "askMerchantSettings", "askMerchantBuy"], owner_requests
    assert "buyFromCreature(" not in handler, "keeper requests must never route into creature sales"
    fixture = r'''
#include "game/SkillType.h"
enum class ResearchEffect {Capacity};
//! \brief Supplies researched table factors; the production floor and capacity checks remain unchanged.
struct SkillManager {
    //! \brief Applies a controlled fixture factor to the configured base table capacity.
    static double getResearchValue(const Seat* seat,SkillType,double base,ResearchEffect) { return base*seat->researchFactor; }
};
//! \brief Supplies the optional figure services referenced by the real room split callback.
struct MerchantEntity {
    //! \brief Supplies unused figure detachment in this goods-only fixture.
    void removeFromGameMap() {}
    //! \brief Supplies unused figure ownership in this goods-only fixture.
    void setSeat(Seat*) {}
    //! \brief Supplies unused figure reattachment in this goods-only fixture.
    void addToGameMap() {}
    //! \brief Supplies unused figure rendering in this goods-only fixture.
    void createMesh() {}
};
@GOODS@
@MERCHANT_TILE@
//! \brief Supplies a real owning bag to the actual gift-delivery and keeper-purchase methods.
struct ItemBagEntity {
    std::unique_ptr<ItemInstance> mItem; GameMap* map; Seat* seat=nullptr; Tile tile; bool removed=false,deleted=false;
    //! \brief Owns the supplied instance exactly once.
    ItemBagEntity(GameMap* world,std::unique_ptr<ItemInstance> item):mItem(std::move(item)),map(world){}
    //! \brief Exposes the held instance without transferring ownership.
    const ItemInstance* getItem() const { return mItem.get(); }
    //! \brief Transfers ownership to the actual gift-delivery method.
    std::unique_ptr<ItemInstance> takeItem() { return std::move(mItem); }
    //! \brief Accepts a rejected full-inventory gift without dropping its ownership.
    void restoreItem(std::unique_ptr<ItemInstance> item) { mItem=std::move(item); }
    //! \brief Returns the fixture keeper.
    Seat* getSeat() const { return seat; }
    //! \brief Sets the fixture keeper for a purchased gift bag.
    void setSeat(Seat* owner) { seat=owner; }
    //! \brief Returns the isolated world for the production pickup guard.
    GameMap* getGameMap() const { return map; }
    //! \brief Exposes a reachable floor to the production pickup guard.
    Tile* getPositionTile() { return &tile; }
    //! \brief Supplies the actual on-map state to the production pickup guard.
    bool getIsOnMap() const { return !removed; }
    //! \brief Uses the unchanged production sealed-goods pickup rule.
    bool tryPickup(Seat* owner);
    //! \brief Records successful gift removal without a world renderer.
    void removeFromGameMap() { removed=true; }
    //! \brief Records deferred successful gift deletion without deleting a stack fixture.
    void deleteYourself() { deleted=true; }
    //! \brief Supplies unused keeper-purchase placement services.
    void addToGameMap() {}
    //! \brief Supplies unused keeper-purchase rendering services.
    void createMesh() {}
    //! \brief Supplies unused keeper-purchase placement services.
    void setPosition(int) {}
};
//! \brief Supplies a keeper's hand while leaving the actual purchase and gift flags unchanged.
struct Player {
    Seat* seat; std::vector<ItemBagEntity*> hand;
    //! \brief Creates an owner-role fixture.
    explicit Player(Seat* owner):seat(owner){}
    //! \brief Returns the requesting owner.
    Seat* getSeat() const { return seat; }
    //! \brief Receives the exact bag created by the production keeper purchase.
    void pickUpEntity(ItemBagEntity* bag) { hand.push_back(bag); }
};
//! \brief Holds fixture table membership; tested goods and transaction methods are production code.
struct RoomMerchant:Room {
    std::vector<Tile*> mCoveredTiles; std::map<Tile*,TileData*> mTileData; bool mGoodsChanged=false;
    //! \brief Creates the standard room type for a known owner.
    RoomMerchant(GameMap* map,Seat* seat):Room(map,seat,RoomType::merchant){}
    //! \brief Uses the actual researched capacity and table scan.
    Tile* getFreeTable() const;
    //! \brief Uses actual sealed-stock ownership transfer.
    bool addGoods(std::unique_ptr<ItemInstance>& item,Tile* table);
    //! \brief Uses actual stable stock identity lookup.
    const MerchantGood* findGood(uint32_t index,Tile*& table) const;
    //! \brief Uses actual purchase removal and goods-flag clearing.
    std::unique_ptr<ItemInstance> takeGoods(uint32_t index);
    //! \brief Uses actual equipment/potion desirability.
    static bool wantsItem(const Creature& creature,const ItemInstance& item);
    //! \brief Supplies a preassigned reservation, leaving allocation policy outside the arithmetic fixture.
    void reserveGoods() {}
    //! \brief Supplies the unused social-log service after a completed production trade.
    void recordDeal(const std::string&,const ItemInstance&,double,bool) {}
    //! \brief Supplies the unused post service after a completed production gift or trade.
    static void announceDeal(Creature&,const ItemInstance&,uint8_t) {}
    //! \brief Runs actual creature-sale arithmetic and ownership checks.
    bool buyFromCreature(Creature& creature,size_t slot);
    //! \brief Runs actual creature-purchase arithmetic and ownership checks.
    bool sellToCreature(Creature& creature,uint32_t index);
    //! \brief Runs actual keeper purchase without margin.
    bool sellToKeeper(Player& player,uint32_t index);
    //! \brief Runs the actual old-room callback after the engine clones a transferred tile.
    void splitRoom(Room& receiver,const std::vector<Tile*>& tiles);
    //! \brief Supplies fixture room discovery to the production takeover callback.
    static RoomMerchant* getForSeat(GameMap& map,const Seat* seat) {
        for(Room* room:map.rooms) if(room->getType()==RoomType::merchant&&room->getSeat()==seat) return static_cast<RoomMerchant*>(room); return nullptr;
    }
    //! \brief Supplies controlled merchant stocks to the production recipe selection.
    static uint32_t countPotion(GameMap& map,const Seat*,const std::string& id) { return map.merchantPotions[id]; }
    //! \brief Supplies controlled recent sales to the production recipe selection.
    static uint32_t recentPotionSales(GameMap& map,const Seat*,const std::string& id) { return map.potionSales[id]; }
};
//! \brief Retains the production reservation fields for an in-progress batch.
struct AlchemyLabTileData {std::string mPotion; bool mReserved=false; double mDone=0;};
//! \brief Supplies stock and owner state while using actual recipe eligibility and selection.
struct RoomAlchemyLab:Room {
    std::map<std::string,uint32_t> mHerbs;
    //! \brief Creates an owner's lab fixture.
    RoomAlchemyLab(GameMap* map,Seat* seat):Room(map,seat,RoomType::alchemyLab){}
    //! \brief Uses the actual all-ingredient stock predicate.
    bool canBrew(const PotionDefinition& potion) const;
    //! \brief Uses actual size, mode, stock, sales and file-order rules.
    const PotionDefinition* choosePotion() const;
    //! \brief Supplies controlled waiting stocks to the actual recipe comparator.
    static uint32_t countWaitingPotion(GameMap& map,const Seat*,const std::string& id) { return map.waitingPotions[id]; }
    //! \brief Executes the unchanged reservation branch extracted from production useRoom.
    bool reserveForCheck(Creature& creature,AlchemyLabTileData& data);
};
static const double PERCENT=100.0,EQUIP_MARGIN=0.5;
static const uint32_t LARGE_LEVEL=20,MEDIUM_LEVEL=10;
static uint32_t nextGoodsIndex=1;
'''
    fixture = fixture.replace("@GOODS@", function(header, "struct MerchantGood") + ";")
    fixture = fixture.replace("@MERCHANT_TILE@", function(header, "class RoomMerchantTileData") + ";")
    definitions = "\n".join(function(merchant, signature) for signature in (
        "double setting(", "double margin(", "double thrift(", "size_t tableCapacity(",
        "MerchantGood::MerchantGood(", "RoomMerchantTileData::RoomMerchantTileData()",
        "RoomMerchantTileData::RoomMerchantTileData(const", "TileData* RoomMerchantTileData::cloneTileData(",
        "Tile* RoomMerchant::getFreeTable(", "bool RoomMerchant::addGoods(", "const MerchantGood* RoomMerchant::findGood(",
        "std::unique_ptr<ItemInstance> RoomMerchant::takeGoods(", "bool RoomMerchant::wantsItem(",
        "bool RoomMerchant::buyFromCreature(", "bool RoomMerchant::sellToCreature(", "bool RoomMerchant::sellToKeeper(",
        "void RoomMerchant::splitRoom("))
    definitions += "\n" + function(source("source/entities/ItemBagEntity.cpp"), "bool ItemBagEntity::tryPickup(")
    definitions += "\n" + function(source("source/game/CreatureMerchantAI.cpp"), "bool deliverGift(")
    definitions += "\n" + "\n".join(function(lab, signature) for signature in (
        "bool usableSize(", "bool RoomAlchemyLab::canBrew(", "const PotionDefinition* RoomAlchemyLab::choosePotion("))
    reserve = function(function(lab, "bool RoomAlchemyLab::useRoom("), "if(!data.mReserved)")
    definitions += "\nbool RoomAlchemyLab::reserveForCheck(Creature& creature,AlchemyLabTileData& data) {\n" + reserve + "\nreturn true;\n}\n"
    drinking = function(source("source/entities/CreaturePotions.cpp"), "void Creature::decidePotion(")
    refill = drinking[drinking.index("    resizePotionSlots();"):drinking.index("    bool enemyInRange")]
    definitions += "\nvoid Creature::refillForCheck() {\n" + refill + "\n}\n"
    pickup = source("source/creatureaction/CreatureActionPickupItem.cpp")
    pickup_guard = re.search(r"if\(item->mMerchantGoods && !enemy\)\s*continue;", pickup)
    assert pickup_guard, "missing actual sealed-goods creature pickup guard"
    definitions += "\n//! \\brief Exercises the unchanged production ownership guard around one candidate.\nbool mayTakeGoods(const ItemInstance* item,bool enemy) { for(int once=0;once<1;++once) {\n" + pickup_guard[0] + "\nreturn true; } return false; }\n"
    tests = r'''
//! \brief Creates controlled quality instances using the production parser and roller.
std::unique_ptr<ItemInstance> itemFor(GameMap& map,const std::string& id,Quality quality) {
    const ItemDefinition* definition=map.getItemDefinition(id); check(definition!=nullptr,id); return ItemInstance::create(*definition,quality);
}
//! \brief Checks a successful unchanged transaction at one of the specified margin settings.
void transactions(GameMap& map,int32_t marginValue) {
    Seat seat; seat.margin=marginValue; RoomMerchant room(&map,&seat); Tile tile; tile.room=&room; RoomMerchantTileData data; data.mTable=true;
    room.mCoveredTiles.push_back(&tile); room.mTileData[&tile]=&data; map.rooms={&room};
    Creature seller(&map,&seat); seller.mLevel=30;
    seller.mEquipment[2]=itemFor(map,"BLK_A_Head",Quality::common); seller.mEquipment[2]->mBonuses={{"Damage%",100}};
    seller.mInventory[0]=itemFor(map,"BLK_B_Head",Quality::common); const double base=seller.mInventory[0]->getPrice(&map);
    const double oldGold=seller.gold; check(room.buyFromCreature(seller,0),"actual creature sale succeeds");
    check(std::abs(seller.gold-oldGold-base*.5*(1-marginValue/100.0))<1e-8,"sale payout arithmetic");
    check(std::abs(seat.merchantGold-base*.5*marginValue/100.0)<1e-8,"sale keeper margin arithmetic");
    check(seller.mood==(10-marginValue)*15,"sale mood points");
    check(seller.mInventory[0].get()==nullptr&&data.mGoods.size()==1&&data.mGoods[0].mItem.mMerchantGoods,"sale transfers sealed stock");
    Creature buyer(&map,&seat); buyer.mLevel=30; data.mGoods[0].mReservedBy=buyer.name;
    const double before=buyer.gold,keeperBefore=seat.merchantGold; const uint32_t index=data.mGoods[0].mIndex;
    check(room.sellToCreature(buyer,index),"actual creature purchase succeeds");
    check(std::abs(before-buyer.gold-base*(1+marginValue/100.0))<1e-8,"purchase price arithmetic");
    check(std::abs(seat.merchantGold-keeperBefore-base*marginValue/100.0)<1e-8,"purchase keeper margin arithmetic");
    check(buyer.mood==(10-marginValue)*15,"purchase mood points");
    check(data.mGoods.empty(),"purchase removes one stock entry");
    std::unique_ptr<ItemInstance> keeperItem=itemFor(map,"BLK_A_Head",Quality::common); check(room.addGoods(keeperItem,&tile),"keeper stock fixture");
    Player keeper(&seat); const double treasuryBefore=seat.treasury; check(room.sellToKeeper(keeper,data.mGoods.back().mIndex),"keeper purchase");
    check(seat.treasury==treasuryBefore-100,"keeper pays base price without margin");
    check(keeper.hand.size()==1&&keeper.hand[0]->mItem->mGifted&&!keeper.hand[0]->mItem->mMerchantGoods,"keeper gets unsealed gifted hand bag");
    check(mayTakeGoods(seller.mEquipment[2].get(),false),"ordinary own non-goods control");
}
//! \brief Runs all required economy, ownership, combat, gifted-potion and recipe cases.
int main(int argc,char** argv) {
    check(argc==2,"repository argument"); GameMap map; loadCatalogue(argv[1],map);
    for(int marginValue=0;marginValue<=50;++marginValue) transactions(map,marginValue);
    Seat owner,enemy; RoomMerchant room(&map,&owner); map.rooms={&room}; Tile one,two; one.room=&room; two.room=&room;
    RoomMerchantTileData first,second; first.mTable=true; second.mTable=true; room.mCoveredTiles={&one,&two}; room.mTileData={{&one,&first},{&two,&second}};
    for(double factor:{1.0,1.25,1.5}) { owner.researchFactor=factor; first.mGoods.clear(); second.mGoods.clear(); const size_t capacity=static_cast<size_t>(std::floor(3*factor));
        for(size_t count=0;count<capacity;++count) { std::unique_ptr<ItemInstance> item=itemFor(map,"BLK_A_Head",Quality::common); check(room.addGoods(item,&one),"fill real table capacity"); }
        check(room.getFreeTable()==&two,"capacity is per table");
        for(size_t count=0;count<capacity;++count) { std::unique_ptr<ItemInstance> item=itemFor(map,"BLK_B_Head",Quality::common); check(room.addGoods(item,&two),"fill second table"); }
        check(room.getFreeTable()==nullptr,"all tables full"); std::unique_ptr<ItemInstance> overflow=itemFor(map,"BLK_A_Head",Quality::common);
        check(!room.addGoods(overflow,&one)&&overflow.get()!=nullptr,"full table preserves rejected ownership");
    }
    ItemBagEntity sealed(&map,itemFor(map,"BLK_A_Head",Quality::common)); sealed.seat=&owner; sealed.mItem->mMerchantGoods=true;
    check(!sealed.tryPickup(&owner)&&!mayTakeGoods(sealed.getItem(),false),"flagged bags cannot be taken free by owner or own creature");
    check(mayTakeGoods(sealed.getItem(),true),"enemy-looting control retains access");
    std::unique_ptr<TileData> transferred(first.cloneTileData()); RoomMerchantTileData* taken=static_cast<RoomMerchantTileData*>(transferred.get());
    RoomMerchant captured(&map,&enemy); captured.mCoveredTiles={&one}; captured.mTileData[&one]=taken;
    const size_t transferredCount=taken->mGoods.size(); room.splitRoom(captured,{&one});
    check(transferredCount>0&&taken->mGoods.size()==transferredCount&&first.mGoods.empty(),"takeover clone keeps goods and old holder releases them");
    for(const MerchantGood& good:taken->mGoods) check(good.mItem.mMerchantGoods,"captured items stay goods, not free gifts");
    Creature creature(&map,&owner); creature.tile.room=nullptr;
    for(uint32_t level:{1u,9u,10u,19u,20u,30u}) { creature.mLevel=level; creature.resizePotionSlots(); check(creature.mPotionSlots.size()==(level<10?1:level<20?2:3),"potion slots by level"); }
    creature.mLevel=1; creature.resizePotionSlots(); check(creature.mPotionSlots.size()==3,"potion slots never shrink");
    creature.mInventory[0]=ItemInstance::createPotion("healing_small"); creature.fighting=true;
    ItemInstance* carried=creature.mInventory[0].get(); creature.refillForCheck(); check(creature.mInventory[0].get()==carried&&creature.mPotionSlots[0].get()==nullptr,"combat does not refill from inventory");
    creature.decideEquipment(); check(creature.mInventory[0].get()==carried,"combat inventory decision leaves ownership unchanged");
    creature.fighting=false; creature.refillForCheck(); check(creature.mInventory[0].get()==nullptr&&creature.mPotionSlots[0].get()==carried,"outside-combat refill control");
    for(const std::string& id:{"healing_small","mana_small","thaw","strength_small"}) {
        Creature recipient(&map,&owner); recipient.mLevel=30; recipient.hp=99; recipient.mana=49; recipient.frozen=true; recipient.fighting=true;
        ItemBagEntity gift(&map,ItemInstance::createPotion(id)); gift.mItem->mGifted=true;
        check(deliverGift(recipient,gift)&&recipient.drinks==1&&recipient.mood==300&&gift.removed,"useful gift drinks immediately and gives300 mood");
    }
    Creature recipient(&map,&owner); recipient.mLevel=30; recipient.resizePotionSlots();
    ItemBagEntity stored(&map,ItemInstance::createPotion("healing_small")); check(deliverGift(recipient,stored)&&recipient.mPotionSlots[0].get()!=nullptr&&recipient.drinks==0,"non-useful gift fills free potion slot");
    for(std::unique_ptr<ItemInstance>& slot:recipient.mPotionSlots) if(slot.get()==nullptr) slot=ItemInstance::createPotion("healing_small");
    ItemBagEntity inventoryGift(&map,ItemInstance::createPotion("mana_small")); check(deliverGift(recipient,inventoryGift)&&recipient.mInventory[0].get()!=nullptr,"gift then uses free inventory");
    for(std::unique_ptr<ItemInstance>& slot:recipient.mInventory) if(slot.get()==nullptr) slot=ItemInstance::createPotion("mana_small");
    const double moodBefore=recipient.mood; ItemBagEntity rejected(&map,ItemInstance::createPotion("mana_small")); ItemInstance* rejectedIdentity=rejected.mItem.get();
    check(!deliverGift(recipient,rejected)&&rejected.mItem.get()==rejectedIdentity&&rejected.mItem->mGifted&&!rejected.removed&&recipient.mood==moodBefore+300,"full gift remains the same bag yet grants300 mood");
    Creature brewer(&map,&owner); brewer.mLevel=30; map.creatures={&brewer}; RoomAlchemyLab laboratory(&map,&owner);
    laboratory.mHerbs={{"Bloodroot",40},{"Moonlily",40},{"Ironfern",40},{"Sunthorn",40}};
    check(laboratory.choosePotion()->getId()=="healing_large","file order and largest usable size");
    map.merchantPotions["healing_large"]=1; check(laboratory.choosePotion()->getId()=="mana_large","stock minimisation includes merchant stock");
    map.waitingPotions["mana_large"]=1; check(laboratory.choosePotion()->getId()=="lifespring","stock minimisation includes waiting bags");
    map.merchantPotions.clear(); map.waitingPotions.clear(); map.potionSales["flow_large"]=1;
    check(laboratory.choosePotion()->getId()=="flow_large","sales break equal-stock ties");
    owner.labMode=1; check(laboratory.choosePotion()->getId()=="healing_large","healing-mana mode excludes combat recipes");
    owner.labMode=2; check(laboratory.choosePotion()->getId()=="flow_large","combat mode and sales tie-break");
    map.potionSales.clear(); check(laboratory.choosePotion()->getId()=="strength_large","combat mode preserves file order");
    owner.labMode=1;
    for(uint32_t level:{1u,9u,10u,19u,20u,30u}) { brewer.mLevel=level; const std::string expected=level<10?"healing_small":level<20?"healing_medium":"healing_large"; check(laboratory.choosePotion()->getId()==expected,"largest size at level boundary"); }
    const PotionDefinition* recipe=laboratory.choosePotion(); const std::map<std::string,uint32_t> before=laboratory.mHerbs;
    AlchemyLabTileData batch; check(laboratory.reserveForCheck(brewer,batch)&&batch.mReserved&&batch.mPotion==recipe->getId(),"actual recipe reservation");
    for(const std::pair<const std::string,uint32_t>& herb:before) { std::map<std::string,uint32_t>::const_iterator used=recipe->getHerbs().find(herb.first); const uint32_t quantity=used==recipe->getHerbs().end()?0:used->second; check(laboratory.mHerbs[herb.first]==herb.second-quantity,"consumes exact configured herbs once"); }
    const std::map<std::string,uint32_t> reserved=laboratory.mHerbs; batch.mDone=4.5; check(laboratory.reserveForCheck(brewer,batch)&&laboratory.mHerbs==reserved&&batch.mDone==4.5,"paused reserved batch does not consume twice or reset progress");
    laboratory.mHerbs.clear(); check(laboratory.choosePotion()==nullptr,"no ingredients means no brew");
    std::cout<<"merchant production rules passed; unresolved outside-combat drinking and room-remodelling policies remain outside this probe\n";
}
'''
    compile_and_run("merchant-economy", catalogue_fixture() + creature_fixture() + fixture + definitions + tests)


if __name__ == "__main__":
    main()
