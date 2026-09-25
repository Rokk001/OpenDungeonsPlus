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
| 0 | The whole interface, the pointer, the hand and the creature texts disappear. The camera cuts (no flight) to a low oblique view of the heart. A small camera symbol is shown in the top right corner until the end. |
| 0 to 0.8 | A client-only copy of the heart stands on the platform; it shakes, pulses and its core glows red, more and more. |
| 0.8 | The heart bursts: the copy disappears, flash, fireballs, green sparks and smoke start (see "Heart burst"), the rubble flies out and lands on the platform within 1 s. |
| 0 to 15 | Red tint over the scene, subtitle "Your dungeon heart has been destroyed.". The burst effects are removed at 15 s; the rubble stays until the end. |
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
  `start` is ignored. The timeline follows the wall clock: `start` stores a
  `std::chrono::steady_clock` time and `advanceTo(now)` sets the elapsed time to now minus
  that start. `GameMode::onFrameStarted` runs twice per frame in this fork (from
  `ODFrameListener::frameStarted` and from `ModeManager::update`), so summing frame times
  ran the sequence at double speed (29.5 s took 15 s); with the clock, repeated calls in a
  frame change nothing and a long frame moves the timeline by exactly its length.
- `GameMode::updateDefeatSequence` runs at the end of `onFrameStarted`. It hides every
  child window of the game sheet each frame (so windows the game shows again, such as
  chat or event messages, disappear again), sets the alpha of a red and a black full
  screen `OD/StaticText` window, sets the subtitle text and drives the effects.
- Particle effects use `RenderManager::rrCreateFreeParticleEffect`, `rrMoveFreeParticleEffect`
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

## Heart burst

The server removes the heart object one turn before it reports the defeat (in the log of a test
game: `removeEntity` at turn 10, `playerDefeated` at turn 11), so the camera used to cut to an empty
platform. The burst is therefore built on the client only:

- `RenderManager::rrCreateDefeatHeart` places a copy of the real heart: an entity of
  `DungeonTempleObject.mesh` at the heart tile, no turn, scale 1, as `rrCreateRenderedMovableEntity`
  places the real one. Its three materials are clones (`DefeatHeart_<name>`), so that
  `rrUpdateDefeatHeart` can shift their self-illumination towards red without touching other hearts.
  Until 0.8 s it shakes sideways (up to 0.07 tiles), pulses in size (up to 8 %) and glows.
- At 0.8 s `GameMode::startDefeatBurst` removes the copy, starts the four systems of
  `particles/HeartExplosion.particle` 1 above the floor and creates the rubble. `HeartExplosion`:
  about 45 fireballs thrown out and up at once, then fewer for 3 s and a few embers until about 12 s;
  they fall under gravity, stop on the floor (`DeflectorPlane`) and fade from yellow to dark red.
  `HeartExplosionFlash`: a short bright glow. `HeartExplosionSparks`: turquoise-green sparks, a fast
  burst and then sparks rising for 12 s. `HeartExplosionSmoke`: dark smoke for 2.5 s. Every emitter
  has a duration, so the burst is strongest at first and dies out. The added (additive) particles
  fade by colour; their alpha has no effect with additive blending.
- The rubble is 18 pieces of a small procedural shard mesh (`DefeatHeartShard`, an irregular
  five-sided slab made with `Ogre::ManualObject`) with the heart's own shell material `Stacheln`.
  `DefeatHeartBurst::buildRubbleLayout` (`source/modes/DefeatHeartBurst.h`) places them always the
  same way within 0.85 tiles of the centre, higher and more tilted in the middle of the pile, with
  varied turn and size. `rubblePoseAt` flies every piece from the heart's middle on an arc to its
  place, turning, within 1 s after the burst.
- New assets, made for this project: `materials/textures/DefeatFireball.png` (a soft round glow
  drawn by a small Pillow script) and `materials/scripts/DefeatSequence.material` (`DefeatFireball`,
  and `DefeatSmoke` with the existing `Smoke15Frames.png`). The sparks use the existing
  `CombatSparks` material.
- Everything is found by name, not kept as a pointer. `stopDefeatEffects` removes the burst effects,
  the swirl, the copy with its cloned materials, and the rubble with its mesh; it runs from the
  finished hook (the screen is black by then) and from the destructor.

The swirl was nearly invisible before: its `Ring` emitter had no `depth`, and Ogre's area emitters
default to 100, so the ring spread its particles over 100 units up and down (bounding box z from -50
to +50 in the render check). It now has a depth of 0.1, stays low (the camera sees only about 1 above
the floor a few tiles behind the heart) and fades by colour.

## Debriefing

`onDefeatSequenceFinished` opens the debriefing once (`DefeatSequence::openDebriefing`
returns true only once). `GameMode::showDefeatDebriefing` loads
`gui/WindowDefeatDebriefing.layout` (picked up with the rest of `gui/`, no build list
to change), adds it to the game sheet above the black cover, hides the subtitle and the
camera symbol, and shows the pointer again (the hand stays hidden). The window shows:

- a stone surface: the tiled `ODHudSurface/Stone` image (the one the HUD navigation frame
  uses) fills the whole screen, slightly dimmed, and the panel is the same stone, dimmed
  further so the white text stays readable. Both are `OD/StaticImage` windows in the layout,
  darkened with `ImageColours`,
- the title "Mission debriefing", the local player's nickname,
- "Level won: No" or "Level won: Yes",
- "Time elapsed: mm:ss" (h:mm:ss from one hour on),
- the statistics table in `Panel/StatisticsArea` (a scrollable pane, hidden until it has
  content): one row per statistic, one column per seat, each number in the seat colour,
- one confirm button (the existing tick icon).

The full screen stone `Background` has `RiseOnClickEnabled` off. CEGUI raises a clicked
window in front of its siblings, so without it a click on the stone beside the panel put
the opaque stone in front of the panel: a grey screen with the button covered, and no way
out because keys are blocked during the defeat.

"Level won" and the time come from the statistics packet (`ODClient::hasLevelStatistics()`,
a snapshot taken by the server at the moment of the defeat) when it was received. Without
a packet the client's own values are used: not won, and `debriefingElapsedSeconds`, the
client map's turn number divided by `ODApplication::turnsPerSecond`.

The table has the rows Enemy keepers defeated, Enemy creatures killed, Heroes destroyed,
Rooms captured, Items made and Creatures converted. It is built from the statistics by
the pure function `buildDebriefingTable` in `source/modes/DebriefingTable.h`, and
`GameMode::fillDefeatStatistics` creates the text windows. The counters, the packet and
the details of the table are described in [LEVEL-STATISTICS.md](LEVEL-STATISTICS.md).

Rank and score are not shown. `hideInterfaceForDefeat` skips the debriefing window and
`destroyDefeatWindows` (called from the destructor) destroys it.

### Camera symbol

The symbol in the top right corner is an `OD/StaticImage` window (`DefeatCameraMarker`, 40 by
40 pixels, tinted red through `ImageColours`) showing `OpenDungeonsIcons/CameraIcon`. The
project had no camera, eye or film icon, so a new white 32 by 32 glyph was drawn (a small
script with Pillow, not part of the repository) into the free cell at x 0, y 32 of
`gui/ODIcons.png` and registered in `gui/ODIcons.imageset`. The whole `gui` directory is
installed, so nothing else lists it.

### Leaving to the menu

The confirm button calls `DefeatSequence::confirmDebriefing` (true once, so a double
click acts once) and then `ModeManager::requestMainMenuWithSkirmishSubMenu()`. That
sets a flag on the `ModeManager` and requests `MENU_MAIN`, the same request as
`onClickYesQuitMenu`. `MenuModeMain::activate` consumes the flag
(`consumeSkirmishSubMenuRequest`) after resetting its windows and opens the skirmish
sub-menu the way its skirmish button does, the nearest equivalent of the reference's
single-player menu (there is no campaign in this fork).

The main menu of this fork is a flat picture (`MainMenuBackground.png` on a full screen
rectangle, with animated fire, mist and ember overlays, see `RenderSceneMenu`), not a 3D
scene, and it has no camera path or intro flight to reuse. The reference flies the camera
through a 3D corridor; that cannot be reproduced here, so `MenuFlight` (`source/render/MenuFlight.h`)
approximates it as a zoom: for 3 seconds the picture (and with it the overlays) starts at 1.6
times its normal size around its centre and settles to exactly the normal size, slowing down
towards the end (cubic ease-out). `RenderSceneMenu::updateMenu` applies the scale to the
rectangle corners; the frame time step is clamped to 0.25 s.

The flight runs only when the hand-over flag was set: `MenuModeMain::activate` then hides the
menu buttons, starts the flight (`ODFrameListener::startMainMenuFlight`) after the scene was
created, and `MenuModeMain::onFrameStarted` opens the skirmish sub-menu when the flight is no
longer active. So the sub-menu appears at the end of the flight, and since no menu control is
visible during the flight, input to the menu is effectively ignored. Every other way into the
main menu is unchanged. Freeing the menu scene stops a running flight.

Destroying the game mode is what disconnects: `GameEditorModeBase::~GameEditorModeBase`
disconnects the client and stops the server if this process runs one. So a defeated
client simply leaves its connection, while a defeated host who confirms the debriefing
stops the hosted game for every other player too. Server behaviour was not changed.

## Left out on purpose

- No loading screen, no voices for the two subtitle lines (text only; the server still
  plays the existing Lost voice), no rank or score.
- The reference G key that toggles the interface does not exist in this fork, so the
  interface is hidden by the sequence itself.
- The reference rows mana saved, creatures commanded and creature level trained: their
  meaning is not established, so they are not shown (see LEVEL-STATISTICS.md).
- Any restart, keep-watching or quit choice: the reference offers only the confirm
  button.

## Verification limits

`source/tests/check_defeat_sequence.py` compiles the real `DefeatSequence.h` and the
real driver functions of `GameMode.cpp` against small mocks and checks the boundaries
above, the one-shot guard, the swirl colour and the missing swirl for an unknown
conqueror, and that the input handlers start with the gate.
`source/tests/check_defeat_debriefing.py` covers the time text (0, 59, 60, 3599, over an
hour, invalid input), the input routing decision through the real handler guards, that
the finished hook opens the window once, that the packet values are used for "Level won"
and the time (and the client values without a packet), the table rows and the windows
made from them, and that confirming requests the main menu once and sets the hand-over
exactly once. The game was not run.
`source/tests/check_defeat_heart_burst.py` checks the pure functions of `DefeatHeartBurst.h`
(timing, layout inside the platform, determinism, settle animation) and runs the real driver of
`GameMode.cpp` with the real render functions, models, materials and particle scripts in a hidden
Ogre window: it counts changed, warm and green pixels at chosen times, writes the pictures to
`build/defeat-burst-preview/`, and checks that nothing is left after the end and after an early stop.
`source/tests/check_defeat_camera_culling.py` runs the real camera cut and the real
`CullingManager::computeIntersectionPoints` with the Ogre library: with pitch 60 and the game
camera's 45 degree field of view every corner ray reaches the floor (with the former 68 the two
upper rays did not, which filled the log and left stale culling corners).
`source/tests/check_defeat_debriefing_click.py` clicks the real layout with the CEGUI library.
These parts are guesses that need a look in the game: the camera height and pitch
(`CAMERA_HEIGHT`, `CAMERA_PITCH`), the whole look of the heart burst (shake, glow colour, the
sizes, colours, rates and lifetimes of the four burst systems, the smoke, the shard shape, its
material and the pile layout are guesses modelled on the reference recording; the fireballs are soft
glows, not textured flames; the render check has no walls, map lights or red tint), the tint
strength, the swirl direction and shape, the subtitle position and font, and the size, tint and look
of the drawn camera glyph.

For the debriefing these are guesses that need a look in the game: the look of the
statistics table (column widths, row height, seat colours, scrolling), the size, position,
colours and fonts in the layout (the dimmed stone surface stands in for the stone corridor
picture of the reference, and the tint values are guesses), the h:mm:ss form for games over an hour, that the tick button renders with
the used button type, that clicks reach the button through the black cover windows, and
that the main menu shows its skirmish sub-menu correctly when entered this way (the
mouse position is not moved onto a button, as it is at the first start).
For the flight: that the zoom looks like a flight at all (start scale 1.6, duration 3 s, easing
are guesses), that the overlays follow the zoom without a visible jump at its end, and that
the buttons and the sub-menu appear correctly afterwards. The flight tests
(`source/tests/check_defeat_menu_flight.py`) cover the timing and path functions (start, end,
clamping, restart only after the end), the frame hook that opens the sub-menu once, the
hand-over flag being consumed once, that the camera symbol is an image window with an existing,
non-empty icon, and that every image the layout names exists in the imagesets.
