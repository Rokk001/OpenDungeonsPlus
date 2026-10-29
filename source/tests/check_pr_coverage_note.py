#!/usr/bin/env python3
"""Test that check_pr_coverage.py reports its gap count with `orch note` (using a dummy orch program).

Usage: python -I source/tests/check_pr_coverage_note.py
Nothing is compiled and the real orchestrator database is never touched: orch is replaced by a stub
program in a temporary folder that only records its arguments.
Exit codes: 0 = all checks passed, 1 = a check failed.
"""
import contextlib
import io
import os
import shutil
import stat
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_pr_coverage  # noqa: E402


def write_stub(folder, exit_code):
    """Create a stub orch program in folder that appends its arguments to args.txt and exits with exit_code."""
    log = os.path.join(folder, "args.txt")
    if os.name == "nt":
        path = os.path.join(folder, "orch.cmd")
        with open(path, "w", newline="") as handle:
            handle.write("@echo off\r\necho %%* >> \"%s\"\r\nexit /b %d\r\n" % (log, exit_code))
    else:
        path = os.path.join(folder, "orch")
        with open(path, "w") as handle:
            handle.write("#!/bin/sh\necho \"$@\" >> \"%s\"\nexit %d\n" % (log, exit_code))
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
    return log


class ReportCountTest(unittest.TestCase):
    """Tests of report_count with a dummy orch program put first on PATH."""

    def setUp(self):
        """Create the temporary folder and put it on PATH."""
        self.folder = tempfile.mkdtemp(prefix="pr-coverage-note-")
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.folder + os.pathsep + self.old_path

    def tearDown(self):
        """Restore PATH and remove the temporary folder."""
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.folder, ignore_errors=True)

    def test_reports_note_with_expected_arguments(self):
        """The stub receives note --project ODP --text with the gap count."""
        log = write_stub(self.folder, 0)
        self.assertTrue(check_pr_coverage.report_count(7, True))
        with open(log) as handle:
            recorded = handle.read()
        self.assertIn("note", recorded)
        self.assertIn("--project ODP", recorded)
        self.assertIn("PR coverage gaps (last run): 7", recorded)

    def test_red_run_reports_nothing(self):
        """In a red run orch is not called at all, so the last note stays the count of the last green run."""
        log = write_stub(self.folder, 0)
        self.assertFalse(check_pr_coverage.report_count(7, False))
        self.assertFalse(os.path.exists(log))

    def test_failing_orch_only_warns(self):
        """A failing orch call returns False and does not raise."""
        write_stub(self.folder, 3)
        self.assertFalse(check_pr_coverage.report_count(1, True))

    def test_missing_orch_only_warns(self):
        """When orch cannot be found, report_count returns False and does not raise."""
        original = check_pr_coverage.find_orch
        check_pr_coverage.find_orch = lambda: None
        try:
            self.assertFalse(check_pr_coverage.report_count(1, True))
        finally:
            check_pr_coverage.find_orch = original

    def test_option_replaced(self):
        """The old --count-file option is gone and --note is a switch."""
        with open(check_pr_coverage.__file__, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn('"--count-file"', text)
        self.assertIn('"--note"', text)


class MainTest(unittest.TestCase):
    """Tests of main() with the GitHub CLI layer and the git diffs replaced and a dummy orch program put first on PATH."""

    def setUp(self):
        """Create the temporary folder with the dummy orch program and put it on PATH."""
        self.folder = tempfile.mkdtemp(prefix="pr-coverage-main-")
        self.log = write_stub(self.folder, 0)
        self.old_path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.folder + os.pathsep + self.old_path

    def tearDown(self):
        """Restore PATH and remove the temporary folder."""
        os.environ["PATH"] = self.old_path
        shutil.rmtree(self.folder, ignore_errors=True)

    def run_main(self, arguments):
        """Run main() with the arguments; one file of the target is covered by no open pull request (one gap). Returns (exit code, output)."""
        def fake_diff(base, ref):
            """Return the target (ref HEAD) with one changed file and a pull request head without changes."""
            if ref == "HEAD":
                return {"a.txt"}, {"a.txt": {"line"}}
            return set(), {}

        output = io.StringIO()
        with mock.patch.object(check_pr_coverage, "list_open_pr_heads", return_value=[(1, "branch", "abc")]), \
                mock.patch.object(check_pr_coverage, "resolve_head", return_value="abc"), \
                mock.patch.object(check_pr_coverage, "diff_added", side_effect=fake_diff), \
                mock.patch.object(sys, "argv", ["check_pr_coverage.py"] + arguments), \
                contextlib.redirect_stdout(output):
            code = check_pr_coverage.main()
        return code, output.getvalue()

    def test_green_run_calls_orch_note_with_the_count(self):
        """With --note the stub receives the note with the gap count of the run."""
        code, text = self.run_main(["--note"])
        self.assertEqual(code, 0)
        self.assertIn("1 gaps", text)
        with open(self.log) as handle:
            recorded = handle.read()
        self.assertIn("note", recorded)
        self.assertIn("PR coverage gaps (last run): 1", recorded)

    def test_run_red_does_not_call_orch(self):
        """With --note --run-red orch is not called and the output says so."""
        code, text = self.run_main(["--note", "--run-red"])
        self.assertEqual(code, 0)
        self.assertIn("not reported", text)
        self.assertFalse(os.path.exists(self.log))

    def test_without_note_does_not_call_orch(self):
        """Without --note orch is not called either."""
        self.run_main([])
        self.assertFalse(os.path.exists(self.log))


if __name__ == "__main__":
    unittest.main()
