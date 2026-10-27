"""Lava spa configuration: every Spa key of rooms.cfg has the value of the design, the keys that are derived from
existing game values still equal them, the research entry, the effect line and the base line are present, the spa
follows the tavern in the order the AI builds, and every key is documented in the header of its config file.

What is checked
  rooms.cfg [Rooms]       all Spa keys with their values, no Spa key without a design value, every key documented
  derived values          SpaMoodPerTurn = TemplePrayerReliefPerTurn (SpaMoodMax 300 and SpaMoodDecayPerTurn 0.4 are set by the owner),
                          SpaBathTurns = SpaMoodMax / SpaMoodPerTurn,
                          SpaRelaxTurns = HangoverTurns of global.cfg, SpaRelaxWorkFactor = 1 + SpaBathTurns / SpaRelaxTurns
                          (both to 4 places), SpaCostPerTile = CasinoCostPerTile, SpaHP = CasinoHP,
                          SpaDirtPerBath = 1.6154 / (0.557 x 9 / (SpaBathTurns + 1)) to 4 places
  skills.cfg              roomSpa 250 (tier II), the effect line roomSpa RelaxTime mul 1.0 1.2 1.4, both documented
  SkillManager.cpp        the research entry (parent tavern), the base line for RelaxTime and its effect text
  KeeperAI.cpp            the AI builds the spa directly after the tavern
  social-texts.cfg        the six texts of the post "relaxed"
  global.cfg              BeerPrice exists (the price of a bath is read from it, the spa has no own price key)

Calls (from the repository root):
  python source/tests/check_spa_config.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[2]


# Returns the text of a repository file.
def read(path):
    return (root / path).read_text(encoding='utf-8')


# Returns the key -> value words of the first block [tag]...[/tag] of a text (comments skipped).
def block_values(text, tag):
    match = re.search(r'^\[' + tag + r'\]\s*$(.*?)^\[/' + tag + r'\]', text, re.M | re.S)
    assert match is not None, 'block [' + tag + '] missing'
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            values.setdefault(words[0], words[1])
    return values


# Asserts that a comment line "# <key> " (header documentation) exists in the text.
def assert_documented(text, key, where):
    assert re.search(r'^#\s*' + re.escape(key) + r'\s', text, re.M), key + ' is not documented in the header of ' + where


rooms_cfg = read('config/rooms.cfg')
global_cfg = read('config/global.cfg')
skills_cfg = read('config/skills.cfg')
social_cfg = read('config/social-texts.cfg')
skill_manager = read('source/game/SkillManager.cpp')
keeper_ai = read('source/ai/KeeperAI.cpp')

rooms = block_values(rooms_cfg, 'Rooms')
tavern = block_values(global_cfg, 'Tavern')

# 1. Every Spa key with the value of the design (section 4 of the design)
SPA = {
    'SpaCostPerTile': '290', 'SpaHP': '40', 'SpaMinRoomSide': '4', 'SpaMoodMax': '300', 'SpaMoodPerTurn': '21',
    'SpaMoodDecayPerTurn': '0.4', 'SpaBathTurns': '14.2857', 'SpaRelaxTurns': '252', 'SpaRelaxWorkFactor': '1.0567',
    'SpaDirtPerBath': '4.925697143427089', 'SpaMudTrailTiles': '3', 'SpaAttendantActMinSeconds': '10',
    'SpaAttendantActMaxSeconds': '20', 'SpaAttendantCannonballMinSeconds': '120',
    'SpaAttendantCannonballMaxSeconds': '180', 'SpaCannonballChance': '0.25', 'SpaJumpTurns': '2',
    'SpaJumpHeight': '1.0',
}
found = sorted(k for k in rooms if k.startswith('Spa'))
assert found == sorted(SPA), 'the Spa keys of rooms.cfg are not the design keys: ' + ', '.join(found)
for key, value in SPA.items():
    assert float(rooms[key]) == float(value), key + ' is ' + rooms[key] + ', the design says ' + value
    if key != 'SpaHP':
        assert_documented(rooms_cfg, key, 'rooms.cfg')
# The tile hit points are documented by the generic <RoomName>HP line and named in the SpaCostPerTile line
assert re.search(r'^#\s*<RoomName>HP\s', rooms_cfg, re.M) and 'the tile hit points are SpaHP' in rooms_cfg
# The price of a bath has no own key: the beer price is read
assert 'SpaBathPrice' not in rooms and 'SpaPrice' not in rooms, 'the bath costs BeerPrice, no own price key'
assert float(tavern['BeerPrice']) == 5.0, 'BeerPrice is 5 gold'

# 2. The values that derive from existing keys still equal them
assert float(rooms['SpaMoodPerTurn']) == float(rooms['TemplePrayerReliefPerTurn'])
bath_turns = float(rooms['SpaMoodMax']) / float(rooms['SpaMoodPerTurn'])
assert round(bath_turns, 4) == float(rooms['SpaBathTurns']), 'SpaBathTurns = SpaMoodMax / SpaMoodPerTurn'
assert float(rooms['SpaRelaxTurns']) == float(tavern['HangoverTurns']), 'SpaRelaxTurns = HangoverTurns'
factor = 1.0 + float(rooms['SpaBathTurns']) / float(rooms['SpaRelaxTurns'])
assert round(factor, 4) == float(rooms['SpaRelaxWorkFactor']), 'SpaRelaxWorkFactor = 1 + SpaBathTurns / SpaRelaxTurns'
assert float(rooms['SpaCostPerTile']) == float(rooms['CasinoCostPerTile'])
assert float(rooms['SpaHP']) == float(rooms['CasinoHP'])
# The dirt formula: class high 1.6154, occupancy 0.557, nine pool spots of a 25 tile room, one use per bath turn plus one
use_rate = 9.0 / (float(rooms['SpaBathTurns']) + 1.0)
dirt = 1.6154 / (0.557 * use_rate)
assert round(dirt, 4) == round(float(rooms['SpaDirtPerBath']), 4), 'SpaDirtPerBath by the dirt formula: ' + str(round(dirt, 4))
# The jump timings are ordered ranges
assert float(rooms['SpaAttendantActMinSeconds']) <= float(rooms['SpaAttendantActMaxSeconds'])
assert float(rooms['SpaAttendantCannonballMinSeconds']) <= float(rooms['SpaAttendantCannonballMaxSeconds'])
assert 0.0 <= float(rooms['SpaCannonballChance']) <= 1.0

# 3. Research: entry and cost in skills.cfg, the effect line, the entry of the tree and the base line
skills = block_values(skills_cfg, 'Skills')
assert skills.get('roomSpa') == '250', 'roomSpa costs 250 (tier II)'
assert skills['roomSpa'] == skills['roomCasino'], 'tier II rooms cost the same'
assert_documented(skills_cfg, 'roomSpa', 'skills.cfg')
effect = re.search(r'^\s*roomSpa\s+RelaxTime\s+mul\s+(\S+)\s+(\S+)\s+(\S+)\s*$', skills_cfg, re.M)
assert effect is not None and effect.groups() == ('1.0', '1.2', '1.4'), 'effect line roomSpa RelaxTime mul 1.0 1.2 1.4'
assert re.search(r'^#\s+RelaxTime\b', skills_cfg, re.M), 'RelaxTime is documented in the header of skills.cfg'
relax_levels = [float(rooms['SpaRelaxTurns']) * float(g) for g in effect.groups()]
assert [round(v, 1) for v in relax_levels] == [252.0, 302.4, 352.8], relax_levels
assert re.search(r'createSkill\(mSkills, SkillType::roomSpa, std::vector<SkillType>\{SkillType::roomTavern\}\)', skill_manager)
assert re.search(r'new SkillDefRoom\(TREE_PREFIX_ROOMS, "SpaButton", skill, 2, RoomType::spa\)', skill_manager)
assert '{SkillType::roomSpa, "RelaxTime", ResearchBaseSource::rooms, "SpaRelaxTurns", ""}' in skill_manager
assert 'texts[ResearchEffect::RelaxTime] = "Relaxation time";' in skill_manager
assert 'static const std::string RelaxTime = "RelaxTime";' in read('source/game/SkillManager.h')
# The spa button sits directly after the beer button of the tier II block
assert skill_manager.index('"BeerButton"') < skill_manager.index('"SpaButton"') < skill_manager.index('// Rooms tab, tier III')

# 4. The AI builds the spa directly after the tavern
wanted = re.search(r'wantedBuildings = \{(.*?)\};', keeper_ai, re.S).group(1)
order = re.findall(r'RoomType::(\w+)', wanted)
assert order.index('spa') == order.index('tavern') + 1, 'the spa follows the tavern in wantedBuildings: ' + ', '.join(order)

# 5. The six texts of the post "relaxed"
texts = re.findall(r'^Post\trelaxed\t\*\t(.+)$', social_cfg, re.M)
assert texts == [
    'Mud bath done. I am a new monster.', 'The pool attendant whistled at me. Worth it.',
    'Hot mud, warm heart. Back to work.', 'Jumped from the board. Best splash of the week.',
    'My hangover drowned in the mud.', 'Relaxed. Do not talk to me about the payday.'], texts

print('spa config ok')
