# Creature health and needs

## Existing path

Creature simulation already maintains health, hunger, wakefulness and mood on
the server. Its existing actions send hungry creatures to food, tired or weak
creatures to their beds, and sufficiently dissatisfied creatures through work
refusal, allied conflict or departure. Worker creatures retain their existing
food and lair exemption.

The renderer already attached health, level and cycling status children to each
visible creature. Gameplay now enables that path continuously while preserving
the editor's temporary hover display and inheritance by creatures rendered
later.

## Indicator presentation

The eight existing health-state textures are now deterministic softened,
segmented ring assets. Their light segments are tinted through the existing
owner-colour material path. The enlarged level is optically centred during the
ordinary interval;
hunger, tiredness, mood and activity symbols alternate there one second at a
time. The previously omitted unhappy state has its own centred face.

The unhappy face is derived client-side from the already negotiated full mood
value. It is never added to the legacy overlay bit field, so existing packet
formats and enemy information filtering remain unchanged.

## Verification

The source-path probe passes 25 checks. The deterministic asset probe passes 26
checks across all eight decreasing health states and the unhappy icon. A real
OGRE overlay render passes 234 checks for visibility, lifetime, cleanup, default
stacking, centred level and status composition, resource loading, all eight
health states and all eight configured player colours. The existing serializer,
mood-transition, handshake, legacy-packet and activity probe passes 1,117 checks.
An additional 27-check probe executes the production overlay class and verifies
all health materials, need order, the level interval, unhappy display, level
changes, visibility rules and cleanup.

Windows Release compilation and runtime preparation pass. The executable dated
2026-09-08 20:34:19 is 4,490,752 bytes and has SHA-256
`9221DF8E21452ED11010E228404492926872F458E9346F505C6F84678FEA7905`.

The user accepted the gameplay appearance on September 8, 2026.
README documents the visible status display. Version 0.7.1 remains unchanged
because no release was requested, and the project has no changelog.
