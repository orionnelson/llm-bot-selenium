"""Weekend polling policy and durable dedupe for synthetic monitoring demos.

No daemon, cron installation, alert sends or production targets. A caller must
own browser deadlines, session lifecycle and operational authorization.
"""
from datetime import datetime
import sqlite3
from zoneinfo import ZoneInfo

from .core import GuardError


class WeekendPlan:
    def __init__(self, timezone="UTC", interval_seconds=900):
        if type(interval_seconds) is not int or not 60 <= interval_seconds <= 86400:
            raise GuardError("poll interval must be 60 seconds..24 hours")
        self.zone = ZoneInfo(timezone)
        self.interval = interval_seconds

    def due(self, instant: datetime, last_poll: datetime | None = None):
        if instant.tzinfo is None or (last_poll is not None and last_poll.tzinfo is None):
            raise GuardError("timezone-aware polling timestamps required")
        if instant.astimezone(self.zone).weekday() < 5:
            return False
        if last_poll is None:
            return True
        seconds = instant.timestamp() - last_poll.timestamp()
        if seconds < 0:
            raise GuardError("poll clock moved backwards")
        return seconds >= self.interval


class MonitorState:
    """One local transaction per result; stores no log bodies or credentials."""
    def __init__(self, path, *, remind_after_seconds=14400):
        if type(remind_after_seconds) is not int or remind_after_seconds < 60:
            raise GuardError("invalid reminder TTL")
        self.path, self.ttl = str(path), remind_after_seconds
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS findings (account TEXT, region TEXT, function TEXT, finding TEXT, notified_at INTEGER, observed_at INTEGER, PRIMARY KEY(account,region,function))")

    def record(self, context, finding, now):
        context.check()
        if type(now) is not int or now < 0 or not isinstance(finding, str) or len(finding) > 100:
            raise GuardError("invalid monitor state update")
        key = (context.account, context.region, context.function)
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            old = db.execute("SELECT finding,notified_at,observed_at FROM findings WHERE account=? AND region=? AND function=?", key).fetchone()
            if old and now < old[2]:
                raise GuardError("monitor clock moved backwards")
            duplicate = bool(old and old[0] == finding and now-old[1] < self.ttl)
            notified_at = old[1] if duplicate else now
            db.execute("INSERT OR REPLACE INTO findings VALUES (?,?,?,?,?,?)", (*key, finding, notified_at, now))
        return duplicate
