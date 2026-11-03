"""Tavern and thirst configuration: every key of the [Tavern] block of global.cfg has the value of the design, the
tavern keys of rooms.cfg and skills.cfg match the hatchery and the research table, every creature type carries the
thirst values that follow from its hunger values, and everything is documented in the header of its config file.

What is checked
  global.cfg [Tavern]      all keys with their values, no key without a design value, every key documented
  derived values           BeerPrice = cheapest FeeBase / 10, GameWinnerXp = TrainHallXpPerAttack,
                           TavernCostPerTile = HatcheryCostPerTile, TavernHP = HatcheryHP,
                           TavernDirtPerDrink = 0.8077 / (0.557 x 25 / (DrinkTurns + 1)) rounded to 4 places
  creatures.cfg            every type has a Casino, an Arena and a Tavern affinity line and a Hunger mood line is
                           optional. A type WITH a Hunger mood line has the Thirst mood line with the same two numbers,
                           ThirstGrowth/Turn = HungerGrowth/Turn and the Tavern likeness of its Casino line (efficiency
                           1.0). A type WITHOUT a Hunger mood line has no thirst at all: ThirstGrowth/Turn is an
                           explicit 0, no Thirst mood line and Tavern likeness 0 (Mario, 2026-10-25: no hunger, no thirst)
  skills.cfg               roomTavern 100, tavernBeer 250, FreeLevelOne has roomTavern, the one effect line of the
                           portal cooldown (1.0 / 0.9 / 0.8), both keys documented
  rooms.cfg                TavernCostPerTile, TavernHP, TavernDirtPerDrink documented
  furniture                one table per eight tiles (one table tile per four, a table covers two) and one keg per
                           six; a model of the spread of RoomTavern::updateActiveSpots on closed rectangular rooms from
                           3x3 to 8x8 tiles: every table covers two free tiles of the room, no keg stands next to another
                           keg or away from a wall, no tile carries two pieces, the maxima hold, every room with a 3x3
                           block gets a table, and from 5x5 on at least two tables have free floor on both bench sides

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
    'ThirstSeek': '80', 'UrgeFromBeer': '15', 'UrgeFromWater': '5', 'BeerPrice': '5', 'BeerMood': '100',
    'BeerMoodTurns': '168', 'NoCoinMood': '-33.3333', 'NoCoinMoodTurns': '168', 'DrinkTurns': '4', 'NextDrinkPercent': '50',
    'MaxDrinksPerVisit': '5', 'DrunkPerBeer': '25', 'DrunkDecayPerTurn': '0.5', 'StaggerAt': '50',
    'StaggerSpeedFactor': '0.5', 'VomitAt': '75', 'HangoverAt': '50', 'HangoverTurns': '252',
    'HangoverWorkFactor': '0.5', 'HangoverMood': '-66.6667', 'GameChancePercent': '50', 'GameTurns': '8',
    'GameWinnerMood': '133.3333', 'GameLoserMood': '-66.6667', 'GameSpectatorMood': '66.6667', 'GameSpectatorRadius': '2',
    'GameUnderdogBasePercent': '50', 'GameUnderdogPerLevel': '2.5', 'GameUnderdogMinPercent': '5',
    'GameUnderdogMoodPerLevel': '33.3333', 'GameUnderdogMoodMax': '333.3333', 'SlapDamage': '10', 'SlapCritBasePercent': '10',
    'SlapCritPerLevel': '0.25', 'SlapDuelLoseBelowHp': '30', 'DuelKoTurns': '42', 'GameWinnerXp': '2.86',
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
assert float(tavern['GameWinnerXp']) == float(rooms['TrainHallXpPerAttack']), 'GameWinnerXp must equal TrainHallXpPerAttack'
expected_dirt = round(0.8077 / (0.557 * 25 / (float(tavern['DrinkTurns']) + 1)), 4)
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

# Furniture density follows the room area: one table tile per four tiles (a table covers two, so one table per eight)
# and one keg per six.
room_cpp = read('source/rooms/RoomTavern.cpp')
assert 'const size_t tableLimit = orderedTiles.size() / TAVERN_TILES_PER_TABLE;' in room_cpp
assert 'const size_t kegLimit = orderedTiles.size() / TAVERN_TILES_PER_KEG;' in room_cpp
assert 'const size_t TAVERN_TILES_PER_KEG = 6;' in room_cpp and 'const size_t TAVERN_TILES_PER_TABLE = 8;' in room_cpp
# The model below follows these lines of the placement; a change of them needs a change of the model.
for token in ('const double TABLE_ANGLES[] = { 0.0, 90.0 };', 'if(!wall || adjacentKeg)',
              'if((benchesFree && !bestBenchesFree) || ((benchesFree == bestBenchesFree) && (distance > bestDistance)))',
              'const int32_t acrossX = second.getY() - tile.getY();', 'const int32_t acrossY = tile.getX() - second.getX();',
              'if(isBenchBehindWall(gameMap, *tile, angle, 0) && isBenchBehindWall(gameMap, *tile, angle, 1))',
              'second = tableSecondTile(gameMap, *tile, angle);', 'furnitureTiles.push_back(bestSecond);',
              'std::sort(orderedTiles.begin(), orderedTiles.end(), Room::compareTile);'):
    assert token in room_cpp, token


# The benches of a table that have a wall (a tile outside the room) behind them, next to either of its two tiles: bench 0 lies
# on the +x side of the table turned by its angle, bench 1 on the opposite side. Nobody sits on such a bench.
def walled_benches(inside, tile, second):
    across = (second[1] - tile[1], tile[0] - second[0])
    return [bench for bench, side in ((0, 1), (1, -1))
            if any((t[0] + side * across[0], t[1] + side * across[1]) not in inside for t in (tile, second))]


# A model of the spread of the furniture of RoomTavern::updateActiveSpots for a closed rectangular room (every tile around
# it is a wall). Returns the counter tile, the kegs and the tables as (tile, second tile, both bench sides free). A table
# with a wall behind both of its benches is not placed; a bench with a wall behind it stays empty (see walled_benches).
def spread(width, height):
    tiles = sorted((x, y) for x in range(width) for y in range(height))
    inside = set(tiles)
    counter = tiles[0]
    furniture = [counter]
    kegs = []
    tables = []
    for kind, limit in (('keg', len(tiles) // 6), ('table', len(tiles) // 8)):
        for _ in range(limit):
            best = None
            best_distance = -1
            best_free = False
            for tile in tiles:
                if tile in furniture:
                    continue
                # A table points along y (0 degrees: second tile at y + 1) or along -x (90 degrees: at x - 1)
                for second in ((None,) if kind == 'keg' else ((tile[0], tile[1] + 1), (tile[0] - 1, tile[1]))):
                    free = False
                    if kind == 'keg':
                        neighbours = ((tile[0], tile[1] + 1), (tile[0], tile[1] - 1), (tile[0] - 1, tile[1]), (tile[0] + 1, tile[1]))
                        if all(n in inside for n in neighbours) or any(n in kegs for n in neighbours):
                            continue
                    else:
                        if second not in inside or second in furniture:
                            continue
                        # Across the table, where the benches stand: both sides of both tiles are free floor of the room
                        across = (second[1] - tile[1], tile[0] - second[0])
                        if len(walled_benches(inside, tile, second)) == 2:
                            continue
                        free = all((t[0] + side * across[0], t[1] + side * across[1]) in inside and
                                   (t[0] + side * across[0], t[1] + side * across[1]) not in furniture
                                   for t in (tile, second) for side in (1, -1))
                    pieces = (tile,) if second is None else (tile, second)
                    distance = min((a[0] - f[0]) ** 2 + (a[1] - f[1]) ** 2 for a in pieces for f in furniture)
                    if (free and not best_free) or (free == best_free and distance > best_distance):
                        best, best_distance, best_free = (tile, second), distance, free
            if best is None:
                break
            if kind == 'keg':
                kegs.append(best[0])
                furniture.append(best[0])
            else:
                tables.append(best + (best_free,))
                furniture.extend(best)
    return counter, kegs, tables


for width in range(3, 9):
    for height in range(3, 9):
        counter, kegs, tables = spread(width, height)
        inside = {(x, y) for x in range(width) for y in range(height)}
        taken = [counter] + kegs + [t for table in tables for t in table[:2]]
        assert len(taken) == len(set(taken)) and set(taken) <= inside, (width, height, 'a tile carries two pieces')
        assert len(kegs) <= width * height // 6 and len(tables) <= width * height // 8, (width, height, 'the maxima hold')
        assert tables, (width, height, 'a room with a 3x3 block gets a table')
        if min(width, height) >= 5:
            assert sum(1 for table in tables if table[2]) >= min(2, len(tables)), (width, height, 'two tables have free floor at both benches')
        for first, second, _ in tables:
            assert abs(first[0] - second[0]) + abs(first[1] - second[1]) == 1, (width, height, 'a table covers two neighbouring tiles')
            assert len(walled_benches(inside, first, second)) < 2, (width, height, 'a table has a bench with no wall behind it')
        # Every room with a 3x3 block keeps at least four usable places (a bench without a wall behind it)
        assert sum(4 * (2 - len(walled_benches(inside, first, second))) for first, second, _ in tables) >= 4, (width, height, 'places')
        for keg in kegs:
            assert any(n not in inside for n in ((keg[0] + 1, keg[1]), (keg[0] - 1, keg[1]), (keg[0], keg[1] + 1), (keg[0], keg[1] - 1))), \
                (width, height, 'a keg stands at a wall')
            assert not any(abs(keg[0] - other[0]) + abs(keg[1] - other[1]) == 1 for other in kegs), (width, height, 'two kegs side by side')

print('tavern config ok')
