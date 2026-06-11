import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..legal_guard import require_current_consent
from ..models import AuthUser, Conversation, ConversationMember, Message, MessageThread, User
from ..modules.safety_service import (
    enforce_message_friction,
    recipient_protection_flags,
    should_hide_message_for_recipient,
    update_risk_for_event,
)
from ..rate_limit import rate_limiter
from ..security import get_current_auth_user
from ..settings import get_settings

router = APIRouter(tags=["messaging"])
settings = get_settings()


def _pair_key(user_id_1: str, user_id_2: str) -> str:
    a, b = sorted([user_id_1, user_id_2])
    return f"{a}:{b}"


class ThreadCreateRequest(BaseModel):
    other_user_id: str = Field(min_length=3, max_length=128)


class ThreadSummary(BaseModel):
    thread_id: str
    other_user_id: str
    other_user_name: str
    updated_at: str
    last_message: str | None = None


class ThreadListResponse(BaseModel):
    ok: bool
    threads: list[ThreadSummary]


class MessageSendRequest(BaseModel):
    thread_id: str | None = Field(default=None, min_length=3, max_length=128)
    body: str = Field(min_length=1, max_length=2000)
    client_message_id: str | None = Field(default=None, min_length=3, max_length=128)


class MessageItem(BaseModel):
    id: int
    thread_id: str
    sender_user_id: str
    recipient_user_id: str
    body: str
    hidden_by_safety: bool = False
    created_at: str


class MessageListResponse(BaseModel):
    ok: bool
    thread_id: str
    messages: list[MessageItem]
    next_cursor: int | None = None


class MessageSendResponse(BaseModel):
    ok: bool
    message: MessageItem


@router.post("/messages/threads", response_model=ThreadSummary)
@router.post("/conversations", response_model=ThreadSummary)
def create_or_get_thread(
    payload: ThreadCreateRequest,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    current_profile = db.get(User, current_user.id)
    other_profile = db.get(User, payload.other_user_id)
    if not current_profile:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="current_profile_missing")
    if not other_profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="other_user_not_found")
    if payload.other_user_id == current_user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="other_user_must_be_different")

    pair_key = _pair_key(current_user.id, payload.other_user_id)
    thread = db.scalar(select(MessageThread).where(MessageThread.pair_key == pair_key))
    if not thread:
        a, b = sorted([current_user.id, payload.other_user_id])
        thread = MessageThread(
            id=f"thr-{uuid.uuid4().hex[:16]}",
            pair_key=pair_key,
            user_a_id=a,
            user_b_id=b,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(thread)
    conv = db.get(Conversation, thread.id)
    if not conv:
        db.add(Conversation(id=thread.id, created_at=datetime.utcnow(), updated_at=datetime.utcnow()))
    for uid in [thread.user_a_id, thread.user_b_id]:
        membership = db.scalar(
            select(ConversationMember).where(
                ConversationMember.conversation_id == thread.id,
                ConversationMember.user_id == uid,
            )
        )
        if not membership:
            db.add(ConversationMember(conversation_id=thread.id, user_id=uid, joined_at=datetime.utcnow(), left_at=None))
    db.commit()
    db.refresh(thread)

    last_msg = db.scalar(select(Message).where(Message.thread_id == thread.id).order_by(Message.id.desc()).limit(1))
    return ThreadSummary(
        thread_id=thread.id,
        other_user_id=other_profile.id,
        other_user_name=other_profile.name,
        updated_at=thread.updated_at.isoformat(),
        last_message=(last_msg.body if last_msg else None),
    )


@router.get("/messages/threads", response_model=ThreadListResponse)
@router.get("/conversations", response_model=ThreadListResponse)
def list_threads(
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    rows = db.scalars(
        select(MessageThread).where(
            or_(MessageThread.user_a_id == current_user.id, MessageThread.user_b_id == current_user.id)
        )
    ).all()

    other_ids: list[str] = []
    for row in rows:
        other_ids.append(row.user_b_id if row.user_a_id == current_user.id else row.user_a_id)
    users = {u.id: u for u in db.scalars(select(User).where(User.id.in_(other_ids))).all()}

    out: list[ThreadSummary] = []
    for row in sorted(rows, key=lambda r: r.updated_at, reverse=True):
        other_id = row.user_b_id if row.user_a_id == current_user.id else row.user_a_id
        other = users.get(other_id)
        last_msg = db.scalar(select(Message).where(Message.thread_id == row.id).order_by(Message.id.desc()).limit(1))
        out.append(
            ThreadSummary(
                thread_id=row.id,
                other_user_id=other_id,
                other_user_name=other.name if other else other_id,
                updated_at=row.updated_at.isoformat(),
                last_message=(last_msg.body if last_msg else None),
            )
        )

    return ThreadListResponse(ok=True, threads=out)


def _thread_access_or_403(db: Session, thread_id: str, user_id: str) -> MessageThread:
    thread = db.get(MessageThread, thread_id)
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="thread_not_found")
    if user_id not in {thread.user_a_id, thread.user_b_id}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="thread_access_denied")
    return thread


@router.get("/messages/threads/{thread_id}", response_model=MessageListResponse)
@router.get("/conversations/{thread_id}/messages", response_model=MessageListResponse)
def list_messages(
    thread_id: str,
    cursor: int | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    _thread_access_or_403(db, thread_id, current_user.id)
    thread = db.get(MessageThread, thread_id)
    counterparty_id = thread.user_b_id if current_user.id == thread.user_a_id else thread.user_a_id
    safety_flags = recipient_protection_flags(db, counterparty_id)

    stmt = select(Message).where(Message.thread_id == thread_id)
    if cursor:
        stmt = stmt.where(Message.id < cursor)
    rows = db.scalars(stmt.order_by(Message.id.desc()).limit(limit + 1)).all()
    has_next = len(rows) > limit
    rows = rows[:limit]
    next_cursor = rows[-1].id if has_next and rows else None

    return MessageListResponse(
        ok=True,
        thread_id=thread_id,
        messages=[
            MessageItem(
                id=row.id,
                thread_id=row.thread_id,
                sender_user_id=row.sender_user_id,
                recipient_user_id=row.recipient_user_id,
                body=(
                    "[Safety-hidden message. Tap to reveal in app.]"
                    if row.hidden_by_safety and row.sender_user_id != current_user.id and safety_flags["auto_hide_enabled"]
                    else row.body
                ),
                hidden_by_safety=bool(row.hidden_by_safety),
                created_at=row.created_at.isoformat(),
            )
            for row in reversed(rows)
        ],
        next_cursor=next_cursor,
    )


@router.post("/messages/send", response_model=MessageSendResponse)
@router.post("/conversations/{thread_id}/messages", response_model=MessageSendResponse)
def send_message(
    payload: MessageSendRequest,
    thread_id: str | None = None,
    db: Session = Depends(get_db),
    _consent: None = Depends(require_current_consent),
    current_user: AuthUser = Depends(get_current_auth_user),
):
    req_thread_id = thread_id or payload.thread_id
    req_body = payload.body.strip()
    if not req_thread_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="thread_id_required")

    # Baseline anti-abuse limiter independent of risk banding.
    rate_limiter.check(
        key=f"message_send:{current_user.id}",
        max_requests=settings.message_send_rate_limit_per_minute,
        window_seconds=60,
    )

    thread = _thread_access_or_403(db, req_thread_id, current_user.id)
    allowed, friction_msg = enforce_message_friction(db, current_user.id)
    if not allowed:
        db.commit()
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=friction_msg)
    recipient_id = thread.user_b_id if current_user.id == thread.user_a_id else thread.user_a_id

    if payload.client_message_id:
        existing = db.scalar(
            select(Message).where(
                and_(
                    Message.thread_id == req_thread_id,
                    Message.sender_user_id == current_user.id,
                    Message.client_message_id == payload.client_message_id,
                )
            )
        )
        if existing:
            return MessageSendResponse(
                ok=True,
                message=MessageItem(
                    id=existing.id,
                    thread_id=existing.thread_id,
                    sender_user_id=existing.sender_user_id,
                    recipient_user_id=existing.recipient_user_id,
                    body=existing.body,
                    created_at=existing.created_at.isoformat(),
                ),
            )

    msg = Message(
        thread_id=thread.id,
        sender_user_id=current_user.id,
        recipient_user_id=recipient_id,
        body=req_body,
        hidden_by_safety=should_hide_message_for_recipient(req_body, current_user.id, db),
        client_message_id=payload.client_message_id,
        created_at=datetime.utcnow(),
    )
    thread.updated_at = datetime.utcnow()
    conv = db.get(Conversation, thread.id)
    if conv:
        conv.updated_at = datetime.utcnow()
    db.add(msg)
    db.commit()
    db.refresh(msg)
    try:
        update_risk_for_event(db, current_user.id, "message_sent", {"body": req_body})
        db.commit()
    except Exception:
        db.rollback()

    return MessageSendResponse(
        ok=True,
        message=MessageItem(
            id=msg.id,
            thread_id=msg.thread_id,
            sender_user_id=msg.sender_user_id,
            recipient_user_id=msg.recipient_user_id,
            body=msg.body,
            hidden_by_safety=bool(msg.hidden_by_safety),
            created_at=msg.created_at.isoformat(),
        ),
    )
