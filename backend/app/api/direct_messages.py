from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.user import User
from app.models.direct_message import DMConversation, DMParticipant, DirectMessage
from app.models.attachment import Attachment
from app.schemas.message import AttachmentInfo
from app.schemas.direct_message import (
    StartDMRequest, DMUser, DMConversationResponse,
    DirectMessageCreate, DirectMessageResponse, PaginatedDirectMessages,
)
from app.core.dependencies import get_current_user
from app.core.limiter import limiter
from app.core.files import save_upload, attachment_url

router = APIRouter(prefix="/dm", tags=["Direct Messages"])


def _attachment_info(att: Attachment) -> AttachmentInfo:
    return AttachmentInfo(
        id=att.id,
        filename=att.filename,
        url=attachment_url(att.stored_name),
        content_type=att.content_type,
        size=att.size,
    )


async def assert_participant(conversation_id: int, user_id: int, db: AsyncSession):
    """Raise 403 if the user is not part of this conversation."""
    result = await db.execute(
        select(DMParticipant).where(
            DMParticipant.conversation_id == conversation_id,
            DMParticipant.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not part of this conversation")


async def get_other_user(conversation_id: int, me_id: int, db: AsyncSession) -> User:
    """Return the OTHER person in a 1-to-1 conversation."""
    result = await db.execute(
        select(User)
        .join(DMParticipant, DMParticipant.user_id == User.id)
        .where(
            DMParticipant.conversation_id == conversation_id,
            DMParticipant.user_id != me_id,
        )
    )
    return result.scalar_one_or_none()


@router.post("/start", response_model=DMConversationResponse, status_code=status.HTTP_201_CREATED)
async def start_dm(
    body: StartDMRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Start a DM with someone by username — or return the existing
    conversation if you've already talked before.
    """
    # Find the target user
    target_row = await db.execute(select(User).where(User.username == body.username))
    target = target_row.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == current_user.id:
        raise HTTPException(status_code=400, detail="You can't DM yourself")

    # Look for an existing conversation that BOTH users are part of.
    # We find conversation ids containing me, then check which also contain them.
    my_convos = select(DMParticipant.conversation_id).where(
        DMParticipant.user_id == current_user.id
    )
    shared = await db.execute(
        select(DMParticipant.conversation_id).where(
            DMParticipant.user_id == target.id,
            DMParticipant.conversation_id.in_(my_convos),
        )
    )
    existing_id = shared.scalars().first()

    if existing_id:
        conversation_id = existing_id
    else:
        # Create a new conversation with two participants
        conversation = DMConversation()
        db.add(conversation)
        await db.flush()
        db.add(DMParticipant(conversation_id=conversation.id, user_id=current_user.id))
        db.add(DMParticipant(conversation_id=conversation.id, user_id=target.id))
        await db.flush()
        conversation_id = conversation.id

    # Read created_at for the response
    convo_row = await db.execute(
        select(DMConversation).where(DMConversation.id == conversation_id)
    )
    convo = convo_row.scalar_one()

    return DMConversationResponse(
        id=conversation_id,
        other_user=DMUser.model_validate(target),
        created_at=convo.created_at,
    )


@router.get("", response_model=list[DMConversationResponse])
async def list_dms(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all my DM conversations, showing the other person in each."""
    # All conversation ids I'm part of
    my_convo_ids = (await db.execute(
        select(DMParticipant.conversation_id).where(
            DMParticipant.user_id == current_user.id
        )
    )).scalars().all()

    conversations = []
    for convo_id in my_convo_ids:
        other = await get_other_user(convo_id, current_user.id, db)
        if not other:
            continue  # skip malformed/solo conversations
        convo = (await db.execute(
            select(DMConversation).where(DMConversation.id == convo_id)
        )).scalar_one()
        conversations.append(DMConversationResponse(
            id=convo_id,
            other_user=DMUser.model_validate(other),
            created_at=convo.created_at,
        ))

    return conversations


@router.get("/{conversation_id}/messages", response_model=PaginatedDirectMessages)
async def get_dm_messages(
    conversation_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch messages in a conversation, newest first, paginated."""
    await assert_participant(conversation_id, current_user.id, db)

    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    total = (await db.execute(
        select(func.count(DirectMessage.id)).where(
            DirectMessage.conversation_id == conversation_id
        )
    )).scalar()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(DirectMessage, User.display_name, User.username)
        .join(User, User.id == DirectMessage.user_id)
        .where(DirectMessage.conversation_id == conversation_id)
        .order_by(DirectMessage.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    # Load attachments for these DM messages in one query
    message_ids = [m.id for (m, _dn, _un) in rows]
    attachments_by_msg = {}
    if message_ids:
        att_rows = await db.execute(
            select(Attachment).where(Attachment.dm_message_id.in_(message_ids))
        )
        for att in att_rows.scalars().all():
            attachments_by_msg[att.dm_message_id] = _attachment_info(att)

    messages = [
        DirectMessageResponse(
            **{k: getattr(m, k) for k in (
                "id", "conversation_id", "user_id",
                "content", "is_edited", "created_at", "updated_at",
            )},
            display_name=display_name,
            username=username,
            attachment=attachments_by_msg.get(m.id),
        )
        for (m, display_name, username) in reversed(rows)
    ]

    return PaginatedDirectMessages(
        messages=messages,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.post("/{conversation_id}/messages", response_model=DirectMessageResponse,
             status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")
async def send_dm(
    request: Request,
    conversation_id: int,
    body: DirectMessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a DM (HTTP fallback — the live path is the WebSocket)."""
    await assert_participant(conversation_id, current_user.id, db)

    content = body.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    message = DirectMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=content,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    return DirectMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        user_id=message.user_id,
        display_name=current_user.display_name,
        username=current_user.username,
        content=message.content,
        is_edited=message.is_edited,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@router.post("/{conversation_id}/upload", response_model=DirectMessageResponse,
             status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def upload_dm_file(
    request: Request,
    conversation_id: int,
    file: UploadFile = File(...),
    caption: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file into a DM conversation and broadcast it live."""
    await assert_participant(conversation_id, current_user.id, db)

    stored_name, size = await save_upload(file)

    message = DirectMessage(
        conversation_id=conversation_id,
        user_id=current_user.id,
        content=(caption or "").strip(),
    )
    db.add(message)
    await db.flush()

    attachment = Attachment(
        dm_message_id=message.id,
        uploader_id=current_user.id,
        filename=file.filename or stored_name,
        stored_name=stored_name,
        content_type=file.content_type or "application/octet-stream",
        size=size,
    )
    db.add(attachment)
    await db.flush()
    await db.refresh(message)
    await db.refresh(attachment)

    att_info = _attachment_info(attachment)

    from app.api.websocket import dm_manager
    await dm_manager.broadcast(conversation_id, {
        "type": "message",
        "id": message.id,
        "content": message.content,
        "user_id": message.user_id,
        "display_name": current_user.display_name,
        "username": current_user.username,
        "conversation_id": message.conversation_id,
        "attachment": att_info.model_dump(),
        "created_at": message.created_at.isoformat(),
    })

    return DirectMessageResponse(
        id=message.id,
        conversation_id=message.conversation_id,
        user_id=message.user_id,
        display_name=current_user.display_name,
        username=current_user.username,
        content=message.content,
        is_edited=message.is_edited,
        attachment=att_info,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )
