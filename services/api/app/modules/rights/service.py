BACKUP_EVENTUAL_DELETION_DAYS = 35


def backup_deletion_note() -> str:
    return f"Backups purge within scheduled window (up to {BACKUP_EVENTUAL_DELETION_DAYS} days)."
