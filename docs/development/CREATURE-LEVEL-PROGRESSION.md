# Creature level progression

## Existing paths and bounded change

Levels already increased HP/defenses linearly and attack channels through skill
definitions. The gap was weak visible growth, lost experience surplus and maximum
HP increasing without a corresponding increase in current HP.

The thirty-level cap, save format, species, skill unlocks, room caps, research,
movement, weapon bonuses and cooldowns remain unchanged. Vitality, physical/
magical/elemental defenses and innate melee/ranged power now use a shared
interpolated curve, from 1x at level 1 to 6x at level 30. Configured linear
growth remains a floor, preserving custom high-growth definitions. Damage keeps
its existing level-1 base (including the first configured per-level increment).

All 34 default species receive strictly increasing XP costs with a gradual early
curve and steeper later progression. Each species retains exactly the same total
XP requirement to reach level 30. The existing explicit XP-table configuration
format is unchanged; saved/custom definitions retain their own XP tables.

Level-ups retain surplus experience, including grants covering multiple levels.
Current HP grows proportionally with maximum HP, without fully healing an injured
creature or reviving a dead/knocked-out one. Direct level changes remain clamped
to 1..30. Capped creatures no longer accumulate unusable experience.

The pre-existing ranged elemental-base mapping and strength-effect discrepancy
are outside this contribution; this change preserves those channel baselines
instead of silently mixing a separately releasable combat fix into the feature.

## Verification

- Compiled production stat/level methods: 5,115 checks passed for every level
  across all 34 default species, health fractions, XP boundaries, large grants,
  invalid gains, cap, unchanged movement and configured-growth floors.
- Default XP validation: 986 checks passed; separate exact-decimal comparison
  confirmed all 34 species' original total XP budgets are unchanged.
- Missile launch/visibility regression: 17 checks passed.
- The expanded probe adds 180 checks of production melee/ranged channel
  calculations; it compiles, but Windows application control blocked that new
  executable (4551). It also blocked the refreshed packet regression; the earlier
  377 packet checks passed before the level change. These are not runtime passes.
- Test entry points: `source/tests/check_creature_level_progression.py`,
  `source/tests/check_creature_progress.py`,
  `source/tests/check_missile_launch_visibility.py`.
- No game was launched. User acceptance covers training/combat advancement,
  lower- versus higher-level vitality/power, saved creatures and the XP ring.

No release/version bump is requested; the development index and feature note
are updated, with cumulative executable evidence in BUILDING.md.
