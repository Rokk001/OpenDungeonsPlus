# Creature combat feedback

## Approved animation follow-up

Inspection found that the preceding renderer only cycled faster authored attacks
and squashed the whole target on impact. The follow-up extends those clips rather
than replacing their individual skeletal motion, and removes the generic whole-
model squash. The existing combat payload distinguishes body damage from absorbed
hits; it does not report a new active blocking mechanic. Blood remains optional
and subtle. The blood flare also had opaque black corners; the material now uses
flare brightness for transparency, without changing the particle count.

## Scope

Creature melee combat derives alternating variants from the model's authored
attack clips. A nonlinear playback curve separates anticipation, a quick strike
and recovery; clip lengths are capped at 0.95 seconds for biting/crawling types,
1.45 seconds for heavy types and 1.15 seconds otherwise, before the existing
combat playback multiplier. Shorter original clips retain their duration.
Body turns, head/jaw motion and root-bone weight shifts distinguish biting,
crawling, heavy, flying and tentacled creatures. Fluid creatures deform their
body bone during windup, extension and recoil. These are skeletal changes, not
movement or scale changes to the creature's gameplay node.

Targets receive a 0.28-second additive skeletal response from one of four local
impact directions while retaining their underlying attack. Absorbed hits use
bracing or armed forearm recoil; damage to the body always uses the hit response.
Heavy creatures recoil less; crawlers crouch on absorbed hits. Armed opponents
produce a compact spark burst, while applied body damage produces a restrained
blood burst at model-scaled height. The blood presentation can be disabled on the
Game page in Settings; sparks and combat rules remain unchanged.

Death clips play slightly faster. The Cultist and Lich models, whose authored
death clips do not finish in a usable lying pose, use the same short model-based
fall and grounded alignment as hand drops. Other creatures retain their authored
death clips.

## Existing path and integration

The combat-only animation request is emitted by the existing creature attack
path. The renderer resolves it to the model's available attack variants without
changing non-combat uses of the original attack animation. The existing melee
damage result and equipped weapons classify the presentation-only impact payload;
health, defense, targeting, timing and sound calculations are unchanged.

Impact notifications are sent only to human players with vision of the target.
The client owns the short-lived particles and additive skeletal reaction and removes
them when they finish, when the creature disappears or when the renderer stops.
The new notification value is appended to preserve existing protocol numbering.

## Verification boundary

The follow-up passes 5,062 isolated real-Ogre lifecycle/geometry checks across all
33 creature meshes, including derived attacks, four-direction hit and guard
responses, simultaneous impacts, the blood toggle and restoration of the original
skeleton blend mode. Earlier hand/drop/get-up, feeding, sleep/bed and menu-hand
regressions remain covered. Representative attack frames were inspected. Ten GPU
pixel checks separately verify transparent blood corners, visible body and alpha
fade (`python source/tests/check_feather_material.py --combat-blood`).
The local renderer fixture is `build/windows/build-held-display-probe.ps1`;
its final run is labelled `combat-ready`. It reports pre-existing missing
`Panels_Diffuse.png` bed-texture warnings, not failures in the new combat shaders.
These isolated checks do not establish final in-game choreography, weapon contact
timing or gameplay acceptance; those checks remain with the user.

The preceding implementation's checks, retained as historical evidence:

The source-path probe passes 19 checks covering combat-only animation selection,
speed changes, server/client notification flow, simultaneous weapon/body effects,
the blood setting, fallback death models and cleanup. The production particle
scripts pass 22 real Ogre resource and live-emission checks; their isolated spark
and blood render was visually inspected. The real Ogre creature lifecycle probe
passes 386 checks across all 33 distinct creature meshes, including rotating
attack variants and grounded Cultist/Lich death falls. The settings layout passes
the existing headless multi-resolution and UI-scale probe.

The Windows Release target compiles successfully, runtime preparation passes and
CTest has no registered tests.
The implementation agent did not launch the game, so final combat timing and
appearance still require the documented manual check.

The follow-up adds no protocol or version change; the combined fork remains at
0.7.2, introduced by the separate research-progression protocol update.
