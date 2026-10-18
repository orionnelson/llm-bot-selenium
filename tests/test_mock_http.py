import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from triage.mock_server import make_server


class MockHTTPTests(unittest.TestCase):
    def setUp(self):
        self.server = make_server()
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = "http://127.0.0.1:" + str(self.server.server_port)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_discovery_catalog_and_query_contract(self):
        with urlopen(self.base, timeout=2) as response:
            self.assertIn(b'data-ui-version="mock-v1"', response.read())
        params = dict(account="demo", region="us-east-1", function="checkout", start=1, end=2, query="failure_events")
        with urlopen(self.base + "/page/logs?" + urlencode(params), timeout=2) as response:
            text = response.read().decode()
        self.assertIn("DEPENDENCY_TIMEOUT", text)
        self.assertIn("run-read-query", text)

    def test_forbidden_mock_query_rejected(self):
        params = dict(account="demo", region="us-east-1", function="checkout", start=1, end=2, query="delete")
        with self.assertRaises(HTTPError) as err:
            urlopen(self.base + "/page/logs?" + urlencode(params), timeout=2)
        self.assertEqual(err.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
