# Creature selection by level

Work branch: `feature/creature-level-selection`, retaining complete dialog/panel
checkpoint `6eeb4885` and the newer parallel lighting checkpoint `fe86bf03`.
The shared checkout remains on the parallel work branch; local documentation
and working files are preserved.

The approved local HUD contract documents Ctrl + period + portrait click for
the highest-level creature and Ctrl + comma + portrait click for the lowest-level
creature. The current portrait callback only handles right-click focus, and count
pickup chooses the first eligible creature. Levels and the server-validated
entity-specific pickup request already exist; reuse them without changing AI,
network payloads, ownership rules or ordinary worker/fighter quick selectors.

The keyboard wrapper currently queries modifiers only. OIS supplies key-state
queries, and the existing SFML event adapter already maps the required keys.
Expose a shared key-state query by reusing that table rather than duplicating
key mappings or tracking a second set of pressed keys in the panel. The existing
SFML Ctrl predicate accidentally checks left Ctrl twice; correct that lookup so
the documented gesture also works with right Ctrl in that backend.

Within a portrait's criterion, retain eligibility and in-flight request guards,
then select the highest/lowest available level. Keep stable existing order for
equal levels. Ctrl without exactly one of the two punctuation keys does not
request level ordering, preserving the ordinary count/portrait behavior.

## Implementation and verification

The panel now applies these two unambiguous shortcuts to portraits and their
count overlays. Ordinary portrait, count, worker and right-click behavior is
retained. The existing pickup loop chooses a matching eligible level without
changing server permissions or sending a different packet. Repeated clicks skip
pending requests; equal levels retain the original map-list order.

The keyboard wrapper delegates key queries to OIS, or looks up the requested
scan code through the existing SFML mapping and queries its current key state.
No separate pressed-key state is stored in the panel. The right-Ctrl lookup is
also corrected in the SFML modifier path.

- The real Ogre/CEGUI panel probe now passes 847 checks, including ordinary
  behavior, both level shortcuts, equal-level stability, repeated pending
  requests, held/unpickable exclusion, unchanged category filters, unsupported
  key combinations and the existing five-viewport scaling/hit-target matrix.
  It uses production panel code with simulated creatures and command endpoints;
  it does not run gameplay or press keys on the user's desktop.
- The keyboard probe compiles the production wrapper for both backends, using
  the installed SDK enums, the actual existing mapping function and simulated
  physical key states. All 21 OIS and 324 SFML checks pass, covering every mapped
  key, both sides of each modifier, release and unmapped keys.
- The production SFML wrapper also compiles against the real installed headers,
  without test substitutes, in `build/windows/keyboard-sfml-production-build.log`.
  This is a compilation check, not an SFML-window game acceptance run.
- The Windows Release game build passes in
  `build/windows/creature-level-selection-build.log`; runtime preparation and the
  final executable identity are recorded in BUILDING.md.

The prepared executable has timestamp September 6, 2026 at 17:02:57, SHA-256
`4f3a6b35d625897dcb66662bad4bc9a2aa15636869ab1b64237447e2bdf026dc`;
runtime preparation passes in `build/windows/creature-level-selection-runtime.log`.

Local probe commands are `build/windows/build-creature-panel-ui-probe.ps1` and
`build-keyboard-state-probe.ps1`, with `creature-panel-ui-probe-results.log`,
`keyboard-state-ois-results.log` and `keyboard-state-sfml-results.log` beside them.
Manual acceptance of the shortcuts remains with the user; no game was launched.
Version remains 0.7.1 because this is not a release; README documents the new
gestures, and there is no changelog. No push or upstream PR was made.
