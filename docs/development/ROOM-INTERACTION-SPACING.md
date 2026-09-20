# Room interaction positions

Training already reserves a different dummy tile for each user. Training,
library, workshop and casino then call `RoomObjectNavigation::workApproach`,
which checks terrain and furniture but not another user's body. The resulting
stand-off position can overlap a neighbouring station's user, particularly when
different creature sizes require different stand-off distances.

Extend this existing endpoint selection with room-owned interaction reservations
and lateral candidates. Reuse the measured, oriented creature bounds already
used for furniture clearance. Reservations are endpoint-only: they must never
be included in walking obstacles, path costs or speed calculations. Release them
when room use ends, preserve a valid chosen position between work cycles, and
re-evaluate it when the assigned object changes.

The same endpoint selection also covers torture apparatus, retaining the existing
permission to enter the assigned apparatus. Its animation faces the direction
used by the footprint check; effect placement remains on the assigned apparatus,
even if the creature's separate stand position lies on an adjacent room tile.
Runtime validation results are recorded below; visual acceptance remains with the user.

The shared four-workstation path now stores chosen endpoints in the owning room,
keeps valid endpoints stable and releases them when room use ends or training
assignments are refreshed. Other users' oriented bounds are checked only during
endpoint selection. Unoccupied stations retain their original straight stand-off;
lateral candidates are considered where a user already occupies that space.
Room absorption transfers remaining reservations alongside remaining users.

The final dispatch also needs to retain that validated route: ordinary
`MovableGameEntity::setWalkPath` refines routes again and may move the endpoint
away from the reserved position. Workstation callers explicitly identify their
already-refined path, preserving its checked final leg and disabling jitter;
ordinary movement retains its existing refinement. This is not a network option.

The production navigation fixture includes paired rat/spider
users, stable repeated work cycles, endpoint release and identical passing routes
with or without reservations. Its final ordinary run passes 6,678 checks; an
additional packed-bedroom/full-room-layout run is still blocked before execution
by Windows application control (4551), not counted as a pass.

Other room interactions were inspected: dormitory creation reserves every bed
tile for one owner, and sleeping centres the resting pose on that owner's bed;
these are not shared standing stations. Crypt delivery reserves one corpse spot,
then the carrier leaves. Prison/arena actions do not use standing furniture
stations. Hatchery use selects and locks a freely moving chicken, not a coop
interaction position; its existing chase and eating behaviour is unchanged.
The user test must include occupied workstations, neighbouring apparatus and
passing traffic; existing bedroom and feeding behaviour must remain unchanged.

The torture-entry fixture checks that an unoccupied apparatus keeps its central
position and that arrival becomes ready without repeated walking. The optional
`--compile-only` mode explicitly reports that no checks ran; it does not attempt
to evade the Windows application-control block.

Windows Release compilation passed with the final dispatch correction on
September 20 (`build/review-followups/work-route-dispatch-build.log`). The normal
executable was updated with a verified backup; see BUILDING.md for the hash.

The dispatch follow-up adds `check_work_route_dispatch.py`: it compiles the actual
walk-path setter against a recording transport and refiner, covering exact
validated endpoints, ordinary refinement, empty paths, client/server behaviour,
unchanged packet flags and non-creature movement. All 41 actual dispatch checks
pass. No movement-speed or transit-obstacle change is introduced. User appearance
and the blocked expanded-layout regression remain unverified.

Documentation/version assessment: development guide and index only; no release
version, release changelog or top-level README change is needed for this work.
