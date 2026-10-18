"""Explicit, isolated Edge/Chrome WebDriver setup; never download a driver."""
from dataclasses import dataclass
from importlib import import_module
import os
from pathlib import Path
import shutil


@dataclass(frozen=True)
class BrowserSpec:
    binary_env: str
    driver_env: str
    binary_names: tuple
    driver_name: str
    webdriver_name: str


BROWSERS = {
    'edge': BrowserSpec('MSEDGE_BINARY', 'MSEDGEDRIVER',
                        ('microsoft-edge', 'microsoft-edge-stable', 'msedge'),
                        'msedgedriver', 'Edge'),
    'chrome': BrowserSpec('CHROME_BINARY', 'CHROMEDRIVER',
                          ('chromium', 'google-chrome', 'chrome'),
                          'chromedriver', 'Chrome'),
}


def selected_browser(browser=None):
    if browser is None:
        browser = os.environ.get('SELENIUM_BROWSER')
    if browser is None:
        # Preserve the original explicit Chrome environment contract.
        browser = 'chrome' if os.environ.get('CHROME_BINARY') and not os.environ.get('MSEDGE_BINARY') else 'edge'
    if browser not in BROWSERS:
        raise ValueError('browser must be edge or chrome')
    return browser


def browser_spec(browser):
    return BROWSERS[selected_browser(browser)]


def is_executable(path):
    return bool(path and Path(path).is_file() and os.access(path, os.X_OK))


def runtime_paths(browser, binary=None, driver=None):
    spec = browser_spec(browser)
    binary = binary or os.environ.get(spec.binary_env)
    if not binary:
        binary = next((path for name in spec.binary_names if (path := shutil.which(name))), None)
    driver = driver or os.environ.get(spec.driver_env) or shutil.which(spec.driver_name)
    # The test subprocess changes CWD: never pass an unresolved relative path.
    return tuple(str(Path(path).expanduser().resolve()) if path else None for path in (binary, driver))


def runtime_environment(browser, binary, driver):
    spec = browser_spec(browser)
    return {'SELENIUM_BROWSER': selected_browser(browser), spec.binary_env: binary, spec.driver_env: driver}


def create_driver(browser, binary, driver_path, profile_dir):
    """Caller owns profile lifetime and must quit the returned driver."""
    browser = selected_browser(browser)
    spec = browser_spec(browser)
    if not all(is_executable(path) for path in (binary, driver_path)):
        raise ValueError('Explicit executable browser and driver paths required')
    from selenium import webdriver
    service = import_module('selenium.webdriver.' + browser + '.service').Service
    options = getattr(webdriver, spec.webdriver_name + 'Options')()
    options.binary_location = str(binary)
    for argument in ('--headless=new', '--disable-dev-shm-usage', '--user-data-dir=' + str(profile_dir)):
        options.add_argument(argument)
    return getattr(webdriver, spec.webdriver_name)(
        service=service(executable_path=str(driver_path)), options=options)
