# Defeat notification (server to client)

## Purpose

When a human player loses the dungeon heart, the server tells that player's
client to start the defeat sequence. Before this notification the client only
received chat text.

## Message

`ServerNotificationType::playerDefeated` (appended as the last enum value, so no
existing numeric value changes). Payload, in packet order:

| Field | Type | Meaning |
|---|---|---|
| `conquerorSeatId` | `int32_t` | Seat that dealt the final blow to the heart, or -1 if unknown |
| `heartTileX` | `int32_t` | X of the centre tile of the destroyed heart, or -1 if unknown |
| `heartTileY` | `int32_t` | Y of the centre tile of the destroyed heart, or -1 if unknown |

The client reads it in `ODClient::processServerNotification` and calls
`GameMode::startDefeatSequence(int32_t conquerorSeatId, int32_t heartTileX, int32_t heartTileY)`.
If the client is not in the game mode (menu, editor) the message is ignored.

## When it is sent

- From `Player::notifyNoMoreDungeonTemple`, once per player (guarded by `mHasLost`).
- To the defeated player only, and only if that player is human.
- Whether the whole team lost or only this player lost. Allies and enemies get nothing.
- After the existing chat text; chat text and keeper voice are unchanged.

`RoomDungeonTemple::takeHeartDamage` stores the conqueror seat id and the heart
centre tile on the owning `Player` (`recordHeartDestroyed`) when the heart's health
reaches 0, because the room is removed shortly afterwards.

## Client presentation

`GameMode::startDefeatSequence` runs the sequence described in [DEFEAT-SEQUENCE.md](DEFEAT-SEQUENCE.md).

## Verification limits

Covered by `source/tests/check_defeat_notification.py` and
`source/tests/check_dungeon_heart_combat.py`, which compile the production
functions against small mocks. The network round trip and the real client were
not run in a game.
