# Creature portrait clipping after interface rendering

The held-creature display check exposed an existing offscreen-rendering failure:
portraits created after a GUI draw could retain only a small part of the model.
The isolated renderer reproduced this after drawing a square icon; Lizardman's
portrait then failed the visible-image check. Generating the same 33 portraits
without the intervening GUI drawing passed.

The installed CEGUI Ogre geometry buffer enables scissoring for clipped batches.
Its renderer restores the preceding viewport, but does not disable that clip.
OGRE GL3Plus's full-target buffer clear leaves an existing scissor test active.
Consequently the next portrait can inherit an unrelated window-sized clip.

The correction disables the scissor test immediately before updating the
isolated portrait render target. The next GUI batch sets its own clipping again.
Mesh framing, artwork, portrait caching and normal GUI clipping remain unchanged.
This is a separate rendering prerequisite for the held-creature display.

## Verification

The same isolated Ogre/CEGUI probe now renders all 33 configured creature meshes
with GUI drawing interspersed between portrait creation. It checks visible
pixels, cached texture sharing and cleanup of temporary scene/material resources.
The preceding implementation fails on Lizardman after the first GUI draw;
the corrected implementation passes. Logs are
`build/windows/held-icon-first-failure.log` and `held-icon-preview-results.log`.
The initial failed assertion was obscured by the probe's exception-cleanup crash;
a local case handler exposed it without changing game error handling.

The Windows Release build and runtime preparation pass; see [BUILDING.md](BUILDING.md)
for the prepared executable. No game was launched. This correction belongs on
`fix/creature-portrait-clipping`, separately from the held-creature presentation.

Version remains 0.7.1 because no release was requested. README controls are
unaffected and no changelog exists; this note and the development index record
the rendering correction.
