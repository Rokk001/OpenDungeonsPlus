# Missile wall crash investigation

## Evidence and existing implementation

Work branch: `fix/segmentation-fault`, created from the complete current fork
at `32550ad8`, preserving all uncommitted Escape navigation and documentation work.

The supplied Linux trace at 19:22:37 immediately follows a Wizard missile wall
hit at `[49,92]` and reports a read at address `0xf8`. Its executable offsets
have no function names. The separate 18:47:25 trace reports address `0x8` and
does not include the preceding game event; it cannot be assigned to this same
failure from the supplied evidence.

The existing server path is `ODServer::serverThread()` -> `startNewTurn()` ->
`GameMap::doTurn()` -> active-object `MissileObject::doUpkeep()`.
`TileContainer::tilesBetween()` includes the starting tile. When that tile is
already a wall, the previous-tile pointer is still null. Before the existing
fix, a non-bouncing missile logged the wall hit and immediately read the previous
tile's coordinates. The Wizard's `MissileOneHit` inherits the non-bouncing wall
handler. Both current wall handlers leave the tile argument untouched.

Commit `6a7a66b1af88543a8e0bf7a708ec35a943765b27` already guards this exact null
pointer and stops the missile at its existing position. Its recorded original
failure also reads address `0xf8` after a wall hit. It was merged by upstream
PR #19 and is an ancestor of the current fork; the guard is present in the
working source. Therefore reuse the existing correction: no additional
production-code change is justified by this report.

This is a matching known failure mechanism, not symbolication of the supplied
Linux executable: its build identity and inclusion of the fix are unknown.

## Verification

On September 6, 2026, an isolated Windows C++ probe compiled the production
`doUpkeep()`, `computeDestination()`, `tilesBetween()` and default wall handler
with the installed OGRE vectors. It uses test doubles for map storage, tile
objects, entity lifecycle and queued rendering/network movement; it is not a
Linux binary reproduction or a complete gameplay test.

The same first-wall scenario produces a caught access violation with the method
from the parent of `6a7a66b1`; the current method passes all nine checks:
first-wall termination and preserved fractional coordinates, waiting for movement
before removal, removal after movement, westward first-wall collision, a later
wall stopping at the previous tile, unobstructed flight, a tile filled under a
missile and removal when the position tile is missing.

Diagnostic files under ignored `build/windows/`:

- `generate-missile-wall-probe.py`, `build-missile-wall-probe.ps1`.
- `missile-wall-probe-sources.json`: extracted method hashes and source revisions.
- `missile-wall-before-results.log`: caught access violation, expected exit 2.
- `missile-wall-current-results.log`: nine checks, zero failures, exit 0.
- `missile-wall-before-build.log`, `missile-wall-current-build.log`: successful
  probe compilations.

No production source changed, so no game rebuild, version bump or public README
change was needed. No game, manual QA session, commit or push was performed.
The exact Linux build and the first crash at `0x8` remain unidentified; the
additional log is consistent with the existing wall correction but does not
prove which correction the reporter's executable contains.
