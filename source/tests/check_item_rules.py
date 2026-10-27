"""Compile actual catalogue, rolling, rating, outfitting and item-loss code against bounded world fixtures.

This check compiles C++; do not execute it during a compilation-free feature window.
Quality expectations interpolate the approved level-one and level-thirty endpoints exactly.
"""
from item_probe_support import catalogue_fixture, creature_fixture, compile_and_run, function, source


# Exercise actual catalogue and creature rules with fixed-seed production fixtures.
def main():
    """Exercise production item rules without replacing their algorithms with a Python model."""
    entity_types = source("source/entities/GameEntityType.h")
    entity_types = entity_types[entity_types.index("enum class GameEntityType"):]
    entity_types = entity_types[:entity_types.index("};") + 2]
    lookup = function(source("source/gamemap/GameMap.cpp"), "GameEntity* GameMap::getEntityFromTypeAndName(")
    lookup_fixture = r"""
#include <string>
#include <vector>
#include <stdexcept>
//! \brief Supplies named registered entities to the actual typed lookup dispatcher.
struct GameEntity { std::string name;GameEntityType type=GameEntityType::unknown;
    //! \brief Constructs a named identity with its independently selected registered type.
    GameEntity(const std::string& value,GameEntityType kind=GameEntityType::unknown):name(value),type(kind){}
    //! \brief Supplies the type checked by the production ghost and box dispatcher.
    GameEntityType getObjectType()const{return type;}
};
//! \brief Uses the rendered registry interface expected by the production ghost dispatcher.
using RenderedMovableEntity=GameEntity;
//! \brief Isolates the real dispatch from unrelated map systems without replacing its switch.
struct GameMap {
    std::vector<GameEntity*> rendered;
    //! \brief Finds the exact registered rendered identity, or preserves a missing-name result.
    GameEntity* getRenderedMovableEntity(const std::string& name) {
        for(GameEntity* entity:rendered) if(entity->name==name) return entity;
        return nullptr;
    }
    //! \brief Keeps creatures outside this rendered-equipment fixture.
    GameEntity* getCreature(const std::string&) { return nullptr; }
    //! \brief Keeps spells outside this rendered-equipment fixture.
    GameEntity* getSpell(const std::string&) { return nullptr; }
    //! \brief Keeps lights outside this rendered-equipment fixture.
    GameEntity* getMapLight(const std::string&) { return nullptr; }
    //! \brief Keeps rooms outside this rendered-equipment fixture.
    GameEntity* getRoomByName(const std::string&) { return nullptr; }
    //! \brief Keeps traps outside this rendered-equipment fixture.
    GameEntity* getTrapByName(const std::string&) { return nullptr; }
    //! \brief Runs the unchanged production type-to-registry dispatcher.
    GameEntity* getEntityFromTypeAndName(GameEntityType type,const std::string& name);
};
"""
    lookup_checks = r"""
//! \brief Verifies equipment and infirmary figures resolve their registered identities and missing names stay missing.
int main() {
    GameMap map; GameEntity bag={"ItemBag__171"},merchant={"Merchant_1"},bundle={"HerbBundle_1"},shaman={"InfirmaryShaman_1"};
    map.rendered={&bag,&merchant,&bundle,&shaman};
    const GameEntityType types[]={GameEntityType::itemBagEntity,GameEntityType::merchantEntity,GameEntityType::herbBundleEntity,GameEntityType::infirmaryShamanEntity};
    for(size_t index=0;index<map.rendered.size();++index) {
        if(map.getEntityFromTypeAndName(types[index],map.rendered[index]->name)!=map.rendered[index])
            throw std::runtime_error("registered equipment entity lookup failed");
        if(map.getEntityFromTypeAndName(types[index],"missing")!=nullptr)
            throw std::runtime_error("missing equipment identity resolved");
    }
    GameEntity ghost("Ghost_1",GameEntityType::ghostEntity),box("GhostBox_1",GameEntityType::ghostBoxEntity);
    map.rendered.push_back(&ghost);map.rendered.push_back(&box);
    if(map.getEntityFromTypeAndName(GameEntityType::ghostEntity,ghost.name)!=&ghost ||
       map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,box.name)!=&box)
        throw std::runtime_error("registered ghost and box identities must resolve");
    if(map.getEntityFromTypeAndName(GameEntityType::ghostEntity,box.name)!=nullptr ||
       map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,ghost.name)!=nullptr ||
       map.getEntityFromTypeAndName(GameEntityType::ghostEntity,bag.name)!=nullptr ||
       map.getEntityFromTypeAndName(GameEntityType::ghostBoxEntity,"missing")!=nullptr)
        throw std::runtime_error("ghost lookup must reject wrong concrete types and missing identities");
    if(map.getEntityFromTypeAndName(GameEntityType::unknown,bag.name)!=nullptr)
        throw std::runtime_error("unknown entity type resolved");
}
"""
    compile_and_run("equipment-entity-lookup", entity_types + lookup_fixture +
                    "\n//! \\brief Runs the production entity lookup without changing its dispatch.\n" + lookup + lookup_checks)
    garden = function(source("source/rooms/RoomHerbGarden.cpp"), "bool RoomHerbGarden::hasOpenCreatureSpot(")
    lab = function(source("source/rooms/RoomAlchemyLab.cpp"), "bool RoomAlchemyLab::hasOpenCreatureSpot(")
    affinity_rooms = r'''
//! \brief Keeps bed availability independent of the actual production affinity gate.
struct RoomHerbGarden:Room {
    //! \brief Creates the fixture room with the normal garden identity.
    RoomHerbGarden(GameMap* map,Seat* seat):Room(map,seat,RoomType::herbGarden){}
    //! \brief Supplies an available bed, so an affinity denial cannot be hidden by missing work.
    Tile* findRipeBed() const { static Tile tile; return &tile; }
    //! \brief Runs the production affinity gate unchanged.
    bool hasOpenCreatureSpot(Creature* creature);
};
//! \brief Keeps cauldron availability independent of the production affinity gate.
struct RoomAlchemyLab:Room {
    //! \brief Creates a lab with a known owner.
    RoomAlchemyLab(GameMap* map,Seat* seat):Room(map,seat,RoomType::alchemyLab){}
    //! \brief Supplies an available cauldron while the production method evaluates affinity.
    Tile* findCauldron() const { static Tile tile; return &tile; }
    //! \brief Runs the production affinity gate unchanged.
    bool hasOpenCreatureSpot(Creature* creature);
};
'''
    checks = r'''
//! \brief Counts all actual held item and potion instances after a production arrival roll.
std::pair<uint32_t,uint32_t> heldCounts(const Creature& creature) {
    uint32_t items=0,potions=0;
    for(const std::unique_ptr<ItemInstance>& item:creature.mEquipment) if(item.get()!=nullptr) ++items;
    for(const std::unique_ptr<ItemInstance>& item:creature.mInventory) if(item.get()!=nullptr) { if(item->mPotionId.empty()) ++items; else ++potions; }
    for(const std::unique_ptr<ItemInstance>& item:creature.mPotionSlots) if(item.get()!=nullptr) ++potions;
    for(const std::unique_ptr<ItemInstance>& item:creature.dropped) if(item.get()!=nullptr) { if(item->mPotionId.empty()) ++items; else ++potions; }
    return std::make_pair(items,potions);
}
//! \brief Runs fixed-seed roll, ownership, affinity and the approved drop probabilities and armed arrival flow.
int main(int argc,char** argv) { try {
    check(argc==2,"repository argument"); GameMap map; Seat seat; loadCatalogue(argv[1],map);
    for(uint32_t rank=0;rank<4;++rank) {
        const Quality quality=static_cast<Quality>(rank); std::vector<const ItemDefinition*> eligible;
        for(const ItemDefinition* definition:map.mItemDefinitions) if(definition->getQuality(quality).mAvailable) eligible.push_back(definition);
        check(!eligible.empty(),"quality has definitions");
        for(uint32_t roll=0;roll<10000;++roll) {
            const ItemDefinition& definition=*eligible[roll%eligible.size()]; const ItemQuality& spec=definition.getQuality(quality);
            std::unique_ptr<ItemInstance> item=ItemInstance::create(definition,quality);
            check(item.get()!=nullptr&&item->mBonuses.size()>=spec.mBonusMinimum&&item->mBonuses.size()<=spec.mBonusMaximum,"actual bonus count");
            check(item->mEffects==spec.mEffects,"exact configured effects");
            check(item->mEffects.size()==(rank<2?0:rank-1),"quality effect count");
            for(size_t index=0;index<item->mBonuses.size();++index) {
                const std::pair<std::string,double>& bonus=item->mBonuses[index]; const ItemBonusRange& range=spec.mBonuses[index];
                check(bonus.first==range.mKind,"ordered bonus kind");
                check(bonus.second>=range.mMinimum-1e-9&&bonus.second<=range.mMaximum+1e-9,"inclusive roll range");
                check(std::abs(bonus.second*10-std::round(bonus.second*10))<1e-8,"one decimal retained");
            }
            check(std::abs(item->getPrice(&map)-(spec.mPrice+spec.mPricePerBonus*item->mBonuses.size()))<1e-9,"actual rolled item price");
        }
    }
    const ItemDefinition* primary=map.getItemDefinition("BLK_A_Head"); const ItemDefinition* alternate=map.getItemDefinition("BLK_B_Head");
    check(primary!=nullptr&&alternate!=nullptr,"real rating catalogue lines");
    Creature wearer(&map,&seat); wearer.mLevel=30;
    std::unique_ptr<ItemInstance> own=ItemInstance::create(*primary,Quality::common),other=ItemInstance::create(*alternate,Quality::common);
    own->mBonuses={{"Damage%",10}}; other->mBonuses=own->mBonuses;
    check(wearer.rateItem(*own)>wearer.rateItem(*other),"actual rating prefers primary path for identical bonuses");
    std::unique_ptr<ItemInstance> first=map.rollItem(Quality::epic,"head","","Arms");
    std::unique_ptr<ItemInstance> second=map.rollItem(Quality::epic,"head","","Arms");
    check(first.get()!=nullptr&&second.get()!=nullptr&&first->mQuality==Quality::epic&&first->mEpicSerial>0,"first unique Epic");
    check(second->mQuality==Quality::rare&&second->mDefinitionId==first->mDefinitionId,"registered Epic line falls back to Rare");
    Creature victim(&map,&seat); victim.mEquipment[2]=ItemInstance::create(*primary,Quality::common);
    victim.mEquipment[3]=ItemInstance::createPoor("armour"); victim.mInventory[0]=ItemInstance::create(*alternate,Quality::rare);
    victim.mPotionSlots[0]=ItemInstance::createPotion("healing_small");
    Weapon sword,shield; sword.name="BasicSword"; sword.type="sword"; sword.hands=1; shield.name="RustyShield"; shield.type="shield"; shield.hands=1;
    ConfigManager::getSingleton().weapons[sword.name]=&sword;
    ConfigManager::getSingleton().weapons[shield.name]=&shield;
    std::unique_ptr<ItemInstance> poorSword=ItemDrops::poorWeapon(sword),poorShield=ItemDrops::poorWeapon(shield);
    check(poorSword->mDefinitionId==sword.name&&poorShield->mDefinitionId==shield.name,"Poor bags retain equipment identity");
    check(poorSword->getDisplayName(&map)==sword.name&&poorShield->getDisplayName(&map)==shield.name,"Poor spawn equipment names");
    check(poorSword->getPrice(&map)==20&&poorShield->getPrice(&map)==20,"Poor spawn equipment price");
    for(const ItemInstance* poor:{poorSword.get(),poorShield.get()}) {
        const std::string image=poor->getImageName(); check(image.size()>5&&image.substr(image.size()-5)=="_base","Poor weapon uses base image");
        const ItemDefinition* imageLine=map.getItemDefinition(image.substr(0,image.size()-5));
        const Weapon* equipment=ConfigManager::getSingleton().getWeapon(poor->mDefinitionId);
        check(imageLine!=nullptr&&imageLine->getWeaponClass()==equipment->getWeaponType()&&
            imageLine->getQuality(Quality::common).mAvailable,"Poor icon uses a path line of the spawn WeaponClass");
        const std::string atlas=cleanFile(std::string(argv[1])+"/gui/Items.imageset");
        check(atlas.find("name=\""+image+"\"")!=std::string::npos,"Poor icon exists in the actual atlas");
    }
    victim.mWeaponR=&sword; victim.mWeaponL=&shield;
    victim.dropItems(false); check(victim.dropped.size()==1&&victim.dropped[0]->mQuality!=Quality::poor||
        (victim.dropped.size()==1&&!victim.dropped[0]->mPotionId.empty()),"KO drops exactly one eligible item or potion");
    check(victim.mEquipment[3].get()!=nullptr,"KO retains Poor worn fallback");
    victim.dropItems(false); check(victim.dropped.size()==1,"second KO call in one fight cannot drop twice");
    victim.dropItems(true); check(victim.dropped.size()==6,"death drops all four held instances and both spawn fallbacks");
    for(const std::unique_ptr<ItemInstance>& item:victim.mEquipment) check(item.get()==nullptr,"death empties worn items");
    for(const std::unique_ptr<ItemInstance>& item:victim.mInventory) check(item.get()==nullptr,"death empties inventory");
    RoomHerbGarden garden(&map,&seat); RoomAlchemyLab laboratory(&map,&seat);
    check(!garden.hasOpenCreatureSpot(&wearer)&&!laboratory.hasOpenCreatureSpot(&wearer),"missing affinities never work despite free work spots");
    wearer.definition.mRoomAffinity.push_back(CreatureRoomAffinity(RoomType::herbGarden,100,0));
    wearer.definition.mRoomAffinity.push_back(CreatureRoomAffinity(RoomType::alchemyLab,90,0));
    check(!garden.hasOpenCreatureSpot(&wearer)&&!laboratory.hasOpenCreatureSpot(&wearer),"zero affinities never work");
    wearer.definition.mRoomAffinity.clear(); wearer.definition.mRoomAffinity.push_back(CreatureRoomAffinity(RoomType::herbGarden,100,1));
    wearer.definition.mRoomAffinity.push_back(CreatureRoomAffinity(RoomType::alchemyLab,90,1));
    check(garden.hasOpenCreatureSpot(&wearer)&&laboratory.hasOpenCreatureSpot(&wearer),"positive affinity control can work");
    // Expected flows use the approved chance per slot and exact quality endpoints.
    const double expectedFlows[5][3]={{1,.36,.31},{5,.40,.35},{10,.45,.40},{20,1.10,.50},{30,1.95,.60}};
    for(const double* expected:expectedFlows) {
        const uint32_t level=static_cast<uint32_t>(expected[0]); uint32_t qualities[4]={0,0,0,0},items=0,potions=0,armedItems=0,armedPotions=0;
        for(uint32_t roll=0;roll<100000;++roll) {
            ++qualities[static_cast<size_t>(heroQuality(level))];
            map.mEpicRegistry.clear(); Creature arrival(&map,&seat); arrival.mLevel=level; arrival.resizePotionSlots();
            ItemDrops::outfit(arrival,"hero"); const std::pair<uint32_t,uint32_t> held=heldCounts(arrival); items+=held.first; potions+=held.second;
            map.mEpicRegistry.clear(); Creature armed(&map,&seat); armed.mLevel=level; armed.resizePotionSlots(); armed.mWeaponR=&sword; armed.mWeaponL=&shield;
            ItemDrops::outfit(armed,"hero"); const std::pair<uint32_t,uint32_t> armedHeld=heldCounts(armed); armedItems+=armedHeld.first; armedPotions+=armedHeld.second;
        }
        const double progress=(level-1)/29.0;
        const double linear[4]={.60+(.02-.60)*progress,.35+(.17-.35)*progress,
            .04+(.62-.04)*progress,.01+(.19-.01)*progress};
        for(size_t rank=0;rank<4;++rank)
            check(std::abs(qualities[rank]/100000.0-linear[rank])<.01,"actual quality roll follows exact endpoint interpolation");
        check(std::abs(items/100000.0-expected[1])<.01,"actual hero outfit item flow");
        check(std::abs(potions/100000.0-expected[2])<.01,"actual hero outfit potion flow");
        check(std::abs(armedItems/100000.0-expected[1])<.01,"armed Poor weapon and shield rolls preserve full item flow");
        check(std::abs(armedPotions/100000.0-expected[2])<.01,"armed hero potion flow");
    }
    std::cout<<"item production rules passed\n";
} catch(const std::exception& error) { std::cerr<<"FAIL: "<<error.what()<<"\n";return 1; }
}
'''
    compile_and_run("item-rules", catalogue_fixture() + creature_fixture() + affinity_rooms + garden + lab + checks)


if __name__ == "__main__":
    main()
