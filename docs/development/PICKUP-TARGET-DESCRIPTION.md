# Pickup target descriptions

## Existing behavior and cause

Work branch: `fix/pickup-target-description`, based on the complete fork at
`fcb9714c`, including the wall-outline correction.

The existing idle-hand path already finds the nearest eligible pickup target.
It describes creatures by their class name but uses an internal entity identifier
for other objects. A user capture shows a generated hatchery identifier while
hovering a chicken. Gold uses the same faulty fallback.

Current gameplay pickup implementations cover creatures, chickens and gold;
map lights are pickup targets only in the editor. The existing entity type
distinguishes these objects, so no additional target query, display-name API or
identifier change is needed. Correct the chicken and gold descriptions in this
existing presentation path, retaining creature names and all targeting behavior.

Before implementation, upstream was fetched at `be44649f` and the 12 open issues
and 19 open PRs were checked. The relevant patches in PRs 15 and 16 change
construction/cooldown behavior, not these target descriptions. No upstream
change was imported and no issue is claimed resolved by this narrow correction.

## Verification

The existing context strip now displays `Chicken` and `Gold` for these two
object types. Creature class names, nearest-target selection, pickup eligibility,
highlighting and entity/network identifiers are unchanged.

The focused source diff and `git diff --check` pass. The Windows Release build
and runtime preparation succeeded on September 6, 2026:

- `build/windows/pickup-description-build.log`.
- `build/windows/pickup-description-runtime.log`.

The prepared executable is `build/windows/opendungeons-plus.exe`, SHA-256
`3c4989a48148e88f23b4ba2c3a6d1453c5fe3f139d36388c118ef6774ce6e4e8`.
It includes the preceding wall-outline and user-accepted HUD corrections.

The user has been asked to verify chicken/gold hover descriptions and the wall
outline, including marking and cancellation. No game was launched by the
assistant. Compilation and source review do not establish visual acceptance.

Version remains 0.7.1; no release was requested and no changelog exists. The
README's current-target description remains accurate without another feature
entry. This note and the build index record the corrective change.
