# Hand rotation and selected-object drops

Work branch: `fix/hand-rotation`, based on complete checkpoint `8fcfde02`,
preserving all preceding feature work and the parallel lighting changes.

## Existing behavior and confirmed causes

Game and editor already use Ctrl + mouse wheel to rotate the local player's
held-object list. Pickup/drop rendering arranges that list with a 0.05-unit
spacing, but the separate rotation renderer places it at 1-unit intervals.
The same hand parent scales both layouts, making the rotation spacing twenty
times larger. Reuse the existing hand layout method after rotation.

There is also a selection mismatch in the existing drop path. Rotation changes
only the client list. Both game and editor send just the target tile, and the
server validates/drops its own list's first object. Its acknowledgement also
contains only seat and tile, so the client removes whichever object is first
when the reply arrives. Even synchronizing the request's selection alone would
leave rotation or pickup during the reply delay unsafe.

## Focused correction

Keep the existing rotation gesture, local list order, default last-picked-first-
dropped behavior, pickup/drop animations and permission checks. Append the
selected object's existing type/name identity to the current drop request and
the actual dropped object's identity to its acknowledgement. Resolve that
identity only within the relevant player's hand; never accept an arbitrary
world entity or fall back to another object when an explicit identity is invalid.
Use the same optional suffix in game and editor. Legacy packets without a suffix
retain their existing first-object behavior. Existing packet prefixes and message
IDs remain unchanged; no separate rotation command or second inventory is added.

Both endpoints must be updated for identity-aware rotation/drop correctness.
An older endpoint ignores the suffix or cannot supply it, retaining the previous
limitation. This correction must not claim that old rotating clients/servers
become synchronized. Saved games and creature mood/activity negotiation are
outside this change.

## Verification

The rotation renderer now calls the existing pickup/drop layout method. Requests
from game and editor include the selected identity after the tile. The server
resolves it in the requesting player's hand before running the existing drop
permission check. The drop notification includes the actual dropped identity;
the client finds that object in its current list, even after intervening input.
Missing/truncated or no-longer-held explicit identities never select another
object. Only a completely absent suffix takes the legacy first-object path.

The focused probe compiles the current production rotation/layout methods,
hand-index lookup, request builders, drop handlers, notification construction
and drop-event emission. It uses real Ogre scene nodes and the production
`ODPacket`/SFML serialization, with simulated map, player and entity state. The
final drop endpoint records inventory removal; this is not a live simulation,
socket, replay playback or visual acceptance run.

- Before the correction: 164 failures in 227 checks.
- After the correction: all 227 checks pass.
- Layout checks cover empty/single/multiple held-object lists, row boundaries,
  both rotation directions, restored order and the existing hand-parent scale.
- Request/reply checks cover game/editor, default and rotated selection,
  rotation or pickup while a reply is pending, selection-specific permission,
  malformed/unknown/wrong-type identities, invalid tiles, foreign replies and
  a repeated stale request. Client/server inventory membership remains equal
  after accepted replies.
- Old request/client and old server/reply code paths retain ordinary unrotated
  dropping; these tests do not certify rotation with an older endpoint.
- Windows Release compilation and runtime preparation pass. Executable:
  `build/windows/opendungeons-plus.exe`, September 6, 2026 at 17:34:49;
  SHA-256 `e5db5cf2eb7d38b077f219c6d20aa3b51e4b79d26a1b1b3e2d345673315462c9`.

Local artifacts under `build/windows/`: `generate-hand-rotation-probe.py`,
`build-hand-rotation-probe.ps1`, `hand-rotation-before-results.log`,
`hand-rotation-probe-results.log`, `hand-rotation-build.log` and
`hand-rotation-runtime.log`.

Manual check: pick up two visibly different creatures, use Ctrl + mouse wheel
in both directions, and right-click valid ground to drop the first displayed
creature. The held objects should keep their spacing, and the selected creature
should be the one that appears on the ground. Also check another rotation before
an earlier drop reply arrives when testing multiplayer. Both endpoints need this
build for the corrected identity handling. The assistant did not launch the game.

Version remains 0.7.1 because this is not a release. README documents the existing
rotation gesture; no changelog exists. No push or upstream PR was made. Original
artwork/animation comparison and broader hand acceptance remain open.
