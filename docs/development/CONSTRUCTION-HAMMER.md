# Construction hammer

## Left tool end as the cursor, September 20

The user clarifies that the visible left striking end itself must select the
tile for both hammer and pickaxe, not a future contact pose or the hand origin.
Screenshots at 08:44:06/19/29 show the misplaced selection. The current hammer
offset samples the midpoint of its swing, while the pickaxe has no tool-specific
pointer alignment at all. The preceding contact-only fix therefore does not
satisfy this clarified cursor requirement.

On `fix/tool-cursor-hotspots`, from complete checkpoint `3dc51836`, identify the
screen-left end from the existing rig/attachment, align that end in the ready
pose with the actual pointer, and preserve a constant offset during its strike.
Keep accepted angle/motion, world-ray selection, building and digging input
unchanged; verify both tool hotspots and projected pointer positions.

The actual rig measurement places positive local X to screen-left for both
tools (hammer axis X = -0.145042; pickaxe = -0.435126). The hammer now uses its
positive-X face centre and the pickaxe its authored positive-X blade tip.
The ready-pose offset stays fixed through both accepted strike animations.
All 4,020 real-asset checks pass, including both left ends, projected cursor
positions over three scales/six camera configurations/nine screen positions,
unchanged tool orientation and frame-by-frame strike equality. Release,
runtime preparation and 32 resource checks pass. The normal executable is
September 20 09:16:01 Europe/Warsaw, 4,872,704 bytes, SHA-256
`FA118F4310C661BBE1CC2E27794FD1D544D1E0972C3C9A1D043E47F03B716853`.
No game was launched; user retest remains pending. README now identifies the
left ready-pose end as the pointer; no version, input or packet change is needed.

## Selected-tile alignment after accepted movement, September 20

The user accepts the new hammer angle and stroke, but reports that the selected
tile is misplaced in screenshots `ODscreenshot_2026-09-20_080648_0.png` and
`ODscreenshot_2026-09-20_080651_1.png`. Preserve that accepted animation.
The mouse ray and overlay origin both use the GUI pointer; construction uses
the ray-selected tile. The hammer's fixed offset, however, is sampled at its
resting pose, so its striking face leaves the selection when the wrist swings.
The preceding checks explicitly accepted this gap at the impact frame.

Sample the fixed offset at the existing stroke's midpoint instead of rest,
without changing the bone animation, tool attachment, cursor ray, tile selection
or build validation. Extend the real-asset test to require pointer contact at
impact, the same offset at rest and throughout the stroke, and preserved
frame-by-frame equality with digging; include projected screen positions.

The impact assertion fails before the fix with a 0.052632-unit pointer offset
and passes afterwards with a 0.0000000021-unit residual. All 3,668 real-asset
checks pass, including unchanged digging-relative bone motion, a constant offset
throughout the stroke, no jump from the resting pose and projected contact across
three scales, six camera configurations and nine pointer positions.
Release compilation, runtime preparation and 32 resource checks pass; the normal
executable now contains the fix (September 20 08:30:00 Europe/Warsaw, 4,872,192
bytes, SHA-256 `D8EB7D35D25F54B44B102554652D3AD882164FFF12B75F918EDCBA0F9722C65E`).
No game was started; user verification of the selected field remains pending.
README already describes pointer-aligned construction; no version, input or
save/network change is required.

## Reuse the digging strike, September 20

The user rejected the custom swing and explicitly requires the same hand angle
and movement as wall digging, with only the tool replaced. Both static grips
already use the same wrist and finger transforms, but construction has a separate
0.28-second five-key swing instead of digging's three-key 4/30-second strike.
Animated pointer recentering also cancels the natural wrist arc and substitutes
a sideways translation. The hammer's independent head roll differs from the
pickaxe's accepted tool orientation.

Reuse the digging animation generator, retain only static resting-pointer
alignment during the entire stroke, and align the hammer with the pickaxe's
attachment after compensating for their different authored shaft axes.
Check actual hand transforms and tool axes against digging frame by frame,
including duration, fixed model offset and return to the resting pointer.
This supersedes both custom strike interpretations below; construction input
and all other hand actions remain unchanged.

The new attachment-angle assertion fails against the previous implementation.
After correction, 3,454 real-asset renderer checks pass, including all hand bone
positions/orientations across 17 stroke samples at 80/100/120 percent scale,
equal strike duration, tool-axis alignment, fixed pointer offset, visibility,
restart and return-to-rest behavior. The isolated impact preview was inspected.
The renderer test ran after one unchanged-binary retry following a transient
Windows execution-policy block; the separate construction-input fixture was
blocked before execution and is not claimed as freshly passed.

Release compilation passes. The staged executable is September 20 02:38:45,
4,872,192 bytes, SHA-256
`19A4241D70D4BFC9ABDC17A119D0D2B4BBEE2E7D89233B7E44012516594FE630`.
Deployment subsequently succeeded after the game closed: the normal executable
matches the staged hash, runtime preparation succeeds and 32 resource checks pass.
The user's September 20 02:38:53/56/58 screenshots were inspected: they show the
previous hammer orientation alongside the pickaxe reference and predate deployment.
At feedback intake the normal executable still had the rejected September 19 hash;
no further animation change was made before installing the already verified fix.
No game was launched or stopped.
Visual acceptance remains with the user. README already describes this same
short construction strike; no version, network/save or input change is needed.
This correction is local and has not been pushed to the existing hammer PR.

## Left-facing striking surface, September 19

The user rejected the forward-pitch result: the hammer must strike left with its
flat head surface, not move into depth against its side. The previous measured
impact normal (.235980, -.406880, -.882475) confirms that it did not face left.
The rest attachment normal is (.235980, .489505, -.839463); its shaft direction
is (.290404, .788860, .541632), reconstructed from the previously measured rig
bind rotations and the production attachment (also reproducing the measured
face normal). Rolling only the head 93 degrees around its own shaft makes the
face coplanar with the screen. A 20-degree leftward wrist strike then points the
flat face left, approximately (-1, .004, 0), without moving the shaft in the grip.

Replace the depth/vertical approach with a right-to-left head travel and retain
the exact pointer contact at impact, tool size, timing and all build input.
Verify both face direction and agreement with its incoming motion, rather than
testing a generic wrist rotation. This supersedes the preceding forward-pitch
interpretation below. Work remains on the construction branch from `4c5696ec`.
The actual hand/asset fixture passes 434 checks, including flat-face direction,
agreement with incoming leftward motion, unchanged shaft alignment and exact
pointer contact at 80/100/120 percent scale. The measured impact normal is
(-.999993, .00367308, -.00000669). Windup and impact renders were inspected.
Windows initially blocked the new diagnostic executable; the same unchanged
binary passed on retry without security-policy changes.

Release compilation and 32 normal-runtime resource checks pass. The staged
executable is September 19 21:21:00, 4,874,752 bytes, SHA-256
`0FACCAAE930C88DDE6F9C7662B850CAD74FC7AE05B383C7696A5E741630E1288`.
After the user closed the game, deployment and runtime preparation succeeded;
the normal executable matches the staged hash above. No game was launched or
stopped. User visual acceptance remains pending. README still describes the
same construction strike; no version,
save/network or input change is required.

## Strike-direction follow-up, September 19

The user reports a backward strike. The existing animation rotates around the
view's Z axis, rolling the hammer sideways rather than pitching it toward the
target. The actual mesh face normal at impact is (-.265626, .474071, -.839464):
its vertical component points upward while the scripted head travel goes down.
Pointer alignment also cancels all depth motion, leaving only a vertical bob.
The native measurement reproduces this; an initial Windows execution-policy
block was resolved by the explicitly approved retry, without policy changes.

On `feature/construction-hammer`, from full checkpoint `84a901e7`, correct only
the strike's axis/direction and its approach depth. Retain the grip, tool scale,
rest pose, exact impact pointer, timing and construction input. Add assertions
for the striking face's downward/forward direction and the head's approach
from the camera side; previous positional checks alone did not cover direction.
The new impact-direction assertion fails against the previous animation and
passes with the forward pitch. At impact the face normal is now
(.235980, -.406880, -.882475), directed down and into the view; the windup has
positive depth and returns to the exact pointer on impact. The production
renderer/asset fixture passes 418 checks at 80/100/120 percent scale, retaining
the accepted pickaxe and idle behavior. Settled windup/impact previews were
inspected; each frozen pose now renders twice so cached skinning and attachments
agree. Windows briefly blocked a newly compiled probe; the same unchanged
binary ran successfully on retry, without security-policy changes.

Release compilation, normal runtime preparation and 32 resource checks pass.
The normal executable matches the staged build: September 19 21:11:36,
4,874,752 bytes, SHA-256
`F210CC584F9C943946FB98E9A7148D0AA191E1B751712FAC0E921F16DED5AD3A`.
No game was launched; the user must retest this corrected strike direction.
README already describes the same construction strike; no release/version,
save/network or input change is needed.

## Screenshot follow-up: strike and pointer alignment

The September 19 19:21 captures show the hammer head outside the selected floor
tile. The overlay follows the mouse at its model origin, while pointer alignment
only handles the pointing finger; the hammer attachment is never aligned to
that origin. The construction validation paths also queue their requests without
triggering a hand animation. These are separate gaps in this same feature.

Extend the existing one-shot hand lifecycle with a closed-grip construction
strike and align the actual hammer striking face to the pointer, preserving
the mouse ray and all build coordinates. Trigger once after validated room/trap
input; previews, cancellation and invalid requests must not swing. Reuse the
existing grip and mesh, not the digging blade or a new input mode. Work remains
on `feature/construction-hammer`, from complete checkpoint `635c190b`.

The production renderer/asset fixture passes 278 assertions, including wrist
rotation, visible windup, exact pointer-axis alignment at rest and impact at
80/100/120 percent scale, tool exclusivity and repeated playback. The original
model-origin path reproduces the off-target head before alignment. The fixture
now advances Ogre's queued-frame counter so bone animation is actually sampled;
otherwise earlier isolated renders could reuse cached bones. Start, windup and
impact renders were inspected. This does not substitute for user gameplay QA.

The actual room/trap/door validators and construction dispatcher pass 560
checks: valid single/area requests swing once, while preview, empty/outside
selection, insufficient gold, invalid door placement and unrelated actions do
not swing. The unchanged release guards still suppress canceled/GUI releases.
The strike reports a locally eligible request, not a server success guarantee;
packet data, costs and action timing are unchanged.

Release compilation, normal runtime preparation and 32 resource checks pass;
the normal September 19 20:58:12 executable includes this correction and the
separate Alt toggle. The game was closed during deployment and was not launched
by the agent. User acceptance remains pending; see BUILDING.md for its hash.
README is updated; no version/save/network format change is needed.

## Existing path and scope

The accepted review follow-up requests a hammer while building and retains the
pickaxe while digging. Gameplay already distinguishes room/trap construction
from digging, selling and casting, but its hand update only selects pointing
or digging. The renderer already provides a closed tool grip, bone attachment,
visibility control and restoration after one-shot animations.

Extend those existing paths with a construction pose and the existing
`BasicHammer.mesh` and diffuse texture, credited to YD under CC0. Reuse the
closed grip without changing the digging wrist or pickaxe. Construction over
the map shows the hammer; GUI hover, paused gameplay and held objects retain
their existing precedence. Building validation, commands and costs are unchanged.
This task does not introduce a new construction strike or change pickaxe alignment.

Work branch: `feature/construction-hammer`, from the complete fork checkpoint
`bcb03af6` with all newer local navigation work preserved.

## Verification

The real Ogre fixture passes 121 checks covering construction input precedence,
room/trap selection, tool exclusivity, pickup/drop/slap interruptions, digging,
visibility and materials. Three rendered scales (80/100/120 percent) were
generated and the 100-percent preview inspected. The authored mesh has no vertex
colour stream, so it uses its own unlit diffuse material instead of inheriting
the procedural pickaxe's vertex-colour tracking; the head is visibly transverse
to the shaft and the closed fingers occlude the grip.

The clean staged Release build plus subsequent rebuild succeeds; while the game
was closed, its executable was copied into the normal runtime and runtime
preparation succeeded. The September 19 17:27:35 executable is 4,853,760 bytes,
SHA-256 `ABAFA35691BDCD04F6034F50F0A38C3977C34C6B6D38BD3987A531E2D7A12E62`.
It also retains the separate navigation correction. No game was launched.
User visual/gameplay acceptance remains pending. README and the development
index document the feature; no release, save or network version change is needed.
