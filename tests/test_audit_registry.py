import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from triage.audit import Audit, verify_audit
from triage.core import GuardError, MockPlanner, explain_trace, investigate
from triage.fixtures import FixturePort
from triage.registry import Registry
from test_core import CTX, NOW, discover, learned


class AuditRegistryTests(unittest.TestCase):
    def test_audit_before_execution_and_verified_evidence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audit.jsonl"
            port = FixturePort()
            trace = investigate(port, MockPlanner(), CTX, "audit-001", "Investigate", now=lambda: NOW, audit=Audit(path))
            rows = verify_audit(path)
            self.assertEqual(len(rows), len(trace.observations) * 2)
            self.assertEqual(rows[0]["event"], "before-read")
            self.assertEqual(rows[1]["event"], "verified-read")
            self.assertNotIn("IGNORE RULES", path.read_text())
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_audit_failure_prevents_query(self):
        class BrokenAudit:
            def record(self, *args):
                raise GuardError("disk unavailable")
        port = FixturePort()
        with self.assertRaises(GuardError):
            investigate(port, MockPlanner(), CTX, "audit-001", "Investigate", now=lambda: NOW, audit=BrokenAudit())
        self.assertEqual(port.calls, [])

    def test_tamper_detection(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audit.jsonl"
            audit = Audit(path)
            audit.record("step", {"value": 1})
            path.write_text(path.read_text().replace('"value": 1', '"value": 2'))
            with self.assertRaises(GuardError):
                verify_audit(path)

    def test_audit_restart_continues_chain(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "audit.jsonl"
            Audit(path).record("one", {})
            Audit(path).record("two", {})
            self.assertEqual(len(verify_audit(path)), 2)

    def test_registry_versions_and_integrity(self):
        skill, _ = learned()
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "skills.sqlite"
            registry = Registry(path)
            self.assertEqual(registry.publish("dependency", skill), 1)
            self.assertEqual(registry.publish("dependency", skill), 2)
            self.assertEqual(registry.load("dependency").fingerprint(), skill.fingerprint())
            self.assertEqual(registry.load("dependency", 1).fingerprint(), skill.fingerprint())
            with sqlite3.connect(path) as db:
                db.execute("UPDATE skills SET payload='{}' WHERE version=2")
            with self.assertRaisesRegex(GuardError, "integrity"):
                registry.load("dependency")

    def test_registry_rejects_unvalidated(self):
        skill, _ = learned()
        skill.validated_on = []
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(GuardError):
                Registry(Path(folder) / "skills.sqlite").publish("bad", skill)

    def test_trace_explanation_links_queries_hypotheses_and_ruleouts(self):
        rows = explain_trace(discover())
        self.assertEqual(rows[0]["role"], "not-needed-by-synthetic-oracle")
        self.assertEqual(rows[-1]["role"], "useful-rule-out")
        self.assertEqual(rows[-1]["hypothesis_after"], "likely-dependency-timeout")
        self.assertIn("throttling", rows[-1]["ruled_out_after"])
