from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class PresignResult:
    upload_url: str
    storage_key: str
    expires_at: str


class StorageAdapter:
    def presign_upload(self, media_id: str, content_type: str) -> PresignResult:  # pragma: no cover - interface
        raise NotImplementedError

    def presign_download(self, storage_key: str) -> PresignResult:  # pragma: no cover - interface
        raise NotImplementedError

    def delete_object(self, storage_key: str) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class LocalDevStorageAdapter(StorageAdapter):
    def __init__(self, base_url: str = "http://127.0.0.1:8000/local-media"):
        self.base_url = base_url.rstrip("/")

    def presign_upload(self, media_id: str, content_type: str) -> PresignResult:
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat()
        storage_key = f"uploads/{media_id}"
        return PresignResult(
            upload_url=f"{self.base_url}/upload/{storage_key}?content_type={content_type}",
            storage_key=storage_key,
            expires_at=expires_at,
        )

    def presign_download(self, storage_key: str) -> PresignResult:
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat()
        return PresignResult(
            upload_url=f"{self.base_url}/download/{storage_key}",
            storage_key=storage_key,
            expires_at=expires_at,
        )

    def delete_object(self, storage_key: str) -> None:
        _ = storage_key
        return
