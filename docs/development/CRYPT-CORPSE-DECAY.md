# Crypt corpse presentation

The crypt accepts only dead creatures and starts a server-side rotting counter
after transport, but never requests a lying/decay animation at that transition.
The client release handler only reattaches the scene node and changes position;
it does not establish a final corpse pose. Mesh creation defaults to Idle, while
animation restoration depends on the transported entity's prior state.

Request a dedicated decay state on successful crypt placement, reusing the
existing animation packet and final death/drop poses, including meshes with no
usable death pose. Add slow corpse settling and an animated fly swarm; neither
room capacity, decay reward, vampire spawning nor research timing changes.
Removing a crypt spot returns the corpse to its ordinary death state and removes
the decay presentation. Destruction, pickup and animation replacement clean up
the swarm. Existing save behaviour (corpses are collected again) is retained.

The server animation is updated explicitly: `clearDestinations` alone only sends
the requested end state to existing clients. Visibility restoration applies the
heading before the corpse tilt and preserves its ground height when position is
restored. The effect follows position updates and is removed on pickup as well.

The settling animation uses the base configured decay duration; research still
controls the server's actual corpse-removal time without changing its rewards.

Validation: the focused production-code fixture compiles, but Windows application
control blocks its executable with error 4551 before any checks run. Consequently
there is no runtime or visual pass. The fixture covers crypt delivery/interruption,
spot removal, every configured skeleton's final pose and settling keys, shared
animation reuse and particle-template parsing. Game appearance remains for the
user to test after deployment; release compilation is recorded separately below.

Windows Release compilation passed on September 20 in `build/review-followups`
(`crypt-final-build.log`). The normal executable has not been replaced.

This is a local feature, not a release: the development index is updated without
a version bump or release changelog entry; the top-level README needs no change.
