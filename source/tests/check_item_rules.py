"""Compile actual catalogue, rolling, rating, outfitting and item-loss code against bounded world fixtures.

This check compiles C++; do not execute it during a compilation-free feature window.
The unchanged historical simulation expectations are deliberately retained: their disagreement with the
configured linear drop rules must remain a failed assertion until the coordinator resolves that conflict.
"""
from item_probe_support import catalogue_fixture, creature_fixture, compile_and_run, function, source


def main():
    """Exercise production item rules without replacing their algorithms with a Python model."""
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
//! \brief Runs fixed-seed roll, ownership, affinity and both prescribed drop expectation sets.
int main(int argc,char** argv) {
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
    // Historical simulation table is intentionally unchanged; the linear rule contradicts these quality columns.
    const double historical[5][7]={{1,.36,.30,.675,.020,.005,.31},{5,.40,.30,.583,.100,.017,.35},
        {10,.45,.30,.468,.200,.032,.40},{20,1.10,.30,.288,.350,.062,.50},{30,1.95,.30,.258,.350,.092,.60}};
    bool simulationMatches=true,flowMatches=true;
    for(const double* expected:historical) {
        const uint32_t level=static_cast<uint32_t>(expected[0]); uint32_t qualities[4]={0,0,0,0},items=0,potions=0,armedItems=0,armedPotions=0;
        for(uint32_t roll=0;roll<100000;++roll) {
            ++qualities[static_cast<size_t>(heroQuality(level))];
            map.mEpicRegistry.clear(); Creature arrival(&map,&seat); arrival.mLevel=level; arrival.resizePotionSlots();
            ItemDrops::outfit(arrival,"hero"); const std::pair<uint32_t,uint32_t> held=heldCounts(arrival); items+=held.first; potions+=held.second;
            map.mEpicRegistry.clear(); Creature armed(&map,&seat); armed.mLevel=level; armed.resizePotionSlots(); armed.mWeaponR=&sword; armed.mWeaponL=&shield;
            ItemDrops::outfit(armed,"hero"); const std::pair<uint32_t,uint32_t> armedHeld=heldCounts(armed); armedItems+=armedHeld.first; armedPotions+=armedHeld.second;
        }
        const double steps=level-1;
        const double linear[4]={.60-.02*steps,1-(.60-.02*steps)-(.04+.02*steps)-(.01+.006*steps),.04+.02*steps,.01+.006*steps};
        for(size_t rank=0;rank<4;++rank) {
            const double observed=qualities[rank]/100000.0;
            check(std::abs(observed-linear[rank])<.01,"actual quality roll follows specified linear rule");
            simulationMatches=simulationMatches&&std::abs(observed-expected[rank+2])<.01;
        }
        check(std::abs(items/100000.0-expected[1])<.01,"actual hero outfit item flow");
        check(std::abs(potions/100000.0-expected[6])<.01,"actual hero outfit potion flow");
        flowMatches=flowMatches&&std::abs(armedItems/100000.0-expected[1])<.01;
        check(std::abs(armedPotions/100000.0-expected[6])<.01,"armed hero potion flow");
        std::cout<<"hero level "<<level<<" simulation quality match "<<simulationMatches<<" armed flow match "<<flowMatches<<"\n";
    }
    check(simulationMatches&&flowMatches,"OPEN: historical simulation quality table conflicts with the specified linear drop rule; armed Poor weapon/shield rolls return no extra instance. Neither expected flow nor quality values may be changed without resolution");
    std::cout<<"item production rules passed\n";
}
'''
    compile_and_run("item-rules", catalogue_fixture() + creature_fixture() + affinity_rooms + garden + lab + checks)


if __name__ == "__main__":
    main()
