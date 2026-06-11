import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuthUser, MediaObject, Message, MessageThread
from ..security import get_current_auth_user
from ..modules.media.storage import LocalDevStorageAdapter

router = APIRouter(prefix="/media", tags=["media"])
storage = LocalDevStorageAdapter()


class MediaPresignRequest(BaseModel):
    media_type: str = Field(min_length=3, max_length=16)
    mime_type: str = Field(min_length=3, max_length=128)


class MediaPresignResponse(BaseModel):
    ok: bool
    media_id: str
    upload_url: str
    storage_key: str
    expires_at: str


class MediaAttachRequest(BaseModel):
    conversation_id: str = Field(min_length=3, max_length=128)
    message_id: int | None = None
    byte_size: int | None = Field(default=None, ge=1)


class MediaAttachResponse(BaseModel):
    ok: bool
    media_id: str
    status: str


class MediaGetResponse(BaseModel):
    ok: bool
    media_id: str
    download_url: str
    expires_at: str


@router.post("/presign", response_model=MediaPresignResponse)
def media_presign(
    payload: MediaPresignRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    media_id = f"med-{uuid.uuid4().hex[:16]}"
    signed = storage.presign_upload(media_id=media_id, content_type=payload.mime_type)
    row = MediaObject(
        id=media_id,
        owner_user_id=current_user.id,
        media_type=payload.media_type,
        mime_type=payload.mime_type,
        storage_key=signed.storage_key,
        status="active",
    )
    db.add(row)
    db.commit()
    return {
        "ok": True,
        "media_id": media_id,
        "upload_url": signed.upload_url,
        "storage_key": signed.storage_key,
        "expires_at": signed.expires_at,
    }


@router.post("/{media_id}/attach", response_model=MediaAttachResponse)
def media_attach(
    media_id: str,
    payload: MediaAttachRequest,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    row = db.get(MediaObject, media_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="media_not_found")
    if row.owner_user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="media_not_owned")

    thread = db.get(MessageThread, payload.conversation_id)
    if not thread or current_user.id not in {thread.user_a_id, thread.user_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="conversation_access_denied")

    if payload.message_id:
        message = db.get(Message, payload.message_id)
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="message_not_found")
        if message.thread_id != payload.conversation_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="message_conversation_mismatch")

    row.conversation_id = payload.conversation_id
    row.message_id = payload.message_id
    row.byte_size = payload.byte_size
    row.attached_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "media_id": row.id, "status": row.status}


@router.get("/{media_id}", response_model=MediaGetResponse)
def media_get(
    media_id: str,
    db: Session = Depends(get_db),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    row = db.get(MediaObject, media_id)
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="media_not_found")

    if row.owner_user_id != current_user.id:
        thread = db.get(MessageThread, row.conversation_id) if row.conversation_id else None
        if not thread or current_user.id not in {thread.user_a_id, thread.user_b_id}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="media_access_denied")

    if row.status in {"quarantined", "removed"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="media_unavailable")

    signed = storage.presign_download(row.storage_key)
    return {
        "ok": True,
        "media_id": row.id,
        "download_url": signed.upload_url,
        "expires_at": signed.expires_at,
    }
