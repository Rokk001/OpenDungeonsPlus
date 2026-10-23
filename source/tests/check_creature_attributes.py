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
        caster = group in ('caster', 'archer')
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
    assert 'setCurrentMana(mMana);' in set_level, 'a level-up caps the mana at the new pool size'

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
    assert 'if(group != "none")' in cost and '(group == "caster") || (group == "archer")' in cost

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
    assert update_export.rstrip().rstrip('}').rstrip().endswith('os << mGoldCarried;'), 'the carried gold stays the last field'
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
