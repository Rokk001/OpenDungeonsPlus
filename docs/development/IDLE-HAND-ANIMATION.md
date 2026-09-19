# Interruptible idle hand effects

## Existing path and gap

`GameMode` already receives mouse/key events and selects the contextual hand pose
in `refreshActionFeedback`. `RenderManager` owns the rig, one-shot animations and
their return to the latest contextual pose. There is no inactivity timer or idle
effect selection; the shipped hand skeleton and assets contain neither a watch
glance nor a yo-yo effect. Extend these paths, without input simulation, gameplay
messages, new saved settings or dependencies.

The approved behavior is a random watch glance or yo-yo after thirty seconds
without input, immediately interrupted by any input. Keep selection as a small
effect list so additional authored effects can be added later. Suppress the
effect during held input, held objects, modal interaction, pause, loss of focus
and hidden-hand presentation. A stationary hover or selected build tool is not
input: allow the idle effect and restore that same context afterwards. Reuse the existing rig and
procedural prop rendering, keeping normal tools and all action animations intact.

Work branch: `feature/idle-hand-animation`, from full checkpoint `169cd6e6`.

## Implementation and verification

The controller tracks inactivity and held keys (including keys already down on
activation), recovers missed releases and cancels before dispatching mouse/key
input. Mode exit, hidden-hand toggles and renderer shutdown clear the effect.
The renderer randomly chooses one non-looped authored rig animation from
`IDLE_HAND_ANIMATIONS`; existing contextual poses, input targets and tool
attachments remain unchanged. A small procedural watch follows the wrist;
the spinning yo-yo and its string follow the animated fingertip. No external
assets, dependencies, gameplay packets, saved settings or version changes.

The production timer/eligibility fixture passes 2,125 checks, covering the
thirty-second boundary, recurrence, immediate cancellation, held/missed key
releases, mode exit, modal/focus/pause guards and deferred one-shot completion.
The installed Ogre rig/material fixture passes 415 checks including previous
hammer/pickaxe regressions, both deterministic random choices, actual wrist
motion, fingertip/string attachment, prop lifetime, natural completion and
restoration of selected tools. Settled start/middle/end previews were inspected;
the fixture advances Ogre's skeleton-cache frame before each pose sample.
The menu-hand fixture passes 100 checks; Alt and construction-input regressions
pass 128 and 560 respectively. A clean Windows Release build succeeds, followed
by an up-to-date incremental check and runtime preparation. The normal executable
matches the staged build: September 19 20:58:18, 4,874,752 bytes, SHA-256
`837A0A66FCBA05B1CAE09FF490D8628C580BD913CA9F0F2A8C5E8E073AA0D82F`.
Generated resources pass 32 checks. The game was closed during deployment and
was not launched by the agent. Ready for user testing: leave the hand untouched
for thirty seconds, observe either effect, then move/click/press a key to cancel;
the normal contextual action must remain usable. Visual acceptance is pending.
