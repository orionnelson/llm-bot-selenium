"""Bounded single-sweep concurrent monitor; no live scheduler or alert sends."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import time
from .core import MockPlanner, investigate


RECOMMENDATIONS = {
    "likely-dependency-timeout": ["Dependency latency/error alarm", "Correlated request IDs across dependency logs"],
    "likely-throttling": ["Throttle and concurrency alarms", "Review reserved concurrency and trigger backlog"],
    "likely-function-timeout": ["Duration percentile versus timeout alarm", "Inspect slow spans and timeout log events"],
    "no-data": ["Missing-telemetry/expected-invocation check; do not report healthy"],
    "unresolved": ["Collect additional evidence; escalate uncertainty rather than invent a cause"],
}


@dataclass
class Monitor:
    workers: int = 3
    # Bounded demo dedupe memory; a durable pilot needs transactional checkpointing.
    seen: dict = field(default_factory=dict)
    state_store: object = None

    def sweep(self, contexts, port_factory, *, now=None):
        if not 1 <= self.workers <= 8 or not 1 <= len(contexts) <= 100:
            raise ValueError("bounded workers and 1..100 resources required")
        def one(ctx):
            # Port/driver is per task: never share a Selenium browser across threads.
            port = port_factory(ctx)
            try:
                return investigate(port, MockPlanner(), ctx, "monitor-" + ctx.function,
                                   "Find evidence of a Lambda failure", now=now)
            finally:
                close = getattr(port, "close", None)
                if close:
                    close()
        reports = []
        with ThreadPoolExecutor(max_workers=self.workers) as pool:
            jobs = {pool.submit(one, ctx): ctx for ctx in contexts}
            for future in as_completed(jobs):
                ctx = jobs[future]
                try:
                    trace = future.result()
                    finding = trace.result.failure
                    # Deliberately exclude changing capture IDs/time windows from dedupe;
                    # resource + finding changes matter. A pilot also needs TTL/recovery.
                    key = (ctx.account, ctx.region, ctx.function)
                    if self.state_store is not None:
                        duplicate = self.state_store.record(ctx, finding, now() if now else int(time.time()))
                    else:
                        duplicate = self.seen.get(key) == finding
                        self.seen[key] = finding
                    reports.append({"function": ctx.function, "account": ctx.account,
                                    "region": ctx.region, "finding": finding,
                                    "evidence": trace.result.evidence, "duplicate": duplicate,
                                    "recommendations": RECOMMENDATIONS.get(finding, [])})
                except Exception as exc:
                    # A failed/expired resource cannot suppress reports for healthy peers.
                    reports.append({"function": ctx.function, "finding": "blocked",
                                    "error_type": type(exc).__name__,
                                    "recommendations": ["Operator review required; no remediation performed"]})
        if len(self.seen) > 10000:
            self.seen.clear()
        return sorted(reports, key=lambda r: r["function"])
