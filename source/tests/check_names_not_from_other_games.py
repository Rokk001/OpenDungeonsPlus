"""Check player-facing item, potion, herb, effect, room and research names against the supplied fixture."""
import re
from check_items_cfg import ROOT, blocks, read, value


def main():
    """Report every whole-word, case-insensitive fixture match without modifying the fixture."""
    fixture = ROOT / "source/tests/fixtures/other_game_terms.txt"
    terms = [line.strip() for line in fixture.read_text(encoding="utf-8").splitlines()
             if line.strip() and not line.lstrip().startswith("#")]
    assert terms, "the supplied name fixture is required"
    displays, counts = [], []
    for text, tag in ((read("config/items.cfg"), "Quality"), (read("config/potions.cfg"), "Potion"),
                      (read("config/potions.cfg"), "Herb")):
        names = [value(block, "Display") for block in blocks(text, tag)]
        counts.append(len(names))
        displays.extend(names)
    effect_table = read("source/entities/ItemEffects.cpp").split("EFFECT_NAMES[]", 1)[1].split("};", 1)[0]
    effect_names = re.findall(r'\{"[^"]+",\s*"([^"]+)"\}', effect_table)
    counts.append(len(effect_names))
    displays.extend(effect_names)
    room_names = []
    for name in ("RoomMerchant", "RoomHerbGarden", "RoomAlchemyLab"):
        source = read("source/rooms/" + name + ".cpp")
        readable = re.findall(r'getNameReadable\(\)[\s\S]*?\{([\s\S]*?)\}', source)
        assert len(readable) == 1, "missing or ambiguous room display getter: " + name
        body = readable[0]
        returned = re.search(r'return\s+(\w+)\s*;', body)
        assert returned, "missing readable return: " + name
        literal = re.search(r'const std::string\s+' + returned[1] + r'\s*=\s*"([^"]+)"', body)
        if literal is None:
            literal = re.search(r'const std::string\s+' + returned[1] + r'\s*=\s*"([^"]+)"', source)
        assert literal, "unresolved readable room constant: " + name
        room_names.append(literal[1])
    assert set(room_names) == {"Merchant room", "Herb garden", "Alchemy lab"}
    counts.append(len(room_names))
    displays.extend(room_names)
    research = read("source/game/SkillType.cpp").split("std::string skillTypeToPlayerVisibleString(", 1)[1]
    research = research.split("bool isRewardSkill(", 1)[0]
    research_names = []
    for skill in ("roomMerchant", "roomHerbGarden", "roomAlchemyLab", "trapFineTools", "trapMasterTools", "spellSunthornCultivation"):
        found = re.search(r'case SkillType::' + skill + r':\s*return "([^"]+)"', research)
        assert found, "missing research display: " + skill
        research_names.append(found[1])
    assert set(research_names) == {"The Merchant Room", "The Herb Garden", "The Alchemy Lab", "Fine Tools", "Master Tools", "Sunthorn Cultivation"}
    counts.append(len(research_names))
    displays.extend(research_names)
    assert counts == [551, 29, 4, 49, 3, 6], "incomplete player-name extraction: " + repr(counts)
    assert len(displays) == 642
    hits = [(display, term) for display in displays for term in terms
            if re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", display, re.I)]
    assert not hits, "forbidden whole-word name matches: " + repr(hits)
    print("player-facing names: fixture word-boundary check passed (%d names)" % len(displays))


if __name__ == "__main__":
    main()
