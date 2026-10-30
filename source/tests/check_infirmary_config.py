"""Check the infirmary config contract without compiling or launching the game."""
from collections import Counter
from pathlib import Path
import re

repo = Path(__file__).resolve().parents[2]

# Read one configured scalar and reject missing or duplicate declarations.
def value(text, key):
    found = re.findall(r"^\s*" + re.escape(key) + r"\s+([^#\s]+)", text, re.M)
    assert len(found) == 1, (key, found)
    return float(found[0])

# Validate every fixed parameter and the roster-derived cot shares.
def main():
    rooms = (repo / "config/rooms.cfg").read_text(encoding="utf-8")
    expected = {"InfirmaryCostPerTile": 240, "InfirmaryHP": 50,
        "InfirmaryFullHealSeconds": 60, "DormitoryFullHealSeconds": 150,
        "InfirmaryCotShareSmall": 12, "InfirmaryCotShareMedium": 17,
        "InfirmaryCotShareLarge": 6, "InfirmaryMinRoomSide": 4,
        "InfirmaryAdmissionWageShare": .3, "InfirmaryMoodWageShare": .3,
        "InfirmaryManaPerWage": 2, "InfirmaryDischargeMinPercent": 40,
        "InfirmaryDischargeMaxPercent": 100, "InfirmaryDischargeStepPercent": 10,
        "InfirmaryDischargeDefaultPercent": 100, "InfirmaryMoodDefaultTurns": 30,
        "InfirmaryHealGlowTurns": 7, "InfirmaryShamanWalkMinSeconds": 8,
        "InfirmaryShamanWalkMaxSeconds": 15, "InfirmaryShamanPoseMinSeconds": 10,
        "InfirmaryShamanPoseMaxSeconds": 20, "InfirmaryShamanAnimationSeconds": 2}
    if "void Tile::addDirt(" in (repo / "source/entities/Tile.cpp").read_text(encoding="utf-8"):
        expected["InfirmaryDirtPerTreatment"] = 17.4
    for key, number in expected.items():
        assert value(rooms, key) == number, key
    assert value(rooms, "InfirmaryCostPerTile") == value(rooms, "PrisonCostPerTile")
    creatures = (repo / "config/creatures.cfg").read_text(encoding="utf-8")
    dimensions = Counter(tuple(sorted(map(int, row))) for row in
        re.findall(r"^\s*BedDim\s+(\d+)\s+(\d+)\s*$", creatures, re.M))
    assert dimensions == {(1, 1): 12, (1, 2): 17, (2, 2): 6}, dimensions
    skills = re.sub(r'#[^\n]*', '', (repo / "config/skills.cfg").read_text(encoding="utf-8"))
    assert value(skills.split("[Skills]", 1)[1].split("[/Skills]", 1)[0], "roomInfirmary") == 600
    assert re.search(r"^\s*roomInfirmary\s+HealTime\s+mul\s+1\.0\s+0\.8\s+0\.667\s*$", skills, re.M)
    manager = (repo / "source/game/SkillManager.cpp").read_text(encoding="utf-8")
    assert re.search(r'\{SkillType::roomInfirmary,\s*"HealTime",\s*ResearchBaseSource::rooms,\s*"InfirmaryFullHealSeconds",\s*""\}', manager)
    assert re.search(r'createSkill\(mSkills,\s*SkillType::roomInfirmary,\s*(?:std::vector<SkillType>)?\{SkillType::roomGuardRoom\}\)', manager)
    print("infirmary config: ok")

if __name__ == "__main__":
    main()
