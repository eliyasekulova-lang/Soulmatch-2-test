from scripts.staged_rollout_check import ProbeSample, evaluate_probe_window


def test_staged_rollout_decision_promote_when_thresholds_met():
    samples = [
        ProbeSample(ok=True, latency_ms=90),
        ProbeSample(ok=True, latency_ms=110),
        ProbeSample(ok=True, latency_ms=130),
        ProbeSample(ok=False, latency_ms=100),
    ]
    decision = evaluate_probe_window(samples, max_error_rate=0.3, max_p95_ms=200)
    assert decision["ok"] is True
    assert decision["recommendation"] == "promote"


def test_staged_rollout_decision_hold_when_error_rate_high():
    samples = [
        ProbeSample(ok=False, latency_ms=90),
        ProbeSample(ok=False, latency_ms=100),
        ProbeSample(ok=True, latency_ms=110),
        ProbeSample(ok=True, latency_ms=120),
    ]
    decision = evaluate_probe_window(samples, max_error_rate=0.2, max_p95_ms=200)
    assert decision["ok"] is False
    assert decision["recommendation"] == "hold"
