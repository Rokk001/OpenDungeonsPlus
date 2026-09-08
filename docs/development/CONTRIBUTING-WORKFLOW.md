# Contributing to the original project

## Local workspace checkpoint, September 6

The user's priority commit request found 173 entries against the old shared
shadow checkout; 157 already matched the complete functional branch stack.
The latest functional commits are minimap stacking `232ac515` and the hand
unmarking correction `711c694e`, on their respective work branches. Remaining
local development notes and the requested move of private planning documents
are preserved on `chore/fork-checkpoint`, which has no upstream PR.

The normal checkout/index are aligned to that complete checkpoint without
rewriting branch history or replacing working files. The user's `.gitignore`
is excluded from the commits; the private files remain in `docs/internal/`.
Subsequent tasks must start from this latest complete state plus newer edits.
Older instructions to leave the shared checkout on the shadow branch describe
the earlier parallel-work phase, not the current baseline.

## Inspect existing behavior before implementation

For every request, first search the current complete fork for an existing
implementation, inspect its actual code path and read the relevant documentation.
Identify how it is invoked, where it stores its data and what it already covers.
Record the existing solution and any concrete gap in the task note before coding.

If the request is already covered, use and document the existing functionality.
If something is missing, extend that implementation wherever it can satisfy the
request. Do not create a parallel feature, storage location or workflow without
first establishing why the existing solution cannot be reused or extended.
Preserve unrelated work while removing any explicitly rejected duplicate.

## Mandatory pull request rule

Create one pull request for one coherent, independently reviewable product
outcome. Include the implementation, required enabling work, tests and any
corrections needed for that outcome to meet its acceptance criteria. Do not
create a pull request for every commit, helper, protocol field, rendering layer
or other internal implementation step when those parts have no useful standalone
result. This avoids both aggregate pull requests and a flood of fragmentary ones.

Keep unrelated features and unrelated bug fixes in separate branches and pull
requests. Never place an independent bug fix in a feature contribution merely
because both were developed in the same local stack. A correction that only
completes an unmerged feature remains part of that feature's pull request; a
pre-existing or separately releasable defect gets its own bug-fix pull request.
Preserve the complete local fork while assembling these focused contributions.

Before publishing, confirm that the user-facing outcome is complete, review its
dependency and issue overlap, exclude private fork material, and state the real
validation and acceptance limits. Dependencies require explicit links and a
focused comparison; they do not justify bundling unrelated outcomes.

Create pull requests only for functional implementations: features and bug fixes.
Never submit documentation-only PRs. Internal development notes, agent rules and
the product improvement roadmap stay in the fork and outside upstream contributions.

Create one pull request per completed coherent outcome; never combine unrelated
work branches into a collection or umbrella PR. Each PR must describe its own
scope, dependencies, issue coverage and verification limits.

For an existing branch stack, link the predecessors and provide a direct
comparison against the preceding work branch. When the user requests finalization,
mark completed functional contributions ready for review; dependencies alone do
not require leaving completed work as drafts.
GitHub compares fork PRs against a branch in the target repository: until the
predecessors merge, its default comparison can also contain those prerequisite
commits. State that explicitly; do not present the cumulative diff as one task.
After the predecessor merges, recheck the base and remaining diff before merging
the dependent PR: it must contain only its own contribution, without internal
documentation. Never merge the cumulative stack as an umbrella contribution.

Preserve the latest complete fork, accepted implementation and any uncommitted
work throughout PR preparation.

Backup/recovery branches are not submitted as separate contributions, and work
still in progress is not included in the PRs for completed tasks.
Use issue-closing keywords only when a PR resolves the entire reported issue.

On September 6, 2026, the user required the combined upstream PR #46 to be
withdrawn and replaced with separate PRs for completed implementation branches.
The mistakenly submitted roadmap PR #52 was closed because it is internal
documentation. The user subsequently requested that all six functional PRs be
marked ready for review.
This rule supersedes any earlier guidance suggesting a combined contribution.

## Current upstream submissions

As verified on September 6, 2026, [PR #46](https://github.com/tomluchowski/OpenDungeonsPlus/pull/46)
is closed and the following separate PRs replace it:

| Work branch | Pull request | Submission state |
| --- | --- | --- |
| `feature/windows-support` | [#47](https://github.com/tomluchowski/OpenDungeonsPlus/pull/47) | Open for review |
| `fix/dynamic-shadows` | [#48](https://github.com/tomluchowski/OpenDungeonsPlus/pull/48) | Open for review; predecessor #47 |
| `fix/settings-option-duplicates` | [#49](https://github.com/tomluchowski/OpenDungeonsPlus/pull/49) | Open for review; predecessor #48 |
| `feature/live-settings` | [#50](https://github.com/tomluchowski/OpenDungeonsPlus/pull/50) | Open for review; predecessor #49 |
| `feature/progressive-edge-scrolling` | [#51](https://github.com/tomluchowski/OpenDungeonsPlus/pull/51) | Open for review; predecessor #50 |
| `docs/improvement-roadmap` | [#52](https://github.com/tomluchowski/OpenDungeonsPlus/pull/52) | Closed; internal documentation |
| `feature/gui-scaling` | [#53](https://github.com/tomluchowski/OpenDungeonsPlus/pull/53) | Open for review; predecessor #51 |

On September 7, 2026, contribution preparation was corrected after an automated
publication split implementation commits and unfinished feature components into
too many pull requests. The publication process was stopped. Pull requests #55
and #72 were replaced by the single coherent Escape-navigation bug fix [#80](https://github.com/tomluchowski/OpenDungeonsPlus/pull/80).
The component or incomplete submissions #58 and #63 through #79 were withdrawn
with an explanation; their code remains preserved in the fork and may return only
as part of a complete, coherent and accepted product outcome.

The additional independent contributions retained after that review are:

| Outcome | Pull request | Reason retained |
| --- | --- | --- |
| Default save-request packet correction | [#54](https://github.com/tomluchowski/OpenDungeonsPlus/pull/54) | One independently verified protocol defect |
| Exit-confirmation layout correction | [#56](https://github.com/tomluchowski/OpenDungeonsPlus/pull/56) | One independently reviewable layout defect |
| Literal event-message path correction | [#57](https://github.com/tomluchowski/OpenDungeonsPlus/pull/57) | One independently verified parser/display defect |
| Windows incremental-build correction | [#59](https://github.com/tomluchowski/OpenDungeonsPlus/pull/59) | One independently verified build-consistency defect |
| Material light accumulation correction | [#62](https://github.com/tomluchowski/OpenDungeonsPlus/pull/62) | One coherent rendering defect; depends on #48 |
| Escape/back navigation correction | [#80](https://github.com/tomluchowski/OpenDungeonsPlus/pull/80) | One accepted interaction defect replacing #55 and #72 |

Remote preparation branches for withdrawn submissions are retained as recovery
references because their deletion was not requested. A pushed branch alone is
not a proposed upstream contribution. Do not reopen those pull requests or create
replacement submissions until the containing product outcome is complete and
passes its remaining acceptance gates.

Each PR uses the already published work-branch head. Its description states its
own issue coverage, verification limits and, where applicable, a direct comparison
against its predecessor. The dependency sequence preserves the existing Git
history; it does not claim that every topic technically requires every earlier
topic. The default comparisons still include prerequisite commits and fork notes;
those must be excluded from each final merge. PR #52 is not a merge prerequisite.
No source changes, rebase, force-push or new game build were introduced
to replace the combined PR. The unfinished action-feedback work stays local.

These submission states supersede older "not yet published" statements in the
historical Windows setup notes below; recheck GitHub before further PR actions.

## Working independently in the fork

The project can be developed independently in your own fork; joining
the original project's team or having write permissions there is not necessary.
On September 6, 2026, GitHub reported read access without push or administrative
permissions to the original repository for this account.

The original project is needed as upstream when you want to incorporate its new
changes or contribute your own changes back through a pull request;
both are optional if you only want to continue development in your own fork.

When a new goal is defined, identify its functional features and create one
separate work branch per feature before implementation starts. Perform each
implementation inside its assigned branch; do not develop the goal in a shared
checkout and split it afterward. For work solely in the fork, create each branch
from your own current complete development state so that existing changes of
your own are preserved. The following steps,
in contrast, describe a contribution to the original project and start its
work branch directly from the upstream state.

## Repositories and target branch

- Own fork: [Rokk001/OpenDungeonsPlus](https://github.com/Rokk001/OpenDungeonsPlus),
  configured locally as `origin`.
- Original project for our contributions:
  [tomluchowski/OpenDungeonsPlus](https://github.com/tomluchowski/OpenDungeonsPlus),
  configured locally as `upstream`.
- Target branch in the original project: `shaders-improvement` (as of September 5, 2026).
  Check the intended target branch on GitHub before a pull request.

## Currently configured: Windows support

As of September 5, 2026. Our work branch in the fork is
`feature/windows-support`; we continue the Windows work here.
Documentation and the preparation of a build environment also belong on a
work branch; a branch is not limited to new game features.

The branch was created from the existing fork state `a8ffa583` and includes
the setup scripts and development notes that had not yet been committed.
The default branch `shaders-improvement` remains at that state;
we do not rewrite its existing documentation commit.
When fetched, the confirmed default branch of the original project,
`upstream/shaders-improvement`, pointed to commit `be44649f`.
The fork's default branch was therefore one documentation commit ahead of
the original at the time of setup.

The setup is recorded in two commits: first the existing local
Windows setup scripts, then the documentation including this workflow.
There is no change to the game code or game version at this point;
README and the development documentation describe the actual state,
and an additional game changelog entry is not needed for this setup.

### Daily work

When resuming Windows support work, check `git status` and use `feature/windows-support`;
the environment and build commands are in [BUILDING.md](BUILDING.md).
Do not create a new branch for each session of this ongoing Windows task.
Commit completed, coherent changes separately and review them together
with their associated general build documentation; keep personal
computer notes in a separate documentation commit.

The default branch is not changed for this work. First fetch new changes from
the original with `git fetch upstream` and compare them before incorporating them;
a fetch alone changes neither working files nor local work branches.

`origin` is configured locally as the default target for future pushes and is
also explicitly set as the push remote for the Windows work branch.
The new branch currently exists only locally and has no remote-tracking branch yet;
the main project is configured as the source for fetching and as the future PR target.
A push is still only performed after explicit authorization.

### Separate task: live settings

The related work is kept as a local stack so each branch adds one reviewable task:
`feature/windows-support`, `fix/dynamic-shadows`,
`fix/settings-option-duplicates`, then `feature/live-settings`. The live-settings
changes affect shared game code, including Linux paths, so they remain separate
from installing and building on Windows. Their implementation and verification
status is in [LIVE-SETTINGS.md](LIVE-SETTINGS.md). Prepare upstream contributions
from these boundaries after checking their dependencies. Linux validation is
still pending.

### Separate task: progressive edge scrolling

`feature/progressive-edge-scrolling` continues from `feature/live-settings` and
contains the mouse-edge camera control change. Its implementation and verification
status are recorded in [PROGRESSIVE-EDGE-SCROLLING.md](PROGRESSIVE-EDGE-SCROLLING.md).

### Path to the future Windows PR

The work branch contains our fork context, including personal paths
and notes; the directory name or a separate commit does not
automatically exclude them from a pull request.
The finished contribution will therefore later be assembled on a separate PR branch
directly from the then-current `upstream/shaders-improvement`.
This PR branch has not yet been created.

First get the Windows build actually working, make the setup scripts usable
on other computers and document the results of the user's game tests.
Include only the verified, generally reusable changes and their instructions
in the PR; local installation logs and agent instructions
from this fork stay outside the contribution.
Explicitly review the selection and all affected file differences before the PR
and rebuild the assembled state, since it must not depend on the private
fork context. Only after explicit push authorization, publish the PR branch
in your own fork and propose it against the original project's default branch.

## 1. Add the original project as a remote once

Show existing remotes:

```powershell
git remote -v
```

If `upstream` is still missing:

```powershell
git remote add upstream https://github.com/tomluchowski/OpenDungeonsPlus.git
```

## 2. Keep the base up to date

Before switching branches, use `git status` to check that there are no unsaved changes;
save ongoing work on its own branch first.

```powershell
git fetch upstream
git switch shaders-improvement
git merge --ff-only upstream/shaders-improvement
```

This updates the local base branch; do not develop features on this
branch. If Git rejects the fast-forward, inspect the divergent commits
before taking further steps.

To also update the base branch on GitHub in your own fork:

```powershell
git push origin shaders-improvement
```

## 3. Create a separate branch for each change

Example for work on GUI scaling:

```powershell
git switch -c feature/gui-scaling upstream/shaders-improvement
```

Adapt the name to the specific task. The branch starts directly from the
previously fetched original state so that existing fork-only changes do not
automatically become part of the contribution.

## 4. Develop, verify and commit

Implement the change and verify the affected functionality; include only files
belonging to this task in the commit. Before each commit, check whether the version,
README, changelog or other documentation needs to be updated.

Review the changes with `git diff`, stage the intended files explicitly with `git add`
and then check the full commit content with `git diff --cached`.

```powershell
git commit -m "Describe the change"
```

Replace the example message with a specific description of the change.

## 5. Push the branch to your own fork

For the example branch:

```powershell
git push -u origin feature/gui-scaling
```

When Codex performs the work, every push requires explicit authorization;
the commands in this guide do not themselves constitute authorization.

## 6. Create a pull request to the original project

On GitHub, open a pull request with these settings:

- Target repository (base repository): `tomluchowski/OpenDungeonsPlus`.
- Target branch (base): `shaders-improvement`.
- Source repository (head repository): `Rokk001/OpenDungeonsPlus`.
- Source branch (compare): your own work branch, `feature/gui-scaling` in the example.

Describe the problem, change and checks performed; before creating the PR,
check under "Files changed" that only the intended changes
are included.

## 7. Address review comments

Implement, verify and commit corrections on the same work branch; then
push that branch to your own fork again, which automatically updates the existing
pull request.

## Documentation in the fork and in the pull request

Personal development notes are stored under `docs/development/` and remain in
the fork. Do not create documentation-only PRs or submit the internal roadmap,
agent rules or local installation notes upstream. Review the actual PR diff:
neither a directory name nor a separate documentation commit excludes those
files automatically.
