"""Single-writer, hash-chained synthetic audit; not immutable external storage."""
import hashlib
import json
import os
from pathlib import Path
import threading

from .core import GuardError


def _digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def verify_audit(path):
    previous = "0" * 64
    rows = []
    if not Path(path).exists():
        return rows
    try:
        for line in Path(path).read_text().splitlines():
            row = json.loads(line)
            claimed = row.pop("sha256")
            if row.get("previous") != previous or row.get("sequence") != len(rows) + 1 or _digest(row) != claimed:
                raise GuardError("audit chain is invalid")
            row["sha256"] = claimed
            previous = claimed
            rows.append(row)
    except (ValueError, KeyError, TypeError) as exc:
        raise GuardError("audit is malformed or tampered") from exc
    return rows


class Audit:
    """Fail closed on write error. One instance / process owns a given file."""
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if self.path.is_symlink():
            raise GuardError("audit path must not be a symlink")
        rows = verify_audit(self.path)
        self.previous = rows[-1]["sha256"] if rows else "0" * 64
        self.sequence = len(rows)
        self.lock = threading.Lock()

    def record(self, event, data):
        with self.lock:
            row = {"sequence": self.sequence + 1, "previous": self.previous, "event": event, "data": data}
            row["sha256"] = _digest(row)
            encoded = (json.dumps(row, sort_keys=True, allow_nan=False) + "\n").encode()
            flags = os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
            try:
                fd = os.open(self.path, flags, 0o600)
                with os.fdopen(fd, "ab") as stream:
                    stream.write(encoded)
                    stream.flush()
                    os.fsync(stream.fileno())
            except OSError as exc:
                raise GuardError("audit write failed; execution stopped") from exc
            self.previous = row["sha256"]
            self.sequence += 1
