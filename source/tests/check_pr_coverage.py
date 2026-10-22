#!/usr/bin/env python3
"""Check that every change on the integration line is also carried by an open pull request.

Compares the target ref (default origin/integration/all, or HEAD when --count-file is given) with the union of the heads of all
open pull requests of one author (default Rokk001, listed through the GitHub CLI against the
upstream repository). Both sides are diffed against the merge base with the upstream base
branch. Reported are

  file  a file changed on the target that no open pull request touches,
  lines added lines of the target (whitespace-only lines ignored) that appear in no open
        pull request, for files that some pull request touches.
Files listed in EXCLUDED_FILES are skipped. In CLAUDE.md, lines that git blame attributes to a commit
listed in source/tests/pr-coverage-not-upstream.txt are skipped; all other lines count.

Usage: python -I source/tests/check_pr_coverage.py [--target <ref>] [--base <ref>]
           [--repo <owner/name>] [--author <login>] [--max-lines <n>] [--strict]
           [--count-file <path>]
Output: one line "file: <path>" per uncovered file and "lines: <path>: <count> uncovered"
(with the first lines shown) per partly covered file, then a summary.
With --count-file the number of gaps of every run is stored in that file as one line
"PR coverage gaps (last run): <n>" (the line is replaced, or appended if the file or the
line is missing); with --count-file the target defaults to HEAD, so an integration run measures the
merged state of its worktree and not the remote ref; the run fails when the number is higher than the stored value of the
previous run (the first run only stores it), so old gaps do not turn a run red. When the
number rose, the stored value is left unchanged.
Exit codes: 0 = finished (gaps are only listed unless --strict is given), 1 = gaps found
with --strict or more gaps than in the previous run, 2 = the check could not run (GitHub CLI missing or not logged in, no network,
a pull request head is not available locally); this is never reported as green.
Nothing is compiled.
"""
import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_TARGET = "origin/integration/all"
DEFAULT_BASE = "upstream/shaders-improvement"
DEFAULT_REPO = "tomluchowski/OpenDungeonsPlus"
DEFAULT_AUTHOR = "Rokk001"
COUNT_MARKER = "PR coverage gaps (last run):"

# Files that deliberately never go to the upstream project; they are not reported as gaps.
# Every entry names where the decision is recorded.
EXCLUDED_FILES = frozenset([
    # Merge-order note of the integration line, recorded as not for upstream in commit 82a7a051b.
    "docs/development/INTEGRATION-ORDER.md",
    # This check is a tool of the integration line and is not submitted upstream.
    "source/tests/check_pr_coverage.py",
    # The list of commits below is read by this check and not submitted upstream either.
    "source/tests/pr-coverage-not-upstream.txt",
    # Not submitted, replaced by feature/dungeonbook-whole-portraits (decision of 2026-10-20): the part-based
    # Dungeonbook portrait tooling and checks of the withdrawn portrait branches.
    "materials/portraits/generation-inventory.json",
    "materials/portraits/neutral-bases/Knight.mesh.png",
    "scripts/check_portrait_manifests.py",
    "source/tests/check_portrait_option_orientation.py",
    "tools/portraits/check_plan_completion.py",
    "tools/portraits/deliver_neutral_variants.py",
    "tools/portraits/export_generation_inventory.py",
    "tools/portraits/measure_base_tints.py",
    "tools/portraits/neutral-feature-layouts.json",
    "tools/portraits/prepare_neutral_bases.py",
    "tools/portraits/prepare_neutral_features.py",
    "tools/portraits/prepare_outfit_variants.py",
    "tools/portraits/render_manifest_reviews.py",
    "tools/portraits/render_native_check_sheets.py",
    "tools/portraits/validate_neutral_features.py",
    "tools/portraits/verify_portrait_sources.py",
])

# Directories whose files are not submitted, replaced by feature/dungeonbook-whole-portraits (decision of 2026-10-20):
# the part-based Dungeonbook portrait variants of the withdrawn portrait branches.
EXCLUDED_PREFIXES = (
    "materials/portraits/variants/",
    "materials/portraits/neutral-variants/",
)

# Commits whose lines in BLAME_FILTERED_FILE are not submitted upstream; their lines in other files still count.
NOT_UPSTREAM_COMMITS_FILE = "source/tests/pr-coverage-not-upstream.txt"
BLAME_FILTERED_FILE = "CLAUDE.md"


class CheckError(Exception):
    """The check could not run; the message is printed and the exit code is 2."""


def run(args, what):
    """Run a command and return its stdout text; raise CheckError with a clear message on failure."""
    try:
        proc = subprocess.run(args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as err:
        raise CheckError("%s: cannot start %s (%s)" % (what, args[0], err))
    if proc.returncode != 0:
        detail = proc.stderr.decode("utf-8", "replace").strip().splitlines()
        raise CheckError("%s failed (exit %d): %s" % (what, proc.returncode, detail[-1] if detail else "no output"))
    return proc.stdout.decode("utf-8", "replace")


def list_open_pr_heads(repo, author):
    """Return (number, head branch, head commit) of every open pull request of the author."""
    text = run(["gh", "pr", "list", "--repo", repo, "--author", author, "--state", "open",
                "--limit", "500", "--json", "number,headRefName,headRefOid"],
               "listing open pull requests with the GitHub CLI")
    try:
        entries = json.loads(text)
    except ValueError:
        raise CheckError("the GitHub CLI returned unreadable data")
    return [(e["number"], e["headRefName"], e["headRefOid"]) for e in entries]


def resolve_head(number, branch, commit):
    """Return a locally available ref for a pull request head, or raise CheckError if there is none."""
    candidates = [commit, "origin/" + branch]
    for ref in candidates:
        probe = subprocess.run(["git", "cat-file", "-e", ref + "^{commit}"], cwd=ROOT,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if probe.returncode == 0:
            return ref
    raise CheckError("head of pull request #%d (%s) is not available locally; fetch the remote first" % (number, branch))


def diff_added(base, ref):
    """Return (all changed files, {file: set of added stripped lines}) of ref against its merge base with base."""
    merge_base = run(["git", "merge-base", base, ref], "merge base of %s and %s" % (base, ref)).strip()
    names = run(["git", "diff", "--name-only", merge_base, ref], "file list of %s" % ref)
    files = set(line for line in names.splitlines() if line)
    text = run(["git", "diff", "-U0", "--no-color", "--no-ext-diff", merge_base, ref], "diff of %s" % ref)
    added = {}
    current = None
    for line in text.splitlines():
        if line.startswith("+++ "):
            current = line[6:] if line.startswith("+++ b/") else None
            if current is not None:
                added.setdefault(current, set())
        elif line.startswith("+") and current is not None:
            stripped = line[1:].strip()
            if stripped:
                added[current].add(stripped)
    return files, added


def read_not_upstream_commits():
    """Return the set of commit hashes listed in the not-upstream list (first word per line, # starts a comment)."""
    commits = set()
    with open(os.path.join(ROOT, NOT_UPSTREAM_COMMITS_FILE), encoding="utf-8") as handle:
        for line in handle:
            words = line.split()
            if words and not words[0].startswith("#"):
                commits.add(words[0])
    return commits


def lines_from_commits(ref, path, commits):
    """Return the stripped, non-empty lines of path at ref that git blame attributes to one of the commits."""
    text = run(["git", "blame", "--porcelain", ref, "--", path], "blame of %s at %s" % (path, ref))
    found = set()
    owner = None
    for line in text.splitlines():
        if line.startswith("	"):
            stripped = line[1:].strip()
            if owner in commits and stripped:
                found.add(stripped)
        else:
            words = line.split()
            if len(words) >= 3 and len(words[0]) == 40 and words[2].isdigit():
                owner = words[0]
    return found


def read_count(path):
    """Return the gap count stored in the counter file, or None if the file or the line is missing."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8", errors="replace", newline="") as handle:
        text = handle.read()
    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith(COUNT_MARKER):
            try:
                return int(line[len(COUNT_MARKER):].strip())
            except ValueError:
                return None
    return None


def write_count(path, gaps):
    """Store the gap count in the counter file: replace the marker line, or append it; keep the line ending style."""
    lines = []
    eol = "\n"
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace", newline="") as handle:
            text = handle.read()
        if "\r\n" in text:
            eol = "\r\n"
        lines = text.split(eol)
    found = False
    for index, line in enumerate(lines):
        if line.startswith(COUNT_MARKER):
            lines[index] = "%s %d" % (COUNT_MARKER, gaps)
            found = True
            break
    if not found:
        while lines and lines[-1] == "":
            lines.pop()
        lines.append("%s %d" % (COUNT_MARKER, gaps))
        lines.append("")
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(eol.join(lines))


def main():
    """Parse the arguments, compute the gaps and print them; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--target", default=None, help="ref to measure (default: HEAD with --count-file, else %s)" % DEFAULT_TARGET)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--author", default=DEFAULT_AUTHOR)
    parser.add_argument("--max-lines", type=int, default=5, help="uncovered lines shown per file")
    parser.add_argument("--count-file", default=None, help="file that keeps the gap count of the last run")
    parser.add_argument("--strict", action="store_true", help="exit 1 when gaps are found")
    options = parser.parse_args()
    if options.target is None:
        # An integration run measures the merged HEAD of its worktree; without a count file the remote ref is measured.
        options.target = "HEAD" if options.count_file else DEFAULT_TARGET
    try:
        heads = list_open_pr_heads(options.repo, options.author)
        if not heads:
            raise CheckError("no open pull requests found for %s in %s; refusing to report an empty comparison" % (options.author, options.repo))
        target_files, target_added = diff_added(options.base, options.target)
        target_files -= EXCLUDED_FILES
        target_files = set(f for f in target_files if not f.startswith(EXCLUDED_PREFIXES))
        if BLAME_FILTERED_FILE in target_files:
            target_added[BLAME_FILTERED_FILE] -= lines_from_commits(options.target, BLAME_FILTERED_FILE, read_not_upstream_commits())
            if not target_added[BLAME_FILTERED_FILE]:
                target_files.discard(BLAME_FILTERED_FILE)
        pr_files = set()
        pr_added = {}
        for number, branch, commit in heads:
            files, added = diff_added(options.base, resolve_head(number, branch, commit))
            pr_files |= files
            for path, lines in added.items():
                pr_added.setdefault(path, set()).update(lines)
    except CheckError as err:
        sys.stderr.write("check_pr_coverage: cannot run: %s\n" % err)
        return 2
    gaps = 0
    for path in sorted(target_files - pr_files):
        print("file: %s" % path)
        gaps += 1
    for path in sorted(target_files & pr_files):
        missing = sorted(target_added.get(path, set()) - pr_added.get(path, set()))
        if missing:
            gaps += 1
            print("lines: %s: %d uncovered" % (path, len(missing)))
            for text in missing[:options.max_lines]:
                print("    %s" % text[:160])
    print("%d open pull requests, %d files changed on %s, %d gaps" % (len(heads), len(target_files), options.target, gaps))
    rose = False
    if options.count_file:
        previous = read_count(options.count_file)
        if previous is not None and gaps > previous:
            rose = True
            print("gap count rose from %d to %d; stored value stays %d" % (previous, gaps, previous))
        else:
            write_count(options.count_file, gaps)
            print("gap count %d stored (previous %s)" % (gaps, "none" if previous is None else previous))
    return 1 if ((gaps and options.strict) or rose) else 0


if __name__ == "__main__":
    sys.exit(main())
