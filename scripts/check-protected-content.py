#!/usr/bin/env python3
"""Pre-push check for protected content.

Installed as the git pre-push hook (see docs/internal/GIT-WORKFLOW.md). Git passes
"<local ref> <local sha> <remote ref> <remote sha>" lines on stdin and the remote
name and url as arguments. The push is blocked (exit 1) if the pushed commits contain:

  * a term from protected-terms.txt in a commit message, an added diff line,
    a ref name or a file name (binary files: names only),
  * files under levels/campaign/ that are not in CAMPAIGN_ALLOW_LIST,
  * anything under tools/level-convert/,
  * new media files that are not covered by the CREDITS file at the pushed tip.

If the term list is missing or empty the push is blocked as well (fail safe).

Usage:
  check-protected-content.py [--terms <file>] [<remote> [<url>]] < ref-lines
  check-protected-content.py --self-test
"""

import fnmatch
import os
import re
import shutil
import subprocess
import sys
import tempfile

ZERO_SHA = "0" * 40

TERMS_RELATIVE_PATH = "docs/internal/protected-terms.txt"

# Placeholder campaign files that exist in origin/integration/all.
CAMPAIGN_ALLOW_LIST = [
    "levels/campaign/Bonus1.level",
    "levels/campaign/Campaign.cfg",
    "levels/campaign/Campaign1.level",
    "levels/campaign/Campaign2.level",
    "levels/campaign/Campaign3.level",
]

CAMPAIGN_PREFIX = "levels/campaign/"
CONVERTER_PREFIX = "tools/level-convert/"

MEDIA_EXTENSIONS = set([
    "png", "jpg", "jpeg", "gif", "bmp", "tga", "dds", "tif", "tiff", "svg",
    "ogg", "wav", "mp3", "flac", "mid", "mesh", "skeleton", "glb", "gltf",
    "fbx", "obj", "blend", "ico", "ttf", "otf", "mp4", "avi", "ogv",
])

CREDITS_NAMES = ["CREDITS", "CREDITS.md", "CREDITS.txt"]


def run_git(args, cwd):
    proc = subprocess.run(["git"] + args, cwd=cwd, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    return proc.returncode, proc.stdout.decode("utf-8", errors="replace")


def read_terms_file(path):
    terms = []
    with open(path, "r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if line == "" or line.startswith("#"):
                continue
            terms.append(line.lower())
    return terms


def find_terms_file(cwd):
    candidates = []
    code, out = run_git(["rev-parse", "--git-common-dir"], cwd)
    if code == 0:
        common = os.path.abspath(os.path.join(cwd, out.strip()))
        candidates.append(os.path.join(os.path.dirname(common), TERMS_RELATIVE_PATH))
    code, out = run_git(["rev-parse", "--show-toplevel"], cwd)
    if code == 0:
        candidates.append(os.path.join(out.strip(), TERMS_RELATIVE_PATH))
    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate
    return None


def find_terms(cwd, explicit_path):
    """Returns (terms, error message)."""
    path = explicit_path
    if path is None:
        path = find_terms_file(cwd)
    if path is None or not os.path.isfile(path):
        return None, ("The protected term list is missing (expected %s in the main "
                      "working tree). Push blocked." % TERMS_RELATIVE_PATH)
    terms = read_terms_file(path)
    if len(terms) == 0:
        return None, "The protected term list %s is empty. Push blocked." % path
    return terms, None


def find_term(text, terms):
    lowered = text.lower()
    for term in terms:
        if term in lowered:
            return term
    return None


def split_lines(text):
    return [line for line in text.split("\n") if line != ""]


def credits_text(tip, cwd):
    for name in CREDITS_NAMES:
        code, out = run_git(["show", "%s:%s" % (tip, name)], cwd)
        if code == 0:
            return out
    return ""


def is_covered_by_credits(path, credits):
    tokens = re.split(r"[\s`,;()\[\]<>\"']+", credits)
    for token in tokens:
        token = token.strip()
        if token == "":
            continue
        if token == path:
            return True
        if "/" in token and not any(c in token for c in "*?["):
            if path.startswith(token.rstrip("/") + "/"):
                return True
        if any(c in token for c in "*?["):
            if fnmatch.fnmatch(path, token):
                return True
            if "/" not in token and fnmatch.fnmatch(os.path.basename(path), token):
                return True
    return False


def commits_to_check(local_sha, remote_sha, remote_name, cwd):
    if remote_sha != ZERO_SHA:
        code, out = run_git(["rev-list", "%s..%s" % (remote_sha, local_sha)], cwd)
        if code == 0:
            return split_lines(out)
    code, out = run_git(["rev-list", local_sha, "--not", "--remotes"], cwd)
    if code != 0:
        return []
    return split_lines(out)


def check_commit(commit, terms, cwd, added_files, problems):
    short = commit[:10]
    code, message = run_git(["log", "-1", "--format=%B", commit], cwd)
    term = find_term(message, terms)
    if term is not None:
        problems.append("commit %s: term '%s' in the commit message" % (short, term))

    code, parents = run_git(["rev-list", "--parents", "-n", "1", commit], cwd)
    if len(parents.split()) > 2:
        return  # merge commit: the merged commits are checked on their own

    code, names = run_git(["diff-tree", "--root", "--no-commit-id", "-r", "-M",
                           "--name-status", commit], cwd)
    for line in split_lines(names):
        fields = line.split("\t")
        status = fields[0][0]
        path = fields[-1]
        if status == "D":
            continue
        term = find_term(path, terms)
        if term is not None:
            problems.append("commit %s: term '%s' in file name %s" % (short, term, path))
        if path.startswith(CAMPAIGN_PREFIX) and path not in CAMPAIGN_ALLOW_LIST:
            problems.append("commit %s: %s is not in the campaign allow list"
                            % (short, path))
        if path.startswith(CONVERTER_PREFIX):
            problems.append("commit %s: %s is under %s" % (short, path, CONVERTER_PREFIX))
        extension = path.rsplit(".", 1)[-1].lower() if "." in os.path.basename(path) else ""
        if status in ("A", "C", "R") and extension in MEDIA_EXTENSIONS:
            added_files.setdefault(path, short)

    code, diff = run_git(["show", "--format=", "-p", "--no-color", "-U0", commit], cwd)
    for line in diff.split("\n"):
        if line.startswith("+") and not line.startswith("+++"):
            term = find_term(line, terms)
            if term is not None:
                problems.append("commit %s: term '%s' in an added line: %s"
                                % (short, term, line[:80]))


def check_push(ref_lines, terms, remote_name, cwd):
    problems = []
    for ref_line in ref_lines:
        fields = ref_line.split()
        if len(fields) != 4:
            continue
        local_ref, local_sha, remote_ref, remote_sha = fields
        for ref in (local_ref, remote_ref):
            term = find_term(ref, terms)
            if term is not None:
                problems.append("ref %s: term '%s' in the ref name" % (ref, term))
        if local_sha == ZERO_SHA:
            continue  # deleted ref: only the name is checked
        code, tip = run_git(["rev-parse", "%s^{commit}" % local_sha], cwd)
        if code != 0:
            continue  # tag pointing to a non-commit
        tip = tip.strip()
        added_files = {}
        for commit in commits_to_check(tip, remote_sha, remote_name, cwd):
            check_commit(commit, terms, cwd, added_files, problems)
        if added_files:
            credits = credits_text(tip, cwd)
            for path in sorted(added_files):
                code, listed = run_git(["ls-tree", "--name-only", tip, "--", path], cwd)
                if listed.strip() == "":
                    continue  # no longer present at the tip
                if not is_covered_by_credits(path, credits):
                    problems.append("commit %s: new media file %s is not mentioned in "
                                    "CREDITS" % (added_files[path], path))
    return problems


def report_and_exit(problems):
    sys.stderr.write("Push blocked by check-protected-content:\n")
    for problem in problems:
        sys.stderr.write("  - %s\n" % problem)
    sys.stderr.write("Fix the commits (do not bypass this check without an owner "
                     "decision).\n")
    return 1


def self_test():
    failures = []
    work = tempfile.mkdtemp(prefix="protected-selftest-")

    def git(*args):
        proc = subprocess.run(["git"] + list(args), cwd=work, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE)
        if proc.returncode != 0:
            raise RuntimeError("git %s failed: %s" % (args, proc.stderr.decode()))
        return proc.stdout.decode().strip()

    def commit_files(files, message, delete=()):
        for name, content in files.items():
            full = os.path.join(work, name)
            os.makedirs(os.path.dirname(full) or work, exist_ok=True)
            mode = "wb" if isinstance(content, bytes) else "w"
            with open(full, mode) as handle:
                handle.write(content)
            git("add", name)
        git("commit", "-q", "-m", message)
        return git("rev-parse", "HEAD")

    def expect(name, lines, terms, should_block, needle=None):
        problems = check_push(lines, terms, "origin", work)
        blocked = len(problems) > 0
        if blocked != should_block or (needle and not any(needle in p for p in problems)):
            failures.append("%s: blocked=%s problems=%s" % (name, blocked, problems))

    try:
        git("init", "-q")
        git("config", "user.email", "test@example.invalid")
        git("config", "user.name", "Test")
        base = commit_files({"readme.txt": "hello\n"}, "base")
        terms = ["zzterm"]

        def push_lines(sha, ref="refs/heads/topic"):
            return ["%s %s %s %s" % (ref, sha, ref, git("rev-parse", sha + "~1"))]

        sha = commit_files({"a.txt": "fine\n"}, "clean change")
        expect("clean", push_lines(sha), terms, False)

        sha = commit_files({"b.txt": "x\n"}, "mentions ZZTerm here")
        expect("message", push_lines(sha), terms, True, "commit message")

        sha = commit_files({"c.txt": "line with zzterm inside\n"}, "add c")
        expect("added line", push_lines(sha), terms, True, "added line")

        sha = commit_files({"zzterm-file.txt": "x\n"}, "add file")
        expect("file name", push_lines(sha), terms, True, "file name")

        sha = commit_files({"bin.dat": b"\x00zzterm\x00"}, "binary content")
        expect("binary content ignored", [l for l in push_lines(sha)], terms, False)

        expect("ref name", push_lines(sha, "refs/heads/feature/zzterm-x"), terms, True,
               "ref name")

        expect("deleted ref", ["(delete) %s refs/heads/old %s" % (ZERO_SHA, base)],
               terms, False)
        expect("deleted ref name", ["(delete) %s refs/heads/zzterm %s" % (ZERO_SHA, base)],
               terms, True, "ref name")

        sha = commit_files({"levels/campaign/Campaign1.level": "ok\n"}, "allowed level")
        expect("allowed level", push_lines(sha), terms, False)

        sha = commit_files({"levels/campaign/Other.level": "x\n"}, "other level")
        expect("campaign", push_lines(sha), terms, True, "allow list")

        sha = commit_files({"tools/level-convert/run.py": "x\n"}, "converter")
        expect("converter", push_lines(sha), terms, True, "tools/level-convert/")

        sha = commit_files({"gfx/pic.png": b"\x89PNG"}, "add picture")
        expect("media without credits", push_lines(sha), terms, True, "CREDITS")

        sha = commit_files({"CREDITS": "gfx/*.png - own work, CC0\n"}, "credits")
        expect("media with glob", push_lines(sha), terms, False)

        sha = commit_files({"snd/a.ogg": b"OggS"}, "add sound")
        expect("media new uncovered", push_lines(sha), terms, True, "snd/a.ogg")

        sha = commit_files({"CREDITS": "gfx/*.png - own work, CC0\nsnd/ - own, CC0\n"},
                           "credits dir")
        expect("media with directory", push_lines(sha), terms, False)

        git("branch", "-q", "newbranch")
        expect("new branch", ["refs/heads/newbranch %s refs/heads/newbranch %s"
                              % (sha, ZERO_SHA)], terms, True)

        # fail safe on the term list
        empty = os.path.join(work, "empty-terms.txt")
        with open(empty, "w") as handle:
            handle.write("# nothing\n")
        found, error = find_terms(work, empty)
        if found is not None or error is None:
            failures.append("empty term list must block")
        found, error = find_terms(work, os.path.join(work, "does-not-exist.txt"))
        if found is not None or error is None:
            failures.append("missing term list must block")
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if failures:
        for failure in failures:
            sys.stderr.write("SELF-TEST FAIL: %s\n" % failure)
        return 1
    print("self-test passed")
    return 0


def main(argv):
    terms_path = None
    positional = []
    index = 1
    while index < len(argv):
        if argv[index] == "--self-test":
            return self_test()
        if argv[index] == "--terms" and index + 1 < len(argv):
            terms_path = argv[index + 1]
            index += 2
            continue
        positional.append(argv[index])
        index += 1
    remote_name = positional[0] if positional else "origin"

    cwd = os.getcwd()
    terms, error = find_terms(cwd, terms_path)
    if terms is None:
        sys.stderr.write("check-protected-content: %s\n" % error)
        return 1

    ref_lines = [line for line in sys.stdin.read().split("\n") if line.strip() != ""]
    problems = check_push(ref_lines, terms, remote_name, cwd)
    if problems:
        return report_and_exit(problems)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
