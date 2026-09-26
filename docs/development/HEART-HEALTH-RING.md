# Dungeon heart health ring

## Behaviour

The ring of the heart badge in the top-left corner (next to the mana number) shows the
health of the local player's dungeon heart. It is split into six segments by spokes that are part
of the silver rim, the first spoke at the top. One segment stands for one sixth of the health and
the segments fill green clockwise from the top: at 17 % one segment is green, at 50 % three. A
segment that is only partly covered is filled only in part, clockwise over the covered share. The
unlit part stays as a dark groove. A destroyed heart (fraction 0) shows no green.
While the heart is under attack the badge glows magenta behind the silver heart; the glow is
switched off after 3 seconds without a further message and never shows on a destroyed heart.

`healthFraction` is the remaining heart health divided by the health of an undamaged heart,
`RoomDungeonTemple::getHeartMaxHP` (`getHeartHealthFraction`), a fixed 10000. A living heart
heals 2.5 per second up to that maximum (`RoomDungeonTemple::doUpkeep`). The gold badge is not changed.

## How it works

- The badges are still generated procedurally at start-up by `createNavigationImages` in
  `source/render/Gui.cpp`, now through `drawBadgePixels`. `Gui::updateHeartBadge` draws the
  heart badge again and writes it with `blitFromMemory` into the existing texture (`ManaBadge`),
  so the layout, the image scaling and the resource strip are unchanged; only the badge tooltip
  reads "Dungeon heart health bar" instead of "Your Mana". It first
  used `loadFromMemory`: the CEGUI Ogre renderer then makes a new Ogre texture, while the badge
  window keeps drawing the Ogre texture stored in its cached geometry, so the ring never moved.
- The rules (segments and spokes, one-point step, glow timer, percentage) are in `source/game/HeartHealthRing.h`.
- New server notification `heartHealth` (last value of `ServerNotificationType`):
  `float healthFraction`, `bool underAttack`, `double heartHP`, `double heartMaxHP`, sent to the
  owning human player only.
- `notifyHeartHealth` in `source/network/ODServer.cpp` runs once per turn for every client. It
  sends at once when the fraction changed by at least one percentage point since the previous
  message, when the heart is destroyed, and once for a client that has not been told anything
  yet, which covers a new game and a loaded game. A change of the whole heart HP alone (the
  exact value of the tooltip, which changes every turn while the heart heals) is sent at most
  once per second (`HeartHealthRing::isHpMessageDue`, measured in turns with
  `ODApplication::turnsPerSecond`). `underAttack` is true when the health fell since the
  previous message, so healing never lights the glow.
- `ODClient` keeps the state (`HeartHealthRing::BadgeState`, including the exact HP set with
  `setPoints`), resets it on `clientAccepted`, and `GameMode::onFrameStarted` runs the glow
  timer, redraws the badge when needed and sets the info line of the badge icon (its
  `ContextHelp` text) to "Dungeon heart at 17 %. Right-click moves the view to the heart."
  The percentage is the current HP divided by the maximum HP, rounded to the nearest whole
  percent (`HeartHealthRing::healthPercent`). A right-click on the badge calls
  `GameMode::focusRoom` for the dungeon heart, which flies the camera to the local player's
  living heart (`CameraManager::flyTo`) and does nothing when there is none.

## Verification and limits

`source/tests/check_heart_health_ring.py` compiles the production rules, `notifyHeartHealth`,
the heart health and save methods and `drawBadgePixels` into a fixture. It checks the segments
and spokes for 0, 17, 50 and 100 percent, a partly filled segment, the percentage text, clamping, the one-point rule, the human-owner-only delivery, the
payload order, the once-per-second limit for HP-only messages, healing, the glow timer, a save and load round trip and the wiring in the client and the
game mode. On Windows, application control sometimes blocks freshly compiled fixtures (error
4551); the script retries four times.
`source/tests/check_heart_badge_texture.py` runs the real `updateHeartBadge` with the CEGUI Ogre
renderer in a hidden window: it reproduces that `loadFromMemory` replaces the Ogre texture, and
reads back that the update keeps the texture and holds the ring of the new health, with the
segments for 0, 17, 50 and 100 percent and a partly filled segment.

Not verified: how the badge looks in the running game. The magenta glow strength and the
dark groove colour are estimates. Hits smaller than one percentage point in total are not
sent, so a very slow attack lights the glow only at each full point.
