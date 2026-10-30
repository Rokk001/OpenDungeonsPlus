"""Exercise extracted production crystal rules, trades and real packet codecs.

This check compiles bounded C++ fixtures. Run only after the feature completeness gate.
"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]


# Read the current implementation independently of the caller's directory.
def read(path):
    return (ROOT / path).read_text(encoding="utf-8")


# Retain a complete production function, including its unchanged signature and body.
def function(text, signature):
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


# Read one uniquely declared numeric setting rather than copying gameplay constants.
def scalar(text, name):
    rows = re.findall(r"^\s*" + re.escape(name) + r"\s+([-+0-9.eE]+)\s*(?:#.*)?$", text, re.M)
    assert len(rows) == 1, (name, rows)
    return float(rows[0])


# Compile production bodies with real packet transport, keeping child stdin closed and bounded.
def run_probe(code):
    prefix = Path(os.environ["CMAKE_PREFIX_PATH"])
    with tempfile.TemporaryDirectory(prefix="odp-soul-crystal-") as directory:
        work = Path(directory)
        source, binary = work / "check.cpp", work / "check.exe"
        source.write_text(code, encoding="utf-8")
        subprocess.run(["cl", "/nologo", "/EHsc", "/MD", "/std:c++17", "/I" + str(ROOT / "source"),
            "/I" + str(prefix / "include"), "/I" + str(prefix / "include/OGRE"), str(source),
            str(ROOT / "source/network/ODPacket.cpp"), "/Fe:" + str(binary), "/link",
            "/LIBPATH:" + str(prefix / "lib"), "sfml-network.lib", "sfml-system.lib", "OgreMain.lib"],
            cwd=work, stdin=subprocess.DEVNULL, check=True, timeout=180)
        subprocess.run([str(binary)], cwd=work, stdin=subprocess.DEVNULL, check=True, timeout=180)


PRELUDE = r'''
#include "network/ODPacket.h"
#include "entities/ItemInstance.h"
#include "entities/PotionDefinition.h"
#include "entities/Weapon.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
#include <map>
#include <memory>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>
#include <utility>
static const uint32_t MAX_LEVEL=30,BONUS_KIND_COUNT=17;
static const double PERCENT=100.0;
#define OD_LOG_ERR(value) static_cast<void>(0)
//! \brief Fails a named assertion about the actual production result.
void check(bool value,const std::string& name){if(!value)throw std::runtime_error(name);}
//! \brief Compares exact fractional gameplay values within serialization precision.
void near(double value,double expected,const std::string& name){check(std::abs(value-expected)<1e-9,name);}
struct Creature;struct Room;struct Tile;struct RoomMerchant;
//! \brief Records the keeper's unchanged margin and actual merchant purchase income.
struct Seat {double margin=0,gold=0;
 //! \brief Supplies the keeper margin selected by a test case.
 double getMerchantMargin()const{return margin;}
 //! \brief Records keeper income without substituting the production transaction.
 void addMerchantGold(double amount){gold+=amount;}
};
//! \brief Supplies the real numeric config inputs and inert catalogue services.
struct ConfigManager {std::map<std::string,double> values;
 //! \brief Provides the isolated fixture settings.
 static ConfigManager& getSingleton(){static ConfigManager instance;return instance;}
 //! \brief Supplies the real configured crystal base price.
 double getSoulCrystalPrice()const{return values.at("SoulCrystalPrice");}
 //! \brief Supplies the actual configured use threshold.
 double getSoulCrystalBreakBelow()const{return values.at("SoulCrystalBreakBelow");}
 //! \brief Supplies the actual normal experience rate.
 double getSoulCrystalNormalXpPerSecond()const{return values.at("SoulCrystalNormalXpPerSecond");}
 //! \brief Supplies the actual hero endpoint probability.
 double getSoulCrystalHeroRareStart()const{return values.at("SoulCrystalHeroRareStart");}
 //! \brief Supplies the actual hero endpoint probability.
 double getSoulCrystalHeroRareEnd()const{return values.at("SoulCrystalHeroRareEnd");}
 //! \brief Supplies the real payday duration.
 double getTimePayDay()const{return values.at("TimePayDay");}
 //! \brief Supplies the real merchant purchase share and room amounts.
 double getRoomConfigDouble(const std::string& name)const{return values.at(name);}
 //! \brief Supplies the configured item effect setting used by the codec.
 double getItemSetting(const std::string&,const std::string& key)const{return values.at(key);}
 //! \brief Supplies the real equipment limits; every key the fixture reaches is loaded from the config.
 double getEquipmentConfigDoubleOrDefault(const std::string& name,double)const{return values.at(name);}
 //! \brief Leaves unrelated catalogue items outside the crystal-only fixture.
 const ItemDefinition* getItem(const std::string&)const{return nullptr;}
 //! \brief Leaves unrelated potions outside the crystal-only fixture.
 const PotionDefinition* getPotion(const std::string&)const{return nullptr;}
 //! \brief Leaves unrelated weapons outside the crystal-only fixture.
 const Weapon* getWeapon(const std::string&)const{return nullptr;}
};
//! \brief Supplies the real definition lookup interface used by crystal price fallbacks.
struct GameMap {
 //! \brief Leaves unrelated equipment catalogue entries outside these cases.
 const ItemDefinition* getItemDefinition(const std::string&)const{return nullptr;}
};
//! \brief Supplies deterministic draws and captures the threshold used by the real hero roll.
namespace Random {double draw=0,lastUpper=0;
 //! \brief Returns an independently selected random fraction to exercise both probability sides.
 double Double(double low,double high){lastUpper=high;return low+(high-low)*draw;}
}
//! \brief Reads hero inputs from the actual config values loaded by Python.
double dropSetting(const std::string& key){return ConfigManager::getSingleton().values.at(key);}
//! \brief Reads merchant inputs from the actual room configuration.
double setting(const std::string& key){return ConfigManager::getSingleton().getRoomConfigDouble(key);}
//! \brief Supplies a wage class and the actual shared experience table.
struct CreatureDefinition {int32_t mFeeBase=0,mFeePerLevel=0;std::vector<double> mXPTable;
 //! \brief Returns the controlled payday wage for the specified wage class.
 int32_t getFee(unsigned int level)const;
 //! \brief Returns the actual configured XP step used by the production worth-it rule.
 double getXPNeededWhenLevel(unsigned int level)const;
};
//! \brief Represents only the entity kinds touched by gifts and worker delivery.
enum class GameEntityType {creature,itemBagEntity,other};
//! \brief Stores the fixture's actual gift recipient and carried bag ownership.
struct GameEntity {Seat* seat=nullptr;GameEntityType type=GameEntityType::other;
 //! \brief Supplies the production gift recipient type gate.
 GameEntityType getObjectType()const{return type;}
 //! \brief Supplies the production same-seat gift gate.
 Seat* getSeat()const{return seat;}
};
//! \brief Provides a tile's keeper-visible occupants and room ownership.
struct Tile {Room* room=nullptr;std::vector<GameEntity*> entities;
 //! \brief Supplies the room checked by gift and delivery code.
 Room* getCoveringRoom()const{return room;}
 //! \brief Supplies the actual occupants scanned by the gift code.
 std::vector<GameEntity*> getEntitiesInTile()const{return entities;}
 //! \brief Keeps rendered sound events outside this null-position fixture.
 std::vector<Seat*> getSeatsWithVision()const{return {};}
 //! \brief Supplies packet sound coordinates without rendering.
 int32_t getX()const{return 0;}
 //! \brief Supplies packet sound coordinates without rendering.
 int32_t getY()const{return 0;}
};
//! \brief Identifies only the room kinds used by gift handling.
enum class RoomType {merchant,arena,other};
//! \brief Supplies room identity to unchanged transaction and gift methods.
struct Room {Seat* seat=nullptr;GameMap map;RoomType type=RoomType::merchant;
 //! \brief Supplies actual keeper identity to transactions.
 Seat* getSeat()const{return seat;}
 //! \brief Supplies the map for the actual item-price call.
 GameMap* getGameMap(){return &map;}
 //! \brief Supplies the production room type gate.
 RoomType getType()const{return type;}
 //! \brief Supplies the stable merchant action target.
 std::string getName()const{return "Merchant_1";}
};
//! \brief Supplies the arena-only optional guard used by ordinary gifts.
struct RoomArena:Room {
 //! \brief Keeps an active arena fight in the fixture to verify crystals ignore potion delays.
 bool hasRunningFight()const{return true;}
};
//! \brief Supplies only the combat and purchase action identities used by crystal decisions.
enum class CreatureActionType {fight,buyItem};
//! \brief Captures purchases queued by the real decision function.
struct CreatureActionBuyItem {
 //! \brief Records the target without performing unrelated movement.
 CreatureActionBuyItem(Creature&,const std::string&,uint32_t){}
};
//! \brief Supplies the existing unique-pointer creation interface to the unchanged decision body.
namespace Utils {
 //! \brief Constructs the selected production action type using explicit forwarded argument types.
 template<class T,class... Args>std::unique_ptr<T> make_unique(Args&&... args){return std::unique_ptr<T>(new T(std::forward<Args>(args)...));}
}
//! \brief Supplies creature state while leaving worth, use and decision bodies unchanged.
struct Creature:GameEntity {CreatureDefinition* mDefinition=nullptr;uint32_t mLevel=1;double mExp=0,mExperienceProgress=0,gold=0,thrift=0;
 bool fighting=false,tried=false;int changes=0,purchases=0;Tile* tile=nullptr;GameMap map;
 std::vector<std::unique_ptr<ItemInstance>> inventory;
 //! \brief Initializes a creature with four independent inventory slots.
 Creature(){type=GameEntityType::creature;inventory.resize(4);}
 //! \brief Supplies the current whole creature level.
 uint32_t getLevel()const{return mLevel;}
 //! \brief Implements only the existing level transition service, recording XP reset.
 void setLevel(uint32_t level){mLevel=level;mExp=0;}
 //! \brief Reports the server path used by the actual progress calculation.
 bool getIsOnServerMap()const{return true;}
 //! \brief Supplies the real inventory ownership container.
 const std::vector<std::unique_ptr<ItemInstance>>& getInventory()const{return inventory;}
 //! \brief Transfers an exact slot to the caller without cloning its item.
 std::unique_ptr<ItemInstance> setInventorySlot(size_t slot,std::unique_ptr<ItemInstance> value){std::unique_ptr<ItemInstance> old=std::move(inventory.at(slot));inventory[slot]=std::move(value);return old;}
 //! \brief Counts actual item-change notifications from consuming a crystal.
 void itemsChanged(){++changes;}
 //! \brief Supplies the controlled sound and gift position.
 Tile* getPositionTile()const{return tile;}
 //! \brief Supplies the map for stock and item prices.
 GameMap* getGameMap()const{return const_cast<GameMap*>(&map);}
 //! \brief Supplies the named item-effect discount.
 double getItemEffect(const std::string&)const{return thrift;}
 //! \brief Supplies exact available creature gold.
 double getGoldCarriedAmount()const{return gold;}
 //! \brief Supplies the production reservation identity.
 std::string getName()const{return "Hunter_1";}
 //! \brief Supplies the production combat gate.
 bool isActionInList(CreatureActionType)const{return fighting;}
 //! \brief Supplies the existing failed-action guard.
 bool hasActionBeenTried(CreatureActionType)const{return tried;}
 //! \brief Records a purchase selected by the production decision.
 void pushAction(std::unique_ptr<CreatureActionBuyItem>){++purchases;}
 //! \brief Leaves unrelated gift-potion effects outside crystal cases.
 bool receiveGiftedPotion(std::unique_ptr<ItemInstance>&){return false;}
 //! \brief Accepts an unrelated ordinary gift through the existing service interface.
 void acceptItem(std::unique_ptr<ItemInstance>,bool){}
 //! \brief Leaves the independent merchant mood effect outside these economic assertions.
 void addMerchantMood(double){}
 //! \brief Runs the actual production worth-it method.
 bool wantsSoulCrystal(double price)const;
 //! \brief Runs the actual production crystal consumption method.
 bool breakSoulCrystal(std::unique_ptr<ItemInstance>& item);
 //! \brief Runs the actual production fractional XP progress method.
 double getExperienceProgress()const;
};
//! \brief Stores a transferable crystal bag and records its destruction once accepted.
struct ItemBagEntity:GameEntity {std::unique_ptr<ItemInstance> item;bool removed=false,deleted=false;
 //! \brief Creates an actual movable-holder fixture of the requested item.
 ItemBagEntity(std::unique_ptr<ItemInstance> value):item(std::move(value)){type=GameEntityType::itemBagEntity;}
 //! \brief Exposes the held instance without transferring ownership.
 const ItemInstance* getItem()const{return item.get();}
 //! \brief Transfers ownership exactly once.
 std::unique_ptr<ItemInstance> takeItem(){return std::move(item);}
 //! \brief Restores ownership after a rejected gift.
 void restoreItem(std::unique_ptr<ItemInstance> value){item=std::move(value);}
 //! \brief Records removal after successful transfer.
 void removeFromGameMap(){removed=true;}
 //! \brief Records deferred entity deletion after successful transfer.
 void deleteYourself(){deleted=true;}
};
//! \brief Retains stable ordinary and crystal stock records for the actual table methods.
struct MerchantGood {uint32_t mIndex=0;ItemInstance mItem;std::string mReservedBy;};
//! \brief Keeps table availability separate from the production capacity counting algorithm.
struct RoomMerchantTileData {bool mTable=true;std::vector<MerchantGood> mGoods;};
//! \brief Gives the unchanged crystal decision access to real stable stock entries.
struct MerchantStockEntry {RoomMerchant* mRoom;Tile* mTile;const MerchantGood* mGood;};
//! \brief Supplies independent table capacity to the unchanged per-item count algorithm.
size_t tableCapacity(const Seat*){return static_cast<size_t>(ConfigManager::getSingleton().values.at("MerchantGoodsPerTable"));}
//! \brief Holds real stock containers and adopts only the extracted production methods.
struct RoomMerchant:Room {std::vector<Tile*> mCoveredTiles;std::map<Tile*,RoomMerchantTileData*> mTileData;bool mGoodsChanged=false;uint32_t nextGoodsIndex=1;
 static std::vector<MerchantStockEntry> stock;
 //! \brief Supplies existing independently reserved goods to the decision body.
 static std::vector<MerchantStockEntry> getStock(GameMap&,const Seat*){return stock;}
 //! \brief Leaves the independent presentation notification outside ownership assertions.
 static void announceDeal(Creature&,const ItemInstance&,int){}
 //! \brief Leaves the independent history presentation outside keeper-income assertions.
 void recordDeal(const std::string&,const ItemInstance&,double,bool){}
 //! \brief Runs the production first-table and ordinary-capacity selection.
 Tile* getFreeTable(const ItemInstance* item=nullptr)const;
 //! \brief Runs actual item adoption into stable table stock.
 bool addGoods(std::unique_ptr<ItemInstance>& item,Tile* table);
 //! \brief Runs actual worker-delivery availability.
 bool hasCarryEntitySpot(GameEntity* entity);
 //! \brief Runs actual worker-delivery transaction and keeper payment.
 void notifyCarryingStateChanged(Creature* carrier,GameEntity* entity);
};
std::vector<MerchantStockEntry> RoomMerchant::stock;
//! \brief Defines the real decision and gift signatures before their extracted bodies.
namespace CreatureMerchantAI {bool decideSoulCrystal(Creature&);bool offerGift(ItemBagEntity&,Tile&);}
//! \brief Supplies only the sound-notification interface used after actual consumption.
struct Player {
 //! \brief Supplies the human-recipient sound gate to the production break method.
 bool getIsHuman()const{return true;}};
//! \brief Identifies the production crystal sound notification.
enum class ServerNotificationType {playSpatialSound};
//! \brief Stores sound fields outside the gameplay assertions.
struct ServerNotification {ODPacket mPacket;
 //! \brief Creates an isolated sound packet with the production constructor shape.
 ServerNotification(ServerNotificationType,Player*){}};
//! \brief Accepts production sound notifications without launching a renderer.
struct ODServer {
 //! \brief Supplies the isolated notification sink.
 static ODServer& getSingleton(){static ODServer server;return server;}
 //! \brief Releases the emitted sound record after observing its creation.
 void queueServerNotification(ServerNotification* notification){delete notification;}
};
namespace Spell {
//! \brief Accepts the actual crystal particle hook without rendering.
void fireSpellEffect(Tile&,const std::string&,const std::string&) {}}
'''


# Assemble all complete production bodies and the exact hero-only tail, without executing them here.
def main():
    global_cfg, rooms_cfg = read("config/global.cfg"), read("config/rooms.cfg")
    keys = ["SoulCrystalPrice", "SoulCrystalBreakBelow", "SoulCrystalNormalXpPerSecond", "SoulCrystalHeroRareStart",
        "SoulCrystalHeroRareEnd", "TimePayDay", "HeroItemBase", "HeroItemPerLevel", "MaxItemEffects"]
    values = {key: scalar(global_cfg, key) for key in keys}
    values.update({key: scalar(rooms_cfg, key) for key in ("MerchantBuyShare", "MerchantGoodsPerTable", "MerchantGiftMood", "MerchantTradeChance")})
    creatures = re.sub(r"#[^\n]*", "", read("config/creatures.cfg"))
    tables = [list(map(float, block.split())) for block in re.findall(r"\[XP\](.*?)\[/XP\]", creatures, re.S) if block.strip()]
    assert tables and all(table == tables[0] for table in tables), "the crystal wage cases require the actual shared XP table"
    assert len(tables[0]) == 29
    fee_pairs = {(int(base), int(per)) for base, per in re.findall(r"FeeBase\s+(\d+)\s+FeePerLevel\s+(\d+)", creatures)}
    fee_per_level = []
    for wage in (400, 200, 100, 50):
        found = [per for base, per in fee_pairs if base == wage]
        assert len(found) == 1, (wage, found)
        fee_per_level.append(found[0])
    instance, definition = read("source/entities/ItemInstance.cpp"), read("source/entities/ItemDefinition.cpp")
    merchant, ai = read("source/rooms/RoomMerchant.cpp"), read("source/game/CreatureMerchantAI.cpp")
    equipment = read("source/entities/CreatureEquipmentAI.cpp")
    code = PRELUDE.replace("struct Seat {double margin=0,gold=0;", "struct Player;\nstruct Seat {double margin=0,gold=0;\n //! \\brief Omits viewers in this server-only transaction fixture.\n Player* getPlayer()const{return nullptr;}")
    code += "\n" + "\n".join(function(definition, signature) for signature in
        ("ODPacket& operator <<(ODPacket& packet, Quality", "ODPacket& operator >>(ODPacket& packet, Quality", "const ItemQuality& ItemDefinition::getQuality("))
    code += "\n" + function(instance, "const ItemDefinition* resolveItemDefinition(")
    code += "\n" + "\n".join(function(instance, signature) for signature in
        ("std::unique_ptr<ItemInstance> ItemInstance::createSoulCrystal(", "void ItemInstance::exportToStream(",
         "bool ItemInstance::importFromStream(", "void ItemInstance::exportToPacket(", "bool ItemInstance::importFromPacket(",
         "double ItemInstance::getPrice("))
    creature_definition = read("source/entities/CreatureDefinition.cpp")
    code += "\n" + function(creature_definition, "int32_t CreatureDefinition::getFee(")
    code += "\n" + function(creature_definition, "double CreatureDefinition::getXPNeededWhenLevel(")
    code += "\n" + function(equipment, "bool Creature::wantsSoulCrystal(")
    code += "\n" + function(equipment, "bool Creature::breakSoulCrystal(")
    code += "\n" + function(read("source/entities/Creature.cpp"), "double Creature::getExperienceProgress(")
    code += "\n" + "\n".join(function(merchant, signature) for signature in
        ("Tile* RoomMerchant::getFreeTable(", "bool RoomMerchant::addGoods(", "bool RoomMerchant::hasCarryEntitySpot(",
         "void RoomMerchant::notifyCarryingStateChanged("))
    code += "\n" + function(ai, "bool deliverGift(")
    code += "\n" + function(ai, "bool CreatureMerchantAI::decideSoulCrystal(")
    code += "\n" + function(ai, "bool CreatureMerchantAI::offerGift(")
    outfit = function(read("source/game/ItemDrops.cpp"), "void ItemDrops::outfit(")
    tail = outfit[outfit.index("    const ConfigManager& config = ConfigManager::getSingleton();"):]
    code += "\n//! \\brief Executes the unchanged final crystal roll of the real outfit method.\nvoid heroCrystal(Creature& creature,const std::string& kind){const uint32_t level=creature.getLevel();\n" + tail
    initialization = "\n".join('config.values["%s"] = %.17g;' % item for item in values.items())
    code += TESTS.replace("CONFIG_VALUES", initialization).replace("XP_VALUES", ",".join(map(repr, tables[0]))).replace("FEE_LEVEL_VALUES", ",".join(map(str, fee_per_level)))
    run_probe(code)


TESTS = r'''
//! \brief Exercises configured worth thresholds, ownership, transaction rejection and codec compatibility.
int main(){try{
 ConfigManager& config=ConfigManager::getSingleton();CONFIG_VALUES
 CreatureDefinition definition;definition.mXPTable={XP_VALUES};Seat owner,enemy;Creature creature;creature.mDefinition=&definition;creature.seat=&owner;
 const int wages[4]={400,200,100,50};const int perLevels[4]={FEE_LEVEL_VALUES};const int margins[3]={0,10,50};
 const int first[3][4]={{13,19,26,0},{14,19,27,0},{16,22,0,0}};
 for(int marginIndex=0;marginIndex<3;++marginIndex)for(int wageIndex=0;wageIndex<4;++wageIndex){
  definition.mFeeBase=wages[wageIndex];definition.mFeePerLevel=perLevels[wageIndex];int found=0;
  for(uint32_t level=1;level<30;++level){creature.mLevel=level;const bool wanted=creature.wantsSoulCrystal(800*(1+margins[marginIndex]/100.0));
   check(wanted==(first[marginIndex][wageIndex]!=0&&int(level)>=first[marginIndex][wageIndex]),"every wage/margin/level threshold");if(wanted&&!found)found=int(level);}
  check(found==first[marginIndex][wageIndex],"first worthwhile level at each margin");}
 definition.mFeeBase=0;definition.mFeePerLevel=0;creature.mLevel=29;check(!creature.wantsSoulCrystal(0),"zero wage never buys");definition.mFeeBase=wages[0];definition.mFeePerLevel=perLevels[0];
 creature.mLevel=30;check(!creature.wantsSoulCrystal(0),"maximum level never buys even free");
 std::unique_ptr<ItemInstance> crystal=ItemInstance::createSoulCrystal();
 check(crystal->mSoulCrystal&&!crystal->mDefinitionId.empty()&&crystal->mPotionId.empty()&&crystal->mBonuses.empty()&&crystal->mEffects.empty(),"factory gives a valid bonus-free holder identity");
 near(crystal->getPrice(),800,"actual central price");
 check(!creature.breakSoulCrystal(crystal)&&crystal.get()!=nullptr,"level30 preserves crystal ownership");
 creature.mLevel=11;creature.mExp=999;check(creature.breakSoulCrystal(crystal)&&!crystal&&creature.mLevel==12&&creature.mExp==0,"actual break advances exactly one level and resets XP");
 check(creature.changes==1&&!creature.breakSoulCrystal(crystal),"null item cannot trigger duplicate consumption");
 crystal.reset(new ItemInstance);check(!creature.breakSoulCrystal(crystal)&&crystal!=nullptr,"ordinary item is not consumed");
 for(double share:{0.0,.399999999,.4,.400000001,.9}){
  creature.mLevel=11;creature.mExp=definition.mXPTable[10]*share;creature.inventory[0]=ItemInstance::createSoulCrystal();
  const bool acted=CreatureMerchantAI::decideSoulCrystal(creature);check(acted==(share<.4),"strict threshold below0.4");
  check((creature.inventory[0]==nullptr)==(share<.4),"above threshold crystal remains carried");
 }
 creature.inventory[0]=ItemInstance::createSoulCrystal();creature.mLevel=30;check(!CreatureMerchantAI::decideSoulCrystal(creature)&&creature.inventory[0]!=nullptr,"max level idle never breaks");
 creature.mLevel=11;creature.mExp=0;creature.fighting=true;check(!CreatureMerchantAI::decideSoulCrystal(creature),"combat does not consume");creature.fighting=false;
 creature.inventory[0].reset();RoomMerchant merchant;merchant.seat=&owner;Tile table;table.room=&merchant;RoomMerchantTileData stock;merchant.mCoveredTiles={&table};merchant.mTileData[&table]=&stock;
 for(size_t index=0;index<tableCapacity(&owner);++index){MerchantGood good;good.mIndex=uint32_t(index+1);stock.mGoods.push_back(good);}
 crystal=ItemInstance::createSoulCrystal();check(merchant.getFreeTable()==nullptr&&merchant.getFreeTable(crystal.get())==&table,"full ordinary table accepts a crystal");
 for(int index=0;index<30;++index){crystal=ItemInstance::createSoulCrystal();check(merchant.addGoods(crystal,nullptr)&&!crystal,"unlimited crystals adopt on the first table");}
 check(merchant.getFreeTable()==nullptr,"crystals never consume or create ordinary capacity");
 crystal.reset(new ItemInstance);check(!merchant.addGoods(crystal,&table)&&crystal!=nullptr,"full ordinary table rejects without stealing item");
 ItemBagEntity delivery(ItemInstance::createSoulCrystal());delivery.seat=&owner;creature.tile=&table;
 check(merchant.hasCarryEntitySpot(&delivery),"worker advertises full-table crystal delivery");
 merchant.notifyCarryingStateChanged(&creature,&delivery);near(owner.gold,400,"keeper receives base price times buyshare");check(!delivery.item&&delivery.removed&&delivery.deleted,"delivery transfers and removes bag once");
 merchant.notifyCarryingStateChanged(&creature,&delivery);near(owner.gold,400,"repeated delivery pays nothing");
 ItemBagEntity sealed(ItemInstance::createSoulCrystal());sealed.item->mMerchantGoods=true;merchant.notifyCarryingStateChanged(&creature,&sealed);near(owner.gold,400,"sealed merchant goods do not pay twice");
 ItemBagEntity wrong(ItemInstance::createSoulCrystal());Tile foreign;creature.tile=&foreign;merchant.notifyCarryingStateChanged(&creature,&wrong);check(wrong.item!=nullptr&&!wrong.removed,"wrong room preserves ownership");
 merchant.mCoveredTiles.clear();check(!merchant.hasCarryEntitySpot(&wrong),"no table is not unlimited stock");merchant.mCoveredTiles={&table};
 Tile gift;gift.entities={&creature};creature.tile=nullptr;creature.mLevel=11;creature.mExp=definition.mXPTable[10]*.99;
 ItemBagEntity offered(ItemInstance::createSoulCrystal());offered.seat=&owner;
 creature.fighting=true;check(CreatureMerchantAI::offerGift(offered,gift)&&creature.mLevel==12&&offered.removed,"keeper drop breaks immediately regardless XPshare and combat");creature.fighting=false;
 ItemBagEntity capped(ItemInstance::createSoulCrystal());capped.seat=&owner;creature.mLevel=30;
 check(!CreatureMerchantAI::offerGift(capped,gift)&&capped.item!=nullptr&&!capped.removed,"maximum-level gift stays on floor");
 ItemBagEntity hostile(ItemInstance::createSoulCrystal());hostile.seat=&enemy;creature.mLevel=11;
 check(!CreatureMerchantAI::offerGift(hostile,gift)&&hostile.item!=nullptr,"gift never applies to another keeper");gift.entities.clear();check(!CreatureMerchantAI::offerGift(hostile,gift),"empty tile leaves bag");
 creature.tile=nullptr;creature.mLevel=14;creature.mExp=0;owner.margin=10;const double effectivePrice=800*(1+owner.margin/100.0);creature.gold=effectivePrice;
 stock.mGoods.clear();MerchantGood good;good.mItem=*ItemInstance::createSoulCrystal();good.mReservedBy=creature.getName();stock.mGoods.push_back(good);
 RoomMerchant::stock={{&merchant,&table,&stock.mGoods[0]}};Random::draw=.299999;
 check(CreatureMerchantAI::decideSoulCrystal(creature)&&creature.purchases==1,"eligible reserved crystal purchases below30percent");
 creature.gold=effectivePrice-.000001;check(!CreatureMerchantAI::decideSoulCrystal(creature),"insufficient exact gold refuses purchase");creature.gold=effectivePrice;
 Random::draw=.3;check(!CreatureMerchantAI::decideSoulCrystal(creature),"draw at30percent refuses purchase");Random::draw=0;
 creature.tried=true;check(!CreatureMerchantAI::decideSoulCrystal(creature),"failed-action guard prevents another purchase");creature.tried=false;
 stock.mGoods[0].mReservedBy="other";check(!CreatureMerchantAI::decideSoulCrystal(creature),"other reservation refuses purchase");stock.mGoods[0].mReservedBy=creature.getName();
 creature.mLevel=30;check(!CreatureMerchantAI::decideSoulCrystal(creature),"maximum level never purchases");
 creature.mLevel=1;check(!CreatureMerchantAI::decideSoulCrystal(creature),"worth-it denial prevents purchase");creature.mLevel=14;
 for(std::unique_ptr<ItemInstance>& held:creature.inventory)held.reset(new ItemInstance);
 check(!CreatureMerchantAI::decideSoulCrystal(creature),"full inventory refuses purchase");for(std::unique_ptr<ItemInstance>& held:creature.inventory)held.reset();
 creature.inventory[0]=ItemInstance::createSoulCrystal();creature.mExp=definition.mXPTable[13]*.5;check(!CreatureMerchantAI::decideSoulCrystal(creature),"already-held crystal prevents second purchase");creature.inventory[0].reset();
 const uint32_t levels[5]={1,5,10,20,30};const double chances[5]={.0144,.048,.099,.231,.403};
 for(int index=0;index<5;++index){creature.mLevel=levels[index];Random::draw=chances[index]-1e-10;heroCrystal(creature,"hero");check(creature.inventory[0]!=nullptr,"hero roll succeeds just below decided chance");creature.inventory[0].reset();
  Random::draw=chances[index]+1e-10;heroCrystal(creature,"hero");check(creature.inventory[0]==nullptr,"hero roll fails just above decided chance");}
 creature.mLevel=30;Random::draw=0;for(std::unique_ptr<ItemInstance>& held:creature.inventory)held.reset(new ItemInstance);
 heroCrystal(creature,"hero");for(const std::unique_ptr<ItemInstance>& held:creature.inventory)check(!held->mSoulCrystal,"full hero inventory gains no crystal");
 for(std::unique_ptr<ItemInstance>& held:creature.inventory)held.reset();heroCrystal(creature,"portal");check(creature.inventory[0]==nullptr,"nonhero receives no extra crystal roll");
 ItemInstance original=*ItemInstance::createSoulCrystal(),loaded;original.mBonuses={{"Strength",.125}};original.mEffects={{"Thrift",.0625}};
 std::stringstream stream;original.exportToStream(stream);stream<<" NEXT";check(loaded.importFromStream(stream)&&loaded.mSoulCrystal&&loaded.mDefinitionId==original.mDefinitionId,"stream crystal roundtrip");std::string next;stream>>next;check(next=="NEXT","new stream marker preserves next record");
 std::stringstream legacy("old 0 0 0 0 0 0 none NEXT");check(loaded.importFromStream(legacy)&&!loaded.mSoulCrystal,"old stream defaults crystal false");legacy>>next;check(next=="NEXT","old stream lookahead restores next record");
 loaded=original;std::stringstream malformed("bad 0 0 0 0 0 0 none SoulCrystal");check(!loaded.importFromStream(malformed)&&loaded.mDefinitionId==original.mDefinitionId&&loaded.mSoulCrystal,"short stream marker cannot partially adopt");
 ODPacket packet;original.exportToPacket(packet);packet<<std::string("NEXT");check(loaded.importFromPacket(packet)&&loaded.mSoulCrystal,"real packet crystal roundtrip");packet>>next;check(next=="NEXT","new packet preserves next record");
 ODPacket old;old<<std::string("old")<<Quality::poor<<uint32_t(0)<<uint32_t(0)<<uint32_t(0)<<false<<false<<std::string("")<<std::string("NEXT");
 check(loaded.importFromPacket(old)&&!loaded.mSoulCrystal,"real old packet defaults false");old>>next;check(next=="NEXT","copied packet lookahead does not consume following record");
 ItemInstance second;second.mDefinitionId="SECOND";second.mBonuses={{"Life",.375}};
 ODPacket consecutive;original.exportToPacket(consecutive);second.exportToPacket(consecutive);consecutive<<uint32_t(0x12345678);
 ItemInstance nextItem;check(loaded.importFromPacket(consecutive)&&nextItem.importFromPacket(consecutive)&&nextItem.mDefinitionId=="SECOND"&&!nextItem.mSoulCrystal,"two actual consecutive packet records preserve their identities");
 uint32_t sentinel=0;consecutive>>sentinel;check(sentinel==0x12345678,"two packet records leave following section untouched");
 std::stringstream consecutiveStream;original.exportToStream(consecutiveStream);consecutiveStream<<' ';second.exportToStream(consecutiveStream);consecutiveStream<<" NEXT";
 check(loaded.importFromStream(consecutiveStream)&&nextItem.importFromStream(consecutiveStream)&&nextItem.mDefinitionId=="SECOND"&&!nextItem.mSoulCrystal,"two actual consecutive stream records preserve flags");consecutiveStream>>next;check(next=="NEXT","two stream records preserve following section");
 ODPacket shortMarker;shortMarker<<std::string("bad")<<Quality::poor<<uint32_t(0)<<uint32_t(0)<<uint32_t(0)<<false<<false<<std::string("")<<std::string("SoulCrystal");loaded=original;
 check(!loaded.importFromPacket(shortMarker)&&loaded.mDefinitionId==original.mDefinitionId&&loaded.mSoulCrystal,"short optional packet marker is transactional");
 ODPacket invalid;invalid<<std::string("bad")<<int32_t(99)<<uint32_t(0);check(!loaded.importFromPacket(invalid)&&loaded.mDefinitionId==original.mDefinitionId,"invalid quality cannot partially adopt");
 ODPacket excessive;excessive<<std::string("bad")<<Quality::poor<<uint32_t(18);check(!loaded.importFromPacket(excessive)&&loaded.mSoulCrystal,"invalid bonus count rejected");
 std::cout<<"soul crystal production rules: ok\n";
}catch(const std::exception& error){std::cerr<<error.what()<<'\n';return 1;}}
'''

if __name__ == "__main__":
    main()
