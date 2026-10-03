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
- Files in `docs/internal/` are local only: never commit them, never add them with
  `git add -f` and never push them. The pre-push check blocks every push in which a commit
  adds or changes a file under `docs/internal/`.
- Every new asset needs a `CREDITS` entry with source and licence in the same commit;
  AI-generated assets are marked as such.
- `scripts/check-protected-content.py` checks pushes against these rules. Install it once
  per clone as the `pre-push` hook (a small wrapper in the shared hooks directory that
  calls the script); it needs a local term list and blocks the push if that list is missing.

## Integration

- Only the campaign session merges into `integration/all` and only the campaign session
  starts integration subagents. No other session (animation, relationship or any other
  feature session) merges into `integration/all`, pushes it, or starts an integration
  agent.
- Every other session finishes its work on its own branch and only registers it as
  "ready for integration/all" in its own state file (`docs/internal/ANIMATION-STATE.md`,
  `docs/internal/RELATIONSHIP-STATE.md`). It does not merge, rebase onto or push
  `integration/all` itself, and it keeps commits that were never meant for the remote on
  its own branch.
- The campaign session starts a fresh integration subagent (`pr-fixer`, no model override,
  never resume an old one) after every finished batch and otherwise at the latest every
  30 minutes. The subagent does only this:
  1. Find what is ready: finished campaign branches and every branch that
     `docs/internal/ANIMATION-STATE.md` or `docs/internal/RELATIONSHIP-STATE.md` lists as
     "ready for integration/all". Branches not listed as ready are not merged.
  2. Merge them into `integration/all`, then run the release build, all check scripts and,
     (no load test, see below).
  3. If everything is green, push `integration/all` normally (no force push, no PRs) and
     set the merged entries in the state files to "integrated".
  4. If anything fails: push nothing, record the reason in `CAMPAIGN-STATE.md` or the
     state file of the affected branch and report briefly to the campaign session.
  If there is nothing to integrate, it ends immediately.

## Load tests

- Integrations run no load tests and never start the game. `integration/all` is pushed once
  the release build and all check scripts are green.
- Load tests (`scripts/run-level-test.py`, level samples or the full run) run only when the
  owner explicitly asks for them. If an integration changes code or shared files, the
  integration agent may propose a load test to the main session, but never starts one.
- Check scripts and the pre-push hook are never removed, weakened or bypassed. If a check
  measures wrongly, correct the check openly and report it to the owner first.
