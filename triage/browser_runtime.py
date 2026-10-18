"""Explicit, isolated Edge/Chrome WebDriver setup; never download a driver."""
import os
from pathlib import Path
import shutil


def selected_browser(browser=None):
    if browser is None:
        browser = os.environ.get('SELENIUM_BROWSER')
    if browser is None:
        # Retain the original explicit Chrome environment contract.
        browser = 'chrome' if os.environ.get('CHROME_BINARY') and not os.environ.get('MSEDGE_BINARY') else 'edge'
    if browser not in ('edge', 'chrome'):
        raise ValueError('browser must be edge or chrome')
    return browser


def runtime_paths(browser, binary=None, driver=None):
    browser = selected_browser(browser)
    if browser == 'edge':
        binary = binary or os.environ.get('MSEDGE_BINARY') or shutil.which('microsoft-edge') or shutil.which('microsoft-edge-stable') or shutil.which('msedge')
        driver = driver or os.environ.get('MSEDGEDRIVER') or shutil.which('msedgedriver')
    else:
        binary = binary or os.environ.get('CHROME_BINARY') or shutil.which('chromium') or shutil.which('google-chrome') or shutil.which('chrome')
        driver = driver or os.environ.get('CHROMEDRIVER') or shutil.which('chromedriver')
    return binary, driver


def create_driver(browser, binary, driver_path, profile_dir):
    """Caller owns profile lifetime and must quit the returned driver."""
    browser = selected_browser(browser)
    for path in (binary, driver_path):
        if not path or not Path(path).is_file() or not os.access(path, os.X_OK):
            raise ValueError('Explicit executable browser and driver paths required')
    from selenium import webdriver
    if browser == 'edge':
        from selenium.webdriver.edge.service import Service
        options = webdriver.EdgeOptions()
        constructor = webdriver.Edge
    else:
        from selenium.webdriver.chrome.service import Service
        options = webdriver.ChromeOptions()
        constructor = webdriver.Chrome
    options.binary_location = str(binary)
    options.add_argument('--headless=new')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--user-data-dir=' + str(profile_dir))
    return constructor(service=Service(executable_path=str(driver_path)), options=options)
