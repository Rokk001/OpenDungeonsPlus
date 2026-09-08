# Worker creation effect

## Scope

Workers created by the summon-worker spell now appear inside one short
turquoise-green spark burst. Existing workers, map-loaded workers and ordinary
creature spawning remain unchanged.

## Implementation

The spell attaches a finite presentation-only particle effect before placing the
new worker. The existing entity add packet carries that effect to every client
with vision, and the existing renderer attaches it after creating the creature
mesh.

Creature upkeep distinguishes presentation-only particles from gameplay creature
effects. Save serialization counts and writes only gameplay creature effects, so
the transient creation burst cannot alter creature behaviour or saved-game data.
The dedicated particle script uses the existing flare texture and material path;
no new dependency or texture is required.

## Verification

The headless OGRE particle probe loads the production material and particle
scripts, creates the particle system and verifies its one emitter, two affectors,
bounded quota, compact spark dimensions, dense 0.2-second emission and 0.8-second
particle lifetime. All 10 checks pass.

The user confirmed the visual result in game on September 8, 2026. Release
compilation and runtime preparation also pass.

Version 0.7.1 remains unchanged because no release was requested. The README is
unchanged because the summon-worker control and gameplay rules did not change.
