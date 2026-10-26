# Notes for AI coding assistants

These instructions apply to every change made to this repository with an AI assistant.

## Coding style

- Write variable types out explicitly. Do not use `auto`, not even for iterators or
  return values (see issue #42):

  ```cpp
  std::map<Tile*, TileData*>::iterator it = mTileData.find(tile);
  Command::Result result = interface.tryExecuteClientCommand(cmd, mode, modeManager);
  ```

  When a closure is needed, give it a `std::function<...>` type; otherwise prefer a
  named function over a lambda.
- The project is built as C++11 (see `CMakeLists.txt`); do not rely on newer language
  features.
- Match the surrounding code: four-space indentation, braces on their own line,
  `if(condition)` without a space before the parenthesis, member variables prefixed
  with `m`, `OD_LOG_*` for logging and `OD_ASSERT_TRUE_MSG` for invariants.
- Keep changes focused on what was asked; do not reformat or restyle code that the
  change does not need to touch.

## Branches

- Every new feature or fix branch starts from the tip of integration/all, never from shaders-improvement and never from main. Nothing is committed directly on integration/all. No upstream pull requests are created any more. A pull request is only created when Mario explicitly instructs it. The pull request coverage check is informational only and never blocks an integration.

## Working mode

Working mode: never wait idle. While a build, load test or agent runs, start every other task that does not depend on its result at once as a separate subagent (analysis, code fixes on own branches, checks, documentation). Only Blender work stays sequential, and timing measurements run without competing game instances. Before reporting 'waiting', list what else could run now and start it.

## Agent model

- Agent model: Claude Code agents use Sonnet 5.5 medium, Codex agents use GPT-6.1-Sol medium. Both are equivalent; a plan's model line is fulfilled by either. Never ask Mario about the model.

## Protected content

- Never copy or derive levels, maps, graphics, models, sounds, texts or data tables from
  commercial games. Only general ideas and generic terms may be used; everything else is
  created independently.
- Never use distinctive names from other games. Use the alias table in
  `docs/development/NAME-ALIASES.md` as the reference for our own names.
- Never cite another game, its publisher or any outside source for rules, values or names
  in code, comments, docs, commits, branch names or PR texts.
- Data from commercial games used for local testing stays outside the repository
  (`..\OpenDungeonsPlus-private`) and is never committed.
- Every new asset needs a `CREDITS` entry with source and licence in the same commit;
  AI-generated assets are marked as such.
- `scripts/check-protected-content.py` checks pushes against these rules. Install it once
  per clone as the `pre-push` hook (a small wrapper in the shared hooks directory that
  calls the script); it needs a local term list and blocks the push if that list is missing.

## Load tests

- Every integration runs exactly one load test: start the game, load one level and let it
  run briefly. If level files were changed in the integration, only those levels are loaded
  in addition. There are no sample levels and no run over all maps.
- The full load test of all levels runs only when the owner explicitly asks for it. If an
  integration changes code or shared files, the integration agent may propose the full run
  to the main session, but never starts it itself.
- `integration/all` is pushed once the release build, all check scripts and this load test
  are green.
- Check scripts, load tests and the pre-push hook are never removed, weakened or bypassed.
  If a check measures wrongly, correct the check openly and report it to the owner first.

## Tool-Pfade

- Dependency root: `C:\Users\mario\od-deps-next` (default in `scripts/win32/windows-paths.ps1`, overridable with `OD_DEPS_ROOT`); Python 3.14 at `C:\Users\mario\AppData\Local\Programs\Python\Python314`
- OgreXMLConverter.exe: `C:\Users\mario\od-deps-next\install\bin\OgreXMLConverter.exe`
- blender.exe: `C:\Users\mario\AppData\Local\Microsoft\WindowsApps\blender-launcher.exe` (Store-App, `blender.exe` selbst ist nicht direkt ausfuehrbar; Aufruf `--background <blend> --python <script>`)
- cl.exe (VS 2026 Build Tools): `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Tools\MSVC\14.51.36231\bin\Hostx64\x64\cl.exe`
- vcvars64.bat: `C:\Program Files (x86)\Microsoft Visual Studio\18\BuildTools\VC\Auxiliary\Build\vcvars64.bat`
- cmake.exe (4.4.1; CMake generator `Visual Studio 18 2026`): `C:\Users\mario\od-deps-next\tools\cmake-4.4.1-windows-x86_64\bin\cmake.exe`

Diese Pfade direkt verwenden, nie danach suchen.

## Builds

- Build flow (Mario, 2026-10-25):
  1. The integrator is the only one that runs a full build: once per run, Release, --parallel 1, at least 2 GB free RAM,
     then all check scripts, the load test, push and deploy.
  2. Feature and fix windows (Claude Code and Codex) never run a full build, not even when a prompt releases one, and
     compile nothing while a plan is in progress.
  3. After the completeness question is answered with 'Offene Anforderungen: 0', the window merges the current
     origin/integration/all into its branch and resolves all conflicts itself.
  4. Then it runs scripts/win32/compile-check-changed.ps1 in its worktree. The script compiles only the .cpp files the branch
     changed against origin/integration/all, with the compiler settings of the integrator's build folder, without linking
     and without building the game. The window fixes every compile error and repeats until the script exits 0.
  5. Then it runs the check scripts for its changed source files, pushes normally and registers ready in
     the integration queue file with the checked tip and 'Kompiliertest: Exit 0'.
  6. The integrator refuses a ready row without 'Kompiliertest: Exit 0' for its exact tip and sends it back.
  7. Plans run in parallel, also when they change the same files. Only a plan that needs another plan's result (it builds
     on code that plan adds) waits until that plan is integrated. Every window merges the current origin/integration/all into
     its branch whenever another branch has been integrated (checked at the start of every package and at least once per
     hour) and always before ready, and resolves all conflicts so that the content of both sides is kept completely. The
     coordinator applies the same rule when planning.
- Check scripts in source/tests that compile small C++ probes with cl are not a game build. Feature windows run them before marking a branch ready for every source file the branch changes; skipping them is not allowed.
- Every integrator release build that is pushed and deployed gets the next build number (version 0.7.3.N); branch and test builds use build number 0. Major, minor and patch version change only on Mario's explicit instruction. When major, minor or patch changes (for example 0.7.3 to 0.7.4), the build number starts again at 1 (0.7.4.1); otherwise every integrator build only increases the last digit. `scripts/next-build-number.py` computes N by comparing OD_MAJOR_VERSION, OD_MINOR_VERSION and OD_PATCH_LEVEL in CMakeLists.txt with the last deployed state.
