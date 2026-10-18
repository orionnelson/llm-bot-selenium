"""Loopback-only mock pages. Contains no AWS or Dynatrace connections."""
from dataclasses import asdict
from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import time
from urllib.parse import parse_qs, urlsplit
from .core import Action, Context, GuardError, Policy
from .fixtures import FixturePort


def make_server(port=0, *, failure="dependency", ui="mock-v1", expired=False):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            route = urlsplit(self.path)
            fixture = FixturePort(failure, now=int(time.time()), ui=ui, expired=expired)
            try:
                if route.path == "/":
                    links = "".join(f'<a href="/" data-page="{r["page"]}" data-query="{r["query"]}">{escape(r["description"])}</a><br>'
                                    for r in fixture.catalog())
                    body = f'<h1 data-ui-version="{escape(ui)}">Synthetic observability console</h1>{links}'
                elif route.path.startswith("/page/"):
                    q = parse_qs(route.query, strict_parsing=True)
                    if set(q) != {"account", "region", "function", "start", "end", "query"} or any(len(v) != 1 for v in q.values()):
                        raise GuardError("unexpected query fields")
                    context = Context(q["account"][0], q["region"][0], q["function"][0], int(q["start"][0]), int(q["end"][0]))
                    action = Action(route.path.removeprefix("/page/"), q["query"][0])
                    policy = Policy(context)
                    policy.action(action)
                    observation = asdict(fixture.observe(action, context))
                    payload = json.dumps(observation).replace("<", "\\u003c")
                    body = (f'<h1 data-ui-version="{escape(ui)}">{escape(action.page)}</h1>'
                            '<button data-action="run-read-query" onclick="document.getElementById(\'result\').setAttribute(\'data-observation\',\'ready\')">Run read-only query</button>'
                            f'<script type="application/json" id="result">{payload}</script>')
                else:
                    self.send_error(404)
                    return
            except (ValueError, KeyError) as exc:
                self.send_error(400, "Invalid mock query")
                return
            payload = ("<!doctype html><html><head><meta charset='utf-8'><title>Mock console</title></head><body>" + body + "</body></html>").encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(payload)
    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    server = make_server(8765)
    print("Synthetic UI at http://127.0.0.1:8765", flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
