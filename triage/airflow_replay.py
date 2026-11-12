"""Server-only immutable synthetic replay registry and bounded Airflow 3 API client."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import time
from urllib.parse import quote, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError
import uuid

from .standalone import export_python, export_spec
from .standalone_runtime import require

LIMIT = 1000000
TERMINAL = {'success', 'failed'}


class AirflowError(ValueError):
    def __init__(self, message, status=None):
        super().__init__(message)
        self.status = status


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class AirflowClient:
    """credential_provider() -> (username, password), invoked only on the server.

    Applications may inject a Vault-backed provider without importing tools or
    placing Vault configuration in this repository. transport is a unit-test seam.
    """
    def __init__(self, base, credential_provider, transport=None):
        u = urlsplit(base)
        require(u.scheme in ('http', 'https') and u.hostname and not u.username and not u.password and not u.query and not u.fragment and u.path in ('', '/'), 'Invalid server Airflow origin')
        self.base, self.provider, self.transport = base.rstrip('/'), credential_provider, transport
        self.token, self.token_until = None, 0

    def _http(self, method, path, body=None, token=None):
        try:
            if self.transport:
                return self.transport(method, path, body, token)
            data = None if body is None else json.dumps(body, allow_nan=False).encode()
            headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}
            if token:
                headers['Authorization'] = 'Bearer ' + token
            req = Request(self.base + path, data=data, headers=headers, method=method)
            with build_opener(NoRedirect).open(req, timeout=2) as response:
                raw = response.read(LIMIT + 1)
            if len(raw) > LIMIT:
                raise ValueError()
            return json.loads(raw) if raw else {}
        except HTTPError as error:
            raise AirflowError('Airflow API rejected request; refresh to reconcile', error.code) from None
        except AirflowError:
            raise
        except Exception:
            # Never expose response bodies, URLs, credentials or transport exceptions.
            raise AirflowError('Airflow request failed or response exceeded bounds; refresh to reconcile') from None

    def request(self, method, path, body=None):
        try:
            if self.token is None or time.monotonic() >= self.token_until:
                username, password = self.provider()
                self.token = self._http('POST', '/auth/token', {'username': username, 'password': password})['access_token']
                self.token_until = time.monotonic() + 60
            return self._http(method, '/api/v2' + path, body, self.token)
        except AirflowError as error:
            if error.status == 401:
                self.token = None
            raise
        except Exception:
            raise AirflowError('Airflow authentication or API unavailable; no success claimed') from None

    def cancel_marker(self, key):
        try:
            self.request('POST', '/variables', {'key': key, 'value': 'true', 'description': 'Synthetic replay cancellation'})
        except AirflowError as error:
            if error.status != 409:
                raise
            # Idempotent after a lost response/partial cancellation. Never change
            # a variable outside this artifact and unique run's owned namespace.
            self.request('PATCH', '/variables/' + key, {'key': key, 'value': 'true'})


def write_json(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        temporary = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        temporary.unlink(missing_ok=True)


def bundle(source, artifact_id, config, worker=None):
    worker = worker or Path(__file__).with_name('airflow_worker.py').read_text()
    return ("# Immutable synthetic replay; Airflow 3.4, no application imports.\n"
            "from datetime import datetime, timezone, timedelta\nfrom airflow.sdk import DAG, task\n" + worker +
            '\nwith DAG(dag_id=' + repr('sre_replay_' + artifact_id) +
            ", schedule=None, catchup=False, is_paused_upon_creation=True, max_active_runs=1, max_active_tasks=1, start_date=datetime(2025, 1, 1, tzinfo=timezone.utc), tags=[" + repr('artifact:' + artifact_id) + "]) as dag:\n"
            "    @task(task_id='replay_chain', retries=0, execution_timeout=timedelta(seconds=370))\n"
            "    def replay_chain():\n        return execute_replay(" + ', '.join(repr(x) for x in (source, config['grid'], config['browser'], config['isolation'], artifact_id)) + ")\n    replay_chain()\n")


class ReplayRegistry:
    def __init__(self, root, dag_dir, client, config):
        from .grid import endpoint
        self.root, self.dag_dir, self.client = Path(root), Path(dag_dir), client
        self.config = {'grid': endpoint(config['grid']), 'browser': config['browser'], 'isolation': config['isolation']}
        require(self.config['browser'] in ('edge', 'chrome') and self.config['isolation'] in ('browser', 'container'), 'Invalid server browser/isolation')
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        require(self.dag_dir.is_dir(), 'Configured Airflow DAG directory unavailable')

    @contextlib.contextmanager
    def locked(self):
        with (self.root / '.lock').open('a') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            yield

    def artifact(self, artifact_id):
        require(isinstance(artifact_id, str) and re.fullmatch('[0-9a-f]{64}', artifact_id), 'Invalid artifact ID')
        value = json.loads((self.root / (artifact_id + '.json')).read_text())
        binding = {k: value[k] for k in ('source', 'config', 'spec', 'worker', 'format')}
        require(hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest() == artifact_id, 'Artifact integrity failure')
        require(value['id'] == artifact_id and value['revision'] == value['spec']['revision'] and value['tasks'] == [t['id'] for t in value['spec']['tasks']], 'Artifact metadata integrity failure')
        expected = hashlib.sha256(bundle(value['source'], artifact_id, value['config'], value['worker']).encode()).hexdigest()
        require(value['bundleHash'] == expected == hashlib.sha256((self.dag_dir / ('sre_replay_' + artifact_id + '.py')).read_bytes()).hexdigest(), 'Deployed bundle integrity failure')
        return value

    @staticmethod
    def public(value):
        return {k: value[k] for k in ('id', 'revision', 'tasks', 'createdAt')}

    def listing(self):
        with self.locked():
            return {'configured': True, 'artifacts': [self.public(self.artifact(p.stem)) for p in sorted(self.root.glob('[0-9a-f]' * 64 + '.json'))][:100], 'active': self.active()}

    def save(self, dag, revision, urls, records, revision_check=None):
        source = export_python(dag, revision, urls, records)
        spec = export_spec(dag, revision, urls, records)
        worker = Path(__file__).with_name('airflow_worker.py').read_text()
        binding = {'source': source, 'config': self.config, 'spec': spec, 'worker': worker, 'format': 'airflow-replay/v1'}
        artifact_id = hashlib.sha256(json.dumps(binding, sort_keys=True).encode()).hexdigest()
        text = bundle(source, artifact_id, self.config, worker)
        require(len(text.encode()) <= LIMIT, 'Replay bundle exceeds 1 MB')
        with self.locked():
            require(revision_check is None or revision_check() == revision, 'Canonical revision changed during export; review again')
            path = self.root / (artifact_id + '.json')
            if path.exists():
                return self.public(self.artifact(artifact_id))
            require(len(list(self.root.glob('[0-9a-f]' * 64 + '.json'))) < 100, 'Registry full; operator archival required')
            deployed = self.dag_dir / ('sre_replay_' + artifact_id + '.py')
            # Exclusive creation; never overwrite any existing DAG or artifact.
            if deployed.exists():
                require(deployed.read_text() == text, 'Existing bundle differs; operator reconciliation required')
            else:
                with tempfile.NamedTemporaryFile(dir=self.dag_dir, suffix='.tmp', delete=False) as stream:
                    temporary = Path(stream.name)
                    stream.write(text.encode())
                    stream.flush()
                    os.fsync(stream.fileno())
                try:
                    # Atomic publication without overwriting an existing DAG.
                    os.link(temporary, deployed)
                    deployed.chmod(0o644)
                    fd = os.open(self.dag_dir, os.O_RDONLY)
                    try:
                        os.fsync(fd)
                    finally:
                        os.close(fd)
                finally:
                    temporary.unlink(missing_ok=True)
            value = dict(binding, id=artifact_id, revision=revision, tasks=[t['id'] for t in spec['tasks']], createdAt=int(time.time()), bundleHash=hashlib.sha256(text.encode()).hexdigest())
            write_json(path, value)
            return self.public(value)

    def active(self):
        path = self.root / 'active.json'
        return json.loads(path.read_text()) if path.exists() else None

    def dag_path(self, artifact_id):
        return '/dags/sre_replay_' + artifact_id

    def run_path(self, run):
        return self.dag_path(run['artifactId']) + '/dagRuns/' + quote(run['runId'], safe='')

    def start(self, artifact_id):
        with self.locked():
            value = self.artifact(artifact_id)
            require(not self.active(), 'A run is active or unresolved; refresh its status before another replay')
            path = self.dag_path(artifact_id)
            details = self.client.request('GET', path)
            require('artifact:' + artifact_id in [t['name'] for t in details.get('tags', [])], 'Airflow has not loaded the exact immutable artifact')
            require(details.get('max_active_runs') == 1 and details.get('timetable_summary') in (None, 'None', 'Never, external triggers only'), 'Unexpected loaded DAG scheduling policy')
            loaded = self.client.request('GET', '/dagSources/sre_replay_' + artifact_id)
            require(hashlib.sha256(loaded['content'].encode()).hexdigest() == value['bundleHash'], 'Airflow loaded source differs from immutable bundle')
            tasks = self.client.request('GET', path + '/tasks')['tasks']
            require([t['task_id'] for t in tasks] == ['replay_chain'] and all(t.get('retries') == 0 for t in tasks), 'Loaded task contract differs')
            runs = self.client.request('GET', path + '/dagRuns?limit=1&state=queued&state=running')['dag_runs']
            require(all(r.get('state') in TERMINAL for r in runs), 'Airflow has an existing nonterminal run')
            run = {'artifactId': artifact_id, 'revision': value['revision'], 'runId': 'replay__' + uuid.uuid4().hex, 'state': 'submitting'}
            # Persist before any side effect. A lost POST response never permits a duplicate.
            write_json(self.root / 'active.json', run)
            # Airflow 3.4 drains this manual-only DAG and automatically re-pauses it,
            # even if the app disconnects before terminal status is observed.
            self.client.request('POST', path + '/dagRuns', {'dag_run_id': run['runId'], 'logical_date': None, 'conf': {}, 'drain_dag': True})
            run['state'] = 'queued'
            write_json(self.root / 'active.json', run)
            return run

    def status(self, artifact_id):
        with self.locked():
            artifact = self.artifact(artifact_id)
            run = self.active()
            if not run or run['artifactId'] != artifact_id:
                previous = self.root / ('last_' + artifact_id + '.json')
                return json.loads(previous.read_text()) if previous.exists() else {'artifactId': artifact_id, 'state': 'idle', 'steps': [], 'tasks': []}
            path = self.run_path(run)
            actual = self.client.request('GET', path)
            state = actual['state']
            require(state in ('queued', 'running', 'success', 'failed'), 'Unexpected Airflow run state')
            instances = self.client.request('GET', path + '/taskInstances')['task_instances']
            task_states = {'removed', 'scheduled', 'queued', 'running', 'success', 'restarting', 'failed', 'up_for_retry', 'up_for_reschedule', 'upstream_failed', 'skipped', 'deferred', None}
            run['tasks'] = [{'task_id': 'replay_chain', 'state': t.get('state') if t.get('state') in task_states else 'unknown', 'try_number': t.get('try_number') if type(t.get('try_number')) is int else None} for t in instances if t.get('task_id') == 'replay_chain']
            run['state'] = 'stopping' if run.get('stopRequested') and state not in TERMINAL else state
            run['steps'] = []
            if state in TERMINAL:
                # XCom may be unavailable on a crash. Terminal state remains truthful.
                try:
                    xcom = self.client.request('GET', path + '/taskInstances/replay_chain/xcomEntries/replay_result')['value']
                    if isinstance(xcom, str):
                        xcom = json.loads(xcom)
                    run['steps'] = self.safe_steps(xcom.get('steps', []), artifact['spec'])
                except (AirflowError, ValueError, KeyError, TypeError):
                    pass
                self.client.request('PATCH', self.dag_path(artifact_id), {'is_paused': True})
                write_json(self.root / ('last_' + artifact_id + '.json'), run)
                (self.root / 'active.json').unlink()
            else:
                write_json(self.root / 'active.json', run)
            return run

    @staticmethod
    def safe_steps(rows, spec):
        result = []
        limits = {t['id']: len(t['steps']) for t in spec['tasks']}
        for row in rows[:101]:
            if not isinstance(row, dict):
                continue
            task, step = row.get('task'), row.get('step')
            if isinstance(task, str) and type(step) is int and ((task in limits and 1 <= step <= limits[task]) or (task == 'startup' and step == 0)) and row.get('state') in ('passed', 'failed'):
                item = {'task': row['task'], 'step': row['step'], 'state': row['state']}
                if row.get('reason') in {'explicit wait or visible assertion timed out', 'control identity changed', 'ambiguous locator', 'private/form boundary', 'click effect already satisfied; no click sent', 'browser operation failed', 'Selenium dependency unavailable in replay environment', 'replay process exited before first browser step', 'cancelled', 'sandbox verification unavailable', 'browser sandbox disabled', 'missing or invalid synthetic runtime input', 'URL assertion failed', 'task budget exceeded', 'run budget exceeded'}:
                    item['reason'] = row['reason']
                result.append(item)
        return result

    def logs(self, artifact_id):
        # Never forward raw worker/provider logs, which may contain environment data.
        value = self.status(artifact_id)
        return {'state': value['state'], 'logs': [f"{s['task']}/step-{s['step']}: {s['state']}" + (" · " + s['reason'] if s.get('reason') else "") for s in value.get('steps', [])], 'notice': 'Sanitized structured replay events only; refresh after completion for XCom results.'}

    def stop(self, artifact_id):
        with self.locked():
            run = self.active()
            require(run and run['artifactId'] == artifact_id, 'No active run for this artifact')
            if run.get('stopSignalsWritten'):
                return run
            run['stopRequested'], run['state'] = True, 'stopping'
            write_json(self.root / 'active.json', run)
            # Supported Airflow Variables API + SDK polling, not task-state patching.
            # Unique bucket names bound missing-value cache latency to one minute.
            bucket = int(time.time()) // 60
            prefix = 'sre_stop_' + artifact_id + '_' + run['runId'] + '_'
            self.client.cancel_marker(prefix + 'requested')
            for i in range(7):
                self.client.cancel_marker(prefix + str(bucket + i))
            run['stopSignalsWritten'] = True
            write_json(self.root / 'active.json', run)
            return run


def from_env(credential_provider=None):
    if os.environ.get('SRE_AIRFLOW_REPLAY_ENABLED') != '1':
        return None
    provider = credential_provider or (lambda: (os.environ['AIRFLOW_USERNAME'], os.environ['AIRFLOW_PASSWORD']))
    return ReplayRegistry(os.environ['SRE_AIRFLOW_REGISTRY_DIR'], os.environ['SRE_AIRFLOW_DAG_DIR'], AirflowClient(os.environ['AIRFLOW_BASE_URL'], provider), {'grid': os.environ['SELENIUM_GRID_URL'], 'browser': os.environ.get('SRE_AIRFLOW_BROWSER', 'edge'), 'isolation': os.environ.get('SELENIUM_ISOLATION_MODE', os.environ.get('GRID_ISOLATION_MODE', os.environ.get('SELENIUM_GRID_ISOLATION', 'browser')))})
