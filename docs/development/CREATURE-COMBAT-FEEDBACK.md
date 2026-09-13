# Creature combat feedback

## Immediate projectile launch visibility

The user accepts the improved fireball appearance but reports it first appearing
mid-flight. Server turn ordering updates animations and visibility before creature
upkeep; missiles created during upkeep are therefore first announced next turn,
after their initial flight has advanced. Reuse the launch tile's existing vision
list to announce a newly positioned missile immediately, before its first flight
path notification, without revealing it to seats outside that tile's visibility.
Use the caster's actual XY position instead of the tile center so the announced
origin matches the caster. Retain particle appearance, flight speed, damage,
collision and existing turn ordering; do not move the global visibility pass.

The extracted production launch/vision regression reproduces four failures and
passes all 17 checks after the correction, including launch-position packets,
creation-before-flight ordering, no duplicate creation in the next vision pass,
and no notifications to unseen/nonhuman seats. Existing projectile collision 75,
fireball rendering 180 and attack dispatch 19 checks also pass. The accepted
fireball appearance is unchanged. This is a same-protocol launch-order fix, not
a new effect, damage rule or version; no additional README feature is required.

## September 13 projectile and facing correction

The user rejects the current combat presentation: white-looking caster shots,
unreadable arrows and attackers facing away from opponents. The existing magic
effect uses many overlapping additive blue-white flares, not a fireball; replace
its presentation with a warm core and flame trail. Archers already select the
shipped arrow mesh, so inspect its rendered orientation and visibility rather
than replacing their skill or damage rules.

The movement update calls the queued attack animation when it reaches the final
waypoint, then overwrites that attack direction with the previous walking
direction. Fix the ordering at arrival and retain ordinary walking/end animations.
Attack facing also aims at the target tile center rather than the creature's
actual offset position; use the actual creature position while retaining tile
aiming for buildings. Keep attack range, costs, damage and cooldowns unchanged.
Work continues from the complete fork on `fix/combat-projectiles-and-facing`;
the unrelated bedroom passage task remains queued on its own branch.

The native arrow probe also reproduces four unreadable views out of eight:
the inherited material requests missing `Panels_Diffuse.png` in its first pass
before applying the bow texture. Use the arrow's existing bow texture in one
lit pass, without the unrelated inherited panel texture. This removes the missing
resource but does not fix the four failing views: the native thin shaft misses
pixels when axis-aligned (eight visible tip pixels versus 66 diagonal pixels).
Increase only the rendered cross-section threefold; retain the shipped mesh,
native -Y flight axis, length and gameplay collision path.

The fireball uses a procedurally shaded hot core and turbulent orange rim, with
shrinking, fading trail particles and alpha blending instead of additive white
overexposure. No new texture or dependency is required. Arrival facing passes
82 checks (eight failed before), attack dispatch/offset targets 19, and missile
collision 75. The actual arrow material/mesh passes eight directional GPU views
after the shaft adjustment; rendered previews show the retained shaft and tip.
The real-model renderer retains all 10,136 existing animation/lifecycle checks.
The fireball passes 180 GPU checks over 60 frames at the configured 4.2 tiles
per second, including a visible warm core and no white saturation; the rendered
preview was inspected. The normal executable is prepared for retesting as
recorded in [BUILDING.md](BUILDING.md).
Gameplay choreography and appearance still require the user's retest; tests do
not prove final live combat acceptance. No version or packet/save layout changes
are needed; the development index now names fireballs and readable arrows.

## Ranged-attack readability follow-up

The preceding attack dispatch always sent the melee combat animation, including
all six missile-using creature models. Classification now uses the selected skill's allowed
range, not the current target distance, so a point-blank shot remains ranged.
Use the model's authored casting clip where present, otherwise its authored
attack clip (including bow shooting), without the generated melee twist/lunge.
Preserve melee variants, recoil and impact effects. The existing meshless magic
missile uses intermittent, broad, pure-blue spray; replace that spray with a
continuous compact blue-white bolt and short trail in the same particle system.
Keep ranges, speeds, damage and save/packet layouts unchanged.

The dispatch probe passes 15 checks, including point-blank ranged attacks and
unchanged melee dispatch, costs and cooldowns. The hidden GPU projectile probe
passes 120 checks over 60 moving frames, with continuous emission and a visible
bright core at the current projectile position. Both committed probes require
the Windows development environment from the environment helper.
The real-model renderer passes 10,136 checks across all 33 models, including
native ranged clip selection for the six missile models and restoration of the
generated melee clips, plus the retained hand, feeding and sleep regressions.
Representative rendered poses were inspected. These checks do not establish
live-game readability or synchronize server damage with client interpolation;
the latter timing remains unchanged. Gameplay acceptance remains with the user.
No release version increment is needed: this completes the existing unmerged
combat feature without changing saved data or the packet layout.

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
