#!/usr/bin/env python3
"""Check that every change on the integration line is also carried by an open pull request.

Compares the target ref (default origin/integration/all) with the union of the heads of all
open pull requests of one author (default Rokk001, listed through the GitHub CLI against the
upstream repository). Both sides are diffed against the merge base with the upstream base
branch. Reported are

  file  a file changed on the target that no open pull request touches,
  lines added lines of the target (whitespace-only lines ignored) that appear in no open
        pull request, for files that some pull request touches.

Usage: python -I source/tests/check_pr_coverage.py [--target <ref>] [--base <ref>]
           [--repo <owner/name>] [--author <login>] [--max-lines <n>] [--strict]
           [--count-file <path>]
Output: one line "file: <path>" per uncovered file and "lines: <path>: <count> uncovered"
(with the first lines shown) per partly covered file, then a summary.
With --count-file the number of gaps of every run is stored in that file as one line
"PR coverage gaps (last run): <n>" (the line is replaced, or appended if the file or the
line is missing); the run fails when the number is higher than the stored value of the
previous run (the first run only stores it), so old gaps do not turn a run red.
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


def update_count(path, gaps):
    """Store the gap count in the counter file and return the previous count, or None if there was none."""
    lines = []
    eol = "\n"
    if os.path.exists(path):
        with open(path, encoding="utf-8", errors="replace", newline="") as handle:
            text = handle.read()
        if "\r\n" in text:
            eol = "\r\n"
        lines = text.split(eol)
    previous = None
    found = False
    for index, line in enumerate(lines):
        if line.startswith(COUNT_MARKER):
            try:
                previous = int(line[len(COUNT_MARKER):].strip())
            except ValueError:
                previous = None
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
    return previous


def main():
    """Parse the arguments, compute the gaps and print them; return the exit code."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--target", default=DEFAULT_TARGET)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--author", default=DEFAULT_AUTHOR)
    parser.add_argument("--max-lines", type=int, default=5, help="uncovered lines shown per file")
    parser.add_argument("--count-file", default=None, help="file that keeps the gap count of the last run")
    parser.add_argument("--strict", action="store_true", help="exit 1 when gaps are found")
    options = parser.parse_args()
    try:
        heads = list_open_pr_heads(options.repo, options.author)
        if not heads:
            raise CheckError("no open pull requests found for %s in %s; refusing to report an empty comparison" % (options.author, options.repo))
        target_files, target_added = diff_added(options.base, options.target)
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
        previous = update_count(options.count_file, gaps)
        if previous is None:
            print("gap count %d stored (no previous value)" % gaps)
        elif gaps > previous:
            rose = True
            print("gap count rose from %d to %d" % (previous, gaps))
        else:
            print("gap count %d (previous %d)" % (gaps, previous))
    return 1 if ((gaps and options.strict) or rose) else 0


if __name__ == "__main__":
    sys.exit(main())
