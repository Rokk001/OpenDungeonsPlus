# Downward hand strike on wall marking

## Existing implementation and requested change

The user requested a downward tool swing when clicking a wall, preserving the
accepted closed grip. Wall selection already validates eligible tiles and queues
one marking request after release. Preview, cancellation and invalid selection
return before that request. Previously, no hand animation was triggered there.

The existing renderer plays non-looping hand animations and restores the current
hover pose afterward. The change extends that lifecycle with a short closed-grip downward
strike for a confirmed marking request. The attached tool remains visible with
the existing grip material throughout the strike. Unmarking, sounds, gameplay
rules and authored animation clips retain their existing behavior.

## Implementation

`RenderManager.cpp` builds a three-keyframe `DigSwing` clip on the existing rig,
retaining every finger track from the accepted Dig pose and rotating the wrist.
The cycle takes 4/30 second and reaches its downward pose halfway through.
It reuses `setEntityAnimation` and `updateRenderAnimations` for interruption and
return to the latest contextual pose; it adds no timer, queue or input mode.
The tool and grip material remain active for the strike and are immediately
updated when another animation starts or the strike finishes.

`GameMode.cpp` invokes the strike only after queuing an eligible, confirmed
marking request. It does not run on preview, empty/invalid selection, cancellation,
release over an interface surface, repeated release events or unmarking.
The short animation does not delay the existing network request and does not
claim server acceptance of a request that may subsequently become invalid.

The work branch is `feature/hand-dig-animation`, based on the complete map
checkpoint `a4d1b0f5`, retaining held display `6b248742` and every prerequisite.
The shared checkout/index and newer local work are preserved; no push was made.

## Verification, September 6, 2026

- Actual renderer methods with installed Ogre assets: 876 checks pass, including
  the 77 held-display regression checks. They verify downward head movement,
  unchanged closed fingers, exact return to rest, 80/100/120 percent scaling,
  non-looping playback, repeated commands, contextual return, hand visibility
  and interruptions by Pickup, Drop and Slap.
- Actual release and wall-selection methods with domain adapters: 781 checks
  pass. They cover 64 combinations of release guards for mark/unmark and valid/
  invalid targets, 120-frame preview sequences, empty selections, unchanged
  packet fields and duplicate/secondary releases. The adapter dispatches only
  the digging action; this is not a full gameplay or network test.
- Rendered start, impact and return frames were inspected. The head moves
  downward while the shaft remains enclosed; rest and return coincide.
- Release compilation and runtime preparation pass. The headless resource check
  resolves the required shader header and all four internal shadow programs.
  Its first invocation omitted the required arguments; the corrected invocation
  completed successfully without changing production resources.

Logs under `build/windows/`: `hand-dig-probe-current.log`,
`hand-dig-input-results.log`, `hand-dig-release-build.log`, `hand-dig-runtime.log`
and `hand-dig-resources.log`. Source-derived probe generators use the same prefix.
Rendered frames are `build/reference-audit/hand-dig-{80,100,120}-{0..8}.png`.
The executable is dated September 6 at 22:21:21, 4,197,376 bytes, SHA-256
`60a29defc506b4940cb9699d407715c705b7c84596c2af36800a4ca1aab54f17`.

The assistant did not launch the game. User gameplay/visual acceptance of the
new strike remains pending; the static grip was already accepted separately.
The wider interface and action-feedback roadmap remains incomplete.

Version remains 0.7.1 because no release was requested. README controls and the
development index/build note are updated; the repository has no changelog.
