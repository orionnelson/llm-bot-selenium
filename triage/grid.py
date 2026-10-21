"""Explicit Selenium Grid client + synthetic smoke check. No real-site navigation."""
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
    return {'ready': value.get('ready') is True, 'nodes': len(value.get('nodes', []))}


def create_driver(url):
    from selenium import webdriver
    from selenium.webdriver.remote.client_config import ClientConfig
    options = webdriver.ChromeOptions()
    # The official image's shell wrapper adds --no-sandbox. Use the native binary instead.
    options.binary_location = '/opt/google/chrome/chrome'
    options.add_argument('--headless=new')
    url = endpoint(url)
    return webdriver.Remote(command_executor=url, options=options,
                            client_config=ClientConfig(remote_server_addr=url, timeout=30))


def verify_sandbox(driver):
    args = driver.execute_cdp_cmd('Browser.getBrowserCommandLine', {})['arguments']
    if any(arg.split('=')[0] in ('--no-sandbox', '--disable-setuid-sandbox') for arg in args):
        raise ValueError('Unsafe Grid browser: sandbox disabled')


def smoke(url):
    if not status(url)['ready']:
        raise ValueError('Grid is not ready')
    driver = create_driver(url)
    try:
        driver.set_page_load_timeout(10)
        verify_sandbox(driver)
        driver.get('data:text/html,<title>Synthetic Grid check</title><h1>grid-ok</h1>')
        if driver.title != 'Synthetic Grid check':
            raise ValueError('Synthetic page was not loaded')
        return {'status': 'passed', 'browser': driver.capabilities.get('browserName'),
                'evidence': 'actual synthetic data-URL session', 'sandbox_disabled': False}
    finally:
        driver.quit()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default=os.environ.get('SELENIUM_GRID_URL'))
    parser.add_argument('--smoke', action='store_true', help='Create one isolated session, load an in-memory page, then quit')
    args = parser.parse_args()
    try:
        if not args.url:
            raise ValueError('Configure SELENIUM_GRID_URL or --url first')
        print(json.dumps(smoke(args.url) if args.smoke else status(args.url)))
    except Exception as error:
        parser.exit(2, f'Grid blocked: {type(error).__name__}; no success claimed\n')


if __name__ == '__main__':
    main()
