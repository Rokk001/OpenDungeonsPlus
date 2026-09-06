# Small-creature shadow depth

Work branch: `fix/rat-shadow`, based on complete fork checkpoint `11949bc2`.

## Existing path and diagnosed gap

Creature entities already use the shared world-shadow path and cast shadows by
default. The Rat material uses the same integrated depth-shadow sampling as the
other creature materials; there is no Rat-specific shadow disable or alternate
rendering path.

An isolated render with the real animated `Rat.mesh` confirms that it reaches
the shadow map, but its world bounds extend only about 0.28 units above the
floor. The existing 16-bit depth texture therefore retains much less visible
coverage than a full-height creature at gameplay camera distances. A 24-bit
depth texture increases Rat coverage from 78 to 176 relative-shadow pixels in
the distant-camera case and from 332 to 526 in the close case without changing
the projection, light position, colour, attenuation or creature scale.

Use the existing renderer setting with a 24-bit depth-stencil texture and match
the receiver comparison tolerance to one step of that texture. This corrects
the precision loss while preserving the current creature creation and lighting
paths.

## Verification

The real GL3Plus render path passes Rat coverage on all eight existing receiver
materials over five camera and light placements, for 40 receiver checks and 80
repeated off/on restoration checks. All six focused Rat placements pass, and 64
existing Wizard, Dragon and Slime receiver cases remain free of stray shadow
pixels. The renderer accepts the 24-bit depth-stencil texture and produces the
expected shadow texture in each run.

Windows Release compilation and runtime preparation pass. The executable is
dated September 6, 2026 at 23:46:31, is 4,206,080 bytes and has SHA-256
`964df352e4e30a568641769eed90ab22a404ce4b15db9fa7dba15420a7c625de`.
The game was not launched by the assistant. On September 6, 2026, the user ran
the corrected build and confirmed that the Rat shadow is fixed.

Version remains 0.7.1 because this is a rendering bug fix rather than a release.
The root README needs no change and the repository has no changelog file.
