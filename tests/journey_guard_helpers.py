import json, os, tempfile, unittest
from pathlib import Path
from threading import Lock
from unittest.mock import patch
from triage.browser_loop import BrowserRuns
from triage.journey import start_journey
from test_journey import Driver, PUBLIC

class JourneyRecoveryTests(unittest.TestCase):
    def run_worker(self, instructions, propose, driver=None):
        driver = driver or Driver()
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {'SELENIUM_GRID_URL': 'http://grid:4444'}), patch('triage.public_browser.socket.getaddrinfo', return_value=PUBLIC), patch('triage.journey.grid_status', return_value={'ready': True}), patch('triage.journey.propose_step', side_effect=propose) as model:
            manager = BrowserRuns(Path(directory), Lock(), lambda: 'revision', driver_factory=lambda url: driver, evidence_kind='simulated')
            queued = start_journey(manager, 'https://or9.ca/', instructions)
            self.assertTrue(manager.generation_lock.acquire(timeout=15))
            manager.generation_lock.release()
            return manager.read(queued['id']), model.call_count, driver

    @staticmethod
    def finish(instruction, observation):
        return {'action': 'finish', 'candidate': None, 'evidence': observation['evidence'], 'result': 'MODEL CLAIM NOT TRUSTED', 'python': 'def run(browser):\n    browser.observe('+json.dumps(observation['evidence'])+')'}

