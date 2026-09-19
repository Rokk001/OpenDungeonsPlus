# Construction hammer

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
Deployment is pending because the user's game is running; the normal executable
still has the preceding `F210CC58...` hash and rejected forward-pitch motion.
No game was launched or stopped. User visual acceptance remains pending after
deployment. README still describes the same construction strike; no version,
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
