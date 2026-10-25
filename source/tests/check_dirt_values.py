"""Dirt, cleaning and toilet values: every key of the [Dirt] block and of the room table has the value of the design,
the per-room dirt keys are the ones the formula of tools/balance/dirt_values.py gives, the per-type factors are right
and everything is documented in the header of its config file.

Calls (from the repository root):
  python source/tests/check_dirt_values.py            plain file checks, no compiler, no game
"""
from pathlib import Path
import re
import subprocess
import sys

root = Path(__file__).resolve().parents[2]


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


global_cfg = read('config/global.cfg')
rooms_cfg = read('config/rooms.cfg')
creatures_cfg = read('config/creatures.cfg')

# 1. The tool recomputes the table from the config keys and holds the file to it
result = subprocess.run([sys.executable, str(root / 'tools' / 'balance' / 'dirt_values.py'), '--check'],
                        capture_output=True, text=True, cwd=str(root))
assert result.returncode == 0, 'dirt_values.py --check failed:\n' + result.stdout + result.stderr

# 2. Every key of the [Dirt] block with the value of the design
DIRT = {
    'DirtVisibleFrom': '10', 'DirtStage2At': '33.3333', 'DirtStage3At': '66.6667', 'DirtMoodStage2': '-30', 'DirtMoodStage3': '-60',
    'DirtPileMood': '-30', 'DirtPileRadius': '2', 'DirtOutputStage2': '0.75', 'DirtOutputStage3': '0.5',
    'UrgeSeek': '80', 'UrgeOnTheWay': '75', 'UrgeRelieve': '100', 'UrgePerChicken': '20', 'UrgePerDrink': '15',
    'ToiletUseTurns': '4', 'ToiletWaitRadius': '1', 'ToiletReserveFactor': '3',
    'CleaningWorkerSharePercent': '20', 'CleanRoomFromStage': '2', 'CleanRateFactor': '1',
    'CleaningMaxTurnsPerTile': '20',
    'CombatDirtPerHit': '1.5922', 'TrailDirtPerTile': '0.1448',
    'CreatureDirtPerFightWon': '5', 'CreatureDirtPerKo': '25', 'CreatureDirtDecayPerTurn': '0.1',
    'BloodDryTurns': '168', 'DirtNoticeSeconds': '60', 'FilthyPostSeconds': '600',
    'DirtSyncTurns': '2', 'DirtResyncTurns': '60',
    'PrisonDirtDamageStage2': '1.25', 'PrisonDirtDamageStage3': '1.5',
    'TortureDirtConvertStage2': '0.9', 'TortureDirtConvertStage3': '0.8',
}
dirt = block_values(global_cfg, 'Dirt')
for key, value in DIRT.items():
    assert dirt.get(key) == value, '[Dirt] ' + key + ' is ' + str(dirt.get(key)) + ', expected ' + value
extra = set(dirt) - set(DIRT)
assert not extra, '[Dirt] keys without a design value: ' + ', '.join(sorted(extra))
assert 'CreatureDirtPerFight' not in dirt, 'the old key CreatureDirtPerFight must not come back'
# The stage thresholds split 0-100 into three equal parts and the block documents each key
assert float(dirt['DirtStage2At']) < float(dirt['DirtStage3At']) < 100.0
for key in DIRT:
    assert_documented(global_cfg, key, 'global.cfg')

# 3. The per-room keys of rooms.cfg (the same values the tool computes) and the toilet room keys
ROOM_KEYS = {
    'WorkshopDirtPerWork': '1.5922', 'ArenaDirtPerHit': '1.5922', 'ToiletDirtPerUse': '0.5211',
    'HatcheryDirtPerHenTurn': '0.0323', 'HatcheryDirtPerMeal': '8.0769', 'TrainHallDirtPerHit': '0.7961',
    'CasinoDirtPerWork': '0.7961', 'DormitoryDirtPerSleepTurn': '0.1448', 'GuardRoomDirtPerDuty': '1.2304',
    'LibraryDirtPerWork': '0.3980', 'TempleDirtPerPrayerTurn': '0.0724', 'PrisonDirtPerPrisonerTurn': '0.1615',
    'TortureDirtPerSession': '1.4475', 'TavernDirtPerDrink': '0.2605',
}
room_values = block_values(rooms_cfg, 'Rooms')
for key, value in ROOM_KEYS.items():
    assert room_values.get(key) == value, 'rooms.cfg ' + key + ' is ' + str(room_values.get(key)) + ', expected ' + value
    assert_documented(rooms_cfg, key, 'rooms.cfg')
# Only the rooms of the table make dirt: no other DirtPer key (crypt, treasury, portals, heart, bridges have none)
other = sorted(k for k in room_values if 'DirtPer' in k and k not in ROOM_KEYS)
assert not other, 'rooms.cfg has dirt keys outside the table: ' + ', '.join(other)
assert room_values['ToiletCostPerTile'] == room_values['DormitoryCostPerTile'] == '92', 'ToiletCostPerTile must equal DormitoryCostPerTile'
assert room_values['ToiletHP'] == '50'
assert_documented(rooms_cfg, 'ToiletCostPerTile', 'rooms.cfg')
# CombatDirtPerHit is the arena value, TrailDirtPerTile the dormitory value
assert dirt['CombatDirtPerHit'] == room_values['ArenaDirtPerHit']
assert dirt['TrailDirtPerTile'] == room_values['DormitoryDirtPerSleepTurn']

# 4. Per type: UrgeGrowth/Turn = HungerGrowth/Turn, Cleanliness and DirtFactor of the table
FACTORS = {}
for names, cleanliness, dirt_factor in [
        ('Rat Roach Spider Slime CaveHornet Scarab', '0.25', '1.75'),
        ('Orc Troll Goblin PitDemon LavaSpawn TentacleAlbine TentacleGreen Wyvern Kreatur LizardMan', '0.5', '1.5'),
        ('Skeleton Lich', '0.5', '0.25'),
        ('Kobold DwarfWorker Dwarf1 Dwarf2 RunelordDwarf Gnome Cultist Dragon NatureMonster Champion', '1', '1'),
        ('Adventurer Monk Knight Wizard Defender', '1.5', '0.75'),
        ('Elf DarkElf', '2', '0.5')]:
    for name in names.split():
        FACTORS[name] = (cleanliness, dirt_factor)
assert len(FACTORS) == 35, len(FACTORS)
seen = set()
for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', creatures_cfg, re.S):
    fields = {}
    for line in block.splitlines():
        words = line.split()
        if len(words) >= 2 and not words[0].startswith('#'):
            fields.setdefault(words[0], words[1])
    name = fields.get('Name')
    if name is None:
        continue
    assert name in FACTORS, 'creature type without a dirt row: ' + name
    seen.add(name)
    assert fields.get('UrgeGrowth/Turn') == fields['HungerGrowth/Turn'], name + ': UrgeGrowth/Turn must equal HungerGrowth/Turn'
    assert (fields.get('Cleanliness'), fields.get('DirtFactor')) == FACTORS[name], \
        name + ': Cleanliness / DirtFactor ' + str((fields.get('Cleanliness'), fields.get('DirtFactor'))) + ' differ from the table'
assert seen == set(FACTORS), 'types missing in creatures.cfg: ' + ', '.join(sorted(set(FACTORS) - seen))
for key in ('UrgeGrowth/Turn', 'Cleanliness', 'DirtFactor'):
    assert_documented(creatures_cfg, key, 'creatures.cfg')

# 5. The skill cost of the toilet (tier II) is documented and set in skills.cfg
skills_cfg = read('config/skills.cfg')
assert re.search(r'^\s*roomToilet\s+250\s*$', skills_cfg, re.M), 'skills.cfg: roomToilet 250 missing'
assert_documented(skills_cfg, 'roomToilet', 'skills.cfg')

print('dirt values ok')
