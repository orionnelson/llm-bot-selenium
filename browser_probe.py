"""Explicit test-browser gate: blocked != skipped != browser success.

Does not install/download browsers, weaken sandboxing, or use existing profiles.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile


def inspect_runtime(chrome=None, driver=None, *, browser=None, edge=None):
    from triage.browser_runtime import (BROWSER_ENV, selected_browser, runtime_paths, is_executable)
    if (chrome and edge) or (browser == 'edge' and chrome) or (browser == 'chrome' and edge):
        raise ValueError('Browser and binary options disagree')
    browser = selected_browser(browser or ('chrome' if chrome else 'edge' if edge else None))
    binary, driver = runtime_paths(browser, edge if browser == 'edge' else chrome, driver)
    labels = (browser, BROWSER_ENV[browser][1].lower())
    missing = []
    if importlib.util.find_spec("selenium") is None:
        missing.append("selenium-package")
    for label, value in zip(labels, (binary, driver)):
        if not is_executable(value):
            missing.append(label)
    return {"status": "blocked" if missing else "ready-not-run", "missing": missing,
            "browser": browser, "binary": binary, "driver": driver,
            labels[0]: binary, labels[1]: driver, "python": sys.version.split()[0],
            "scope": "isolated synthetic browser only; no live LLM or SSO"}


def stop_process_tree(process):
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
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
    try:
        report = inspect_runtime(args.chrome, args.driver, browser=args.browser, edge=args.edge)
    except ValueError as exc:
        parser.error(str(exc))
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    exit_code = 2 if report["missing"] else 0
    if args.run and not report["missing"]:
        # Do not pass ambient cloud credentials/tokens into the synthetic test.
        env = {k: v for k, v in os.environ.items() if k in
               ("PATH", "LANG", "LC_ALL", "TZ", "LD_LIBRARY_PATH", "PYTHONHOME", "VIRTUAL_ENV",
                "SYSTEMROOT", "SystemRoot", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP")}
        with tempfile.TemporaryDirectory(prefix="triage-test-home-") as home:
            from triage.browser_runtime import BROWSER_ENV
            env.update(HOME=home, USERPROFILE=home, LOCALAPPDATA=home,
                       BROWSER_ARTIFACT_DIR=str(output))
            env["SELENIUM_BROWSER"] = report["browser"]
            env.update(zip(BROWSER_ENV[report["browser"]], (report["binary"], report["driver"])))
            process = subprocess.Popen([sys.executable, "-m", "unittest", "discover", "-s", "tests",
                                        "-p", "test_selenium_browser.py", "-v"],
                                       cwd=Path(__file__).resolve().parent, env=env,
                                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, start_new_session=os.name != "nt",
                                       creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0)
            try:
                stdout, _ = process.communicate(timeout=120)
                exit_code = process.returncode or int("skipped" in stdout.lower())
                report.update(status="failed" if exit_code else "passed", test_exit_code=exit_code)
            except subprocess.TimeoutExpired:
                # Synthetic test timed out: stop its driver descendants too.
                stop_process_tree(process)
                stdout, _ = process.communicate(timeout=10)
                report["status"] = "failed-timeout"
                exit_code = 1
            (output / "browser-test.log").write_text(stdout)
    (output / "runtime-report.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
