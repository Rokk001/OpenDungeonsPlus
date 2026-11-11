"""Check all class hand defaults and probe real equipment pictures/tooltips (decision 922).

--source-only checks catalogue/atlas coverage and emits the C++ probe without compiling.
The default run compiles and executes the production parsers and presentation methods.
"""
import re
import sys
import xml.etree.ElementTree as ET

from item_probe_support import ROOT, catalogue_fixture, compile_and_run, function, source


def blocks(name, tag):
    """Read complete config blocks without treating examples in comments as definitions."""
    text = re.sub(r"#[^\n]*", "", source(name))
    return re.findall(r"\[" + tag + r"\](.*?)\[/" + tag + r"\]", text, re.S)


def field(block, key, default="none"):
    """Read one scalar setting with the same absent-hand default as CreatureDefinition."""
    found = re.search(r"^\s*" + key + r"\s+(\S+)", block, re.M)
    return default if found is None else found[1]


def main():
    """Verify 35 classes, 19 distinct defaults, real atlas entries and production tooltip probe generation."""
    creatures = blocks("config/creatures.cfg", "Creature")
    weapons = {field(b, "Name"): b for b in blocks("config/equipments.cfg", "Equipment")}
    items = blocks("config/items.cfg", "Item")
    defaults = {field(b, "WeaponSpawn" + hand) for b in creatures for hand in ("R", "L")} - {"none"}
    assert len(creatures) == 35, len(creatures)
    assert len(defaults) == 19, defaults
    atlas = {entry.get("name") for entry in ET.parse(ROOT / "gui/Items.imageset").getroot()}
    for name in sorted(defaults):
        kind = field(weapons[name], "WeaponType")
        candidates = [b for b in items if field(b, "WeaponClass") == kind and "Name\tCommon" in b]
        assert candidates, name
        assert all(field(b, "Id") + "_base" in atlas for b in candidates), name
    fill = function(source("source/entities/Creature.cpp"), "void Creature::fillItemSlotWindows(")
    assert fill.index("item = creature->mEquipment[slot].get()") < fill.index("if(item == nullptr && slot < VISIBLE_ITEM_HAND_SLOTS)")
    assert "slot == 0 ? creature->mWeaponR : creature->mWeaponL" in fill
    assert "heldWeapon = weapon;" in fill and "item->getImageName(heldWeapon)" in fill
    assert "Gui::setItemTooltip(image, *item, creature->getGameMap(), heldWeapon)" in fill

    # Replace only the world fixture's weapon stand-in with the actual class and actual parser.
    probe = catalogue_fixture()
    stub = function(probe, "struct Weapon {") + ";"
    probe = probe.replace(stub, '#include "entities/Weapon.h"')
    probe += r'''
#define OD_LOG_ERR(message) static_cast<void>(message)
namespace Helper {
//! \brief Supplies numeric conversion services to the actual equipment parser.
double toDouble(const std::string& value) { return std::stod(value); }
//! \brief Supplies unsigned conversion services to the actual equipment parser.
uint32_t toUInt32(const std::string& value) { return static_cast<uint32_t>(std::stoul(value)); }
}
'''
    for signature in ("Weapon* Weapon::load(", "bool Weapon::update(", "std::string Weapon::getWeaponType("):
        probe += "\n" + function(source("source/entities/Weapon.cpp"), signature)
    probe += r'''
//! \brief Checks real parser data, exact-equipment pictures, precision, quality and authoritative overrides.
int main(int argc, char** argv) {
    check(argc==2,"repository path"); GameMap map; loadCatalogue(argv[1],map);
    std::vector<std::unique_ptr<Weapon>> equipment; std::string line;
    std::stringstream input(cleanFile(std::string(argv[1])+"/config/equipments.cfg"));
    while(std::getline(input,line)) if(line=="[Equipment]") {
        std::unique_ptr<Weapon> weapon(Weapon::load(input)); check(weapon.get()!=nullptr,"equipment parser");
        ConfigManager::getSingleton().weapons[weapon->getName()]=weapon.get(); equipment.push_back(std::move(weapon));
    }
    ItemInstance sword; sword.mDefinitionId="RustySword";
    const Weapon* actual=ConfigManager::getSingleton().getWeapon("RustySword");
    check(actual!=nullptr,"sword exists");
    const std::string tooltip=sword.describe(&map,actual);
    check(tooltip.find("Quality: Poor")!=std::string::npos,"explicit Poor quality");
    check(tooltip.find("0.14-0.2 / 0-0 / 0-0")!=std::string::npos,"base values retain sub-unit precision");
    check(sword.getImageName(actual)=="BLK_A_Sword_base","exact-equipment picture before type fallback");
    std::stringstream tuned("Name RustySword [Stats] MeshName Longsword.mesh WeaponType axe Hands 2 PhysicalDamageMin 0.375 PhysicalDamage 0.625 [/Stats] [/Equipment]");
    std::unique_ptr<Weapon> overrideWeapon(Weapon::load(tuned));
    check(overrideWeapon.get()!=nullptr,"authoritative override parsed");
    check(sword.describe(&map,overrideWeapon.get()).find("0.375-0.625")!=std::string::npos,"actual held values override global config");
    check(sword.getImageName(overrideWeapon.get())=="BLK_A_Axe_base","actual held class controls fallback image");
    ItemInstance rare; rare.mDefinitionId="BLK_A_Sword"; rare.mQuality=Quality::rare;
    rare.mBonuses.push_back(std::make_pair("Damage%",12.3));
    check(rare.getImageName()=="BLK_A_Sword_rare","rolled picture retained");
    check(rare.describe(&map).find("Damage +12.3%")!=std::string::npos,"rolled bonus retained");
'''
    for name in sorted(defaults):
        probe += '\n    { ItemInstance item; item.mDefinitionId="' + name + '"; const Weapon* weapon=ConfigManager::getSingleton().getWeapon(item.mDefinitionId);\n'
        probe += '      check(weapon!=nullptr,"default exists"); const std::string image=item.getImageName(weapon);\n'
        probe += '      check(cleanFile(std::string(argv[1])+"/gui/Items.imageset").find("name=\\\""+image+"\\\"")!=std::string::npos,"default picture in atlas");\n'
        probe += '      check(item.describe(&map,weapon).find(item.mDefinitionId)!=std::string::npos,"actual default name"); }\n'
    probe += '\n    std::cout<<"decision 922 production probe passed\\n";\n}\n'
    if "--source-only" in sys.argv:
        output = ROOT / "out/dungeonbook-defaults-922/probe.cpp"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(probe, encoding="utf-8")
        print("decision 922: 35 classes, 19 defaults, atlas coverage passed; C++ probe emitted, not compiled")
    else:
        compile_and_run("dungeonbook-defaults-922", probe)


if __name__ == "__main__":
    main()
