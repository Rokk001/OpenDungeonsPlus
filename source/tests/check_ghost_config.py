"""Check declared ghost, corpse, crystal, research and job values without compiling."""
from pathlib import Path
import math
import re

repo = Path(__file__).resolve().parents[2]

# Read a tracked source using the repository root rather than the caller's directory.
def read(path):
    return (repo / path).read_text(encoding="utf-8")

# Parse numeric configuration rows while rejecting duplicate declarations.
def numbers(path):
    result = {}
    for line in read(path).splitlines():
        row = line.split('#', 1)[0].split()
        if len(row) == 2:
            try:
                value = float(row[1])
            except ValueError:
                continue
            assert row[0] not in result or not row[0].startswith(("Ghost","Corpse","SoulCrystal","Crypt")), (path, row[0], "duplicate")
            result[row[0]] = value
    return result

# Check every decided value, exact jobs, research mapping and fear membership.
def main():
    global_values = numbers("config/global.cfg")
    room = numbers("config/rooms.cfg")
    expected = {"GhostLifetimeSeconds":344.4444,"GhostFloatSpeed":.36,"GhostWanderRadius":8,
        "CorpseLieSeconds":120,"CorpseDecaySeconds":240,"SoulCrystalPrice":800,
        "SoulCrystalBreakBelow":.4,"SoulCrystalNormalXpPerSecond":0.49322750960632944,
        "SoulCrystalHeroRareStart":.04,"SoulCrystalHeroRareEnd":.62,
        "GhostAiGoldPerResearchPoint":.4144,"GhostAiGoldPerXp":0.8536668706148699}
    for key, value in expected.items():
        assert global_values[key] == value, (key, global_values.get(key), value)
    expected = {"GhostTransferSeconds":20,"GhostBoxCapacity":1,"GhostBeamRange":1,
        "GhostBoxOpenSeconds":120,"GhostHuntersPerCauldron":3,"GhostLevelsPerEctoplasm":10,
        "GhostEctoplasmMana":1580,"GhostEctoplasmResearchPoints":319.8663176854666,"GhostEctoplasmPerCrystal":6,"GhostReviveMana":14000,
        "GhostReviveHpShare":.35,"CryptCorpsesPerLich":10,"CryptLichLevelBonus":0,
        "GhostRoomCostPerTile":620,"GhostRoomHP":50,"GhostRoomMinSide":4,
        "GhostRiseSeconds":1.5,"GhostDissolveSeconds":1.5,"GhostHowlMinSeconds":10,
        "GhostHowlMaxSeconds":20,"GhostBellSeconds":3,"GhostRepathTurns":5,
        "GhostApparatusTurns":5.5,"GhostHeroProductFactor":4.333333333333333,"GhostHeroProductWeightMana":6,
        "GhostHeroProductWeightBook":6,"GhostHeroProductWeightCrystal":1,"GhostProductBoxChance":.05}
    for key, value in expected.items():
        assert room[key] == value, (key, room.get(key), value)
    # Owner decision 726: the catch takes 2 s throw, 16 s beam and 2 s snap, 20 s for every hunter; the former
    # efficiency- and research-scaled beam turns are gone.
    catch = {"GhostBoxThrowSeconds":2,"GhostBeamSeconds":16,"GhostBoxSnapSeconds":2}
    for key, value in catch.items():
        assert room[key] == value, (key, room.get(key), value)
    assert sum(catch.values()) == 20, catch
    assert "GhostBeamTurns" not in room, "GhostBeamTurns replaced by GhostBeamSeconds"
    # Every apparatus value has a documentation line directly above its key (a comment or a key of the same block)
    rows = read('config/rooms.cfg').splitlines()
    for key in ('GhostApparatusTurns','GhostHeroProductFactor','GhostHeroProductWeightMana','GhostProductBoxChance',
            'GhostBoxThrowSeconds','GhostBeamSeconds','GhostBoxSnapSeconds'):
        index = next(i for i, row in enumerate(rows) if row.split()[:1] == [key])
        assert rows[index-1].lstrip().startswith('#'), (key, 'documentation line')
    for key in ('GhostHeroProductWeightBook','GhostHeroProductWeightCrystal'):
        index = next(i for i, row in enumerate(rows) if row.split()[:1] == [key])
        assert rows[index-1].split()[0].startswith('GhostHeroProductWeight'), (key, 'documented weight block')
    # Chances are fractions, never percentages
    assert 0 < room['GhostProductBoxChance'] < 1
    assert room['GhostRoomCostPerTile'] == room['CryptCostPerTile']
    assert room['GhostRoomHP'] == room['CryptHP']
    trap = numbers('config/traps.cfg')
    assert trap['FearRadius']==3 and trap['FearDurationTurns']==20
    assert round(2*62/global_values['GhostFloatSpeed'], 4) == global_values['GhostLifetimeSeconds']
    assert not {'CryptRotNbTurns','CryptPointsForSpawn','CryptBonusWallActiveSpot'} & room.keys()
    skills = read('config/skills.cfg')
    assert re.search(r'^\s*roomGhostRoom\s+600\s*$', skills, re.M)
    for effect, mode, values in [('EctoplasmLevels','mul',[1,.8,.6]),('BoxCapacity','add',[0,1,2]),
            ('BeamRange','add',[0,1,2]),('CatchTime','mul',[1,.8,.667]),('RevivePrice','add',[0,-2000,-4000]),
            ('LichCorpses','mul',[1,.8,.6]),('LichLevel','add',[0,1,2])]:
        skill = 'roomCrypt' if effect.startswith('Lich') else 'roomGhostRoom'
        matches = re.findall(r'^\s*'+skill+r'\s+'+effect+r'\s+(\w+)\s+([^\n#]+)', skills, re.M)
        assert len(matches)==1 and matches[0][0]==mode and list(map(float,matches[0][1].split()))==values, effect
    assert not re.search(r'^\s*roomCrypt\s+RotTime\b', skills, re.M)
    ai = read('source/ai/KeeperAI.cpp')
    # The compiled room order and the [RoomPlan] order of ai.cfg are the same whole list of the plan
    plan_section = re.search(r'^\[RoomPlan\]\s*$(.*?)^\[/RoomPlan\]', read('config/ai.cfg'), re.M | re.S).group(1)
    plan_names = [row.split()[0] for row in plan_section.splitlines() if row.strip() and not row.lstrip().startswith('#')]
    compiled_names = re.findall(r'"(\w+)"', re.search(r'wantedBuildingKeys = \{(.*?)\};', ai, re.S).group(1))
    assert plan_names == ['treasury', 'dormitory', 'hatchery', 'tavern', 'library', 'training', 'workshop', 'casino', 'toilet', 'treasury2', 'merchant', 'guard', 'herbgarden', 'arena', 'prison', 'alchemy', 'infirmary', 'ghostroom', 'spa', 'crypt', 'temple', 'torture'], plan_names
    assert compiled_names == plan_names, compiled_names
    assert plan_names.index('ghostroom') == 17 and plan_names.index('crypt') == 19
    creatures = {}
    for block in re.findall(r'\[Creature\](.*?)\[/Creature\]', read('config/creatures.cfg'), re.S):
        match = re.search(r'^\s*Name\s+(\S+)', block, re.M)
        if match:
            creatures[match[1]] = block
    afraid = {name for name, block in creatures.items() if re.search(r'^\s*AfraidOfGhosts\s+1\s*$',block,re.M)}
    assert afraid == {'Rat','Roach','Spider','CaveHornet','Goblin','Adventurer','Elf','Gnome','Dwarf1','Dwarf2'}, afraid
    jobs = {'CaveHornet':('HerbGarden',100,1.5),'Roach':('HerbGarden',90,1),'Spider':('HerbGarden',80,.5),
        'DarkElf':('AlchemyLab',90,1),'LavaSpawn':('AlchemyLab',80,.5),'Elf':('AlchemyLab',100,1.5),
        'NatureMonster':('AlchemyLab',90,1),'Adventurer':('AlchemyLab',80,.5),
        'PitDemon':('GhostRoom',0,3),'Troll':('GhostRoom',0,1.5),'Skeleton':('GhostRoom',0,.5),
        'RunelordDwarf':('GhostRoom',0,3),'Knight':('GhostRoom',0,1.5),'Defender':('GhostRoom',0,.5)}
    hunters = set()
    for name, block in creatures.items():
        match = re.search(r'\[RoomAffinity\](.*?)\[/RoomAffinity\]', block, re.S)
        affinities = {} if match is None else {row[0]:(float(row[1]),float(row[2])) for line in match[1].splitlines()
            if len(row:=line.split('#',1)[0].split())==3}
        if 'GhostRoom' in affinities:
            hunters.add(name)
            assert name not in afraid
            assert affinities['GhostRoom'][0] == 0
        if name in jobs:
            job, likeness, efficiency = jobs[name]
            assert affinities.get(job)==(likeness,efficiency), (name, job, affinities)
        removed = {'Elf':('Workshop','Library'),'Monk':('Workshop',),'Defender':('Workshop',),
            'DarkElf':('Workshop',),'Gnome':('Workshop',)}.get(name,())
        assert not set(removed)&affinities.keys(), name
    assert hunters == {'PitDemon','Troll','Skeleton','RunelordDwarf','Knight','Defender'}, hunters
    expected_jobs = {'Library':{'Orc':3,'Cultist':1.5,'Rat':.5,'Wizard':3,'Monk':1,'Slime':.5},
        'Workshop':{'Goblin':2,'LavaSpawn':1.2,'LizardMan':.8,'Rat':.4,'Dwarf1':2,'Dwarf2':1.5,'Scarab':.6,'Slime':.4},
        'HerbGarden':{'CaveHornet':1.5,'Roach':1,'Spider':.5,'NatureMonster':1.5,'Elf':1.2,'Monk':1},
        'AlchemyLab':{'LizardMan':1.5,'DarkElf':1,'LavaSpawn':.5,'Elf':1.5,'NatureMonster':1,'Adventurer':.5},
        'GhostRoom':{'PitDemon':3,'Troll':1.5,'Skeleton':.5,'RunelordDwarf':3,'Knight':1.5,'Defender':.5}}
    for room_name, expected_types in expected_jobs.items():
        actual = {}
        for name, block in creatures.items():
            affinity = re.search(r'\[RoomAffinity\](.*?)\[/RoomAffinity\]',block,re.S)
            if affinity:
                row = re.search(r'^\s*'+room_name+r'\s+([-+0-9.]+)\s+([-+0-9.]+)\s*$',affinity[1],re.M)
                if row and float(row[2])>0 and (room_name=='GhostRoom' or float(row[1])>0):
                    actual[name] = float(row[2])
        assert all(actual.get(name)==efficiency for name,efficiency in expected_types.items()), (room_name,actual)
        # All other pre-existing affinities are explicitly retained, including side jobs.
    manager = read('source/game/SkillManager.cpp')
    for skill,effect,key in [('roomGhostRoom','EctoplasmLevels','GhostLevelsPerEctoplasm'),
            ('roomGhostRoom','BoxCapacity','GhostBoxCapacity'),('roomGhostRoom','BeamRange','GhostBeamRange'),
            ('roomGhostRoom','CatchTime','GhostTransferSeconds'),('roomGhostRoom','RevivePrice','GhostReviveMana'),
            ('roomCrypt','LichCorpses','CryptCorpsesPerLich'),('roomCrypt','LichLevel','CryptLichLevelBonus')]:
        assert re.search(r'SkillType::'+skill+r'\s*,\s*"'+effect+r'"\s*,\s*ResearchBaseSource::rooms\s*,\s*"'+key+r'"',manager), (effect,key)

    definition = read('source/entities/CreatureDefinition.cpp')
    assert 'AfraidOfGhosts' in definition and 'mAfraidOfGhosts' in definition
    print('ghost configuration: ok')

if __name__ == '__main__':
    main()
