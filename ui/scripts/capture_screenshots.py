#!/usr/bin/env python3
"""Capture genuine fixture UI screenshots with the project's sandboxed browser adapter."""
import argparse
from pathlib import Path
import sys
import tempfile
from urllib.parse import urlsplit
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:4173/')
    parser.add_argument('--browser', choices=['chrome', 'edge'], default='chrome')
    parser.add_argument('--binary', required=True)
    parser.add_argument('--driver', required=True)
    parser.add_argument('--output', type=Path, default=ROOT / 'docs/images')
    args = parser.parse_args()
    target = urlsplit(args.url)
    if target.scheme not in {'http', 'https'} or target.hostname not in {'localhost', '127.0.0.1', '::1'} or target.username or target.password:
        parser.error('Screenshot helper only opens the loopback demo, never private/production pages')
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from triage.browser_runtime import create_driver
    args.output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sre-ui-capture-') as profile:
        driver = create_driver(args.browser, args.binary, args.driver, profile)
        try:
            driver.set_window_size(1536, 1024)
            driver.get(args.url)
            wait = WebDriverWait(driver, 20)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, '.react-flow__node[data-id="check-lambda"]')))
            wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, '.react-flow__edge-path')) >= 8)
            driver.save_screenshot(str(args.output / 'sre-flow-workspace.png'))
            driver.find_element(By.CSS_SELECTOR, '.react-flow__node[data-id="check-errors"]').click()
            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Use input i > 3"]'))).click()
            driver.find_element(By.XPATH, '//button[normalize-space()="Python"]').click()
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'textarea[aria-label="Node Python source"]')))
            driver.save_screenshot(str(args.output / 'sre-flow-python-node.png'))
            driver.find_element(By.XPATH, '//button[normalize-space()="Record"]').click()
            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Start UI recording"]'))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, '//button[normalize-space()="Stop recording"]')))
            driver.save_screenshot(str(args.output / 'sre-flow-recording.png'))
            print('3 actual UI screenshots captured from the loopback demo')
        finally:
            driver.quit()

if __name__ == '__main__':
    main()
