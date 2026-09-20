# Creature health and needs

## Depleted-segment transparency, September 20

Branch `fix/creature-health-transparency` starts from the complete release
checkpoint `6eedb504`. The current texture generator composites a nearly opaque
border and depleted fill, obscuring creature details beneath missing health.
The existing material already uses alpha blending. Omit both strokes for depleted
segments in the generator, leaving visible health, centre, owner tint, level/status
cycling and the accepted Alt toggle unchanged. Regenerate the existing assets;
no C++ or network change is needed.

The texture regression checks the fill and both border bands in every health
state, plus the unchanged centre: 200 checks pass, with 96 failures before the
correction. The existing hidden-window OGRE overlay probe passes 234 checks
across all eight health states and owner colours; the rendered matrix was
inspected. Full-health and unhappy textures retain their byte-identical hashes.
The normal build's materials junction points to these updated assets, so no
executable rebuild or replacement is required; restart the game to reload them.
No game was launched by the assistant. The user accepted the result on September
20 and requested publication in the existing health-and-needs pull request.
PR #108 was updated with functional commit `8fcbbf2d`; its published fixed reply
links that commit, and its description records the changed transparency.

README and the unreleased change note describe the new gaps. Application version
0.7.3 remains unchanged because no new release or protocol change is requested.

## Toggle-Alt correction

The user clarified that each Alt press must toggle visibility and releasing Alt
must leave that choice unchanged, superseding the hold-to-show interpretation
below. The current activation/frame polling overwrites visibility from the
physical modifier state, causing the reported behavior. Replace that assignment
with an edge-triggered input latch and retain the display choice across mode
reactivation. Start a new gameplay mode hidden, as before; keyboard repeats must
not toggle repeatedly, and either Alt key must work. Preserve overlay lifetime,
new-creature inheritance and editor hover behavior; no persistence or protocol
change is required. Work remains on `fix/creature-indicator-alt` from `df45fc85`.

The production input/lifetime fixture passes 64 checks with each backend (128
total), including repeated events, release during pause, fast press/release,
overlapping left/right Alt keys, activation with a key held and missed-release
recovery. The renderer's existing visibility setter and child timers are unchanged.
Release compilation succeeds (September 19 19:36:22, staged executable under
`build/review-followups`); the running game prevents replacement of the normal
executable at that point. The subsequent September 19 20:58:12 combined build is
now deployed after the game closed; see BUILDING.md. User retest remains pending.

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
visible creature. Gameplay toggles that path on Alt presses, preserving
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
