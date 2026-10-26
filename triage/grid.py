"""Edge Selenium Grid client with synthetic and explicit read-only or9.ca checks."""
import argparse
import json
import os
from urllib.parse import urlsplit
from urllib.request import urlopen


def endpoint(value):
    url = urlsplit(value)
    if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password or url.query or url.fragment or url.path not in ('', '/'):
        raise ValueError('Expected explicit Grid HTTP(S) origin without credentials')
    return value.rstrip('/')


def status(url):
    with urlopen(endpoint(url) + '/status', timeout=5) as response:
        content = response.read(100001)
    if len(content) > 100000:
        raise ValueError('Oversized Grid status')
    value = json.loads(content)['value']
    browsers = sorted({s.get('stereotype', {}).get('browserName', '')
                       for n in value.get('nodes', []) for s in n.get('slots', [])} - {''})
    return {'ready': value.get('ready') is True, 'nodes': len(value.get('nodes', [])),
            'browsers': browsers, 'edgeAvailable': 'MicrosoftEdge' in browsers}


def isolation_mode():
    mode = os.environ.get('SELENIUM_GRID_ISOLATION', 'browser')
    if mode not in ('browser', 'container'):
        raise ValueError('SELENIUM_GRID_ISOLATION must be browser or container')
    return mode


def create_driver(url, *, page_load_strategy='normal'):
    from selenium import webdriver
    from selenium.webdriver.remote.client_config import ClientConfig
    options = webdriver.EdgeOptions()
    options.page_load_strategy = page_load_strategy
    # Container isolation is an explicit operator choice, never a failure fallback.
    options.binary_location = ('/usr/bin/microsoft-edge' if isolation_mode() == 'container'
                               else '/opt/microsoft/msedge/msedge')
    options.add_argument('--headless=new')
    if isolation_mode() == 'container':
        # Match the official launcher even if an older node overrides its binary path.
        options.add_argument('--no-sandbox')
    url = endpoint(url)
    return webdriver.Remote(command_executor=url, options=options,
                            client_config=ClientConfig(remote_server_addr=url, timeout=30))


def verify_sandbox(driver):
    args = driver.execute_cdp_cmd('Browser.getBrowserCommandLine', {})['arguments']
    disabled = any(arg.split('=')[0] in ('--no-sandbox', '--disable-setuid-sandbox') for arg in args)
    mode = isolation_mode()
    if mode == 'browser' and disabled:
        raise ValueError('Unsafe Grid browser: sandbox disabled')
    return {'mode': mode, 'browserSandbox': not disabled}


def verify_or9(driver):
    if driver.current_url != 'https://or9.ca/' or not driver.title.strip():
        raise ValueError('Expected titled or9.ca homepage without redirects')
    # Edge retains the requested URL and a title when displaying its internal network-error page.
    if driver.execute_script('return document.documentURI') != 'https://or9.ca/':
        raise ValueError('or9.ca returned a browser error document, not the approved homepage')
    if not driver.find_element('tag name', 'body').is_displayed():
        raise ValueError('or9.ca body is not visible')


def smoke(url, *, or9=False):
    if not status(url)['ready']:
        raise ValueError('Grid is not ready')
    driver = create_driver(url)
    try:
        if driver.capabilities.get('browserName', '').lower() != 'microsoftedge':
            raise ValueError('Expected Microsoft Edge from Grid')
        driver.set_page_load_timeout(15)
        isolation = verify_sandbox(driver)
        driver.get('https://or9.ca/' if or9 else
                   'data:text/html,<title>Synthetic Grid check</title><h1>grid-ok</h1>')
        if or9:
            # Fixed, owner-approved public example; no clicks, input, capture or model calls.
            verify_or9(driver)
        elif driver.title != 'Synthetic Grid check':
            raise ValueError('Synthetic page was not loaded')
        return {'status': 'passed', 'browser': driver.capabilities.get('browserName'),
                'evidence': 'actual read-only https://or9.ca/ session' if or9 else 'actual synthetic data-URL session', 'sandbox_disabled': not isolation['browserSandbox'], 'isolation': isolation}
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('SELENIUM_GRID_URL'))
    checks = parser.add_mutually_exclusive_group()
    checks.add_argument('--smoke', action='store_true', help='Load an in-memory test page in Edge, then quit')
    checks.add_argument('--or9', action='store_true', help='Explicit read-only https://or9.ca/ check; requires approved network egress')
    args = parser.parse_args()
    try:
        if not args.url:
            raise ValueError('Configure SELENIUM_GRID_URL or --url first')
        print(json.dumps(smoke(args.url, or9=args.or9) if args.smoke or args.or9 else status(args.url)))
    except Exception as error:
        parser.exit(2, f'Grid blocked: {type(error).__name__}; no success claimed. Check Grid/container logs and browser/network readiness.\n')


if __name__ == '__main__':
    main()
