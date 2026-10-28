#!/usr/bin/env python3
"""Test that check_pr_coverage.py reports its gap count with `orch note` (using a dummy orch program).

Usage: python -I source/tests/check_pr_coverage_note.py
Nothing is compiled and the real orchestrator database is never touched: orch is replaced by a stub
program in a temporary folder that only records its arguments.
Exit codes: 0 = all checks passed, 1 = a check failed.
"""
import os
import shutil
import stat
import sys
import tempfile
import unittest

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
        self.assertTrue(check_pr_coverage.report_count(7))
        with open(log) as handle:
            recorded = handle.read()
        self.assertIn("note", recorded)
        self.assertIn("--project ODP", recorded)
        self.assertIn("PR coverage gaps (last run): 7", recorded)

    def test_failing_orch_only_warns(self):
        """A failing orch call returns False and does not raise."""
        write_stub(self.folder, 3)
        self.assertFalse(check_pr_coverage.report_count(1))

    def test_missing_orch_only_warns(self):
        """When orch cannot be found, report_count returns False and does not raise."""
        original = check_pr_coverage.find_orch
        check_pr_coverage.find_orch = lambda: None
        try:
            self.assertFalse(check_pr_coverage.report_count(1))
        finally:
            check_pr_coverage.find_orch = original

    def test_option_replaced(self):
        """The old --count-file option is gone and --note is a switch."""
        with open(check_pr_coverage.__file__, encoding="utf-8") as handle:
            text = handle.read()
        self.assertNotIn('"--count-file"', text)
        self.assertIn('"--note"', text)


if __name__ == "__main__":
    unittest.main()
