"""Check the creature attribute model: config fields and keys, attribute levels and the derived values (no build needed).

Part A: the [Stats] fields of creatures.cfg, the equipment fields, the global.cfg keys, the attribute level formulas
and the places that use the attribute level instead of the creature level. Other parts are added by later packages.
"""
from pathlib import Path
import re
import sys

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
    # Worker hit points are not changed by this plan
    assert creatures['Kobold']['MinHP'] == '62' and creatures['DwarfWorker']['MinHP'] == '62'

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
