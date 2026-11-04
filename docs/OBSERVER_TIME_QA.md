# Nonnegative observer timestamps

Recorder timestamps use exact nonnegative integer seconds. Previously a negative timestamp in an earlier hand-built issue event could survive conversion when the final chart was valid; the same event could enter Studio metadata export. Shared recorder validation now refuses negative sample/capture timestamps before appending. Conversion and Studio export already replay recorder validation and inherit this fix. Zero remains valid; loading/expired evidence remains recordable for explicit uncertainty. This validates representation, not clock accuracy, evidence authenticity or consent attestation.

## Executed scenario

`PYTHONPATH=.:tests python docs/observer_time_demo.py` creates and closes its own loopback HTTP fixture. Selenium waits use a fake DOM, not a rendered browser. For each negative capture/sample timestamp, normal capture rejects with zero appended events; forged issue conversion and consented Studio export reject. Restored valid evidence resumes the same observer. The genuine navigation+shortcut issue exports two events, supports independent alternative-route failure investigation and the SAME reusable check supports bounded 300-second failure/dedupe/recovery/loading-unknown/recovery/end ticks. Fresh output/source hash: `OBSERVER_TIME_DEMO.json`.

Commands:

```sh
python -m unittest discover -s tests
python evaluate.py
python -m examples.chart_release
PYTHONPATH=.:tests python docs/observer_time_demo.py
cd ui && npm ci --include=dev --no-audit --no-fund && npm test && npm run build
```

Two initial new unit methods reproduced four failing assertions before the fix. Added actual HTTP/fake-DOM regression verifies capture, conversion, export and connected assistance/release recovery. Two existing condition lines and their error messages changed; no dependencies, schema, framework, scheduler, transport or Studio projection changes.

## Evidence limits

No UI exists for the changed recorder/issue conversion API. Fresh related-fixture screenshot gate remains INCOMPLETE: fixture not freshly rendered; last verified local missing libnspr4.so and remote Grid-to-separate-loopback access limitations carried without repeated probes or bypass. No old screenshots substituted. No new actual browser/model/video acceptance. Full UC1/UC2, expanded Studio/full graph/parallel/capture/replay/handoff gates remain open. Existing owner source, services, canonical DAG, recordings, main releases and production boundaries preserved.
