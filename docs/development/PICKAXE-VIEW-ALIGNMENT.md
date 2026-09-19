# Pickaxe view alignment

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
