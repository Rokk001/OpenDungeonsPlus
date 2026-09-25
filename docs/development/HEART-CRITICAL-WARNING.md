# Dungeon heart critical-condition warning

## Behaviour

When an enemy hits a dungeon heart whose health is at or below 11 % of its total
durability, the heart's owner receives one event message:
"Your dungeon heart is in critical condition!"

The check runs on the server in `RoomDungeonTemple::takeHeartDamage`, after the
damage is applied. The message is a `chatServer` notification of type
`majorGameEvent`, sent the same way as the "You lost" and "You Won" messages.

## Rules

- **Threshold: 11 %.** It was measured on the reference recording of the original
  game: the warning came at the first hit while the heart was already at about
  10-11 % health.
- **One warning only.** A flag (`mCriticalWarningSent`) is set at the first hit at
  or below the threshold. The message is never repeated before the heart is
  destroyed. The flag is not saved, so a reloaded game with an already critical
  heart warns once more at the next hit.
- **No warning on the killing hit.** If the heart reaches 0 in the same hit, the
  defeat flow handles it.
- **Recipient.** Only the owning seat's player, and only if that player is human
  and has not lost. Allies and enemies get nothing. Nothing is sent in the editor.
- **Text only.** The original keeper voice line ("Das Herz eures Dungeons ist in
  einem kritischen Zustand.") is not recorded yet, so no sound is played.

## Verification and limits

`source/tests/check_dungeon_heart_combat.py` compiles the production
`takeHeartDamage` into a fixture with stubbed room, seat, player and network
classes. It checks: no warning above 11 %, exactly one at or below it (including a
first hit while already below), no repeat, no warning on the killing hit or for a
non-human, lost or absent owner, and none in the editor.

Not verified: an actual game session (real network delivery, chat display) and a
full Release build. `RoomDungeonTemple.cpp` was only syntax-checked with `cl /Zs`.
On Windows, application-control policy sometimes blocks freshly compiled fixtures
(error 4551); run the check again if that happens.
