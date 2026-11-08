"""Standalone Selenium replay template. Only stdlib and Selenium; no repair/model hooks."""
import argparse
import json
import os
import re
import signal
import sys
import threading
import time
from urllib.parse import unquote, urlsplit

SPEC = None  # Replaced with embedded JSON by the exporter, never executable task source.
ID = re.compile(r'[a-z][a-z0-9_-]{0,63}')
ENV = re.compile(r'SRE_REPLAY_INPUT_[A-Z][A-Z0-9_]{0,47}')
SENSITIVE = re.compile(r'password|passwd|secret|token|authorization|api.?key|cookie|session|login|account|payment|checkout|private', re.I)
REGION = '[data-sre-observe]'
# Fixed guard only; no script, selector or action source is accepted from the spec.
BOUNDARY = """
const r=arguments[0],e=arguments[1],input=arguments[2];
const p='form,[contenteditable],[data-private]';
if(r.closest(p+',input,textarea,select')||!r.contains(e)||e.closest(p)||e.form)return false;
if(input)return e.tagName==='INPUT'&&e.type==='text'&&e.getAttribute('data-sre-input')==='synthetic'&&e.autocomplete==='off'&&!/password|secret|token|login|account|payment|email|phone|address|name|birth/i.test([e.id,e.name,e.getAttribute('aria-label'),e.placeholder].join(' '));
return !e.closest('input,textarea,select')&&!e.querySelector('input,textarea,select,form,[contenteditable],[data-private]');
"""


class ReplayFailure(ValueError):
    pass


def require(ok, reason):
    if not ok:
        raise ReplayFailure(reason)


def approved_url(value):
    require(isinstance(value, str) and 1 <= len(value) <= 2000 and '\\' not in value
            and not any(ord(c) <= 32 or ord(c) == 127 for c in value), 'invalid URL')
    u = urlsplit(value)
    require(u.scheme in ('http', 'https') and u.hostname and not u.username and not u.password
            and not u.query and not u.fragment and '?' not in value and '#' not in value
            and not SENSITIVE.search(unquote(u.path)) and '%' not in u.path, 'sensitive or unsupported URL')
    _ = u.port
    return value


def identity(value):
    require(isinstance(value, str) and ID.fullmatch(value) and not SENSITIVE.search(value), 'invalid synthetic identifier')
    return value


def validate_step(s, urls):
    require(isinstance(s, dict), 'missing replay action')
    op = s.get('op')
    extra = {'navigate': {'url'}, 'click': {'id', 'tag', 'href'}, 'input': {'id', 'env'},
             'wait_visible': {'id', 'text'}, 'assert_text': {'id', 'text'}}
    require(op in extra, 'unsupported replay operation')
    require(set(s) == {'op', 'pre_url', 'post_url', 'wait'} | extra[op], 'missing or unknown action/locator/URL/wait data')
    for key in ('pre_url', 'post_url'):
        require(s[key] in urls, 'action URL not approved')
    require(s['wait'] == {'kind': 'ready_region', 'timeout': 10}, 'explicit ready-region wait required')
    if op == 'navigate':
        require(s['url'] in urls and s['post_url'] == s['url'], 'navigation URL not approved')
    else:
        identity(s['id'])
    if op == 'click':
        require(s['tag'] in ('a', 'button'), 'unsupported control tag')
        require((s['tag'] == 'button' and s['href'] is None) or
                (s['tag'] == 'a' and s['href'] in urls), 'missing or unapproved control href')
    if op == 'input':
        require(isinstance(s['env'], str) and ENV.fullmatch(s['env']) and not SENSITIVE.search(s['env']), 'named synthetic input env ref required')
        require(s['pre_url'] == s['post_url'], 'input cannot navigate')
    if op in ('wait_visible', 'assert_text'):
        require(isinstance(s['text'], str) and 1 <= len(s['text']) <= 500 and
                not SENSITIVE.search(s['text']) and not any(ord(c) < 32 for c in s['text']), 'approved synthetic visible text required')
        require(s['pre_url'] == s['post_url'], 'assertion cannot navigate')
    return s


def validate_spec(spec):
    require(isinstance(spec, dict) and set(spec) == {'version', 'revision', 'urls', 'tasks', 'run_timeout'}, 'invalid replay spec')
    require(spec['version'] == 'sre-selenium/v1' and isinstance(spec['revision'], str)
            and re.fullmatch('[0-9a-f]{64}', spec['revision']), 'invalid source revision')
    urls = spec['urls']
    require(isinstance(urls, list) and 1 <= len(urls) <= 10 and len(set(urls)) == len(urls), 'explicit bounded URL list required')
    for url in urls:
        approved_url(url)
    require(type(spec['run_timeout']) is int and 10 <= spec['run_timeout'] <= 300, 'invalid run budget')
    tasks = spec['tasks']
    require(isinstance(tasks, list) and 1 <= len(tasks) <= 100, 'task budget exceeded')
    previous, count, last_url, seen = None, 0, None, set()
    for task in tasks:
        require(isinstance(task, dict) and set(task) == {'id', 'depends_on', 'timeout', 'steps'}, 'invalid replay task')
        identity(task['id'])
        require(task['id'] not in seen, 'duplicate task ID')
        seen.add(task['id'])
        require(task['depends_on'] == ([] if previous is None else [previous]), 'serial dependencies required')
        require(type(task['timeout']) in (int, float) and 1 <= task['timeout'] <= 300, 'invalid task budget')
        require(isinstance(task['steps'], list) and task['steps'], 'task has no actions')
        for index, s in enumerate(task['steps']):
            validate_step(s, urls)
            if s['op'] == 'click' and s['pre_url'] == s['post_url']:
                following = task['steps'][index + 1] if index + 1 < len(task['steps']) else {}
                require(s['tag'] == 'button' and following.get('op') in ('wait_visible', 'assert_text') and following.get('pre_url') == s['post_url'], 'same-page click requires an explicit following visible result assertion')
            require(last_url is None or s['pre_url'] == last_url, 'discontinuous URL assertions')
            require(count > 0 or s['op'] == 'navigate', 'first action must navigate')
            last_url = s['post_url']
            count += 1
        previous = task['id']
    require(count <= 100 and tasks[-1]['steps'][-1]['op'] == 'assert_text', 'bounded actions and final visible assertion required')
    return spec


def run(spec, grid, browser='edge', driver_factory=None, isolation=None):
    """driver_factory injection is for UNIT tests only; CLI always creates a real Grid session."""
    validate_spec(spec)
    require(isinstance(grid, str) and '\\' not in grid and not any(ord(c) <= 32 or ord(c) == 127 for c in grid), 'explicit Grid origin required')
    u = urlsplit(grid)
    require(u.scheme in ('http', 'https') and u.hostname and not u.username and not u.password
            and u.path in ('', '/') and not u.query and not u.fragment, 'explicit Grid origin required')
    _ = u.port
    require(browser in ('edge', 'chrome'), 'Edge or Chrome required')
    isolation = isolation or os.environ.get('SELENIUM_ISOLATION_MODE', os.environ.get('GRID_ISOLATION_MODE', os.environ.get('SELENIUM_GRID_ISOLATION', 'browser')))
    require(isolation in ('browser', 'container'), 'explicit browser or container isolation required')
    from selenium import webdriver
    from selenium.webdriver.remote.client_config import ClientConfig
    from selenium.common.exceptions import StaleElementReferenceException, NoSuchElementException
    driver, task_id, step_number = None, 'startup', 0
    deadline = time.monotonic() + spec['run_timeout']
    task_deadline = deadline
    cancelled = threading.Event()
    old_handlers = {}
    def cancel(signum, frame):
        cancelled.set()
        raise ReplayFailure('cancelled')
    def guard():
        require(not cancelled.is_set(), 'cancelled')
        require(time.monotonic() < deadline, 'run budget exceeded')
        require(time.monotonic() < task_deadline, 'task budget exceeded')
        require(len(driver.window_handles) == 1, 'window context unsupported')
        require(driver.execute_script('return window.top === window.self') is True, 'frame context unsupported')
    def url(expected):
        guard()
        require(approved_url(driver.current_url) in spec['urls'] and driver.current_url == expected, 'URL assertion failed')
    def unique(selector):
        found = driver.find_elements('css selector', selector)
        require(len(found) <= 1, 'ambiguous locator')
        return found[0] if found else None
    def target(s):
        root = unique(REGION)
        if root is None or not root.is_displayed():
            return None
        attr = 'data-sre-result' if s['op'] in ('assert_text', 'wait_visible') else 'data-sre-action'
        e = unique('[' + attr + '="' + s['id'] + '"]')
        if e is None or not e.is_displayed():
            return None
        require(driver.execute_script(BOUNDARY, root, e, s['op'] == 'input') is True, 'private/form boundary')
        if s['op'] in ('click', 'input'):
            require(e.get_attribute('data-sre-safe') == 'true' and e.get_attribute('aria-disabled') != 'true', 'control not annotated safe')
            if not e.is_enabled():
                return None
        if s['op'] == 'click':
            require(e.tag_name == s['tag'] and (e.get_attribute('href') if s['tag'] == 'a' else None) == s['href'], 'control identity changed')
            require(s['tag'] != 'button' or e.get_attribute('type') == 'button', 'submit controls forbidden')
        if s['op'] in ('assert_text', 'wait_visible'):
            # Only read the explicitly approved synthetic result, never region/DOM text.
            if e.text != s['text']:
                return None
        return e
    def wait_for(check, expected, transitioning_from=None):
        end = min(deadline, task_deadline, time.monotonic() + 10)
        while time.monotonic() < end:
            guard()
            current = approved_url(driver.current_url)
            require(current in spec['urls'] and current in (expected, transitioning_from), 'URL assertion failed')
            if current != expected:
                time.sleep(.1)
                continue
            try:
                result = check()
                if result:
                    return result
            except (StaleElementReferenceException, NoSuchElementException):
                pass
            time.sleep(.1)
        raise ReplayFailure('explicit wait or visible assertion timed out')
    def ready(expected, before):
        # The region may contain inputs, so validate its ancestry rather than its descendants.
        def region_ready():
            root = unique(REGION)
            return driver.execute_script('return document.readyState') == 'complete' and root is not None and root.is_displayed() and driver.execute_script("return !arguments[0].closest('form,input,textarea,select,[contenteditable],[data-private]')", root) is True
        wait_for(region_ready, expected, before)
    # Hard process ceiling also covers a Grid ignoring transport timeouts. A grace window
    # allows finally/quit; no personal profile/session reuse is requested.
    hard_stop = threading.Timer(spec['run_timeout'] + 20, lambda: (print('FAIL budget: hard transport deadline', file=sys.stderr, flush=True), os._exit(2)))
    hard_stop.daemon = True
    try:
        hard_stop.start()
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                old_handlers[sig] = signal.signal(sig, cancel)
        options = webdriver.EdgeOptions() if browser == 'edge' else webdriver.ChromeOptions()
        options.add_argument('--headless=new')
        if isolation == 'container':
            if browser == 'edge':
                options.binary_location = '/usr/bin/microsoft-edge'
            options.add_argument('--no-sandbox')
        driver = (driver_factory(grid, options) if driver_factory else webdriver.Remote(
            command_executor=grid, options=options, client_config=ClientConfig(remote_server_addr=grid, timeout=10)))
        require(driver.capabilities.get('browserName', '').lower() == ('microsoftedge' if browser == 'edge' else 'chrome'), 'Grid returned an unexpected browser')
        try:
            args = driver.execute_cdp_cmd('Browser.getBrowserCommandLine', {}).get('arguments')
        except Exception:
            raise ReplayFailure('sandbox verification unavailable') from None
        require(isinstance(args, list) and args and all(isinstance(a, str) for a in args), 'sandbox verification unavailable')
        disabled = any(a.split('=')[0] in ('--no-sandbox', '--disable-sandbox', '--disable-setuid-sandbox', '--disable-namespace-sandbox', '--disable-seccomp-filter-sandbox', '--disable-gpu-sandbox', '--single-process', '--in-process-gpu') for a in args)
        require(isolation == 'container' or not disabled, 'browser sandbox disabled')
        driver.implicitly_wait(0)
        driver.set_page_load_timeout(10)
        driver.set_script_timeout(10)
        require(driver.current_url in ('about:blank', 'data:,'), 'fresh browser required')
        for task in spec['tasks']:
            task_id = task['id']
            task_deadline = min(deadline, time.monotonic() + task['timeout'])
            for step_number, s in enumerate(task['steps'], 1):
                guard()
                if task == spec['tasks'][0] and step_number == 1:
                    require(s['op'] == 'navigate', 'initial navigation required')
                else:
                    url(s['pre_url'])
                if s['op'] == 'navigate':
                    driver.get(s['url'])
                elif s['op'] in ('click', 'input'):
                    e = wait_for(lambda: target(s), s['pre_url'])
                    url(s['pre_url'])
                    if s['op'] == 'click':
                        if s['pre_url'] == s['post_url']:
                            effect = task['steps'][step_number]
                            require(target(effect) is None, 'click effect already satisfied; no click sent')
                        e.click()
                    else:
                        value = os.environ.get(s['env'])
                        require(isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9 _.-]{1,80}', value)
                                and not SENSITIVE.search(value), 'missing or invalid synthetic runtime input')
                        e.clear()
                        url(s['pre_url'])
                        e = wait_for(lambda: target(s), s['pre_url'])
                        e.send_keys(value)
                else:
                    wait_for(lambda: target(s), s['pre_url'])
                ready(s['post_url'], s['pre_url'])
                url(s['post_url'])
                if s['op'] == 'click' and s['pre_url'] == s['post_url']:
                    wait_for(lambda: target(task['steps'][step_number]), s['post_url'])
                print('REPLAY_RESULT ' + json.dumps({'task': task_id, 'step': step_number, 'state': 'passed'}), flush=True)
    except BaseException as error:
        reason = str(error) if type(error) is ReplayFailure else 'browser operation failed'
        print('REPLAY_RESULT ' + json.dumps({'task': task_id, 'step': step_number, 'state': 'failed', 'reason': reason}), flush=True)
        # IDs are validated synthetic identifiers; raw WebDriver/DOM/transport errors are never printed.
        raise ReplayFailure(f'{task_id}/step-{step_number}: {reason}') from None
    finally:
        try:
            if driver is not None:
                driver.quit()
        except Exception:
            raise ReplayFailure(f'{task_id}/step-{step_number}: browser cleanup failed') from None
        finally:
            hard_stop.cancel()
            for sig, old in old_handlers.items():
                signal.signal(sig, old)
    print('PASS standalone Selenium replay (visible result verified; session quit)', flush=True)


def main():
    parser = argparse.ArgumentParser(description='Deterministic synthetic Selenium replay; no self-healing.')
    parser.add_argument('--grid', default=os.environ.get('SELENIUM_GRID_URL'), help='Required configured Grid HTTP(S) origin')
    parser.add_argument('--browser', choices=('edge', 'chrome'), default='edge')
    parser.add_argument('--check', action='store_true', help='Validate embedded data without starting Selenium')
    args = parser.parse_args()
    try:
        validate_spec(SPEC)
        if args.check:
            print('VALID standalone specification; browser not executed')
        else:
            require(bool(args.grid), 'configure SELENIUM_GRID_URL or --grid')
            run(SPEC, args.grid, args.browser)
    except Exception as error:
        print('FAIL ' + (str(error) if type(error) is ReplayFailure else 'startup/step-0: dependency or configuration unavailable'), file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main())
