# Painted skin sources

Original painted source art generated with the built-in image generation tool, 2026-10-24, using `docs/design/ingame-gui/vorschlag-A-hud-korrigiert.png` as the material reference. GPLv3+. The reference supplies the art direction, not game-scene pixels.

`frames.png` contains four frame families (HUD, window, inset, icon/button), each with four separately painted states. `frame-<family>-<state>.png` are the individual source tiles. Their independently chipped corners and four different edge crops supply the nine-slice pieces; opposing edges are not mirrored copies. `glyphs.png` and its separate `glyph-*.png` tiles supply symbols and orb/minimap rings. `controls.png` and `control-*.png` supply independently painted radio, tick and progress states. `stone.png` supplies the quiet HUD surface and mirrored centre assembly with matching opposite boundaries.

Rebuild from the repository root with `python scripts/gui/build_skin_atlas.py` (Pillow is required). The script extracts the committed source grids, assembles the 2048x2048 atlas, writes every named rectangle, and resizes the HUD Stone to 3548x1774. `slots.json` preserves the original 314 names, source dimensions and offsets; each original dimension becomes four source pixels. Additional state images are collected from the look file. No layout geometry is generated. The existing runtime scale path must account for skin density 4 and HUD density 2.

State suffixes `__Hover`, `__Pushed`, `__Disabled` reference the corresponding painted state column. `__Edge2` selects the second independently damaged stretch of an edge. The complete nine-slice roles are HudPlate, WindowFrame, InsetPanel, Button, TabButton, Checkbox, Combobox, EditBox, Listbox, ScrollbarTrack, ScrollbarThumb, ProgressBar, Tooltip and IconSlot. Each exposes TopLeft, TopRight, BottomLeft, BottomRight, Top, Bottom, Left, Right and Middle pieces, with both edge variants in every state. Normal image names and every public widget/property/child/named-area contract remain unchanged. Glyphs are cut from their painted sources; alpha is retained. The separate `OrbRing` and `MinimapRing` images are provided for the HUD navigation.

Exact generation prompts follow. Outputs were 1254x1254 even though a 2048 square was requested; atlas assembly resamples the source crops.

## Source 1: frames.png

```text
Use case: stylized-concept. Production raster source asset for OpenDungeonsPlus CEGUI skin, matching the black iron and quiet cracked stone material in reference image 1, not its game scene. Generate a square 2048x2048 sprite sheet, exactly four columns and four rows of equal 512x512 cells, no gutters, no captions, no text. Every cell is a complete square inset panel seen straight-on orthographic, same frame thickness 52px, with an opaque dark cracked stone centre and painted forged charcoal iron frame. Sparse rust in bevel crevices, restrained bone-grey highlights, shallow relief, no glow, no lava, no fire, no chains, no spikes, no ornamental clutter. Corners have different asymmetric chips and a few rivets; left and right edges visibly differ. The center must be subdued nearly seamless dark stone so it can be tiled in a UI. Four rows are frame families, four columns are their distinct physical states. Row 1: thick riveted HUD plates. Row 2: slightly thinner window frame with fractured rim. Row 3: fine inset stone frame. Row 4: small icon slot / button frame. Columns left to right: normal dark iron; hover with slightly brighter worn bronze bevel; pressed with sunken inner rim and darker recessed centre; disabled with visibly cold corroded desaturated dull frame. Keep each frame entirely within its own cell, every cell touches exact grid boundaries, no perspective, no labels or icons. Painted texture detail, intimidating ruined dungeon mood, quiet restrained variant A appearance. No foreign game names or brands.
```

## Source 2: stone.png

```text
Production raster texture asset for OpenDungeonsPlus GUI, seamless tile of broad dark cracked stone matching the restrained bottom stone slab of reference image 1. Entire square image filled edge to edge, flat orthographic diffuse material painting, no frame, no vignette, no perspective, no objects, no text. Very dark charcoal blue-black slate, large irregular fractured plates, shallow light grey chipped ridges and sparse faint rust-brown mineral seams. Low contrast and quiet enough behind text. No orange glow, no lava, no fire, no ornament, no noisy tiny pebbles. Opposite edges must tile seamlessly. 2048x2048.
```

## Source 3: glyphs.png

```text
Use case: stylized-concept. Raster sprite source sheet for OpenDungeonsPlus painted iron GUI, match black iron / muted bronze / bone ivory palette of reference 1. Exact square sheet with 4 columns and 4 rows equal cells, each isolated sprite centered in its cell, generous transparent space, no labels no text. Transparent background. Row1: bone-white tick mark, bone-white X close symbol, bronze plus sign, bronze minus sign. Row2: bronze triangular arrow up, bronze triangular arrow down, bronze triangular arrow left, bronze triangular arrow right. Row3: iron ring with bone-white central dot radio selected, empty iron ring radio off, orange segmented rectangular progress fill (no frame), dark rust brown rectangular selection strip. Row4: iron pointed arrow mouse cursor pointing upper left, bone-white capital I shaped text caret, small bronze four-direction move cursor, circular iron orb/minimap frame with transparent hole and irregular chipped rust rim. Painted tactile worn metal, legible simple silhouettes, quiet A style; no flames, no glowing trims, no busy spikes or ornament, no game brands. Orthographic flat sprites, do not include the reference scene.
```

## Source 4: controls.png

```text
Production sprite sheet, 4 columns by 4 rows equal cells, transparent background. Original painted OpenDungeonsPlus GUI in the quiet black iron, sparse rust and ivory material of reference 1. Every cell centered with transparent margins. Columns are physical states: normal charcoal iron with restrained bronze edges, hovered slightly brighter worn bronze bevel, pressed recessed darkened iron, disabled cold dull grey corroded metal. Rows top to bottom: 1 empty small round iron radio-button ring; 2 same radio ring with bone-white centre dot; 3 bone-white checkbox tick mark mounted on a tiny chipped dark iron shape (no full box); 4 a horizontal row of five orange-brown progress segments (no outer frame), disabled version unlit dull brown. The four columns must be individually painted visibly different states, not identical copies. No captions, no letters, no fire or lava, no luminous outline, no ornaments. Orthographic game UI sprites, transparent holes in rings. 2048x2048.
```
