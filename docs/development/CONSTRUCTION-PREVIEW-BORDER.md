# Construction preview border

The September 20 13:51:43 screenshot shows a one-pixel purple floor outline.
`GameMode::updateSelectedTiles` sends valid/invalid construction tiles to
`RenderManager::rrDrawTilePreview`, which renders every edge as a hardware line.
Line thickness therefore stays one pixel, regardless of the selected tile size.

Use an inset triangle ribbon for construction floor previews, retaining the
existing tile boundary, purple/red validity colours and empty/cancel handling.
Digging wall boxes and non-construction outlines remain unchanged.
The ribbon is 0.06 tile units wide; it does not fill or enlarge the selected tile.

The production renderer geometry probe passes 333 checks, covering triangle
winding, six-percent inset width, open centres, bounds, valid/invalid colours,
multi-tile previews, unchanged wall boxes and cancellation; construction dispatch
checks also pass, as does the September 20 Release build.
Normal-executable deployment will follow the cumulative queue build;
manual game acceptance remains with the user.
This presentation correction does not change saves, protocol or release version;
the development index documents it, with no release changelog required.
