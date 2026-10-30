"""Shared production-source extraction and world fixtures for the two item C++ checks."""
from pathlib import Path
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def source(name):
    """Read production code while leaving its implementation unchanged."""
    return (ROOT / name).read_text(encoding="utf-8")


def function(text, signature):
    """Extract a complete production function, retaining its signature and body."""
    start = text.index(signature)
    opening = text.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    return text[start:end]


def cpp(name):
    """Use a production translation unit with only its world-service includes replaced."""
    return re.sub(r"^#include[^\n]*\n", "", source(name), flags=re.M)


def compile_and_run(name, probe):
    """Compile and run a bounded standalone probe only when this check is explicitly executed."""
    output = ROOT / "out" / name
    output.mkdir(parents=True, exist_ok=True)
    code, executable = output / "probe.cpp", output / "probe.exe"
    code.write_text(probe, encoding="utf-8")
    command = ["cl", "/nologo", "/EHsc", "/std:c++14", "/I" + str(ROOT / "source"), str(code),
               "/Fe:" + str(executable), "/Fo:" + str(output / "probe.obj")]
    subprocess.run(command, cwd=output, stdin=subprocess.DEVNULL, check=True, timeout=600)
    subprocess.run([str(executable), str(ROOT)], cwd=ROOT, stdin=subprocess.DEVNULL, check=True, timeout=600)


def catalogue_fixture():
    """Combine the actual definition, instance, price, roll and Epic-registry code with small world services."""
    fixture = r'''
#include "entities/ItemDefinition.h"
#include "entities/ItemInstance.h"
#include "entities/PotionDefinition.h"
#include "rooms/RoomType.h"
static const uint32_t MAX_LEVEL = 30;
#include <algorithm>
#include <cmath>
#include <cctype>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <random>
#include <set>
#include <sstream>
#include <stdexcept>
#include <vector>
// Retain production log expressions while the fixture supplies no game log service.
#define OD_LOG_INF(message) static_cast<void>(message)
//! \brief Supplies unused packet services while stream and gameplay methods run unchanged.
class ODPacket {
public:
    //! \brief Accepts an unused packet write in catalogue functions outside this probe's scope.
    template<class T> ODPacket& operator<<(const T&) { return *this; }
    //! \brief Accepts an unused packet read in catalogue functions outside this probe's scope.
    template<class T> ODPacket& operator>>(T&) { return *this; }
    //! \brief Reports a valid fixture packet; no packet assertion is made by these probes.
    explicit operator bool() const { return true; }
};
namespace Random {
std::mt19937 engine(20261024);
//! \brief Produces reproducible inclusive integral draws for production rolling methods.
uint32_t Uint(uint32_t low, uint32_t high) { return std::uniform_int_distribution<uint32_t>(low, high)(engine); }
//! \brief Produces reproducible uniform real draws for production rolling methods.
double Double(double low, double high) { return std::uniform_real_distribution<double>(low, high)(engine); }
}
//! \brief Supplies spawn-weapon metadata without rendering or combat services.
struct Weapon {
    std::string name="BasicAxeOrc", type="axe"; uint32_t hands=2;
    //! \brief Returns the fixture spawn equipment id.
    const std::string& getName() const { return name; }
    //! \brief Returns its actual weapon-class fixture value.
    const std::string& getWeaponType() const { return type; }
    //! \brief Returns how many hands this spawn weapon occupies.
    uint32_t getHands() const { return hands; }
};
namespace CreatureSkillTree {
//! \brief Supplies creature group/family identity to the real drop and rating methods.
struct TypeInfo { std::string mGroup="blocker", mFamily="human"; };
//! \brief Holds the fixture's real catalogue primary path.
struct TemplateDef { std::string mPrimary="Arms"; };
//! \brief Supplies world-selected paths; path scoring itself remains production code.
struct SkillTreeConfig {
    TemplateDef primary;
    //! \brief Gives the fixed fixture template used for the primary-path comparison.
    const TemplateDef* findTemplate(const std::string&, const std::string&) const { return &primary; }
    //! \brief Supplies valid paths for the blocker fixture to the actual outfit method.
    std::vector<std::string> getPathNames(const TypeInfo& type) const;
};
}
//! \brief Loads the actual catalogue and configured probability/price inputs used by production methods.
struct ConfigManager {
    std::map<std::string, std::unique_ptr<ItemDefinition>> items;
    std::map<std::string, PotionDefinition> potions;
    std::map<std::string, const Weapon*> weapons;
    std::vector<PotionDefinition> potionOrder;
    std::map<std::string, std::map<std::string,double>> settings;
    CreatureSkillTree::SkillTreeConfig tree;
    //! \brief Returns the single isolated configuration fixture.
    static ConfigManager& getSingleton() { static ConfigManager cfg; return cfg; }
    //! \brief Looks up a parsed item line.
    const ItemDefinition* getItem(const std::string& id) const { std::map<std::string,std::unique_ptr<ItemDefinition>>::const_iterator i=items.find(id); return i==items.end()?nullptr:i->second.get(); }
    //! \brief Looks up a parsed potion definition.
    const PotionDefinition* getPotion(const std::string& id) const { std::map<std::string,PotionDefinition>::const_iterator i=potions.find(id); return i==potions.end()?nullptr:&i->second; }
    //! \brief Preserves the actual potion-file order for production brew selection.
    const std::vector<PotionDefinition>& getPotions() const { return potionOrder; }
    //! \brief Supplies the configured item lines for Poor weapon image lookup.
    std::vector<const ItemDefinition*> getItems() const { std::vector<const ItemDefinition*> result; for(const std::pair<const std::string,std::unique_ptr<ItemDefinition>>& entry:items) result.push_back(entry.second.get()); return result; }
    //! \brief Resolves the fixture's explicit spawn equipment identities.
    const Weapon* getWeapon(const std::string& id) const { std::map<std::string,const Weapon*>::const_iterator found=weapons.find(id); return found==weapons.end()?nullptr:found->second; }
    //! \brief Returns a required numeric global configuration input.
    double getItemSetting(const std::string& section,const std::string& key) const { return settings.at(section).at(key); }
    //! \brief Returns a required numeric room configuration input.
    double getRoomConfigDouble(const std::string& key) const { return settings.at("Rooms").at(key); }
    //! \brief Returns a room setting when the fixture read it, else the code fallback (equal to the shipped value).
    double getRoomConfigDoubleOrDefault(const std::string& key, double fallback) const { std::map<std::string,std::map<std::string,double>>::const_iterator rooms=settings.find("Rooms"); if(rooms==settings.end()) return fallback; std::map<std::string,double>::const_iterator found=rooms->second.find(key); return found==rooms->second.end()?fallback:found->second; }
    //! \brief Returns an equipment setting; the code fallback equals the shipped equipments.cfg value.
    double getEquipmentConfigDoubleOrDefault(const std::string&, double fallback) const { return fallback; }
    //! \brief Returns the configured soul crystal price of the global settings.
    double getSoulCrystalPrice() const { return 800.0; }
    //! \brief Returns the configured hero soul crystal chance at the first level.
    double getSoulCrystalHeroRareStart() const { return 0.04; }
    //! \brief Returns the configured hero soul crystal chance at the last level.
    double getSoulCrystalHeroRareEnd() const { return 0.62; }
    //! \brief Returns the fixture path metadata used by production rating and outfit logic.
    const CreatureSkillTree::SkillTreeConfig& getCreatureSkillTree() const { return tree; }
};
//! \brief Derives valid fixture paths from real catalogue metadata without reproducing drop selection.
std::vector<std::string> CreatureSkillTree::SkillTreeConfig::getPathNames(const TypeInfo& type) const {
    std::set<std::string> paths;
    for(const std::pair<const std::string,std::unique_ptr<ItemDefinition>>& entry:ConfigManager::getSingleton().items) {
        const ItemDefinition& item=*entry.second; std::string family=item.getPath();
        for(char& letter:family) letter=static_cast<char>(std::tolower(static_cast<unsigned char>(letter)));
        if(item.getGroup()==type.mGroup || (item.getGroup()=="family"&&family==type.mFamily)) paths.insert(item.getPath());
    }
    return std::vector<std::string>(paths.begin(),paths.end());
}
struct Seat;
struct Room;
struct Creature;
//! \brief Supplies catalogue ownership and the actual per-map Epic registry.
struct GameMap {
    std::vector<const ItemDefinition*> mItemDefinitions; std::set<std::string> mEpicRegistry; uint32_t mNextEpicSerial=1;
    std::vector<Creature*> creatures; std::vector<Room*> rooms;
    std::map<std::string,uint32_t> merchantPotions,waitingPotions,potionSales;
    //! \brief Looks up an authoritative parsed item definition.
    const ItemDefinition* getItemDefinition(const std::string& id) const { return ConfigManager::getSingleton().getItem(id); }
    //! \brief Reports whether a unique Epic line already has a holder.
    bool isEpicRegistered(const std::string& id) const { return mEpicRegistry.count(id)!=0; }
    //! \brief Allocates an isolated serial for fixed-line Epic resolution.
    uint32_t allocateEpicSerial() { return mNextEpicSerial++; }
    //! \brief Runs the actual production candidate selection and Epic downgrade.
    std::unique_ptr<ItemInstance> rollItem(Quality quality,const std::string& slot="",const std::string& weaponClass="",const std::string& path="");
    //! \brief Runs the actual production registration method.
    void registerEpic(const ItemInstance& item);
    //! \brief Runs the actual production release method.
    void unregisterEpic(const ItemInstance& item);
    //! \brief Supplies real fixture occupants to production brew selection.
    const std::vector<Creature*>& getCreatures() const { return creatures; }
    //! \brief Supplies fixture room ownership to inventory and merchant methods.
    std::vector<Room*> getRoomsByTypeAndSeat(RoomType type,const Seat* seat) const;
    //! \brief Exercises keeper payments without a rendered treasury.
    bool withdrawFromTreasuries(int32_t amount,Seat* seat);
    //! \brief Keeps this isolated simulation out of editor bypass paths.
    bool isInEditorMode() const { return false; }
};
namespace ItemEffects {
//! \brief Leaves tooltip rendering outside the roll checks; effect ids are checked against source by the config check.
const std::string& getName(const std::string& id) { return id; }
//! \brief Supplies the unused stream-validation service; catalogue ids are checked independently.
bool exists(const std::string&) { return true; }
}
//! \brief Fails a real gameplay invariant with its precise case label.
void check(bool valid,const std::string& label) { if(!valid) throw std::runtime_error(label); }
//! \brief Reads a config with comments removed before using the actual parsers.
std::string cleanFile(const std::string& path) {
    std::ifstream file(path); check(bool(file),path); std::string line,result;
    while(std::getline(file,line)) { const size_t comment=line.find('#'); if(comment!=std::string::npos) line.erase(comment); result+=line+"\n"; } return result;
}
//! \brief Loads real supplied definitions and numeric settings for both probes.
void loadCatalogue(const std::string& root, GameMap& map) {
    ConfigManager& cfg=ConfigManager::getSingleton(); std::string line;
    std::stringstream items(cleanFile(root+"/config/items.cfg"));
    while(std::getline(items,line)) if(line=="[Item]") { std::unique_ptr<ItemDefinition> item(ItemDefinition::load(items)); check(item.get()!=nullptr,"parse actual item"); const std::string id=item->getId(); map.mItemDefinitions.push_back(item.get()); cfg.items[id]=std::move(item); }
    std::stringstream potions(cleanFile(root+"/config/potions.cfg"));
    while(std::getline(potions,line)) if(line=="[Potion]") { PotionDefinition potion; check(potion.importFromStream(potions),"parse actual potion"); cfg.potions[potion.getId()]=potion; cfg.potionOrder.push_back(potion); }
    for(const std::string& name : {"global.cfg","rooms.cfg"}) { std::stringstream input(cleanFile(root+"/config/"+name)); std::string section;
        while(std::getline(input,line)) { std::stringstream row(line); std::string key; double number; if(!(row>>key)) continue;
            if(key.front()=='[') { if(key.size()>2&&key[1]!='/') section=key.substr(1,key.size()-2); else section.clear(); }
            else if(row>>number) cfg.settings[section][key]=number;
        }
    }
    check(cfg.items.size()==187&&cfg.potions.size()==29,"actual catalogue sizes");
}
'''
    definitions = cpp("source/entities/ItemDefinition.cpp") + cpp("source/entities/PotionDefinition.cpp")
    definitions += cpp("source/entities/ItemInstance.cpp")
    game_map = source("source/gamemap/GameMap.cpp")
    for signature in ("std::unique_ptr<ItemInstance> GameMap::rollItem(", "void GameMap::registerEpic(", "void GameMap::unregisterEpic("):
        definitions += "\n" + function(game_map, signature)
    return fixture + "\n" + definitions


def creature_fixture():
    """Use actual slot, rating, knockout and gift code with minimal creature/world storage."""
    affinity = function(source("source/entities/CreatureDefinition.h"), "class CreatureRoomAffinity") + ";"
    fixture = r'''
struct Tile;
struct MerchantEntity;
//! \brief Supplies a keeper's visible storage and owner settings to the production methods.
struct Seat {
    int32_t margin=10,labMode=0; double treasury=100000,merchantGold=0,researchFactor=1;
    MerchantEntity* merchant=nullptr;
    //! \brief Returns the configured fixture margin in percentage points.
    int32_t getMerchantMargin() const { return margin; }
    //! \brief Returns the configured fixture lab mode.
    int32_t getLabMode() const { return labMode; }
    //! \brief Collects the exact fractional keeper income calculated by the merchant.
    void addMerchantGold(double amount) { merchantGold+=amount; }
    //! \brief Makes tiles visible unless a test explicitly supplies a different owner.
    bool hasVisionOnTile(Tile*) const { return true; }
    //! \brief Supplies the optional room figure for takeover code.
    MerchantEntity* getMerchant() const { return merchant; }
};
//! \brief Supplies only room ownership and engine-managed tile membership.
struct Room {
    GameMap* map; Seat* seat; RoomType type;
    //! \brief Creates fixture world ownership without game services.
    Room(GameMap* value,Seat* owner,RoomType kind):map(value),seat(owner),type(kind){}
    //! \brief Supports production polymorphic room casts.
    virtual ~Room() {}
    //! \brief Returns the assigned room type.
    RoomType getType() const { return type; }
    //! \brief Returns the owning keeper.
    Seat* getSeat() const { return seat; }
    //! \brief Returns the isolated world.
    GameMap* getGameMap() const { return map; }
};
//! \brief Represents a reachable floor position for storage and delivery fixtures.
struct Tile {
    Room* room=nullptr;
    //! \brief Returns the current covering fixture room.
    Room* getCoveringRoom() const { return room; }
    //! \brief Supplies an opaque position to unused rendering services.
    int getPosition() const { return 0; }
};
//! \brief Provides the actual base copy contract used by merchant tile cloning.
struct TileData {
    //! \brief Starts a plain world tile.
    TileData() {}
    //! \brief Accepts the original tile's base state during production cloning.
    explicit TileData(const TileData*) {}
    //! \brief Supports production-specific tile clones.
    virtual ~TileData() {}
    //! \brief Supplies the polymorphic engine clone interface.
    virtual TileData* cloneTileData() const { return new TileData(this); }
};
@AFFINITY@
static CreatureRoomAffinity EMPTY_AFFINITY(RoomType::nullRoomType,0,0);
//! \brief Supplies creature identity while using the actual room-affinity lookup.
struct CreatureDefinition {
    std::string group="blocker",family="human"; bool worker=false;
    std::vector<CreatureRoomAffinity> mRoomAffinity;
    //! \brief Returns the fixture skill group.
    const std::string& getSkillGroup() const { return group; }
    //! \brief Returns the fixture family.
    const std::string& getSkillFamily() const { return family; }
    //! \brief Returns whether worker-only rating weights apply.
    bool isWorker() const { return worker; }
    //! \brief Uses the actual missing/zero-affinity lookup contract.
    const CreatureRoomAffinity& getRoomAffinity(RoomType roomType) const;
};
enum class CreatureActionType {fight};
//! \brief Supplies holder state; all tested inventory, rating and loss methods are production functions.
struct Creature {
    GameMap* map; Seat* seat; CreatureDefinition definition; const CreatureDefinition* mDefinition; Tile tile;
    uint32_t mLevel=1; bool fighting=false,mKoDroppedThisFight=false,mNeedFireRefresh=false;
    bool frozen=false,wanted=true; double hp=100,mana=50,gold=10000,mood=0; unsigned drinks=0;
    Weapon* mWeaponR=nullptr; Weapon* mWeaponL=nullptr; std::string name="buyer";
    //! \brief Supplies the template identity consumed by the actual rating function.
    struct Build {std::string mTemplate="fixture";} mSkillBuild;
    std::array<std::unique_ptr<ItemInstance>,6> mEquipment;
    std::array<std::unique_ptr<ItemInstance>,4> mInventory;
    std::vector<std::unique_ptr<ItemInstance>> mPotionSlots;
    std::vector<std::unique_ptr<ItemInstance>> dropped;
    //! \brief Creates an empty living holder for a particular keeper.
    Creature(GameMap* value,Seat* owner):map(value),seat(owner),mDefinition(&definition),mPotionSlots(1){}
    //! \brief Returns the isolated authoritative world.
    GameMap* getGameMap() const { return map; }
    //! \brief Returns the assigned keeper.
    Seat* getSeat() const { return seat; }
    //! \brief Returns fixture identity metadata.
    const CreatureDefinition* getDefinition() const { return &definition; }
    //! \brief Returns the configured fixture level.
    uint32_t getLevel() const { return mLevel; }
    //! \brief Supplies the exact combat gate to the production inventory methods.
    bool isActionInList(CreatureActionType) const { return fighting; }
    //! \brief Identifies a living fixture occupant.
    bool isAlive() const { return hp>0; }
    //! \brief Identifies this isolated server holder.
    bool getIsOnServerMap() const { return true; }
    //! \brief Returns its current fixture floor.
    Tile* getPositionTile() { return &tile; }
    //! \brief Returns a spawn weapon without applying equipment bonuses.
    const Weapon* getWeaponR() const { return mWeaponR; }
    //! \brief Returns a spawn off-hand without applying equipment bonuses.
    const Weapon* getWeaponL() const { return mWeaponL; }
    //! \brief Exposes real fixture inventory storage.
    const std::array<std::unique_ptr<ItemInstance>,4>& getInventory() const { return mInventory; }
    //! \brief Exposes the real fixture equipment for production merchant desirability checks.
    const std::array<std::unique_ptr<ItemInstance>,6>& getEquipment() const { return mEquipment; }
    //! \brief Exposes real fixture potion storage.
    const std::vector<std::unique_ptr<ItemInstance>>& getPotionSlots() const { return mPotionSlots; }
    //! \brief Returns fixture health for useful-now gift decisions.
    double getHP() const { return hp; }
    //! \brief Supplies the unchanged fixture maximum health.
    double getMaxHp() const { return 100; }
    //! \brief Sets fixture health during production arrival outfitting.
    void setHP(double value) { hp=value; }
    //! \brief Returns fixture mana for useful-now gift decisions.
    double getCurrentMana() const { return mana; }
    //! \brief Supplies the unchanged fixture maximum mana.
    double getMaxMana() const { return 50; }
    //! \brief Sets fixture mana during production arrival outfitting.
    void setCurrentMana(double value) { mana=value; }
    //! \brief Reports the fixture freeze state.
    bool isFrozen() const { return frozen; }
    //! \brief Records a requested useful drink; potion effects themselves have separate production checks.
    bool drinkPotion(std::unique_ptr<ItemInstance>& item) { ++drinks; item.reset(); return true; }
    //! \brief Exposes a controlled zero Thrift bonus to merchant arithmetic.
    double getItemEffect(const std::string&) const { return 0; }
    //! \brief Returns exact fractional carried gold.
    double getGoldCarriedAmount() const { return gold; }
    //! \brief Applies the exact merchant-calculated fractional amount.
    void addGoldCarriedFraction(double value) { gold+=value; }
    //! \brief Records the exact mood points requested by a completed trade.
    void addMerchantMood(double value) { mood+=value; }
    //! \brief Returns the reservation identity.
    const std::string& getName() const { return name; }
    //! \brief Flags real holder mutations without rendering.
    void itemsChanged() { mNeedFireRefresh=true; }
    //! \brief Supplies the unused path-release callback in the recipe branch.
    void popAction() {}
    //! \brief Uses actual spawn-class slot restrictions.
    int32_t getItemEquipmentSlot(const ItemInstance& item) const;
    //! \brief Uses actual quality level gates.
    bool isItemEquippable(const ItemInstance& item) const;
    //! \brief Uses actual configured bonus and path weights.
    double rateItem(const ItemInstance& item) const;
    //! \brief Uses actual safe equip/store/overflow ownership.
    bool acceptItem(std::unique_ptr<ItemInstance> item,bool equip=true);
    //! \brief Fixture stand-in: these probes never buy soul crystals, the crystal rules have their own check.
    bool wantsSoulCrystal(double) const { return false; }
    //! \brief Uses the actual combat-gated inventory decision.
    void decideEquipment();
    //! \brief Uses the actual knockout/death loss rule.
    void dropItems(bool dead);
    //! \brief Uses actual slot exchanges.
    std::unique_ptr<ItemInstance> setEquipment(size_t slot,std::unique_ptr<ItemInstance> item);
    //! \brief Uses actual inventory exchanges.
    std::unique_ptr<ItemInstance> setInventorySlot(size_t slot,std::unique_ptr<ItemInstance> item);
    //! \brief Uses actual potion exchanges.
    std::unique_ptr<ItemInstance> setPotionSlot(size_t slot,std::unique_ptr<ItemInstance> item);
    //! \brief Uses actual level thresholds and never-shrink potion sizing.
    void resizePotionSlots();
    //! \brief Fixture stand-in: consumes the crystal and raises the level, the crystal effects have their own check.
    bool breakSoulCrystal(std::unique_ptr<ItemInstance>& item) { item.reset(); ++mLevel; return true; }
    //! \brief Uses actual gift use/slot/inventory/ownership priorities.
    bool receiveGiftedPotion(std::unique_ptr<ItemInstance>& item);
    //! \brief Runs the unchanged refill branch extracted from production decidePotion.
    void refillForCheck();
};
//! \brief Provides a no-loss world drop sink; the production loss method chooses each item.
void dropCreatureItem(Creature& creature,std::unique_ptr<ItemInstance> item) { if(item.get()!=nullptr) creature.dropped.push_back(std::move(item)); }
//! \brief Filters fixture room ownership for the production inventory code.
std::vector<Room*> GameMap::getRoomsByTypeAndSeat(RoomType type,const Seat* seat) const {
    std::vector<Room*> result; for(Room* room:rooms) if(room->getType()==type&&room->getSeat()==seat) result.push_back(room); return result;
}
//! \brief Supplies treasury withdrawal while preserving the actual keeper-price calculation.
bool GameMap::withdrawFromTreasuries(int32_t amount,Seat* seat) { if(seat->treasury<amount) return false; seat->treasury-=amount; return true; }
#include "game/ItemDrops.h"
'''.replace("@AFFINITY@", affinity)
    definitions = source("source/entities/CreatureDefinition.cpp")
    fixture += function(definitions, "const CreatureRoomAffinity& CreatureDefinition::getRoomAffinity(")
    equipment = source("source/entities/CreatureEquipmentAI.cpp")
    fixture += "\nstatic const double EQUIP_UPGRADE_MARGIN=0.5;\n" + function(equipment, "bool sameItemPath(")
    for signature in ("int32_t Creature::getItemEquipmentSlot(", "bool Creature::isItemEquippable(",
                      "double Creature::rateItem(", "bool Creature::acceptItem(", "void Creature::decideEquipment(", "void Creature::dropItems("):
        fixture += "\n" + function(equipment, signature)
    creature = source("source/entities/Creature.cpp")
    for signature in ("std::unique_ptr<ItemInstance> Creature::setEquipment(", "std::unique_ptr<ItemInstance> Creature::setInventorySlot(",
                      "std::unique_ptr<ItemInstance> Creature::setPotionSlot(", "void Creature::resizePotionSlots("):
        fixture += "\n" + function(creature, signature)
    potions = source("source/entities/CreaturePotions.cpp")
    fixture += "\n" + function(potions, "bool isPotionBuff(")
    fixture += "\n" + function(potions, "bool Creature::receiveGiftedPotion(")
    return fixture + "\n" + cpp("source/game/ItemDrops.cpp")
