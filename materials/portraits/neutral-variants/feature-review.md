# Concrete portrait findings

Per-file findings; placement corrections do not prove source regeneration is required.

## Kobold.mesh - build-1-slim.png

Status: closed-native-and-50x100

The source ends at the upper arms and upper torso; registered shoulder shading and contour transitions remain visible at native size.

Cause: The existing source covers only the upper torso, whereas the neutral base contains the complete visible body.

Required action: Check the derived body transition beneath the available clothing and both body options.

Evidence: Kobold.mesh/review/combined-1.png

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh/review/native-body-check.jpg

## Kobold.mesh - build-2-sturdy.png

Status: closed-native-and-50x100

The source ends at the upper arms and upper torso; registered shoulder shading and contour transitions remain visible at native size.

Cause: The existing source covers only the upper torso, whereas the neutral base contains the complete visible body.

Required action: Check the derived body transition beneath the available clothing and both body options.

Evidence: Kobold.mesh/review/combined-2.png

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh/review/native-body-check.jpg

## Kobold.mesh-female - build-1-slim.png

Status: closed-native-and-50x100

The source ends at the upper arms and upper torso; registered shoulder shading and contour transitions remain visible at native size.

Cause: The existing source covers only the upper torso, whereas the neutral base contains the complete visible body.

Required action: Check the derived body transition beneath the available clothing and both body options.

Evidence: Kobold.mesh-female/review/combined-1.png

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh-female/review/native-body-check.jpg

## Kobold.mesh-female - build-2-sturdy.png

Status: closed-native-and-50x100

The source ends at the upper arms and upper torso; registered shoulder shading and contour transitions remain visible at native size.

Cause: The existing source covers only the upper torso, whereas the neutral base contains the complete visible body.

Required action: Check the derived body transition beneath the available clothing and both body options.

Evidence: Kobold.mesh-female/review/combined-2.png

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh-female/review/native-body-check.jpg

## Dwarf1.mesh - hair-1-braid.png

Status: closed-native-and-50x100

The hair source includes a complete moustache and beard plus the side braid.

Cause: The generated hair asset contains more than the intended hair-slot content.

Required action: Retain the side braid using the recorded derived alpha polygon; inspect the temple attachment.

Evidence: ../generated-features/Dwarf1.mesh/hair-1-braid.png

Resolution: Both hair roots feathered on derived copies; separate brooch and necklace anchors retained, necklace cord fitted behind the beard union. All delivered options checked in native panels and twelve 50x100 composites.

Final evidence: ../../variants/Dwarf1.mesh/review/native-body-check.jpg

## Dwarf1.mesh - neck-2-tooth.png

Status: closed-native-and-50x100

The necklace shared the right-chest brooch anchor.

Cause: Two accessories with different attachment locations used one centred transform.

Required action: Use the separate neck-centred transform already recorded for this option and inspect beneath the beard.

Evidence: Dwarf1.mesh/review/combined-2.png

Resolution: Both hair roots feathered on derived copies; separate brooch and necklace anchors retained, necklace cord fitted behind the beard union. All delivered options checked in native panels and twelve 50x100 composites.

Final evidence: ../../variants/Dwarf1.mesh/review/native-body-check.jpg

## Dwarf1.mesh-female - chin-1-square.png

Status: closed-native-and-50x100

Surrounding skin boundaries remain visible below the mouth in the individual overview.

Cause: Different source skin shading meets the neutral face at the patch contour.

Required action: Inspect and adjust the derived contour feathering with all mouth variants.

Evidence: Dwarf1.mesh-female/review/overview.jpg

Resolution: Transparent padded alpha filtering removes the rectangular patch boundaries; all delivered options were inspected in native face/body panels and all twelve 50x100 composites.

Final evidence: ../../variants/Dwarf1.mesh-female/review/native-face-check.jpg

## Dwarf1.mesh-female - chin-2-rounded.png

Status: closed-native-and-50x100

Surrounding skin boundaries remain visible below the mouth in the individual overview.

Cause: Different source skin shading meets the neutral face at the patch contour.

Required action: Inspect and adjust the derived contour feathering with all mouth variants.

Evidence: Dwarf1.mesh-female/review/overview.jpg

Resolution: Transparent padded alpha filtering removes the rectangular patch boundaries; all delivered options were inspected in native face/body panels and all twelve 50x100 composites.

Final evidence: ../../variants/Dwarf1.mesh-female/review/native-face-check.jpg

## Orc.mesh-female - scar-1-diagonal.png

Status: closed-native-and-50x100

In the literal manifest composite, the upper scar crossed the ear root.

Cause: Scar is drawn after ears and its current alpha extended into the ear area.

Required action: Move the scar into the cheek and bake alpha avoidance against all ear and hair options; inspect the literal manifest composite.

Evidence: ../variants/Orc.mesh-female/review/combined-1.png

Resolution: Derived scar placement avoids the ear root; padded alpha feathering removes the mouth boundary. Every delivered option reviewed at native scale and in twelve 50x100 composites.

Final evidence: ../../variants/Orc.mesh-female/review/native-face-check.jpg

## Orc.mesh-female - mouth-1-tusks.png

Status: closed-native-and-50x100

A horizontal surrounding-skin edge was visible below the right mouth corner.

Cause: The mouth source includes skin that ends at the lower contour.

Required action: Apply the derived lower-edge feather already implemented and recheck every chin combination.

Evidence: ../variants/Orc.mesh-female/review/combined-1.png

Resolution: Derived scar placement avoids the ear root; padded alpha feathering removes the mouth boundary. Every delivered option reviewed at native scale and in twelve 50x100 composites.

Final evidence: ../../variants/Orc.mesh-female/review/native-face-check.jpg

## Knight.mesh - outfit-1-plate-build0.png

Status: closed-native-and-50x100

The new outfit has its bent sleeves and belt roughly 200 pixels above the neutral body anchors; the raw composite exposes a second pair of arms.

Cause: New clothing geometry is vertically compressed relative to the saved neutral body.

Required action: Correct this newly generated outfit within the three permitted attempts; preserve the existing 632 sources and the neutral base.

Evidence: ../../../work/knight-outfit-2-raw-composite.png

Resolution: Existing corrected clothing sources fitted to both body options; helmets cover the neutral head. Every delivered option reviewed at native size and twelve 50x100 composites.

Final evidence: ../../variants/Knight.mesh/review/native-body-check.jpg

## Knight.mesh - outfit-1-plate-build0.png

Status: closed-native-and-50x100

The new outfit has its bent sleeves and belt roughly 200 pixels above the neutral body anchors; the raw composite exposes a second pair of arms.

Cause: New clothing geometry is vertically compressed relative to the saved neutral body.

Required action: Correct this newly generated outfit within the three permitted attempts; preserve the existing 632 sources and the neutral base.

Evidence: ../../../work/knight-outfit-3-raw-composite.png

Resolution: Existing corrected clothing sources fitted to both body options; helmets cover the neutral head. Every delivered option reviewed at native size and twelve 50x100 composites.

Final evidence: ../../variants/Knight.mesh/review/native-body-check.jpg

## Knight.mesh-female - outfit-1-plate-build0.png

Status: closed-native-and-50x100

The new armor leaves neutral forearm wedges visible at both sides between rows 1250 and 1550.

Cause: The generated sleeve openings are larger than the neutral forearm outline.

Required action: Correct the new clothing source to cover the existing neutral arms; preserve the base and all existing feature sources.

Evidence: Knight.mesh-female/review/outfits/outfit-1-plate-build0.png

Resolution: Existing corrected clothing sources fitted to both body options; helmets cover the neutral head. Every delivered option reviewed at native size and twelve 50x100 composites.

Final evidence: ../../variants/Knight.mesh-female/review/native-body-check.jpg

## Goblin.mesh - chin-1-forked.png

Status: closed-native-and-50x100

The native composite has a hard skin transition at the upper jaw patch.

Cause: Source contour and neutral geometry differ at this attachment.

Required action: Feather the derived jaw alpha and check both chin options with all mouth options.

Evidence: Goblin.mesh/review/combined-1.png

Resolution: Padded face feathering, crown anchoring and wider continuous garment registration remove the documented boundaries and exposed arm strips; all options reviewed at native size and 50x100.

Final evidence: ../../variants/Goblin.mesh/review/native-body-check.jpg

## Goblin.mesh - outfit-1-patched-build0.png

Status: closed-native-and-50x100

Visible neutral forearm pixels remain at the lower sleeve edge.

Cause: Source contour and neutral geometry differ at this attachment.

Required action: Register sleeve width to cover the neutral and both existing body options, without changing the source.

Evidence: Goblin.mesh/review/combined-1.png

Resolution: Padded face feathering, crown anchoring and wider continuous garment registration remove the documented boundaries and exposed arm strips; all options reviewed at native size and 50x100.

Final evidence: ../../variants/Goblin.mesh/review/native-body-check.jpg

## Goblin.mesh-female - chin-1-square.png

Status: closed-native-and-50x100

The native composite has a hard skin transition at the upper jaw patch.

Cause: Source contour and neutral geometry differ at this attachment.

Required action: Feather the derived jaw alpha and check both chin options with all mouth options.

Evidence: Goblin.mesh-female/review/combined-1.png

Resolution: Padded face feathering, crown anchoring and wider continuous garment registration remove the documented boundaries and exposed arm strips; all options reviewed at native size and 50x100.

Final evidence: ../../variants/Goblin.mesh-female/review/native-body-check.jpg

## Goblin.mesh-female - outfit-1-patched-build0.png

Status: closed-native-and-50x100

Visible neutral forearm pixels remain at the lower sleeve edge.

Cause: Source contour and neutral geometry differ at this attachment.

Required action: Register sleeve width to cover the neutral and both existing body options, without changing the source.

Evidence: Goblin.mesh-female/review/combined-1.png

Resolution: Padded face feathering, crown anchoring and wider continuous garment registration remove the documented boundaries and exposed arm strips; all options reviewed at native size and 50x100.

Final evidence: ../../variants/Goblin.mesh-female/review/native-body-check.jpg

## Cultist.mesh-female - helmet-1-crest.png

Status: closed-native-and-50x100

The literal combined review shows a dark gap between the helmet lower edge and the robe collar; inspect all four helmet options against both builds.

Cause: Existing helmet registration and the new robe collar do not share the neutral head and neck anchors.

Required action: Adjust existing helmet or robe registration locally and inspect every helmet at native size and 50x100; preserve all raw sources.

Evidence: ../../variants/Cultist.mesh-female/review/combined-native-sheet.jpg

Resolution: Old costume neckline masked on both derived build options; all four helmets and every delivered option checked at native size and 50x100. The earlier dark gap observation was neutral-neck shading, not a missing background region; the collar boundary is now continuous.

Final evidence: ../../variants/Cultist.mesh-female/review/native-face-check.jpg

## Dwarf1.mesh-female - eyes-1-narrow.png

Status: closed-native-and-50x100

Native combined review shows a hard skin edge at the rectangular option boundary.

Cause: Previous alpha filtering replicated opaque edge pixels instead of treating pixels outside the slot as transparent.

Required action: Use transparent padded alpha filtering, then inspect every facial option in native and 50x100 composites.

Evidence: ../../variants/Dwarf1.mesh-female/review/combined-1.png

Resolution: Transparent padded alpha filtering removes the rectangular patch boundaries; all delivered options were inspected in native face/body panels and all twelve 50x100 composites.

Final evidence: ../../variants/Dwarf1.mesh-female/review/native-face-check.jpg

## Monk.mesh-female - eyes-1-narrow.png

Status: closed-native-and-50x100

Native combined review shows a hard skin edge at the rectangular option boundary.

Cause: Previous alpha filtering replicated opaque edge pixels instead of treating pixels outside the slot as transparent.

Required action: Use transparent padded alpha filtering, then inspect every facial option in native and 50x100 composites.

Evidence: ../../variants/Monk.mesh-female/review/combined-1.png

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

## Monk.mesh-female - nose-1-crooked.png

Status: closed-native-and-50x100

Native combined review shows a hard skin edge at the rectangular option boundary.

Cause: Previous alpha filtering replicated opaque edge pixels instead of treating pixels outside the slot as transparent.

Required action: Use transparent padded alpha filtering, then inspect every facial option in native and 50x100 composites.

Evidence: ../../variants/Monk.mesh-female/review/combined-1.png

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

## Monk.mesh-female - mouth-1-teeth.png

Status: closed-native-and-50x100

Native combined review shows a hard skin edge at the rectangular option boundary.

Cause: Previous alpha filtering replicated opaque edge pixels instead of treating pixels outside the slot as transparent.

Required action: Use transparent padded alpha filtering, then inspect every facial option in native and 50x100 composites.

Evidence: ../../variants/Monk.mesh-female/review/combined-1.png

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

## Monk.mesh-female - chin-1-square.png

Status: closed-native-and-50x100

Native combined review shows a hard skin edge at the rectangular option boundary.

Cause: Previous alpha filtering replicated opaque edge pixels instead of treating pixels outside the slot as transparent.

Required action: Use transparent padded alpha filtering, then inspect every facial option in native and 50x100 composites.

Evidence: ../../variants/Monk.mesh-female/review/combined-1.png

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

## Cultist.mesh-female - build-1-slim.png

Status: closed-native-and-50x100

Native review shows bright red old collar fragments beside the new robe neckline.

Cause: The preserved build source contains the original costume, which extends above the new robe.

Required action: Mask the old neckline on derived build copies, then recheck both body choices with every helmet.

Evidence: ../../variants/Cultist.mesh-female/review/native-face-check.jpg

Resolution: Old costume neckline masked on both derived build options; all four helmets and every delivered option checked at native size and 50x100. The earlier dark gap observation was neutral-neck shading, not a missing background region; the collar boundary is now continuous.

Final evidence: ../../variants/Cultist.mesh-female/review/native-face-check.jpg

## Cultist.mesh-female - build-2-sturdy.png

Status: closed-native-and-50x100

Native review shows bright red old collar fragments beside the new robe neckline.

Cause: The preserved build source contains the original costume, which extends above the new robe.

Required action: Mask the old neckline on derived build copies, then recheck both body choices with every helmet.

Evidence: ../../variants/Cultist.mesh-female/review/native-face-check.jpg

Resolution: Old costume neckline masked on both derived build options; all four helmets and every delivered option checked at native size and 50x100. The earlier dark gap observation was neutral-neck shading, not a missing background region; the collar boundary is now continuous.

Final evidence: ../../variants/Cultist.mesh-female/review/native-face-check.jpg

## Monk.mesh - hair-2-waves.png

Status: closed-native-and-50x100

The second hairstyle was vertically centred inside its tall slot and left an unintended exposed scalp above the fringe.

Cause: Whole-image bounds were centred even when source aspect ratio left unused slot height.

Required action: Anchor the existing hair source at the measured crown rather than the slot centre and recheck both hairstyles.

Evidence: ../../variants/Monk.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh/review/native-face-check.jpg

## Monk.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

The second hairstyle was vertically centred inside its tall slot and left an unintended exposed scalp above the fringe.

Cause: Whole-image bounds were centred even when source aspect ratio left unused slot height.

Required action: Anchor the existing hair source at the measured crown rather than the slot centre and recheck both hairstyles.

Evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

Resolution: Hair crown anchored at the top, ears fitted to the neutral head, and padded alpha feathering removes rectangular facial boundaries. Every option reviewed at native scale and twelve 50x100 composites.

Final evidence: ../../variants/Monk.mesh-female/review/native-face-check.jpg

## Kobold.mesh - outfit-1-patched-build0.png

Status: closed-native-and-50x100

Horizontal texture streaks and abrupt sleeve/torso jumps visible in native body panels.

Cause: Earlier row-span extension changes sampling width abruptly between rows.

Required action: Refit the existing clothing source using continuous sleeve extensions and inspect native and 50x100 composites.

Evidence: ../../variants/Kobold.mesh/review/native-body-check.jpg

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh/review/native-body-check.jpg

## Kobold.mesh-female - outfit-1-patched-build0.png

Status: closed-native-and-50x100

Horizontal texture streaks and abrupt sleeve/torso jumps visible in native body panels.

Cause: Earlier row-span extension changes sampling width abruptly between rows.

Required action: Refit the existing clothing source using continuous sleeve extensions and inspect native and 50x100 composites.

Evidence: ../../variants/Kobold.mesh-female/review/native-body-check.jpg

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh-female/review/native-body-check.jpg

## Kobold.mesh - scar-1-diagonal.png

Status: closed-native-and-50x100

Lower scar tip extends outside the left cheek in the native composite.

Cause: Scar slot too far left on the neutral head.

Required action: Move scar slot 35 pixels right; inspect all scar options.

Evidence: ../../variants/Kobold.mesh/review/native-face-check.jpg

Resolution: Continuous sleeve registration covers both body options; preserved background gaps remain unchanged. Scar shifted onto the cheek. Native panels and twelve 50x100 composites checked.

Final evidence: ../../variants/Kobold.mesh/review/native-body-check.jpg

## Goblin.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Hair leaves a bare crown strip when centered vertically.

Cause: Alpha bounds of the shorter hairstyle centered in the tall hair slot.

Required action: Anchor existing hair at the crown and review both hairstyles.

Evidence: ../../variants/Goblin.mesh-female/review/native-face-check.jpg

Resolution: Padded face feathering, crown anchoring and wider continuous garment registration remove the documented boundaries and exposed arm strips; all options reviewed at native size and 50x100.

Final evidence: ../../variants/Goblin.mesh-female/review/native-body-check.jpg

## Dwarf2.mesh - eyes-2-round.png

Status: closed-native-and-50x100

Eye-source skin extends outside the neutral head right contour.

Cause: Slot position and scale do not match the neutral head.

Required action: Reduce eye-slot width to 385 pixels and height to 165 pixels.

Evidence: ../../variants/Dwarf2.mesh/review/native-face-check.jpg

Resolution: Eye width fitted to head contour; side-hair root and crown aligned; neck accessory restored beneath the beard occlusion mask. All options viewed at native scale and 50x100.

Final evidence: ../../variants/Dwarf2.mesh/review/native-face-check.jpg

## Dwarf2.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Hair root does not meet the neutral crown/temple.

Cause: Slot position and scale do not match the neutral head.

Required action: Anchor female hair at the crown; move male side hair to the temple.

Evidence: ../../variants/Dwarf2.mesh/review/native-face-check.jpg

Resolution: Eye width fitted to head contour; side-hair root and crown aligned; neck accessory restored beneath the beard occlusion mask. All options viewed at native scale and 50x100.

Final evidence: ../../variants/Dwarf2.mesh/review/native-face-check.jpg

## Dwarf2.mesh-female - eyes-2-round.png

Status: closed-native-and-50x100

Eye-source skin extends outside the neutral head right contour.

Cause: Slot position and scale do not match the neutral head.

Required action: Reduce eye-slot width to 385 pixels and height to 165 pixels.

Evidence: ../../variants/Dwarf2.mesh-female/review/native-face-check.jpg

Resolution: Eye width fitted to head contour; side-hair root and crown aligned; neck accessory restored beneath the beard occlusion mask. All options viewed at native scale and 50x100.

Final evidence: ../../variants/Dwarf2.mesh-female/review/native-face-check.jpg

## Dwarf2.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Hair root does not meet the neutral crown/temple.

Cause: Slot position and scale do not match the neutral head.

Required action: Anchor female hair at the crown; move male side hair to the temple.

Evidence: ../../variants/Dwarf2.mesh-female/review/native-face-check.jpg

Resolution: Eye width fitted to head contour; side-hair root and crown aligned; neck accessory restored beneath the beard occlusion mask. All options viewed at native scale and 50x100.

Final evidence: ../../variants/Dwarf2.mesh-female/review/native-face-check.jpg

## Dwarf2.mesh - neck-2-torque.png

Status: closed-native-and-50x100

Neck ornament lies across the beard.

Cause: Neck slot too high and missing beard occlusion.

Required action: Move neck slot lower and bake inverse beard alpha union into necklaces.

Evidence: ../../variants/Dwarf2.mesh/review/native-body-check.jpg

Resolution: Eye width fitted to head contour; side-hair root and crown aligned; neck accessory restored beneath the beard occlusion mask. All options viewed at native scale and 50x100.

Final evidence: ../../variants/Dwarf2.mesh/review/native-face-check.jpg

## RunelordDwarf.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Hair roots centred below the temples, leaving an unintended bald crown.

Cause: Vertical centring of an asymmetric hair source.

Required action: Anchor the hair silhouette at the top of its head slot.

Evidence: ../../variants/RunelordDwarf.mesh/review/native-face-check.jpg

Resolution: Side-hair repositioned and masked behind the neutral head silhouette; neck overlays masked behind beard options. All options checked at native scale and 50x100.

Final evidence: ../../variants/RunelordDwarf.mesh/review/native-face-check.jpg

## RunelordDwarf.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Hair roots centred below the temples, leaving an unintended bald crown.

Cause: Vertical centring of an asymmetric hair source.

Required action: Anchor the hair silhouette at the top of its head slot.

Evidence: ../../variants/RunelordDwarf.mesh/review/native-face-check.jpg

Resolution: Side-hair repositioned and masked behind the neutral head silhouette; neck overlays masked behind beard options. All options checked at native scale and 50x100.

Final evidence: ../../variants/RunelordDwarf.mesh/review/native-face-check.jpg

## RunelordDwarf.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Hair roots centred below the temples, leaving an unintended bald crown.

Cause: Vertical centring of an asymmetric hair source.

Required action: Anchor the hair silhouette at the top of its head slot.

Evidence: ../../variants/RunelordDwarf.mesh-female/review/native-face-check.jpg

Resolution: Side-hair repositioned and masked behind the neutral head silhouette; neck overlays masked behind beard options. All options checked at native scale and 50x100.

Final evidence: ../../variants/RunelordDwarf.mesh-female/review/native-face-check.jpg

## RunelordDwarf.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Hair roots centred below the temples, leaving an unintended bald crown.

Cause: Vertical centring of an asymmetric hair source.

Required action: Anchor the hair silhouette at the top of its head slot.

Evidence: ../../variants/RunelordDwarf.mesh-female/review/native-face-check.jpg

Resolution: Side-hair repositioned and masked behind the neutral head silhouette; neck overlays masked behind beard options. All options checked at native scale and 50x100.

Final evidence: ../../variants/RunelordDwarf.mesh-female/review/native-face-check.jpg

## RunelordDwarf.mesh - neck-2-torque.png

Status: closed-native-and-50x100

Neck accessory drawn over the beard.

Cause: Neck draw order without beard occlusion.

Required action: Mask the neck overlay behind the union of the existing beard options.

Evidence: ../../variants/RunelordDwarf.mesh/review/native-body-check.jpg

Resolution: Side-hair repositioned and masked behind the neutral head silhouette; neck overlays masked behind beard options. All options checked at native scale and 50x100.

Final evidence: ../../variants/RunelordDwarf.mesh/review/native-face-check.jpg

## Gnome.mesh - chin-1-square.png

Status: closed-native-and-50x100

Chin patch extends below neutral jaw.

Cause: Source centred in a generic slot.

Required action: Fit the chin into the 300x100 slot at y=750, below the mouth.

Evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

## Gnome.mesh - chin-2-rounded.png

Status: closed-native-and-50x100

Chin patch extends below neutral jaw.

Cause: Source centred in a generic slot.

Required action: Fit the chin into the 300x100 slot at y=750, below the mouth.

Evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

## Gnome.mesh - neck-1-teeth.png

Status: closed-native-and-50x100

Neck ornament floats in the middle of the chest.

Cause: Source centred in a generic slot.

Required action: Move the neck slot up 120 pixels.

Evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

## Gnome.mesh - neck-2-torque.png

Status: closed-native-and-50x100

Neck ornament floats in the middle of the chest.

Cause: Source centred in a generic slot.

Required action: Move the neck slot up 120 pixels.

Evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh/review/native-face-check.jpg

## Gnome.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Side-hair roots overlap the bald forehead.

Cause: Source centred in a generic slot.

Required action: Mask the existing side hair behind the neutral head contour.

Evidence: ../../variants/Gnome.mesh-female/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh-female/review/native-face-check.jpg

## Gnome.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Side-hair roots overlap the bald forehead.

Cause: Source centred in a generic slot.

Required action: Mask the existing side hair behind the neutral head contour.

Evidence: ../../variants/Gnome.mesh-female/review/native-face-check.jpg

Resolution: Chin fitted within jaw while preserving mouth; necklace raised to neckline; side-hair masked behind neutral head. All options checked at native scale and 50x100.

Final evidence: ../../variants/Gnome.mesh-female/review/native-face-check.jpg

## Adventurer.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Hair centred across the face with bald crown.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

## Adventurer.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Hair centred across the face with bald crown.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

## Adventurer.mesh - build-1-slim.png

Status: closed-native-and-50x100

Old costume contours protrude into neutral arm gaps.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

## Adventurer.mesh - build-2-sturdy.png

Status: closed-native-and-50x100

Old costume contours protrude into neutral arm gaps.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh/review/native-face-check.jpg

## Adventurer.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Hair centred across the face with bald crown.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

## Adventurer.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Hair centred across the face with bald crown.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

## Adventurer.mesh-female - build-1-slim.png

Status: closed-native-and-50x100

Old costume contours protrude into neutral arm gaps.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

## Adventurer.mesh-female - build-2-sturdy.png

Status: closed-native-and-50x100

Old costume contours protrude into neutral arm gaps.

Cause: Generic centred hair registration or unmasked source costume.

Required action: Anchor hair at slot top; clip body sources to neutral skin silhouette.

Evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

Resolution: Hair anchored at crown; female face occlusion baked into hair alpha; old costume clipped to neutral body silhouette. All options checked at native scale and 50x100.

Final evidence: ../../variants/Adventurer.mesh-female/review/native-face-check.jpg

## Defender.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Hair roots lie below the crown.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Hair roots lie below the crown.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh - build-1-slim.png

Status: closed-native-and-50x100

Old body/costume contours appear inside arm gaps.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh - build-2-sturdy.png

Status: closed-native-and-50x100

Old body/costume contours appear inside arm gaps.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Hair roots lie below the crown.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Hair roots lie below the crown.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh-female - build-1-slim.png

Status: closed-native-and-50x100

Old body/costume contours appear inside arm gaps.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh-female - build-2-sturdy.png

Status: closed-native-and-50x100

Old body/costume contours appear inside arm gaps.

Cause: Centred hair registration or body-source costume outside the new silhouette.

Required action: Anchor hair at slot top; clip old costume to neutral silhouette and fit clothing to uncovered arms.

Evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Defender.mesh-female - chin-1-square.png

Status: closed-native-and-50x100

Rectangular chin boundary visible on the left jaw.

Cause: Source surrounding-skin rectangle.

Required action: Feather the derived chin alpha boundary.

Evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg

Resolution: Head silhouette mask and top hair anchor; body clipped to neutral skin silhouette; sleeves extended over uncovered forearms; female chin moved, feathered, and masked behind all mouth options.

Final evidence: ../../variants/Defender.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Side hair overlaps forehead and cheek.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Side hair overlaps forehead and cheek.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh - build-1-slim.png

Status: closed-native-and-50x100

Old red and blue garment visible outside robe.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh - build-2-sturdy.png

Status: closed-native-and-50x100

Old red and blue garment visible outside robe.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Side hair overlaps forehead and cheek.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Side hair overlaps forehead and cheek.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh-female - build-1-slim.png

Status: closed-native-and-50x100

Old red and blue garment visible outside robe.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Wizard.mesh-female - build-2-sturdy.png

Status: closed-native-and-50x100

Old red and blue garment visible outside robe.

Cause: Source overlaps neutral head or extends outside neutral body.

Required action: Mask hair behind head and clip build to neutral body.

Evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg

Resolution: Hair masked behind neutral head and body sources clipped to neutral silhouette; all options reviewed at native scale and 50x100.

Final evidence: ../../variants/Wizard.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - hair-1-swept.png

Status: closed-native-and-50x100

Hair crown starts below neutral head crown.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - hair-2-waves.png

Status: closed-native-and-50x100

Hair crown starts below neutral head crown.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - chin-1-square.png

Status: closed-native-and-50x100

Chin patch floats below mouth across clothing.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - chin-2-rounded.png

Status: closed-native-and-50x100

Chin patch floats below mouth across clothing.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - build-1-slim.png

Status: closed-native-and-50x100

Old body silhouette visible inside arm gap.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh-male - build-2-sturdy.png

Status: closed-native-and-50x100

Old body silhouette visible inside arm gap.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Hair crown starts below neutral head crown.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Hair crown starts below neutral head crown.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - chin-1-square.png

Status: closed-native-and-50x100

Chin patch floats below mouth across clothing.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - chin-2-rounded.png

Status: closed-native-and-50x100

Chin patch floats below mouth across clothing.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - build-1-slim.png

Status: closed-native-and-50x100

Old body silhouette visible inside arm gap.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Elf.mesh - build-2-sturdy.png

Status: closed-native-and-50x100

Old body silhouette visible inside arm gap.

Cause: Centred hair registration and low chin slot; unmasked body silhouette.

Required action: Anchor crown, reposition chin with mouth occlusion, clip body.

Evidence: ../../variants/Elf.mesh/review/native-face-check.jpg

Resolution: Hair crown anchored at slot top; female fringe masked outside face; chin repositioned and mouth mask preserved; body clipped to neutral silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/Elf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh-male - hair-1-swept.png

Status: closed-native-and-50x100

Crown below head; strands cross facial features.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh-male - hair-2-waves.png

Status: closed-native-and-50x100

Crown below head; strands cross facial features.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh-male - chin-1-square.png

Status: closed-native-and-50x100

Chin extends over garment.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh-male - chin-2-rounded.png

Status: closed-native-and-50x100

Chin extends over garment.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh-male - outfit-1-tunic-build0.png

Status: closed-native-and-50x100

Blue forearm contours visible inside sleeve gaps.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh-male/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh - hair-1-swept.png

Status: closed-native-and-50x100

Crown below head; strands cross facial features.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh - hair-2-waves.png

Status: closed-native-and-50x100

Crown below head; strands cross facial features.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh - chin-1-square.png

Status: closed-native-and-50x100

Chin extends over garment.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh - chin-2-rounded.png

Status: closed-native-and-50x100

Chin extends over garment.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## DarkElf.mesh - outfit-1-tunic-build0.png

Status: closed-native-and-50x100

Blue forearm contours visible inside sleeve gaps.

Cause: Low centred registration and narrow sleeve coverage.

Required action: Anchor crown, mask face, reposition chin and extend existing sleeve texture.

Evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg

Resolution: Crown anchored, face-contour alpha mask applied, chin repositioned with mouth occlusion and continuous sleeve extensions fitted; body clipped to neutral blue skin silhouette. Native and 50x100 checks completed.

Final evidence: ../../variants/DarkElf.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Troll.mesh - outfit-1-leather-build0.png

Status: closed-native-and-50x100

Raised collar covers right cheek.

Cause: Head colour mask misses stone shading; centred hair placement.

Required action: Use measured head polygon and anchor/mask existing hair.

Evidence: ../../variants/Troll.mesh/review/native-face-check.jpg

Resolution: Collars masked behind measured stone-head silhouettes; female hair crown anchored and face strands masked. Native and 50x100 checks completed.

Final evidence: ../../variants/Troll.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Troll.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Crown sits below head top and strands cross face.

Cause: Head colour mask misses stone shading; centred hair placement.

Required action: Use measured head polygon and anchor/mask existing hair.

Evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg

Resolution: Collars masked behind measured stone-head silhouettes; female hair crown anchored and face strands masked. Native and 50x100 checks completed.

Final evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Troll.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Strands cross facial features.

Cause: Head colour mask misses stone shading; centred hair placement.

Required action: Use measured head polygon and anchor/mask existing hair.

Evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg

Resolution: Collars masked behind measured stone-head silhouettes; female hair crown anchored and face strands masked. Native and 50x100 checks completed.

Final evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Troll.mesh-female - outfit-1-leather-build0.png

Status: closed-native-and-50x100

Collar overlaps right cheek after hair registration reveals it.

Cause: Stone colour threshold misses dark head shading.

Required action: Mask collar behind measured head silhouette.

Evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg

Resolution: Collars masked behind measured stone-head silhouettes; female hair crown anchored and face strands masked. Native and 50x100 checks completed.

Final evidence: ../../variants/Troll.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh-female - hair-1-swept.png

Status: closed-native-and-50x100

Crest starts below head crown.

Cause: Centred crest and low jaw registration; sleeve contour too narrow.

Required action: Anchor crest, reposition jaw and extend existing sleeve alpha/texture.

Evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh-female - hair-2-waves.png

Status: closed-native-and-50x100

Crest starts below head crown.

Cause: Centred crest and low jaw registration; sleeve contour too narrow.

Required action: Anchor crest, reposition jaw and extend existing sleeve alpha/texture.

Evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh-female - chin-1-square.png

Status: closed-native-and-50x100

Jaw patch is separated from lower lip by clothing.

Cause: Centred crest and low jaw registration; sleeve contour too narrow.

Required action: Anchor crest, reposition jaw and extend existing sleeve alpha/texture.

Evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh-female - chin-2-rounded.png

Status: closed-native-and-50x100

Jaw patch is separated from lower lip by clothing.

Cause: Centred crest and low jaw registration; sleeve contour too narrow.

Required action: Anchor crest, reposition jaw and extend existing sleeve alpha/texture.

Evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh-female - outfit-1-leather-build0.png

Status: closed-native-and-50x100

Uncovered yellow body sliver inside left lower sleeve.

Cause: Centred crest and low jaw registration; sleeve contour too narrow.

Required action: Anchor crest, reposition jaw and extend existing sleeve alpha/texture.

Evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh-female/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png

## Lizardman.mesh - outfit-1-leather-build0.png

Status: closed-native-and-50x100

Yellow body sliver remains inside lower sleeve gap.

Cause: Existing sleeve gap wider than first derived extension.

Required action: Extend preserved garment texture over measured uncovered body.

Evidence: ../../variants/Lizardman.mesh/review/native-body-check.jpg

Resolution: Existing crest anchored at crown; female jaw moved up and masked against mouth; preserved sleeve texture translated into uncovered body gaps. Native face/body panels and twelve 50x100 combinations inspected; no source regenerated.

Final evidence: ../../variants/Lizardman.mesh/review/native-face-check.jpg; native-body-check.jpg; combined-small-sheet.png
