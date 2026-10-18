"""Local versioned SQLite skill register with payload integrity checking."""
from dataclasses import asdict
import hashlib
import json
import sqlite3

from .core import Action, GuardError, Skill


class Registry:
    def __init__(self, path):
        self.path = str(path)
        with sqlite3.connect(self.path) as db:
            db.execute("CREATE TABLE IF NOT EXISTS skills (name TEXT, version INTEGER, payload TEXT, digest TEXT, PRIMARY KEY(name, version))")

    def publish(self, name, skill):
        if skill.status != "validated" or not skill.validated_on or skill.learned_from in skill.validated_on:
            raise GuardError("registry requires distinct held-out validation")
        if not isinstance(name, str) or not name or len(name) > 100:
            raise GuardError("invalid skill name")
        payload = json.dumps(asdict(skill), sort_keys=True)
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with sqlite3.connect(self.path) as db:
            db.execute("BEGIN IMMEDIATE")
            version = db.execute("SELECT COALESCE(MAX(version), 0)+1 FROM skills WHERE name=?", (name,)).fetchone()[0]
            db.execute("INSERT INTO skills VALUES (?, ?, ?, ?)", (name, version, payload, digest))
        return version

    def load(self, name, version=None):
        with sqlite3.connect(self.path) as db:
            if version is None:
                row = db.execute("SELECT payload,digest FROM skills WHERE name=? ORDER BY version DESC LIMIT 1", (name,)).fetchone()
            else:
                row = db.execute("SELECT payload,digest FROM skills WHERE name=? AND version=?", (name, version)).fetchone()
        if not row:
            raise GuardError("skill not found")
        payload, digest = row
        if hashlib.sha256(payload.encode()).hexdigest() != digest:
            raise GuardError("stored skill integrity check failed")
        try:
            data = json.loads(payload)
            data["actions"] = [Action(**a) for a in data["actions"]]
            skill = Skill(**data)
            if skill.status != "validated" or not skill.validated_on:
                raise GuardError("stored skill lacks validation")
            return skill
        except (ValueError, KeyError, TypeError) as exc:
            raise GuardError("invalid stored skill") from exc
