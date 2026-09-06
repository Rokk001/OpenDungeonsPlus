# Entity information selection

## Existing implementation and remaining gap

The current fork opens creature statistics with the middle mouse button in
`GameMode::mousePressed`. It chooses the nearest entity on the pointed tile
whose `canDisplayStatsWindow` permits inspection, then calls its existing
`createStatsWindow`. `Creature` supplies the statistics window, its refresh
subscription and close handler. Before this checkpoint, no selectable information
action or minimap button entered that path.

Reuse that target selection and window lifecycle for an information toggle at
the minimap. Integrate it with `PlayerSelection`, the existing action symbol,
right-click cancellation and guarded world-release dispatch. Keep the existing
middle-click shortcut and tile-debug fallback. Inspecting must not pick up a
creature, mark a tile, drop a held object or create a second statistics window.

The creature portion is the first implementation checkpoint. Trap range is
still required before the full information tool can be considered complete.
The client receives visible `TrapEntity` render objects, not the server-side
`Trap` and its target-selection rules. Cannon targets use configured range
and visibility, spikes target their own tile, and boulders trigger on adjacent
tiles before launching a moving missile. A generic circle or an assumed range
would not describe these different mechanics. Do not label trigger distance
as projectile travel distance. Range transport/rendering is not implemented
by the creature checkpoint.

## Controls and verification

The creature checkpoint is implemented on `feature/entity-query`, starting from
the complete `fix/hand-rotation` checkpoint `c245acfa`:

- Click the question-mark button at the minimap's upper-left corner, then click
  a creature. The existing world-release guards validate the click. Previewing
  and holding the button do not open windows or repeat requests.
- Query reuses the middle-click target selection, including its permission check
  and nearest-target ordering. It remains selected after inspection. The existing
  action symbol and invalid-target indicator describe the current selection.
- Click Query again or right-click the world to cancel. Selecting another action
  replaces Query. Inspection and cancellation preserve held objects.
- The middle-click shortcut and its optional tile-debug fallback remain available.
  Existing statistics content, refresh subscriptions and close behavior are reused.

Verification on September 6, 2026:

- 56 source-derived behavior checks pass for target selection, preview, guarded
  release, cancellation, selection changes, held objects and pause/disconnection.
  Production controller methods run against simulated map/entity/input endpoints;
  the window endpoint records calls. This does not prove a live statistics
  subscription, network exchange or game-session lifecycle.
- 3,563 installed CEGUI/Ogre layout checks pass, including the new button's real
  click event, square bounds, existing image and accessible minimap center across
  800x600 through 3840x2160 and 80/100/120 percent scaling. This includes the
  existing HUD regression matrix, not 3,563 new query-only checks.
- Release compilation and runtime preparation pass in
  `build/windows/entity-query-build.log` and `entity-query-runtime.log`.
  The prepared executable is dated 17:57:58 local time; SHA-256
  `c28f1b651dad76f4b848440d1b49964350bac75c108b996f8fbf7aa149ac6fb9`.
- Probe generator, build helper and results are under `build/windows/` as
  `generate-entity-query-probe.py`, `build-entity-query-probe.ps1`,
  `entity-query-probe-results.log` and `entity-query-ui-probe-results.log`.

Manual check: select Query and click a creature, verify its information updates,
close the window, and confirm that inspecting did not pick it up. The shared
shadow checkout and normal index are preserved. No game was launched or push
made. Full tool acceptance remains open, including the trap-range work above.
