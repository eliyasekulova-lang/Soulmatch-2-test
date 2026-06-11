CRITICAL_REASON_CODES = {"minor", "csam", "sexual_content_minor", "violent_threat"}


def is_critical_reason(reason: str) -> bool:
    return reason.lower() in CRITICAL_REASON_CODES
