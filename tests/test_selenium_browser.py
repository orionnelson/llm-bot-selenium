"""Explicit opt-in real-browser integration; never download a driver implicitly."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from triage.core import (Context, MockPlanner, compile_skill, export_script,
                         investigate, validate_skill)
from triage.mock_server import make_server
from triage.browser_runtime import selected_browser, create_driver
from triage.selenium_port import SeleniumPort


BROWSER = selected_browser()
BINARY_ENV, DRIVER_ENV = (("MSEDGE_BINARY", "MSEDGEDRIVER") if BROWSER == "edge"
                          else ("CHROME_BINARY", "CHROMEDRIVER"))
READY = (bool(os.environ.get(BINARY_ENV)) and bool(os.environ.get(DRIVER_ENV))
         and importlib.util.find_spec("selenium") is not None)


@unittest.skipUnless(READY, "NOT RUN: explicit browser binary, matching driver and Selenium required")
class SeleniumBrowserTests(unittest.TestCase):
    def test_actual_browser_discover_learn_and_generated_script_reuse(self):
        server = make_server()
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        profile = tempfile.TemporaryDirectory(prefix="synthetic-" + BROWSER + "-profile-")
        driver = None
        try:
            driver = create_driver(BROWSER, os.environ[BINARY_ENV], os.environ[DRIVER_ENV], profile.name)
            port = SeleniumPort(driver, "http://127.0.0.1:" + str(server.server_port))
            ctx = Context("demo", "us-east-1", "checkout", 1, 2)
            result = investigate(port, MockPlanner(), ctx, "browser-001", "Investigate")
            self.assertEqual(result.result.failure, "likely-dependency-timeout")
            skill, contribution = compile_skill(result)
            heldout = Context("demo", "us-east-1", "payments", 3, 4)
            validate_skill(skill, [(port, heldout, "browser-heldout-002", "likely-dependency-timeout")])
            artifact = Path(os.environ.get("BROWSER_ARTIFACT_DIR", "artifacts/browser"))
            artifact.mkdir(parents=True, exist_ok=True)
            module_path = artifact / "generated_browser_skill.py"
            export_script(skill, module_path)
            spec = importlib.util.spec_from_file_location("generated_browser_skill", module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            warm = module.run(driver, "http://127.0.0.1:" + str(server.server_port),
                              Context("demo", "us-east-1", "orders", 5, 6), "browser-fresh-003")
            self.assertEqual(warm.result.failure, result.result.failure)
            self.assertEqual(warm.model_calls, 0)
            self.assertLess(len(warm.observations), len(result.observations))
            self.assertTrue(driver.save_screenshot(str(artifact / "synthetic-result.png")))
            summary = {"status": "passed", "scope": "real browser, deterministic synthetic planner; no LLM/SSO",
                       "browser": BROWSER,
                       "browser_version": driver.capabilities.get("browserVersion"),
                       "cold_reads": len(result.observations), "reused_reads": len(warm.observations),
                       "reused_planner_calls": warm.model_calls, "finding": warm.result.failure,
                       "query_contribution": contribution}
            (artifact / "browser-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        finally:
            if driver:
                driver.quit()
            profile.cleanup()
            server.shutdown()
            server.server_close()
            worker.join(timeout=2)
