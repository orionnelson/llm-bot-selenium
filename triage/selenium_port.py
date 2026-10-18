"""Real Selenium adapter for the local synthetic UI contract ONLY.

No implicit browser/driver downloads, real SSO or production-domain access.
Caller owns an isolated WebDriver and supplies an explicit loopback origin.
"""
import json
from urllib.parse import urlencode, urlsplit
from .core import Action, CATALOG, Context, GuardError, Observation, Policy


class SeleniumPort:
    def __init__(self, driver, base_url, *, wait_seconds=5):
        url = urlsplit(base_url)
        if (url.scheme != "http" or url.hostname not in ("127.0.0.1", "localhost", "::1")
                or url.username or url.password or url.query or url.fragment or url.path not in ("", "/")):
            raise GuardError("demo Selenium is restricted to a loopback HTTP origin")
        self.driver, self.base_url = driver, base_url.rstrip("/")
        self.wait_seconds = wait_seconds
        self.driver.set_page_load_timeout(wait_seconds)

    def _origin_check(self):
        expected, actual = urlsplit(self.base_url), urlsplit(self.driver.current_url)
        if (actual.scheme, actual.hostname, actual.port) != (expected.scheme, expected.hostname, expected.port):
            raise GuardError("unexpected browser origin")

    def _wait(self, selector):
        # Explicit waits instead of sleeps; dependency import is lazy for unit tests.
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        return WebDriverWait(self.driver, self.wait_seconds).until(
            lambda d: d.find_element(By.CSS_SELECTOR, selector))

    def _load(self, path):
        self.driver.get(self.base_url + path)
        self._origin_check()

    def version(self):
        self._load("/")
        return self._wait("[data-ui-version]").get_attribute("data-ui-version")

    def catalog(self):
        self._load("/")
        from selenium.webdriver.common.by import By
        self._wait("[data-query]")
        return [{"page": e.get_attribute("data-page"), "query": e.get_attribute("data-query")}
                for e in self.driver.find_elements(By.CSS_SELECTOR, "[data-query]")]

    def observe(self, action: Action, context: Context):
        Policy(context).action(action)
        self._load("/page/" + action.page + "?" + urlencode({**context.__dict__, "query": action.query}))
        # Mock's explicit read-only form; selectors never come from the model.
        self._wait('button[data-action="run-read-query"]').click()
        self._origin_check()
        data = json.loads(self._wait("[data-observation]").get_attribute("textContent"))
        return Observation(Action(**data["action"]), Context(**data["context"]),
                           data["evidence_id"], data["facts"], data["captured_at"],
                           data["ui_version"], data["session_valid"], data.get("page_text", ""))
