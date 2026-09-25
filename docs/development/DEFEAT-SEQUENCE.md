# Defeat sequence (client)

## Purpose

When the server reports that the local player lost the dungeon heart (see
[DEFEAT-NOTIFICATION.md](DEFEAT-NOTIFICATION.md)), the game mode plays a short
sequence instead of leaving the player with a frozen game screen. The game world and
the server keep running; only the local presentation and input change.

## Timeline

t = 0 is the moment `GameMode::startDefeatSequence` is called. All values live in
`DefeatSequenceSettings` in `source/modes/DefeatSequence.h`.

| Time (s) | What happens |
|---|---|
| 0 | The whole interface, the pointer, the hand and the creature texts disappear. The camera cuts (no flight) to a low oblique view of the heart. A small "CAM" marker is shown in the top right corner until the end. |
| 0 to 15 | Explosion effect at the heart (`particles/HeartExplosion.particle`), red tint over the scene, subtitle "Your dungeon heart has been destroyed." |
| 15 to 15.5 | The red tint fades out. |
| 15.5 to 18.5 | Swirl (`particles/DefeatSwirl.particle`) in the seat colour of the conqueror moves 14 tiles away from the heart, away from the camera. Skipped if the conqueror seat is -1 or not known to the client. |
| 19.5 to 28.5 | Linear fade to black. |
| 20.5 | Subtitle "That's it for today. Until next time." replaces the first one. |
| 29.5 | `GameMode::onDefeatSequenceFinished()` is called once. The screen stays black and the debriefing window opens on it (see below). |

If the heart position is -1/-1 the camera keeps its current target and only changes
height and angle.

## How it works

- `DefeatSequence` (header only) holds the state and the pure timeline functions
  (`phaseAt`, `redTintAlphaAt`, `blackAlphaAt`, subtitle and swirl windows). A second
  `start` is ignored. One slow frame advances at most 0.25 s so no phase is skipped.
- `GameMode::updateDefeatSequence` runs at the end of `onFrameStarted`. It hides every
  child window of the game sheet each frame (so windows the game shows again, such as
  chat or event messages, disappear again), sets the alpha of a red and a black full
  screen `OD/StaticText` window, sets the subtitle text and drives the effects.
- Effects use `RenderManager::rrCreateFreeParticleEffect`, `rrMoveFreeParticleEffect`
  and `rrDestroyFreeParticleEffect`. The swirl script has no colour of its own: the
  emitter colour is set to the seat colour at runtime, so there is one script for all
  seats.
- Input: `mouseMoved`, `mousePressed`, `mouseReleased`, `keyPressed` and `keyReleased`
  of `GameMode` are gated first by `DefeatSequence::blocksInput()` (true from the start
  on) and return before any game code (this also blocks Escape, hotkeys, selection and
  the camera), and `updateCameraControls` stops the camera. Until the debriefing is open
  nothing reaches the interface either. While it is open (`allowsGuiInput()`), the
  three mouse handlers still hand the event to the CEGUI context and then return: mouse
  move (and wheel) through `AbstractApplicationMode::mouseMoved`, button down and up
  through `injectMouseButtonDown/Up`, the same calls the normal path uses. The key
  handlers stay fully blocked, so Escape and hotkeys do nothing in the debriefing.
- When the mode is destroyed the effects and windows are removed, and the hand and
  pointer are made visible again for the next game.

## Debriefing

`onDefeatSequenceFinished` opens the debriefing once (`DefeatSequence::openDebriefing`
returns true only once). `GameMode::showDefeatDebriefing` loads
`gui/WindowDefeatDebriefing.layout` (picked up with the rest of `gui/`, no build list
to change), adds it to the game sheet above the black cover, hides the subtitle and the
"CAM" marker, and shows the pointer again (the hand stays hidden). The window shows:

- the title "Mission debriefing", the local player's nickname,
- "Level won: No",
- "Time elapsed: mm:ss" (h:mm:ss from one hour on), from `debriefingElapsedSeconds`:
  the client map's turn number divided by `ODApplication::turnsPerSecond`,
- an empty, hidden container `Panel/StatisticsArea` for the statistics table, so that
  the table can be added below the summary lines without a new layout,
- one confirm button (the existing tick icon).

Rank and score are not shown. `hideInterfaceForDefeat` skips the debriefing window and
`destroyDefeatWindows` (called from the destructor) destroys it.

### Leaving to the menu

The confirm button calls `DefeatSequence::confirmDebriefing` (true once, so a double
click acts once) and then `ModeManager::requestMainMenuWithSkirmishSubMenu()`. That
sets a flag on the `ModeManager` and requests `MENU_MAIN`, the same request as
`onClickYesQuitMenu`. `MenuModeMain::activate` consumes the flag
(`consumeSkirmishSubMenuRequest`) after resetting its windows and opens the skirmish
sub-menu the way its skirmish button does, the nearest equivalent of the reference's
single-player menu (there is no campaign in this fork).

Destroying the game mode is what disconnects: `GameEditorModeBase::~GameEditorModeBase`
disconnects the client and stops the server if this process runs one. So a defeated
client simply leaves its connection, while a defeated host who confirms the debriefing
stops the hosted game for every other player too. Server behaviour was not changed.

## Left out on purpose

- No loading screen, no voices for the two subtitle lines (text only; the server still
  plays the existing Lost voice), no rank or score.
- The reference G key that toggles the interface does not exist in this fork, so the
  interface is hidden by the sequence itself.
- The statistics table of the debriefing (a later task) and any restart, keep-watching
  or quit choice: the reference offers only the confirm button.

## Verification limits

`source/tests/check_defeat_sequence.py` compiles the real `DefeatSequence.h` and the
real driver functions of `GameMode.cpp` against small mocks and checks the boundaries
above, the one-shot guard, the swirl colour and the missing swirl for an unknown
conqueror, and that the input handlers start with the gate.
`source/tests/check_defeat_debriefing.py` covers the time text (0, 59, 60, 3599, over an
hour, invalid input), the input routing decision through the real handler guards, that
the finished hook opens the window once, and that confirming requests the main menu
once and sets the hand-over exactly once. The game was not run.
These parts are guesses that need a look in the game: the camera height and pitch
(`CAMERA_HEIGHT`, `CAMERA_PITCH`), the look of both particle scripts (both use the
existing `CombatSparks` material, so the fireballs are soft flares, not textured
flames), the tint strength, the swirl direction and shape, the subtitle position and
font, the "CAM" text standing in for the camera symbol, and whether the `Ring`
emitter and the runtime emitter colour behave as expected in the used Ogre version.

For the debriefing these are guesses that need a look in the game: the size, position,
colours and fonts in the layout (a dark panel stands in for the stone corridor of the
reference), the h:mm:ss form for games over an hour, that the tick button renders with
the used button type, that clicks reach the button through the black cover windows, and
that the main menu shows its skirmish sub-menu correctly when entered this way (the
mouse position is not moved onto a button, as it is at the first start).
