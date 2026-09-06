# Save request payload

## Existing path and diagnosed gap

The existing server handler for `askSaveMap` reads two strings: an optional
directory and filename. The editor's explicit Save dialog already sends both.
The game Save command, editor Options Save command and editor quick-save command
send only the notification type. Reading either string from those packets fails
and enters the existing critical assertion log path. The assertion logs rather
than aborting; default-initialized empty strings can still let saving continue.
This diagnosis does not claim that every affected save fails or crashes.

Keep the existing packet format and send two empty strings from these three
default-location callers. The server already interprets empty editor fields as
the current map path and generates its existing timestamped game-save filename.
Keep the explicit editor filename, authorization, save destination and result
notification paths unchanged. Named in-game saves and in-game loading are
separate interface/lifecycle gaps and are not implemented by this correction.

## Verification

The focused probe executes the three production caller bodies, serializes
through the real notification and ODPacket code, and runs the actual server
payload-read statements. Before the correction, six of 58 checks fail: two
missing strings for each default-location caller. After the correction, all
58 checks pass. Host/connection guards, the existing message/Options path,
editor modified flags and explicit filenames with spaces, brackets and UTF-8
characters are covered. The six source hashes recorded by the probe still
match the working files after execution.

Windows Release compilation passes. Runtime preparation initially encountered
an in-use OgreBites.dll; after checking that no game or build process remained,
the retry passes. The headless OGRE resource check also passes. No game was
launched, no live network session was exercised and no saved map was written;
actual save/load acceptance remains with the user. This is a packet-format
verification, not proof of a crash fix.

Evidence under `build/windows/`: `save-request-before-results.log`,
`save-request-after-results.log`, `save-request-probe-source.json`,
`save-request-release-build.log`, `save-request-runtime-retry.log` and
`save-request-resources.log`. See [BUILDING.md](BUILDING.md) for the executable.

The preceding upstream check on September 6 inspected the current default
branch at `be44649f` and the actual source at open PR heads #15, #16, #21, #29,
#41 and #45. Those inspected heads retain the same three missing payloads;
none supplies this correction. No issue is claimed as fully resolved and no
push or pull request is included in this task.

Version remains 0.7.1 because no release is requested. Controls and save behavior
do not change, so the user-facing README needs no new usage instructions; this
note and the development index record the protocol correction. The repository
has no changelog. This work remains a separate functional branch and does not
close a broader interface or save/load issue.
