"""External synthetic demo fixture. Run separately on infrastructure reachable from Grid.

Only GET pages; no administration/actions/credentials. Edit --variant-file between runs:
its entire content must be show-result (baseline) or show-result-v2 (changed fixture).
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def handler(variant_file):
    class Fixture(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            if self.path == '/':
                page = '<a data-sre-safe="true" data-sre-action="open-details" href="/details.html">Open synthetic details</a>'
            elif self.path == '/details.html':
                identity = variant_file.read_text().strip()
                if identity not in ('show-result', 'show-result-v2'):
                    self.send_error(503)
                    return
                page = '<button type="button" data-sre-safe="true" data-sre-action="' + identity + '" onclick="document.getElementById(\'result\').hidden=false">Show synthetic result</button><p id="result" data-sre-result="status" hidden>Synthetic replay complete</p>'
            else:
                self.send_error(404)
                return
            body = ('<!doctype html><meta charset="utf-8"><title>Synthetic replay fixture</title><main data-sre-observe>' + page + '</main>').encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
    return Fixture


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--bind', default='127.0.0.1')
    p.add_argument('--port', type=int, default=8080)
    p.add_argument('--variant-file', type=Path, required=True)
    args = p.parse_args()
    with ThreadingHTTPServer((args.bind, args.port), handler(args.variant_file)) as server:
        server.serve_forever()
