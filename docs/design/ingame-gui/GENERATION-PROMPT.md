Every future in-game screen (new windows, skill tree rework, new rooms, new creatures) is generated with this prompt, with the current in-game screenshot as background and the matching vorschlag-A image as style reference.

# Generation prompts — variant A

## Tool, provenance and output

- Date: 2026-10-24.
- Tool: built-in `image_gen.imagegen` (exposed in this session as `image_gen__imagegen`), with `referenced_image_paths` and `transparent_background: false`.
- Underlying image-model identifier: not exposed by the tool in this session; no model identifier is inferred.
- Each delivered PNG is 1920 × 1200. The tool did not always return that native size; the session used System.Drawing high-quality bicubic resampling to the requested delivery size. This document does not describe the delivery files as native-resolution generations.
- Inputs below are ordered exactly as supplied. Screenshot files came from the local OpenDungeonsPlus screenshot directory. Only file names are recorded, not machine-specific paths. Intermediate images are identified for provenance and are not approved additional references.
- Exact prompt text is retained in the fenced blocks, including the original concatenation between blocks. No prompt below is labelled reconstructed: the prompt strings and their composition were recovered from this session.
- The historical prompts are visual-generation records, not instructions to add controls or change game behaviour. The existing widget functions and layout geometry stay authoritative. In particular the existing information buttons keep their meaning and symbol, and creature details remain in Dungeonbook.

## Owner art direction (verbatim)

> düster, abschreckend, einschüchternd, Ruine mit asymmetrischen Schäden, gemalte Texturen (Eisen, Stein, Knochen, Blut, Glut), Tiefe und Verwitterung – nie sauber, glatt, symmetrisch, freundlich.

> Referenz für den Look: materials/textures/menu/bg16-9.png (Menübild).

> kein Web-/App-Look (keine flachen Panels, keine Glas-Effekte, keine Sans-Serif-Weboptik).

The subsequent owner corrections retained the painted dimensional icon direction and explicitly reduced frame clutter: no lava/fire treatment around the GUI, quiet broad dark material fields, damage at selected edges only, and no extra individual-creature information window in or above the bottom bar. The corrected HUD is the approved visual anchor.

## Shared base for the eighteen additional views (verbatim)

For those views, the exact submitted string is the following base immediately followed by the per-image addition, with no inserted separator. The full submitted string is also reproduced in each image record below.

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.
```

## Image records

### vorschlag-A-hud-korrigiert.png

Inputs, in order:

1. intermediate `exec-2ec4c0a8-4c5c-4941-8201-e56d5e6b491e.png` (same A HUD before removal of the extra creature window)
2. ODscreenshot_2026-10-23_174522_5.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Complete submitted prompt (verbatim):

```text
Precisely edit IMAGE 1 at 1920x1200. Owner approved its entire material, icon and frame design. CHANGE ONLY ONE THING: completely remove the floating Goblin creature-information window in upper right, restoring the actual underlying world from image2 in its place. No replacement panel. NO single-creature health, level, nameplate or individual info anywhere in HUD. Creature details exist exclusively inside Dungeonbook, which is closed in this screenshot. Keep all existing main HUD frames, new painted icons, resource counters, room tiles, minimap and overview counts exactly as image1. Preserve every other part of image1. Do not add anything. Final full game screenshot no montage.
```

### vorschlag-A-dungeonbook-final.png

Inputs, in order:

1. ODscreenshot_2026-10-22_213043_3.png
2. intermediate `exec-bb06fc6f-1a55-4b4d-a4b2-6498549d315a.png` (quiet A HUD before the later creature-window removal)

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Complete submitted prompt (verbatim):

```text
Use case: compositing. Finished full-screen in-game GUI concept, PNG EXACTLY 1920x1200 pixels, landscape 16:10. IMAGE 1 IS THE MANDATORY EDIT TARGET: preserve its actual rendered 3D background, camera, geometry, creatures and floor tiles in their exact positions. Replace interface artwork only. Other images are style/reference inputs only, NEVER use their background. All visible interface is richly hand-painted, oppressive, intimidating ruined dark fantasy: deeply weathered tactile surfaces, asymmetric missing chunks, irregular cracks and heavy depth. NOT neat, smooth, symmetrical decoration, friendly, flat panels, glass, website, app, modern sans-serif or pixel bitmap text. Readable antialiased serif lettering, pale ivory with restrained hierarchy. Preserve source controls/content. No extra gameplay features, invented product names, external game names, logos or watermarks. No presentation board, no inset screenshots, no titles outside UI. STYLE A REVISED: quiet oppressive matte blackened iron and charcoal basalt. Simple broad heavy forged borders with a few asymmetrically broken edges, sparse large rivets, soot and old scratches. NO lava, NO flames, NO glowing cracks, NO ember outlines, NO decorative skulls, NO spikes, NO banners, NO chains. Restrained steel gray edge light. Large calm dark textured surfaces; distress concentrated at a few corners, never everywhere. Clear visual hierarchy, minimal visual noise. Deep relief and painterly material, never flat website panel.DUNGEONBOOK SCREEN: Keep EXACT source background from image1, including its top mana 82787, +488 / -35 and gold 6551, its different dungeon rooms and bottom minimap. Restyle large centered Dungeonbook window fitting screen, title and close cross, left creature list headed Creatures (23) and Show all creatures, right Feed and Profile tabs and Posts of: everyone. Preserve source names/messages and list/feed proportions. Clear selected row, scroll affordance, readable text, physical weathered separators. Surrounding true source dungeon and HUD visible. Image2 is variant style reference only. CRITICAL ICON REDESIGN: EVERY SINGLE visible interface icon MUST be completely newly hand-painted, not reused/recoloured old artwork. Source icons are semantic inventory ONLY. Replace golden stick-man with sinister hooded creature bust, house with ruined stone doorway, sparkling wand with twisted scorched staff, pick with battered iron pickaxe, orange smiling head with snarling goblin relief; objective scroll with torn bloodsealed parchment, skill flask with cracked alchemical vessel, production anvil with scarred forge, info circles with chipped stone runic plaques, eye with realistically painted lidless ominous eye, camera with engraved lens relic, disk symbols with carved save/load tablets, help with weathered question rune, settings with broken iron cog, minimap zoom with rough optical lens, arrows with chipped blades, gold badge with weathered stacked coins, mana with pulsating dark anatomical heart. Room symbols: ruined straw pallet (no ZZZ), menacing hatching egg/claw (no cartoon chick), stained grimoire (no smiling book), scarred training dummy and crossed iron swords (no colourful target). No shiny gold flat pictograms, no orange cartoon goblin heads, no floppy disks, no generic lowercase i symbols, no bright yellow stick-men, no repeated old symbols. Material and palette match this variant throughout. Preserve the exact functions, positions, counts and source text. LATEST OWNER CORRECTION: all GUI must be calm and visually restrained. No fire, lava, glowing edges or pervasive decoration. Distinguish shapes and material using large painterly forms and sparse wear. Background world lighting remains unchanged. ALL navigation icons must visibly be newly painted full-material miniatures; zero old gold pictograms or cartoon symbols, INCLUDING repeated information buttons (replace with carved stone question-rune plaques), help, zoom, arrows, row action icons. Navigation icons are focal points and must read at small size.Match image2's restrained frame and icon language exactly.
```

### vorschlag-A-optionen-final.png

Inputs, in order:

1. ODscreenshot_2026-10-22_213041_2.png
2. intermediate `exec-2ec4c0a8-4c5c-4941-8201-e56d5e6b491e.png` (quiet A HUD before the later creature-window removal)

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Complete submitted prompt (verbatim):

```text
Use case: compositing. Finished full-screen in-game GUI concept, PNG EXACTLY 1920x1200 pixels, landscape 16:10. IMAGE 1 IS THE MANDATORY EDIT TARGET: preserve its actual rendered 3D background, camera, geometry, creatures and floor tiles in their exact positions. Replace interface artwork only. Other images are style/reference inputs only, NEVER use their background. All visible interface is richly hand-painted, oppressive, intimidating ruined dark fantasy: deeply weathered tactile surfaces, asymmetric missing chunks, irregular cracks and heavy depth. NOT neat, smooth, symmetrical decoration, friendly, flat panels, glass, website, app, modern sans-serif or pixel bitmap text. Readable antialiased serif lettering, pale ivory with restrained hierarchy. Preserve source controls/content. No extra gameplay features, invented product names, external game names, logos or watermarks. No presentation board, no inset screenshots, no titles outside UI. STYLE A REVISED: quiet oppressive matte blackened iron and charcoal basalt. Simple broad heavy forged borders with a few asymmetrically broken edges, sparse large rivets, soot and old scratches. NO lava, NO flames, NO glowing cracks, NO ember outlines, NO decorative skulls, NO spikes, NO banners, NO chains. Restrained steel gray edge light. Large calm dark textured surfaces; distress concentrated at a few corners, never everywhere. Clear visual hierarchy, minimal visual noise. Deep relief and painterly material, never flat website panel.OPTIONS SCREEN: Keep EXACT target image1 dungeon background, top mana 82140, +488 / -35, gold 6560 and bottom minimap. Restyle full HUD and tall centered Options window fitting screen. Exact option order and wording: Objectives; Skill; Save Game; Load Game (F8); Settings; End Game; Help; Player information; Define user cameras; Production; Continue Game. Close cross. All eleven rows readable and separated, deep tactile buttons, serious painted icons. Image2 is variant style reference only. CRITICAL ICON REDESIGN: EVERY SINGLE visible interface icon MUST be completely newly hand-painted, not reused/recoloured old artwork. Source icons are semantic inventory ONLY. Replace golden stick-man with sinister hooded creature bust, house with ruined stone doorway, sparkling wand with twisted scorched staff, pick with battered iron pickaxe, orange smiling head with snarling goblin relief; objective scroll with torn bloodsealed parchment, skill flask with cracked alchemical vessel, production anvil with scarred forge, info circles with chipped stone runic plaques, eye with realistically painted lidless ominous eye, camera with engraved lens relic, disk symbols with carved save/load tablets, help with weathered question rune, settings with broken iron cog, minimap zoom with rough optical lens, arrows with chipped blades, gold badge with weathered stacked coins, mana with pulsating dark anatomical heart. Room symbols: ruined straw pallet (no ZZZ), menacing hatching egg/claw (no cartoon chick), stained grimoire (no smiling book), scarred training dummy and crossed iron swords (no colourful target). No shiny gold flat pictograms, no orange cartoon goblin heads, no floppy disks, no generic lowercase i symbols, no bright yellow stick-men, no repeated old symbols. Material and palette match this variant throughout. Preserve the exact functions, positions, counts and source text. LATEST OWNER CORRECTION: all GUI must be calm and visually restrained. No fire, lava, glowing edges or pervasive decoration. Distinguish shapes and material using large painterly forms and sparse wear. Background world lighting remains unchanged. ALL navigation icons must visibly be newly painted full-material miniatures; zero old gold pictograms or cartoon symbols, INCLUDING repeated information buttons (replace with carved stone question-rune plaques), help, zoom, arrows, row action icons. Navigation icons are focal points and must read at small size.Match image2 style. Navigation icons MUST ALL be newly painted: no old icons, no floppy disks. No individual creature stats in bottom bar.
```

### vorschlag-A-forschungsbaum.png

Inputs, in order:

1. ODscreenshot_2026-10-22_213046_4.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Restyle the large Skill Tree window. KEEP all three columns, EVERY existing node at its source position, EVERY prerequisite connector and AND junction exactly as image1, all 0/3 and 1/3 labels, disabled marks, current orange active connector as muted aged brass rather than glow. All research node icons newly painted physical room/trap/spell miniatures matching their original meanings. Existing title, close cross, Auto Fill, Unselect All, bottom cancel and confirm. No new research nodes, do not omit nodes, no new mechanics. Calm near-black column interiors and sparse chipped iron window border.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Restyle the large Skill Tree window. KEEP all three columns, EVERY existing node at its source position, EVERY prerequisite connector and AND junction exactly as image1, all 0/3 and 1/3 labels, disabled marks, current orange active connector as muted aged brass rather than glow. All research node icons newly painted physical room/trap/spell miniatures matching their original meanings. Existing title, close cross, Auto Fill, Unselect All, bottom cancel and confirm. No new research nodes, do not omit nodes, no new mechanics. Calm near-black column interiors and sparse chipped iron window border.
```

### vorschlag-A-dungeonbook-profil.png

Inputs, in order:

1. ODscreenshot_2026-10-07_184425_0.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Restyle Dungeonbook with PROFILE tab active. Preserve screenshot's left list of 5 creatures and right social profile, portrait of Squib Scrapheap and all actual displayed fields, Health and XP bars, status, likes/dislikes, relationships and Recent posts. It is an in-world social-profile page; portrait and name establish visual hierarchy, text stays in same layout. Use the SOURCE PORTRAIT, no new person or creature identity. No new profile functions or icons not in source. No standalone creature window anywhere. Portrait and all creature health/level details only inside Dungeonbook.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Restyle Dungeonbook with PROFILE tab active. Preserve screenshot's left list of 5 creatures and right social profile, portrait of Squib Scrapheap and all actual displayed fields, Health and XP bars, status, likes/dislikes, relationships and Recent posts. It is an in-world social-profile page; portrait and name establish visual hierarchy, text stays in same layout. Use the SOURCE PORTRAIT, no new person or creature identity. No new profile functions or icons not in source. No standalone creature window anywhere. Portrait and all creature health/level details only inside Dungeonbook.
```

### vorschlag-A-ziele.png

Inputs, in order:

1. ODscreenshot_2026-10-18_094010_9.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Restyle Goals window and behind it HUD/event panel. Preserve EXACT source checklist wording and sequence, heading Victory!, six checked boxes and one unchecked box in its actual row: Defeat the watch post in the village yard. Do not change achievement states or add goals. Newly painted carved checkboxes with muted moss-green completed marks. Calm near-black slate writing area, clear ivory typography, slightly larger heading, close cross. No large ornament.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Restyle Goals window and behind it HUD/event panel. Preserve EXACT source checklist wording and sequence, heading Victory!, six checked boxes and one unchecked box in its actual row: Defeat the watch post in the village yard. Do not change achievement states or add goals. Newly painted carved checkboxes with muted moss-green completed marks. Calm near-black slate writing area, clear ivory typography, slightly larger heading, close cross. No large ornament.
```

### vorschlag-A-ereignismeldung.png

Inputs, in order:

1. ODscreenshot_2026-10-18_093839_8.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Restyle the wide low event popup above the bottom action rail. EXACT source message Goblin9 has been killed, small newly painted goblin event icon, original cancel cross and confirm check, tooltip Close message, selected event rail item. Keep popup location, approximate dimensions and empty content area as source; no extra text or mechanics. Other HUD stays visible, dark quiet iron border, muted ochre event text, rest newly painted nav icons.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Restyle the wide low event popup above the bottom action rail. EXACT source message Goblin9 has been killed, small newly painted goblin event icon, original cancel cross and confirm check, tooltip Close message, selected event rail item. Keep popup location, approximate dimensions and empty content area as source; no extra text or mechanics. Other HUD stays visible, dark quiet iron border, muted ochre event text, rest newly painted nav icons.
```

### vorschlag-A-kreaturenuebersicht.png

Inputs, in order:

1. ODscreenshot_2026-10-23_174931_6.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Show CREATURES tab active. Preserve bottom aggregate status counts 15,0,0,0, one goblin SPECIES portrait with COUNT 2 (this means total two goblins, NOT level), worker total15 and fighter total2 on right. Group overview only; absolutely NO health, XP, levels or individual creature nameplate anywhere. Preserve top Wall. Click or drag to mark for digging. hint. Replace all nav/status/event buttons with new painted icons and quiet A frames. Source minimap/world view exact. Do NOT replace creature aggregate panel with room tiles.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Show CREATURES tab active. Preserve bottom aggregate status counts 15,0,0,0, one goblin SPECIES portrait with COUNT 2 (this means total two goblins, NOT level), worker total15 and fighter total2 on right. Group overview only; absolutely NO health, XP, levels or individual creature nameplate anywhere. Preserve top Wall. Click or drag to mark for digging. hint. Replace all nav/status/event buttons with new painted icons and quiet A frames. Source minimap/world view exact. Do NOT replace creature aggregate panel with room tiles.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

### vorschlag-A-bauen.png

Inputs, in order:

1. ODscreenshot_2026-10-18_003444_2.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Show ROOMS tab active, original two available room tiles (dormitory and hatchery), dormitory selected, exact upper hint Build Dormitory room [1472 gold], source cursor-adjacent cost $1472 in red and size 4x4 label, rectangular source world selection unchanged. Replace dormitory cartoon bed/ZZZ with newly painted ragged straw pallet and hatchery cartoon chick with cracked egg gripped by claws, in dark A style. Restyle cursor-adjacent tile and size/cost labels as quiet worn iron/slate; retain actual selection geometry, values and world as source. No creature info windows.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Show ROOMS tab active, original two available room tiles (dormitory and hatchery), dormitory selected, exact upper hint Build Dormitory room [1472 gold], source cursor-adjacent cost $1472 in red and size 4x4 label, rectangular source world selection unchanged. Replace dormitory cartoon bed/ZZZ with newly painted ragged straw pallet and hatchery cartoon chick with cracked egg gripped by claws, in dark A style. Restyle cursor-adjacent tile and size/cost labels as quiet worn iron/slate; retain actual selection geometry, values and world as source. No creature info windows.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

### vorschlag-A-grabauswahl.png

Inputs, in order:

1. ODscreenshot_2026-10-23_174057_3.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Show original drag-to-dig selection scene with its rectangular blue-violet outline and pick-holding cursor unchanged. Preserve top hint exactly Release to mark selected walls for digging. and cursor size label 5x5 in quiet dark slate tooltip, all source values and minimap. Rooms tab displays four room miniatures (ragged straw pallet, cracked egg/claws, stained open grimoire, scarred training dummy with crossed swords), replace all old cartoon room icons. New material painted icons and calm A frames, no creature stat panel.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Show original drag-to-dig selection scene with its rectangular blue-violet outline and pick-holding cursor unchanged. Preserve top hint exactly Release to mark selected walls for digging. and cursor size label 5x5 in quiet dark slate tooltip, all source values and minimap. Rooms tab displays four room miniatures (ragged straw pallet, cracked egg/claws, stained open grimoire, scarred training dummy with crossed swords), replace all old cartoon room icons. New material painted icons and calm A frames, no creature stat panel.CRITICAL: replicate image2's NEW hand-painted icons, not image1's old cartoon or gold glyph artwork. No orange cartoon head anywhere in HUD, no gold flat human silhouette.
```

### vorschlag-A-zauber.png

Inputs, in order:

1. ODscreenshot_2026-10-01_084758_3.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
SPELLS tab selected. Preserve exact five bottom spell buttons and their meanings/order: summon worker, call to war, heal, creature explosion, lightning. Paint NEW tactile miniatures: snarling goblin summoning effigy, tattered red war standard with swords, anatomical heart bound by restorative metal clasp, contained violent burst, jagged lightning struck iron. No old smiling orange face, no glossy emoji heart, no flat yellow lightning. Keep real screenshot's entire world, resource values, minimap and rail. No extra spells or invented windows.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.SPELLS tab selected. Preserve exact five bottom spell buttons and their meanings/order: summon worker, call to war, heal, creature explosion, lightning. Paint NEW tactile miniatures: snarling goblin summoning effigy, tattered red war standard with swords, anatomical heart bound by restorative metal clasp, contained violent burst, jagged lightning struck iron. No old smiling orange face, no glossy emoji heart, no flat yellow lightning. Keep real screenshot's entire world, resource values, minimap and rail. No extra spells or invented windows.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

### vorschlag-A-fallen.png

Inputs, in order:

1. ODscreenshot_2026-09-26_115422_1.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
TRAPS tab selected. Source has ONLY ONE unlocked cannon tile bottom-left of content area; retain that exact inventory, no adding locked trap tiles or extra features. Replace flat cartoon blue cannon with serious hand-painted battered iron cannon with rough wood carriage. Restyle all old nav/minimap icons and dark HUD in approved A. Real world and resource values unchanged.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.TRAPS tab selected. Source has ONLY ONE unlocked cannon tile bottom-left of content area; retain that exact inventory, no adding locked trap tiles or extra features. Replace flat cartoon blue cannon with serious hand-painted battered iron cannon with rough wood carriage. Restyle all old nav/minimap icons and dark HUD in approved A. Real world and resource values unchanged.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

### vorschlag-A-produktion.png

Inputs, in order:

1. ODscreenshot_2026-09-26_115426_4.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Trap production window: same title, No workshops with empty first list, No pending trap orders with empty second list, disabled Move up and Move down buttons, exact explanatory text at bottom, Close button. Preserve empty state; do NOT invent workshops, progress bars or orders. Replace ornate silver UI with calm heavy dark A frames, new nav icons. Underlying active rooms tab shows actual same four source buttons newly painted equivalents.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Trap production window: same title, No workshops with empty first list, No pending trap orders with empty second list, disabled Move up and Move down buttons, exact explanatory text at bottom, Close button. Preserve empty state; do NOT invent workshops, progress bars or orders. Replace ornate silver UI with calm heavy dark A frames, new nav icons. Underlying active rooms tab shows actual same four source buttons newly painted equivalents.CRITICAL: copy the style reference's NEW miniatures, never old source pictograms. All icons newly painted, no old flat UI glyph artwork. Exact 1920x1200.
```

### vorschlag-A-spielerinformationen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_154004_9.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Player settings window: preserve Seat / Nickname / Team columns, exact two players and team values, checked KO enemy creatures instead of killing, resource counters 545 and 15/15, cancel/apply and close buttons. Keep player row colours semantically red/green but improve reading on charcoal background using muted light versions. Paint all icons new in A language. Do not add players or settings. No single creature windows.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Player settings window: preserve Seat / Nickname / Team columns, exact two players and team values, checked KO enemy creatures instead of killing, resource counters 545 and 15/15, cancel/apply and close buttons. Keep player row colours semantically red/green but improve reading on charcoal background using muted light versions. Paint all icons new in A language. Do not add players or settings. No single creature windows.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

### vorschlag-A-sandbox.png

Inputs, in order:

1. ODscreenshot_2026-10-04_100750_3.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Sandbox side window: preserve Score 124, Next room: The Guard Room in 0, Hero toolbox list with EXACT source creature names, Hero level: 1 button, Take hero, Hero invasion, Single invasion and Continual invasion. Source top score/room text must remain readable and non-overlapping, fit within top band using existing area; no additional labels. Exact scene and source control structure; only visual styling/typography changes. Dark quiet A framing, all icons newly painted, no standalone creature info window.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Sandbox side window: preserve Score 124, Next room: The Guard Room in 0, Hero toolbox list with EXACT source creature names, Hero level: 1 button, Take hero, Hero invasion, Single invasion and Continual invasion. Source top score/room text must remain readable and non-overlapping, fit within top band using existing area; no additional labels. Exact scene and source control structure; only visual styling/typography changes. Dark quiet A framing, all icons newly painted, no standalone creature info window.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

### vorschlag-A-einstellungen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_172654_0.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Settings navigation page Game Options. Preserve its two-column, three-row arrangement: Graphics Options; Sound Options; Control Options; Define User Cameras; Game Settings; footer Continue Game and Back. Turn the existing dark page area into a quiet opaque painted charcoal stone/iron backing with heavy restrained edging in A style, enough material depth without glass. Keep exact controls and positions, don't add fields. HUD surrounds newly painted. Original source background unchanged.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Settings navigation page Game Options. Preserve its two-column, three-row arrangement: Graphics Options; Sound Options; Control Options; Define User Cameras; Game Settings; footer Continue Game and Back. Turn the existing dark page area into a quiet opaque painted charcoal stone/iron backing with heavy restrained edging in A style, enough material depth without glass. Keep exact controls and positions, don't add fields. HUD surrounds newly painted. Original source background unchanged.CRITICAL: use image2 NEW painted nav icons, never image1 old bitmap symbols. All new dark painterly icons and physical frames. 1920x1200.
```

### vorschlag-A-grafikeinstellungen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_160959_0.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Graphics Options page. Retain Video/Audio/Input/Game tabs with Video selected. Preserve Resolution 1920 x 1200, checked Fullscreen and Dynamic Shadows, Renderer selector with exact source value, unchecked VSync, UI Scale 110%, vertical scrollbar, cancel and apply. Source page dimensions/positions and same controls, no new settings. Replace transparent unframed source area with solid hand-painted A charcoal stone page, quiet iron etched labels and physical dropdowns/checkboxes. Do not change source world or settings values. Text readable serif.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Graphics Options page. Retain Video/Audio/Input/Game tabs with Video selected. Preserve Resolution 1920 x 1200, checked Fullscreen and Dynamic Shadows, Renderer selector with exact source value, unchecked VSync, UI Scale 110%, vertical scrollbar, cancel and apply. Source page dimensions/positions and same controls, no new settings. Replace transparent unframed source area with solid hand-painted A charcoal stone page, quiet iron etched labels and physical dropdowns/checkboxes. Do not change source world or settings values. Text readable serif.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

### vorschlag-A-toneinstellungen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_164112_2.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Sound Options page with Video/Audio/Input/Game tabs, Audio selected, Music: 60% and the single existing horizontal volume slider, cancel/apply. Preserve sparse empty layout, no additional sliders or sound settings. Painted A solid charcoal page, iron channel and tactile worn metal slider thumb, readable restrained serif text. All HUD nav icons new painted miniatures. Source world unchanged.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Sound Options page with Video/Audio/Input/Game tabs, Audio selected, Music: 60% and the single existing horizontal volume slider, cancel/apply. Preserve sparse empty layout, no additional sliders or sound settings. Painted A solid charcoal page, iron channel and tactile worn metal slider thumb, readable restrained serif text. All HUD nav icons new painted miniatures. Source world unchanged.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

### vorschlag-A-steuerungseinstellungen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_162029_1.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Control Options page with Video/Audio/Input/Game tabs, Input selected; checked Keyboard grab, Mouse grab, Autoscroll; Camera pan speed 100% slider and cancel/apply. Preserve all settings values and original control positions and no new fields. Painted solid quiet charcoal stone/iron page matching A, tactile metal checks and slider, readable serif type. Source world and overview unchanged.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Control Options page with Video/Audio/Input/Game tabs, Input selected; checked Keyboard grab, Mouse grab, Autoscroll; Camera pan speed 100% slider and cancel/apply. Preserve all settings values and original control positions and no new fields. Painted solid quiet charcoal stone/iron page matching A, tactile metal checks and slider, readable serif type. Source world and overview unchanged.STYLE CONSISTENCY: solid opaque dark painted stone page with restrained worn iron border; all serif lettering clear. The SOURCE actual 3D game scene must remain visible around the menu. Full 1920x1200 screenshot.
```

### vorschlag-A-spieleinstellungen.png

Inputs, in order:

1. ODscreenshot_2026-09-07_164113_3.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Game Options page with Video/Audio/Input/Game tabs, Game selected; Nickname rokk, Keeper Voice Default, Minimap Type with source selected value, Ambient Light +100% slider, cancel/apply. Preserve exact existing settings and control positions. Quiet solid painted charcoal/iron page matching A, tactile weathered dropdowns, inset text field, physical slider thumb. No new toggles or gameplay rules. Actual source background unchanged.Match approved A exactly in calm material treatment and newly painted icons. Opaque stone/iron surfaces, no transparent glass. Full 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Game Options page with Video/Audio/Input/Game tabs, Game selected; Nickname rokk, Keeper Voice Default, Minimap Type with source selected value, Ambient Light +100% slider, cancel/apply. Preserve exact existing settings and control positions. Quiet solid painted charcoal/iron page matching A, tactile weathered dropdowns, inset text field, physical slider thumb. No new toggles or gameplay rules. Actual source background unchanged.Match approved A exactly in calm material treatment and newly painted icons. Opaque stone/iron surfaces, no transparent glass. Full 1920x1200.
```

### vorschlag-A-neustart-bestaetigung.png

Inputs, in order:

1. ODscreenshot_2026-10-02_075140_0.png
2. vorschlag-A-hud-korrigiert.png

Delivery: 1920 × 1200 PNG. Tool: built-in `image_gen.imagegen`. Prompt fidelity: verbatim session text.

Per-image addition (verbatim; concatenated directly to the shared base):

```text
Restyle actual layered End Game menu and front confirmation dialog. Front title exactly Do you really want to restart this level?; Yes and No buttons, unchecked Save the game replay? checkbox, close cross. Behind it preserve Quit to Menu, Exit to System, Restart Level, Back, Continue Game. Keep same source scene, controls, layering and values. Opaque painted charcoal surfaces with quiet worn iron frames and sparse chips, NEW icons; no glass, no extra confirmations or actions.Match approved A exactly in calm material treatment and newly painted icons. Opaque stone/iron surfaces, no transparent glass. Full 1920x1200.
```

Complete submitted prompt (verbatim):

```text
Use case: compositing. Produce ONE finished full-screen 1920x1200 game GUI concept. Image1 is the MANDATORY actual screenshot edit target: preserve its real rendered 3D scene, camera, room geometry, objects, cursor and game state. Image2 is the OWNER-APPROVED VARIANT A style ONLY, never use its world background. Restyle ALL interface to match image2 exactly: matte blackened iron, worn charcoal basalt, cool gray soft bevel highlights, broad calm dark textured fields, very sparse asymmetrically chipped corners and a few aged rivets. NO lava glow, NO flames in UI, NO spikes, NO ornamental skulls/chains/banners, NO busy tiny decoration. Ominous and intimidating through weight and weathering. Painterly tactile dimensional materials, no flat app/web panels, no glass, no sans-serif or bitmap typography. Readable smooth ivory serif text. All existing UI icons must be newly hand-painted serious miniature objects in the approved A language, including nav tabs/room tiles/actions/scrollbars/buttons, not merely coloured old icons. Creature tab hooded bust, room tab ruined doorway, spells twisted staff, traps battered pick, objective bloodsealed parchment, skill alchemical flask, production scarred anvil, Dungeonbook snarling goblin relief, minimap controls weathered relief symbols. No yellow stick-men, orange cartoon heads, cartoon chick, ZZZ, floppy disks or shiny flat gold icons. Preserve all actual screenshot functions and exact visible content, with no invented features, no external names/logos/watermarks. Individual creature details ONLY INSIDE Dungeonbook, never create any separate creature info window or put individual stats into the bottom bar. Keep the full top resource strip, contextual hint, bottom minimap, tab/action rail, aggregate overview and current tab content. Source UI controls/text positions and semantic relationships are authoritative. Preserve world flames/lighting as in screenshot. Full screenshot, no montage, no inset.Restyle actual layered End Game menu and front confirmation dialog. Front title exactly Do you really want to restart this level?; Yes and No buttons, unchecked Save the game replay? checkbox, close cross. Behind it preserve Quit to Menu, Exit to System, Restart Level, Back, Continue Game. Keep same source scene, controls, layering and values. Opaque painted charcoal surfaces with quiet worn iron frames and sparse chips, NEW icons; no glass, no extra confirmations or actions.Match approved A exactly in calm material treatment and newly painted icons. Opaque stone/iron surfaces, no transparent glass. Full 1920x1200.
```

## Corrected HUD predecessor (historical provenance only)

The corrected HUD record above removes an unwanted window from an intermediate image. The following is the exact prompt that produced that immediate predecessor. The window request in this historical block was rejected and must not be repeated. Inputs were, in order: `ODscreenshot_2026-10-23_174522_5.png`, `ODscreenshot_2026-10-23_174059_4.png`, and intermediate `exec-bb06fc6f-1a55-4b4d-a4b2-6498549d315a.png`.

```text
Use case: compositing. Finished full-screen in-game GUI concept, PNG EXACTLY 1920x1200 pixels, landscape 16:10. IMAGE 1 IS THE MANDATORY EDIT TARGET: preserve its actual rendered 3D background, camera, geometry, creatures and floor tiles in their exact positions. Replace interface artwork only. Other images are style/reference inputs only, NEVER use their background. All visible interface is richly hand-painted, oppressive, intimidating ruined dark fantasy: deeply weathered tactile surfaces, asymmetric missing chunks, irregular cracks and heavy depth. NOT neat, smooth, symmetrical decoration, friendly, flat panels, glass, website, app, modern sans-serif or pixel bitmap text. Readable antialiased serif lettering, pale ivory with restrained hierarchy. Preserve source controls/content. No extra gameplay features, invented product names, external game names, logos or watermarks. No presentation board, no inset screenshots, no titles outside UI. STYLE A REVISED: quiet oppressive matte blackened iron and charcoal basalt. Simple broad heavy forged borders with a few asymmetrically broken edges, sparse large rivets, soot and old scratches. NO lava, NO flames, NO glowing cracks, NO ember outlines, NO decorative skulls, NO spikes, NO banners, NO chains. Restrained steel gray edge light. Large calm dark textured surfaces; distress concentrated at a few corners, never everywhere. Clear visual hierarchy, minimal visual noise. Deep relief and painterly material, never flat website panel.HUD SCREEN: Preserve actual full image1 dungeon, top mana/gold, bottom-left circular minimap and controls, main navigation tabs, action/event rail, creature TYPE portraits and aggregate creature counts in bottom strip, room/action icons per image2. CRITICAL: bottom strip contains ONLY species/aggregate overview and navigation, NEVER health or level or individual creature stats. No individual stat panel docked into bottom strip. Show a SEPARATE small floating selected-Goblin information window in the gameplay area on RIGHT SIDE ABOVE bottom bar, with visible gap between it and bar, title Goblin, portrait, health and Level 2 allowed ONLY inside that separate floating window. Keep bottom strip calm and uncluttered. All icons newly painted serious tactile miniatures, replace all original gold stick figures and old orange cartoon faces. Room icons and hint styling informed by image2, without using its world background. CRITICAL ICON REDESIGN: EVERY SINGLE visible interface icon MUST be completely newly hand-painted, not reused/recoloured old artwork. Source icons are semantic inventory ONLY. Replace golden stick-man with sinister hooded creature bust, house with ruined stone doorway, sparkling wand with twisted scorched staff, pick with battered iron pickaxe, orange smiling head with snarling goblin relief; objective scroll with torn bloodsealed parchment, skill flask with cracked alchemical vessel, production anvil with scarred forge, info circles with chipped stone runic plaques, eye with realistically painted lidless ominous eye, camera with engraved lens relic, disk symbols with carved save/load tablets, help with weathered question rune, settings with broken iron cog, minimap zoom with rough optical lens, arrows with chipped blades, gold badge with weathered stacked coins, mana with pulsating dark anatomical heart. Room symbols: ruined straw pallet (no ZZZ), menacing hatching egg/claw (no cartoon chick), stained grimoire (no smiling book), scarred training dummy and crossed iron swords (no colourful target). No shiny gold flat pictograms, no orange cartoon goblin heads, no floppy disks, no generic lowercase i symbols, no bright yellow stick-men, no repeated old symbols. Material and palette match this variant throughout. Preserve the exact functions, positions, counts and source text. LATEST OWNER CORRECTION: all GUI must be calm and visually restrained. No fire, lava, glowing edges or pervasive decoration. Distinguish shapes and material using large painterly forms and sparse wear. Background world lighting remains unchanged. ALL navigation icons must visibly be newly painted full-material miniatures; zero old gold pictograms or cartoon symbols, INCLUDING repeated information buttons (replace with carved stone question-rune plaques), help, zoom, arrows, row action icons. Navigation icons are focal points and must read at small size.Image3 is owner-favoured restrained iron style, match its icons and frame calmness. Absolutely no individual health or level numbers in bottom bar: floating selection ABOVE it.
```
