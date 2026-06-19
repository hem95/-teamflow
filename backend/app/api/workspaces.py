from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember, MemberRole
from app.models.channel import Channel, ChannelMember
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse
from app.core.dependencies import get_current_user
import re

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


def make_slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(
    body: WorkspaceCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new workspace. The creator automatically becomes the owner
    and a #general channel is created for them.
    """
    slug = make_slug(body.name)

    # Make slug unique by appending a number if it already exists
    existing = await db.execute(select(Workspace).where(Workspace.slug == slug))
    if existing.scalar_one_or_none():
        slug = f"{slug}-{current_user.id}"

    workspace = Workspace(
        name=body.name,
        slug=slug,
        description=body.description,
        owner_id=current_user.id,
    )
    db.add(workspace)
    await db.flush()

    # Add creator as owner member
    db.add(WorkspaceMember(
        workspace_id=workspace.id,
        user_id=current_user.id,
        role=MemberRole.owner,
    ))

    # Create a default #general channel
    general = Channel(
        workspace_id=workspace.id,
        name="general",
        description="Company-wide announcements and work-based matters",
        is_private=False,
        created_by=current_user.id,
    )
    db.add(general)
    await db.flush()

    db.add(ChannelMember(channel_id=general.id, user_id=current_user.id))
    await db.refresh(workspace)

    return workspace


@router.get("", response_model=list[WorkspaceResponse])
async def list_my_workspaces(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return all workspaces the current user belongs to."""
    result = await db.execute(
        select(Workspace)
        .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
        .where(WorkspaceMember.user_id == current_user.id)
    )
    return result.scalars().all()


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
async def get_workspace(
    workspace_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Workspace).where(Workspace.id == workspace_id))
    workspace = result.scalar_one_or_none()

    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")

    # Check user is a member
    member = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    if not member.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this workspace")

    return workspace


@router.post("/{workspace_id}/invite")
async def invite_user(
    workspace_id: int,
    username: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite another user to the workspace by their username."""
    # Only admins and owners can invite
    member_row = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == current_user.id,
        )
    )
    member = member_row.scalar_one_or_none()
    if not member or member.role not in (MemberRole.owner, MemberRole.admin):
        raise HTTPException(status_code=403, detail="Only admins can invite members")

    target = await db.execute(select(User).where(User.username == username))
    target_user = target.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Check if already a member
    already = await db.execute(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == target_user.id,
        )
    )
    if already.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User is already a member")

    db.add(WorkspaceMember(workspace_id=workspace_id, user_id=target_user.id))
    return {"message": f"{username} added to workspace"}
