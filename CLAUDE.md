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

## Pull request lifecycle

- Never close a pull request (on this repo or any fork remote) without the
  user's explicit, additional permission for that specific closing action.
  Permission for something else (e.g. cleaning up commit messages or PR text)
  does not imply permission to close PRs, and this must never happen
  automatically as a side effect of another task.
