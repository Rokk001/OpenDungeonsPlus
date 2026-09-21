# Crypt worker departure

The fixed delivery offset can land on a wall statue. The fine navigation finds
a corner in which the worker can arrive, but its asymmetric walking bounds
overlap the statue when turning toward any terrain-valid exit. Actual game logs
and a production-navigation fixture reproduce the failure; the carrying action
itself is correctly removed. Corpse animation is not a movement lock.

Reuse each crypt spot's existing reservation, but choose an unoccupied adjacent
tile belonging to the same crypt for delivery. Prefer the existing lower tile
when free, then the other cardinal neighbors; never reserve a spot without a
free neighbor. Check the same tile when transport ends, retaining interruption
handling and the existing corpse/rotting transition. No collision relaxation,
teleportation, speed change, corpse timing or other room behavior is required.

September 21 verification: the focused navigation fixture previously completed
6,958 checks without failures, including 48 collision-safe delivery/departure
cases across four rotations and 16 oversized-dwarf negative controls; the latest
unchanged rerun compiled but Windows application control blocked execution
(4551). The retained delivery/decay fixture log proves 12,593 checks passed.
Release compilation, deployment hash comparison, runtime preparation and all
32 resource checks pass. No game was launched; user gameplay acceptance remains
open, and the separately reported missing visible decomposition is not fixed here.

This local correction needs no release version or release changelog update;
the development index and build evidence are updated, with no top-level README
change required and no remote publication.
