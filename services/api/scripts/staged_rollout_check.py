import argparse
import json
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import requests


@dataclass
class ProbeSample:
    ok: bool
    latency_ms: float


def evaluate_probe_window(samples: list[ProbeSample], max_error_rate: float, max_p95_ms: float) -> dict:
    total = len(samples)
    if total == 0:
        return {
            "ok": False,
            "reason": "no samples collected",
            "error_rate": 1.0,
            "p95_latency_ms": None,
            "recommendation": "hold",
        }

    failures = sum(1 for sample in samples if not sample.ok)
    error_rate = failures / total
    latencies = sorted(sample.latency_ms for sample in samples)
    p95_index = min(len(latencies) - 1, max(0, int(len(latencies) * 0.95) - 1))
    p95_latency_ms = latencies[p95_index]
    ok = error_rate <= max_error_rate and p95_latency_ms <= max_p95_ms
    return {
        "ok": ok,
        "reason": "thresholds_met" if ok else "thresholds_exceeded",
        "error_rate": round(error_rate, 4),
        "p95_latency_ms": round(p95_latency_ms, 2),
        "recommendation": "promote" if ok else "hold",
    }


def _probe_once(base_url: str, paths: list[str], timeout: float) -> list[ProbeSample]:
    samples: list[ProbeSample] = []
    for path in paths:
        url = f"{base_url.rstrip('/')}{path}"
        started = time.perf_counter()
        try:
            response = requests.get(url, timeout=timeout)
            elapsed_ms = (time.perf_counter() - started) * 1000
            samples.append(ProbeSample(ok=response.status_code == 200, latency_ms=elapsed_ms))
        except requests.RequestException:
            elapsed_ms = (time.perf_counter() - started) * 1000
            samples.append(ProbeSample(ok=False, latency_ms=elapsed_ms))
    return samples


def main() -> None:
    parser = argparse.ArgumentParser(description="Run staged rollout canary checks on critical API paths")
    parser.add_argument("--base-url", required=True, help="API base URL")
    parser.add_argument("--iterations", type=int, default=20, help="How many probe rounds to run")
    parser.add_argument("--interval-seconds", type=float, default=1.0, help="Delay between rounds")
    parser.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout in seconds")
    parser.add_argument("--max-error-rate", type=float, default=0.02, help="Max allowed error rate")
    parser.add_argument("--max-p95-ms", type=float, default=500.0, help="Max allowed p95 latency")
    parser.add_argument(
        "--paths",
        default="/health/live,/health/ready,/health/jobs,/openapi.json",
        help="Comma-separated paths to probe",
    )
    args = parser.parse_args()

    paths = [path.strip() for path in args.paths.split(",") if path.strip()]
    samples: list[ProbeSample] = []
    for idx in range(args.iterations):
        samples.extend(_probe_once(args.base_url, paths, args.timeout))
        if idx < args.iterations - 1:
            time.sleep(args.interval_seconds)

    decision = evaluate_probe_window(
        samples=samples,
        max_error_rate=args.max_error_rate,
        max_p95_ms=args.max_p95_ms,
    )
    payload = {
        "ok": decision["ok"],
        "evaluated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "base_url": args.base_url.rstrip("/"),
        "iterations": args.iterations,
        "paths": paths,
        "sample_count": len(samples),
        "thresholds": {
            "max_error_rate": args.max_error_rate,
            "max_p95_ms": args.max_p95_ms,
        },
        "decision": decision,
    }
    print(json.dumps(payload, indent=2))
    if not decision["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
