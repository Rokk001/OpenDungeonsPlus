# Server shutdown ownership

The September 13 Windows report at 15:14:28 is an AppHangB1, not a new native
exception. The game log ends at processing the server `exit` notification after
the application thread has already entered `stopServer()`.

The existing notification handler calls `stopServer()` on the server thread.
That deletes its own `sf::Thread`; the installed SFML destructor calls `wait()`
and Windows waits indefinitely on that same thread. Concurrent application
shutdown can also enter that deletion while waiting for the server. This defect
is independent of the now-corrected room-object search slowdown.

Keep thread joining, socket cleanup and map cleanup on the owning application
thread. Exit requests only clear an atomic running flag; they must not edit the
server-owned notification queue from the application thread. The server loop
must check that flag after socket polling before starting another turn. Existing
owner-side `stopServer()` calls perform cleanup after the worker has returned.
An already-queued exit notification follows the same non-joining request path.

`python source/tests/check_server_shutdown.py --source-ref 225059d6` reproduces
both queued-exit and application-exit self-waits (bounded five-second timeouts).
Ordinary owner-side stopping succeeds on that baseline. The corrected production
shutdown/notification functions pass 31 checks using actual installed SFML
threads, plus two source guards for atomic visibility and the post-poll exit.
The fixtures substitute game/map/socket bookkeeping, not the thread mechanism;
no game is launched. They cover pending events, owner-side cleanup, repeated
requests, repeated stops and a subsequent server lifecycle.

The existing 60 menu-cursor checks and Release linking also pass. The normal
executable is in use, so the corrected 15:42:10 output is
`build/windows/opendungeons-plus-pending.exe`, using the existing staged runtime.
The user must test shutdown with the new executable after closing the old run.
No game process or runtime DLL was changed and no push was made.

This does not prove that all post-load latency has disappeared: the user's new
15:37 run of the navigation executable still records multi-second upkeep. That
remaining slowdown requires continued navigation diagnosis separately.

No version bump is required: this changes only shutdown ownership and does not
change save files, packet layouts, settings or gameplay rules.
