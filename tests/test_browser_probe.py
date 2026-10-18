import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from browser_probe import inspect_runtime


class BrowserProbeTests(unittest.TestCase):
    def test_missing_binaries_are_blocked_not_success(self):
        report = inspect_runtime("/not-present/chrome", "/not-present/chromedriver")
        self.assertEqual(report["status"], "blocked")
        self.assertIn("chrome", report["missing"])
        self.assertIn("chromedriver", report["missing"])

    def test_present_executables_are_ready_not_tested(self):
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / "fake-executable"
            binary.write_text("#!/bin/sh\nexit 0\n")
            binary.chmod(0o700)
            with patch("browser_probe.importlib.util.find_spec", return_value=object()):
                report = inspect_runtime(str(binary), str(binary))
        self.assertEqual(report["status"], "ready-not-run")

    def test_missing_selenium_is_explicit(self):
        with patch("browser_probe.importlib.util.find_spec", return_value=None):
            report = inspect_runtime("/not-present/chrome", "/not-present/driver")
        self.assertIn("selenium-package", report["missing"])
