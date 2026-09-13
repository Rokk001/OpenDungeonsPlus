# Legacy save version compatibility

The user's September 13 screenshot and game log show a failed single-player
load of a September 6 save. The file identifies itself as version 0.7.1, while
the running executable is 0.7.2. Map listing already accepts 0.7.1, but the
actual map loader rejects it before reading the Info or Seat sections.
Consequently a selectable save cannot be opened, despite the existing legacy
research-state migration.

Accept exactly the same current/0.7.1 versions in the loader as in map listing.
Keep the network version, unsupported-version rejection, save contents and all
subsequent parsing unchanged. The user assigned this regression to
`feature/research-progression`, advanced to the complete `0f32c080` checkpoint
before fixing it; no game launch or push is authorized.

## Verification

`source/tests/check_map_version.py` compiles the actual listing/loading header
checks and the production file reader, including comment removal. It covers
current and 0.7.1 files, unsupported older/future headers and malformed Info
sections. With both reported saved games supplied through `--save`, the old
loader fails three of 26 checks; the corrected loader passes all 26.
The separate 411 research/save/packet regression checks also pass.

Release compilation and runtime preparation pass. The test reads the existing
saves without modifying them; it verifies the reported header rejection, not a
complete running match or every later entity deserializer. Loading and resuming
the affected saves in the game remains for the user's acceptance test.

Version 0.7.2 is retained: this corrects its file compatibility regression and
does not change the network protocol or saved format. The development index,
research note and build record are updated; no unrelated feature changes apply.
