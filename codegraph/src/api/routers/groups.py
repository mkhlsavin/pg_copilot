"""
Project Groups Router.

Provides endpoints for managing project groups and user access.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User, GroupRole, UserRole
from src.api.database.repositories.group_repo import ProjectGroupRepository
from src.api.dependencies import get_current_active_user

router = APIRouter()


# Request/Response Models
class GroupCreate(BaseModel):
    """Create group request."""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None


class GroupUpdate(BaseModel):
    """Update group request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None


class GroupResponse(BaseModel):
    """Group response model."""
    id: str
    name: str
    description: Optional[str]
    created_at: str
    updated_at: str
    project_count: int = 0


class GroupListResponse(BaseModel):
    """Group list response model."""
    groups: List[GroupResponse]
    total: int


class UserAccessCreate(BaseModel):
    """Add user access request."""
    user_id: str
    role: str = Field(default="viewer", pattern="^(viewer|editor|admin)$")


class UserAccessResponse(BaseModel):
    """User access response model."""
    id: str
    user_id: str
    username: str
    role: str
    created_at: str


class UserAccessListResponse(BaseModel):
    """User access list response model."""
    users: List[UserAccessResponse]
    total: int


# Helper functions
def _check_admin(user: User) -> None:
    """Check if user is admin."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )


async def _check_group_access(
    repo: ProjectGroupRepository,
    group_id: UUID,
    user: User,
    min_role: GroupRole = GroupRole.VIEWER,
) -> None:
    """Check if user has access to group with minimum role."""
    # Admins have access to everything
    if user.role == UserRole.ADMIN:
        return

    has_access = await repo.has_access(group_id, user.id, min_role)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this group",
        )


# Endpoints
@router.get("", response_model=GroupListResponse)
async def list_groups(
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List project groups accessible by the current user.

    Admin users see all groups, regular users see only their groups.
    """
    repo = ProjectGroupRepository(db)

    if current_user.role == UserRole.ADMIN:
        groups = await repo.list_all(limit=limit, offset=offset)
        total = await repo.count_all()
    else:
        groups = await repo.get_user_groups(current_user.id, limit=limit, offset=offset)
        total = await repo.count_user_groups(current_user.id)

    return GroupListResponse(
        groups=[
            GroupResponse(
                id=str(g.id),
                name=g.name,
                description=g.description,
                created_at=g.created_at.isoformat() if g.created_at else "",
                updated_at=g.updated_at.isoformat() if g.updated_at else "",
                project_count=len(g.projects) if g.projects else 0,
            )
            for g in groups
        ],
        total=total,
    )


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: GroupCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new project group.

    Only admin users can create groups.
    """
    _check_admin(current_user)

    repo = ProjectGroupRepository(db)

    # Check if name already exists
    existing = await repo.get_by_name(request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Group with name '{request.name}' already exists",
        )

    group = await repo.create(
        name=request.name,
        description=request.description,
    )

    await db.commit()

    return GroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        created_at=group.created_at.isoformat() if group.created_at else "",
        updated_at=group.updated_at.isoformat() if group.updated_at else "",
        project_count=0,
    )


@router.get("/{group_id}", response_model=GroupResponse)
async def get_group(
    group_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get project group by ID.
    """
    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id, include_projects=True)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await _check_group_access(repo, group_id, current_user)

    return GroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        created_at=group.created_at.isoformat() if group.created_at else "",
        updated_at=group.updated_at.isoformat() if group.updated_at else "",
        project_count=len(group.projects) if group.projects else 0,
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: UUID,
    request: GroupUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update project group.

    Requires admin access to the group.
    """
    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await _check_group_access(repo, group_id, current_user, GroupRole.ADMIN)

    # Check name uniqueness if changing
    if request.name and request.name != group.name:
        existing = await repo.get_by_name(request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Group with name '{request.name}' already exists",
            )

    updated = await repo.update(
        group_id=group_id,
        name=request.name,
        description=request.description,
    )

    await db.commit()

    return GroupResponse(
        id=str(updated.id),
        name=updated.name,
        description=updated.description,
        created_at=updated.created_at.isoformat() if updated.created_at else "",
        updated_at=updated.updated_at.isoformat() if updated.updated_at else "",
        project_count=0,
    )


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a project group.

    Only admin users can delete groups.
    """
    _check_admin(current_user)

    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await repo.delete(group_id)
    await db.commit()


# User access management
@router.get("/{group_id}/users", response_model=UserAccessListResponse)
async def list_group_users(
    group_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List users with access to a group.
    """
    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await _check_group_access(repo, group_id, current_user)

    access_list = await repo.get_users(group_id)

    return UserAccessListResponse(
        users=[
            UserAccessResponse(
                id=str(a.id),
                user_id=str(a.user_id),
                username=a.user.username if a.user else "Unknown",
                role=a.role.value,
                created_at=a.created_at.isoformat() if a.created_at else "",
            )
            for a in access_list
        ],
        total=len(access_list),
    )


@router.post("/{group_id}/users", response_model=UserAccessResponse, status_code=status.HTTP_201_CREATED)
async def add_group_user(
    group_id: UUID,
    request: UserAccessCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Add user access to a group.

    Requires admin access to the group.
    """
    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await _check_group_access(repo, group_id, current_user, GroupRole.ADMIN)

    user_id = UUID(request.user_id)
    role = GroupRole(request.role)

    # Check if access already exists
    existing = await repo.get_user_access(group_id, user_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User already has access to this group",
        )

    access = await repo.add_user(group_id, user_id, role)
    await db.commit()

    # Refresh to get user relationship
    access = await repo.get_user_access(group_id, user_id)

    return UserAccessResponse(
        id=str(access.id),
        user_id=str(access.user_id),
        username=access.user.username if access.user else "Unknown",
        role=access.role.value,
        created_at=access.created_at.isoformat() if access.created_at else "",
    )


@router.delete("/{group_id}/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_group_user(
    group_id: UUID,
    user_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Remove user access from a group.

    Requires admin access to the group.
    """
    repo = ProjectGroupRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    await _check_group_access(repo, group_id, current_user, GroupRole.ADMIN)

    removed = await repo.remove_user(group_id, user_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User access not found",
        )

    await db.commit()
