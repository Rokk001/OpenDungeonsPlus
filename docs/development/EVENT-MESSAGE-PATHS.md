# Literal paths in event messages

Work branch: `fix/event-message-paths`, continuing from the complete
`feature/creature-level-selection` checkpoint `ed56e5d2`, including the parallel
lighting work. The shared checkout remains on its existing branch.

## Existing behavior and cause

The user's September 6, 13:47 capture shows a successful-save notification whose
Windows path has lost its backslashes. The corresponding save file exists at
the expected path. `ODServer.cpp` sends the original filesystem path in the
notification; `EventMessage::getMessageAsString` adds icon/colour markup around
that unescaped text. `GameEditorModeBase` appends the resulting formatted string
to the existing event window and uses the same formatter when rebuilding it.

The installed CEGUI parser treats backslash as an escape character and an opening
square bracket as the start of a formatting tag. As a result, the displayed
message can lose path separators or bracketed directory/file names even though
the received message and saved file are correct.

The inspected event producers send plain text. Retain the event type's existing
icon, colour and trailing reset/newline, and escape only the literal payload at
the existing formatting boundary. This also preserves paths in failure notices.
Chat formatting, player nicknames, network packets, save paths, file contents and
notification timing are outside this correction.

## Verification

The formatter now escapes backslashes and opening square brackets in a local
copy of the payload before adding the unchanged icon/colour decoration. The
stored event remains unchanged, so rebuilding the message window cannot
double-escape it.

The isolated check compiles the production formatter and actual event enum into
a small fixture, loads the real event window and skin, and passes the resulting
text through the installed CEGUI parser. It inspects the rendered text components
and image/colour state rather than comparing the formatter against itself.
The fixture substitutes only event construction; it does not run the game,
server, save operation or input devices.

- Before the correction: 156 failures in 504 checks.
- After the correction: all 504 checks pass.
- Cases include the reported save-path shape, UNC and POSIX paths, bracketed
  names, UTF-8, trailing separators/brackets, multiline errors, plain/empty text,
  literal markup and repeated append/rebuild. All five event types and the
  existing fallback retain their icon and colour.
- Windows Release compilation and runtime preparation pass. Executable:
  `build/windows/opendungeons-plus.exe`, September 6, 2026 at 17:18:02;
  SHA-256 `71000f94b27c1406e4be50193c6b4924be748d5e331c38969ceb83ef6b1363d0`.

Local verification artifacts under `build/windows/`:
`generate-event-message-probe.py`, `build-event-message-probe.ps1`,
`event-message-before-results.log`, `event-message-probe-results.log`,
`event-message-paths-build.log` and `event-message-paths-runtime.log`.
The first probe build had an inspection-only header-access problem; correcting
that fixture allowed the installed parser to reproduce the production failure.
No dependency or compiler configuration was changed.

Manual verification: save a game with an empty hand and check that its existing
confirmation displays the full path, including separators and any brackets.
Saving/loading behavior was not changed or certified by this display check.
The assistant did not launch the game. Version stays 0.7.1 because this is not a
release; README already describes save feedback and needs no new user command.
No changelog exists. No push or upstream PR was made.
