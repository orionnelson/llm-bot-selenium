"""HTTP + Selenium-wait contract tests with a fake DOM, NOT browser tests."""
from html.parser import HTMLParser
import importlib.util
import threading
import unittest
from urllib.request import urlopen

from triage.core import Action, Context, GuardError, MockPlanner, investigate
from triage.mock_server import make_server
from triage.selenium_port import SeleniumPort


class Element:
    def __init__(self, attrs, driver):
        self.attrs = dict(attrs)
        self.driver = driver
        self.text = ''

    def is_displayed(self):
        return True  # fake contract only; real rendering belongs to browser acceptance

    def get_attribute(self, name):
        return self.attrs.get(name)

    def click(self):
        if self.attrs.get("data-action") == "run-read-query":
            self.driver.clicked = True


class DOM(HTMLParser):
    def __init__(self, driver):
        super().__init__()
        self.driver = driver
        self.elements = []
        self.script = None
        self.chart = None

    def handle_starttag(self, tag, attrs):
        element = Element(attrs, self.driver)
        self.elements.append(element)
        if 'data-chart-view' in element.attrs:
            self.chart = element
        if tag == "script" and element.attrs.get("id") == "result":
            self.script = element

    def handle_endtag(self, tag):
        if tag == 'div':
            self.chart = None
        if tag == "script":
            self.script = None

    def handle_data(self, data):
        if self.chart:
            self.chart.text += data
        if self.script:
            self.script.attrs["textContent"] = self.script.attrs.get("textContent", "") + data


class FakeHTTPDriver:
    """Only supports the exact mock contract; does not execute JS or render CSS."""
    def __init__(self):
        from uuid import uuid4
        self.session_id = 'fake-' + uuid4().hex

    def set_page_load_timeout(self, seconds):
        self.timeout = seconds

    def get(self, url):
        self.current_url, self.clicked = url, False
        with urlopen(url, timeout=self.timeout) as response:
            text = response.read().decode()
        self.dom = DOM(self)
        self.dom.feed(text)

    def find_elements(self, by, selector):
        if selector == '[data-chart-view]':
            return [e for e in self.dom.elements if 'data-chart-view' in e.attrs]
        if selector == '[data-ui-version]':
            return [e for e in self.dom.elements if "data-ui-version" in e.attrs]
        if selector == '[data-query]':
            return [e for e in self.dom.elements if "data-query" in e.attrs]
        if selector == 'button[data-action="run-read-query"]':
            return [e for e in self.dom.elements if e.attrs.get("data-action") == "run-read-query"]
        if selector == '[data-observation]' and self.clicked:
            return [e for e in self.dom.elements if e.attrs.get("id") == "result"]
        return []

    def find_element(self, by, selector):
        from selenium.common.exceptions import NoSuchElementException
        elements = self.find_elements(by, selector)
        if not elements:
            raise NoSuchElementException(selector)
        return elements[0]


@unittest.skipUnless(importlib.util.find_spec("selenium"), "Selenium package not installed; contract NOT RUN")
class SeleniumContractTests(unittest.TestCase):
    def setUp(self):
        self.servers = []

    def tearDown(self):
        for server, thread in self.servers:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def port(self, **kwargs):
        server = make_server(**kwargs)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.servers.append((server, thread))
        return SeleniumPort(FakeHTTPDriver(), "http://127.0.0.1:" + str(server.server_port))

    def test_selenium_adapter_contract_with_real_http_and_fake_dom(self):
        result = investigate(self.port(), MockPlanner(), Context("demo", "us-east-1", "checkout", 1, 2),
                             "http-contract", "Investigate")
        self.assertEqual(result.result.failure, "likely-dependency-timeout")
        self.assertEqual(len({o.evidence_id for o in result.observations}), len(result.observations))

    def test_expired_session_is_rejected_from_mock_ui_evidence(self):
        with self.assertRaisesRegex(GuardError, "SSO session expired"):
            investigate(self.port(expired=True), MockPlanner(), Context("demo", "us-east-1", "checkout", 1, 2),
                        "http-expired", "Investigate")

    def test_forbidden_action_rejected_by_adapter_before_navigation(self):
        port = self.port()
        with self.assertRaises(GuardError):
            port.observe(Action("alarms", "delete"), Context("demo", "us-east-1", "checkout", 1, 2))
        self.assertFalse(hasattr(port.driver, "current_url"))
