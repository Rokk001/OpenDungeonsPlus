# Selling from the minimap

## Current gameplay entry point

Gameplay now exposes only the shared minimap Sell control. The legacy room and
trap removal buttons are hidden in the game sheet, and construction actions
start in the freed column. The editor retains its separate area-removal tools.
Single-tile sale rules, refunds, ownership checks and cancellation are unchanged.
This supersedes the earlier requirement below to retain both panel commands in
gameplay; those paragraphs describe the original integration checkpoint.

The focused UI probe passes 13,217 checks, including scale changes, research
visibility, construction hit targets, one visible sale entry point and preserved
editor removal controls; the existing behavior/packet probe passes 70 checks.
Map entities and transport are controlled fixtures, so in-game visual acceptance
and actual sale/refund confirmation remain user testing.

## Existing implementation and integration

Before this task, room and trap panels already exposed separate sell commands.
`RoomManager::checkSellRoomTiles` and `TrapManager::checkSellTrapTiles` collect
eligible owned tiles, display their existing refunds and send their existing
requests only after confirmation. The server revalidates ownership and the
building's sale permission. Doors use the trap path. Portals are excluded from
room sales. These rules and the original panel commands must remain intact.

Add the common Sell toggle beside the minimap and dispatch the pointed tile to
the matching existing validator. It sells the clicked room tile, trap or door;
this common entry point must not accidentally sell adjacent tiles because an
old drag origin remains in the input manager. Add explicit-tile overloads to
the two validators; their existing rectangle-based entry points delegate to
the same implementations. Do not duplicate refund, eligibility or network code.

Use the existing currency image, selection/hand feedback and guarded world-release
path. A second Sell click or existing world right-click cancels the action.
Selecting another action replaces it. Held objects, prices, game rules and the
existing room/trap area-selling commands remain unchanged.

## Implementation and verification

The common Sell toggle is implemented on `feature/contextual-selling`, starting
from complete checkpoint `a0d0335a` on `feature/entity-query`.

- The currency button occupies the minimap's upper-right corner. It selects the
  shared sale action; clicking it again cancels. The hand uses the existing
  currency image on eligible targets and the existing invalid-target feedback.
- The context strip displays the existing server-supplied refund for the pointed
  tile. World confirmation passes exactly that tile to the room or trap validator;
  doors retain the trap path. Previewing never sends a sale request.
- World right-click cancels before attempting a held-object drop. Query and Sell
  replace each other through the existing selection state. The separate room and
  trap panel commands still support their existing area selections.
- Game rules, server validation, refund amounts and network/replay identifiers
  are unchanged. No release/version change or additional dependency was required.

Verification on September 6, 2026:

- 70 focused behavior/packet checks pass. They exercise the production selection,
  release and sale-validator functions, including explicit single-tile selection,
  refund display, ownership/portal exclusions, cancellation, held objects, paused
  or disconnected input and the existing area-sale entry points.
- Request checks use the actual `ODPacket` and installed SFML serialization and
  verify the message type, tile count and coordinates. Map/entity endpoints and
  transport delivery are simulated; server execution and treasury credit in a
  running game remain manual acceptance items.
- 3,643 installed CEGUI/Ogre layout checks pass across 800x600 through 3840x2160
  and 80/100/120 percent scaling. They include the existing HUD matrix plus the
  new button's square geometry, hit target, currency resource, minimap access and
  production event binding/toggle with controlled game-state endpoints.
- The preceding creature-query behavior regression passes all 56 checks.
- Release compilation and runtime preparation pass in
  `build/windows/contextual-selling-build.log` and `contextual-selling-runtime.log`.
  The prepared executable is dated 18:16:46 local time; SHA-256
  `f09479c82a868637aa55a7978fdfdf66fd263036ce3a41d4e7c79090b192ead3`.
- Probe sources and results are in `build/windows/`:
  `generate-contextual-selling-probe.py`, `build-contextual-selling-probe.ps1`,
  `contextual-selling-probe-results.log` and `contextual-selling-ui-probe-results.log`.

Manual check: select Sell, inspect the displayed refund and sell one room tile
and one trap or door. Confirm only the clicked target is removed and its refund
is credited. Full visual/game-session acceptance remains open. No game was
launched or push made. The shared shadow checkout and normal index are preserved.
