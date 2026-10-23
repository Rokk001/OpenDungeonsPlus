"""Check the creature skill tree system (package C of the attribute plan): skill points, ranks, unlock rules,
pre-skill, tier 4, template order, personal deviation with a fixed seed, reset rules, stream round trip, skill line
building and the wiring in the creature code (passives, new skill kinds, effect stacking, packets).

The rules are checked twice: the compiled probe runs CreatureSkillTree.cpp (it has no engine dependency) and a Python
model written from the rules computes the expected result. The probe needs the compiler (cl) in the PATH; without it
only the source checks run, with --probe a missing compiler is an error.
The content of config/creatureSkills.cfg (every skill row of the catalog, the tier four skills and the templates),
the per-type keys and the removal of today's skill lines are checked by check_content() against expected values
kept in this file; the rules themselves are checked with the small example config in source/tests/fixtures.
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

root = Path(__file__).resolve().parents[2]
FIXTURE = root / 'source/tests/fixtures/creature_skills_example.cfg'
BS = chr(92)

# Constants of the rules (the same as the plan states them)
FIRST_LEVEL = 10
MAX_RANK = 5
DEVIATION = 25
TIER_FOUR_MIN_SPENT = 20
RESET_FOLLOWERS = 3
CHICKENS = 2
WINDOW = 60.0


# Expected content of the skill catalog (data built from the catalog tables).
EXPECTED_SKILLS = [
    ('BLK_A1', 'Group', 'blocker', 'Arms', '1', 'Weapon Training', 'PASSIVE_dmg%', '0.313 0.626 0.939 1.252 1.564', '-', '-', '-', '-', '-', '-'),
    ('BLK_A2', 'Group', 'blocker', 'Arms', '2', 'Keen Edge', 'PASSIVE_crit', '0.313 0.626 0.939 1.252 1.564', '-', '-', '-', '-', '-', '-'),
    ('BLK_A3', 'Group', 'blocker', 'Arms', '3', 'Heavy Blow', 'STRIKE', '1.125 1.146 1.167 1.188 1.209', '5 5 5 5 5', '30', '-', '-', '-', '-'),
    ('BLK_B1', 'Group', 'blocker', 'Bulwark', '1', 'Thick Hide', 'PASSIVE_hp%', '0.746 1.492 2.237 2.983 3.729', '-', '-', '-', '-', '-', '-'),
    ('BLK_B2', 'Group', 'blocker', 'Bulwark', '2', 'Iron Hide', 'BUFF_SELF_Defense', '0.298 0.597 0.895 1.193 1.492', '7 7 7 7 7', '45', '25', '-', '-', 'DefenseSelf 45 2 15 25 3 3 3'),
    ('BLK_B3', 'Group', 'blocker', 'Bulwark', '3', 'Shield Wall', 'PASSIVE_avoid', '0.497 0.994 1.492 1.989 2.486', '-', '-', '-', '-', '-', '-'),
    ('BLK_C1', 'Group', 'blocker', 'War Cries', '1', 'War Roar', 'BUFF_SELF_StrengthChange', '1.01 1.02 1.03 1.04 1.05', '7 7 7 7 7', '55', '20', '-', '-', 'StrengthSelf 55 2 18 20 1.15'),
    ('BLK_C2', 'Group', 'blocker', 'War Cries', '2', 'Rallying Shout', 'AURA_ALLY_StrengthChange', '1.003 1.007 1.01 1.013 1.017', '5 5 5 5 5', '60', '20', '4', '-', '-'),
    ('BLK_C3', 'Group', 'blocker', 'War Cries', '3', 'Cleaving Spin', 'WHIRLWIND', '1/1 1/1 1/1 1/1 1/1', '12.5 13 13.5 14 14.5', '14', '-', '-', '2', 'Whirlwind 14 1 2 8 3 3'),
    ('BLZ_A1', 'Group', 'blitzer', 'Zeal', '1', 'Holy Fervor', 'PASSIVE_dmg%', '0.445 0.89 1.335 1.781 2.226', '-', '-', '-', '-', '-', '-'),
    ('BLZ_A2', 'Group', 'blitzer', 'Zeal', '2', 'Swift Strikes', 'PASSIVE_cd%', '0.445 0.89 1.335 1.781 2.226', '-', '-', '-', '-', '-', '-'),
    ('BLZ_A3', 'Group', 'blitzer', 'Zeal', '3', 'Searing Blast', 'EXPLOSION', '0.178 0.208 0.237 0.267 0.297', '5 5.5 6 6.5 7', '40', '-', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('BLZ_B1', 'Group', 'blitzer', 'Protection', '1', 'Sacred Armor', 'PASSIVE_hp%', '1.391 2.782 4.173 5.564 6.955', '-', '-', '-', '-', '-', '-'),
    ('BLZ_B2', 'Group', 'blitzer', 'Protection', '2', 'Bulwark', 'BUFF_SELF_Defense', '0.556 1.113 1.669 2.225 2.782', '35 35 35 35 35', '45', '25', '-', '-', 'DefenseSelf 45 2 15 25 3 3 3'),
    ('BLZ_B3', 'Group', 'blitzer', 'Protection', '3', 'Resolute', 'PASSIVE_avoid', '0.927 1.855 2.782 3.709 4.636', '-', '-', '-', '-', '-', '-'),
    ('BLZ_C1', 'Group', 'blitzer', 'Charge', '1', 'Storm Rush', 'BUFF_SELF_SpeedChange', '1.04 1.08 1.12 1.16 1.2', '10 10 10 10 10', '30', '10', '-', '-', 'HasteSelf 30 0 5 10 1.2'),
    ('BLZ_C2', 'Group', 'blitzer', 'Charge', '2', 'Battle Prayer', 'HEAL_SELF', '6 7.5 9 10.5 12', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('BLZ_C3', 'Group', 'blitzer', 'Charge', '3', 'Commanding Aura', 'AURA_ALLY_StrengthChange', '1.02 1.04 1.06 1.08 1.1', '10 10 10 10 10', '60', '20', '4', '-', '-'),
    ('FLK_A1', 'Group', 'flanker', 'Shadow', '1', 'Quickstep', 'BUFF_SELF_SpeedChange', '1.04 1.08 1.12 1.16 1.2', '10 10 10 10 10', '30', '10', '-', '-', 'HasteSelf 30 0 5 10 1.2'),
    ('FLK_A2', 'Group', 'flanker', 'Shadow', '2', 'Shadow Veil', 'INVISIBLE', '20 40 60 80 100', '13 13 13 13 13', '150', '-', '-', '-', 'Invisible 150 0 8 100'),
    ('FLK_A3', 'Group', 'flanker', 'Shadow', '3', 'Cruel Eye', 'PASSIVE_crit', '1.841 3.682 5.524 7.365 9.206', '-', '-', '-', '-', '-', '-'),
    ('FLK_B1', 'Group', 'flanker', 'Venom', '1', 'Enfeeble', 'DEBUFF_Weak', '0.991 0.981 0.972 0.963 0.954', '4 4 4 4 4', '55', '20', '-', '6', 'Weak 55 2 6 18 20 0.85'),
    ('FLK_B2', 'Group', 'flanker', 'Venom', '2', 'Hamstring', 'DEBUFF_Slow', '0.96 0.92 0.88 0.84 0.8', '11 11 11 11 11', '30', '10', '-', '6', 'Slow 30 1 6 5 10 0.8'),
    ('FLK_B3', 'Group', 'flanker', 'Venom', '3', 'Venom Edge', 'PASSIVE_dmg%', '0.369 0.739 1.108 1.478 1.847', '-', '-', '-', '-', '-', '-'),
    ('FLK_C1', 'Group', 'flanker', 'Evasion', '1', 'Nimble', 'PASSIVE_avoid', '0.411 0.821 1.232 1.643 2.053', '-', '-', '-', '-', '-', '-'),
    ('FLK_C2', 'Group', 'flanker', 'Evasion', '2', 'Light Feet', 'PASSIVE_cd%', '0.616 1.232 1.848 2.464 3.08', '-', '-', '-', '-', '-', '-'),
    ('FLK_C3', 'Group', 'flanker', 'Evasion', '3', 'Lick Wounds', 'HEAL_SELF', '2.464 3.08 3.696 4.312 4.928', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('ARC_A1', 'Group', 'archer', 'Bow', '1', 'Steady Aim', 'PASSIVE_ar%', '0.616 1.232 1.847 2.463 3.079', '-', '-', '-', '-', '-', '-'),
    ('ARC_A2', 'Group', 'archer', 'Bow', '2', 'Seeking Shot', 'GUIDEDBOLT', '0.092 0.108 0.123 0.139 0.154', '8 7.7 7.4 7.1 6.8', '3', '-', '-', '-', 'GuidedBolt 3 2 7 0 8 ArrowProjectile none 2 0 0 0 0 13 0.25 0 0 0 0 18.11 27.17'),
    ('ARC_A3', 'Group', 'archer', 'Bow', '3', 'Blast Shot', 'GRENADE', '0.092 0.108 0.123 0.139 0.154', '5 5.5 6 6.5 7', '10', '-', '-', '-', 'Grenade 10 2 6 0 8 Cannonball none 1 0 0 0 0 5 0.1 2 0 0 0 0 6.97 10.46'),
    ('ARC_B1', 'Group', 'archer', 'Hunter', '1', 'Keen Eye', 'PASSIVE_crit', '0.65 1.301 1.951 2.602 3.252', '-', '-', '-', '-', '-', '-'),
    ('ARC_B2', 'Group', 'archer', 'Hunter', '2', 'Pinning Shot', 'DEBUFF_Slow', '0.96 0.92 0.88 0.84 0.8', '11 11 11 11 11', '30', '10', '-', '6', 'Slow 30 1 6 5 10 0.8'),
    ('ARC_B3', 'Group', 'archer', 'Hunter', '3', 'Piercing Arrows', 'PASSIVE_dmg%', '0.65 1.301 1.951 2.602 3.252', '-', '-', '-', '-', '-', '-'),
    ('ARC_C1', 'Group', 'archer', 'Skirmish', '1', 'Fleetfoot', 'BUFF_SELF_SpeedChange', '1.04 1.08 1.12 1.16 1.2', '10 10 10 10 10', '30', '10', '-', '-', 'HasteSelf 30 0 5 10 1.2'),
    ('ARC_C2', 'Group', 'archer', 'Skirmish', '2', 'Evasion', 'PASSIVE_avoid', '0.57 1.14 1.71 2.28 2.85', '-', '-', '-', '-', '-', '-'),
    ('ARC_C3', 'Group', 'archer', 'Skirmish', '3', 'Thick Leather', 'PASSIVE_hp%', '0.855 1.71 2.565 3.42 4.275', '-', '-', '-', '-', '-', '-'),
    ('CST_A1', 'Group', 'caster', 'Fire', '1', 'Ember Burst', 'EXPLOSION', '0.061 0.071 0.081 0.091 0.102', '5 5.5 6 6.5 7', '40', '-', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('CST_A2', 'Group', 'caster', 'Fire', '2', 'Kindled Mind', 'PASSIVE_spell%', '0.152 0.305 0.457 0.609 0.762', '-', '-', '-', '-', '-', '-'),
    ('CST_A3', 'Group', 'caster', 'Fire', '3', 'Ice Storm', 'HAILSTORM', '0.061 0.071 0.081 0.091 0.102', '23 24 25 26 27', '21', '-', '-', '-', 'HailStorm 21 2 4 8 2 11 3.08 none 2.05'),
    ('CST_B1', 'Group', 'caster', 'Frost', '1', 'Frost Grip', 'FREEZE', '0.036 0.042 0.049 0.055 0.061', '9 10 11 12 13', '80', '-', '-', '-', 'Freeze 80 2 6 8 28'),
    ('CST_B2', 'Group', 'caster', 'Frost', '2', 'Hex of Weakness', 'DEBUFF_Weak', '0.998 0.996 0.995 0.993 0.991', '4 4 4 4 4', '55', '20', '-', '6', 'Weak 55 2 6 18 20 0.85'),
    ('CST_B3', 'Group', 'caster', 'Frost', '3', 'Soul Siphon', 'DRAIN', '1.821 2.124 2.428 2.731 3.035', '9 9 9 9 9', '50', '-', '-', '6', 'Drain 50 2 6 8 25'),
    ('CST_C1', 'Group', 'caster', 'Healing', '1', 'Mend', 'HEAL_ALLY', '0.83 1.037 1.245 1.452 1.66', '6 7 8 9 10', '12', '1', '-', '6', '-'),
    ('CST_C2', 'Group', 'caster', 'Healing', '2', 'Greater Mend', 'HEAL_ALLY', '2.075 2.49 2.905 3.32 3.735', '15 17 19 21 23', '35', '1', '-', '6', '-'),
    ('CST_C3', 'Group', 'caster', 'Healing', '3', 'Healing Circle', 'HEAL_AREA', '0.622 0.726 0.83 0.934 1.037', '20 22 24 26 28', '40', '1', '3', '-', '-'),
    ('WRK_A1', 'Group', 'worker', 'Delving', '1', 'Strong Picks', 'PASSIVE_dig%', '5 10 15 20 25', '-', '-', '-', '-', '-', '-'),
    ('WRK_A2', 'Group', 'worker', 'Delving', '2', 'Tunnel Legs', 'PASSIVE_move%', '3 6 9 12 15', '-', '-', '-', '-', '-', '-'),
    ('WRK_A3', 'Group', 'worker', 'Delving', '3', 'Rock Splitter', 'PASSIVE_crit', '0.735 1.471 2.206 2.941 3.677', '-', '-', '-', '-', '-', '-'),
    ('WRK_B1', 'Group', 'worker', 'Claiming', '1', 'Quick Claim', 'PASSIVE_claim%', '5 10 15 20 25', '-', '-', '-', '-', '-', '-'),
    ('WRK_B2', 'Group', 'worker', 'Claiming', '2', 'Deep Pockets', 'PASSIVE_carry%', '10 20 30 40 50', '-', '-', '-', '-', '-', '-'),
    ('WRK_B3', 'Group', 'worker', 'Claiming', '3', 'Hurry', 'BUFF_SELF_SpeedChange', '1.04 1.08 1.12 1.16 1.2', '10 10 10 10 10', '30', '10', '-', '-', 'HasteSelf 30 0 5 10 1.2'),
    ('WRK_C1', 'Group', 'worker', 'Survival', '1', 'Blink', 'TELEPORT', '1 1 1 1 1', '24 23 22 21 20', '7', '-', '-', '-', 'Teleport 7 0 8 8 30'),
    ('WRK_C2', 'Group', 'worker', 'Survival', '2', 'Toughen', 'BUFF_SELF_Defense', '0.221 0.441 0.662 0.882 1.103', '7 7 7 7 7', '45', '25', '-', '-', 'DefenseSelf 45 2 15 25 3 3 3'),
    ('WRK_C3', 'Group', 'worker', 'Survival', '3', 'Patch Up', 'HEAL_SELF', '2.206 2.758 3.309 3.861 4.412', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('GRN_1', 'Family', 'greenskin', 'Greenskin', '1', 'Thick Skull', 'PASSIVE_hp%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('GRN_2', 'Family', 'greenskin', 'Greenskin', '2', 'Brutal Swing', 'PASSIVE_dmg%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('GRN_3', 'Family', 'greenskin', 'Greenskin', '3', 'Regrowth', 'HEAL_SELF', '2.206 2.758 3.309 3.861 4.412', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('DWF_1', 'Family', 'dwarf', 'Dwarf', '1', 'Stoneborn', 'PASSIVE_dr%', '1.471 2.941 4.412 5.883 7.353', '-', '-', '-', '-', '-', '-'),
    ('DWF_2', 'Family', 'dwarf', 'Dwarf', '2', 'Rune Ward', 'BUFF_SELF_Defense', '0.221 0.441 0.662 0.882 1.103', '7 7 7 7 7', '45', '25', '-', '-', 'DefenseSelf 45 2 15 25 3 3 3'),
    ('DWF_3', 'Family', 'dwarf', 'Dwarf', '3', 'Forge Fury', 'BUFF_SELF_StrengthChange', '1.011 1.022 1.033 1.044 1.055', '7 7 7 7 7', '55', '20', '-', '-', 'StrengthSelf 55 2 18 20 1.15'),
    ('UND_1', 'Family', 'undead', 'Undead', '1', 'Raise the Fallen', 'RAISEDEAD', '1 1 2 2 3', '6 7 8 9 10', '24', '-', '-', '-', 'RaiseDead 24 2 10 4 3 42 Skeleton'),
    ('UND_2', 'Family', 'undead', 'Undead', '2', 'Deathless', 'PASSIVE_hp%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('UND_3', 'Family', 'undead', 'Undead', '3', 'Bone Legion', 'SKELARMY', '1 1 2 2 3', '8 9 10 11 12', '21', '-', '-', '-', 'SkeletonArmy 21 2 10 3 42 Skeleton'),
    ('VRM_1', 'Family', 'vermin', 'Vermin', '1', 'Buzzing Spin', 'WHIRLWIND', '1/1 1/1 1/1 1/1 1/1', '12.5 13 13.5 14 14.5', '14', '-', '-', '2', 'Whirlwind 14 1 2 8 3 3'),
    ('VRM_2', 'Family', 'vermin', 'Vermin', '2', 'Chitin', 'PASSIVE_avoid', '0.368 0.735 1.103 1.471 1.838', '-', '-', '-', '-', '-', '-'),
    ('VRM_3', 'Family', 'vermin', 'Vermin', '3', 'Frenzy', 'PASSIVE_cd%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('TNT_1', 'Family', 'tentacle', 'Tentacle', '1', 'Grasping Coils', 'DEBUFF_Slow', '0.96 0.92 0.88 0.84 0.8', '11 11 11 11 11', '30', '10', '-', '6', 'Slow 30 1 6 5 10 0.8'),
    ('TNT_2', 'Family', 'tentacle', 'Tentacle', '2', 'Constrict', 'DEBUFF_Weak', '0.989 0.978 0.967 0.956 0.945', '4 4 4 4 4', '55', '20', '-', '6', 'Weak 55 2 6 18 20 0.85'),
    ('TNT_3', 'Family', 'tentacle', 'Tentacle', '3', 'Deep Hunger', 'DRAIN', '5.515 6.434 7.353 8.273 9.192', '9 9 9 9 9', '50', '-', '-', '6', 'Drain 50 2 6 8 25'),
    ('DMN_1', 'Family', 'demon', 'Demon', '1', 'Hellfire Burst', 'EXPLOSION', '0.221 0.257 0.294 0.331 0.368', '5 5.5 6 6.5 7', '40', '-', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('DMN_2', 'Family', 'demon', 'Demon', '2', 'Infernal Hide', 'PASSIVE_hp%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('DMN_3', 'Family', 'demon', 'Demon', '3', 'Brimstone Rage', 'BUFF_SELF_StrengthChange', '1.011 1.022 1.033 1.044 1.055', '7 7 7 7 7', '55', '20', '-', '-', 'StrengthSelf 55 2 18 20 1.15'),
    ('ELF_1', 'Family', 'elf', 'Elf', '1', 'Elven Grace', 'PASSIVE_dr%', '1.471 2.941 4.412 5.883 7.353', '-', '-', '-', '-', '-', '-'),
    ('ELF_2', 'Family', 'elf', 'Elf', '2', 'Moonlit Step', 'BUFF_SELF_SpeedChange', '1.04 1.08 1.12 1.16 1.2', '10 10 10 10 10', '30', '10', '-', '-', 'HasteSelf 30 0 5 10 1.2'),
    ('ELF_3', 'Family', 'elf', 'Elf', '3', 'Eagle Eye', 'PASSIVE_crit', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('HUM_1', 'Family', 'human', 'Human', '1', 'Discipline', 'PASSIVE_cd%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('HUM_2', 'Family', 'human', 'Human', '2', 'Second Wind', 'HEAL_SELF', '2.206 2.758 3.309 3.861 4.412', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('HUM_3', 'Family', 'human', 'Human', '3', 'Valor', 'BUFF_SELF_StrengthChange', '1.011 1.022 1.033 1.044 1.055', '7 7 7 7 7', '55', '20', '-', '-', 'StrengthSelf 55 2 18 20 1.15'),
    ('ARC_1', 'Family', 'arcane', 'Arcane', '1', 'Arcane Flow', 'PASSIVE_manacost%', '6 12 18 24 30', '-', '-', '-', '-', '-', '-'),
    ('ARC_2', 'Family', 'arcane', 'Arcane', '2', 'Arcane Ward', 'BUFF_SELF_Defense', '0.221 0.441 0.662 0.882 1.103', '7 7 7 7 7', '45', '25', '-', '-', 'DefenseSelf 45 2 15 25 3 3 3'),
    ('ARC_3', 'Family', 'arcane', 'Arcane', '3', 'Mind Spark', 'PASSIVE_alldmg%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('DRK_1', 'Family', 'dragonkin', 'Dragonkin', '1', 'Hail of Scales', 'HAILSTORM', '0.221 0.257 0.294 0.331 0.368', '22 23 24 25 26', '21', '-', '-', '-', 'HailStorm 21 2 4 8 2 11 3.08 none 2.05'),
    ('DRK_2', 'Family', 'dragonkin', 'Dragonkin', '2', 'Scaled Hide', 'PASSIVE_hp%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('DRK_3', 'Family', 'dragonkin', 'Dragonkin', '3', 'Wing Buffet', 'WHIRLWIND', '1/1 1/1 1/1 1/1 1/1', '12.5 13 13.5 14 14.5', '14', '-', '-', '2', 'Whirlwind 14 1 2 8 3 3'),
    ('WLD_1', 'Family', 'wild', 'Wild', '1', 'Toxic Cloud', 'GASCLOUD', '0.221 0.257 0.294 0.331 0.368', '20 20 20 20 20', '7', '-', '-', '-', 'GasCloud 7 1 2 4 1.5 2 14.35 Smoke 9.57'),
    ('WLD_2', 'Family', 'wild', 'Wild', '2', 'Ooze Skin', 'PASSIVE_hp%', '0.552 1.103 1.655 2.206 2.758', '-', '-', '-', '-', '-', '-'),
    ('WLD_3', 'Family', 'wild', 'Wild', '3', 'Overgrowth', 'HEAL_SELF', '2.206 2.758 3.309 3.861 4.412', '10 10 10 10 10', '35', '5', '-', '-', '-'),
    ('WKF_1', 'Family', 'workfolk', 'Workfolk', '1', 'Tireless', 'PASSIVE_wake%', '6 12 18 24 30', '-', '-', '-', '-', '-', '-'),
    ('WKF_2', 'Family', 'workfolk', 'Workfolk', '2', 'Gold Nose', 'PASSIVE_dig%', '5 10 15 20 25', '-', '-', '-', '-', '-', '-'),
    ('WKF_3', 'Family', 'workfolk', 'Workfolk', '3', 'Steady Hands', 'PASSIVE_claim%', '5 10 15 20 25', '-', '-', '-', '-', '-', '-'),
]

EXPECTED_TIER_FOUR = [
    ('Orc', 'Blood Frenzy', 'BUFF_SELF_StrengthChange', '1.201', '140', '20', '30', '-', '-', '-'),
    ('Troll', 'Unstoppable Rage', 'BUFF_SELF_StrengthChange', '1.146', '140', '20', '30', '-', '-', '-'),
    ('PitDemon', 'Infernal Wrath', 'BUFF_SELF_StrengthChange', '1.238', '140', '20', '30', '-', '-', '-'),
    ('Scarab', 'Carapace Charge', 'BUFF_SELF_StrengthChange', '1.263', '140', '20', '30', '-', '-', '-'),
    ('Knight', 'Oath of Steel', 'BUFF_SELF_StrengthChange', '1.318', '140', '20', '30', '-', '-', '-'),
    ('Adventurer', "Hero's Moment", 'BUFF_SELF_StrengthChange', '1.163', '140', '20', '30', '-', '-', '-'),
    ('Goblin', 'Dirty Tricks', 'BUFF_SELF_StrengthChange', '1.266', '140', '20', '30', '-', '-', '-'),
    ('Rat', 'Swarm Fury', 'BUFF_SELF_StrengthChange', '1.111', '140', '20', '30', '-', '-', '-'),
    ('Roach', 'Scuttle Fury', 'BUFF_SELF_StrengthChange', '1.175', '140', '20', '30', '-', '-', '-'),
    ('Spider', 'Venom Frenzy', 'BUFF_SELF_StrengthChange', '1.095', '140', '20', '30', '-', '-', '-'),
    ('Wyvern', 'Sky Fury', 'BUFF_SELF_StrengthChange', '1.099', '140', '20', '30', '-', '-', '-'),
    ('Dwarf1', "Ancestor's Rage", 'BUFF_SELF_StrengthChange', '1.198', '140', '20', '30', '-', '-', '-'),
    ('Dwarf2', 'Hammer Storm', 'BUFF_SELF_StrengthChange', '1.264', '140', '20', '30', '-', '-', '-'),
    ('Cultist', 'Dark Ecstasy', 'BUFF_SELF_StrengthChange', '1.261', '140', '20', '30', '-', '-', '-'),
    ('LavaSpawn', 'Magma Eruption', 'EXPLOSION', '1.244', '120', '1', '38', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('Wizard', 'Arcane Cataclysm', 'EXPLOSION', '1.016', '120', '1', '40', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('Kreatur', 'Void Burst', 'EXPLOSION', '0.978', '120', '1', '40', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('Dragon', 'Dragonfire', 'EXPLOSION', '0.921', '120', '1', '40', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('LizardMan', 'Swamp Fire', 'EXPLOSION', '0.118', '120', '1', '40', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('Gnome', 'Spark Storm', 'EXPLOSION', '1.076', '120', '1', '40', '-', '-', 'Explosion 40 2 6 12 1 30.75 20.5'),
    ('Monk', 'Inner Light', 'HEAL_AREA', '32.262', '140', '1', '38', '4', '-', '-'),
    ('NatureMonster', 'Bloom', 'HEAL_AREA', '21.36', '140', '1', '38', '4', '-', '-'),
    ('Slime', 'Ooze Mend', 'HEAL_AREA', '60', '140', '1', '40', '4', '-', '-'),
    ('Defender', 'Unbreakable', 'BUFF_SELF_Defense', '20', '140', '20', '35', '-', '-', '-'),
    ('RunelordDwarf', 'Runic Bastion', 'BUFF_SELF_Defense', '20', '140', '20', '35', '-', '-', '-'),
    ('TentacleAlbine', 'Abyssal Shell', 'BUFF_SELF_Defense', '20', '140', '20', '35', '-', '-', '-'),
    ('TentacleGreen', 'Abyssal Shell', 'BUFF_SELF_Defense', '20', '140', '20', '35', '-', '-', '-'),
    ('Skeleton', 'Bone Legion Call', 'SKELARMY', '4', '140', '42', '38', '-', '-', 'SkeletonArmy 21 2 10 3 42 Skeleton'),
    ('Lich', 'Army of the Dead', 'SKELARMY', '4', '140', '42', '40', '-', '-', 'SkeletonArmy 21 2 10 3 42 Skeleton'),
    ('Elf', 'Arrow Rain', 'HAILSTORM', '0.673', '120', '11', '40', '-', '-', 'HailStorm 21 2 4 8 2 11 3.08 none 2.05'),
    ('DarkElf', 'Shadow Volley', 'HAILSTORM', '0.723', '120', '11', '40', '-', '-', 'HailStorm 21 2 4 8 2 11 3.08 none 2.05'),
    ('CaveHornet', 'Hive Storm', 'WHIRLWIND', '4/4', '120', '1', '30', '-', '-', 'Whirlwind 14 1 2 8 3 3'),
    ('Kobold', 'Gold Rush', 'PASSIVE_dig%', '40', '-', '-', '-', '-', '-', '-'),
    ('DwarfWorker', 'Mountain Heart', 'PASSIVE_dig%', '40', '-', '-', '-', '-', '-', '-'),
]

EXPECTED_TEMPLATES = [
    ('blocker', '1', 'Berserker', 'Arms', 'War Cries'),
    ('blocker', '2', 'Guardian', 'Bulwark', 'Arms'),
    ('blocker', '3', 'Warlord', 'War Cries', 'Bulwark'),
    ('blitzer', '1', 'Crusader', 'Zeal', 'Charge'),
    ('blitzer', '2', 'Protector', 'Protection', 'Zeal'),
    ('blitzer', '3', 'Vanguard', 'Charge', 'Protection'),
    ('flanker', '1', 'Shade', 'Shadow', 'Evasion'),
    ('flanker', '2', 'Venomist', 'Venom', 'Shadow'),
    ('flanker', '3', 'Dancer', 'Evasion', 'Venom'),
    ('archer', '1', 'Marksman', 'Bow', 'Hunter'),
    ('archer', '2', 'Hunter', 'Hunter', 'Bow'),
    ('archer', '3', 'Skirmisher', 'Skirmish', 'Bow'),
    ('caster', '1', 'Destroyer', 'Fire', 'Frost'),
    ('caster', '2', 'Healer', 'Healing', 'Frost'),
    ('caster', '3', 'Hexer', 'Frost', 'Fire'),
    ('worker', '1', 'Digger', 'Delving', 'Survival'),
    ('worker', '2', 'Claimer', 'Claiming', 'Survival'),
    ('worker', '3', 'Survivor', 'Survival', 'Delving'),
]

# Type -> (SkillGroup, SkillFamily, PreSkill, TierFourSkill)
EXPECTED_TYPES = {
    'Adventurer': ('flanker', 'human', 'none', 'T4_Adventurer'),
    'CaveHornet': ('flanker', 'vermin', 'VRM_1', 'T4_CaveHornet'),
    'Cultist': ('flanker', 'arcane', 'none', 'T4_Cultist'),
    'DarkElf': ('archer', 'elf', 'ARC_A2', 'T4_DarkElf'),
    'Defender': ('blocker', 'human', 'none', 'T4_Defender'),
    'Dragon': ('blitzer', 'dragonkin', 'DRK_1', 'T4_Dragon'),
    'Dwarf1': ('blocker', 'dwarf', 'none', 'T4_Dwarf1'),
    'Dwarf2': ('blocker', 'dwarf', 'none', 'T4_Dwarf2'),
    'DwarfWorker': ('worker', 'workfolk', 'WRK_C1', 'T4_DwarfWorker'),
    'Elf': ('archer', 'elf', 'ARC_A3', 'T4_Elf'),
    'Gnome': ('flanker', 'arcane', 'FLK_A2', 'T4_Gnome'),
    'Goblin': ('flanker', 'greenskin', 'FLK_A2', 'T4_Goblin'),
    'Knight': ('blocker', 'human', 'none', 'T4_Knight'),
    'Kobold': ('worker', 'workfolk', 'WRK_C1', 'T4_Kobold'),
    'Kreatur': ('caster', 'arcane', 'none', 'T4_Kreatur'),
    'LavaSpawn': ('blocker', 'demon', 'none', 'T4_LavaSpawn'),
    'Lich': ('caster', 'undead', 'UND_1', 'T4_Lich'),
    'LizardMan': ('caster', 'dragonkin', 'none', 'T4_LizardMan'),
    'Monk': ('blocker', 'human', 'none', 'T4_Monk'),
    'NatureMonster': ('blocker', 'wild', 'none', 'T4_NatureMonster'),
    'Orc': ('blocker', 'greenskin', 'none', 'T4_Orc'),
    'PitDemon': ('blocker', 'demon', 'none', 'T4_PitDemon'),
    'Rat': ('flanker', 'vermin', 'none', 'T4_Rat'),
    'Roach': ('flanker', 'vermin', 'none', 'T4_Roach'),
    'RunelordDwarf': ('blocker', 'dwarf', 'none', 'T4_RunelordDwarf'),
    'Scarab': ('blocker', 'vermin', 'none', 'T4_Scarab'),
    'Skeleton': ('blocker', 'undead', 'none', 'T4_Skeleton'),
    'Slime': ('flanker', 'wild', 'WLD_1', 'T4_Slime'),
    'Spider': ('flanker', 'vermin', 'none', 'T4_Spider'),
    'TentacleAlbine': ('blocker', 'tentacle', 'none', 'T4_TentacleAlbine'),
    'TentacleGreen': ('blocker', 'tentacle', 'none', 'T4_TentacleGreen'),
    'Troll': ('blocker', 'greenskin', 'none', 'T4_Troll'),
    'Wizard': ('caster', 'arcane', 'CST_B1', 'T4_Wizard'),
    'Wyvern': ('flanker', 'dragonkin', 'none', 'T4_Wyvern'),
}


def text(relative):
    return (root / relative).read_text(encoding='utf-8')


# ---------------------------------------------------------------- Python model of the rules
def parse_fixture(path):
    """Reads the example config: skills by id, tier four skills and templates."""
    skills, tiers, templates, block, kind = {}, {}, [], None, None
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.split('#')[0].strip()
        if not line:
            continue
        if line.startswith('[/'):
            if kind == 'Skill':
                skills[block['Id']] = block
            elif kind == 'TierFour':
                tiers[block['Creature']] = block
            else:
                templates.append(block)
            block = None
        elif line.startswith('['):
            kind, block = line.strip('[]'), {}
        else:
            key, _, rest = line.partition(' ')
            block[key] = rest.strip()
    return skills, tiers, templates


SKILLS, TIERS, TEMPLATES = parse_fixture(FIXTURE)


def owner_of(skill):
    return skill.get('Group') or skill.get('Family').lower()


def path_skill(owner, path, tier):
    for skill in SKILLS.values():
        if owner_of(skill) == owner and skill['Path'].lower() == path.lower() and int(skill['Tier']) == tier:
            return skill['Id']
    return ''


def can_raise(ranks, spent, group, family, tier_four, skill_id):
    if skill_id == tier_four:
        return ranks.get(skill_id, 0) == 0 and spent >= TIER_FOUR_MIN_SPENT
    skill = SKILLS.get(skill_id)
    if skill is None or owner_of(skill) not in (group, family):
        return False
    if ranks.get(skill_id, 0) >= MAX_RANK:
        return False
    tier = int(skill['Tier'])
    if tier == 1:
        return True
    previous = path_skill(owner_of(skill), skill['Path'], tier - 1)
    return ranks.get(previous, 0) >= (1 if tier == 2 else 2)


def model_picks(group, family, template):
    primary = [path_skill(group, template['Primary'], tier) for tier in (1, 2, 3)]
    picks = [primary[0], primary[1], primary[1], primary[2]]
    picks += [primary[0]] * (MAX_RANK - 1) + [primary[1]] * (MAX_RANK - 2) + [primary[2]] * (MAX_RANK - 1)
    if family:
        fam_path = next(s['Path'] for s in SKILLS.values() if owner_of(s) == family)
        fam = [path_skill(family, fam_path, tier) for tier in (1, 2, 3)]
        picks += [fam[0], fam[0], fam[1], fam[1], fam[2]]
    return picks


def model_build(template_index, seed, pre, level, group='blocker', family='greenskin', tier_four='T4_Orc'):
    """Spends the points of a creature of the level from level 10 on, one per level, as plan section 7.8 says."""
    template = [t for t in TEMPLATES if t['Group'] == group][template_index]
    ranks = {pre: 1} if pre else {}
    state, cursor, order = seed, 0, []
    picks = model_picks(group, family, template)
    alternative = [path_skill(group, template['Alternative'], tier) for tier in (1, 2, 3)]
    fam_path = next(s['Path'] for s in SKILLS.values() if owner_of(s) == family)
    family_ids = [path_skill(family, fam_path, tier) for tier in (1, 2, 3)]
    others = [path_skill(group, name, tier) for name in ('Arms', 'Bulwark', 'War Cries') for tier in (1, 2, 3)]

    def spent():
        return sum(v for k, v in ranks.items() if not k.startswith('T4_')) - (1 if pre and ranks.get(pre, 0) >= 1 else 0)

    for _ in range(max(0, level - FIRST_LEVEL + 1)):
        done = spent()
        if done >= TIER_FOUR_MIN_SPENT:
            if can_raise(ranks, done, group, family, tier_four, tier_four):
                ranks[tier_four] = 1
                order.append(tier_four)
            continue
        state = (1103515245 * state + 12345) % (2 ** 31)
        raised = None
        if state % 100 < DEVIATION:
            for skill_id in alternative:
                if can_raise(ranks, done, group, family, tier_four, skill_id):
                    raised = skill_id
                    break
        if raised is None:
            while cursor < len(picks):
                pick = picks[cursor]
                cursor += 1
                if can_raise(ranks, done, group, family, tier_four, pick):
                    raised = pick
                    break
        if raised is None:
            for skill_id in family_ids + others:
                if can_raise(ranks, done, group, family, tier_four, skill_id):
                    raised = skill_id
                    break
        if raised is None:
            break
        ranks[raised] = ranks.get(raised, 0) + 1
        order.append(raised)
    return ranks, order


# ---------------------------------------------------------------- compiled probe
PROBE = r'''
#include "creatureskill/CreatureSkillTree.h"
#include <fstream>
#include <iostream>
#include <sstream>
using namespace CreatureSkillTree;

static void printRanks(const SkillBuild& build)
{
    for(std::map<std::string, uint32_t>::const_iterator it = build.mRanks.begin(); it != build.mRanks.end(); ++it)
        std::cout << " " << it->first << "=" << it->second;
}

int main(int argc, char** argv)
{
    std::ifstream file(argv[1]);
    SkillTreeConfig config;
    std::string error;
    if(!config.load(file, error))
    {
        std::cout << "load error " << error << std::endl;
        return 1;
    }
    std::cout << "counts " << config.getSkills().size() << " " << config.getTierFours().size() << " "
              << config.getTemplateDefs().size() << std::endl;

    const uint32_t levels[5] = {1, 9, 10, 11, 30};
    for(int i = 0; i < 5; ++i)
        std::cout << "points " << levels[i] << " " << pointsAtLevel(levels[i], 10) << std::endl;

    TypeInfo orc;
    orc.mGroup = "blocker";
    orc.mFamily = "greenskin";
    orc.mTierFour = "T4_Orc";
    SkillBuild empty;
    std::cout << "unlock A2 empty " << canRaise(config, orc, empty, "BLK_A2", 5) << std::endl;
    SkillBuild one;
    one.mRanks["BLK_A1"] = 1;
    std::cout << "unlock A2 after A1 " << canRaise(config, orc, one, "BLK_A2", 5) << std::endl;
    one.mRanks["BLK_A2"] = 1;
    std::cout << "unlock A3 after A2 rank 1 " << canRaise(config, orc, one, "BLK_A3", 5) << std::endl;
    one.mRanks["BLK_A2"] = 2;
    std::cout << "unlock A3 after A2 rank 2 " << canRaise(config, orc, one, "BLK_A3", 5) << std::endl;
    std::cout << "unlock other path tier 2 " << canRaise(config, orc, one, "BLK_B2", 5) << std::endl;
    std::cout << "unlock rank limit " << canRaise(config, orc, one, "BLK_A1", 1) << std::endl;
    std::cout << "unlock foreign skill " << canRaise(config, orc, one, "GRN_9", 5) << std::endl;
    SkillBuild nineteen;
    nineteen.mRanks["BLK_A1"] = 5;
    nineteen.mRanks["BLK_A2"] = 5;
    nineteen.mRanks["BLK_A3"] = 5;
    nineteen.mRanks["BLK_B1"] = 4;
    std::cout << "tier4 at 19 " << canRaise(config, orc, nineteen, "T4_Orc", 5) << std::endl;
    nineteen.mRanks["BLK_B1"] = 5;
    std::cout << "tier4 at 20 " << canRaise(config, orc, nineteen, "T4_Orc", 5) << std::endl;
    SkillBuild preSkilled;
    TypeInfo pre = orc;
    pre.mPreSkill = "GRN_1";
    startBuild(preSkilled, pre, 77);
    std::cout << "pre spent " << spentInPaths(preSkilled, pre) << " rank " << getRank(preSkilled, "GRN_1") << std::endl;

    for(int t = 0; t < 3; ++t)
    {
        std::cout << "picks " << t;
        std::vector<std::string> picks = templatePicks(config, orc, t, 5);
        for(size_t i = 0; i < picks.size(); ++i)
            std::cout << " " << picks[i];
        std::cout << std::endl;
    }

    const uint32_t seeds[4] = {1, 12345, 987654321u, 4000000000u};
    for(int t = 0; t < 3; ++t)
    {
        for(int s = 0; s < 4; ++s)
        {
            for(int p = 0; p < 2; ++p)
            {
                TypeInfo type = orc;
                if(p == 1)
                    type.mPreSkill = "GRN_1";
                SkillBuild build;
                build.mTemplate = t;
                startBuild(build, type, seeds[s]);
                std::cout << "build " << t << " " << seeds[s] << " " << p << " :";
                for(uint32_t level = 10; level <= 30; ++level)
                {
                    const std::string raised = spendNextPoint(config, type, build, 25.0, 5);
                    std::cout << " " << raised;
                }
                std::cout << " |";
                printRanks(build);
                std::cout << std::endl;
            }
        }
    }

    // The personal generator
    SkillBuild draws;
    draws.mRngState = 12345;
    std::cout << "draws";
    for(int i = 0; i < 5; ++i)
        std::cout << " " << nextDeviationDraw(draws);
    std::cout << std::endl;

    // Level up by level: spendUpToLevel gives the same result as the single points
    {
        SkillBuild leveled;
        leveled.mTemplate = 1;
        startBuild(leveled, orc, 12345);
        spendUpToLevel(config, orc, leveled, 9, 10, 25.0, 5);
        std::cout << "leveled 9 spent " << spentPoints(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 10, 10, 25.0, 5);
        std::cout << "leveled 10 spent " << spentPoints(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 30, 10, 25.0, 5);
        std::cout << "leveled 30 spent " << spentPoints(leveled, orc) << " tier4 " << getRank(leveled, "T4_Orc")
                  << " paths " << spentInPaths(leveled, orc) << std::endl;
        spendUpToLevel(config, orc, leveled, 30, 10, 25.0, 5);
        std::cout << "leveled again spent " << spentPoints(leveled, orc) << std::endl;
    }

    // Template choice: weight 1, times 3 when nobody follows
    {
        std::vector<uint32_t> followers;
        followers.push_back(2);
        followers.push_back(0);
        followers.push_back(1);
        const double units[6] = {0.0, 0.19, 0.2, 0.79, 0.8, 0.99};
        std::cout << "choose";
        for(int i = 0; i < 6; ++i)
            std::cout << " " << chooseTemplate(followers, units[i]);
        std::cout << std::endl;
        std::vector<uint32_t> none(3, 0);
        std::cout << "choose none";
        for(int i = 0; i < 6; ++i)
            std::cout << " " << chooseTemplate(none, units[i]);
        std::cout << std::endl;
    }

    // Reset rules
    {
        std::vector<uint32_t> followers;
        followers.push_back(3);
        followers.push_back(0);
        followers.push_back(0);
        std::cout << "reset a " << findResetTemplate(0, followers) << std::endl;
        followers[0] = 2;
        std::cout << "reset b " << findResetTemplate(0, followers) << std::endl;
        followers[0] = 3;
        followers[1] = 1;
        followers[2] = 1;
        std::cout << "reset c " << findResetTemplate(0, followers) << std::endl;
        followers[2] = 0;
        std::cout << "reset d " << findResetTemplate(0, followers) << std::endl;
        std::cout << "reset e " << findResetTemplate(-1, followers) << std::endl;

        SkillBuild chicken;
        countChicken(chicken, 2, 60.0);
        std::cout << "chicken 1 " << chicken.mChickens << " " << chicken.mRespecWindow << std::endl;
        countChicken(chicken, 2, 60.0);
        std::cout << "chicken 2 " << chicken.mChickens << " " << chicken.mRespecWindow << std::endl;
        tickRespecWindow(chicken, 59.5);
        std::cout << "window " << chicken.mRespecWindow << std::endl;
        tickRespecWindow(chicken, 1.0);
        std::cout << "window end " << chicken.mRespecWindow << std::endl;

        TypeInfo type = orc;
        type.mPreSkill = "GRN_1";
        SkillBuild before;
        before.mTemplate = 0;
        startBuild(before, type, 4242);
        spendUpToLevel(config, type, before, 30, 10, 25.0, 5);
        SkillBuild after = before;
        resetBuild(config, type, after, 2, 30, 10, 25.0, 5);
        std::cout << "reset build template " << after.mTemplate << " spent " << spentPoints(after, type) << " pre "
                  << getRank(after, "GRN_1") << " seed " << after.mSeed << " :";
        printRanks(after);
        std::cout << std::endl;
        SkillBuild again = before;
        resetBuild(config, type, again, 2, 30, 10, 25.0, 5);
        std::cout << "reset repeat " << (again.mRanks == after.mRanks) << std::endl;
        SkillBuild low = before;
        resetBuild(config, type, low, 1, 12, 10, 25.0, 5);
        std::cout << "reset level 12 spent " << spentPoints(low, type) << " pre " << getRank(low, "GRN_1") << std::endl;
    }

    // Save and stream round trip
    {
        SkillBuild build;
        build.mTemplate = 2;
        startBuild(build, orc, 31337);
        spendUpToLevel(config, orc, build, 20, 10, 25.0, 5);
        build.mChickens = 1;
        build.mRespecWindow = 12.25;
        std::ostringstream out;
        writeBuild(build, out);
        std::cout << "stream " << out.str() << std::endl;
        std::istringstream in(out.str());
        SkillBuild back;
        const bool ok = readBuild(in, back);
        std::ostringstream again;
        writeBuild(back, again);
        std::cout << "roundtrip " << ok << " " << (again.str() == out.str()) << " " << (back.mRanks == build.mRanks)
                  << std::endl;
        std::istringstream shortInput("2 31337 5");
        SkillBuild bad;
        std::cout << "short " << readBuild(shortInput, bad) << std::endl;
        std::cout << "passive dmg " << passiveSum(config, build, "dmg%") << " hp " << passiveSum(config, build, "hp%")
                  << " none " << passiveSum(config, build, "ar%") << std::endl;
    }

    // Skill lines
    {
        SkillNumber none;
        SkillNumber seven;
        seven.mSet = true;
        seven.mValue = 55;
        const SkillDef* roar = config.findSkill("BLK_C1");
        std::cout << "line roar1 " << buildSkillLine(roar->mKind, roar->mValues[0], roar->mCooldown, roar->mDuration,
            roar->mRadius, roar->mRange, roar->mBaseLine) << std::endl;
        std::cout << "line roar5 " << buildSkillLine(roar->mKind, roar->mValues[4], roar->mCooldown, roar->mDuration,
            roar->mRadius, roar->mRange, roar->mBaseLine) << std::endl;
        const SkillDef* spin = config.findSkill("BLK_C3");
        std::cout << "line spin " << buildSkillLine(spin->mKind, spin->mValues[2], spin->mCooldown, spin->mDuration,
            spin->mRadius, spin->mRange, spin->mBaseLine) << std::endl;
        const SkillDef* rally = config.findSkill("BLK_C2");
        std::cout << "line rally " << buildSkillLine(rally->mKind, rally->mValues[1], rally->mCooldown,
            rally->mDuration, rally->mRadius, rally->mRange, rally->mBaseLine) << std::endl;
        const SkillDef* blow = config.findSkill("BLK_A3");
        std::cout << "line strike " << buildSkillLine(blow->mKind, blow->mValues[3], blow->mCooldown, blow->mDuration,
            blow->mRadius, blow->mRange, blow->mBaseLine) << std::endl;
        const SkillDef* wall = config.findSkill("BLK_B2");
        std::cout << "line defense " << buildSkillLine(wall->mKind, wall->mValues[0], wall->mCooldown,
            wall->mDuration, wall->mRadius, wall->mRange, wall->mBaseLine) << std::endl;
        const SkillDef* mend = config.findSkill("GRN_3");
        std::cout << "line heal " << buildSkillLine(mend->mKind, mend->mValues[1], mend->mCooldown, mend->mDuration,
            mend->mRadius, mend->mRange, mend->mBaseLine) << std::endl;
        const SkillDef* passive = config.findSkill("BLK_A1");
        std::cout << "line passive [" << buildSkillLine(passive->mKind, passive->mValues[0], passive->mCooldown,
            passive->mDuration, passive->mRadius, passive->mRange, passive->mBaseLine) << "]" << std::endl;
        const TierFourDef* frenzy = config.findTierFour("Orc");
        std::cout << "line tier4 " << buildSkillLine(frenzy->mKind, frenzy->mValue, frenzy->mCooldown,
            frenzy->mDuration, frenzy->mRadius, frenzy->mRange, frenzy->mBaseLine) << std::endl;
        std::cout << "line explosion " << buildSkillLine("EXPLOSION", "0.5", none, none, none, none,
            "Explosion 40 2 6 12 1 30.75 20.5") << std::endl;
        std::cout << "line grenade " << buildSkillLine("GRENADE", "0.5", seven, none, none, none,
            "Grenade 10 2 6 0 8 Cannonball none 1 0 0 0 0 5 0.1 2 0 0 0 0 6.97 10.46") << std::endl;
        std::cout << "line missing base " << buildSkillLine("EXPLOSION", "0.5", none, none, none, none, "").size()
                  << std::endl;
        std::cout << "line class " << skillClassOfKind("HEAL_AREA") << " " << skillClassOfKind("PASSIVE_hp%").size()
                  << std::endl;
    }
    return 0;
}
'''



# Probe for the real config: every rank of every skill and every tier four skill builds a skill line
REAL_PROBE = r'''
#include "creatureskill/CreatureSkillTree.h"
#include <fstream>
#include <iostream>
using namespace CreatureSkillTree;

int main(int argc, char** argv)
{
    std::ifstream file(argv[1]);
    SkillTreeConfig config;
    std::string error;
    if(!config.load(file, error))
    {
        std::cout << "load error " << error << std::endl;
        return 1;
    }
    std::cout << "counts " << config.getSkills().size() << " " << config.getTierFours().size() << " "
              << config.getTemplateDefs().size() << std::endl;
    const std::vector<SkillDef>& skills = config.getSkills();
    for(size_t i = 0; i < skills.size(); ++i)
    {
        const SkillDef& def = skills[i];
        for(size_t rank = 0; rank < def.mValues.size(); ++rank)
        {
            std::cout << "line " << def.mId << " " << def.mKind << " " << (rank + 1) << " : "
                      << buildSkillLine(def.mKind, def.mValues[rank], def.mCooldown, def.mDuration, def.mRadius,
                                        def.mRange, def.mBaseLine)
                      << std::endl;
        }
    }
    const std::vector<TierFourDef>& tiers = config.getTierFours();
    for(size_t i = 0; i < tiers.size(); ++i)
    {
        const TierFourDef& def = tiers[i];
        std::cout << "line T4_" << def.mCreature << " " << def.mKind << " 1 : "
                  << buildSkillLine(def.mKind, def.mValue, def.mCooldown, def.mDuration, def.mRadius, def.mRange,
                                    def.mBaseLine)
                  << std::endl;
    }
    return 0;
}
'''


def check_real_probe(output):
    """The loader reads the real config completely and every active skill builds a non-empty skill line of the class
    of its kind; passive skills build none."""
    assert output[0] == 'counts 90 34 18', output[0]
    classes = dict(KINDS_WITH_LINE)
    classes.update({'STRIKE': 'Strike', 'AURA_ALLY_StrengthChange': 'AuraAlly', 'HEAL_SELF': 'HealSelf',
                    'HEAL_ALLY': 'HealAlly', 'HEAL_AREA': 'HealArea'})
    built = 0
    for entry in output[1:]:
        head, _, line = entry.partition(' : ')
        _, skill_id, kind, rank = head.split()
        if kind.startswith('PASSIVE_'):
            assert line == '', entry
        else:
            assert line.split()[0] == classes[kind], entry
            built += 1
    assert built == 5 * sum(1 for row in EXPECTED_SKILLS if not row[6].startswith('PASSIVE_')) + \
        sum(1 for row in EXPECTED_TIER_FOUR if not row[2].startswith('PASSIVE_')), built


def run_probe(require, source=PROBE, config=FIXTURE):
    compiler = shutil.which('cl')
    if compiler is None:
        assert not require, '--probe needs the compiler (cl) in the PATH'
        print('compiled probe not run (no cl in the PATH)')
        return None
    with tempfile.TemporaryDirectory() as work_name:
        work = Path(work_name)
        (work / 'probe.cpp').write_text(source, encoding='utf-8')
        subprocess.run(['cl', '/nologo', '/EHsc', '/std:c++17', f'/I{root / "source"}', 'probe.cpp',
                        str(root / 'source/creatureskill/CreatureSkillTree.cpp'), '/Fe:probe.exe'],
                       cwd=work, check=True, stdout=subprocess.DEVNULL)
        result = subprocess.run([str(work / 'probe.exe'), str(config)], cwd=work, check=True,
                                capture_output=True, text=True)
    return result.stdout.splitlines()


def lines_starting(output, prefix):
    return [line for line in output if line.startswith(prefix)]


def check_probe(output):
    out = '\n'.join(output)
    assert 'counts 12 1 3' in out, out[:200]
    # 7.1: one point per level from 10 to 30 (21 points)
    for level, points in ((1, 0), (9, 0), (10, 1), (11, 2), (30, 21)):
        assert f'points {level} {points}\n' in out + '\n', (level, points)
    # 7.2: unlock rules and tier 4
    for line, value in (('unlock A2 empty', 0), ('unlock A2 after A1', 1), ('unlock A3 after A2 rank 1', 0),
                        ('unlock A3 after A2 rank 2', 1), ('unlock other path tier 2', 0), ('unlock rank limit', 0),
                        ('unlock foreign skill', 0), ('tier4 at 19', 0), ('tier4 at 20', 1)):
        assert f'{line} {value}' in output, (line, value)
    # 7.3: the free rank of the pre-skill is not a spent point
    assert 'pre spent 0 rank 1' in output
    # 7.8: the point order of the templates, from the rules written down independently
    for index, template in enumerate(t for t in TEMPLATES if t['Group'] == 'blocker'):
        expected = 'picks %d %s' % (index, ' '.join(model_picks('blocker', 'greenskin', template)))
        assert expected in output, expected
    # 7.8: the whole build of every template, seed and pre-skill equals the model (deviation with fixed seeds)
    seeds = (1, 12345, 987654321, 4000000000)
    for t in range(3):
        for seed in seeds:
            for p, pre in enumerate(('', 'GRN_1')):
                ranks, order = model_build(t, seed, pre, 30)
                order += [''] * (21 - len(order))
                tail = ' '.join(f'{k}={v}' for k, v in sorted(ranks.items()))
                expected = f'build {t} {seed} {p} : ' + ' '.join(order) + ' | ' + tail
                got = [line for line in output if line.startswith(f'build {t} {seed} {p} :')]
                assert got and got[0].replace('  ', ' ') == expected.replace('  ', ' '), (expected, got)
                # 20 points are spent at level 29 and the tier 4 skill is the 21st point
                assert order[20] == 'T4_Orc' and 'T4_Orc' not in order[:20], (t, seed, p, order)
    assert 'draws ' + ' '.join(str(d) for d in lcg_draws(12345, 5)) in output
    # Deviation really happens: with 25 percent over 20 points some build differs from the plain template order
    plain = {t: model_build(t, 1, '', 30)[1] for t in range(3)}
    assert any(model_build(t, s, '', 30)[1] != plain[t] for t in range(3) for s in seeds[1:])
    # Level by level and a repeated call give the same state
    assert 'leveled 9 spent 0' in output and 'leveled 10 spent 1' in output
    assert 'leveled 30 spent 21 tier4 1 paths 20' in output and 'leveled again spent 21' in output
    # Template choice with weights 1, 3, 1 (total 5): 0 to 0.2 -> 0, 0.2 to 0.8 -> 1, 0.8 to 1 -> 2
    assert 'choose 0 0 1 1 2 2' in output
    assert 'choose none 0 0 0 2 2 2' in output
    # 7.8 reset rules
    for line in ('reset a 1', 'reset b -1', 'reset c -1', 'reset d 2', 'reset e -1'):
        assert line in output, line
    assert 'chicken 1 1 0' in output and 'chicken 2 0 60' in output
    assert 'window 0.5' in output and 'window end 0' in output
    reset = [line for line in output if line.startswith('reset build template 2 spent 21 pre ')]
    assert reset, 'a reset spends all points again and keeps the free rank of the pre-skill'
    ranks, _ = model_build(2, 4242, 'GRN_1', 30)
    assert reset[0].endswith(': ' + ' '.join(f'{k}={v}' for k, v in sorted(ranks.items()))), reset
    assert 'reset repeat 1' in output
    assert 'reset level 12 spent 3 pre 1' in output
    # Stream round trip of the new creature fields
    assert 'roundtrip 1 1 1' in output and 'short 0' in output
    stream = lines_starting(output, 'stream ')[0].split()
    assert stream[1:7] == ['2', '31337', stream[3], stream[4], '1', '12.25'], stream
    # Passives add up over the ranked skills
    passive = lines_starting(output, 'passive dmg')[0].split()
    assert passive[-1] == '0', passive
    # Skill lines (7.4, 7.6)
    expected_lines = {
        'line roar1': 'StrengthSelf 55 2 0 20 1.01',
        'line roar5': 'StrengthSelf 55 2 0 20 1.05',
        'line spin': 'Whirlwind 14 1 2 0 1 1',
        'line rally': 'AuraAlly 60 0 0 4 20 1.007',
        'line strike': 'Strike 30 0 0 1.188',
        'line defense': 'DefenseSelf 45 0 0 25 0.298 0.298 0.298',
        'line heal': 'HealSelf 35 0 0 5 0 2.758',
        'line passive': '',
        'line tier4': 'StrengthSelf 140 0 0 20 1.201',
        'line explosion': 'Explosion 40 2 6 0 1 15.375 10.25',
    }
    for prefix, line in expected_lines.items():
        got = [l for l in output if l.startswith(prefix + ' ')]
        assert got and got[0][len(prefix) + 1:].replace('[', '').replace(']', '') == line, (prefix, got, line)
    # A grenade line: the cooldown cell replaces the base cooldown, the rank value halves every damage value
    assert 'line grenade Grenade 55 2 6 0 0 Cannonball none 1 0 0 0 0 2.5 0.05 2 0 0 0 0 3.485 5.23' in output
    assert 'line missing base 0' in output
    assert 'line class HealArea 0' in output


def lcg_draws(seed, count):
    draws, state = [], seed
    for _ in range(count):
        state = (1103515245 * state + 12345) % (2 ** 31)
        draws.append(state % 100)
    return draws


# ---------------------------------------------------------------- source checks
def function(source, signature):
    """Returns the source of the function that starts with the signature (up to its closing brace)."""
    start = source.index(signature)
    end = source.index('{', start) + 1
    depth = 1
    while depth:
        depth += (source[end] == '{') - (source[end] == '}')
        end += 1
    return source[start:end]


def check_sources():
    creature_cpp = text('source/entities/Creature.cpp')
    creature_h = text('source/entities/Creature.h')
    cmake = text('CMakeLists.txt')
    config_manager = text('source/utils/ConfigManager.cpp')

    # The loader: creatureSkills.cfg is read by the ConfigManager, the file exists with a documented header
    cfg = text('config/creatureSkills.cfg')
    for key in ('Id', 'Name', 'Kind', 'Group', 'Family', 'Path', 'Tier', 'Values', 'Mana', 'Cooldown', 'Duration',
                'Radius', 'Range', 'BaseLine', 'Creature', 'Value', 'Index', 'Primary', 'Alternative'):
        assert re.search(r'^#\s+' + key + r'\s', cfg, re.M), key
    for block in ('[Skill]', '[TierFour]', '[Template]'):
        assert block in cfg
    assert 'loadCreatureSkills' in config_manager and 'mCreatureSkillTree.load(' in config_manager
    assert 'creatureSkills.cfg' in config_manager and 'CreatureSkills' in text('config/global.cfg')
    example = FIXTURE.read_text(encoding='utf-8')
    assert '[/Skill]' in example and '[/TierFour]' in example and '[/Template]' in example

    # The skill classes: one file pair each, registered like HealSelf
    for name in ('Strike', 'AuraAlly', 'HealAlly', 'HealArea'):
        header = text(f'source/creatureskill/CreatureSkill{name}.h')
        source = text(f'source/creatureskill/CreatureSkill{name}.cpp')
        assert f'class CreatureSkill{name} : public CreatureSkill' in header
        assert f'static CreatureSkillRegister reg(new CreatureSkill{name}Factory);' in source
        assert f'const std::string CreatureSkill{name}Name = "{name}";' in source
        assert f'creatureskill/CreatureSkill{name}.cpp' in cmake
    assert 'creatureskill/CreatureSkillTree.cpp' in cmake
    heal_self = text('source/creatureskill/CreatureSkillHealSelf.cpp')
    assert 'mHealPercent' in heal_self and 'getSkillHealSelfBelow' in heal_self

    # Passives are read from the ranks (the stub is gone) and used by the derived values
    body = function(creature_cpp, 'double Creature::getSkillPassive(')
    assert 'passiveSum' in body and 'return 0.0;\n}' not in body.replace(' ', '')
    for stat in ('cd%', 'avoid', 'move%', 'wake%', 'hp%', 'ar%', 'dr%'):
        assert f'getSkillPassive("{stat}")' in creature_cpp, stat

    # Points, template choice, deviation and reset are driven from the creature
    assert 'CreatureSkillTree::spendUpToLevel' in function(creature_cpp, 'void Creature::updateSkillPoints(')
    assert 'chooseTemplate' in function(creature_cpp, 'void Creature::updateSkillPoints(')
    assert 'updateSkillPoints();' in function(creature_cpp, 'void Creature::setLevel(')
    assert 'initSkillBuild();' in function(creature_cpp, 'void Creature::setupDefinition(')
    assert 'resetBuild' in function(creature_cpp, 'void Creature::upkeepSkillTree(') and \
        'findResetTemplate' in function(creature_cpp, 'void Creature::upkeepSkillTree(')
    assert 'upkeepSkillTree();' in function(creature_cpp, 'void Creature::doUpkeep(')
    assert 'registerChickenEaten();' in text('source/creatureaction/CreatureActionEatChicken.cpp')

    # Save and network: the stream and the three packets carry the skill state; old saves load without it
    assert 'SkillBuild' in function(creature_cpp, 'void Creature::exportToStream(')
    assert 'readBuild' in function(creature_cpp, 'bool Creature::importFromStream(')
    for signature, call in (('void Creature::exportToPacket(', 'exportSkillBuildToPacket(os);'),
                            ('void Creature::exportToPacketForUpdate(', 'exportSkillBuildToPacket(os);'),
                            ('void Creature::importFromPacket(', 'importSkillBuildFromPacket(is);'),
                            ('void Creature::updateFromPacket(', 'importSkillBuildFromPacket(is);')):
        assert call in function(creature_cpp, signature), signature

    # Effect stacking (7.4): products and sums of the active contributions, only the own one is removed
    for name in ('Strength', 'Speed'):
        update = function(creature_cpp, f'void Creature::update{name}Modifier(')
        assert 'modifier *= it->second;' in update
    assert 'phy += it->second.mPhy;' in function(creature_cpp, 'void Creature::updateDefenseModifier(')
    for effect, calls in (('StrengthChange', ('setStrengthContribution', 'removeStrengthContribution')),
                          ('SpeedChange', ('setSpeedContribution', 'removeSpeedContribution')),
                          ('Defense', ('setDefenseContribution', 'removeDefenseContribution'))):
        source = text(f'source/creatureeffect/CreatureEffect{effect}.cpp')
        for call in calls:
            assert call in source, (effect, call)
        assert 'clear' not in function(source, f'void CreatureEffect{effect}::releaseEffect(')
    assert 'releaseEffect(*this)' in function(creature_cpp, 'void Creature::doUpkeep(')
    add_effect = function(creature_cpp, 'void Creature::addCreatureEffect(')
    assert 'effectRefreshKey' in add_effect and 'delete effect;' in add_effect and 'mNbTurnsEffect = ' in add_effect

    # Skill kinds: STRIKE is consumed by the melee blow against creatures only, spell damage scaling of 7.6
    melee = function(text('source/creatureskill/CreatureSkillMeleeFight.cpp'), 'bool CreatureSkillMeleeFight::tryUseFight(')
    creature_branch = melee[melee.index('rollMeleeDefence'):melee.index('phyAtk = magAtk = eleAtk = 0.0;')]
    assert 'consumeStrikeMultiplier()' in creature_branch and 'consumeStrikeMultiplier' not in melee[:melee.index('rollAttackHit')]
    assert 'getTreeSpellDamageFactor()' in text('source/creatureskill/CreatureSkillExplosion.cpp')
    assert 'getTreeSpellDamageFactor()' in text('source/creatureskill/CreatureSkillAreaDamage.cpp')
    factor = function(creature_cpp, 'double Creature::getTreeSpellDamageFactor(')
    assert 'getSkillSpellReferenceMinHP' in factor and 'damageMultiplierAt' in factor and 'spell%' in factor
    base = function(creature_cpp, 'double Creature::getHealBase(')
    assert 'getManaLevel()' in base and 'getMinHp()' in base
    assert 'getMaxHp' in text('source/creatureskill/CreatureSkillHealAlly.cpp')


# Lines of today's skill lists that the trees replace (section 7.7); only these may be removed from a skill list
REMOVED_LINES = ('HasteSelf', 'Teleport', 'HealSelf', 'Explosion', 'DefenseSelf', 'Weak', 'Slow', 'StrengthSelf',
                 'Invisible', 'Whirlwind', 'GasCloud', 'Drain', 'RaiseDead', 'Freeze', 'HailStorm', 'SkeletonArmy',
                 'GuidedBolt', 'Grenade')
# Skill lines that stay in a skill list
KEPT_LINES = ('Melee', 'MissileLaunch')
# Kinds whose skill scales a line of the base line table
KINDS_WITH_LINE = {
    'BUFF_SELF_StrengthChange': 'StrengthSelf', 'BUFF_SELF_SpeedChange': 'HasteSelf', 'BUFF_SELF_Defense': 'DefenseSelf',
    'DEBUFF_Weak': 'Weak', 'DEBUFF_Slow': 'Slow', 'EXPLOSION': 'Explosion', 'HAILSTORM': 'HailStorm',
    'GASCLOUD': 'GasCloud', 'GRENADE': 'Grenade', 'GUIDEDBOLT': 'GuidedBolt', 'WHIRLWIND': 'Whirlwind',
    'FREEZE': 'Freeze', 'INVISIBLE': 'Invisible', 'TELEPORT': 'Teleport', 'DRAIN': 'Drain', 'RAISEDEAD': 'RaiseDead',
    'SKELARMY': 'SkeletonArmy'}
# Tier four kinds that carry a line of the base line table (and then no range)
TIER_FOUR_LINES = {'EXPLOSION': 'Explosion', 'HAILSTORM': 'HailStorm', 'SKELARMY': 'SkeletonArmy',
                   'WHIRLWIND': 'Whirlwind'}
SKILL_GROUPS = ('blocker', 'blitzer', 'flanker', 'archer', 'caster', 'worker')
SKILL_FAMILIES = ('greenskin', 'dwarf', 'undead', 'vermin', 'tentacle', 'demon', 'elf', 'human', 'arcane', 'dragonkin',
                  'wild', 'workfolk')


def level_files():
    """All level files of the repository as repository relative paths."""
    return sorted(p.relative_to(root).as_posix() for p in (root / 'levels').rglob('*.level'))


def parse_config_blocks(relative):
    """Reads the real skill config: lists of Skill, TierFour and Template blocks in file order."""
    blocks = {'Skill': [], 'TierFour': [], 'Template': []}
    block, kind = None, None
    for raw in text(relative).splitlines():
        line = raw.split('#')[0].strip()
        if not line:
            continue
        if line.startswith('[/'):
            assert kind == line[2:-1], line
            blocks[kind].append(block)
            block, kind = None, None
        elif line.startswith('['):
            assert block is None, line
            kind, block = line.strip('[]'), {}
        else:
            key, _, rest = line.partition(' ')
            assert key not in block, (key, line)
            block[key] = rest.strip()
    assert block is None
    return blocks


def creature_blocks(relative):
    """Reads the [Creature] blocks of a config or level file: name -> list of (keys, skill line tokens)."""
    result, name, keys, skills, in_skills = {}, None, {}, [], False
    for raw in text(relative).splitlines():
        stripped = raw.strip()
        if stripped == '[Creature]':
            name, keys, skills, in_skills = None, {}, [], False
        elif stripped == '[CreatureSkills]':
            in_skills = True
        elif stripped == '[/CreatureSkills]':
            in_skills = False
        elif stripped == '[/Creature]':
            if name is not None:
                result.setdefault(name, []).append((keys, skills))
        elif stripped and not stripped.startswith('#'):
            tokens = stripped.split()
            if in_skills:
                skills.append(tokens)
            elif tokens[0] == 'Name' and name is None and len(tokens) > 1:
                name = tokens[1]
            elif len(tokens) > 1:
                keys.setdefault(tokens[0], tokens[1])
    return result


def check_skill_rows(skills):
    """Every skill block equals its expected row of the catalog and follows the base line rules of the syntax."""
    assert len(skills) == len(EXPECTED_SKILLS) == 90, len(skills)
    for block, row in zip(skills, EXPECTED_SKILLS):
        (sid, owner_key, owner, path, tier, name, kind, values, mana, cooldown, duration, radius, range_, base) = row
        assert [k for k in ('Group', 'Family') if k in block] == [owner_key], sid
        assert block[owner_key] == owner, sid
        got = (block['Id'], block['Path'], block['Tier'], block['Name'], block['Kind'], block['Values'], block['Mana'],
               block['Cooldown'], block['Duration'], block['Radius'], block['Range'], block['BaseLine'])
        assert got == (sid, path, tier, name, kind, values, mana, cooldown, duration, radius, range_, base), (sid, got)
        assert set(block) == {'Id', 'Name', 'Kind', owner_key, 'Path', 'Tier', 'Values', 'Mana', 'Cooldown',
                              'Duration', 'Radius', 'Range', 'BaseLine'}, sid
        assert len(values.split()) == 5 and (mana == '-' or len(mana.split()) == 5), sid
        # A line of the base line table exactly for the kinds that scale one, and it is the line of that kind
        if kind in KINDS_WITH_LINE:
            assert base.split()[0] == KINDS_WITH_LINE[kind], sid
        else:
            assert base == '-', sid
    assert len({b['Id'] for b in skills}) == 90

    # Structure: 6 groups with 3 paths of 3 tiers, 12 families with one path of 3 tiers
    for group in SKILL_GROUPS:
        group_skills = [b for b in skills if b.get('Group') == group]
        assert len(group_skills) == 9, group
        assert len({b['Path'] for b in group_skills}) == 3, group
        for path in {b['Path'] for b in group_skills}:
            assert sorted(b['Tier'] for b in group_skills if b['Path'] == path) == ['1', '2', '3'], (group, path)
    for family in SKILL_FAMILIES:
        family_skills = [b for b in skills if b.get('Family') == family]
        assert sorted(b['Tier'] for b in family_skills) == ['1', '2', '3'], family
        assert len({b['Path'] for b in family_skills}) == 1, family


def check_tier_four_rows(tiers):
    """Every tier four block equals its expected row; lines and radius follow the syntax of the config."""
    assert len(tiers) == len(EXPECTED_TIER_FOUR) == len(EXPECTED_TYPES) == 34, len(tiers)
    for block, row in zip(tiers, EXPECTED_TIER_FOUR):
        creature, name, kind, value, cooldown, duration, mana, radius, range_, base = row
        got = (block['Creature'], block['Name'], block['Kind'], block['Value'], block['Cooldown'], block['Duration'],
               block['Mana'], block['Radius'], block['Range'], block['BaseLine'])
        assert got == row, (creature, got)
        assert set(block) == {'Creature', 'Name', 'Kind', 'Value', 'Cooldown', 'Duration', 'Mana', 'Radius', 'Range',
                              'BaseLine'}, creature
        if kind in TIER_FOUR_LINES:
            assert base.split()[0] == TIER_FOUR_LINES[kind] and range_ == '-' and radius == '-', creature
        else:
            assert base == '-' and range_ == '-', creature
            assert (radius == '4') == (kind == 'HEAL_AREA'), creature
    assert {b['Creature'] for b in tiers} == set(EXPECTED_TYPES)


def check_template_rows(templates, skills):
    """Every template block equals its expected row; each group has three templates over its three paths."""
    assert len(templates) == len(EXPECTED_TEMPLATES) == 18
    for block, row in zip(templates, EXPECTED_TEMPLATES):
        got = (block['Group'], block['Index'], block['Name'], block['Primary'], block['Alternative'])
        assert got == row, got
        assert set(block) == {'Group', 'Index', 'Name', 'Primary', 'Alternative'}
    for group in SKILL_GROUPS:
        group_paths = {b['Path'] for b in skills if b.get('Group') == group}
        group_templates = [t for t in templates if t['Group'] == group]
        assert [t['Index'] for t in group_templates] == ['1', '2', '3'], group
        for template in group_templates:
            assert template['Primary'] in group_paths and template['Alternative'] in group_paths, template
            assert template['Primary'] != template['Alternative'], template
        assert {t['Primary'] for t in group_templates} == group_paths, group


def check_type_keys(skills, tiers):
    """Per-type keys of creatures.cfg and the level files: values of the catalog, every named id exists."""
    skill_ids = {b['Id'] for b in skills}
    tier_ids = {'T4_' + b['Creature'] for b in tiers}
    families = {b['Family'] for b in skills if 'Family' in b}
    creatures = creature_blocks('config/creatures.cfg')
    for name, (group, family, pre, tier_four) in EXPECTED_TYPES.items():
        assert len(creatures[name]) == 1, name
        keys = creatures[name][0][0]
        got = (keys.get('SkillGroup'), keys.get('SkillFamily'), keys.get('PreSkill'), keys.get('TierFourSkill'))
        assert got == (group, family, pre, tier_four), (name, got)
        assert family in families, name
        assert pre == 'none' or pre in skill_ids, name
        assert tier_four in tier_ids, name
    champion = creatures['Champion'][0][0]
    assert champion.get('SkillGroup') == 'none' and champion.get('SkillFamily') == 'none', champion
    assert champion.get('PreSkill', 'none') == 'none' and champion.get('TierFourSkill', 'none') == 'none'
    # Level-file classes carry the keys of their base type and every id they name exists
    for relative in level_files():
        for name, entries in creature_blocks(relative).items():
            for keys, skill_lines in entries:
                if 'SkillGroup' not in keys:
                    continue
                assert keys['SkillGroup'] in SKILL_GROUPS, (relative, name)
                assert keys.get('SkillFamily', 'none') in families | {'none'}, (relative, name)
                assert keys.get('PreSkill', 'none') in skill_ids | {'none'}, (relative, name)
                assert keys.get('TierFourSkill', 'none') in tier_ids | {'none'}, (relative, name)


def check_removed_lines():
    """Section 7.7: the skill lists keep Melee and the MissileLaunch lines; the Champion keeps every line."""
    for relative in ['config/creatures.cfg'] + level_files():
        for name, entries in creature_blocks(relative).items():
            for keys, skill_lines in entries:
                names = [tokens[0] for tokens in skill_lines]
                if name == 'Champion':
                    continue
                for line_name in names:
                    assert line_name not in REMOVED_LINES, (relative, name, line_name)
                    assert line_name in KEPT_LINES, (relative, name, line_name)
                assert names.count('Melee') <= 1, (relative, name)
                assert names.count('MissileLaunch') <= 1, (relative, name)
    creatures = creature_blocks('config/creatures.cfg')
    # The Champion keeps every line it has (Melee and its Explosion), the Explosion line is not removed
    assert sorted(t[0] for t in creatures['Champion'][0][1]) == ['Explosion', 'Melee']
    # Casters and archers keep their first MissileLaunch, the Dragon its second attack line (a MissileLaunch after
    # Melee), everything else has none
    for name, (group, family, pre, tier_four) in EXPECTED_TYPES.items():
        shots = [t[0] for t in creatures[name][0][1]].count('MissileLaunch')
        if group in ('caster', 'archer', 'blitzer'):
            assert shots == 1, name
        else:
            assert shots == 0, name


def check_content():
    """The content of creatureSkills.cfg (every row of the catalog and the templates), the per-type keys and the
    removed lines; the expected values are data of this check."""
    blocks = parse_config_blocks('config/creatureSkills.cfg')
    check_skill_rows(blocks['Skill'])
    check_tier_four_rows(blocks['TierFour'])
    check_template_rows(blocks['Template'], blocks['Skill'])
    check_type_keys(blocks['Skill'], blocks['TierFour'])
    check_removed_lines()


def main():
    require_probe = '--probe' in sys.argv
    check_sources()
    check_content()
    output = run_probe(require_probe)
    if output is not None:
        if '--show' in sys.argv:
            print(chr(10).join(output))
        check_probe(output)
    real_output = run_probe(require_probe, REAL_PROBE, root / 'config/creatureSkills.cfg')
    if real_output is not None:
        check_real_probe(real_output)
    print('check_creature_skill_trees: ok')


main()
