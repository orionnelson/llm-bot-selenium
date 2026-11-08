"""Portable Airflow task body, embedded verbatim in each generated DAG.

Only Airflow's SDK, stdlib and the embedded Selenium executable are used.
"""


def execute_replay(source, grid, browser, isolation, artifact_id):
    import json
    import os
    import signal
    import subprocess
    import sys
    import tempfile
    import time
    from airflow.sdk import Variable, get_current_context

    context = get_current_context()
    run_id = context['run_id']
    # Minute-scoped keys avoid a cached missing Variable suppressing cancellation
    # indefinitely. Stop writes this and the next six buckets (run ceiling 330s).
    prefix = 'sre_stop_' + artifact_id + '_' + run_id + '_'
    process = None
    results = []
    stopping = False
    old = {}

    def terminate(*_):
        nonlocal stopping
        stopping = True
        if process is not None and process.poll() is None:
            process.terminate()  # Runtime SIGTERM handler quits its Grid session.

    def collect(path):
        rows = []
        with open(path, encoding='utf-8', errors='replace') as stream:
            for line in stream:
                if line.startswith('REPLAY_RESULT '):
                    try:
                        row = json.loads(line[14:])
                        if set(row) <= {'task', 'step', 'state', 'reason'}:
                            rows.append(row)
                    except (ValueError, TypeError):
                        pass
        return rows[-101:]

    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old[sig] = signal.signal(sig, terminate)
        # A queued run can start long after the bounded polling buckets expire.
        # Check its permanent, unique run marker before creating any browser.
        if Variable.get(prefix + 'requested', default='false') == 'true':
            context['ti'].xcom_push(key='replay_result', value={'artifactId': artifact_id, 'state': 'stopped', 'steps': []})
            raise RuntimeError('Synthetic replay stopped before browser startup')
        with tempfile.TemporaryDirectory(prefix='sre-replay-') as root:
            script, output = root + '/replay.py', root + '/output'
            with open(script, 'x', encoding='utf-8') as stream:
                stream.write(source)
            # Credentials/model configuration never enter the Selenium child.
            env = {k: v for k, v in os.environ.items() if k in ('PATH', 'HOME', 'LANG', 'SSL_CERT_FILE', 'SSL_CERT_DIR') or k.startswith('SRE_REPLAY_INPUT_')}
            env['SELENIUM_ISOLATION_MODE'] = isolation
            with open(output, 'wb') as stream:
                process = subprocess.Popen([sys.executable, '-I', script, '--grid', grid, '--browser', browser], stdout=stream, stderr=stream, env=env)
                deadline = time.monotonic() + 330
                while process.poll() is None:
                    requested = Variable.get(prefix + str(int(time.time()) // 60), default='false')
                    if requested == 'true' or time.monotonic() >= deadline or os.path.getsize(output) > 1000000:
                        terminate()
                    if stopping:
                        try:
                            process.wait(timeout=15)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait(timeout=5)
                        break
                    time.sleep(2)
            results = collect(output)
            value = {'artifactId': artifact_id, 'state': 'stopped' if stopping else ('success' if process.returncode == 0 else 'failed'), 'steps': results}
            context['ti'].xcom_push(key='replay_result', value=value)
            print('REPLAY_SUMMARY ' + json.dumps(value), flush=True)
            if stopping or process.returncode != 0:
                raise RuntimeError('Synthetic replay stopped or failed; see sanitized replay_result')
            return value
    finally:
        if process is not None and process.poll() is None:
            terminate()
            try:
                process.wait(timeout=15)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
        for sig, previous in old.items():
            signal.signal(sig, previous)
