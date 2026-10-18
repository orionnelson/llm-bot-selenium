"""Explicit Edge/Chrome launch; no downloads or personal profiles."""
from importlib import import_module
import os
from pathlib import Path
import shutil

BROWSER_ENV = {'edge': ('MSEDGE_BINARY', 'MSEDGEDRIVER'),
               'chrome': ('CHROME_BINARY', 'CHROMEDRIVER')}


def selected_browser(browser=None):
    browser = browser or os.getenv('SELENIUM_BROWSER')
    browser = browser or ('chrome' if os.getenv('CHROME_BINARY') and not os.getenv('MSEDGE_BINARY') else 'edge')
    if browser not in BROWSER_ENV:
        raise ValueError('browser must be edge or chrome')
    return browser


def is_executable(path):
    return bool(path and Path(path).is_file() and os.access(path, os.X_OK))


def runtime_paths(browser, binary=None, driver=None):
    browser = selected_browser(browser)
    binary_env, driver_env = BROWSER_ENV[browser]
    candidates = ('microsoft-edge', 'microsoft-edge-stable', 'msedge') if browser == 'edge' else ('chromium', 'google-chrome', 'chrome')
    binary = binary or os.getenv(binary_env) or next((p for name in candidates if (p := shutil.which(name))), None)
    driver = driver or os.getenv(driver_env) or shutil.which(driver_env.lower())
    return tuple(str(Path(p).expanduser().resolve()) if p else None for p in (binary, driver))


def create_driver(browser, binary, driver_path, profile_dir):
    """Caller owns the temporary profile lifetime and must quit the driver."""
    browser = selected_browser(browser)
    if not all(is_executable(p) for p in (binary, driver_path)):
        raise ValueError('Explicit executable browser and driver paths required')
    from selenium import webdriver
    service = import_module('selenium.webdriver.' + browser + '.service').Service
    options = getattr(webdriver, browser.title() + 'Options')()
    options.binary_location = str(binary)
    for argument in ('--headless=new', '--disable-dev-shm-usage', '--user-data-dir=' + str(profile_dir)):
        options.add_argument(argument)
    return getattr(webdriver, browser.title())(service=service(executable_path=str(driver_path)), options=options)
