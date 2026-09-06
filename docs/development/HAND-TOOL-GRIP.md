# Hand tool grip

Work branch: `fix/hand-tool-grip`, based on combined checkpoint `7d534b4e`,
preserving hand orientation `efa8fa5d`, picker counts `505cbf97` and parallel
room lighting `0c7d6234`; the shared checkout/index remain unchanged.

## Evidence and existing code path

The September 6 user capture at 19:46:47 shows the tool across the hand's back.
The existing tool is already attached to the palm bone, but its identity
rotation aligns the shaft along the hand instead of across the closed fingers;
its positive depth offset places it above the back of the hand. The sampled
closed-finger rig has its grasp channel around local Y 0.030 and Z -0.009,
with finger joints distributed along X. This is a placement failure, not a
missing attachment or a reason to replace the existing mesh or input path.

The hand's existing material also disables depth testing/writing and blends at
half opacity, so the tool remains visible through the fingers. The GUI render
queue already clears world depth before drawing the interface and hand.

## Targeted correction

Reuse the existing closed-finger pose, turn the shaft 90 degrees around local Z
at palm offset (0, 0.030, -0.009), and roll the digging wrist 120 degrees around
local Y so the head extends above the index/thumb side. Scale the attached tool
uniformly to 0.6 to fit the existing fist. Give only the digging pose an
opaque depth-tested hand material so the fingers obscure the enclosed shaft;
retain the original hand material for other poses and existing animations.
Use depth writing for the tool itself. Keep the same geometry, textures,
cursor position, hit testing, tool visibility rules and digging behavior.

The attachment values and wrist roll are fitted to this project's existing rig;
they are not recovered constants from a reference engine. Public task text uses
neutral terminology; detailed image comparisons remain in local planning notes.

## Verification

The isolated GL3Plus probe uses the actual rig, generated poses, attachment,
material scripts and animation setter. All 94 checks pass with shadows disabled
and enabled; the preceding implementation fails 14 of those checks. Coverage
includes the grasp channel, head direction, material restoration through repeated
Point/Pickup/Drop/Slap/Idle transitions, unchanged unrelated animated entities,
cursor coordinates, held-object placement and parent visibility.

Rendered hand-only, tool-only and combined layers verify mutual occlusion from
three camera angles: the corrected fingers hide 891 to 1,033 overlapping shaft
pixels while 397 to 508 exposed shaft pixels remain visible. All six current
shadow-on/off comparisons pass, while the three preceding views fail. The 11
non-digging before/after pose images are byte-identical. These checks prove the
rendered grip correction, not exact reference fidelity or game acceptance.

Logs are `build/windows/hand-grip-check-{before,current,shadows}.log` and
`hand-grip-image-results.log`; images are under `build/reference-audit/hand-grip-*`.
The initial full Release attempt in `hand-grip-release-build.log` encountered an
unrelated concurrent camera-navigation compilation error: a const GameMode
method calls a non-const connection query. This task does not overwrite or
alter that parallel work. The parallel task subsequently corrected its method;
the full Release rebuild and runtime preparation pass in
`hand-grip-release-rebuild.log` and `hand-grip-runtime.log`. The executable at
`build/windows/opendungeons-plus.exe` includes this correction and the current
parallel camera work; its final timestamp and hash are recorded in BUILDING.md.
The assistant did not launch the game; visual game acceptance belongs to the user.

The user's subsequent 20:06 crash report is not a successful game acceptance.
The dump and the later 20:08 executable reveal an incompatible virtual-call
layout: the event-notice caller uses slot 0x88, which the current game-mode
table assigns to chat reception; the event handler is at 0x90. A separate
Windows build correction must restore consistent objects before another test.

Version remains 0.7.1 because no release was requested. README controls are
unchanged, and no changelog exists; this note records the correction.
