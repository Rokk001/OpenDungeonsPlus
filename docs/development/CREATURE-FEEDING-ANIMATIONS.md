# Creature feeding animations

## Existing path and scoped change

Eating already uses an authoritative chicken lock, removes the consumed chicken
on its next upkeep and applies existing hunger, healing and cooldown values.
The visible creature previously played its generic weapon attack once.

The change introduces a dedicated feeding presentation with a generated skeletal
clip based on each model's idle pose and actual head, jaw and arm bones, distinct
rhythms for small crawlers, lunging beasts, large eaters, humanoids, magical
creatures and tentacles, and short feather bursts. A presentation-only chicken
copy is animated from its consumed world position toward the creature's mouth;
the already-consumed source is hidden locally and retains its normal server
removal. Pickup, death, movement and scene teardown must cancel the presentation
and restore the actor's transform. Hunger, healing and cooldown remain unchanged.

The real Ogre inventory covers all 33 current creature meshes and their actual
bone and animation names; no dedicated eating clip existed in that inventory.
## Verification

The isolated real Ogre renderer passes 815 checks, including the retained hand,
drop, get-up and combat regressions and feeding lifecycle checks for all 33 meshes.
It loads the production feather material and particle system, confirms live
particles, advances the generated clips, releases the consumed-chicken copy,
restores transforms and verifies pickup cancellation. Close-up renders exposed
an incorrect chicken pivot; the final presentation centers and turns the chicken
at the mouth instead of placing its feet on the head.

Windows Release compilation, runtime preparation and `git diff --check` pass.
Evidence is in the ignored `build/windows/held-display-probe-feeding-final.log`
and `build/reference-audit/feeding-*.png`. No manual game was launched. The
multiplayer event timing and subjective in-game appearance remain for user testing.
