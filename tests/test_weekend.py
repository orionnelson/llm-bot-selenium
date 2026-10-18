from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from triage.core import GuardError
from triage.fixtures import FixturePort
from triage.monitor import Monitor
from triage.weekend import MonitorState, WeekendPlan
from test_core import CTX, NOW


class WeekendTests(unittest.TestCase):
    def test_weekend_and_interval_policy_without_live_scheduling(self):
        plan = WeekendPlan("UTC", 900)
        friday = datetime(2026, 10, 16, 23, 59, tzinfo=timezone.utc)
        saturday = datetime(2026, 10, 17, 0, 0, tzinfo=timezone.utc)
        soon = datetime(2026, 10, 17, 0, 5, tzinfo=timezone.utc)
        due = datetime(2026, 10, 17, 0, 15, tzinfo=timezone.utc)
        monday = datetime(2026, 10, 19, 0, 0, tzinfo=timezone.utc)
        self.assertFalse(plan.due(friday))
        self.assertTrue(plan.due(saturday))
        self.assertFalse(plan.due(soon, saturday))
        self.assertTrue(plan.due(due, saturday))
        self.assertFalse(plan.due(monday))

    def test_weekend_uses_selected_timezone_not_utc_weekday(self):
        # Saturday UTC is still Friday in New York at this instant.
        instant = datetime(2026, 10, 17, 1, 0, tzinfo=timezone.utc)
        self.assertTrue(WeekendPlan("UTC").due(instant))
        self.assertFalse(WeekendPlan("America/New_York").due(instant))

    def test_naive_timestamps_and_backwards_clock_rejected(self):
        plan = WeekendPlan()
        with self.assertRaises(GuardError):
            plan.due(datetime(2026, 10, 17))
        with self.assertRaises(GuardError):
            plan.due(datetime(2026, 10, 17, tzinfo=timezone.utc), datetime(2026, 10, 18, tzinfo=timezone.utc))

    def test_durable_dedupe_restart_ttl_recovery_and_recurrence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "monitor.sqlite"
            self.assertFalse(MonitorState(path, remind_after_seconds=60).record(CTX, "failure", NOW))
            self.assertTrue(MonitorState(path, remind_after_seconds=60).record(CTX, "failure", NOW+1))
            self.assertFalse(MonitorState(path, remind_after_seconds=60).record(CTX, "failure", NOW+60))
            self.assertFalse(MonitorState(path).record(CTX, "no-failure-observed", NOW+61))
            self.assertFalse(MonitorState(path).record(CTX, "failure", NOW+62))
            with self.assertRaises(GuardError):
                MonitorState(path).record(CTX, "failure", NOW)

    def test_monitor_restart_preserves_dedupe(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "monitor.sqlite"
            first = Monitor(state_store=MonitorState(path)).sweep([CTX], lambda ctx: FixturePort(), now=lambda: NOW)
            second = Monitor(state_store=MonitorState(path)).sweep([CTX], lambda ctx: FixturePort(), now=lambda: NOW)
            self.assertFalse(first[0]["duplicate"])
            self.assertTrue(second[0]["duplicate"])
