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
| 29.5 | `GameMode::onDefeatSequenceFinished()` is called once. It only logs for now; the debriefing window is the next step. The screen stays black and input stays blocked. |

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
  of `GameMode` return before doing anything while the sequence is started (this also
  blocks Escape, hotkeys, selection and the mouse wheel), and `updateCameraControls`
  stops the camera.
- When the mode is destroyed the effects and windows are removed, and the hand and
  pointer are made visible again for the next game.

## Left out on purpose

- No loading screen, no voices for the two subtitle lines (text only; the server still
  plays the existing Lost voice), no rank or score.
- The reference G key that toggles the interface does not exist in this fork, so the
  interface is hidden by the sequence itself.
- The debriefing window and the way back to the menu are a separate task.

## Verification limits

`source/tests/check_defeat_sequence.py` compiles the real `DefeatSequence.h` and the
real driver functions of `GameMode.cpp` against small mocks and checks the boundaries
above, the one-shot guard, the swirl colour and the missing swirl for an unknown
conqueror, and that the input handlers start with the gate. The game was not run.
These parts are guesses that need a look in the game: the camera height and pitch
(`CAMERA_HEIGHT`, `CAMERA_PITCH`), the look of both particle scripts (both use the
existing `CombatSparks` material, so the fireballs are soft flares, not textured
flames), the tint strength, the swirl direction and shape, the subtitle position and
font, the "CAM" text standing in for the camera symbol, and whether the `Ring`
emitter and the runtime emitter colour behave as expected in the used Ogre version.
