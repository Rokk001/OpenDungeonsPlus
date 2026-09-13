# Creature feeding animations

## September 13 screenshot follow-up

The 12:18:30 screenshot shows the Cultist's broad sleeve across the meal, not a
book: its mesh has no equipment submesh or weapon-bone vertex assignments. The
current solver places the chicken at the wrist bone, inside that sleeve. Its
authored middle-finger joint provides a measured grip point beyond the cuff;
use that point for contact and carrying without changing the sleeve geometry.
Kobold's pick is embedded in its main mesh, with 36 vertices assigned to the
separate `Pick` bone. Stow only that tool during feeding and restore its original
bone scale when the meal ends or is interrupted. Do not hide body submeshes or
change equipment ownership, meal timing or gameplay.

The corrected grip follows the actual middle-finger joints; the isolated real
Ogre matrix passes 10,124 checks (32 failures against the preceding commit), including worker tool restoration on completion
and walking interruption. The extended committed limb test passes 109 checks,
including finger contact, wrist clearance and unchanged forearm lengths. Three
additional elevated camera angles for both affected models were rendered and
inspected. The tool fades out before contact and returns during the existing
release phase; cancellation restores its captured scale immediately. These
visual-only corrections do not require a version or save-format change.
Clean Release compilation and runtime preparation pass; the prepared executable
is recorded in BUILDING.md. No manual game test was started.

## Ground pickup by creatures with hands

The presentation currently interpolates the chicken directly to the head while
only some humanoid forearms rotate; heavy and magical bipeds never reach for it.
Use the inspected hand/arm and foot/leg chains to stage a grounded reach, contact,
hand-carried lift and eating, restoring the pose on completion or cancellation.
Keep the existing direct-feeding path for models without both hands and legs.
The consumed copy must stay at its starting position until contact, then follow
the actual hands rather than a separate flight path. Existing meal gameplay,
the 2.2-second presentation duration, save format and version remain unchanged.

The renderer now reaches with all 22 hand-equipped bipeds and preserves direct
feeding for the other 11 models. It uses the measured limb lengths, keeps the
chicken grounded through the first 28 percent, then carries it between the
actual hands before eating; feather bursts follow the later bites. Short-legged
models shuffle within their reach rather than stretching their legs. The dwarf
with separate body/armour rigs drives both, and cancellation restores every
manual-bone flag and pose. Root updates preserve Ogre's manual-bone dirty flag
so the rendered skin matches the calculated hand contact.

The combined real-Ogre probe passes 10,114 checks, including all 33 models,
actual ground contact, carried-chicken attachment, skinning invalidation,
unchanged limb lengths, completion/walking/pickup cleanup and rotated level-1/30
reach cases. It also retains the sleep-culling, combat and accepted hand/drop/
get-up regressions. Representative rendered reach, lift and eating phases were
inspected, including the separate dwarf rigs. The committed
`source/tests/check_feeding_limb.py` passes 64 focused solver checks against the
installed Ogre library without a game or window. Release compilation passes;
live gameplay and subjective appearance remain for the user's acceptance.

## Reported black rectangles

The feather material alpha-blends a flare image whose black background has
fully opaque alpha (including pixel 0,0). The narrow particle quads therefore
render black rectangles, not cut-out feathers. Replace that flare sampling
with a small unlit feather-shaped shader using particle UV and vertex colour;
retain the existing timing, movement, colour/fade and feeding mechanics.
The old material fails the real framebuffer corner-transparency check and
visibly renders a black quad; the replacement passes all 2,455 renderer checks.
The permanent `source/tests/check_feather_material.py` additionally passes ten
GPU checks for all four transparent corners, a visible vane and complete fade.
Release build and runtime preparation pass; the actual in-game meal needs retest.

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
