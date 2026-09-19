# Creature health and needs

## Accepted hold-Alt follow-up

Current gameplay enables overlays permanently on activation; keyboard abstraction
already reports either Alt key for both backends. Reuse that state on activation
and each gameplay frame, and update the renderer only when it changes. New
creatures already inherit the renderer's current display request.

Need symbols have independent permanent child timers, so hiding only the health
child leaves them visible. Gate the complete creature overlay using the existing
health child's display timer, after its normal update; retain map/death filtering
and the editor's temporary-hover timer. No new timer or saved preference is needed.
Branch: `fix/creature-indicator-alt`, based on complete checkpoint `05e63f71`.

Production lifetime/modifier checks pass 35 assertions with OIS and 35 with SFML,
covering either Alt key, release during pause, unchanged states, hidden/dead
creatures, temporary hover expiry and persistent need-child hiding. The source
checks cover gameplay activation/frame polling and the existing new-creature
inheritance. Release compilation, normal runtime preparation, 32 resource and
eight effective compiler-flag checks pass. The normal executable is September 19
18:07:39, 4,854,272 bytes, SHA-256
`CD65DC8235ACF5E33C44140B34E2994B8D1F227954871677A01FE3963ED24103`.
No game was launched; manual key/visual acceptance remains with the user.
README now documents hold-Alt; no release/save/network version change is needed.

## Existing path

Creature simulation already maintains health, hunger, wakefulness and mood on
the server. Its existing actions send hungry creatures to food, tired or weak
creatures to their beds, and sufficiently dissatisfied creatures through work
refusal, allied conflict or departure. Worker creatures retain their existing
food and lair exemption.

The renderer already attached health, level and cycling status children to each
visible creature. Gameplay enables that path while Alt is held, preserving
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
