"""Check catalogue row comments in their owning functions and configuration."""
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]
ANCHORS = {
    "A01": ("source/ai/AiEconomy.cpp", "ECON::digQueueWatch"),
    "A02": ("source/ai/AiEconomy.cpp", "ECON::claimWatch"),
    "A03": ("source/ai/AiEconomy.cpp", "ECON::summonWatch"),
    "A04": ("source/ai/AiEconomy.cpp", "ECON::walletGate"),
    "A05": ("source/ai/AiEconomy.cpp", "ECON::castCreateGold"),
    "A06": ("source/ai/AiEconomy.cpp", "ECON::goldCapacityWatch"),
    "A07": ("source/ai/AiEconomy.cpp", "ECON::manaCapWatch"),
    "A08": ("source/ai/AiEconomy.cpp", "ECON::sellObsolete"),
    "A09": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B01": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B02": ("source/ai/AiRooms.cpp", "ROOMS::bedWatch"),
    "B03": ("source/ai/AiRooms.cpp", "ROOMS::hatcheryWatch"),
    "B04": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B05": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B06": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B07": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B08": ("source/ai/AiRooms.cpp", "ROOMS::auditTavern"),
    "B09": ("source/ai/AiRooms.cpp", "ROOMS::auditCasino"),
    "B10": ("source/ai/AiRooms.cpp", "ROOMS::toiletWatch"),
    "B11": ("source/ai/AiRooms.cpp", "ROOMS::auditMerchant"),
    "B12": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B13": ("source/ai/AiRooms.cpp", "ROOMS::auditLab"),
    "B14": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B15": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B16": ("source/ai/AiRooms.cpp", "ROOMS::auditInfirmary"),
    "B17": ("source/ai/AiRooms.cpp", "ROOMS::ghostProduct"),
    "B18": ("source/ai/AiRooms.cpp", "ROOMS::auditSpa"),
    "B19": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "B20": ("source/ai/AiRooms.cpp", "ROOMS::templeSacrifice"),
    "B21": ("source/ai/AiRooms.cpp", "ROOMS::bridgeWatch"),
    "B22": ("source/ai/AiRooms.cpp", "ROOMS::rebuildLost"),
    "B23": ("source/ai/AiRooms.cpp", "ROOMS::placeRoom"),
    "B24": ("source/ai/AiRooms.cpp", "ROOMS::auditSettings"),
    "C01": ("source/ai/AiResearch.cpp", "RES::chooseResearch"),
    "C02": ("source/ai/AiResearch.cpp", "RES::refillQueue"),
    "C03": ("source/ai/AiResearch.cpp", "RES::chooseResearch"),
    "C04": ("source/ai/AiResearch.cpp", "RES::chooseResearch"),
    "C05": ("source/ai/AiResearch.cpp", "RES::chooseResearch"),
    "C06": ("source/ai/AiResearch.cpp", "RES::chooseResearch"),
    "D01": ("source/ai/AiEconomy.cpp", "ECON::walletGate"),
    "D02": ("source/ai/AiRooms.cpp", "ROOMS::bedWatch"),
    "D03": ("source/ai/AiRooms.cpp", "ROOMS::hatcheryWatch"),
    "D04": ("source/ai/AiCare.cpp", "CARE::slapWatch"),
    "D05": ("source/ai/AiCare.cpp", "CARE::possessDefender"),
    "D06": ("source/ai/AiCare.cpp", "CARE::idleToHall"),
    "D07": ("source/ai/AiCare.cpp", "CARE::moodPatrol"),
    "D08": ("source/ai/AiCare.cpp", "CARE::levelWatch"),
    "D09": ("source/ai/AiCare.cpp", "CARE::moodRelief"),
    "D10": ("source/ai/AiPrison.cpp", "PRIS::tortureStep"),
    "D11": ("source/ai/AiItems.cpp", "ITEMS::classNRows"),
    "E01": ("source/ai/AiEconomy.cpp", "ECON::summonWatch"),
    "E02": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "E03": ("source/ai/AiSpells.cpp", "SPELL::castHaste"),
    "E04": ("source/ai/AiSpells.cpp", "SPELL::castEye"),
    "E05": ("source/ai/AiSpells.cpp", "SPELL::castDefense"),
    "E06": ("source/ai/AiSpells.cpp", "SPELL::castStrength"),
    "E07": ("source/ai/AiSpells.cpp", "SPELL::castCallToWar"),
    "E08": ("source/ai/AiSpells.cpp", "SPELL::castSlow"),
    "E09": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "E10": ("source/ai/AiSpells.cpp", "SPELL::castWeak"),
    "E11": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "E12": ("source/ai/AiCare.cpp", "CARE::possessDefender"),
    "E13": ("source/ai/AiEconomy.cpp", "ECON::castCreateGold"),
    "E14": ("source/ai/AiItems.cpp", "ITEMS::classNRows"),
    "E15": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "E16": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "E17": ("source/ai/AiSpells.cpp", "SPELL::castDefector"),
    "E18": ("source/ai/AiSpells.cpp", "SPELL::castHexenHen"),
    "E19": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "F01": ("source/ai/AiTraps.cpp", "TRAP::trapLook"),
    "F02": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F03": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F04": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F05": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F06": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F07": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F08": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F09": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F10": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F11": ("source/ai/AiTraps.cpp", "TRAP::placeTrap"),
    "F12": ("source/ai/AiTraps.cpp", "TRAP::reloadGate"),
    "F13": ("source/ai/AiTraps.cpp", "TRAP::placeDoor"),
    "F14": ("source/ai/AiTraps.cpp", "TRAP::placeDoor"),
    "F15": ("source/ai/AiTraps.cpp", "TRAP::fortifyTunnel"),
    "G01": ("source/ai/AiRooms.cpp", "ROOMS::buildNext"),
    "G02": ("source/ai/AiPrison.cpp", "PRIS::tortureStep"),
    "G03": ("source/ai/AiItems.cpp", "ITEMS::classNRows"),
    "G04": ("source/ai/AiPrison.cpp", "PRIS::tortureStep"),
    "H01": ("source/ai/AiItems.cpp", "ITEMS::classNRows"),
    "H02": ("source/ai/AiRooms.cpp", "ROOMS::auditLab"),
    "H03": ("source/ai/AiItems.cpp", "ITEMS::useStoredSpecial"),
    "I01": ("source/ai/AiWar.cpp", "WAR::planDig"),
    "I02": ("source/ai/AiKnowledge.cpp", "AiKnowledge::planRoute"),
    "I03": ("source/ai/AiKnowledge.cpp", "AiKnowledge::scout"),
    "I04": ("source/ai/AiKnowledge.cpp", "AiKnowledge::estimateEnemy"),
    "I05": ("source/ai/AiKnowledge.cpp", "AiKnowledge::exploreTunnels"),
    "I06": ("source/ai/AiMind.cpp", "Mind::enqueue"),
    "J01": ("source/ai/AiWar.cpp", "WAR::defend"),
    "J02": ("source/ai/AiWar.cpp", "WAR::defend"),
    "J03": ("source/ai/AiWar.cpp", "WAR::defend"),
    "J04": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "J05": ("source/ai/AiWar.cpp", "WAR::heartGuard"),
    "J06": ("source/ai/AiWar.cpp", "WAR::defend"),
    "J07": ("source/ai/AiWar.cpp", "WAR::planAttack"),
    "J08": ("source/ai/AiWar.cpp", "WAR::restAfterFight"),
    "K01": ("source/ai/AiWar.cpp", "WAR::planAttack"),
    "K02": ("source/ai/AiWar.cpp", "WAR::planAttack"),
    "K03": ("source/ai/AiWar.cpp", "WAR::launch"),
    "K04": ("source/ai/AiWar.cpp", "WAR::launch"),
    "K05": ("source/ai/AiWar.cpp", "WAR::launch"),
    "K06": ("source/ai/AiSpells.cpp", "SPELL::chooseSpell"),
    "K07": ("source/ai/AiWar.cpp", "WAR::assaultStep"),
    "K08": ("source/ai/AiWar.cpp", "WAR::secondWave"),
    "K09": ("source/ai/AiWar.cpp", "WAR::assaultStep"),
    "K10": ("source/ai/AiWar.cpp", "WAR::endAssault"),
    "L01": ("source/ai/AiMind.cpp", "Mind::exec"),
    "L02": ("source/ai/AiMind.cpp", "Mind::rowClassAudit"),
    "L03": ("source/ai/AiKnowledge.cpp", "AiKnowledge::isKnown"),
    "L04": ("source/ai/AiActions.cpp", "ACTS::buildRoom"),
    "E20": ("source/ai/AiSpells.cpp", "SPELL::castChampion"),
    "H04": ("source/ai/AiItems.cpp", "ITEMS::buyForStrongest"),
}

# Return a function body, tracking nested braces.
def function_body(text, signature):
    match = re.search(r"\b" + re.escape(signature) + r"\s*\([^;]*?\)\s*(?:const\s*)?\{", text, re.S)
    assert match, f"missing function {signature}"
    start = match.end() - 1
    depth = 1
    end = start + 1
    while depth and end < len(text):
        depth += (text[end] == "{") - (text[end] == "}")
        end += 1
    assert depth == 0, f"unclosed function {signature}"
    return text[start:end]

PROBABILITY_KEYS = ['Pi', 'FocusFire', 'MistakeBaseRoutine', 'MistakeBaseRule', 'MistakeBaseComplex', 'MistakeBaseUnfamiliar', 'MistakeBaseRare', 'MistakeMin', 'MistakeMax', 'HealCastChance', 'PoorDefenceShuffleChance', 'RawHitFactor']

config = (repo / "config/ai.cfg").read_text(encoding="utf-8")
seen_probabilities = set()
for section in ("KeeperAILevels", "KeeperAI"):
    contents = config.split("[" + section + "]", 1)[1].split("[/" + section + "]", 1)[0]
    for line in contents.splitlines():
        fields = line.split("#", 1)[0].split()
        if fields and fields[0] in PROBABILITY_KEYS:
            assert fields[0] not in seen_probabilities, fields[0]
            seen_probabilities.add(fields[0])
            assert len(fields) == (6 if section == "KeeperAILevels" else 2), fields[0]
            assert all(0 < float(value) < 1 for value in fields[1:]), fields[0]
assert seen_probabilities == set(PROBABILITY_KEYS), "missing probability key"
row_section = config.split("[RowClasses]", 1)[1].split("[/RowClasses]", 1)[0]
row_ids = [line.split()[0] for line in row_section.splitlines() if line.strip() and not line.lstrip().startswith("#")]
assert len(row_ids) == len(set(row_ids)), "duplicate row class"
assert set(row_ids) == set(ANCHORS), "row classes differ from catalogue"
for row, (path, signature) in ANCHORS.items():
    text = (repo / path).read_text(encoding="utf-8")
    assert re.search(r"// AI row " + row + r"\b", function_body(text, signature)), f"{row}: missing in {signature}"
print("OK")
