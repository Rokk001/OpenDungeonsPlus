# Dungeon temple duplication

## Existing path and failure

The supplied `build/reference-audit/Screenshot_2026-09-21_11-53-04.jpg`
shows two offset temple objects during combat. All sixteen temple tile variants
in `config/tilesets.cfg` use `Room.mesh`, not the temple object mesh.
`RoomDungeonTemple::updateTemplePosition` creates the single persistent object;
`updateActiveSpots` preserves it during gameplay and moves it in the editor.

`Building::doUpkeep` removes damaged tiles and calls `checkForSplit`.
The inherited `Room::checkForSplit` creates a room for each disconnected group,
transfers its furniture and calls `updateActiveSpots`. A new temple room without
the original object consequently creates another `DungeonTempleObject` at its
own centre. This can multiply the dungeon core during an attack, and can also
produce inconsistent cached object ownership when the original object moves.

Keep the original temple as one logical room while its floor is damaged, using
the existing virtual split hook to exclude this room type only. Its original
object, centre, destruction and visibility lifecycle remain intact; ordinary
rooms must continue splitting. No new rendering or deduplication system is needed.

## Verification

`source/tests/check_dungeon_temple_duplication.py` compiles the actual generic
split, central-tile calculation and temple placement methods, with lightweight
map/entity dependencies and the temple's actual override. A 5x5 floor is severed
along either axis, damaged again and then completely removed, in gameplay and
editor modes. The same fixture checks ordinary rooms as a control and verifies
that the client never locally creates a temple object. Before the fix it reports
361 checks with 24 failures; after the fix all 361 pass. The original core and
gameplay centre survive, with exactly one object and no additional temple room.
All 62 production room-demolition dispatch checks also pass.

September 22: clean Release build, runtime preparation and all 32 generated
resource checks pass. The normal executable matches the built executable;
the previous executable is preserved in `build/before-temple-duplication-20260922`.
Before/after fixture output and the build log are retained under
`build/review-followups/temple-duplication-*`. See [BUILDING.md](BUILDING.md)
for the deployed timestamp and hash.

The screenshot establishes the visible symptom, but its exact map/save and
preceding actions are unavailable; user confirmation of that scenario remains
required. No game or manual QA is launched by the agent.

This scoped local fix does not change a release version, configuration or public
usage; the development note/index and build record carry the relevant updates,
with no top-level README or release changelog change required.
