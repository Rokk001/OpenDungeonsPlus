# Interruptible idle hand effects

## Match the empty-hand angle, September 20

The user requests that both watch and yo-yo effects keep the ordinary empty
hand's angle, instead of turning into a different presentation. The existing
generator starts from the empty-hand pose, but replaces the wrist rotation with
a view-based target (-25 degrees for the watch and roughly -115 for the yo-yo).
The props already follow their existing wrist/fingertip attachment paths and
the yo-yo has its own spinning/drop animation; no new effect is needed.

On `fix/idle-hand-angle`, created from complete hammer checkpoint `0a7a37ca`,
retain the sampled empty-hand wrist rotation for every effect frame, leaving
finger poses, props, timer, random selection and interruption behavior unchanged.
Replace the earlier test requiring a large wrist turn with full-orientation
equality against the normal empty hand throughout both effects.

The new orientation assertion fails against the previous wrist turns and passes
after removing only those turns. All 3,690 real-asset checks pass, comparing both
effects directly with the normal empty-hand wrist at thirteen time samples and
retaining the hammer/contact, tool, prop attachment and cancellation regressions.
Isolated empty-hand, watch and yo-yo previews were inspected; the props remain
visible and the finger/prop animations are unchanged.

Release compilation, runtime preparation and 32 resource checks pass; normal and
staged executables match: September 20 08:38:12 Europe/Warsaw, 4,871,680 bytes,
SHA-256 `8474DC7A481512096AB6CD3A7C9FB990449FCB9092BBADA1BF06A942286AA1CD`.
The normal executable also retains the separate hammer-impact alignment fix.
No game was launched or stopped, no Windows security settings were changed,
and nothing was pushed. Both presentation follow-ups await user retest.
README describes the same existing effects; no version, input, saved-setting
or network change is required.

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
