# Room construction effect

## Scope

Successful gameplay room construction receives a short violet-blue magical spark
burst across the newly built tiles. Room rules, cost, placement timing and the
existing construction sound remain unchanged.

## Existing path and chosen integration

The shared `RoomFactory::buildRoomDefault` path already computes the final room
state and sends a per-seat tile refresh to human clients with vision. Loading,
restored state and editor placement can also refresh room tiles, so a visual
transition inferred only from the received tile state would be ambiguous.

The construction path therefore sends an explicit presentation notification
after its normal tile refresh. The client creates the particles only after the
new room meshes exist. Render-time cleanup owns these transient systems, keeping
them out of room state, tile state, saved games and gameplay upkeep.

## Verification boundary

The production particle and material scripts pass the 10-check headless OGRE
probe. The notification/render-lifecycle source probe passes 12 checks, including
refresh ordering, editor exclusion, per-tile creation and finite cleanup. A real
OGRE preview renders nine simultaneous tile effects with 324 live particles; the
output was visually inspected for colour, position and rendering errors. Release
compilation and runtime preparation pass; CTest has no registered tests. No game
was launched by the implementation agent. The user accepted the in-game
appearance, intensity and timing on September 12, 2026.

Version 0.7.1 remains unchanged because no release was requested. The root README
is unchanged because room construction controls and gameplay rules did not change.
