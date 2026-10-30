"""Check the creature attribute model: config fields and keys, attribute levels and the derived values (no build needed).

Part A: the [Stats] fields of creatures.cfg, the equipment fields, the global.cfg keys, the attribute level formulas
and the places that use the attribute level instead of the creature level. Other parts are added by later packages.
"""
from pathlib import Path
import glob
import re
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / 'tools/balance'))
from combat_sim import combat_stat, multiplier

BS = chr(92)


def text(relative):
    return (root / relative).read_text(encoding='utf-8')


def function(source, signature):
    """Return the source of the function that starts with the signature (up to its closing brace)."""
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def config_value(source, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s+(\S+)', source, re.M)
    assert match, key
    return match[1]


# ---- global.cfg keys (section 3 and the named keys of section 1) with their documented values
global_cfg = text('config/global.cfg')
config_manager_h = text('source/utils/ConfigManager.h')
config_manager_cpp = text('source/utils/ConfigManager.cpp')
GLOBAL_KEYS = {
    'CritChancePerDexterity': '0.2', 'CritDamageMultiplier': '2', 'ManaRefillSeconds': '120',
    'SkillPointFirstLevel': '10', 'SkillRanksPerSkill': '5', 'SkillTemplateDeviationPercent': '25',
    'SkillRespecChickens': '2', 'SkillRespecWindowSeconds': '60', 'SkillSpellReferenceMinHP': '86.1',
    'CritChancePerLevel': '0.3', 'ManaPerCasterShot': '2.5', 'ManaPerDragonSecondShot': '5',
    'SkillHealSelfBelow': '0.6', 'SkillHealAllyBelow': '0.6', 'SkillHealAreaBelow': '0.7',
    'SkillHealAreaMinCreatures': '2', 'GoldCarryPerStrength': '0.01',
}
for key, value in GLOBAL_KEYS.items():
    assert config_value(global_cfg, key) == value, (key, value)
    assert 'nextParam == "' + key + '"' in config_manager_cpp, key
    assert '(global.cfg ' + key + ')' in config_manager_h, key
    assert '(' + key + ' in global.cfg)' in config_manager_h, key
# Every key stands inside the commented block that explains the attribute model
block = global_cfg[global_cfg.index('# Creature attributes, mana'):]
for key in GLOBAL_KEYS:
    assert key in block, key

# ---- creatures.cfg [Stats] fields: documented in the header, parsed, written, streamed, defaulted
creatures_cfg = text('config/creatures.cfg')
definition_cpp = text('source/entities/CreatureDefinition.cpp')
definition_h = text('source/entities/CreatureDefinition.h')
header = creatures_cfg
NUMERIC = {'Strength': '20.0', 'Dexterity': '20.0', 'Life': '20.0', 'Mana': '20.0', 'StrengthPerLevel': '1.0',
           'DexterityPerLevel': '2.0', 'LifePerLevel': '1.0', 'ManaPerLevel': '1.0', 'ManaPerPoint': '1.5',
           'CritChanceBonus': '0.0'}
TEXT = ('SkillGroup', 'SkillFamily', 'PreSkill', 'TierFourSkill')
for key in list(NUMERIC) + list(TEXT):
    member = 'm' + key
    assert re.search(r'^# ' + key + r'\b', header, re.M), 'header documents ' + key
    assert 'nextParam == "' + key + '"' in definition_cpp, 'parse ' + key
    assert 'file << "    ' + key + BS + 't"' in definition_cpp, 'definition diff ' + key
    assert 'os << c->' + member + ';' in definition_cpp, 'stream export ' + key
    assert 'is >> c->' + member + ';' in definition_cpp, 'stream import ' + key
    assert member + '(def.' + member + ')' in definition_cpp, 'copy ' + key
for key, default in NUMERIC.items():
    assert re.search(r'm' + key + r' \(' + re.escape(default) + r'\)', definition_cpp), 'default ' + key
for key in TEXT:
    assert re.search(r'm' + key + r' \("none"\)', definition_cpp), 'default ' + key
# The stream order of export and import is the same
export = [m for m in re.findall(r'os << c->(m\w+);', function(definition_cpp, 'ODPacket& operator<<(ODPacket& os, const CreatureDefinition* c)'))]
imported = [m for m in re.findall(r'is >> c->(m\w+)', function(definition_cpp, 'ODPacket& operator>>(ODPacket& is, CreatureDefinition* c)'))]
export_tail = export[export.index('mSkillDamageFactor'):export.index('mTierFourSkill') + 1]
import_tail = imported[imported.index('mSkillDamageFactor'):imported.index('mTierFourSkill') + 1]
assert export_tail == import_tail and len(export_tail) == 15, (export_tail, import_tail)
# The default per-level points add up to 5
assert 1 + 2 + 1 + 1 == 5

# ---- equipments.cfg fields
equipments_cfg = text('config/equipments.cfg')
weapon_cpp = text('source/entities/Weapon.cpp')
weapon_h = text('source/entities/Weapon.h')
for key in ('Strength', 'Dexterity', 'Life', 'Mana', 'CritChance'):
    member = 'm' + key
    assert re.search(r'^# ' + key + r'\b', equipments_cfg, re.M), 'equipment header documents ' + key
    assert 'nextParam == "' + key + '"' in weapon_cpp, key
    assert 'file << "    ' + key + BS + 't"' in weapon_cpp, key
    assert 'os << weapon->' + member + ';' in weapon_cpp and 'is >> weapon->' + member + ')' in weapon_cpp, key
    assert member + '(0.0)' in weapon_h, key
    # Optional, default 0, all 0 now: no equipment sets a bonus
    assert not re.search(r'^\s*' + key + r'\s+[-\d.]+', equipments_cfg.split('[EquipmentDefinitions]')[1], re.M), key

# ---- curve functions: variants for a fractional level without the 1..30 clamp, old callers unchanged
progression = text('source/entities/CreatureProgression.h')
for name in ('damageMultiplierAt(double level)', 'hpMultiplierAt(double level)', 'attackRatingMultiplierAt(double level)',
             'defenseRatingMultiplierAt(double level)', 'combatStatAt(double base, double perLevel, double level'):
    assert 'inline double ' + name in progression, name
assert 'inline double damageMultiplier(uint32_t level)' in progression
assert 'std::max(1u, std::min(MAX_POWER_LEVEL, level))' in function(progression, 'inline double damageMultiplier(uint32_t level)')
assert 'MAX_POWER_LEVEL' not in function(progression, 'inline double damageMultiplierAt(double level)')
assert 'MAX_POWER_LEVEL' not in function(progression, 'inline double combatStatAt(')

# ---- attribute level formulas (the same arithmetic as Creature.cpp), checked numerically
def attribute_level(per_level, level, equipment):
    """LA = 1 + (A(L) - start) / per level = L + equipment / per level, at least 1; L when per level is 0."""
    if per_level == 0:
        return float(level)
    return max(1.0, level + equipment / per_level)


def attribute_value(start, per_level, level, equipment):
    return start + per_level * (level - 1) + equipment


def stat_at(base, per_level, level, kind):
    level = max(1.0, level)
    curve = {'hp': 'hp', 'damage': 'damage', 'attack': 'attack', 'defense': 'defense'}[kind]
    return max(base + (level - 1.0) * per_level, base * multiplier_at(level, curve))


def multiplier_at(level, kind):
    """The curve without the upper clamp of level 30."""
    damage = 1 + 0.221 * (level - 1) ** 1.167
    if kind == 'damage':
        return damage
    if kind == 'hp':
        return damage * (1 + 0.018 * (level - 1))
    return float(level)


assert config_value(global_cfg, 'CreatureDamageGrowth') == '0.221' and config_value(global_cfg, 'CreatureDamageExponent') == '1.167'
assert config_value(global_cfg, 'CreatureHpGrowthPerLevel') == '0.018'
for per_level_set in ((1, 2, 1, 1), (2, 1, 1, 1), (0, 3, 1, 1), (0, 1, 2, 2)):
    for level in (1, 10, 30):
        for per_level in per_level_set:
            # Without equipment LA equals the level exactly, so every derived value equals the rebalance value
            assert attribute_level(per_level, level, 0.0) == float(level)
            assert attribute_value(20, per_level, level, 0.0) - 20 == per_level * (level - 1)
        for kind in ('hp', 'damage', 'attack', 'defense'):
            assert abs(stat_at(100.0, 2.0, float(level), kind) - combat_stat(100.0, 2.0, level, kind)) < 1e-9, (level, kind)
# Equipment raises the attribute level by bonus / points per level; a bonus on a 0-per-level attribute does nothing
assert attribute_level(2, 10, 6.0) == 13.0
assert attribute_level(1, 1, 4.0) == 5.0
assert attribute_level(2, 1, -10.0) == 1.0
assert attribute_level(0, 10, 50.0) == 10.0
assert stat_at(100.0, 2.0, 13.0, 'hp') > stat_at(100.0, 2.0, 10.0, 'hp')
assert stat_at(100.0, 2.0, 34.0, 'damage') > stat_at(100.0, 2.0, 30.0, 'damage')
assert multiplier(31, 'damage') == multiplier(30, 'damage')

# ---- wiring of the derived values
creature = text('source/entities/Creature.cpp')
creature_h = text('source/entities/Creature.h')
build_stats = function(creature, 'void Creature::buildStats()')
assert 'combatStatAt(mMaxHP, mDefinition->getHpPerLevel(), getLifeLevel()' in build_stats.replace(chr(10), ' ').replace('        ', '')
assert 'hpMultiplierAt' in build_stats and 'getSkillPassive("hp%")' in build_stats
assert build_stats.index('getLifeLevel()') < build_stats.index('if (multiplier <= 0.0)'), 'equipment counts at level 1'
attack = function(creature, 'double Creature::getAttackRating() const')
assert 'getDexterityLevel()' in attack and 'attackRatingMultiplierAt' in attack and 'getSkillPassive("ar%")' in attack
assert attack.index('getSkillPassive("ar%")') < attack.index('mWeaponL->getAttackRating()')
defense = function(creature, 'double Creature::getDefenseRating() const')
assert 'getDexterityLevel()' in defense and 'defenseRatingMultiplierAt' in defense and 'getSkillPassive("dr%")' in defense
for name in ('getStrength', 'getDexterity', 'getLife', 'getMana', 'getStrengthLevel', 'getDexterityLevel', 'getLifeLevel',
             'getManaLevel', 'getEquipmentCritChance', 'carriesBowOrCrossbow', 'getSkillPassive'):
    assert re.search(r'\b' + name + r'\(', creature_h), name
    assert 'Creature::' + name + '(' in creature, name
# Channel defenses keep the creature level (section 5 does not change them)
assert build_stats.count('CreatureProgression::damageMultiplier') == 3
# Bow and crossbow weapon types make the missile lines use the Dexterity level
carries = function(creature, 'bool Creature::carriesBowOrCrossbow() const')
assert '"bow"' in carries and '"crossbow"' in carries

damage = text('source/entities/CombatDamage.h')
scale = function(damage, 'inline void scale(')
assert 'damageMultiplierAt(damageLevel)' in scale and 'getSkillPassive("alldmg%")' in scale
assert scale.index('damageMultiplierAt(damageLevel)') < damage.index('weapon->getPhysicalDamageMin()')
melee = text('source/creatureskill/CreatureSkillMeleeFight.cpp')
assert 'creature->getStrengthLevel(), "dmg%"' in melee.replace(chr(10), ' ').replace('  ', '')
launch = text('source/creatureskill/CreatureSkillMissileLaunch.cpp')
assert 'creature->getDexterityLevel()' in launch and 'carriesBowOrCrossbow()' in launch
assert 'getSkillName() != "Grenade"' in launch, 'the grenade keeps the creature level'
assert 'isFirstAttackSkill(this)' in launch and '"spell%"' in launch
assert 'bool CreatureDefinition::isFirstAttackSkill(' in definition_cpp


# ---- Part H: values per creature type (section 4) and the heart (section 9)
# Group table of section 4: Str, Dex, Life, Mana, Str/L, Dex/L, Life/L, Mana/L, ManaPerPoint
GROUP_VALUES = {
    'blocker': (30.0, 20.0, 25.0, 10.0, 2.0, 1.0, 1.0, 1.0, 1.0),
    'blitzer': (25.0, 20.0, 25.0, 26.6667, 2.0, 1.0, 1.0, 1.0, 1.5),
    'flanker': (20.0, 20.0, 20.0, 25.0, 1.0, 2.0, 1.0, 1.0, 1.75),
    'archer': (20.0, 25.0, 20.0, 15.0, 0.0, 3.0, 1.0, 1.0, 1.5),
    'caster': (10.0, 25.0, 10.0, 35.0, 0.0, 1.0, 2.0, 2.0, 2.0),
    'worker': (15.0, 25.0, 15.0, 25.0, 1.0, 2.0, 1.0, 1.0, 2.0),
}
GROUP_MEMBERS = {
    'blocker': 'Orc LavaSpawn PitDemon Troll Skeleton Scarab Monk Dwarf1 Dwarf2 Knight RunelordDwarf NatureMonster Defender '
               'TentacleAlbine TentacleGreen',
    'blitzer': 'Dragon',
    'flanker': 'Rat Goblin Roach Spider Cultist CaveHornet Slime Adventurer Wyvern Gnome',
    'archer': 'DarkElf Elf',
    'caster': 'LizardMan Lich Wizard Kreatur',
    'worker': 'Kobold DwarfWorker',
}
FAMILY_MEMBERS = {
    'greenskin': 'Orc Troll Goblin', 'dwarf': 'Dwarf1 Dwarf2 RunelordDwarf', 'undead': 'Skeleton Lich',
    'vermin': 'Rat Roach Spider CaveHornet Scarab', 'tentacle': 'TentacleAlbine TentacleGreen', 'demon': 'LavaSpawn PitDemon',
    'elf': 'Elf DarkElf', 'human': 'Adventurer Monk Knight Defender', 'arcane': 'Cultist Wizard Gnome Kreatur',
    'dragonkin': 'LizardMan Wyvern Dragon', 'wild': 'Slime NatureMonster', 'workfolk': 'Kobold DwarfWorker',
}
PRE_SKILLS = {
    'Lich': 'UND_1', 'Dragon': 'DRK_1', 'Slime': 'WLD_1', 'CaveHornet': 'VRM_1', 'Goblin': 'FLK_A2', 'Gnome': 'FLK_A2',
    'Wizard': 'CST_B1', 'Elf': 'ARC_A3', 'DarkElf': 'ARC_A2', 'Kobold': 'WRK_C1', 'DwarfWorker': 'WRK_C1',
}
STAT_KEYS = ('Strength', 'Dexterity', 'Life', 'Mana', 'StrengthPerLevel', 'DexterityPerLevel', 'LifePerLevel', 'ManaPerLevel',
             'ManaPerPoint')
CHAMPION_CRIT_BONUS = 15.0
# Level-file creature classes use the values of the type whose mesh they use
LEVEL_FILE_CLASSES = {'DragonBoss': 'Dragon', 'BossDragon': 'Dragon', 'VeteranScarab': 'Scarab'}
HEART_HP = 15100.0
HEART_HEAL_PER_SECOND = 3.775
LEGACY_HEART_HEALTH_SCALE = 10000.0


def stats_blocks(source):
    """Return {creature name: {key: value}} of the [Stats] part of every [Creature] block in the text."""
    result = {}
    for block in re.findall(r'\[Creature\]\r?\n(.*?)\[/Creature\]', source, re.S):
        name = re.search(r'^\s*Name\s+(\S+)', block, re.M)[1]
        stats = block[block.index('[Stats]'):block.index('[/Stats]')]
        values = {}
        for line in stats.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 2 and not parts[0].startswith('#'):
                values[parts[0]] = parts[1]
        values['_block'] = block
        result[name] = values
    return result


def heart_health_after_load(marker, value, max_hp, research_factor):
    """Mirror of RoomDungeonTemple::importFromStream for the share marker and the HeartHealth10000 marker."""
    if marker == 'HeartHealthShare':
        return min(1.0, max(0.0, value)) * max_hp
    assert marker == 'HeartHealth10000'
    return min(1.0, value / (LEGACY_HEART_HEALTH_SCALE * research_factor)) * max_hp


def check_part_h():
    """Values per creature type of section 4 (also in the level files) and the heart values and save markers of section 9."""
    creatures = stats_blocks(creatures_cfg)
    assert len(creatures) == 35, len(creatures)
    group_of = {}
    for group, members in GROUP_MEMBERS.items():
        for member in members.split():
            assert member not in group_of, member
            group_of[member] = group
    family_of = {}
    for family, members in FAMILY_MEMBERS.items():
        for member in members.split():
            assert member not in family_of, member
            family_of[member] = family
    assert set(group_of) | {'Champion'} == set(creatures), set(creatures) ^ (set(group_of) | {'Champion'})
    assert set(family_of) == set(group_of), 'every type has a family'
    # Every group gives 5 attribute points per level
    for group, values in GROUP_VALUES.items():
        assert sum(values[4:8]) == 5.0, (group, values)

    def check_values(name, stats, group, skill_group, family, pre_skill, tier_four):
        wanted = GROUP_VALUES[group]
        for key, value in zip(STAT_KEYS, wanted):
            assert key in stats and abs(float(stats[key]) - value) < 1e-9, (name, key, stats.get(key), value)
        assert sum(float(stats[key]) for key in STAT_KEYS[4:8]) == 5.0, (name, 'points per level')
        assert stats.get('SkillGroup') == skill_group, (name, 'SkillGroup', stats.get('SkillGroup'))
        assert stats.get('SkillFamily') == family, (name, 'SkillFamily', stats.get('SkillFamily'))
        assert stats.get('PreSkill') == pre_skill, (name, 'PreSkill', stats.get('PreSkill'))
        assert stats.get('TierFourSkill') == tier_four, (name, 'TierFourSkill', stats.get('TierFourSkill'))

    for name, group in group_of.items():
        stats = creatures[name]
        check_values(name, stats, group, group, family_of[name], PRE_SKILLS.get(name, 'none'), 'T4_' + name)
        assert 'CritChanceBonus' not in stats, (name, 'only the Champion has a critical chance bonus')
        # The group follows the combat class and the job of the type
        combat_class = stats.get('CombatClass')
        if group == 'worker':
            assert stats['CreatureJob'] == 'Worker', name
        else:
            assert stats['CreatureJob'] == 'Fighter', name
        if group == 'blitzer':
            assert combat_class == 'Blitzer', name
        elif group == 'flanker':
            assert combat_class == 'Flanker', name
        elif group == 'blocker':
            assert combat_class in ('Blocker', 'Support'), name
        elif group in ('archer', 'caster'):
            assert combat_class == 'Support', name
        if group == 'archer':
            assert 'Bow' in stats['_block'] or 'Crossbow' in stats['_block'], name
    # Champion: blitzer attribute values, no skill tree, critical chance bonus 15
    champion = creatures['Champion']
    check_values('Champion', champion, 'blitzer', 'none', 'none', 'none', 'none')
    assert float(champion['CritChanceBonus']) == CHAMPION_CRIT_BONUS
    # Worker hit points follow the rebalance (70)
    assert creatures['Kobold']['MinHP'] == '70' and creatures['DwarfWorker']['MinHP'] == '70'

    # Level-file creature definitions: the values of the type whose mesh they use
    found_classes = set()
    for level_file in sorted((root / 'levels').rglob('*.level')):
        level_text = level_file.read_text(encoding='utf-8', errors='replace')
        if '[Creature]' not in level_text:
            continue
        for name, stats in stats_blocks(level_text).items():
            if 'MinHP' not in stats:
                # A partial override of a known type (e.g. only a weapon) takes the attribute values from the type
                assert name in group_of and not set(STAT_KEYS) & set(stats), (level_file.name, name)
                continue
            assert name in LEVEL_FILE_CLASSES, (level_file.name, name, 'a level-file creature definition without attribute values')
            base = LEVEL_FILE_CLASSES[name]
            mesh = stats['MeshName'].split('.')[0]
            assert mesh == base, (name, mesh, base)
            check_values(name, stats, group_of[base], group_of[base], family_of[base], PRE_SKILLS.get(base, 'none'), 'T4_' + base)
            found_classes.add(name)
    assert found_classes == set(LEVEL_FILE_CLASSES), found_classes

    # ---- Heart (section 9): values, share record and the conversion of old saves
    rooms_cfg = text('config/rooms.cfg')
    assert float(config_value(rooms_cfg, 'DungeonHeartHP')) == HEART_HP
    assert float(config_value(rooms_cfg, 'DungeonHeartHealPerSecond')) == HEART_HEAL_PER_SECOND
    # The same share of the health per second as before: 2.5 of 10000
    assert abs(HEART_HEAL_PER_SECOND / HEART_HP - 2.5 / LEGACY_HEART_HEALTH_SCALE) < 1e-12
    # The rounded-up building damage factor of the worst type: 10000 x 1.5073 = 15073, next hundred
    assert HEART_HP == -(-int(10000 * 1.5073) // 100) * 100.0
    temple = text('source/rooms/RoomDungeonTemple.cpp')
    assert 'getRoomConfigDoubleOrDefault("DungeonHeartHP", 15100.0)' in temple
    export = function(temple, 'void RoomDungeonTemple::exportToStream(')
    assert '"HeartHealthShare "' in export and 'getHeartHealthFraction()' in export and 'HeartHealth10000' not in export
    import_function = function(temple, 'bool RoomDungeonTemple::importFromStream(')
    assert 'marker == "HeartHealthShare"' in import_function
    assert 'std::min(1.0, std::max(0.0, value)) * getHeartMaxHP()' in import_function
    assert 'marker == "HeartHealth10000"' in import_function
    assert 'std::min(1.0, value / (LEGACY_HEART_HEALTH_SCALE * getHeartHPFactor())) * getHeartMaxHP()' in import_function
    assert re.search(r'LEGACY_HEART_HEALTH_SCALE = 10000\.0;', temple)
    for marker in ('HeartHealth"', 'HeartHP"'):
        assert 'marker == "' + marker in import_function, marker
    # Old saves: a full heart loads as 15100, a half heart as 7550, with the heart health research the same share
    assert heart_health_after_load('HeartHealth10000', 10000.0, HEART_HP, 1.0) == 15100.0
    assert heart_health_after_load('HeartHealth10000', 5000.0, HEART_HP, 1.0) == 7550.0
    assert heart_health_after_load('HeartHealth10000', 0.0, HEART_HP, 1.0) == 0.0
    assert heart_health_after_load('HeartHealth10000', 99999.0, HEART_HP, 1.0) == 15100.0
    factor = 1.698
    assert abs(heart_health_after_load('HeartHealth10000', 10000.0 * factor, HEART_HP * factor, factor) - HEART_HP * factor) < 1e-9
    assert abs(heart_health_after_load('HeartHealth10000', 5000.0 * factor, HEART_HP * factor, factor) - HEART_HP * factor / 2) < 1e-9
    # New saves round-trip their share, also with the research and for a ruin
    for max_hp in (HEART_HP, HEART_HP * factor, HEART_HP * 2.474):
        for health in (0.0, 1.0, 3775.0, max_hp / 3.0, max_hp):
            share = health / max_hp
            assert abs(heart_health_after_load('HeartHealthShare', float(repr(share)), max_hp, 1.0) - health) < 1e-9, (max_hp, health)
    assert heart_health_after_load('HeartHealthShare', 2.0, HEART_HP, 1.0) == HEART_HP
    assert heart_health_after_load('HeartHealthShare', 0.5, HEART_HP, 1.0) == 7550.0
    # The probe of check_dungeon_heart_combat.py runs the same cases against the production functions
    heart_probe = text('source/tests/check_dungeon_heart_combat.py')
    for marker in ('HeartHealthShare 0.5', 'HeartHealth10000 10000', 'HeartHealth10000 5000'):
        assert marker in heart_probe, marker
    print('check_creature_attributes (part H): ok')


check_part_h()

print('check_creature_attributes (part A): ok')


# ---- Part B: mana pool, costs, regeneration, save and network (plan sections 6.1-6.6)
def config_blocks(source, block_name):
    """Return the text of every [block_name] ... [/block_name] block of a cfg or level file."""
    return re.findall(r'^\[' + block_name + r'\]\n(.*?)^\[/' + block_name + r'\]', source, re.M | re.S)


def first_value(block, key):
    match = re.search(r'^\s*' + re.escape(key) + r'\s+(\S+)', block, re.M)
    return match[1] if match else None


def skill_names(block):
    """Skill names of the [CreatureSkills] list of a creature block, in file order."""
    lists = re.search(r'\[CreatureSkills\](.*?)\[/CreatureSkills\]', block, re.S)
    names = []
    for line in lists[1].splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            names.append(line.split()[0])
    return names


def mana_cost_model(group, skill_name, is_first_attack, carries_bow, manacost_percent, caster_shot, second_shot):
    """The cost rules of 6.3 as Creature::getSkillManaCost applies them."""
    if skill_name != 'MissileLaunch':
        return 0.0
    if is_first_attack and carries_bow:
        return 0.0
    caster = is_first_attack
    if group != 'none':
        caster = group == 'caster'
    base = caster_shot if caster else second_shot
    return base * max(0.0, 1.0 - manacost_percent / 100.0)


def check_mana_part_b():
    # 6.1 pool: Mana attribute x ManaPerPoint, full at spawn (start values of the section 4 table)
    max_mana = function(creature, 'double Creature::getMaxMana() const')
    assert 'getMana() * mDefinition->getManaPerPoint()' in max_mana
    assert abs(attribute_value(26.6667, 1, 1, 0.0) * 1.5 - 40.0) < 0.001, 'blitzer: 40 mana at level 1, never rounded'
    assert abs(attribute_value(35, 2, 1, 0.0) * 2 - 70.0) < 1e-9
    assert abs(attribute_value(10, 1, 30, 0.0) * 1 - 39.0) < 1e-9
    assert abs(attribute_value(25, 1, 10, 6.0) * 1.75 - (25 + 9 + 6) * 1.75) < 1e-9, 'equipment mana counts in the pool'
    constructor = creature.split('Creature::Creature(GameMap* gameMap, const CreatureDefinition* definition')[1].split('\nCreature::Creature(GameMap* gameMap)')[0]
    assert 'mMana = getMaxMana();' in constructor, 'a spawned creature has full mana'
    setup = function(creature, 'void Creature::setupDefinition(')
    assert 'if(mManaFromSave)' in setup and 'mMana = std::min(mMana, getMaxMana());' in setup
    assert 'else\n            mMana = getMaxMana();' in setup, 'old saves and level files load with full mana'
    set_level = function(creature, 'void Creature::setLevel(')
    assert 'const double previousMaxMana = getMaxMana();' in set_level and set_level.index('previousMaxMana = getMaxMana()') < set_level.index('mLevel = ')
    assert 'setCurrentMana(mMana * getMaxMana() / previousMaxMana);' in set_level, 'a level-up keeps the mana share like the HP'
    assert 'if(previousMaxMana > 0.0)' in set_level and 'setCurrentMana(mMana);' in set_level, 'pool of 0 does not divide'
    assert abs(30.0 * 90.0 / 60.0 - 45.0) < 1e-9, 'half the pool stays half the pool after the pool grows'

    # 6.2 regeneration: max / (ManaRefillSeconds x turns per second) every turn, capped, always running
    regen = function(creature, 'void Creature::regenerateMana()')
    assert 'getManaRefillSeconds() * ODApplication::turnsPerSecond' in regen
    assert 'maxMana / refillTurns' in regen and 'mMana >= maxMana' in regen
    upkeep = function(creature, 'void Creature::doUpkeep()')
    assert 'regenerateMana();' in upkeep and upkeep.index('regenerateMana();') > upkeep.index('checkLevelUp();')
    turns_per_second = float(re.search(r'turnsPerSecond = ([\d.]+);', text('source/ODApplication.cpp'))[1])
    refill_seconds = float(config_value(global_cfg, 'ManaRefillSeconds'))
    pool, mana, turns = 70.0, 0.0, 0
    while mana < pool:
        mana = min(pool, mana + pool / (refill_seconds * turns_per_second))
        turns += 1
    assert turns == int(refill_seconds * turns_per_second + 0.5) or turns == int(refill_seconds * turns_per_second) + 1, turns
    assert mana == pool and min(pool, mana + pool / (refill_seconds * turns_per_second)) == pool, 'never above the pool'

    # 6.3 costs: caster shot 2.5, the second MissileLaunch 5, free normal attacks, manacost% on every cost
    caster_shot = float(config_value(global_cfg, 'ManaPerCasterShot'))
    second_shot = float(config_value(global_cfg, 'ManaPerDragonSecondShot'))
    assert (caster_shot, second_shot) == (2.5, 5.0)
    cost = function(creature, 'double Creature::getSkillManaCost(const CreatureSkill& skill) const')
    assert 'getManaPerCasterShot()' in cost and 'getManaPerDragonSecondShot()' in cost
    assert 'skill.getSkillName() != "MissileLaunch"' in cost, 'Melee and every other line is free here'
    manacost = function(creature, 'double Creature::getManaCost(double baseCost) const')
    assert 'getSkillPassive("manacost%")' in manacost and '1.0 - getSkillPassive("manacost%") / 100.0' in manacost
    assert mana_cost_model('caster', 'MissileLaunch', True, False, 0, caster_shot, second_shot) == 2.5
    assert mana_cost_model('caster', 'MissileLaunch', True, False, 30, caster_shot, second_shot) == 1.75
    assert mana_cost_model('blitzer', 'MissileLaunch', False, False, 0, caster_shot, second_shot) == 5.0
    assert mana_cost_model('blitzer', 'MissileLaunch', True, False, 0, caster_shot, second_shot) == 5.0, 'level file lists the shot first'
    assert mana_cost_model('none', 'MissileLaunch', False, False, 0, caster_shot, second_shot) == 5.0
    assert mana_cost_model('archer', 'MissileLaunch', True, True, 0, caster_shot, second_shot) == 0.0, 'bow shot is free'
    assert mana_cost_model('archer', 'MissileLaunch', True, False, 0, caster_shot, second_shot) == second_shot, 'no archer special rule'
    assert mana_cost_model('caster', 'Melee', True, False, 0, caster_shot, second_shot) == 0.0
    assert mana_cost_model('blitzer', 'Explosion', False, False, 0, caster_shot, second_shot) == 0.0, 'Champion line is free'
    assert mana_cost_model('caster', 'MissileLaunch', True, False, 100, caster_shot, second_shot) == 0.0
    # The cost classes of the real type lists: casters pay per first shot, only the Dragon has a second shot
    weapon_types = {}
    for block in config_blocks(text('config/equipments.cfg'), 'Equipment'):
        weapon_types[first_value(block, 'Name')] = first_value(block, 'WeaponType')
    caster_types, second_line_types, bow_types = set(), set(), set()
    for block in config_blocks(creatures_cfg, 'Creature'):
        names = skill_names(block)
        attack_names = [name for name in names if name in ('Melee', 'MissileLaunch')]
        if 'MissileLaunch' not in attack_names:
            continue
        type_name = first_value(block, 'Name')
        spawn = [first_value(block, 'WeaponSpawnL'), first_value(block, 'WeaponSpawnR')]
        has_bow = any(weapon_types.get(weapon) in ('bow', 'crossbow') for weapon in spawn)
        if attack_names[0] != 'MissileLaunch':
            second_line_types.add(type_name)
        elif has_bow:
            bow_types.add(type_name)
        else:
            caster_types.add(type_name)
    assert caster_types == {'LizardMan', 'Lich', 'Wizard', 'Kreatur'}, caster_types
    assert second_line_types == {'Dragon'}, second_line_types
    assert bow_types == {'DarkElf', 'Elf'}, bow_types
    # A level-file Dragon lists the shot before the melee line: the cost follows its skill group, not the line order
    for level_name in ('levels/campaign/Bonus1.level', 'levels/skirmish/TestSingleplayerSmall.level'):
        for block in config_blocks(text(level_name), 'Creature'):
            if first_value(block, 'Name') == 'DragonBoss':
                names = [name for name in skill_names(block) if name in ('Melee', 'MissileLaunch')]
                assert names == ['MissileLaunch', 'Melee'], level_name
    assert 'if(group != "none")' in cost and 'casterShot = (group == "caster");' in cost and '"archer"' not in cost, 'no special rule for an archer without bow'

    # 6.4 not enough mana: the skill is not used, as with a cooldown; 6.5 mana is subtracted when the skill starts
    assert 'bool Creature::hasManaFor(' in creature and 'return mMana >= getSkillManaCost(skill);' in creature
    search = function(creature, 'bool Creature::searchBestTargetInList(')
    assert 'hasManaFor(*skillDataTmp.mSkill)' in search
    assert search.index('canBeUsedBy(this)') < search.index('hasManaFor(*skillDataTmp.mSkill)') < search.index('getRangeMax(this, entityAttackCheck)')
    support = upkeep[upkeep.index('We use creature skills if we can'):]
    assert support.index('hasManaFor(*skillData.mSkill)') < support.index('tryUseSupport') < support.index('payManaFor(*skillData.mSkill)')
    use_attack = function(creature, 'void Creature::useAttack(')
    assert use_attack.index('payManaFor(*skillData.mSkill);') < use_attack.index('skillData.mSkill->tryUseFight(')
    assert 'creature.hasManaFor(*skillData.mSkill)' in function(creature, 'bool isPossessedSkillReady(')
    possessed = function(creature, 'void Creature::possessedUseSkill(')
    assert possessed.index('tryUseSupport') < possessed.index('payManaFor(*skillData.mSkill);')
    pay = function(creature, 'void Creature::payManaFor(')
    assert 'setCurrentMana(mMana - cost);' in pay
    # No hard-coded mana number in the code paths
    for body in (cost, regen, pay):
        assert not re.search(r'\b(2\.5|5\.0|120)\b', body)

    # 6.6 save and load: a labelled token after the optional appearance, old saves end without it
    export_stream = function(creature, 'void Creature::exportToStream(std::ostream& os) const')
    assert 'os << "\\t" << MANA_SAVE_LABEL << mMana;' in export_stream
    assert export_stream.index('toToken(mAppearance)') < export_stream.index('MANA_SAVE_LABEL << mMana')
    import_stream = function(creature, 'bool Creature::importFromStream(std::istream& is)')
    assert 'while(is >> appearanceToken)' in import_stream and 'mManaFromSave = true;' in import_stream
    assert import_stream.index('MANA_SAVE_LABEL.size()') < import_stream.index('fromToken(appearanceToken')
    assert 'static const std::string MANA_SAVE_LABEL = "Mana=";' in creature
    label = 'Mana='
    for mana_text, expected in (('Mana=12.5', 12.5), ('Mana=0', 0.0)):
        assert mana_text.startswith(label) and float(mana_text[len(label):]) == expected
    # Same parse rule as the loader: the token is read as a number and rejects text and negative values
    for bad in ('Mana=', 'Mana=abc', 'Mana=-3'):
        value = bad[len(label):]
        try:
            ok = float(value) >= 0.0
        except ValueError:
            ok = False
        assert not ok, bad

    # 6.6 network: the current mana travels in the full and the update packet, before the appearance and the gold
    full_export = function(creature, 'void Creature::exportToPacket(ODPacket& os, const Seat* seat) const')
    full_import = function(creature, 'void Creature::importFromPacket(ODPacket& is)')
    update_export = function(creature, 'void Creature::exportToPacketForUpdate(ODPacket& os, Seat* seat)')
    update_import = function(creature, 'void Creature::updateFromPacket(ODPacket& is)')
    assert full_export.index('exportProgressToPacket(os, seat);') < full_export.index('os << mMana;') < full_export.index('toToken(mAppearance)')
    assert full_import.index('importProgressFromPacket(is);') < full_import.index('is >> mMana') < full_import.index('is >> appearanceToken')
    assert update_export.index('exportProgressToPacket(os, seat);') < update_export.index('os << mMana;') < update_export.index('os << mGoldCarried;')
    # The needs (urge and creature dirt) follow the carried gold as the last fields, the update gives them to the own seat only
    assert update_export.index('os << mGoldCarried;') < update_export.index('os << mUrge;') < update_export.index('os << mCreatureDirt;'), 'the needs come after the carried gold'
    assert update_export.rindex('os << 0.0;') > update_export.index('os << mCreatureDirt;') and 'if(seat == getSeat())' in update_export
    assert update_import.index('importProgressFromPacket(is);') < update_import.index('is >> mMana') < update_import.index('is >> mGoldCarried')
    # The clients are told when the ring crosses a step; the ring has 64 frames (steps 0..63)
    assert 'const uint32_t Creature::MANA_RING_STEPS = 63;' in creature
    set_mana = function(creature, 'void Creature::setCurrentMana(double mana)')
    assert 'step != mManaRingStepNotified' in set_mana and 'mNeedFireRefresh = true;' in set_mana
    assert 'std::max(0.0, std::min(mana, maxMana))' in set_mana, 'clamped to 0 .. max'
    for member in ('double          mMana;', 'bool            mManaFromSave;', 'uint32_t        mManaRingStepNotified;',
                   'static const uint32_t MANA_RING_STEPS;'):
        assert member in creature_h, member
    assert creature.count('mMana                    (0.0)') == 2, 'both constructors initialise the mana'


check_mana_part_b()
print('check_creature_attributes (part B, mana): ok')

def check_part_e():
    """Part E: the critical hit formula and roll at every damage source, digging crits, the cosmetic value, and the
    worker gold capacity and dig% formulas (sections 8.1-8.5 server side and 7.4 of the plan)."""
    creature = text('source/entities/Creature.cpp')
    creature_h = text('source/entities/Creature.h')
    combat = text('source/entities/CombatDamage.h')
    melee = text('source/creatureskill/CreatureSkillMeleeFight.cpp')
    one_hit = text('source/entities/MissileOneHit.cpp')
    launch = text('source/creatureskill/CreatureSkillMissileLaunch.cpp')
    explosion = text('source/creatureskill/CreatureSkillExplosion.cpp')
    area = text('source/creatureeffect/CreatureEffectAreaDamage.cpp')
    dig = text('source/creatureaction/CreatureActionDigTile.cpp')
    tunnel = text('source/creatureaction/CreatureActionTunnel.cpp')
    tile = text('source/entities/Tile.cpp')
    event_h = text('source/network/CosmeticEvent.h')

    # ---- 8.1 chance formula: CritChancePerDexterity x (start Dexterity + equipment Dexterity) + CritChancePerLevel x (L - 1)
    # + CritChanceBonus + crit passives + equipment CritChance, no upper limit
    per_dexterity = float(config_value(global_cfg, 'CritChancePerDexterity'))
    per_level = float(config_value(global_cfg, 'CritChancePerLevel'))

    def crit_chance(start_dexterity, level, bonus=0.0, passives=0.0, equipment_dexterity=0.0, equipment_crit=0.0):
        return per_dexterity * (start_dexterity + equipment_dexterity) + per_level * (level - 1) + bonus + passives + equipment_crit

    assert abs(crit_chance(20, 1) - 4.0) < 1e-9 and abs(crit_chance(25, 1) - 5.0) < 1e-9
    assert abs(crit_chance(20, 30) - (4.0 + 0.3 * 29)) < 1e-9, 'the level part grows the same for every group'
    assert abs(crit_chance(25, 10, bonus=15.0) - (5.0 + 2.7 + 15.0)) < 1e-9, 'Champion bonus 15'
    assert crit_chance(20, 30, passives=40.0, equipment_crit=60.0) > 100.0, 'no upper limit'
    chance = function(creature, 'double Creature::getCritChance() const')
    assert 'getCritChancePerDexterity() * dexterity' in chance
    assert 'mDefinition->getDexterity() +' in chance and 'EquipmentAttribute::dexterity' in chance
    assert 'getCritChancePerLevel() * static_cast<double>(mLevel - 1)' in chance
    assert 'mDefinition->getCritChanceBonus()' in chance and 'getSkillPassive("crit")' in chance
    assert 'getEquipmentCritChance()' in chance
    assert 'std::min' not in chance and 'std::max' not in chance, 'no upper limit'
    roll = function(creature, 'bool Creature::rollCritical() const')
    assert 'Random::Double(0.0, 100.0) < chance' in roll and 'chance <= 0.0' in roll
    assert 'double getCritChance() const;' in creature_h and 'bool rollCritical() const;' in creature_h
    assert 'inline bool rollCriticalChance(double chancePercent)' in combat

    # ---- 8.3 the multiplier acts on every damage value before the defense of the target is subtracted
    assert config_value(global_cfg, 'CritDamageMultiplier') == '2'

    def after_defense(minimum, maximum, defense, multiplier):
        return max(minimum * multiplier - defense, 0.0), max(maximum * multiplier - defense, 0.0)

    assert after_defense(10, 20, 6, 2) == (14, 34), 'multiplied first, then the defense is subtracted'
    assert after_defense(10, 20, 6, 2) != tuple(2 * max(v - 6, 0) for v in (10, 20))
    apply = function(combat, 'inline void applyCriticalToRange(')
    for name in ('phyMin', 'phyMax', 'magMin', 'magMax', 'eleMin', 'eleMax'):
        assert name + ' *= factor;' in apply, name
    assert 'getCritDamageMultiplier()' in apply
    melee_body = function(melee, 'bool CreatureSkillMeleeFight::tryUseFight(')
    assert melee_body.index('CombatDamage::scale(') < melee_body.index('applyCriticalToRange(') < melee_body.index('CombatDamage::roll(')
    assert melee_body.index('CombatDamage::roll(') < melee_body.index('* modifier'), 'the strength modifier follows the roll'
    assert melee_body.index('rollMeleeDefence(false)') < melee_body.rindex('creature->rollCritical()'), 'never critical when missed or avoided'
    assert melee_body.count('creature->rollCritical()') == 2, 'one roll for a creature target, one for a building'
    assert 'phyAtk *= criticalFactor;' in melee_body and 'eleAtk *= criticalFactor;' in melee_body, 'building damage x multiplier'
    hurt = function(one_hit, 'void MissileOneHit::hurt(')
    assert hurt.index('rollMeleeDefence(true)') < hurt.index('rollCriticalChance(mShotCritChance)') < hurt.index('applyCriticalToRange(') < hurt.index('CombatDamage::roll(')
    assert 'mPhysicalDamage * criticalFactor' in hurt, 'building damage of a shot x multiplier'
    assert 'setShotCritChance(creature->getCritChance())' in launch, 'the shot carries the chance of its shooter'

    # ---- 8.4 sources roll, the excluded sources do not
    sources = {'source/creatureskill/CreatureSkillMeleeFight.cpp', 'source/creatureskill/CreatureSkillExplosion.cpp',
               'source/creatureeffect/CreatureEffectAreaDamage.cpp', 'source/creatureaction/CreatureActionDigTile.cpp',
               'source/creatureaction/CreatureActionTunnel.cpp', 'source/entities/MissileOneHit.cpp'}
    users = set()
    for path in (root / 'source').rglob('*.cpp'):
        if 'tests' in path.parts:
            continue
        body = path.read_text(encoding='utf-8', errors='replace')
        if 'rollCritical()' in body or 'rollCriticalChance(' in body:
            users.add(path.relative_to(root).as_posix())
    users.discard('source/entities/Creature.cpp')
    assert sources <= users, sources - users
    excluded = ('source/creatureskill/CreatureSkillDrain.cpp', 'source/creatureeffect/CreatureEffectSlap.cpp',
                'source/creatureeffect/CreatureEffectBurn.cpp', 'source/creatureeffect/CreatureEffectFrozen.cpp',
                'source/creatureeffect/CreatureEffectHeal.cpp', 'source/creatureskill/CreatureSkillHealSelf.cpp',
                'source/rooms/RoomTorture.cpp', 'source/rooms/RoomPrison.cpp', 'source/spells/SpellLightning.cpp',
                'source/spells/SpellTremor.cpp', 'source/traps/TrapSpike.cpp', 'source/traps/TrapFireburst.cpp',
                'source/traps/TrapGas.cpp', 'source/traps/TrapLightning.cpp', 'source/traps/TrapDoor.cpp',
                'source/traps/TrapFreeze.cpp', 'source/entities/MissileBoulder.cpp',
                'source/creatureaction/CreatureActionClaimGroundTile.cpp',
                'source/creatureaction/CreatureActionClaimWallTile.cpp')
    for name in excluded:
        assert name not in users, name + ' must not roll critical hits (percent sources, heals, traps, spells, claiming)'
    explosion_body = function(explosion, 'bool CreatureSkillExplosion::tryUseFight(')
    assert explosion_body.index('creature->rollCritical()') < explosion_body.index('new CreatureEffectExplosion(')
    assert 'damageFactor *= ConfigManager::getSingleton().getCritDamageMultiplier();' in explosion_body
    area_body = function(area, 'void CreatureEffectAreaDamage::applyEffect(')
    assert 'creature.rollCritical()' in area_body and area_body.index('rollCritical()') < area_body.index('takeDamage(')

    # ---- 8.4 digging: one roll per dig step; a critical step removes 2 x the fullness on dirt and walls and pays 2 x the
    # step gold on gold and gem walls (on a gold wall at most what is left); experience follows the configured dig factors
    handle = function(dig, 'bool CreatureActionDigTile::handleDigTile(')
    assert handle.count('creature.rollCritical()') == 1, 'one roll per dig step'
    assert handle.index('creature.rollCritical()') < handle.index('digOutGold(digFactor * criticalFactor)')
    assert 'getCritDamageMultiplier()' in handle
    assert re.search(r'receiveExp\(ConfigManager::getSingleton\(\)\.getGoldDigXpFactor\(\) \* creature\.getDigRate\(\)\s*/\s*ConfigManager::getSingleton\(\)\.getWorkXpRateDivisor\(\)\)', handle)
    assert re.search(r'receiveExp\(ConfigManager::getSingleton\(\)\.getDigXpFactor\(\) \* creature\.getDigRate\(\)\s*/\s*ConfigManager::getSingleton\(\)\.getWorkXpRateDivisor\(\)\)', handle)
    assert not re.search(r'receiveExp\([^;]*(digFactor|criticalFactor|getDigFactor)', handle), 'experience ignores dig% and crits'
    assert 'fireCriticalOnStructure("dig"' in handle
    tunnel_body = function(tunnel, 'bool CreatureActionTunnel::handleTunnel(') if 'bool CreatureActionTunnel::handleTunnel(' in tunnel else tunnel
    assert tunnel_body.count('creature.rollCritical()') == 1
    assert 'tile->digOut(creature.getDigRate() * creature.getDigFactor() * criticalFactor)' in tunnel_body
    gold_step = float(config_value(global_cfg, 'GoldPerDigStep'))
    gem_step = float(config_value(global_cfg, 'GemGoldPerDigStep'))
    seam = float(config_value(global_cfg, 'GoldPerSeamTile'))

    def gold_step_pay(remaining, dig_percent, critical):
        """Mirrors Tile::digOutGold with the factor of the caller: the last step pays what is left."""
        step = gold_step * (1.0 + dig_percent / 100.0) * (float(config_value(global_cfg, 'CritDamageMultiplier')) if critical else 1.0)
        return min(step, remaining)

    assert gold_step_pay(seam, 0, False) == 25.0 and gold_step_pay(seam, 0, True) == 50.0
    assert abs(gold_step_pay(seam, 25, True) - 62.5) < 1e-9, 'dig% and a critical step multiply'
    assert gold_step_pay(30.0, 0, True) == 30.0, 'at most what is left on a gold wall'
    assert abs(gem_step * 2 - 33.34) < 1e-9
    assert 'skirmishPercent / 100.0 * stepFactor;' in function(tile, 'double Tile::digOutGold(double stepFactor)')

    # ---- 8.5 cosmetic value 7, the event for buildings and walls, no damage number
    assert re.search(r'critical = 7\b', event_h)
    fire = function(creature, 'void Creature::fireHitResult(')
    assert 'CosmeticHitResult::critical' in fire and fire.index('damageDone <= 0.0') < fire.index('else if(critical)')
    structure = function(creature, 'void Creature::fireCriticalOnStructure(')
    assert 'CosmeticHitResult::critical' in structure and 'event.mText = kind;' in structure and 'mObject' not in structure
    assert 'void fireCriticalOnStructure(' in creature_h and 'void fireCriticalSpell(' in creature_h

    # ---- 7.4 workers and gold: capacity = MaxGoldCarryable x (1 + GoldCarryPerStrength x (Strength - start Strength))
    # x (1 + carry% / 100), rounded down; the epsilon keeps exact products such as 113 from falling to 112
    carry_per_strength = float(config_value(global_cfg, 'GoldCarryPerStrength'))
    epsilon = 1e-9

    def capacity(max_carry, strength_gain, carry_percent):
        return int(math.floor(max_carry * (1.0 + carry_per_strength * strength_gain) * (1.0 + carry_percent / 100.0) + epsilon))

    assert capacity(100, 0, 0) == 100
    assert capacity(100, 29, 0) == 129, 'level 30 worker without skills'
    assert capacity(100, 29, 50) == 193, 'Deep Pockets rank 5 at most 193'
    assert capacity(100, 13, 0) == 113 and int(math.floor(100 * (1.0 + carry_per_strength * 13))) == 112
    assert capacity(0, 29, 50) == 0, 'a creature that cannot carry gold stays at 0'
    cap = function(creature, 'int32_t Creature::getGoldCapacity() const')
    assert 'if(baseCapacity <= 0)' in cap and 'return baseCapacity;' in cap
    assert 'getStrength() - mDefinition->getStrength()' in cap and 'getGoldCarryPerStrength()' in cap
    assert 'getSkillPassive("carry%")' in cap and 'std::floor(capacity + GOLD_CAPACITY_ROUNDING_EPSILON)' in cap
    assert re.search(r'GOLD_CAPACITY_ROUNDING_EPSILON = 1e-9;', creature)
    assert 'double Creature::getDigFactor() const' in creature and 'getSkillPassive("dig%")' in creature

    # claim%: the claim rate is the config rate x (1 + claim% / 100) for every reader
    claim = function(creature, 'double Creature::getClaimRate() const')
    assert 'mClaimRate * (1.0 + getSkillPassive("claim%") / 100.0)' in claim
    assert 'double getClaimRate() const;' in text('source/entities/Creature.h')
    assert abs(1.5 * (1.0 + 20 / 100.0) - 1.8) < 1e-9, 'claim% 20 on a rate of 1.5'
    assert 'mClaimRate' not in creature.replace(claim, '').replace('mClaimRate = mDefinition->getClaimRate();', '').replace('mClaimRate += mDefinition->getClaimRatePerLevel()', '').replace('mClaimRate               (0.0)', '').replace('os << mClaimRate;', '').replace('is >> mClaimRate', ''), 'all readers use getClaimRate()'
    for action_file in glob.glob(str(root / 'source/creatureaction/*.cpp')):
        assert 'mClaimRate' not in open(action_file, encoding='utf-8').read(), action_file

    # ---- the shot keeps its chance in the save: written after the accuracy, read only when present
    export = function(one_hit, 'void MissileOneHit::exportToStream')
    load = function(one_hit, 'bool MissileOneHit::importFromStream')
    assert export.index('ShotAccuracy') < export.index('CritChance') and 'mShotCritChance' in export
    assert '"CritChance"' in load and 'mShotCritChance = critChance;' in load
    assert 'mShotCritChance(0.0)' in one_hit and one_hit.count('mShotCritChance(0.0)') == 2


import math
check_part_e()

# Check client overlays and profile displays while keeping HUD styling separate from creature mana tint.
def check_part_g():
    """Part G: the client side. The mana ring in the overhead status (6.7), the critical hit feedback with the sound
    (8.5 client and 8.6 file) and the displays of attributes, mana, path and skills (11)."""
    overlay_h = text('source/render/MovableTextOverlay.h')
    overlay_cpp = text('source/render/MovableTextOverlay.cpp')
    status = text('source/render/CreatureOverlayStatus.cpp')
    creature = text('source/entities/Creature.cpp')
    creature_h = text('source/entities/Creature.h')
    visuals = text('source/render/CreatureWeaponVisuals.cpp')
    event_h = text('source/network/CosmeticEvent.h')
    gui = text('source/render/Gui.cpp')
    layout = text('gui/WindowCreatureProfilePage.layout')
    reactions = text('config/creatureReactions.cfg')
    credits = text('CREDITS')

    # ---- 6.7 the offset mechanism: the drawing moves, the next child still centres on the unshifted box
    assert 'Ogre::Real mOffsetX = 0.0f;' in overlay_h and 'Ogre::Real mOffsetY = 0.0f;' in overlay_h
    assert 'void setOffset(uint32_t childOverlayId, Ogre::Real x, Ogre::Real y);' in overlay_h
    set_offset = function(overlay_cpp, 'void MovableTextOverlay::setOffset(')
    assert 'mOffsetX = x;' in set_offset and 'mOffsetY = y;' in set_offset
    update = function(overlay_cpp, 'void MovableTextOverlay::update(')
    assert ('childPosition.x + childOverlay.mOffsetX * childOverlay.mScale / '
            'Ogre::OverlayManager::getSingleton().getViewportWidth()') in update
    assert ('childPosition.y + childOverlay.mOffsetY * childOverlay.mScale / '
            'Ogre::OverlayManager::getSingleton().getViewportHeight()') in update
    assert 'previousPosition = childPosition;' in update, 'the next child centres on the unshifted position'

    # ---- 6.7 the mana ring: health-ring backing and eight tinted segments, right of the health ring
    enum_body = status[status.index('enum class CreatureOverlays'):status.index('};', status.index('enum class CreatureOverlays'))]
    assert enum_body.index('mana,') < enum_body.index('nbCreatureOverlays'), 'enum value mana before nbCreatureOverlays'
    constructor = function(status, 'CreatureOverlayStatus::CreatureOverlayStatus(')
    assert constructor.rindex('CreatureOverlays::mana') > constructor.rindex('CreatureOverlays::status'), 'created last'
    assert 'createChildOverlay("MedievalSharp", 30,\n        Ogre::ColourValue::White, manaMaterial, false)' in constructor
    assert 'forceTextArea(manaId, MANA_RING_SIZE, MANA_RING_SIZE)' in constructor
    assert 'setOffset(manaId, MANA_RING_OFFSET_X, 0.0f)' in constructor and 'displayOverlay(manaId, -1)' in constructor
    assert 'MANA_RING_BASE_MATERIAL + Helper::toString(MANA_RING_SEGMENTS)' in constructor
    assert 'MANA_RING_BACKING_MATERIAL = "CreatureOverlay7"' in status
    assert 'MANA_RING_BASE_MATERIAL = "ManaRing"' in status
    assert 'MANA_RING_SEGMENTS = 8;' in status
    assert 'MANA_RING_SIZE = 64;' in status and 'MANA_RING_OFFSET_X = 64;' in status
    channels = [int(re.search(name + r' = (\d+)\.0f', status)[1]) for name in ('MANA_RING_RED', 'MANA_RING_GREEN', 'MANA_RING_BLUE')]
    assert channels == [127, 227, 166]
    # The painted HUD uses ivory text; the creature's mana ring keeps its original green tint.
    hud = ET.fromstring(text('gui/ModeGame.layout'))
    mana_display = hud.find('.//Window[@name="ManaDisplay"]')
    assert mana_display.find('Property[@name="TextColours"]').get('value') == 'FFF0E2C0', 'ivory HUD mana number'
    progress = function(status, 'void CreatureOverlayStatus::updateProgress(')
    assert 'getCurrentMana() / maxMana' in progress and 'manaShare * MANA_RING_SEGMENTS' in progress
    assert 'MANA_RING_BASE_MATERIAL + Helper::toString(manaSegments)' in progress
    assert 'displayOverlay(manaId, 0)' in progress

    # ---- 8.5 client: value 7 and the feedback (sparks on the target creature, else on the attacker, plus the sound)
    assert 'critical = 7' in event_h
    feedback = function(visuals, 'void showCriticalFeedback(')
    assert 'Creature* shown = (target != nullptr) ? target : attacker;' in feedback
    assert 'queueReaction(reactions, shown->getName(), CRITICAL_REACTION_EVENT, CRITICAL_DELAY)' in feedback
    assert 'playSpatialSound(CRITICAL_SOUND_FAMILY' in feedback
    assert 'CRITICAL_REACTION_EVENT = "CriticalHit"' in visuals and 'CRITICAL_SOUND_FAMILY = "Creatures/Default/Critical"' in visuals
    hit_result = function(visuals, 'void noteHitResult(')
    case = hit_result[hit_result.index('CosmeticHitResult::critical'):]
    case = case[:case.index('break;')]
    assert 'showCriticalFeedback(reactions, target, attacker);' in case
    assert 'noteHitEvent(reactions, attacker, target' in case, 'a critical hit flinches like a hit'
    assert 'damage' not in feedback.lower(), 'no damage number'
    event = reactions[reactions.index('Name        CriticalHit'):]
    event = event[:event.index('[/Event]')]
    assert 'Effect  ReactionSparks' in event
    for forbidden in ('Clip', 'Fallback', 'Emote', 'Motion'):
        assert forbidden not in event, 'no new animation or picture: ' + forbidden

    # ---- 8.6 the sound file and its CREDITS row
    sound = root / 'sounds/Spatial/Creatures/Default/Critical/FxCriticalHit01.ogg'
    assert sound.is_file() and sound.stat().st_size > 0
    assert 'sounds/Spatial/Creatures/Default/Critical/FxCriticalHit01.ogg' in credits
    assert 'opengameart.org/content/37-hitspunches' in credits, 'real recording with source URL'
    assert not (root / 'tools/gen_critical_hit_sound.py').exists(), 'no generator any more'

    # ---- 11 the stats text: after "Level:" the attributes, critical chance, mana, path and skills
    stats = function(creature, 'std::string Creature::getStatsText(const Seat* viewer)')
    assert 'return getStatsText(getSeat());' in function(creature, 'std::string Creature::getStatsText()')
    order = ['"Level: " << getLevel()', '"Strength / Dexterity / Life / Mana: "', '"Critical chance: "',
             '"Mana: " << formatDisplayNumber(getCurrentMana()) << " / " << formatDisplayNumber(getMaxMana())',
             '"Path: " << getSkillPathText()', '"Skills: " << getSkillListText()', '"Experience: "']
    positions = [stats.index(part) for part in order]
    assert positions == sorted(positions), 'stats text order'
    assert 'formatFixedNumber(getCritChance()) << " %"' in stats, 'x.x %'
    assert 'tempSS << "Weapons:"' in stats, 'the weapon lines stay'
    assert 'DISPLAY_NONE_TEXT = "none"' in creature, 'none when empty'
    skills = function(creature, 'std::string Creature::getSkillListText() const')
    assert 'it->second == 0' in skills and 'result += skillName + " " + Helper::toString(it->second);' in skills
    assert 'result += ", "' in skills and 'findTierFourById' in skills and 'DISPLAY_NONE_TEXT' in skills
    attributes = function(creature, 'std::string Creature::getAttributeSummaryText() const')
    parts = ['"Strength "', '" - Dexterity "', '" - Life "', '"\\nMana "', '" - Critical "', '" %"']
    positions = [attributes.index(part) for part in parts]
    assert positions == sorted(positions)
    equipment = function(creature, 'std::string Creature::getEquipmentText() const')
    assert equipment.index('right + " / " + left') > 0 and 'mWeaponR->getName()' in equipment
    for name in ('getSkillPathText', 'getSkillListText', 'getAttributeSummaryText', 'getEquipmentText'):
        assert 'std::string ' + name + '() const;' in creature_h

    # ---- 11 the Dungeonbook profile: four lines below "Job:" in the order of the plan
    profile = function(creature, 'float Creature::fillProfilePage(')
    lines = ['setText("Job: " + profile.mJob)', 'getChild("AttributesText")->setText(getAttributeSummaryText())',
             'getChild("EquipmentText")->setText("Equipment: " + getEquipmentText())',
             'getChild("PathText")->setText("Path: " + getSkillPathText())',
             'getChild("SkillsText")->setText("Skills: " + getSkillListText())', 'getChild("BioText")']
    positions = [profile.index(line) for line in lines]
    assert positions == sorted(positions), 'profile lines order'
    windows = {}
    for match in re.finditer(r'<Window type="OD/StaticText" name="(\w+)" >(.*?)</Window>', layout, re.S):
        windows[match[1]] = match[2]
    job = windows['JobText']
    for name in ('AttributesText', 'EquipmentText', 'PathText', 'SkillsText'):
        block = windows[name]
        # The profile rows reserve the existing scrollbar gutter at the right edge.
        assert 'value="{{0.0,16},{0.0,174},{1.0,-32},{0.0,194}}"' in block, name
        for key in ('FrameEnabled', 'BackgroundEnabled', 'Font', 'VertFormatting', 'HorzFormatting'):
            assert re.search(r'name="' + key + r'" value="([^"]*)"', block)[1] == ('WordWrapLeftAligned' if key == 'HorzFormatting' else re.search(
                r'name="' + key + r'" value="([^"]*)"', job)[1]), name + ' ' + key
    names = re.findall(r'<Window type="OD/\w+" name="(\w+)"', layout)
    assert names.index('AttributesText') < names.index('EquipmentText') and names.index('PathText') < names.index('SkillsText')
    children = [window.attrib['name'] for window in ET.fromstring(layout).find('Window').findall('Window')]
    assert children[children.index('AttributesText'):children.index('EquipmentText') + 1] == ['AttributesText', 'EquipmentRow', 'EquipmentText']
    assert 'name="FrameEnabled" value="False"' in windows['AttributesText'] and 'MedievalSharp-8' in windows['AttributesText']
    flow = gui[gui.index('const char* const PROFILE_FLOW_ROWS[]'):]
    flow = flow[:flow.index('};')]
    assert flow.index('"AttributesText", "EquipmentText", "EquipmentRow"') > 0
    for name in ('PathText', 'SkillsText', 'BioText'):
        assert '"' + name + '"' in flow
    layout_function = function(gui, 'float Gui::layoutCreatureProfilePage(')
    assert layout_function.index('page->getChild("AttributesText")') < layout_function.index('const char* const personalRows')
    assert layout_function.index('page->getChild("EquipmentRow")') < layout_function.index('page->getChild("AttributesText")') < layout_function.index('const char* const personalRows')
    assert 'slot < 13' in layout_function and 'columns[slot] * edge' in layout_function and 'rows[slot] * edge' in layout_function
    assert ('const char* const textRowsBefore[] = {"PathText", "SkillsText", "BioText", "LikesText",\n'
            '        "DislikesText", "RelationsText"};') in layout_function
    assert 'for(std::size_t i = 0; i < 6; ++i)\n        y = layoutProfileTextRow(page->getChild(textRowsBefore[i]), y, scale);' in layout_function



check_part_g()
print('check_creature_attributes (part G): ok')

print('check_creature_attributes (part E): ok')
