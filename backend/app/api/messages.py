from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.core.limiter import limiter
from app.models.user import User
from app.models.channel import ChannelMember
from app.models.message import Message
from app.schemas.message import MessageCreate, MessageUpdate, MessageResponse, PaginatedMessages
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/channels/{channel_id}/messages", tags=["Messages"])


async def assert_channel_member(channel_id: int, user_id: int, db: AsyncSession):
    result = await db.execute(
        select(ChannelMember).where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this channel")


@router.get("", response_model=PaginatedMessages)
async def get_messages(
    channel_id: int,
    page: int = 1,
    page_size: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Fetch messages for a channel, newest first.
    Paginated so we don't load thousands of messages at once.
    page=1 returns the 50 most recent messages.
    """
    await assert_channel_member(channel_id, current_user.id, db)

    # Clamp pagination so a malicious client can't request a huge page
    # (e.g. page_size=1000000) and exhaust the server's memory.
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)

    # Count total messages for pagination info
    count_result = await db.execute(
        select(func.count(Message.id)).where(
            Message.channel_id == channel_id,
            Message.parent_id == None,  # only top-level messages
        )
    )
    total = count_result.scalar()

    # Fetch the page — join users so each message carries its author's name
    offset = (page - 1) * page_size
    result = await db.execute(
        select(Message, User.display_name, User.username)
        .join(User, User.id == Message.user_id)
        .where(Message.channel_id == channel_id, Message.parent_id == None)
        .order_by(Message.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    rows = result.all()

    messages = [
        MessageResponse(
            **{k: getattr(m, k) for k in (
                "id", "content", "channel_id", "user_id",
                "is_edited", "parent_id", "created_at", "updated_at",
            )},
            display_name=display_name,
            username=username,
        )
        for (m, display_name, username) in reversed(rows)
    ]

    return PaginatedMessages(
        messages=messages,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + page_size) < total,
    )


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("30/minute")   # max 30 messages per minute per IP — stops spam flooding
async def send_message(
    request: Request,
    channel_id: int,
    body: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a new message (or reply to a thread if parent_id is set)."""
    await assert_channel_member(channel_id, current_user.id, db)

    # If replying, verify the parent exists in the same channel
    if body.parent_id:
        parent = await db.execute(
            select(Message).where(
                Message.id == body.parent_id,
                Message.channel_id == channel_id,
            )
        )
        if not parent.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Parent message not found")

    message = Message(
        channel_id=channel_id,
        user_id=current_user.id,
        content=body.content.strip(),
        parent_id=body.parent_id,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    return MessageResponse(
        id=message.id,
        content=message.content,
        channel_id=message.channel_id,
        user_id=message.user_id,
        display_name=current_user.display_name,
        username=current_user.username,
        is_edited=message.is_edited,
        parent_id=message.parent_id,
        created_at=message.created_at,
        updated_at=message.updated_at,
    )


@router.patch("/{message_id}", response_model=MessageResponse)
async def edit_message(
    channel_id: int,
    message_id: int,
    body: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Edit your own message."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot edit someone else's message")

    message.content = body.content.strip()
    message.is_edited = True
    await db.flush()
    await db.refresh(message)

    return message


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    channel_id: int,
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete your own message."""
    result = await db.execute(select(Message).where(Message.id == message_id))
    message = result.scalar_one_or_none()

    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    if message.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot delete someone else's message")

    await db.delete(message)
