# Creature hand drop

## Scope

A short right click still drops only the front hand entry. Holding the right
button for 350 milliseconds while at least two creatures are held sends one
request for all held creatures; non-creature hand entries are not included.
Left-click pickup and editor input remain unchanged.

## Existing path and integration

Pickup already inserts new entries at the front of the hand, plays the authored
pickup clip and attaches the visible creature to the animated hand grip. The
single-drop request already identifies that front entry across the client and
server boundary.

The hold path reuses that ordering and adds one appended network request carrying
the exact identities of every held creature. The server resolves and validates
the entire batch before changing the hand, then uses the existing authoritative
drop path for every member. Existing single-drop packets and replies are
unchanged.

Each confirmed creature is restored to the world two units above its approved
ground position and accelerates downward for 350 milliseconds while the existing
hand drop clip plays. Its neutral pose remains stable during the fall. At ground
contact it starts its existing non-looping death pose when that clip finishes in
a lying position. The two configured models without a usable lying death pose
instead rotate during the fall and are aligned to the ground, so every creature
finishes visibly lying down. The original orientation and idle animation return
through a 350-millisecond get-up transition when the authoritative stun counter
expires. Creatures with a usable lying clip play it backward; the two fallback
models rotate smoothly from their grounded pose to their original transform.

## Verification boundary

The source-derived protocol regression passes 233 checks covering front-entry
selection, intervening hand rotation, complete batch delivery and rejection
without partial drops. The source-derived input probe passes 10 checks for the
hold threshold, short release, one-creature fallback and cancellation paths. The
real Ogre lifecycle probe passes 378 checks, including all 34 configured creature
definitions (33 distinct meshes) and five concurrent accelerated falls from hand
height to the ground. Its isolated start, midpoint and grounded render sequence,
six grounded atlases and six get-up midpoint/final atlases covering all distinct
meshes were visually inspected.
The Windows Release target compiles successfully and runtime preparation passes;
CTest has no registered tests. The implementation agent did not launch the game,
so the final combined in-game appearance still requires the documented manual
check.

Version 0.7.1 remains unchanged because no release was requested. The root README
is unchanged because the feature uses the existing mouse controls.
