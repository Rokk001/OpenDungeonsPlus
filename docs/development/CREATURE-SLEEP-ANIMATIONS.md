# Creature sleep transitions

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
