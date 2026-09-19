# Construction hammer

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
