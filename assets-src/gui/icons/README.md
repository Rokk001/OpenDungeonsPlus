# Painted HUD icon sources

Original source artwork generated with the built-in image generation tool on 2026-10-25. The seven sheets repaint the 99 existing icon slots in their original order; source PNGs and individual extracted tiles are committed. GPLv3+.

`slots.json` records the existing names and source rectangles. `motifs.json` records the existing functional motifs used for generation. Rebuild with `python scripts/gui/build_icon_atlas.py` from the repository root (Pillow required). The icon atlas is 2048 pixels wide and its height is derived from the registered rectangles; all original rectangles and offsets are doubled. Nineteen additional 256-square painted sources are registered through source paths in slots.json; their pixels are copied at full resolution and their source files are retained unchanged. Their exact prompts are in FEATURE-ICONS.md. The legacy tools/generate_forged_icons.py atlas command refuses to overwrite this painted atlas; its --sheet previews remain available. The additional 2048-square navigation atlas supplies the existing runtime-only names through the separate OpenDungeonsNavigation imageset. Source sheet 7 cells 4–10 contain heart, gold, help, sell, options, zoom and north. The quiet P1 iron ring and separately painted plate states are reused for the navigation surround; the medallion centres are composited inside that ring. Existing health and attack feedback is composited by the runtime rather than baked into a fixed icon.

The generator returned 1254x1254 sheets for the requested 2048 square. Source cells are resampled to the target rectangles during assembly. `overrides/MapLightButton.png` replaces the sheet's cropped lantern with a complete silhouette. `overrides/ManaBadge.png` supplies an isolated heart: the original sheet's fixed red ring is not read for the heart badge. The heart is placed inside the approved iron surround; the health-ring pixels come solely from the existing live runtime calculation. All seven sheet prompts and the two exact correction prompts follow.

## Correction sources

Both correction PNGs were generated with the built-in image generation tool, `transparent_background=true`, with actual output 1254x1254 RGBA. The internal model identifier was not exposed. The first reference was `vorschlag-A-hud-korrigiert.png`; the second was `icons-2.png` for the lantern and `icons-7.png` for the heart.

### overrides/MapLightButton.png

```text
Production raster sprite asset for OpenDungeonsPlus, a single freestanding painted ruined iron lantern, using reference image 1 for the quiet variant A black iron and restrained weathered material, and the lantern in row 1 column 3 of reference image 2 for its existing identity. Output ONE lantern only, centered on a transparent square, not a sprite sheet, not a scene. Show the COMPLETE top hanging loop, handle, roof, cage and bottom foot, with at least ten percent clear transparent space on every side, especially above the hanging loop. Keep the hanging loop fully closed and visibly uncut. Dark hand-forged chipped charcoal iron, a few worn muted bronze edges, asymmetric rust and rivets, hand-painted depth and weathering. A very small quiet warm candle light behind the iron cage; readable silhouette at small icon size. No surrounding glow, no lava, no flame plume, no sparks, no pedestal, no border, no panel, no labels or text, no branding. No clean symmetric decorative web icon look. The entire silhouette must fit inside the image.
```

### overrides/ManaBadge.png

```text
Production raster sprite asset for OpenDungeonsPlus, ONE freestanding red anatomical dungeon heart painted in the quiet dark ruined variant A material of reference image 1. Reference image 2 row 1 column 4 supplies the identity of its existing heart ONLY: remove and do not reproduce its surrounding ring or status segments. Output a single complete anatomical heart on transparent square background, centered with generous transparent margin around all vessels and its pointed lower tip. Deep crimson red flesh, clear anatomical chambers and curled major vessels at the top, restrained painted highlights and dark maroon creases, tactile detailed game icon painting, legible silhouette at small size. NO ring, NO frame, NO circular backing, NO status or life segments, NO radial marks, NO shield, NO cross, NO green background, NO glow, NO embers, NO fire, NO text, NO numbers, NO branding. Heart only, with all surrounding space genuinely transparent.
```

## icons-1.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: small isolated transparent symbol: single weathered gold coin.
Cell 2: small isolated transparent symbol: red territorial pennant on a stone plinth.
Cell 3: small isolated transparent symbol: blood red faceted mana crystal.
Cell 4: small isolated transparent symbol: worn iron cogwheel.
Cell 5: small isolated transparent symbol: menacing pale goblin head with pointed ears.
Cell 6: small isolated transparent symbol: bone ivory question mark.
Cell 7: small isolated transparent symbol: iron storage tablet with upward bronze arrow.
Cell 8: small isolated transparent symbol: iron storage tablet with downward bronze arrow.
Cell 9: small isolated transparent symbol: blood-red X, clearly red cancellation mark.
Cell 10: small isolated transparent symbol: bone ivory check mark.
Cell 11: small isolated transparent symbol: old rolled parchment scroll with blood red wax seal.
Cell 12: small isolated transparent symbol: glass flask containing a blood red swirling magical liquid.
Cell 13: small isolated transparent symbol: red pennant with bronze fastening.
Cell 14: small isolated transparent symbol: iron cogwheel.
Cell 15: small isolated transparent symbol: old bronze hourglass.
Cell 16: small isolated transparent symbol: blacksmith hammer and battered iron anvil.
```

## icons-2.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: small isolated transparent symbol: old brass camera with lens.
Cell 2: small isolated transparent symbol: bent bronze return arrow.
Cell 3: small isolated transparent symbol: iron hanging lantern with small amber flame.
Cell 4: small isolated transparent symbol: bronze triangular play arrow.
Cell 5: small isolated transparent symbol: painted gold ore surface swatch.
Cell 6: small isolated transparent symbol: painted lava surface swatch, only in this terrain icon.
Cell 7: small isolated transparent symbol: painted dark grey rock surface swatch.
Cell 8: small isolated transparent symbol: painted dark blue water surface swatch.
Cell 9: small isolated transparent symbol: painted brown dirt surface swatch.
Cell 10: small isolated transparent symbol: painted cracked grey flagstone surface swatch.
Cell 11: small isolated transparent symbol: painted clustered red crystal surface swatch.
Cell 12: large framed tile: rough straw bed with a filthy blanket and wooden bedposts.
Cell 13: large framed tile: straw training dummy and crossed iron swords.
Cell 14: large framed tile: iron anvil and blacksmith hammer, tiny working spark.
Cell 15: large framed tile: leather sack and stacked aged gold coins.
Cell 16: large framed tile: open ancient book with small bronze reading sigil.
```

## icons-3.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: large framed tile: large cracked pale egg streaked with blood resting in straw.
Cell 2: large framed tile: weathered stone tombstone with skull and crossed bones.
Cell 3: large framed tile: small grim stone altar with ritual chalice.
Cell 4: large framed tile: battered fortress gate tower and red guard pennant.
Cell 5: large framed tile: heavy demolition hammer striking a cracked stone block.
Cell 6: large framed tile: blacksmith workbench with iron anvil and hammer.
Cell 7: large framed tile: iron barred prison doorway.
Cell 8: large framed tile: wooden torture wheel with iron spikes.
Cell 9: large framed tile: crossed iron swords above a stone arena gate.
Cell 10: large framed tile: bone dice and worn playing cards.
Cell 11: large framed tile: ruined stone shrine with a small ritual brazier.
Cell 12: large framed tile: old stone portal ring with a restrained amber magical centre.
Cell 13: large framed tile: small rough wooden suspension bridge.
Cell 14: large framed tile: small cracked stone arch bridge.
Cell 15: large framed tile: heavy iron cannon on a wooden carriage.
Cell 16: large framed tile: iron spikes rising from a stone trap plate.
```

## icons-4.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: large framed tile: heavy cracked round stone boulder.
Cell 2: large framed tile: weathered bronze alarm bell.
Cell 3: large framed tile: menacing skull on a stone pedestal.
Cell 4: large framed tile: three muted sickly green vapour bubbles over an iron trap vent.
Cell 5: large framed tile: iron trap plate with small amber electrical arcs.
Cell 6: large framed tile: small burst of flame from an iron vent.
Cell 7: large framed tile: bone-white frost crystal over a metal plate.
Cell 8: large framed tile: battle-worn red warning pennant with bronze frame.
Cell 9: large framed tile: red-tipped mechanical lever on iron plate.
Cell 10: large framed tile: circular runed summoning gate with a red concentric centre.
Cell 11: large framed tile: arched heavy timber door with iron bands.
Cell 12: large framed tile: rough wooden arched door reinforced with broad black iron bands.
Cell 13: large framed tile: heavy riveted steel arched door.
Cell 14: large framed tile: rough timber barricade with iron spikes.
Cell 15: large framed tile: concealed stone arch door in cracked masonry.
Cell 16: large framed tile: heavy iron door with a small bronze runic sigil.
```

## icons-5.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: large framed tile: heavy hammer breaking an iron trap mechanism.
Cell 2: large framed tile: menacing horned goblin face within a sparse ritual circle.
Cell 3: large framed tile: torn red battle banner and crossed swords.
Cell 4: large framed tile: red anatomical heart with bone ivory healing cross.
Cell 5: large framed tile: short violent orange burst with stone fragments.
Cell 6: large framed tile: jagged golden lightning bolt.
Cell 7: large framed tile: cracked earth slabs with a red fissure.
Cell 8: large framed tile: single red eye with two bronze circular arrows.
Cell 9: large framed tile: grim skull above a small spiral of possession.
Cell 10: large framed tile: stacked aged gold coins with a small restrained magical glint.
Cell 11: large framed tile: compact painted flame, no glow beyond icon.
Cell 12: large framed tile: pale hen with red comb, grim painted natural animal.
Cell 13: large framed tile: golden lightning bolt with small speed strokes.
Cell 14: large framed tile: worn iron shield with bronze boss.
Cell 15: large framed tile: brown snail with large spiral shell.
Cell 16: large framed tile: clenched iron-gauntleted fist.
```

## icons-6.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: large framed tile: broken iron sword with falling fragments.
Cell 2: large framed tile: watchful orange-red eye with dark vertical pupil.
Cell 3: large framed tile: crossed broad iron swords.
Cell 4: large framed tile: crossed rough-handled iron pickaxes.
Cell 5: large framed tile: crossed broad iron swords.
Cell 6: large framed tile: stone arch doorway.
Cell 7: large framed tile: old twisted wand with small bronze star at tip.
Cell 8: large framed tile: faceless figure in a dark worn hood.
Cell 9: large framed tile: ruined stone arch doorway.
Cell 10: large framed tile: old twisted wand with small bronze star.
Cell 11: large framed tile: battered miner pickaxe.
Cell 12: large framed tile: two simple bronze chevrons, one pointing up and one pointing down.
Cell 13: large framed tile: watchful orange-red eye.
Cell 14: large framed tile: bone ivory lower-case i on a small black iron tablet, clearly i.
Cell 15: large framed tile: bone ivory lower-case i on a dull black iron tablet, clearly i.
Cell 16: large framed tile: worn bronze crown with red studs.
```

## icons-7.png

```text
Use case: stylized-concept. Production painted raster icon sheet for OpenDungeonsPlus, matching the quiet ruined black iron GUI in reference image 1 and the painted object icons in the other references. Exact 2048x2048 square with a strict 4 by 4 grid of equal 512x512 cells. No gutters, captions, names, numbers or extra cells. Each icon stays in its cell, centered with 10% safe margins. Painted tactile dark stone, tarnished iron, aged bone, sparse blood and bronze; legible bold silhouettes, realistic hand-painted object depth, NOT clean flat icons, not shiny toy renders, no global glowing trim, no background fire or lava, no other game names or brands. Small-symbol cells must have transparent backgrounds, no frame. Large tile cells have a quiet thin chipped black iron edge and dark cracked stone background as in reference 1, asymmetrical sparse damage, no bulky ornaments. Order is left to right, top to bottom. The grid boundaries must be exact.
Cell 1: large framed tile: red anatomical heart protected by a dark iron shield.
Cell 2: large framed tile: red anatomical heart with bone ivory healing cross.
Cell 3: large framed tile: single drop of amber magical liquid with short restrained radiating strokes.
Cell 4: isolated transparent sprite: a red anatomical dungeon heart medallion in a quiet weathered circular iron frame, dark annular gap for the live health ring.
Cell 5: isolated transparent sprite: a stack of gold coins medallion in a quiet weathered circular iron frame.
Cell 6: isolated transparent sprite: a bone ivory question mark.
Cell 7: isolated transparent sprite: a bronze selling emblem, gold coin and short return arrow.
Cell 8: isolated transparent sprite: a small iron gear for options.
Cell 9: isolated transparent sprite: a brass magnifying glass for map zoom.
Cell 10: isolated transparent sprite: a bone ivory capital N in a tiny dark circular bronze-rimmed compass marker.
Cell 11: completely empty transparent cell.
Cell 12: completely empty transparent cell.
Cell 13: completely empty transparent cell.
Cell 14: completely empty transparent cell.
Cell 15: completely empty transparent cell.
Cell 16: completely empty transparent cell.
```
