from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.workspace import WorkspaceMember
from app.models.channel import Channel, ChannelMember
from app.schemas.channel import ChannelCreate, ChannelResponse
from app.core.dependencies import get_current_user

router = APIRouter(prefix="/workspaces/{workspace_id}/channels", tags=["Channels"])


async def assert_workspace_member(workspace_id: int, user_id: int, db: AsyncSession):
    """Raise 403 if the user is not in the workspace."""
    result = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this workspace")


@router.get("", response_model=list[ChannelResponse])
async def list_channels(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Return all channels in a workspace that the current user can see.
    Public channels are visible to all workspace members.
    Private channels only appear if the user is a member.
    """
    await assert_workspace_member(workspace_id, current_user.id, db)

    result = await db.execute(
        select(Channel).where(
            Channel.workspace_id == workspace_id,
            # Show public channels OR private channels the user joined
            (Channel.is_private == False) |
            Channel.id.in_(
                select(ChannelMember.channel_id).where(ChannelMember.user_id == current_user.id)
            )
        )
    )
    return result.scalars().all()


@router.post("", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    workspace_id: int,
    body: ChannelCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await assert_workspace_member(workspace_id, current_user.id, db)

    # Prevent duplicate channel names in the same workspace
    existing = await db.execute(
        select(Channel).where(Channel.workspace_id == workspace_id, Channel.name == body.name)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A channel with that name already exists")

    channel = Channel(
        workspace_id=workspace_id,
        name=body.name,
        description=body.description,
        is_private=body.is_private,
        created_by=current_user.id,
    )
    db.add(channel)
    await db.flush()

    # Creator automatically joins the channel
    db.add(ChannelMember(channel_id=channel.id, user_id=current_user.id))
    await db.refresh(channel)

    return channel


@router.post("/{channel_id}/join", response_model=ChannelResponse)
async def join_channel(
    workspace_id: int,
    channel_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Join a public channel."""
    await assert_workspace_member(workspace_id, current_user.id, db)

    result = await db.execute(
        select(Channel).where(Channel.id == channel_id, Channel.workspace_id == workspace_id)
    )
    channel = result.scalar_one_or_none()
    if not channel:
        raise HTTPException(status_code=404, detail="Channel not found")
    if channel.is_private:
        raise HTTPException(status_code=403, detail="Cannot self-join a private channel")

    # Idempotent: if already a member, just return the channel
    existing = await db.execute(
        select(ChannelMember).where(
            ChannelMember.channel_id == channel_id,
            ChannelMember.user_id == current_user.id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(ChannelMember(channel_id=channel_id, user_id=current_user.id))

    return channel
