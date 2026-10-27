"""Static check of the rebuilt research tree: tabs, tiers, parents, costs, free level one entries,
keeper skills, layout pages and icons.

The expected tree is written out here independently of the source. Nothing is compiled.
Usage: python source/tests/check_world_balance_tree.py
"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

repo = Path(__file__).resolve().parents[2]


def read(path):
    return (repo / path).read_text(encoding="utf-8")


# (tab, tier, skill type, research button, parents) in row order, as the tree shows them
EXPECTED = [
    ("Rooms", 1, "roomTreasury", "TreasuryButton", []),
    ("Rooms", 1, "roomDormitory", "DormitoryButton", []),
    ("Rooms", 1, "roomHatchery", "HatcheryButton", []),
    ("Rooms", 1, "roomLibrary", "LibraryButton", []),
    ("Rooms", 1, "roomTavern", "TavernButton", []),
    ("Rooms", 2, "roomTrainingHall", "TrainingHallButton", ["roomTreasury"]),
    ("Rooms", 2, "roomWorkshop", "WorkshopButton", ["roomTreasury"]),
    ("Rooms", 2, "roomBridgeWooden", "WoodenBridgeButton", ["roomTreasury"]),
    ("Rooms", 2, "roomGuardRoom", "GuardRoomButton", ["roomDormitory"]),
    ("Rooms", 2, "roomCasino", "CasinoButton", ["roomTreasury"]),
    ("Rooms", 2, "roomToilet", "ToiletButton", ["roomDormitory"]),
    ("Rooms", 2, "tavernBeer", "BeerButton", ["roomTavern"]),
    ("Rooms", 3, "roomArena", "ArenaButton", ["roomTrainingHall"]),
    ("Rooms", 3, "roomPrison", "PrisonButton", ["roomGuardRoom"]),
    ("Rooms", 3, "roomCrypt", "CryptButton", ["roomLibrary"]),
    ("Rooms", 3, "roomGhostRoom", "GhostRoomButton", ["roomLibrary"]),
    ("Rooms", 3, "roomBridgeStone", "StoneBridgeButton", ["roomBridgeWooden"]),
    ("Rooms", 3, "roomInfirmary", "InfirmaryButton", ["roomGuardRoom"]),
    ("Rooms", 4, "roomTorture", "TortureButton", ["roomPrison"]),
    ("Rooms", 4, "roomTemple", "PrayerTempleButton", ["roomCrypt"]),
    ("Rooms", 4, "keeperDominion", "DominionButton", ["roomArena"]),
    ("Rooms", 2, "roomMerchant", "MerchantButton", ["roomTreasury"]),
    ("Rooms", 2, "roomHerbGarden", "HerbGardenButton", ["roomHatchery"]),
    ("Rooms", 3, "roomAlchemyLab", "AlchemyLabButton", ["roomHerbGarden"]),
    ("Traps", 1, "trapDoorWooden", "WoodenDoorTrapButton", ["roomWorkshop"]),
    ("Traps", 1, "trapSpike", "SpikeTrapButton", ["roomWorkshop"]),
    ("Traps", 1, "trapCannon", "CannonButton", ["roomWorkshop"]),
    ("Traps", 1, "trapAlarm", "AlarmTrapButton", ["roomWorkshop"]),
    ("Traps", 2, "trapDoorIronbound", "IronboundDoorTrapButton", ["trapDoorWooden"]),
    ("Traps", 2, "trapDoorBarricade", "BarricadeTrapButton", ["trapDoorWooden"]),
    ("Traps", 2, "trapGas", "GasTrapButton", ["trapSpike"]),
    ("Traps", 2, "trapBoulder", "BoulderTrapButton", ["trapSpike"]),
    ("Traps", 2, "trapWatchBanner", "WatchBannerTrapButton", ["trapAlarm", "roomGuardRoom"]),
    ("Traps", 2, "trapFear", "FearTrapButton", ["trapAlarm"]),
    ("Traps", 3, "trapDoorSteel", "SteelDoorTrapButton", ["trapDoorIronbound"]),
    ("Traps", 3, "trapDoorSecret", "SecretDoorTrapButton", ["trapDoorIronbound"]),
    ("Traps", 3, "trapLightning", "LightningTrapButton", ["trapCannon"]),
    ("Traps", 3, "trapTrigger", "TriggerTrapButton", ["trapAlarm"]),
    ("Traps", 3, "trapFireburst", "FireburstTrapButton", ["trapGas"]),
    ("Traps", 4, "trapDoorRuned", "RunedDoorTrapButton", ["trapDoorSteel"]),
    ("Traps", 4, "trapFreeze", "FreezeTrapButton", ["trapLightning"]),
    ("Traps", 4, "keeperHeartFortitude", "HeartFortitudeButton", ["trapDoorSteel"]),
    ("Traps", 4, "keeperHeartMending", "HeartMendingButton", ["keeperHeartFortitude"]),
    ("Traps", 2, "trapFineTools", "FineToolsButton", ["roomWorkshop"]),
    ("Traps", 3, "trapMasterTools", "MasterToolsButton", ["trapFineTools"]),
    ("Spells", 1, "spellSummonWorker", "SummonWorkerButton", []),
    ("Spells", 1, "spellCreatureHeal", "CreatureHealButton", ["roomLibrary"]),
    ("Spells", 1, "spellCreatureHaste", "CreatureHasteButton", ["roomLibrary"]),
    ("Spells", 1, "spellEyeEvil", "SpellEyeEvilButton", ["roomLibrary"]),
    ("Spells", 2, "spellCreatureDefense", "CreatureDefenseButton", ["spellCreatureHeal"]),
    ("Spells", 2, "spellCreatureStrength", "CreatureStrengthButton", ["spellCreatureHaste"]),
    ("Spells", 2, "spellCallToWar", "CallToWarButton", ["spellCreatureHaste"]),
    ("Spells", 2, "spellCreatureSlow", "CreatureSlowButton", ["spellEyeEvil"]),
    ("Spells", 2, "spellLightning", "LightningButton", ["spellEyeEvil"]),
    ("Spells", 3, "spellCreatureWeak", "CreatureWeakButton", ["spellCreatureSlow"]),
    ("Spells", 3, "spellCreatureExplosion", "CreatureExplosionButton", ["spellLightning"]),
    ("Spells", 3, "spellPossess", "PossessButton", ["spellEyeEvil"]),
    ("Spells", 3, "spellCreateGold", "CreateGoldButton", ["roomTreasury"]),
    ("Spells", 4, "spellTremor", "TremorButton", ["spellCreatureExplosion"]),
    ("Spells", 4, "spellInferno", "InfernoButton", ["spellCreatureExplosion"]),
    ("Spells", 4, "spellDefector", "DefectorButton", ["spellPossess"]),
    ("Spells", 4, "spellHexenHen", "HexenHenButton", ["spellCreatureWeak"]),
    ("Spells", 4, "keeperManaFlow", "ManaFlowButton", ["roomTemple"]),
    ("Spells", 3, "spellSunthornCultivation", "SunthornButton", ["roomAlchemyLab"]),
]
TIER_COST = {1: 100, 2: 250, 3: 600, 4: 1500}
FREE_LEVEL_ONE = ["roomTreasury", "roomDormitory", "roomHatchery", "roomLibrary", "roomTavern", "spellSummonWorker"]
TAB_TOTALS = {tab: sum((0 if name in FREE_LEVEL_ONE else TIER_COST[tier]) + 6 * TIER_COST[tier]
    for entry_tab, tier, name, button, parents in EXPECTED if entry_tab == tab)
    for tab in ("Rooms", "Traps", "Spells")}
assert TAB_TOTALS == {"Rooms": 79650, "Traps": 82250, "Spells": 84950}
TAB_TITLES = {"Rooms": "Rooms", "Traps": "Traps and doors", "Spells": "Spells"}
KEEPERS = {
    "keeperDominion": ("DominionButton", "Keeper: Dominion", "Rooms"),
    "keeperHeartFortitude": ("HeartFortitudeButton", "Keeper: Heart Fortitude", "Traps"),
    "keeperHeartMending": ("HeartMendingButton", "Keeper: Heart Mending", "Traps"),
    "keeperManaFlow": ("ManaFlowButton", "Keeper: Mana Flow", "Spells"),
    "tavernBeer": ("BeerButton", "Tavern: Beer", "Rooms"),
}

assert len(EXPECTED) == 64, "the tree has 64 entries"

# ---------------------------------------------------------------------------------------------
# 1. The constructor of the skill manager builds exactly this tree
manager = read("source/game/SkillManager.cpp")
constructor = manager[manager.index("SkillManager::SkillManager()"):manager.index("SkillManager::~SkillManager()")]
prefixes = dict(re.findall(r'static const std::string (TREE_PREFIX_\w+) = "([^"]+)";', manager))
assert prefixes == {"TREE_PREFIX_ROOMS": "SkillTabs/Rooms/", "TREE_PREFIX_TRAPS": "SkillTabs/Traps/",
                    "TREE_PREFIX_SPELLS": "SkillTabs/Spells/"}, "tab path prefixes"
prefix_tab = {"TREE_PREFIX_ROOMS": "Rooms", "TREE_PREFIX_TRAPS": "Traps", "TREE_PREFIX_SPELLS": "Spells"}
built = []
current = None
parents = []
for line in constructor.splitlines():
    match = re.search(r"createSkill\(mSkills, SkillType::(\w+), (NO_PARENTS|std::vector<SkillType>\{([^}]*)\})\)", line)
    if match:
        current = match[1]
        parents = re.findall(r"SkillType::(\w+)", match[3] or "")
    match = re.search(r'new SkillDef(\w+)\((TREE_PREFIX_\w+), "([^"]+)", skill, (\d)', line)
    if match and current != "spellSummonChampion":
        built.append((prefix_tab[match[2]], int(match[4]), current, match[3], parents))
        if match[1] == "Keeper":
            assert current in KEEPERS, "only the five keeper skills use SkillDefKeeper"
        else:
            assert current not in KEEPERS, "a keeper skill uses SkillDefKeeper"
    if "new Skill(SkillType::spellSummonChampion" in line:
        current = "spellSummonChampion"
assert built == EXPECTED, "the constructor builds the tree of tabs, tiers, rows and parents"
assert "TREE_PREFIX_SPELLS, \"SummonChampionButton\"" in constructor, "the reward skill stays outside the tree"
for old in ("AttackSkills", "TacticSkills", "MagicSkills", "lvl1depends", "lvl2depends"):
    assert old not in manager, "the old column construction is gone: " + old
# a parent is registered before its children
registered = []
for tab, tier, name, button, parent_list in EXPECTED:
    for parent in parent_list:
        assert parent in registered, "%s needs %s registered first" % (name, parent)
    registered.append(name)

# ---------------------------------------------------------------------------------------------
# 2. skills.cfg: the 64 entries with the tier costs and the free level one block
cfg = read("config/skills.cfg")
body = re.sub(r"#[^\r\n]*", "", cfg)
skills_block = body[body.index("[Skills]") + len("[Skills]"):body.index("[/Skills]")].split()
assert len(skills_block) % 2 == 0
costs = {}
for index in range(0, len(skills_block), 2):
    assert skills_block[index] not in costs, "duplicate entry " + skills_block[index]
    costs[skills_block[index]] = int(skills_block[index + 1])
assert "spellSummonChampion" not in costs, "the reward skill has no entry"
assert sorted(costs) == sorted(entry[2] for entry in EXPECTED), "[Skills] lists exactly the 64 entries"
for tab, tier, name, button, parent_list in EXPECTED:
    assert costs[name] == TIER_COST[tier], "%s costs the tier %d value" % (name, tier)
free_block = body[body.index("[FreeLevelOne]") + len("[FreeLevelOne]"):body.index("[/FreeLevelOne]")].split()
assert sorted(free_block) == sorted(FREE_LEVEL_ONE), "[FreeLevelOne] lists the five starting entries"
assert body.index("[/Skills]") < body.index("[FreeLevelOne]"), "the free block follows the cost block"

totals = {"Rooms": 0, "Traps": 0, "Spells": 0}
for tab, tier, name, button, parent_list in EXPECTED:
    value = costs[name]
    totals[tab] += (0 if name in FREE_LEVEL_ONE else value) + 2 * value + 4 * value
assert totals == TAB_TOTALS, "all levels together: %s" % totals

# The cost rules of the Skill class
skill_cpp = read("source/game/Skill.cpp")
assert "150" not in skill_cpp and ": 100" not in skill_cpp, "the 100/150 fallbacks are gone"
assert "mFreeLevelOne ? 0 : mNeededSkillPoints" in skill_cpp
assert "mNeededSkillPoints * (level == 2 ? 2 : 4)" in skill_cpp
config = read("source/utils/ConfigManager.cpp")
assert "return SKILL_POINTS_MISSING_ENTRY;" in config and "SKILL_POINTS_MISSING_ENTRY = 1500" in read("source/utils/ConfigManager.h")

# ---------------------------------------------------------------------------------------------
# 3. Keeper skills in the enum, the strings and the skill classes
skill_type_h = read("source/game/SkillType.h")
keeper_block = "keeperDominion,\n    keeperHeartFortitude,\n    keeperHeartMending,\n    keeperManaFlow,\n"
assert keeper_block.replace("\n", "\r\n") in skill_type_h or keeper_block in skill_type_h
assert skill_type_h.index("keeperManaFlow") < skill_type_h.index("countSkill,") if "countSkill," in skill_type_h else \
    skill_type_h.index("keeperManaFlow") < skill_type_h.index("countSkill")
assert skill_type_h.index("spellSummonChampion") < skill_type_h.index("keeperDominion"), "appended after the old values"
skill_type_cpp = read("source/game/SkillType.cpp")
for name, (button, title, tab) in KEEPERS.items():
    assert 'return "%s";' % name in skill_type_cpp, "toString name of " + name
    assert 'return "%s";' % title in skill_type_cpp, "player visible name of " + name
assert "enum class SkillTab" in read("source/game/SkillManager.h")
header = read("source/game/SkillManager.h")
assert re.search(r"spells,\s*keeper,\s*nb", header), "SkillFamily::keeper stands before nb"
assert "case SkillFamily::keeper:" in manager
keeper_class = manager[manager.index("class SkillDefKeeper"):manager.index("static Skill* createSkill(")]
assert "return SkillFamily::keeper;" in keeper_class
assert 'return "";' in keeper_class and "static const std::string guiPath;" in keeper_class
for title in ("Dominion", "Heart Fortitude", "Heart Mending", "Mana Flow"):
    assert 'KEEPER_TITLE' in manager and '"%s"' % title in manager

# a skill without an action bar button gets an empty cast button name and is skipped where that matters
assert 'skill->getGuiPath().empty() ? "" :' in manager
assert "skill->getGuiPath().empty() || hoveredWindow->getName()" in manager
editor = read("source/modes/EditorMode.cpp")
assert "if(!castButtonName.empty())" in editor
game = read("source/modes/GameMode.cpp")
assert game.count("if(!castButtonName.empty())") >= 6

# Skirmish game settings: the keeper skills get a row on the page of their tab
seats = read("source/modes/MenuModeConfigureSeats.cpp")
page = seats[seats.index("std::string itemPageName(SkillType type)"):]
page = page[:page.index("\n}\n")]
assert 'type == SkillType::keeperDominion' in page and 'return "Rooms";' in page
assert "SkillType::keeperHeartFortitude" in page and "SkillType::keeperHeartMending" in page
assert "SkillType::keeperManaFlow" in page and 'return "Spells";' in page

# The repeated notice of an empty research queue
player = read("source/game/Player.cpp")
assert "Warning: your library has nothing to research. Choose the next research in the research tree." in player
notice = player[player.index("void Player::notifyNoSkillInQueue()"):]
assert "EventShortNoticeType::aboutSkills" in notice[:notice.index("\n}\n")]

# ---------------------------------------------------------------------------------------------
# 4. The research tree window: one tab control, three pages, every button in the page of its tab
layout = ET.parse(repo / "gui/WindowSkillTree.layout")
skills_window = layout.find('.//Window[@name="Skills"]')
assert skills_window.find('Property[@name="Area"]').get("value") == "{{0,20},{0,38},{1,-20},{1,-64}}", "Skills keeps its area"
assert skills_window.find("Window") is not None and len(skills_window.findall("Window")) == 1, "Skills holds only the tab control"
tabs = skills_window.find('Window[@name="SkillTabs"]')
assert tabs.get("type") == "OD/TabControl"
assert tabs.find('Property[@name="Area"]').get("value") == "{{0,4},{0,4},{1,-4},{1,-4}}"
assert tabs.find('Property[@name="TabHeight"]').get("value") == "{0,30}"
assert tabs.find('Property[@name="RiseOnClickEnabled"]').get("value") == "False"
pages = tabs.findall("Window")
assert [p.get("name") for p in pages] == ["Rooms", "Traps", "Spells"]
for page_window in pages:
    assert page_window.get("type") == "DefaultWindow"
    assert page_window.find('Property[@name="Area"]').get("value") == "{{0,0},{0,0},{1,0},{1,0}}"
    tab = page_window.get("name")
    assert page_window.find('Property[@name="Text"]').get("value") == TAB_TITLES[tab]
    names = [w.get("name") for w in page_window.findall("Window")]
    expected_names = [entry[3] for entry in EXPECTED if entry[0] == tab]
    if tab == "Spells":
        expected_names.append("SummonChampionButton")
    assert sorted(names) == sorted(expected_names), "buttons of the %s page" % tab
for window in tabs.iter("Window"):
    assert window.get("name") not in ("AttackSkills", "TacticSkills", "MagicSkills")
text = read("gui/WindowSkillTree.layout")
assert "SelectionBrush" not in text and "FrameColours" not in text
imageset = read("gui/ODIcons.imageset")
for name, (button, title, tab) in KEEPERS.items():
    node = next(w for w in tabs.iter("Window") if w.get("name") == button)
    assert node.get("type") == "OD/ResearchButton"
    assert node.find('Property[@name="ButtonImage"]').get("value") == "OpenDungeonsIcons/" + button
    assert node.find('Property[@name="TooltipText"]').get("value") == title
    bar = node.find('Window[@name="%sProgressBar"]' % button)
    assert bar is not None and bar.get("type") == "OD/ProgressBar", "progress bar child of " + button
    assert 'name="%s"' % button in imageset, "icon of " + button
cells = {"DominionButton": (512, 1152), "HeartFortitudeButton": (640, 1152), "HeartMendingButton": (768, 1152), "ManaFlowButton": (896, 1152)}
icon_images = ET.fromstring(imageset)
for button, (x, y) in cells.items():
    # The painted atlas doubles source coordinates, retaining each original logical cell.
    nodes = icon_images.findall('Image[@name="%s"]' % button)
    assert len(nodes) == 1, "unique icon of " + button
    assert tuple(int(nodes[0].get(key)) for key in ('xPos', 'yPos', 'width', 'height')) == \
        (x * 2, y * 2, 256, 256), "doubled cell of " + button
motifs = read("tools/forged_motifs.py")
last_four = re.findall(r'^    "(\w+)": _slot\(m_\w+, "(\w+)"\),', motifs, re.M)[-14:-10]
assert last_four == [("DominionButton", "room"), ("HeartFortitudeButton", "trap"), ("HeartMendingButton", "trap"),
                     ("ManaFlowButton", "spell")], "the four keeper icons precede the nine appended item and room icons"
assert motifs.index('"NavigationMessagesRead"') < motifs.index('"DominionButton"') < motifs.index('"MenuReturn"')

# ---------------------------------------------------------------------------------------------
# 5. The window code: tabs, tiers and the gates
assert '"SkillTreeWindow/Skills/SkillTabs"' in game and 'setSelectedTab("Rooms")' in game, "the Rooms page opens first"
connections = game[game.index("void GameMode::refreshSkillConnections()"):game.index("void GameMode::refreshSpellButtonCoolDowns()")]
assert "SkillManager::getSkillTier(type) - 1" in connections, "the row is the tier"
assert "(static_cast<float>(rowPlaced[row]) + .5f) / static_cast<float>(rowSizes[row])" in connections, "x-centre (i + 0.5) / n"
assert "pageWidth / static_cast<float>(widestRow) - freeSpace" in connections, "node size from the page: width of the widest row"
assert "(available - static_cast<float>(rowCount - 1) * freeSpace) / static_cast<float>(rowCount) - badgeHeight" in connections, "node size from the page: all rows with their counters fit the height"
assert "getSkillTab(dependency->getType()) != SkillManager::getSkillTab(entry.first)" in connections, "paths only inside a tab"
assert "ResearchJunction" not in game
assert "Needs: " in game and "SkillManager::getTabTitle(parentTab)" in game
seat = read("source/game/Seat.cpp")
assert "bool Seat::canResearchLevel(SkillType type, int level, const std::vector<std::pair<SkillType, int> >& queuedBefore) const" in seat
gate = seat[seat.index("const char* Seat::getResearchGateFailure("):seat.index("bool Seat::canResearchLevel(")]
for reason in ("not allowed by the level", "parent missing", "tab needs more entries at level 1"):
    assert reason in gate
assert "(nbAllowed + 1) / 2" in gate, "half of the allowed entries, rounded up"
set_tree = seat[seat.index("void Seat::setSkillTree("):seat.index("TileStateNotified* Seat::getTileStateNotified(")]
assert "OD_LOG_WRN(" in set_tree and "continue;" in set_tree, "an invalid entry is dropped with a warning, not the whole queue"
assert "canResearchLevel" in manager and "canResearchLevel" in game, "client buttons and AI use the same function"
assert "if(!mGameMap->isSandbox())" in seat and "addFreeLevelOneSkills(skills);" in seat, "not applied in sandbox mode"
assert "one of them" not in read("source/game/Skill.h"), "the stale parent comment is gone"
print("research tree checks passed")
