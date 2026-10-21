"""Local DAG-first editor backend. Validates/plans definitions; never runs handlers."""
from __future__ import annotations
import argparse
import hashlib
from http.server import HTTPServer, SimpleHTTPRequestHandler
import json
import os
from pathlib import Path
import tempfile
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


def handler(dag_path, assets):
    """One trusted server-side definition path; clients cannot select filesystem paths."""
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

        def do_PUT(self):
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
    args = parser.parse_args()
    try:
        snapshot(args.dag)  # Never seed missing/invalid definitions from browser state.
    except (OSError, ValueError, TypeError, KeyError, SyntaxError, RecursionError, AttributeError):
        parser.error('Server DAG is missing or invalid; no fallback definition loaded')
    # shortcut: one local process owns this file; add locking before multi-worker hosting.
    with HTTPServer(('127.0.0.1', args.port), handler(args.dag.resolve(), args.assets.resolve())) as server:
        print(f'DAG editor: http://127.0.0.1:{server.server_port} (planning only)', flush=True)
        server.serve_forever()


if __name__ == '__main__':
    main()
