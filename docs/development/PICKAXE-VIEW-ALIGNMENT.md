# Pickaxe view alignment

## Screenshot correction, September 19

The 19:24:43 capture still shows a broad blade. Rechecking with the corrected
render fixture (which now advances Ogre's bone-cache frame counter) finds that
the previous visual audit could retain old bones and its angle labels were
relative to the already-rotated attachment. The repeat audit uses absolute shaft
angles and the actual gripping pose. At 45 degrees the blade-tip displacement
in view-aligned axes is (-.0839051, -.00850406, .0573727); at 55 degrees it is
(-.0739715, -.0191596, .0675659). The latter reduces horizontal span by about
12 percent and turns the blade farther into depth, with the intended upward-right
presentation. Change only that attachment roll; retain dimensions, shaft axis,
grip, hotspot, digging strike and the independently corrected hammer.

Branch: `fix/pickaxe-view-alignment`, from full checkpoint `aafcb4bd`.
This supersedes the earlier 45-degree visual conclusion below; exact reference
geometry is not claimed and user acceptance remains pending.

The corrected real-model fixture passes 280 checks, including hammer regressions;
the 55-degree preview was inspected. Release compilation and runtime preparation
pass, with 32 resource checks. The normal executable matches the staged build:
September 19 20:28:25, 4,859,904 bytes, SHA-256
`0756E281C9572A739478F2AEBEFB903E4C0795801CCEE7F834D1C2256FA40326`.
No game was launched; the screenshot follow-up is ready for user retesting.

The existing procedural tool is attached across the closed grip with no roll
around its shaft. Its blade therefore presents a broad downward-right silhouette.
Rotate only the tool around its local shaft, retaining its size, shaft position,
hand pose, hotspot, digging strike and the separate construction hammer.

The isolated actual-model preview compares shaft-axis rolls at 0, 30, 45, 60,
90, 120, -30 and -60 degrees. The 45-degree attachment turns the blade toward
the view, retains a readable head above the fist and reduces its projected span;
90 degrees hides most of the head. Private reference observations remain in
`docs/internal/`; this is an orientation correction, not a replacement asset.

Branch: `fix/pickaxe-view-alignment`, based on the complete `61d4404f` fork.
The real-model/controller fixture passes 124 checks, including unchanged shaft
axis and scale, blade depth alignment, tool switching and digging animation.
Release compilation and normal runtime preparation pass; generated resources
pass 32 checks. The normal executable is September 19 17:49:15, 4,854,272 bytes,
SHA-256 `404F344FB79BA27AEFB6FDA67CCFDA704E8B6671B93E96DA72E9BAAAAE421FE2`.
Rendered orientation candidates were inspected; gameplay acceptance remains
with the user. No game launch, packet/save change or release version bump was
needed; README already describes the unchanged hand/tool behavior.
