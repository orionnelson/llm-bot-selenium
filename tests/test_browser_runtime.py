"""Driver wiring tests use real Selenium options/services, mocked browser launch."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from browser_probe import inspect_runtime
from triage.browser_runtime import create_driver, selected_browser


class BrowserRuntimeTests(unittest.TestCase):
    def test_default_is_edge(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(selected_browser(), 'edge')

    def test_original_chrome_environment_still_selects_chrome(self):
        with patch.dict(os.environ, {'CHROME_BINARY': '/chrome'}, clear=True):
            self.assertEqual(selected_browser(), 'chrome')
            self.assertEqual(selected_browser('edge'), 'edge')

    def test_invalid_browser_rejected(self):
        with self.assertRaises(ValueError):
            selected_browser('unsupported')

    def test_edge_missing_is_not_browser_success(self):
        report = inspect_runtime(driver='/missing/msedgedriver', browser='edge', edge='/missing/edge')
        self.assertEqual(report['status'], 'blocked')
        self.assertEqual(report['browser'], 'edge')
        self.assertIn('edge', report['missing'])
        self.assertIn('msedgedriver', report['missing'])

    def test_each_driver_receives_explicit_service_binary_and_fresh_profile(self):
        try:
            import selenium
        except ImportError:
            self.skipTest('Selenium required for constructor contract tests')
        with tempfile.TemporaryDirectory() as folder:
            executable = Path(folder) / 'executable'
            executable.write_text('#!/bin/sh\nexit 0\n')
            executable.chmod(0o700)
            for browser, constructor in [('edge', 'Edge'), ('chrome', 'Chrome')]:
                with self.subTest(browser=browser), patch('selenium.webdriver.' + constructor) as launch:
                    result = create_driver(browser, str(executable), str(executable), folder)
                    self.assertIs(result, launch.return_value)
                    kwargs = launch.call_args.kwargs
                    self.assertEqual(kwargs['service'].path, str(executable))
                    self.assertEqual(kwargs['options'].binary_location, str(executable))
                    self.assertIn('--user-data-dir=' + folder, kwargs['options'].arguments)
                    self.assertNotIn('--no-sandbox', kwargs['options'].arguments)
                    report = inspect_runtime(str(executable) if browser == 'chrome' else None,
                                             str(executable), browser=browser,
                                             edge=str(executable) if browser == 'edge' else None)
                    self.assertEqual(report['status'], 'ready-not-run')

    def test_missing_paths_rejected_before_selenium_can_download(self):
        with self.assertRaises(ValueError):
            create_driver('edge', '/missing/edge', '/missing/msedgedriver', '/tmp/profile')

    def test_explicit_edge_binary_overrides_ambient_chrome_selection(self):
        with patch.dict(os.environ, {'CHROME_BINARY': '/ambient/chrome'}, clear=True):
            report = inspect_runtime(edge='/missing/edge', driver='/missing/msedgedriver')
        self.assertEqual(report['browser'], 'edge')

    def test_conflicting_binary_hints_are_rejected(self):
        with self.assertRaises(ValueError):
            inspect_runtime(chrome='/chrome', edge='/edge')

    def test_relative_paths_are_resolved_before_subprocess_changes_cwd(self):
        from triage.browser_runtime import runtime_paths
        binary, driver = runtime_paths('edge', 'relative/msedge', 'relative/msedgedriver')
        self.assertEqual(binary, str(Path('relative/msedge').resolve()))
        self.assertEqual(driver, str(Path('relative/msedgedriver').resolve()))

    def test_runtime_environment_uses_shared_browser_spec(self):
        from triage.browser_runtime import browser_spec, runtime_environment
        for browser in ('edge', 'chrome'):
            with self.subTest(browser=browser):
                spec = browser_spec(browser)
                self.assertEqual(runtime_environment(browser, '/browser', '/driver'), {
                    'SELENIUM_BROWSER': browser, spec.binary_env: '/browser', spec.driver_env: '/driver'})
