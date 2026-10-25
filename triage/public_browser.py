"""Public-page URL boundary and browser request filtering for the LAN recorder."""
import ipaddress
import json
import re
import socket
from threading import Event, Lock, Thread
from urllib.parse import urlsplit, urlunsplit, unquote


def public_url(value):
    if not isinstance(value, str) or not 1 <= len(value) <= 2048 or any(ord(c) < 33 for c in value) or '\\' in value:
        raise ValueError('Enter a public HTTP(S) URL')
    u = urlsplit(value)
    if u.scheme not in ('http', 'https') or not u.hostname or u.username or u.password or u.port not in (None, 80, 443):
        raise ValueError('Only public HTTP(S) pages on ports 80/443, without credentials')
    if re.search(r'(?:token|password|secret|api[_-]?key|authorization)=', unquote(u.query + '&' + u.fragment), re.I):
        raise ValueError('Do not put credentials in the URL')
    host = u.hostname.lower().rstrip('.')
    try: literal = ipaddress.ip_address(host)
    except ValueError: literal = None
    if literal is not None and (not literal.is_global or literal.is_multicast): raise ValueError('Private/internal addresses are not available in the public recorder')
    if literal is None and (host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.svc', '.cluster.local')) or '.' not in host):
        raise ValueError('Private/internal pages are not available in the public recorder')
    addresses = {row[4][0] for row in socket.getaddrinfo(host, u.port or (443 if u.scheme == 'https' else 80), type=socket.SOCK_STREAM)}
    if not addresses or any(not ipaddress.ip_address(a).is_global or ipaddress.ip_address(a).is_multicast for a in addresses):
        raise ValueError('Private/internal addresses are not available in the public recorder')
    return urlunsplit((u.scheme, u.netloc.lower(), u.path or '/', u.query, u.fragment))


class PublicRequests:
    """Block internal URLs/subresources/redirects at CDP request time, not just on button clicks."""
    def __init__(self, driver):
        import websocket
        self.ws = websocket.create_connection(driver.capabilities['se:cdp'], timeout=1, suppress_origin=True)
        self.lock, self.pending, self.counter, self.closed = Lock(), {}, 0, False
        self.allowed, self.blocked = {}, []
        self.requests, self.failures, self.console = {}, [], []
        self.exceptions, self.responses = [], []
        self.thread = Thread(target=self.receive, daemon=True); self.thread.start()
        # Edge can have extra tabs. Guard the WebDriver-controlled target, never the first arbitrary page.
        page = driver.execute_cdp_cmd('Target.getTargetInfo', {})['targetInfo']
        if page.get('type') != 'page': raise ValueError('Controlled browser page was not found')
        self.session = self.call('Target.attachToTarget', {'targetId': page['targetId'], 'flatten': True})['sessionId']
        self.call('Network.enable', session=self.session)
        self.call('Log.enable', session=self.session)
        self.call('Runtime.enable', session=self.session)
        self.call('Fetch.enable', {'patterns': [{'urlPattern': '*', 'requestStage': 'Request'}]}, session=self.session)
        # Do not permit downloads triggered by a public site.
        self.call('Browser.setDownloadBehavior', {'behavior': 'deny'})

    def send(self, method, params=None, session=None, pending=None):
        with self.lock:
            self.counter += 1; ident = self.counter
            if pending is not None: self.pending[ident] = pending
            value = {'id': ident, 'method': method, 'params': params or {}}
            if session: value['sessionId'] = session
            self.ws.send(json.dumps(value))
            return ident

    def call(self, method, params=None, session=None):
        event, box = Event(), {}
        ident = self.send(method, params, session, (event, box))
        if not event.wait(8):
            with self.lock: self.pending.pop(ident, None)
            raise TimeoutError('Browser request guard did not initialize')
        if 'error' in box: raise ValueError('Browser request guard rejected a command')
        return box.get('result', {})

    def receive(self):
        import websocket
        while not self.closed:
            try: value = json.loads(self.ws.recv())
            except websocket.WebSocketTimeoutException: continue
            except Exception: break
            if 'id' in value:
                with self.lock: pending = self.pending.pop(value['id'], None)
                if pending: pending[1].update(value); pending[0].set()
            elif value.get('method') == 'Network.requestWillBeSent':
                p = value['params']; self.requests[p['requestId']] = p['request']['url']
            elif value.get('method') == 'Network.responseReceived':
                p = value['params']['response']
                if len(self.responses) < 200: self.responses.append({'url': p.get('url'), 'status': p.get('status')})
            elif value.get('method') == 'Network.loadingFailed':
                p = value['params']
                if len(self.failures) < 100: self.failures.append({'host': urlsplit(self.requests.get(p['requestId'], '')).hostname, 'error': p.get('errorText')})
            elif value.get('method') == 'Runtime.consoleAPICalled':
                p = value['params']
                if p.get('type') in ('error', 'warning'):
                    self.console.append(' '.join(str(a.get('value', a.get('description', ''))) for a in p.get('args', []))[:600]); self.console[:] = self.console[-100:]
            elif value.get('method') == 'Runtime.exceptionThrown':
                p = value['params']['exceptionDetails']
                if len(self.exceptions) < 20: self.exceptions.append(p.get('exception', {}).get('description', p.get('text', 'JavaScript error'))[:1000])
            elif value.get('method') == 'Log.entryAdded':
                p = value['params']['entry']
                if p.get('level') == 'error' and len(self.console) < 50: self.console.append(p.get('text', '')[:300])
            elif value.get('method') == 'Fetch.requestPaused':
                p = value['params']; url = p['request']['url']
                try:
                    # Per-host checks also cover redirects and cross-origin resources. Never send credentials.
                    parsed = urlsplit(url)
                    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password: raise ValueError('Unsupported public request')
                    host = parsed.netloc
                    public_url(url); self.allowed[host] = True
                    if len(self.allowed) > 100: raise ValueError('Public resource-host budget exceeded')
                    self.send('Fetch.continueRequest', {'requestId': p['requestId']}, value.get('sessionId'))
                except Exception:
                    self.blocked.append(urlsplit(url).hostname or 'unsupported URL')
                    self.send('Fetch.failRequest', {'requestId': p['requestId'], 'errorReason': 'BlockedByClient'}, value.get('sessionId'))
        # Fail closed: if request filtering loses its connection, pending requests remain paused.

    def close(self):
        self.closed = True
        self.ws.close()
        self.thread.join(timeout=2)
