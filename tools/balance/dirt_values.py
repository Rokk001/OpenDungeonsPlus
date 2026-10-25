#!/usr/bin/env python3
"""Dirt per room use: recomputes the DirtPer... keys of config/rooms.cfg from the reference dungeon.

Reference dungeon: one 25-tile room (9 centre spots) of every cleanable room type, every spot occupied
OCCUPANCY of the time (10 creatures eating for the hatchery, 25 hens), and one quarter of one worker's time
(REFERENCE_CLEANING_SHARE of the dirt a worker removes per turn: ClaimRate x 100 x CleanRateFactor) keeps the whole
dungeon in balance, so cleaning stays a side job.

Formula, per room R with class weight f_R (high 1.0, medium 0.5, low 0.25; sumF = sum over the cleanable rooms):
  capacity = ClaimRate x 100 x CleanRateFactor x REFERENCE_CLEANING_SHARE
  P_R      = capacity x f_R / sumF, rounded to 4 decimals (the hatchery halves, hens and meals, use half of the
             unrounded high-class production)
  DirtPerUse_R = P_R / (occupancy_R x useRate_R), rounded to 5 and then half up to 4 decimals
Prison and torture chamber are not cleaned by workers: they use f = 1.0 with the same capacity but are not part of sumF.
CombatDirtPerHit is the arena value, TrailDirtPerTile the dormitory value.

Usage (from the repository root):
  python tools/balance/dirt_values.py            print the table
  python tools/balance/dirt_values.py --check    recompute from the config keys, assert the result is the expected
                                                 table (EXPECTED) and that config/rooms.cfg and config/global.cfg
                                                 hold exactly these values; exit code 1 on any difference
"""

import argparse
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]

# Share of one worker's time that keeps the reference dungeon in balance
REFERENCE_CLEANING_SHARE = 0.25
# Working share of a occupied spot in the reference dungeon
OCCUPANCY = 0.62
# Occupancy used for animals, meals and prisoners (always present)
FULL_OCCUPANCY = 1.0
# Centre spots of a 25-tile room
SPOTS = 9
# Tiles of the reference room
ROOM_TILES = 25
# Hens in the reference hatchery
HEN_COUNT = 25
# Hunger growth per turn of the reference creatures
REFERENCE_HUNGER_GROWTH = 0.1
# Prisoner turns per turn of a 25-tile prison (inner tiles + 1)
PRISON_PRISONER_TURNS = 10
# Mean length of one torture session in turns (use rate = SPOTS / this)
TORTURE_SESSION_TURNS = 5
# Class weights
HIGH = 1.0
MEDIUM = 0.5
LOW = 0.25

# The table of the plan (the values the config must hold)
EXPECTED = {
    'WorkshopDirtPerWork': '1.5922',
    'ArenaDirtPerHit': '1.5922',
    'ToiletDirtPerUse': '0.5211',
    'HatcheryDirtPerHenTurn': '0.0323',
    'HatcheryDirtPerMeal': '8.0769',
    'TrainHallDirtPerHit': '0.7961',
    'CasinoDirtPerWork': '0.7961',
    'DormitoryDirtPerSleepTurn': '0.1448',
    'GuardRoomDirtPerDuty': '1.2304',
    'LibraryDirtPerWork': '0.3980',
    'TempleDirtPerPrayerTurn': '0.0724',
    'PrisonDirtPerPrisonerTurn': '0.1615',
    'TortureDirtPerSession': '1.4475',
}


# Rounds half up to the given number of decimals (decimal arithmetic on the shortest repr of the float).
def round_half_up(value, decimals):
    return Decimal(repr(float(value))).quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


# Returns the text of the first block "[tag] ... [/tag]" of a config file as a dict key -> first value word.
def read_block(path, tag):
    text = path.read_text(encoding='utf-8')
    match = re.search(r'^\[' + re.escape(tag) + r'\]\s*$(.*?)^\[/' + re.escape(tag) + r'\]', text, re.M | re.S)
    if match is None:
        raise SystemExit(str(path) + ': block [' + tag + '] missing')
    values = {}
    for line in match.group(1).splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            values.setdefault(words[0], words[1])
    return values


# Returns the value of a key in the whole file (first occurrence) as a string.
def read_key(path, key):
    for line in path.read_text(encoding='utf-8').splitlines():
        words = line.split()
        if len(words) >= 2 and words[0] == key:
            return words[1]
    raise SystemExit(str(path) + ': key ' + key + ' missing')


# Returns the ClaimRate of the Kobold (the cleaning worker of the reference) from creatures.cfg.
def read_claim_rate():
    text = (ROOT / 'config' / 'creatures.cfg').read_text(encoding='utf-8')
    match = re.search(r'\[Creature\]\s*Name\s+Kobold\b.*?ClaimRate\s+([0-9.]+)', text, re.S)
    if match is None:
        raise SystemExit('creatures.cfg: Kobold ClaimRate missing')
    return float(match.group(1))


# Returns the mean of the min and max cooldown keys of a room (turns idle between two uses) as a float.
def read_cooldown_mean(prefix):
    path = ROOT / 'config' / 'rooms.cfg'
    low = float(read_key(path, prefix + 'Min'))
    high = float(read_key(path, prefix + 'Max'))
    return (low + high) / 2.0


# Computes the table: returns a dict key -> Decimal (4 decimals) from the config keys and the reference constants.
def compute():
    rooms_cfg = ROOT / 'config' / 'rooms.cfg'
    global_dirt = read_block(ROOT / 'config' / 'global.cfg', 'Dirt')
    clean_rate = read_claim_rate() * 100.0 * float(global_dirt['CleanRateFactor'])
    capacity = clean_rate * REFERENCE_CLEANING_SHARE
    toilet_turns = float(global_dirt['ToiletUseTurns'])
    hunger_per_meal = float(read_key(rooms_cfg, 'HatcheryHungerPerChicken'))
    creatures = float(read_key(ROOT / 'config' / 'global.cfg', 'MaxCreaturesPerSeatDefault'))
    meals_per_turn = creatures * REFERENCE_HUNGER_GROWTH / hunger_per_meal

    def cooldown_rate(prefix):
        return SPOTS / (1.0 + read_cooldown_mean(prefix))

    # key: (class weight, use rate at full occupancy per turn, occupancy, counts in sumF); the arena has no cooldown
    # keys of its own, the plan gives it the use rate of a workshop (a blow every 5.5 turns per spot)
    rooms = [
        ('WorkshopDirtPerWork', HIGH, cooldown_rate('WorkshopCooldownWork'), OCCUPANCY, True),
        ('ArenaDirtPerHit', HIGH, cooldown_rate('WorkshopCooldownWork'), OCCUPANCY, True),
        ('ToiletDirtPerUse', HIGH, ROOM_TILES / (toilet_turns + 1.0), OCCUPANCY, True),
        ('HatcheryDirtPerHenTurn', None, float(HEN_COUNT), FULL_OCCUPANCY, True),
        ('HatcheryDirtPerMeal', None, meals_per_turn, FULL_OCCUPANCY, True),
        ('TrainHallDirtPerHit', MEDIUM, cooldown_rate('TrainHallCooldownHit'), OCCUPANCY, True),
        ('CasinoDirtPerWork', MEDIUM, cooldown_rate('CasinoCooldownWork'), OCCUPANCY, True),
        ('DormitoryDirtPerSleepTurn', MEDIUM, float(SPOTS), OCCUPANCY, True),
        ('GuardRoomDirtPerDuty', MEDIUM, cooldown_rate('GuardRoomCooldownDuty'), OCCUPANCY, True),
        ('LibraryDirtPerWork', LOW, cooldown_rate('LibraryCooldownWork'), OCCUPANCY, True),
        ('TempleDirtPerPrayerTurn', LOW, float(SPOTS), OCCUPANCY, True),
        ('PrisonDirtPerPrisonerTurn', HIGH, float(PRISON_PRISONER_TURNS), FULL_OCCUPANCY, False),
        ('TortureDirtPerSession', HIGH, SPOTS / float(TORTURE_SESSION_TURNS), OCCUPANCY, False),
    ]
    # The hatchery counts once with weight HIGH (hens and meals take half each)
    sum_f = HIGH
    for key, weight, rate, occupancy, counted in rooms:
        if weight is not None and counted:
            sum_f += weight
    result = {}
    for key, weight, rate, occupancy, counted in rooms:
        if weight is None:
            production = capacity * HIGH / sum_f / 2.0
        else:
            production = float(round_half_up(capacity * weight / sum_f, 4))
        value = production / (occupancy * rate)
        result[key] = round_half_up(round_half_up(value, 5), 4)
    return result


# Prints the table and the two keys that follow it.
def print_table(table):
    for key in EXPECTED:
        print('%-28s %s' % (key, table[key]))
    print('CombatDirtPerHit = ArenaDirtPerHit %s, TrailDirtPerTile = DormitoryDirtPerSleepTurn %s'
          % (table['ArenaDirtPerHit'], table['DormitoryDirtPerSleepTurn']))


# Compares the computed table with EXPECTED and the config files; returns the list of differences.
def check(table):
    problems = []
    rooms_cfg = ROOT / 'config' / 'rooms.cfg'
    global_dirt = read_block(ROOT / 'config' / 'global.cfg', 'Dirt')
    for key, expected in EXPECTED.items():
        if str(table[key]) != expected:
            problems.append('formula gives %s %s, expected %s' % (key, table[key], expected))
        value = read_key(rooms_cfg, key)
        if value != expected:
            problems.append('rooms.cfg %s is %s, expected %s' % (key, value, expected))
    if global_dirt.get('CombatDirtPerHit') != EXPECTED['ArenaDirtPerHit']:
        problems.append('global.cfg CombatDirtPerHit is %s, expected %s'
                        % (global_dirt.get('CombatDirtPerHit'), EXPECTED['ArenaDirtPerHit']))
    if global_dirt.get('TrailDirtPerTile') != EXPECTED['DormitoryDirtPerSleepTurn']:
        problems.append('global.cfg TrailDirtPerTile is %s, expected %s'
                        % (global_dirt.get('TrailDirtPerTile'), EXPECTED['DormitoryDirtPerSleepTurn']))
    return problems


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    table = compute()
    print_table(table)
    if args.check:
        problems = check(table)
        for problem in problems:
            print('FAIL: ' + problem)
        if problems:
            return 1
        print('dirt_values ok')
    return 0


if __name__ == '__main__':
    sys.exit(main())
