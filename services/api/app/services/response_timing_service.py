from __future__ import annotations

from dataclasses import dataclass
from statistics import median
from typing import Iterable

from .psychology_response_adapter import NormalizedPsychologyResponse


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


@dataclass(frozen=True)
class ResponseTimingSummary:
    timing_confidence: float
    hesitation_score: float
    ambivalence_score: float
    reflection_score: float
    speeding_flag: bool
    change_signal: float
    return_signal: float
    skipped_ratio: float
    answered_count: int
    median_response_ms: int | None


def analyze_response_timing(responses: Iterable[NormalizedPsychologyResponse]) -> ResponseTimingSummary:
    rows = list(responses)
    answered = [row for row in rows if not row.skipped and _resolved_answer(row) is not None]
    if not rows:
        return ResponseTimingSummary(
            timing_confidence=0.0,
            hesitation_score=0.0,
            ambivalence_score=0.0,
            reflection_score=0.0,
            speeding_flag=False,
            change_signal=0.0,
            return_signal=0.0,
            skipped_ratio=0.0,
            answered_count=0,
            median_response_ms=None,
        )

    times = [int(row.response_time_ms) for row in answered if row.response_time_ms is not None and row.response_time_ms > 0]
    median_response_ms = int(median(times)) if times else None
    answered_count = len(answered)
    skipped_ratio = clamp((len(rows) - answered_count) / float(len(rows)))

    changed_values = [max(0, int(row.changed_answer_count)) for row in answered]
    change_signal = clamp(sum(min(value, 3) for value in changed_values) / float(max(1, answered_count) * 3))

    return_signal = clamp(sum(1 for row in answered if row.returned_to_question) / float(max(1, answered_count)))

    drift_scores = []
    for row in answered:
        if row.first_answer_value is None or row.final_answer_value is None:
            continue
        drift_scores.append(abs(int(row.first_answer_value) - int(row.final_answer_value)) / 4.0)
    answer_drift = sum(drift_scores) / float(len(drift_scores) or 1)

    slow_factor = 0.0
    if median_response_ms is not None:
        slow_factor = clamp((median_response_ms - 2200) / 7000.0)
    hesitation_score = clamp((slow_factor * 0.45) + (change_signal * 0.30) + (return_signal * 0.20) + (skipped_ratio * 0.05))
    ambivalence_score = clamp((answer_drift * 0.5) + (change_signal * 0.3) + (return_signal * 0.2))

    reflection_base = 0.0
    if median_response_ms is not None:
        if 900 <= median_response_ms <= 7000:
            reflection_base = 1.0 - (abs(median_response_ms - 2800) / 6100.0)
        else:
            reflection_base = 0.2
    reflection_score = clamp((reflection_base * 0.6) + (change_signal * 0.2) + (return_signal * 0.2))

    speeding_flag = bool(median_response_ms is not None and answered_count >= 8 and median_response_ms < 350)

    timing_coverage = clamp(len(times) / float(max(1, answered_count)))
    timing_confidence = clamp((timing_coverage * 0.7) + ((1.0 - skipped_ratio) * 0.3) - (change_signal * 0.15))

    return ResponseTimingSummary(
        timing_confidence=timing_confidence,
        hesitation_score=hesitation_score,
        ambivalence_score=ambivalence_score,
        reflection_score=reflection_score,
        speeding_flag=speeding_flag,
        change_signal=change_signal,
        return_signal=return_signal,
        skipped_ratio=skipped_ratio,
        answered_count=answered_count,
        median_response_ms=median_response_ms,
    )


def _resolved_answer(row: NormalizedPsychologyResponse) -> int | None:
    for value in (row.considered_answer_value, row.final_answer_value, row.answer_value, row.first_answer_value):
        if value is not None:
            return int(value)
    return None
