"""Generated synthetic Selenium skill; requires triage package. No login embedded."""
import json
from triage.core import Action, Skill, replay
from triage.selenium_port import SeleniumPort
DATA = json.loads('{"actions": [{"page": "overview", "query": "invocation_health"}, {"page": "logs", "query": "failure_events"}, {"page": "capacity", "query": "throttling"}], "expected_failure": "likely-dependency-timeout", "intent": "investigate-lambda-failure", "learned_from": "training-001", "schema": 1, "status": "validated", "ui_version": "mock-v1", "validated_on": ["heldout-002"]}')
def run(driver, base_url, context, incident, *, now=None):
    values = dict(DATA)
    values["actions"] = [Action(**a) for a in values["actions"]]
    return replay(Skill(**values), SeleniumPort(driver, base_url), context, incident, now=now)
