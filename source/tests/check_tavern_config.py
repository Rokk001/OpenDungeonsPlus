"""Tavern and thirst configuration: every key of the [Tavern] block of global.cfg has the value of the design, the
tavern keys of rooms.cfg and skills.cfg match the hatchery and the research table, every creature type carries the
thirst values that follow from its hunger values, and everything is documented in the header of its config file.

What is checked
  global.cfg [Tavern]      all keys with their values, no key without a design value, every key documented
  derived values           BeerPrice = cheapest FeeBase / 10, GameWinnerXp = TrainHallXpPerAttack,
                           TavernCostPerTile = HatcheryCostPerTile, TavernHP = HatcheryHP,
                           TavernDirtPerDrink = 0.8077 / (0.62 x 25 / (DrinkTurns + 1)) rounded to 4 places
  creatures.cfg            every type has a Casino, an Arena and a Tavern affinity line and a Hunger mood line is
                           optional. A type WITH a Hunger mood line has the Thirst mood line with the same two numbers,
                           ThirstGrowth/Turn = HungerGrowth/Turn and the Tavern likeness of its Casino line (efficiency
                           1.0). A type WITHOUT a Hunger mood line has no thirst at all: ThirstGrowth/Turn is an
                           explicit 0, no Thirst mood line and Tavern likeness 0 (Mario, 2026-10-25: no hunger, no thirst)
  skills.cfg               roomTavern 100, tavernBeer 250, FreeLevelOne has roomTavern, the one effect line of the
                           portal cooldown (1.0 / 0.9 / 0.8), both keys documented
  rooms.cfg                TavernCostPerTile, TavernHP, TavernDirtPerDrink documented

Calls (from the repository root):
  python source/tests/check_tavern_config.py            plain file checks, no compiler, no game
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


# Returns the lines of an inner block [tag]...[/tag] of a creature block as lists of words (comments skipped).
def inner_lines(block, tag):
    match = re.search(r'^\s*\[' + tag + r'\]\s*$(.*?)^\s*\[/' + tag + r'\]', block, re.M | re.S)
    if match is None:
        return {}
    lines = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            lines.setdefault(words[0], words[1:])
    return lines


global_cfg = read('config/global.cfg')
rooms_cfg = read('config/rooms.cfg')
creatures_cfg = read('config/creatures.cfg')
skills_cfg = read('config/skills.cfg')

# 1. Every key of the [Tavern] block with the value of the design (sections 4 and 5 of the design)
TAVERN = {
    'ThirstSeek': '80', 'UrgeFromBeer': '15', 'UrgeFromWater': '5', 'BeerPrice': '5', 'BeerMood': '15',
    'BeerMoodTurns': '168', 'NoCoinMood': '-5', 'NoCoinMoodTurns': '168', 'DrinkTurns': '4', 'NextDrinkPercent': '50',
    'MaxDrinksPerVisit': '5', 'DrunkPerBeer': '25', 'DrunkDecayPerTurn': '0.5', 'StaggerAt': '50',
    'StaggerSpeedFactor': '0.5', 'VomitAt': '75', 'HangoverAt': '50', 'HangoverTurns': '252',
    'HangoverWorkFactor': '0.5', 'HangoverMood': '-10', 'GameChancePercent': '50', 'GameTurns': '8',
    'GameWinnerMood': '20', 'GameLoserMood': '-10', 'GameSpectatorMood': '10', 'GameSpectatorRadius': '2',
    'GameUnderdogBasePercent': '50', 'GameUnderdogPerLevel': '2.5', 'GameUnderdogMinPercent': '5',
    'GameUnderdogMoodPerLevel': '5', 'GameUnderdogMoodMax': '50', 'SlapDamage': '10', 'SlapCritBasePercent': '10',
    'SlapCritPerLevel': '0.25', 'SlapDuelLoseBelowHp': '30', 'DuelKoTurns': '42', 'GameWinnerXp': '5',
    'TavernNoticeSeconds': '60',
}
tavern = block_values(global_cfg, 'Tavern')
for key, value in TAVERN.items():
    assert tavern.get(key) == value, '[Tavern] ' + key + ' is ' + str(tavern.get(key)) + ', expected ' + value
    assert_documented(global_cfg, key, 'global.cfg')
extra = set(tavern) - set(TAVERN)
assert not extra, '[Tavern] keys without a design value: ' + ', '.join(sorted(extra))
# The turn values are the seconds of the design times the 1.4 turns per second
for key, seconds in (('BeerMoodTurns', 120), ('NoCoinMoodTurns', 120), ('HangoverTurns', 180), ('DuelKoTurns', 30)):
    assert round(seconds * 1.4) == float(tavern[key]), key + ' must be ' + str(seconds) + ' s x 1.4 turns per second'

# 2. Values derived from other keys
rooms = block_values(rooms_cfg, 'Rooms')
assert rooms.get('TavernCostPerTile') == rooms.get('HatcheryCostPerTile') == '110', 'TavernCostPerTile must equal HatcheryCostPerTile'
hp_values = {}
for line in rooms_cfg.splitlines():
    words = line.split()
    if len(words) == 2 and words[0] in ('TavernHP', 'HatcheryHP'):
        hp_values[words[0]] = words[1]
assert hp_values.get('TavernHP') == hp_values.get('HatcheryHP') == '30', 'TavernHP must equal HatcheryHP'
# A type without a wage (FeeBase 0) does not set the price: the cheapest creature that is paid does
fee_bases = [float(v) for v in re.findall(r'^\s*FeeBase\s+(\S+)', creatures_cfg, re.M) if float(v) > 0]
assert len(fee_bases) >= 30, 'FeeBase lines missing'
assert float(tavern['BeerPrice']) == min(fee_bases) / 10, 'BeerPrice must be the smallest FeeBase / 10'
assert tavern['GameWinnerXp'] == str(int(float(rooms['TrainHallXpPerAttack']))), 'GameWinnerXp must equal TrainHallXpPerAttack'
expected_dirt = round(0.8077 / (0.62 * 25 / (float(tavern['DrinkTurns']) + 1)), 4)
assert float(rooms['TavernDirtPerDrink']) == expected_dirt, 'TavernDirtPerDrink is ' + rooms['TavernDirtPerDrink'] + ', expected ' + str(expected_dirt)
for key in ('TavernCostPerTile', 'TavernDirtPerDrink'):
    assert_documented(rooms_cfg, key, 'rooms.cfg')
# TavernHP is named in the comment of TavernCostPerTile, like the other room hit points are named next to their cost
assert re.search(r'^#.*TavernHP', rooms_cfg, re.M), 'TavernHP is not documented in the header of rooms.cfg'

# 3. Per creature type
seen = []
with_hunger = []
without_hunger = []
for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures_cfg, re.S):
    fields = {}
    for line in block.splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            fields.setdefault(words[0], words[1])
    name = fields.get('Name')
    if name is None:
        continue
    seen.append(name)
    moods = inner_lines(block, 'MoodModifiers')
    affinities = inner_lines(block, 'RoomAffinity')
    for room in ('Casino', 'Arena', 'Tavern'):
        assert room in affinities and len(affinities[room]) >= 2, name + ': room affinity line ' + room + ' missing'
    assert 'ThirstGrowth/Turn' in fields, name + ': ThirstGrowth/Turn missing (an explicit value is written for every type)'
    if 'Hunger' in moods:
        with_hunger.append(name)
        assert moods.get('Thirst') == moods['Hunger'], name + ': Thirst mood line must equal the Hunger line'
        assert fields['ThirstGrowth/Turn'] == fields['HungerGrowth/Turn'], name + ': ThirstGrowth/Turn must equal HungerGrowth/Turn'
        assert affinities['Tavern'][0] == affinities['Casino'][0], name + ': Tavern likeness must equal the Casino likeness'
        assert affinities['Tavern'][1] == '1.0', name + ': Tavern efficiency must be 1.0'
    else:
        # No hunger, no thirst: explicit 0 growth, no mood line, never visits a tavern
        without_hunger.append(name)
        assert 'Thirst' not in moods, name + ' has no Hunger mood line, so it must not have a Thirst mood line'
        assert float(fields['ThirstGrowth/Turn']) == 0.0, name + ': ThirstGrowth/Turn must be an explicit 0 without a Hunger line'
        assert float(affinities['Tavern'][0]) == 0.0, name + ': Tavern likeness must be 0 without a Hunger line'
assert len(seen) == 35 and len(set(seen)) == 35, 'expected 35 creature types, found ' + str(len(seen))
assert sorted(without_hunger) == ['Champion', 'DwarfWorker', 'Kobold', 'Skeleton'], 'types without a Hunger line: ' + ', '.join(without_hunger)
assert_documented(creatures_cfg, 'ThirstGrowth/Turn', 'creatures.cfg')
assert re.search(r'^#.*\bThirst\b.*mood', creatures_cfg, re.M | re.I) or 'Thirst line' in creatures_cfg, 'creatures.cfg must document the Thirst mood line'
assert re.search(r'^#.*Tavern', creatures_cfg, re.M), 'creatures.cfg must document the Tavern affinity'
assert re.search(r'^#.*no hunger.*no thirst|^#.*without (a )?Hunger', creatures_cfg, re.M | re.I), \
    'creatures.cfg must document that a type without hunger has no thirst'

# 4. Research: costs, the free start entry and the one effect line of the portal cooldown
skills = block_values(skills_cfg, 'Skills')
assert skills.get('roomTavern') == '100' and skills.get('tavernBeer') == '250', 'skills.cfg costs of roomTavern / tavernBeer'
assert skills['roomTavern'] == skills['roomHatchery'], 'the tavern costs like the hatchery'
free_block = re.search(r'^\[FreeLevelOne\]\s*$(.*?)^\[/FreeLevelOne\]', skills_cfg, re.M | re.S)
assert free_block is not None
free = [w.split()[0] for w in free_block.group(1).splitlines() if w.split() and not w.split()[0].startswith('#')]
assert 'roomTavern' in free and len(free) == 6, 'FreeLevelOne must hold 6 entries including roomTavern: ' + str(free)
effects = block_values(skills_cfg, 'ResearchEffects')
assert effects.get('tavernBeer') == 'PortalCooldown', 'ResearchEffects: tavernBeer PortalCooldown missing'
effect_lines = [re.split(r'\s+', line.strip()) for line in skills_cfg.splitlines() if re.match(r'^\s*tavernBeer\s', line)]
beer_effect_lines = [l for l in effect_lines if len(l) >= 3 and l[1] == 'PortalCooldown']
assert len(beer_effect_lines) == 1, 'exactly one tavernBeer effect line is allowed'
assert beer_effect_lines[0][2:] == ['mul', '1.0', '0.9', '0.8'], 'tavernBeer effect line must be: mul 1.0 0.9 0.8'
assert not [l for l in effect_lines if l[0] == 'roomTavern'], 'roomTavern has no effect line'
for key in ('roomTavern', 'tavernBeer'):
    assert_documented(skills_cfg, key, 'skills.cfg')

print('tavern config ok')
