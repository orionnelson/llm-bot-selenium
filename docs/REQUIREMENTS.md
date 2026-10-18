# Product requirements — confirmed by Orion, 2026-10-18

These two use cases supersede older descriptions that made human observation optional or treated this as another log-combing tool. Existing log analysis is already provided elsewhere.

## 1. Assist the person triaging

Observe an explicitly approved SRE browser session while they navigate Dynatrace, inspect pages/charts and use shortcuts. Record an issue with a timestamped timeline of meaningful navigation, shortcut actions and the visible page context/evidence: entity, filters, time range, chart labels and loading state. Do not collect arbitrary keystrokes, passwords, cookies or session tokens. Capture only consented/allowlisted pages; real data requires an approved storage/model boundary.

The bot interprets what those pages show, identifies relevant evidence and uncertainty, then investigates the recorded issue through its **own** permitted browser navigation. It must not merely replay clicks, claim to know the SRE's private reasoning, or replace the existing log tool. Keep the person's browser separate from the bot's investigation so it cannot interrupt the SRE.

**Acceptance:** a synthetic SRE journey with navigation and a shortcut creates an issue bundle; the bot consumes page-grounded observations, independently chooses an alternative navigation path, verifies fresh evidence and returns a supported conclusion for the person. Compare against an expected result and include misleading text, changed time filters, missing/loading data and expired sessions. Deterministic recorder tests and real model/browser acceptance are separate gates. Existing mock-planner tests do not satisfy this use case.

## 2. Reuse those checks for autonomous monitoring

Take an observed, SRE-validated check such as “this chart looks fine” and make it a reusable building block. Bind the chart/entity/filters/time window and an explicit expected condition; do not infer a reliable failure rule solely from a screenshot or lack of errors.

Support a request such as: **“Check this chart every five minutes during this release and look for failures.”** The check plan records cadence (300 seconds in this example), release start/end or a stop condition, scope, expected evidence and reporting/dedupe policy. Reuse the observed chart check rather than creating an unrelated log-scanning pipeline.

**Acceptance:** use a controllable clock to exercise a bounded release window, healthy and failing chart states, stale/missing data, repeated failures, session expiry and explicit stop. A monitoring failure/unknown produces evidence and uncertainty, not a false healthy result. Reuse the same building-block representation produced by use case 1. No wall-clock sleeps in tests.

A human authorizes a real check plan and its live schedule/alert destination before deployment. This requirement does not itself authorize real Dynatrace access, release monitoring, SSO reuse or production alerts.

## Implementation order and scope

1. Correct public README/spec/architecture to put these two use cases first.
2. Build the smallest synthetic observer → issue bundle → page interpretation → independent investigation slice.
3. Reuse the resulting validated checks for the release-window monitoring slice; keep both acceptance suites passing.
4. Add approved actual Edge/msedgedriver and actual model runs with honest evidence when runtimes/access are available. Retain Chrome compatibility.

Reuse useful existing policy, browser, trace and monitoring code. Do not expand a generic framework, add another log collector or prioritize weekend scheduling over these user journeys. Audit/registry/compiled-script helpers are supporting components, not the product goal. Use installed Ponytail principles: necessary code, small tested changes, no loss of safeguards.

## Automation and reporting

The existing daily project-work cron implements/tests these requirements. Its development cadence is separate from the eventual per-chart monitoring cadence. It must not install a live five-minute production job.

Repository: `orionnelson/llm-bot-selenium`. Work in feature branches and PRs targeting `blue-master`; auto-merge only tested exact heads after checks pass. Releases into `main` remain human-controlled. Every PR includes a concise summary, architecture diagram, file walkthrough, test evidence and limitations. Email concise work/PR reports to `me@or9.ca` only through a verified transport; otherwise save the report and record the delivery blocker.
