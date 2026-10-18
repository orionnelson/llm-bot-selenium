"""Explicit test-browser gate: blocked != skipped != browser success.

Does not install/download browsers, weaken sandboxing, or use existing profiles.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile


def inspect_runtime(chrome=None, driver=None):
    chrome = chrome or os.environ.get("CHROME_BINARY") or shutil.which("chromium") or shutil.which("google-chrome")
    driver = driver or os.environ.get("CHROMEDRIVER") or shutil.which("chromedriver")
    missing = []
    if importlib.util.find_spec("selenium") is None:
        missing.append("selenium-package")
    for label, value in (("chrome", chrome), ("chromedriver", driver)):
        if not value or not Path(value).is_file() or not os.access(value, os.X_OK):
            missing.append(label)
    return {"status": "blocked" if missing else "ready-not-run", "missing": missing,
            "chrome": chrome, "chromedriver": driver, "python": sys.version.split()[0],
            "scope": "isolated synthetic browser only; no live LLM or SSO"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chrome")
    parser.add_argument("--driver")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", default="artifacts/browser")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    report = inspect_runtime(args.chrome, args.driver)
    exit_code = 2 if report["missing"] else 0
    if args.run and not report["missing"]:
        # Do not pass ambient cloud credentials/tokens into the synthetic test.
        env = {k: v for k, v in os.environ.items() if k in
               ("PATH", "LANG", "LC_ALL", "TZ", "LD_LIBRARY_PATH", "PYTHONHOME", "VIRTUAL_ENV")}
        with tempfile.TemporaryDirectory(prefix="triage-test-home-") as home:
            env.update(HOME=home, CHROME_BINARY=report["chrome"], CHROMEDRIVER=report["chromedriver"],
                       BROWSER_ARTIFACT_DIR=str(output))
            process = subprocess.Popen([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                                        "-p", "test_selenium_browser.py", "-v"],
                                       cwd=Path(__file__).resolve().parent, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=True)
            try:
                stdout, stderr = process.communicate(timeout=120)
                (output / "browser-test.log").write_text(stdout + stderr)
                exit_code = process.returncode
                report["status"] = "passed" if exit_code == 0 and "skipped" not in stderr.lower() else "failed"
                if report["status"] == "failed" and exit_code == 0:
                    exit_code = 1
                report["test_exit_code"] = exit_code
            except subprocess.TimeoutExpired:
                # Stop the test's process group, including its driver descendants.
                os.killpg(process.pid, signal.SIGTERM)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    stdout, stderr = process.communicate()
                (output / "browser-test.log").write_text(stdout + stderr)
                report["status"] = "failed-timeout"
                exit_code = 1
    (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
