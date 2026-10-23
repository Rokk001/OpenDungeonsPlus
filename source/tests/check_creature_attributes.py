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
    # step gold on gold and gem walls (on a gold wall at most what is left); experience stays as it is
    handle = function(dig, 'bool CreatureActionDigTile::handleDigTile(')
    assert handle.count('creature.rollCritical()') == 1, 'one roll per dig step'
    assert handle.index('creature.rollCritical()') < handle.index('digOutGold(digFactor * criticalFactor)')
    assert 'getCritDamageMultiplier()' in handle
    assert 'receiveExp(1.5 * creature.getDigRate() / 20.0)' in handle and 'receiveExp(creature.getDigRate() / 20.0)' in handle
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

    # ---- the shot keeps its chance in the save: written after the accuracy, read only when present
    export = function(one_hit, 'void MissileOneHit::exportToStream')
    load = function(one_hit, 'bool MissileOneHit::importFromStream')
    assert export.index('ShotAccuracy') < export.index('CritChance') and 'mShotCritChance' in export
    assert '"CritChance"' in load and 'mShotCritChance = critChance;' in load
    assert 'mShotCritChance(0.0)' in one_hit and one_hit.count('mShotCritChance(0.0)') == 2


import math
check_part_e()
print('check_creature_attributes (part E): ok')
