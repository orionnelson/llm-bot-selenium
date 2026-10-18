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


def inspect_runtime(chrome=None, driver=None, *, browser=None, edge=None):
    from triage.browser_runtime import selected_browser, runtime_paths
    browser = selected_browser(browser or ('chrome' if chrome else None))
    binary, driver = runtime_paths(browser, edge if browser == 'edge' else chrome, driver)
    labels = ('edge', 'msedgedriver') if browser == 'edge' else ('chrome', 'chromedriver')
    missing = []
    if importlib.util.find_spec("selenium") is None:
        missing.append("selenium-package")
    for label, value in zip(labels, (binary, driver)):
        if not value or not Path(value).is_file() or not os.access(value, os.X_OK):
            missing.append(label)
    return {"status": "blocked" if missing else "ready-not-run", "missing": missing,
            "browser": browser, "binary": binary, "driver": driver,
            labels[0]: binary, labels[1]: driver, "python": sys.version.split()[0],
            "scope": "isolated synthetic browser only; no live LLM or SSO"}


def stop_process_tree(process, force=False):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL if force else signal.SIGTERM)
        except ProcessLookupError:
            pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser", choices=("edge", "chrome"))
    parser.add_argument("--edge", help="Microsoft Edge executable")
    parser.add_argument("--chrome", help="Chrome executable (legacy option)")
    parser.add_argument("--driver")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", default="artifacts/browser")
    args = parser.parse_args()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    if args.edge and args.chrome:
        parser.error("Choose only one browser binary")
    if (args.browser == "edge" and args.chrome) or (args.browser == "chrome" and args.edge):
        parser.error("Browser and binary option disagree")
    report = inspect_runtime(args.chrome, args.driver, browser=args.browser or ("edge" if args.edge else None), edge=args.edge)
    exit_code = 2 if report["missing"] else 0
    if args.run and not report["missing"]:
        # Do not pass ambient cloud credentials/tokens into the synthetic test.
        env = {k: v for k, v in os.environ.items() if k in
               ("PATH", "LANG", "LC_ALL", "TZ", "LD_LIBRARY_PATH", "PYTHONHOME", "VIRTUAL_ENV",
                "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP")}
        with tempfile.TemporaryDirectory(prefix="triage-test-home-") as home:
            env.update(HOME=home, USERPROFILE=home, LOCALAPPDATA=home,
                       SELENIUM_BROWSER=report["browser"], BROWSER_ARTIFACT_DIR=str(output))
            if report["browser"] == "edge":
                env.update(MSEDGE_BINARY=report["binary"], MSEDGEDRIVER=report["driver"])
            else:
                env.update(CHROME_BINARY=report["binary"], CHROMEDRIVER=report["driver"])
            process = subprocess.Popen([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                                        "-p", "test_selenium_browser.py", "-v"],
                                       cwd=Path(__file__).resolve().parent, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       text=True, start_new_session=os.name != "nt",
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
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
                stop_process_tree(process)
                try:
                    stdout, stderr = process.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    stop_process_tree(process, force=True)
                    stdout, stderr = process.communicate()
                (output / "browser-test.log").write_text(stdout + stderr)
                report["status"] = "failed-timeout"
                exit_code = 1
    (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
