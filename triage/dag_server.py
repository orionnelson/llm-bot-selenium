"""Local DAG-first editor backend. Validates/plans definitions; never runs handlers."""
from __future__ import annotations
import argparse
import hashlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import tempfile
from threading import Lock
from urllib.parse import unquote, urlsplit

from .dag import DAG, load_python

LIMIT = 1_000_000


def snapshot(path):
    source = path.read_bytes()
    if len(source) > LIMIT:
        raise ValueError('DAG exceeds 1 MB')
    dag = load_python(source.decode('utf-8'))
    return {'definition': dag.to_spec(), 'plan': dag.plan(), 'python': dag.to_python(),
            'revision': hashlib.sha256(source).hexdigest()}


def handler(dag_path, assets, *, test_mode=False, recordings=None):
    """One trusted server-side definition path; clients cannot select filesystem paths."""
    dag_lock, generation_lock = Lock(), Lock()
    from .browser_loop import BrowserRuns
    browser_runs = BrowserRuns(recordings or dag_path.parent / 'browser-recordings', generation_lock, lambda: snapshot(dag_path)['revision']) if test_mode else None
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(assets), **kwargs)

        def setup(self):
            super().setup()
            self.connection.settimeout(5)

        def log_message(self, *args):
            pass  # Task parameters/source are not request logs.

        def end_headers(self):
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'self'; frame-ancestors 'none'")
            super().end_headers()

        def reply(self, status, value):
            body = json.dumps(value, allow_nan=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def local_request(self):
            # Fixed loopback binding + Host validation also blocks DNS rebinding.
            allowed = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
            host = self.headers.get('Host')
            return host in allowed and self.headers.get('Origin') in (None, f'http://{host}')

        def do_GET(self):
            if not self.local_request():
                return self.reply(403, {'error': 'Local same-origin requests only'})
            if urlsplit(self.path).path.startswith('/api/browser/runs'):
                if not browser_runs:
                    return self.reply(503, {'error': 'Test browser execution disabled'})
                parts = urlsplit(self.path).path.strip('/').split('/')
                try:
                    if parts == ['api', 'browser', 'runs']:
                        return self.reply(200, browser_runs.listing())
                    if len(parts) not in (4,5): raise ValueError('Invalid recording route')
                    value = browser_runs.read(parts[3])  # Validates the opaque run ID.
                    if len(parts) == 4: return self.reply(200, value)
                    name = parts[4]
                    if name not in {u.rsplit('/',1)[-1] for u in value['frames']} | ({'actions.webm'} if value.get('video') else set()):
                        raise ValueError('Unknown recording asset')
                    path = (browser_runs.root / parts[3] / name).resolve()
                    if not path.is_relative_to(browser_runs.root.resolve()) or not path.is_file() or path.stat().st_size > 10485760:
                        raise ValueError('Invalid recording asset')
                    body = path.read_bytes()
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/png' if name.endswith('.png') else 'video/webm')
                    self.send_header('Content-Length', str(len(body)))
                    self.end_headers(); self.wfile.write(body)
                    return
                except (ValueError, OSError, KeyError):
                    return self.reply(404, {'error': 'Recording not found'})
            if urlsplit(self.path).path == '/api/test/status':
                if not test_mode:
                    return self.reply(503, {'error': 'Test integrations disabled'})
                from .test_codegen import MODEL
                from .grid import status
                grid = {'ready': False, 'status': 'not configured'}
                if os.environ.get('SELENIUM_GRID_URL'):
                    try:
                        grid = {**status(os.environ['SELENIUM_GRID_URL']), 'status': 'reachable'}
                    except Exception:
                        grid = {'ready': False, 'status': 'unreachable or invalid'}
                return self.reply(200, {'mode': 'test', 'generator': MODEL, 'grid': grid, 'execution': 'consented-test-browser-actions', 'generatedPythonExecution': False, 'modelBusy': generation_lock.locked()})
            if urlsplit(self.path).path == '/api/dag':
                try:
                    return self.reply(200, snapshot(dag_path))
                except (OSError, ValueError, TypeError, KeyError, SyntaxError, RecursionError, AttributeError):
                    return self.reply(422, {'error': 'Server DAG is missing or invalid; no fallback definition loaded'})
            requested = unquote(urlsplit(self.path).path)
            path = (assets / ('index.html' if requested == '/' else requested.lstrip('/'))).resolve()
            if not path.is_relative_to(assets) or not path.is_file():
                return self.reply(404, {'error': 'Not found'})
            super().do_GET()

        def do_HEAD(self):
            # Avoid a second static-file path bypassing the GET boundary.
            self.send_error(405)

        def do_POST(self):
            self.close_connection = True
            if not self.local_request():
                return self.reply(403, {'error': 'Local same-origin requests only'})
            if self.path.startswith('/api/browser/runs'):
                if not browser_runs:
                    return self.reply(503, {'error': 'Test browser execution disabled'})
                parts = self.path.strip('/').split('/')
                try:
                    if len(parts) == 5 and parts[:3] == ['api','browser','runs'] and parts[4] == 'cancel':
                        return self.reply(202, browser_runs.cancel(parts[3]))
                    if parts != ['api','browser','runs']: return self.reply(404, {'error': 'Not found'})
                    if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                        return self.reply(415, {'error': 'Send bounded application/json'})
                    size = int(self.headers.get('Content-Length','0'))
                    if not 0 < size <= 4096: return self.reply(413, {'error': 'Browser request exceeds bounds'})
                    payload = json.loads(self.rfile.read(size))
                    if not isinstance(payload,dict) or set(payload) != {'nodeId','consent','video'} or not isinstance(payload['nodeId'],str):
                        raise ValueError('Expected task ID, consent and video choice')
                    current = snapshot(dag_path)
                    if self.headers.get('If-Match') != current['revision']:
                        return self.reply(409, {'error': 'DAG changed; reload the saved task before approval'})
                    value = browser_runs.start(DAG.from_spec(current['definition']), current['revision'], payload['nodeId'], payload['consent'], payload['video'])
                    return self.reply(202, value)
                except BlockingIOError:
                    return self.reply(429, {'error': 'Model or browser operation already active'})
                except (ValueError, TypeError, KeyError, SyntaxError, RecursionError):
                    return self.reply(400, {'error': 'Invalid saved browser policy or missing explicit consent'})
                except OSError:
                    return self.reply(503, {'error': 'Grid, recording storage or requested video is unavailable; no browser started'})
            if self.path != '/api/python/generate':
                return self.reply(404, {'error': 'Not found'})
            if not test_mode:
                return self.reply(503, {'error': 'Test generation disabled; start with --test-mode'})
            if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                return self.reply(415, {'error': 'Send bounded application/json'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= 65536:
                    return self.reply(413, {'error': 'Generation request exceeds bounds'})
                value = json.loads(self.rfile.read(size))
                node_id, instructions = value['nodeId'], value['instructions']
                if not isinstance(node_id, str) or not isinstance(instructions, str) or not 1 <= len(instructions) <= 12000:
                    raise ValueError('Invalid generation request')
                current = snapshot(dag_path)
                dag = DAG.from_spec(current['definition'])
                if not any(t.task_id == node_id for t in dag.tasks):
                    return self.reply(409, {'error': 'Save the DAG before generating for this task'})
            except (ValueError, TypeError, KeyError, SyntaxError, OSError, RecursionError, AttributeError):
                return self.reply(400, {'error': 'Invalid saved DAG or generation request'})
            from .test_codegen import generate
            if not generation_lock.acquire(blocking=False):
                return self.reply(429, {'error': 'Test generation already in progress'})
            try:
                candidate = generate(dag, node_id, instructions)
                with dag_lock:
                    if snapshot(dag_path)['revision'] != current['revision']:
                        return self.reply(409, {'error': 'DAG changed during generation; candidate discarded. Reload before generating again'})
                    return self.reply(200, candidate)
            except Exception:
                return self.reply(502, {'error': 'Test model unavailable or candidate invalid; no source applied/executed'})
            finally:
                generation_lock.release()

        def do_PUT(self):
            with dag_lock:
                return self.put_definition()

        def put_definition(self):
            self.close_connection = True
            if not self.local_request():
                return self.reply(403, {'error': 'Local same-origin requests only'})
            if self.path != '/api/dag':
                return self.reply(404, {'error': 'Not found'})
            if self.headers.get_content_type() != 'application/json' or self.headers.get('Transfer-Encoding'):
                return self.reply(415, {'error': 'Send bounded application/json'})
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if not 0 < size <= LIMIT:
                    return self.reply(413, {'error': 'DAG request must be 1..1000000 bytes'})
                current = snapshot(dag_path)
                if self.headers.get('If-Match') != current['revision']:
                    return self.reply(409, {'error': 'DAG changed; load the backend definition before saving'})
                dag = DAG.from_spec(json.loads(self.rfile.read(size)))
                source = dag.to_python().encode()
                if len(source) > LIMIT:
                    raise ValueError('Serialized DAG exceeds 1 MB')
                # Validate the persisted representation too; source remains inert.
                load_python(source.decode())
            except (ValueError, TypeError, KeyError, SyntaxError, RecursionError, AttributeError, TimeoutError):
                return self.reply(400, {'error': 'Invalid DAG; previous definition retained'})
            except OSError:
                return self.reply(503, {'error': 'Cannot read server DAG; no change made'})
            temporary = None
            try:
                with tempfile.NamedTemporaryFile(dir=dag_path.parent, delete=False) as output:
                    temporary = Path(output.name)
                    output.write(source)
                    output.flush()
                    os.fsync(output.fileno())
                os.replace(temporary, dag_path)
            except OSError:
                return self.reply(503, {'error': 'Cannot persist DAG; previous definition retained'})
            finally:
                if temporary is not None:
                    temporary.unlink(missing_ok=True)
            return self.reply(200, snapshot(dag_path))
    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dag', type=Path, required=True, help='Existing declarative Python DAG; authoritative, updated atomically')
    parser.add_argument('--assets', type=Path, default=Path('ui/dist'))
    parser.add_argument('--port', type=int, default=3001)
    parser.add_argument('--test-mode', action='store_true', help='Enable review-only local Smol Friend generation and Grid status')
    parser.add_argument('--recordings', type=Path, help='Private bounded browser recording directory')
    args = parser.parse_args()
    try:
        snapshot(args.dag)  # Never seed missing/invalid definitions from browser state.
    except (OSError, ValueError, TypeError, KeyError, SyntaxError, RecursionError, AttributeError):
        parser.error('Server DAG is missing or invalid; no fallback definition loaded')
    # shortcut: one local process owns this file; add locking before multi-worker hosting.
    with ThreadingHTTPServer(('127.0.0.1', args.port), handler(args.dag.resolve(), args.assets.resolve(), test_mode=args.test_mode, recordings=args.recordings)) as server:
        mode = 'consented browser tests; generated Python disabled' if args.test_mode else 'planning only'
        print(f'DAG editor: http://127.0.0.1:{server.server_port} ({mode})', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
