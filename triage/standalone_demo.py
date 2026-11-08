"""Opt-in REAL Grid evidence runner. External synthetic fixture only; no model calls."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from .dag import DAG, Task
from .standalone import action, export_python
from .standalone_runtime import approved_url, identity, require


def demo_dag(home, details, result_id='show-result'):
    def replay(steps):
        return {'replay': {'version': 'sre-replay-task/v1', 'synthetic': True, 'steps': steps}}
    return DAG('Reviewed synthetic two-page replay', (
        Task('start', 'Start', 'start', kind='start', routes={'next': 'task-open'}),
        Task('task-open', 'Open synthetic details', 'application', depends_on=('start',), routes={'next': 'task-details'}, params=replay([
            action('navigate', home, home, url=home),
            action('click', home, details, id='open-details', tag='a', href=details),
        ])),
        Task('task-details', 'Reveal synthetic result', 'application', depends_on=('task-open',), routes={'next': 'end'}, params=replay([
            action('click', details, details, id=result_id, tag='button', href=None),
            action('wait_visible', details, details, id='status', text='Synthetic replay complete'),
            action('assert_text', details, details, id='status', text='Synthetic replay complete'),
        ])),
        Task('end', 'End', 'end', kind='end', depends_on=('task-details',)),
    )).validate()


def artifact(dag, urls):
    revision = hashlib.sha256(dag.to_python().encode()).hexdigest()
    return export_python(dag, revision, urls)


def isolated(source, grid, browser):
    # The child sees ONLY the single artifact, a fresh HOME, system/venv Selenium,
    # and explicit Grid CLI arguments. No PYTHONPATH or project/runtime packages.
    with tempfile.TemporaryDirectory(prefix='standalone-real-') as directory:
        path = Path(directory) / 'replay.py'
        path.write_text(source, encoding='utf-8')
        env = {'PATH': os.environ.get('PATH', ''), 'HOME': directory, 'LANG': 'C.UTF-8'}
        return subprocess.run([sys.executable, '-I', str(path), '--grid', grid, '--browser', browser],
                              cwd=directory, env=env, text=True, capture_output=True, timeout=330)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--consent-synthetic-clicks', action='store_true', required=True)
    p.add_argument('--grid', default=os.environ.get('SELENIUM_GRID_URL'), required=not bool(os.environ.get('SELENIUM_GRID_URL')))
    p.add_argument('--home', required=True)
    p.add_argument('--details', required=True)
    p.add_argument('--reviewed-new-id', default='show-result-v2')
    p.add_argument('--browser', choices=('edge', 'chrome'), default='edge')
    args = p.parse_args()
    try:
        urls = [approved_url(args.home), approved_url(args.details)]
        identity(args.reviewed_new_id)
        require(args.reviewed_new_id != 'show-result', 'Reviewed regeneration requires a distinct new locator')
        original = artifact(demo_dag(*urls), urls)
        baseline = isolated(original, args.grid, args.browser)
        if baseline.returncode:
            print(baseline.stderr.strip(), file=sys.stderr)
        require(baseline.returncode == 0 and 'PASS standalone' in baseline.stdout, 'REAL baseline failed; no acceptance claimed')
        print('REAL baseline: two-page clicks and final visible assertion passed. Session quit.', flush=True)
        input('Change ONLY the external fixture button ID to the reviewed new ID, then press Enter: ')
        broken = isolated(original, args.grid, args.browser)
        print(broken.stderr.strip(), file=sys.stderr)
        require(broken.returncode == 2 and 'task-details/step-1: explicit wait or visible assertion timed out' in broken.stderr,
                'Changed-fixture run did not produce the expected visible missing-element failure')
        print('REAL immutable original: missing element failed visibly; no model/repair invoked.', flush=True)
        input('Confirm review of the new synthetic locator and press Enter to regenerate a NEW artifact: ')
        repaired = artifact(demo_dag(*urls, result_id=args.reviewed_new_id), urls)
        recovered = isolated(repaired, args.grid, args.browser)
        if recovered.returncode:
            print(recovered.stderr.strip(), file=sys.stderr)
        require(recovered.returncode == 0 and 'PASS standalone' in recovered.stdout, 'REAL reviewed regeneration failed')
        print(json.dumps({'evidence': 'REAL Selenium Grid, isolated python -I children', 'baseline': 'passed',
                          'changed_original': 'failed-as-expected', 'reviewed_new_export': 'passed', 'modelCalls': 0,
                          'originalSha256': hashlib.sha256(original.encode()).hexdigest(),
                          'newSha256': hashlib.sha256(repaired.encode()).hexdigest()}))
    except (ValueError, OSError, subprocess.TimeoutExpired, EOFError):
        p.exit(2, 'REAL demo failed or interrupted; no acceptance claimed. Check sandbox-enabled Grid and external synthetic fixture.\n')


if __name__ == '__main__':
    main()
