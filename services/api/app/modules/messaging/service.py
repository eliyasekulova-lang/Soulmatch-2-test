def normalize_client_message_id(value: str | None) -> str | None:
    if not value:
        return None
    return value.strip()[:128]
