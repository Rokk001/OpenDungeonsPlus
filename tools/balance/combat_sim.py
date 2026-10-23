#!/usr/bin/env python3
"""Turn-based combat comparisons against the actual creature and item configuration."""

import argparse
import dataclasses
from dataclasses import dataclass, replace
import json
from pathlib import Path
import random
import re
import statistics

CHANNELS = ("Physical", "Magical", "Element")
MAX_LEVEL = 30
DUEL_LIMIT = 5000
GROUP_LIMIT = 20000
HP_SCALE = 2.05
# Mirror of the level curves of config/global.cfg (CreatureDamageGrowth, CreatureDamageExponent,
# CreatureHpGrowthPerLevel, CooldownReductionPerLevel); the creature check asserts that they match the file.
DAMAGE_GROWTH = 0.221
DAMAGE_EXPONENT = 1.167
HP_GROWTH_PER_LEVEL = 0.018
COOLDOWN_REDUCTION_PER_LEVEL = 0.0


# Read named configuration blocks, ignoring comments and section delimiters.
def definitions(path, section, tag):
    text = path.read_text(encoding="utf-8")
    text = text[text.rindex("[" + section + "]"):]
    result = {}
    for block in re.findall(r"\[" + tag + r"\](.*?)\[/" + tag + r"\]", text, re.S):
        fields = {}
        for line in block.splitlines():
            words = line.split()
            if len(words) >= 2 and not words[0].startswith("#"):
                fields.setdefault(words[0], words[1:])
        result[fields["Name"][0]] = (fields, block)
    return result


# Evaluate the separate level curves within the server's level bounds.
def multiplier(level, kind):
    level = max(1, min(MAX_LEVEL, level))
    if kind == "damage":
        return 1 + DAMAGE_GROWTH * (level - 1) ** DAMAGE_EXPONENT
    if kind == "hp":
        return multiplier(level, "damage") * (1 + HP_GROWTH_PER_LEVEL * (level - 1))
    if kind == "attack":
        return float(level)
    if kind == "defense":
        return float(level)
    raise ValueError(kind)


# Retain configured linear growth whenever it exceeds the selected curve.
def combat_stat(base, per_level, level, kind):
    level = max(1, min(MAX_LEVEL, level))
    return max(base + (level - 1) * per_level, base * multiplier(level, kind))


# Preserve the former interpolated power curve for damage against buildings.
def building_stat(base, per_level, level):
    anchors = (1, 1.25, 1.5, 1.75, 2, 2.25, 2.5, 3, 4, 6)
    position = (max(1, min(MAX_LEVEL, level)) - 1) * 9 / 29
    index = int(position)
    power = anchors[-1] if index == 9 else anchors[index] + (anchors[index + 1] - anchors[index]) * (position - index)
    return max(base + (max(1, level) - 1) * per_level, base * power)


# Hold a combatant's statistics and mutable remaining health.
@dataclass
class Unit:
    name: str
    level: int
    hp: float
    minimum: tuple
    maximum: tuple
    defense: tuple
    attack_rating: float
    defense_rating: float
    cooldown: float
    melee: bool
    avoidance: str
    shield: bool
    parry: float


# Load combat statistics directly from the supplied repository's configuration.
class Roster:
    # Cache current definitions without using an external statistics snapshot.
    def __init__(self, root):
        self.root = Path(root)
        self.creatures = definitions(self.root / "config/creatures.cfg", "CreatureDefinitions", "Creature")
        self.equipment = definitions(self.root / "config/equipments.cfg", "EquipmentDefinitions", "Equipment")
        self.global_values = {}
        for line in (self.root / "config/global.cfg").read_text(encoding="utf-8").splitlines():
            words = line.split()
            if len(words) == 2 and not words[0].startswith("#"):
                self.global_values[words[0]] = words[1]

    # Read a numeric field using the optional-field default when absent.
    @staticmethod
    def number(fields, key, default=0):
        return float(fields.get(key, [default])[0])

    # Select the first level-one melee or single-target attack in definition order.
    def attack(self, name):
        section = re.search(r"\[CreatureSkills\](.*?)\[/CreatureSkills\]", self.creatures[name][1], re.S)
        if section is not None:
            for line in section[1].splitlines():
                words = line.split()
                if not words or words[0].startswith("#"):
                    continue
                if words[0] == "Melee" and int(words[3]) <= 1:
                    return words, 4, 10
                if words[0] == "MissileLaunch" and int(words[5]) <= 1:
                    return words, 9, 15
        raise ValueError("No level-one attack: " + name)

    # Enumerate ordinary fighters, excluding the invulnerable summoned creature.
    def fighters(self):
        result = []
        for name, (fields, _) in self.creatures.items():
            if fields.get("CreatureJob", [""])[0] == "Fighter" and self.number(fields, "Champion") != 1:
                self.attack(name)
                result.append(name)
        return result

    # Apply level curves, typed item bonuses and melee recovery damage compensation.
    def unit(self, name, level=1):
        level = max(1, min(MAX_LEVEL, level))
        fields = self.creatures[name][0]
        attack, old_start, range_start = self.attack(name)
        items = []
        for hand in ("L", "R"):
            item = fields.get("WeaponSpawn" + hand, ["none"])[0]
            if item != "none":
                items.append(self.equipment[item][0])
        minimum, maximum, defense = [], [], []
        for i, channel in enumerate(CHANNELS):
            old = float(attack[old_start + 2 * i]) + float(attack[old_start + 2 * i + 1])
            lo = float(attack[range_start + 2 * i]) if len(attack) >= range_start + 6 else old
            hi = float(attack[range_start + 2 * i + 1]) if len(attack) >= range_start + 6 else old
            minimum.append(lo * multiplier(level, "damage") + sum(self.number(item, channel + "DamageMin", self.number(item, channel + "Damage")) for item in items))
            maximum.append(hi * multiplier(level, "damage") + sum(self.number(item, channel + "Damage") for item in items))
            defense.append(combat_stat(self.number(fields, channel + "Defense"), self.number(fields, channel + "Def/Level"), level, "damage") + sum(self.number(item, channel + "Defense") for item in items))
        melee = attack[0] == "Melee"
        weapon_cooldowns = [self.number(item, "CooldownNbTurns") for item in items if self.number(item, "CooldownNbTurns") > 0]
        skill_cooldown = float(attack[1])
        weapon_cooldown = max(weapon_cooldowns, default=0) if melee else 0
        cooldown = max(skill_cooldown, weapon_cooldown)
        timing_factor = weapon_cooldown / skill_cooldown if weapon_cooldown > skill_cooldown > 0 else 1
        minimum = [value * timing_factor for value in minimum]
        maximum = [value * timing_factor for value in maximum]
        cooldown = max(1, cooldown * (1 - COOLDOWN_REDUCTION_PER_LEVEL * (level - 1))) if cooldown else 0
        parry = 0
        shield = False
        for item in items:
            weapon_type = item.get("WeaponType", [""])[0]
            if not weapon_type:
                mesh = item.get("MeshName", [""])[0].lower()
                weapon_type = "sword"
                for legacy_type, words in (("shield", ("shield",)), ("bow", ("bow",)), ("axe", ("axe",)),
                                           ("hammer", ("hammer", "mace")), ("spear", ("spear", "lance", "pike")),
                                           ("dagger", ("dagger", "knife")), ("staff", ("staff", "wand"))):
                    if any(word in mesh for word in words):
                        weapon_type = legacy_type
                        break
            if weapon_type == "shield":
                shield = True
            elif weapon_type in ("sword", "axe", "dagger", "club", "mace", "hammer", "scepter", "spear", "polearm"):
                base = self.number(item, "ParryBase", float(self.global_values["ParryBase"]))
                step = self.number(item, "ParryPerLevel", float(self.global_values["ParryPerLevel"]))
                cap = self.number(item, "ParryMax", float(self.global_values["ParryMax"]))
                parry = max(parry, max(0, min(cap, base + step * level)))
        return Unit(name, level, combat_stat(self.number(fields, "MinHP"), self.number(fields, "HP/Level"), level, "hp"),
                    tuple(minimum), tuple(maximum), tuple(defense),
                    combat_stat(self.number(fields, "AttackRating", 300), 0, level, "attack") + sum(self.number(item, "AttackRating") for item in items),
                    combat_stat(self.number(fields, "DefenseRating", 100), 0, level, "defense") + sum(self.number(item, "DefenseRating") for item in items),
                    cooldown, melee, fields.get("Avoidance", ["none"])[0], shield, parry)

    # Evaluate exactly one configured avoidance type after a landed hit.
    def avoidance_chance(self, target, melee):
        if int(self.global_values.get("MeleeDodgeParry", "1")) == 0:
            return 0
        prefix = None
        if target.avoidance == "dodge":
            prefix = "Dodge"
        elif target.avoidance == "block" and target.shield:
            prefix = "ShieldBlock"
        elif target.avoidance == "parry" and melee:
            return target.parry
        if prefix is None:
            return 0
        return max(0, min(float(self.global_values[prefix + "Max"]), float(self.global_values[prefix + "Base"]) + target.level * float(self.global_values[prefix + "PerLevel"])))


# Compute the bounded hit percentage independently of avoidance.
def hit_chance(attacker, target):
    return max(5, min(95, 200 * attacker.attack_rating / (attacker.attack_rating + target.defense_rating) * attacker.level / (attacker.level + target.level)))


# Subtract defense separately in each channel before summing the range endpoints.
def damage_bounds(attacker, target):
    return (sum(max(value - defense, 0) for value, defense in zip(attacker.minimum, target.defense)),
            sum(max(value - defense, 0) for value, defense in zip(attacker.maximum, target.defense)))


# Resolve hit, avoidance and one shared random value across all damage channels.
def blow(roster, attacker, target, rng):
    if rng.random() * 100 >= hit_chance(attacker, target):
        return 0
    if rng.random() * 100 < roster.avoidance_chance(target, attacker.melee):
        return 0
    low, high = damage_bounds(attacker, target)
    return low + rng.random() * (high - low)


# Repeat the reference duel scheduler; only a surviving defender answers. The next attack turn keeps the fraction
# of the cooldown: max(previous, turn - 1) + cooldown.
def duel(roster, first, second, fights, rng):
    wins = 0
    for _ in range(fights):
        a, b = replace(first), replace(second)
        next_a = next_b = 0
        for turn in range(1, DUEL_LIMIT + 1):
            if turn >= next_a:
                b.hp -= blow(roster, a, b, rng)
                next_a = max(next_a, turn - 1) + a.cooldown
            if b.hp > 0 and turn >= next_b:
                a.hp -= blow(roster, b, a, rng)
                next_b = max(next_b, turn - 1) + b.cooldown
            if a.hp <= 0 or b.hp <= 0:
                break
        wins += a.hp > 0
    return wins / fights


# Same scheduler as duel, but returns the mean turn at which a fight ends instead of the win share.
def duel_turns(roster, first, second, fights, rng):
    total = 0
    for _ in range(fights):
        a, b = replace(first), replace(second)
        next_a = next_b = 0
        for turn in range(1, DUEL_LIMIT + 1):
            if turn >= next_a:
                b.hp -= blow(roster, a, b, rng)
                next_a = max(next_a, turn - 1) + a.cooldown
            if b.hp > 0 and turn >= next_b:
                a.hp -= blow(roster, b, a, rng)
                next_b = max(next_b, turn - 1) + b.cooldown
            if a.hp <= 0 or b.hp <= 0:
                break
        total += turn
    return total / fights


# Repeat the reference group scheduler, including simultaneous reply ordering.
def fight_group(roster, first, opponent, count, fights, rng):
    wins = 0
    for _ in range(fights):
        a = replace(first)
        opponents = [replace(opponent) for _ in range(count)]
        next_a = 0
        clocks = [0] * count
        for turn in range(1, GROUP_LIMIT + 1):
            if turn >= next_a:
                opponents[0].hp -= blow(roster, a, opponents[0], rng)
                next_a = max(next_a, turn - 1) + a.cooldown
            for i, b in enumerate(opponents):
                if turn >= clocks[i]:
                    a.hp -= blow(roster, b, a, rng)
                    clocks[i] = max(clocks[i], turn - 1) + b.cooldown
            survivors = [i for i, b in enumerate(opponents) if b.hp > 0]
            opponents = [opponents[i] for i in survivors]
            clocks = [clocks[i] for i in survivors]
            if a.hp <= 0 or not opponents:
                break
        wins += a.hp > 0
    return wins / fights


# Run seeded cross-type and level comparisons and return every measured result.
def evaluate(roster, seed=1, fights=150, group_fights=60):
    rng = random.Random(seed)
    names = roster.fighters()
    units = {name: roster.unit(name) for name in names}
    scores = {name: [] for name in names}
    for index, name in enumerate(names):
        for other in names[index + 1:]:
            score = duel(roster, units[name], units[other], fights, rng)
            scores[name].append(score)
            scores[other].append(1 - score)
    averages = {name: statistics.mean(scores[name]) for name in names}
    tiers = {}
    for name in names:
        tier = round(roster.number(roster.creatures[name][0], "MinHP") / HP_SCALE, 8)
        tiers.setdefault(tier, []).append(name)
    tier_means = {tier: statistics.mean(averages[name] for name in members) for tier, members in sorted(tiers.items())}
    levels = {}
    for name in names:
        levels[name] = {
            "10_vs_3x5": fight_group(roster, roster.unit(name, 10), roster.unit(name, 5), 3, group_fights, rng),
            "30_vs_3x15": fight_group(roster, roster.unit(name, 30), roster.unit(name, 15), 3, group_fights, rng),
            "1_vs_10": duel(roster, roster.unit(name, 1), roster.unit(name, 10), group_fights, rng),
            "5_vs_10": duel(roster, roster.unit(name, 5), roster.unit(name, 10), group_fights, rng),
        }
    return {"seed": seed, "fights": fights, "group_fights": group_fights,
            "averages": averages, "tiers": tiers, "tier_means": tier_means, "levels": levels}


# ---------------------------------------------------------------------------------------------------------------
# Attribute, mana, critical hit and skill template model (opt-in: nothing above uses it, the duel and group
# schedulers above keep their model). Every value comes from config/creatures.cfg, config/creatureSkills.cfg and
# config/global.cfg. The model follows the fight model of the attribute rules: attribute levels equal the creature
# level (no equipment), critical hits, a mana pool with regeneration, skill templates with the point order of the tree
# rules (without the personal deviation) and the skills of the catalog turned into damage, defense and timing factors.
# ---------------------------------------------------------------------------------------------------------------

# Mirror of ODApplication::turnsPerSecond; the creature check asserts that it matches the source.
TURNS_PER_SECOND = 1.4
# Hit chance of a grenade, guided bolt or the second missile attack on a target of the same level (model constant).
SKILL_HIT = 0.75
# Fight length in turns at the levels 1, 10, 20, 30 used to schedule the mana use (measured mean fight length).
FIGHT_TURNS = {1: 18.0, 10: 20.0, 20: 22.0, 30: 25.0}
# Damage channel index of a cast (-1 = absolute damage that ignores the defense).
CHANNEL_MAGICAL = 1
ABSOLUTE = -1
# Kinds that are cast again as soon as their effect has run out.
REARM_ON_EXPIRE = ("BUFF_SELF StrengthChange", "BUFF_SELF Defense", "AURA_ALLY StrengthChange", "DEBUFF Weak")
# The 0-based template indices and the cases of the per-type matrix (template -1 = no skills) and of the class means.
TEMPLATES_PER_GROUP = (0, 1, 2)
CASES_MATRIX = [(1, -1)] + [(level, template) for level in (10, 20, 30) for template in (0, 1, 2)]
CASES_CLASS = [(1, -1), (10, -1), (30, -1)] + [(level, template) for level in (10, 20, 30) for template in (0, 1, 2)]


# Combatant of the attribute model: the plain unit plus critical chance (percent) and the mana pool.
@dataclass
class SkillUnit(Unit):
    crit: float = 0.0
    mana_max: float = 0.0
    regen: float = 0.0
    cost: float = 0.0


# Split a "Key value..." block of creatureSkills.cfg into a dictionary; the value is the rest of the line.
def block_fields(block):
    result = {}
    for line in block.splitlines():
        words = line.split(None, 1)
        if len(words) == 2 and not words[0].startswith("#"):
            result.setdefault(words[0], words[1].strip())
    return result


# Turn the Kind token of the file ("BUFF_SELF_Defense") into the form used by the model ("BUFF_SELF Defense").
def skill_kind(token):
    for prefix in ("PASSIVE_", "BUFF_SELF_", "AURA_ALLY_", "DEBUFF_"):
        if token.startswith(prefix):
            return prefix[:-1] + " " + token[len(prefix):]
    return token


# Read one value cell: a number, a "push/stun" pair or None for "-".
def skill_value(token):
    if token == "-":
        return None
    if "/" in token:
        return tuple(float(part) for part in token.split("/"))
    return float(token)


# Read a row of rank cells ("-" gives None).
def rank_cells(text):
    if text is None or text == "-":
        return None
    return [skill_value(token) for token in text.split()]


# Hold the skill catalog, the tier four skills and the templates of config/creatureSkills.cfg.
class SkillCatalog:
    # Parse the file below the given repository root.
    def __init__(self, root):
        text = (Path(root) / "config/creatureSkills.cfg").read_text(encoding="utf-8")
        self.skills = {}
        self.paths = {}
        self.families = {}
        self.tier_four = {}
        self.templates = {}
        for block in re.findall(r"^\[Skill\]\s*$(.*?)^\[/Skill\]", text, re.S | re.M):
            cells = block_fields(block)
            entry = {"id": cells["Id"], "kind": skill_kind(cells["Kind"]), "values": rank_cells(cells["Values"]),
                     "mana": rank_cells(cells.get("Mana", "-")) or [0.0] * 5,
                     "cd": skill_value(cells.get("Cooldown", "-")), "dur": skill_value(cells.get("Duration", "-")),
                     "baseline": None if cells.get("BaseLine", "-") == "-" else cells["BaseLine"].split()}
            self.skills[entry["id"]] = entry
            tier = int(cells["Tier"])
            if "Group" in cells:
                self.paths.setdefault(cells["Group"], {}).setdefault(cells["Path"], {})[tier] = entry["id"]
            else:
                self.families.setdefault(cells["Family"], {})[tier] = entry["id"]
        for block in re.findall(r"^\[TierFour\]\s*$(.*?)^\[/TierFour\]", text, re.S | re.M):
            cells = block_fields(block)
            value = skill_value(cells["Value"])
            mana = skill_value(cells.get("Mana", "-")) or 0.0
            self.tier_four[cells["Creature"]] = {
                "id": "T4_" + cells["Creature"], "kind": skill_kind(cells["Kind"]), "values": [value] * 5, "mana": [mana] * 5,
                "cd": skill_value(cells.get("Cooldown", "-")), "dur": skill_value(cells.get("Duration", "-")),
                "baseline": None if cells.get("BaseLine", "-") == "-" else cells["BaseLine"].split()}
        for block in re.findall(r"^\[Template\]\s*$(.*?)^\[/Template\]", text, re.S | re.M):
            cells = block_fields(block)
            self.templates.setdefault(cells["Group"], {})[int(cells["Index"]) - 1] = (cells["Name"], cells["Primary"], cells["Alternative"])

    # The skill ids of a path of a group in tier order (tier 1, 2, 3).
    def path_skills(self, group, path):
        tiers = self.paths[group][path]
        return [tiers[tier] for tier in (1, 2, 3)]

    # The skill ids of a family path in tier order (tier 1, 2, 3).
    def family_skills(self, family):
        return [self.families[family][tier] for tier in (1, 2, 3)]


# Run the fights of the attribute model for the creatures of one repository checkout.
class World:
    # Load the catalog and the fighter list of a roster; all numbers are read from the roster's configuration.
    def __init__(self, roster):
        self.roster = roster
        self.catalog = SkillCatalog(roster.root)
        self.names = roster.fighters()
        self.wage = {name: roster.number(roster.creatures[name][0], "FeeBase") for name in self.names}
        self.cache = {}
        self.glob = {key: float(value) for key, value in roster.global_values.items() if re.fullmatch(r"-?[0-9.]+", value)}

    # One text field of a creature type ("none" and a missing key give None).
    def field(self, name, key):
        value = self.roster.creatures[name][0].get(key, ["none"])[0]
        return None if value == "none" else value

    # One number of a creature type's stats.
    def stat(self, name, key, default=0.0):
        return self.roster.number(self.roster.creatures[name][0], key, default)

    # The kept second missile attack of a type (an attack line after its first attack) as (average damage, cooldown,
    # damage channel), or None.
    def second_missile(self, name):
        first = self.roster.attack(name)[0]
        section = re.search(r"\[CreatureSkills\](.*?)\[/CreatureSkills\]", self.roster.creatures[name][1], re.S)
        for line in section[1].splitlines():
            words = line.split()
            if words and not words[0].startswith("#") and words[0] == "MissileLaunch" and words != first:
                ranges = [float(value) for value in words[15:21]]
                channels = [i for i in range(3) if ranges[2 * i + 1] > 0]
                assert len(channels) == 1, name
                channel = channels[0]
                return (ranges[2 * channel] + ranges[2 * channel + 1]) / 2, float(words[1]), channel
        return None

    # Average damage of one cast of a damage skill from its base line, and the channel it hits.
    def cast_base(self, kind, line):
        if kind == "EXPLOSION":
            return (float(line[6]) + float(line[7])) / 2, CHANNEL_MAGICAL
        if kind in ("HAILSTORM", "GASCLOUD"):
            return (float(line[7]) + float(line[9])) / 2 * float(line[6]), ABSOLUTE
        ranges = [float(value) for value in line[-6:]]
        channel = [i for i in range(3) if ranges[2 * i + 1] > 0][0]
        return (ranges[2 * channel] + ranges[2 * channel + 1]) / 2, channel

    # The plain unit of a type at a level with critical chance and mana pool (attribute levels equal the level).
    def base_unit(self, name, level):
        level = max(1, min(MAX_LEVEL, level))
        plain = self.roster.unit(name, level)
        values = {f.name: getattr(plain, f.name) for f in dataclasses.fields(plain)}
        group = self.field(name, "SkillGroup")
        mana_max = (self.stat(name, "Mana") + self.stat(name, "ManaPerLevel") * (level - 1)) * self.stat(name, "ManaPerPoint")
        crit = (self.glob["CritChancePerDexterity"] * self.stat(name, "Dexterity")
                + self.glob["CritChancePerLevel"] * (level - 1) + self.stat(name, "CritChanceBonus"))
        return SkillUnit(**values, crit=crit, mana_max=mana_max, regen=mana_max / (self.glob["ManaRefillSeconds"] * TURNS_PER_SECOND),
                         cost=self.glob["ManaPerCasterShot"] if group == "caster" else 0.0)

    # Ranks per skill id after the template's point order for the points a creature of this level has: pre-skill first,
    # then the primary path (tier 1, 2, 2, 3, then tier 1 to 5, 2 to 5, 3 to 5), then the family path (tier 1, 1, 2, 2, 3);
    # a pick at rank 5 is skipped and when the list is used up the points go to the family path tier by tier.
    # Returns the ranks and whether the tier four skill is reached (21 points, 20 spent).
    def allocation(self, name, level, template, skills_on):
        group = self.field(name, "SkillGroup")
        family = self.catalog.family_skills(self.field(name, "SkillFamily"))
        _, primary, _ = self.catalog.templates[group][template]
        tiers = self.catalog.path_skills(group, primary)
        ranks = {}
        if self.field(name, "PreSkill"):
            ranks[self.field(name, "PreSkill")] = 1
        points = max(0, min(21, level - 9)) if skills_on else 0
        picks = [tiers[0], tiers[1], tiers[1], tiers[2]] + [tiers[0]] * 4 + [tiers[1]] * 3 + [tiers[2]] * 4
        picks += [family[0], family[0], family[1], family[1], family[2]]
        overflow = [family[0]] * 5 + [family[1]] * 5 + [family[2]] * 5
        cursor = 0
        spent = 0
        while spent < min(points, 20):
            chosen = None
            while cursor < len(picks):
                candidate = picks[cursor]
                cursor += 1
                if ranks.get(candidate, 0) < 5:
                    chosen = candidate
                    break
            if chosen is None:
                while overflow and ranks.get(overflow[0], 0) >= 5:
                    overflow.pop(0)
                if not overflow:
                    break
                chosen = overflow.pop(0)
            ranks[chosen] = ranks.get(chosen, 0) + 1
            spent += 1
        return ranks, points >= 21 and spent >= 20

    # Per turn, the casts of every skill and attack line over a fight of the given length: the full pool at the start,
    # the regeneration every turn, the skills in the given order (off cooldown and affordable), then the attack lines
    # that cost mana. Returns per skill casts per turn x effective cooldown and per attack line the uses per turn.
    def schedule(self, actives, mana0, regen, turns, lines):
        mana = mana0
        clock = [0.0] * len(actives)
        count = [0] * len(actives)
        steps = int(round(turns))
        line_clock = [0.0] * len(lines)
        line_count = [0] * len(lines)
        for _ in range(steps):
            for i, (cost, cooldown) in enumerate(actives):
                if clock[i] <= 0 and mana >= cost:
                    mana -= cost
                    clock[i] += cooldown
                    count[i] += 1
            for i, (cooldown, cost) in enumerate(lines):
                if line_clock[i] <= 0 and mana >= cost:
                    mana -= cost
                    line_clock[i] += cooldown
                    line_count[i] += 1
            clock = [x - 1.0 if x > 0 else x for x in clock]
            line_clock = [x - 1.0 if x > 0 else x for x in line_clock]
            mana = min(mana0, mana + regen)
        return ([count[i] / steps * cooldown for i, (cost, cooldown) in enumerate(actives)],
                [line_count[i] / steps for i in range(len(lines))])

    # Fight length in turns for a level (linear between the measured levels).
    @staticmethod
    def fight_turns(level):
        keys = sorted(FIGHT_TURNS)
        level = max(1, min(MAX_LEVEL, level))
        for low, high in zip(keys, keys[1:]):
            if low <= level <= high:
                return FIGHT_TURNS[low] + (FIGHT_TURNS[high] - FIGHT_TURNS[low]) * (level - low) / (high - low)
        return FIGHT_TURNS[keys[-1]]

    # Order key of a skill in a turn: tier four first, then heals, buffs and auras, debuffs, everything else.
    @staticmethod
    def kind_order(kind, tier_four):
        if tier_four:
            return 0
        if kind.startswith("HEAL"):
            return 1
        if kind.startswith("BUFF") or kind.startswith("AURA"):
            return 2
        if kind.startswith("DEBUFF"):
            return 3
        return 4

    # Turn the ranked skills of a creature into factors on its unit and a record of the extras the fight needs:
    # passives change hit points, damage, critical chance, cooldown, ratings and avoidance; buffs, debuffs and stuns
    # become their average share of the fight; damage skills become casts per turn; heals and Drain become hit points
    # per turn. Mana limits how often each active skill is cast (see schedule).
    def apply(self, name, level, template, base, skills_on):
        ranks, ult = self.allocation(name, level, template, skills_on)
        group = self.field(name, "SkillGroup")
        u = replace(base)
        dmgk = hpk = spellk = allk = ark = drk = cdk = 1.0
        crit = avoid = defadd = manacost = 0.0
        enemy_dmgk = 1.0
        enemy_turnloss = strike_dpt = drain_dpt = heal_pt = 0.0
        minhp = self.stat(name, "MinHP")
        dm = multiplier(level, "damage") * (minhp / self.glob["SkillSpellReferenceMinHP"])
        items = [(self.catalog.skills[skill_id], rank) for skill_id, rank in ranks.items()]
        tier_four_item = None
        if ult:
            tier_four_item = self.catalog.tier_four[name]
            items.append((tier_four_item, 1))
        eff = []
        eff_tier_four = []
        for skill, rank in items:
            kind = skill["kind"]
            value = skill["values"][rank - 1]
            if kind.startswith("PASSIVE"):
                stat = kind.split()[1]
                if stat == "dmg%" and group != "caster":
                    dmgk *= 1 + value / 100
                elif stat == "spell%":
                    spellk *= 1 + value / 100
                    if group == "caster":
                        dmgk *= 1 + value / 100
                elif stat == "alldmg%":
                    dmgk *= 1 + value / 100
                    allk *= 1 + value / 100
                elif stat == "hp%":
                    hpk *= 1 + value / 100
                elif stat == "crit":
                    crit += value
                elif stat == "cd%":
                    cdk *= 1 - value / 100
                elif stat == "avoid":
                    avoid += value
                elif stat == "ar%":
                    ark *= 1 + value / 100
                elif stat == "dr%":
                    drk *= 1 + value / 100
                elif stat == "manacost%":
                    manacost += value
                continue
            eff.append((skill, kind, value, skill["cd"] or 1, skill["dur"] or 1, skill["mana"][rank - 1]))
            eff_tier_four.append(skill is tier_four_item)
        order = sorted(range(len(eff)), key=lambda i: self.kind_order(eff[i][1], eff_tier_four[i]))
        lines = []
        shot = self.second_missile(name)
        if shot:
            lines.append((shot[1], self.glob["ManaPerDragonSecondShot"] * (1 - manacost / 100)))
        attack_cooldown = max(1, u.cooldown * cdk)
        if u.cost:
            lines.append((attack_cooldown, u.cost * (1 - manacost / 100)))
        timed = []
        for i in order:
            skill, kind, value, cooldown, duration, cost = eff[i]
            timed.append((cost * (1 - manacost / 100), max(cooldown, duration) if kind in REARM_ON_EXPIRE else cooldown))
        sustained, line_rates = self.schedule(timed, u.mana_max, u.regen, self.fight_turns(level), lines)
        shot_rate = line_rates[0] if shot else 0.0
        attack_paid = min(1.0, line_rates[-1] * attack_cooldown) if u.cost else 1.0
        sustain_of = [0.0] * len(eff)
        for slot, i in enumerate(order):
            sustain_of[i] = sustained[slot]
        casts = []
        for (skill, kind, value, cooldown, duration, cost), sustain in zip(eff, sustain_of):
            uptime = min(1.0, duration / cooldown) * sustain
            if kind in ("BUFF_SELF StrengthChange", "AURA_ALLY StrengthChange"):
                dmgk *= 1 + (value - 1) * uptime
            elif kind == "BUFF_SELF Defense":
                defadd += value * uptime
            elif kind == "DEBUFF Weak":
                enemy_dmgk *= 1 - (1 - value) * uptime
            elif kind in ("EXPLOSION", "HAILSTORM", "GASCLOUD", "GRENADE", "GUIDEDBOLT"):
                average, channel = self.cast_base(kind, skill["baseline"])
                hit = SKILL_HIT if kind in ("GRENADE", "GUIDEDBOLT") else 1.0
                area = kind in ("HAILSTORM", "GASCLOUD")
                casts.append([average * value * dm, sustain / cooldown, channel, hit, area])
            elif kind == "STRIKE":
                strike_dpt += (value - 1) * (sum(base.minimum) + sum(base.maximum)) / 2 / cooldown * sustain
            elif kind == "WHIRLWIND":
                enemy_turnloss += value[1] / cooldown * sustain
            elif kind == "FREEZE":
                enemy_turnloss += 28 * value / cooldown * sustain
            elif kind.startswith("HEAL"):
                heal_pt += value / 100 * minhp * multiplier(level, "damage") / cooldown * sustain
            elif kind == "DRAIN":
                share = value / 100 * base.hp / cooldown * sustain
                drain_dpt += share
                heal_pt += share
        u.hp *= hpk
        u.minimum = tuple(x * dmgk * attack_paid for x in u.minimum)
        u.maximum = tuple(x * dmgk * attack_paid for x in u.maximum)
        u.crit += crit
        u.cooldown = max(1, u.cooldown * cdk)
        u.attack_rating *= ark
        u.defense_rating *= drk
        u.defense = tuple(x + defadd for x in u.defense)
        critk = 1 + u.crit / 100
        for cast in casts:
            cast[0] *= spellk * allk * critk
        extras = {"avoid": avoid, "enemy_dmgk": enemy_dmgk, "enemy_turnloss": min(0.6, enemy_turnloss),
                  "extra_dpt": strike_dpt * critk + drain_dpt, "heal_pt": heal_pt, "casts": casts, "shot_rate": shot_rate}
        return u, extras

    # The fighter record of a type at a level with a template (0-based) or without skills (template < 0): the unit,
    # its extras, the type's skill damage factor on the damage skills and the kept second missile attack as one more
    # cast (magical, 75 percent hit chance, damage passives and critical chance of the creature, not the skill factor).
    def unit(self, name, level, template):
        key = (name, level, template)
        if key in self.cache:
            return self.cache[key]
        skills_on = template >= 0
        base = self.base_unit(name, level)
        u, extras = self.apply(name, level, max(template, 0), base, skills_on)
        factor = self.stat(name, "SkillDamageFactor", 1.0)
        extras = dict(extras)
        extras["casts"] = [list(cast) for cast in extras["casts"]]
        for cast in extras["casts"]:
            cast[0] *= factor
        shot = self.second_missile(name)
        if shot:
            average, _, channel = shot
            unskilled = self.apply(name, level, 0, base, False)[0]
            passives = sum(u.maximum) / max(1e-9, sum(unskilled.maximum)) if skills_on else 1.0
            per_shot = average * multiplier(level, "damage") * passives * (1 + u.crit / 100)
            extras["casts"].append([per_shot, extras["shot_rate"], channel, SKILL_HIT, False])
        self.cache[key] = (u, extras)
        return self.cache[key]


# Damage of a creature's casts in one turn: absolute casts ignore the defense, the others subtract the target's
# defense of their channel; area casts hit every target, the others the current (first) one.
def cast_hits(extras, targets):
    for damage, rate, channel, hit, area in extras["casts"]:
        if rate <= 0:
            continue
        for target in (targets if area else targets[:1]):
            target.hp -= (max(0.0, damage - target.defense[channel]) if channel >= 0 else damage) * hit * rate


# Resolve one blow: hit roll, avoidance (plus the avoid passive of the defender), critical roll, then the defense of
# every channel and the shared damage roll, then the attacker's weakening by the defender's debuffs.
def skill_blow(roster, attacker, target, target_extras, rng, crit_multiplier):
    if rng.random() * 100 >= hit_chance(attacker, target):
        return 0
    if rng.random() * 100 < roster.avoidance_chance(target, attacker.melee) + target_extras["avoid"]:
        return 0
    factor = crit_multiplier if rng.random() * 100 < attacker.crit else 1.0
    low = sum(max(value * factor - defense, 0) for value, defense in zip(attacker.minimum, target.defense))
    high = sum(max(value * factor - defense, 0) for value, defense in zip(attacker.maximum, target.defense))
    return (low + rng.random() * (high - low)) * target_extras["enemy_dmgk"]


# Fight one creature (unit and extras) against count copies of another; returns the win share and the mean turns.
# Skill extras act every turn; the copies all attack, the first copy is the target; stuns skip a blow.
def skill_fight(roster, crit_multiplier, first, second, count, fights, rng, limit=GROUP_LIMIT):
    wins = 0
    turns = []
    a_extras = first[1]
    b_extras = second[1]
    for _ in range(fights):
        a = replace(first[0])
        full_a = a.hp
        opponents = [replace(second[0]) for _ in range(count)]
        full_b = opponents[0].hp
        next_a = 0
        clocks = [0] * count
        for turn in range(1, limit + 1):
            a.hp = min(full_a, a.hp + a_extras["heal_pt"])
            for b in opponents:
                b.hp = min(full_b, b.hp + b_extras["heal_pt"])
            opponents[0].hp -= a_extras["extra_dpt"]
            cast_hits(a_extras, opponents)
            for b in opponents:
                a.hp -= b_extras["extra_dpt"]
                cast_hits(b_extras, [a])
            if turn >= next_a:
                if rng.random() >= b_extras["enemy_turnloss"]:
                    opponents[0].hp -= skill_blow(roster, a, opponents[0], b_extras, rng, crit_multiplier)
                next_a = max(next_a, turn - 1) + a.cooldown
            for i, b in enumerate(opponents):
                if b.hp > 0 and turn >= clocks[i]:
                    if rng.random() >= a_extras["enemy_turnloss"]:
                        a.hp -= skill_blow(roster, b, a, a_extras, rng, crit_multiplier)
                    clocks[i] = max(clocks[i], turn - 1) + b.cooldown
            survivors = [i for i, b in enumerate(opponents) if b.hp > 0]
            opponents = [opponents[i] for i in survivors]
            clocks = [clocks[i] for i in survivors]
            if a.hp <= 0 or not opponents:
                break
        wins += a.hp > 0
        turns.append(turn)
    return wins / fights, statistics.mean(turns)


# Per-type matrix of one case: every type of wage above 50 as the single creature against two creatures of every type
# of half its wage, in fighters() order, 80 fights per pairing, one generator seeded from the case.
def world_matrix(world, level, template, fights=80):
    crit_multiplier = world.glob["CritDamageMultiplier"]
    rng = random.Random(1000 * level + template + 7)
    units = {name: world.unit(name, level, template) for name in world.names}
    result = {}
    for a in world.names:
        if world.wage[a] == 50:
            continue
        for b in world.names:
            if world.wage[b] == world.wage[a] // 2:
                result[a + "|" + b] = skill_fight(world.roster, crit_multiplier, units[a], units[b], 2, fights, rng)[0]
    return result


# Mean win share per type as the single creature (rows) and as one of the pair (columns) for every case.
def world_roles(matrices):
    rows, columns = {}, {}
    for case, matrix in matrices.items():
        for key, value in matrix.items():
            a, b = key.split("|")
            rows.setdefault(a, {}).setdefault(case, []).append(value)
            columns.setdefault(b, {}).setdefault(case, []).append(value)
    return ({a: {case: statistics.mean(values) for case, values in cases.items()} for a, cases in rows.items()},
            {b: {case: statistics.mean(values) for case, values in cases.items()} for b, cases in columns.items()})


# Class means: for the wages 100, 200, 400 the share of the single creature against two of half the wage, all types
# of the class together, one generator for all cases in the given order, 60 fights per pairing.
def world_class_means(world, fights=60):
    crit_multiplier = world.glob["CritDamageMultiplier"]
    rng = random.Random(31337)
    result = {}
    for level, template in CASES_CLASS:
        units = {name: world.unit(name, level, template) for name in world.names}
        row = {}
        for wage in (100, 200, 400):
            row[wage] = round(statistics.mean(
                skill_fight(world.roster, crit_multiplier, units[a], units[b], 2, fights, rng)[0]
                for a in world.names if world.wage[a] == wage for b in world.names if world.wage[b] == wage // 2), 3)
        result[(level, template)] = row
    return result


# Rule 2 (level 10 against three at level 5, level 30 against three at level 15, mean of the three templates) and the
# fight length of two equal creatures at levels 1, 10 and 30 (templates averaged), 100 fights each, one generator.
def world_verify(world, fights=100):
    crit_multiplier = world.glob["CritDamageMultiplier"]
    rng = random.Random(424242)
    groups, lengths = {}, {}
    for name in world.names:
        # One fight series of this type: the given level against the other level with a template and copies count.
        def fight_of(level, other, template, count):
            return skill_fight(world.roster, crit_multiplier, world.unit(name, level, template), world.unit(name, other, template), count, fights, rng)
        wins10 = statistics.mean(fight_of(10, 5, t, 3)[0] for t in TEMPLATES_PER_GROUP)
        wins30 = statistics.mean(fight_of(30, 15, t, 3)[0] for t in TEMPLATES_PER_GROUP)
        groups[name] = (round(wins10, 3), round(wins30, 3))
        turns1 = fight_of(1, 1, -1, 1)[1]
        turns10 = statistics.mean(fight_of(10, 10, t, 1)[1] for t in TEMPLATES_PER_GROUP)
        turns30 = statistics.mean(fight_of(30, 30, t, 1)[1] for t in TEMPLATES_PER_GROUP)
        lengths[name] = (round(turns1, 1), round(turns10, 1), round(turns30, 1))
    return groups, lengths


# Rule 1: the worker's hit points and the largest critical blow (every damage value doubled before the defense) of a
# level-1 fighter of wage 50 to 200 with its pre-skill against that worker; returns (worker hit points, damage, type).
def world_rule_one(world):
    crit_multiplier = world.glob["CritDamageMultiplier"]
    worker = world.unit("Kobold", 1, -1)[0]
    worst = max((sum(max(crit_multiplier * value - defense, 0) for value, defense in zip(world.unit(name, 1, 0)[0].maximum, worker.defense)), name)
                for name in world.names if world.wage[name] <= 200)
    return worker.hp, worst[0], worst[1]


# Compare any checkout's configuration using reproducible command-line parameters.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--fights", type=int, default=150)
    parser.add_argument("--group-fights", type=int, default=60)
    args = parser.parse_args()
    print(json.dumps(evaluate(Roster(args.repo), args.seed, args.fights, args.group_fights), indent=2))


if __name__ == "__main__":
    main()
