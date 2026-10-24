"""Opt-in real Edge Grid tests; no local browser/driver installation required."""
import os
import unittest

from triage.grid import smoke


@unittest.skipUnless(os.environ.get('RUN_GRID_EDGE') == '1',
                     'NOT RUN: set RUN_GRID_EDGE=1 for an actual isolated Edge session')
class EdgeGridTests(unittest.TestCase):
    def test_synthetic_edge_session(self):
        result = smoke(os.environ['SELENIUM_GRID_URL'])
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['browser'].lower(), 'microsoftedge')

    @unittest.skipUnless(os.environ.get('RUN_GRID_OR9') == '1',
                         'NOT RUN: explicit RUN_GRID_OR9=1 and approved public-site egress required')
    def test_read_only_or9_homepage(self):
        result = smoke(os.environ['SELENIUM_GRID_URL'], or9=True)
        self.assertEqual(result['status'], 'passed')
        self.assertEqual(result['browser'].lower(), 'microsoftedge')
