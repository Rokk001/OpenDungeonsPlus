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

print('check_creature_attributes (part A): ok')
