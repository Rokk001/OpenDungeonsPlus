# Creature sleep transitions

## Bed alignment correction

Combined model measurements show that resting poses reach or cross floor level
while mattresses are elevated; several clips also translate their root far from
the assigned bed centre (the skeleton reaches y=2.21). The previous fixture had
no beds and therefore missed this. Align the final posed geometry with the
actual rendered bed's central support surface and orientation, blending the
placement during entry and restoring the normal transform on interruption.
Keep creature size, bed allocation, recovery and accepted drop/get-up unchanged.
The renderer now samples the actual deformed rest pose, ray-tests the bed centre
for its mattress height (excluding taller posts), and blends both alignment and
orientation. Missing upright death fallbacks lie down instead of standing in
the bed. Placement is resolved after final walk positioning; waking preserves
the newly requested facing and restores original ground position and scale.
All 3,049 real-Ogre checks pass, covering all 33 models, both bed rotations,
level-1/30 scales and hand/drop/feed regressions. Combined bed renders were
inspected, and Release compilation/runtime preparation pass. Natural tails or
wings may extend past the mattress; creatures are not shrunk to conceal that.
User visual acceptance remains pending.

## Arrival follow-up

The client completes its walk queue by starting the queued sleep state before
applying the final interpolated position. The unconditional sleep cancellation
in `rrMoveEntity` therefore canceled a newly started sleep sequence on arrival.
The expanded real renderer probe reproduces this for all 33 meshes. Cancel there
only while the creature still has an active walk queue; ordinary walk-animation
changes also retain their existing cancellation. Final arrival positioning must
not cancel sleeping. Before the correction, all 33 arrival checks failed; after
the correction, all 2,451 renderer checks pass, including active-walk cancellation
and the retained animation regressions. Release compilation and runtime
preparation pass. Logs: `build/windows/held-display-probe-sleep-arrival-before.log`,
`build/windows/held-display-probe-sleep-arrival-after.log` and
`build/windows/sleep-arrival-build.log`. User game acceptance remains pending.

## Existing path and scoped change

The sleep action already walks to the assigned dormitory bed, orients the
creature and applies its existing recovery values. Walking uses a separate
pushed action, preserving the first active sleep turn on arrival. The renderer
selects Sleep directly, falling back to Die when absent; authored Sleep_Start
clips are unused and there is no transition into a resting pose.

Reuse authored sleep-entry clips where present. Otherwise generate a smooth
skeletal transition from Idle to the final sleeping pose or the existing
grounded fallback pose, without playing the death sequence. Subtle breathing
continues until the normal action changes. Cancel the presentation on movement,
pickup, death and teardown. Recovery, bed selection and duration stay unchanged.

## Verification

The isolated real Ogre renderer passes 2,385 checks across all 33 meshes,
including existing hand, drop, get-up, combat and feeding regressions. Sleep
checks cover the actual skeletal transition and midpoint translations, authored
entry selection, sustained rest, and cleanup on walking, pickup and destruction.
The slime changes bone scale rather than rotation or translation; the motion
check includes that authored deformation. Representative beginning, midpoint
and resting renders were inspected. Models retain their authored resting pose,
including the Cultist's upright bowed pose.

Windows Release compilation and runtime preparation pass, after adding the
required entity-type header. Logs: `build/windows/sleep-build-final.log` and
`build/windows/held-display-probe-sleeping-final.log`; isolated renders are
`build/reference-audit/sleep-*.png`. Manual game appearance and bed alignment
remain for user testing. No game was launched and recovery rules are unchanged.
