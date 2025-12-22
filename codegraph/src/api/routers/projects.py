"""
Projects Router.

Provides endpoints for managing projects within groups.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.database.connection import get_db
from src.api.database.models import User, GroupRole, UserRole
from src.api.database.repositories.group_repo import ProjectGroupRepository
from src.api.database.repositories.project_repo import ProjectRepository
from src.api.dependencies import get_current_active_user

router = APIRouter()


# Request/Response Models
class ProjectCreate(BaseModel):
    """Create project request."""
    group_id: str
    name: str = Field(..., min_length=1, max_length=255)
    db_path: Optional[str] = None
    cpg_path: Optional[str] = None
    source_path: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectUpdate(BaseModel):
    """Update project request."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    db_path: Optional[str] = None
    cpg_path: Optional[str] = None
    source_path: Optional[str] = None
    language: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ProjectResponse(BaseModel):
    """Project response model."""
    id: str
    group_id: str
    name: str
    db_path: Optional[str]
    cpg_path: Optional[str]
    source_path: Optional[str]
    language: Optional[str]
    description: Optional[str]
    is_active: bool
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class ProjectListResponse(BaseModel):
    """Project list response model."""
    projects: List[ProjectResponse]
    total: int


# Helper functions
async def _check_group_access(
    group_repo: ProjectGroupRepository,
    group_id: UUID,
    user: User,
    min_role: GroupRole = GroupRole.VIEWER,
) -> None:
    """Check if user has access to group with minimum role."""
    if user.role == UserRole.ADMIN:
        return

    has_access = await group_repo.has_access(group_id, user.id, min_role)
    if not has_access:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this group",
        )


async def _check_project_access(
    project_repo: ProjectRepository,
    group_repo: ProjectGroupRepository,
    project_id: UUID,
    user: User,
    min_role: GroupRole = GroupRole.VIEWER,
) -> None:
    """Check if user has access to project via its group."""
    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_group_access(group_repo, project.group_id, user, min_role)


# Endpoints
@router.get("", response_model=ProjectListResponse)
async def list_projects(
    group_id: Optional[UUID] = None,
    limit: int = 100,
    offset: int = 0,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    List projects accessible by the current user.

    If group_id is specified, list projects in that group only.
    Otherwise, list all projects from accessible groups.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    if group_id:
        # Check group access
        await _check_group_access(group_repo, group_id, current_user)
        projects = await project_repo.get_by_group(group_id, limit=limit, offset=offset)
        total = await project_repo.count_by_group(group_id)
    else:
        # Get all accessible projects
        projects = await project_repo.get_user_projects(current_user.id, limit=limit, offset=offset)
        total = await project_repo.count_user_projects(current_user.id)

    return ProjectListResponse(
        projects=[
            ProjectResponse(
                id=str(p.id),
                group_id=str(p.group_id),
                name=p.name,
                db_path=p.db_path,
                cpg_path=p.cpg_path,
                source_path=p.source_path,
                language=p.language,
                description=p.description,
                is_active=p.is_active,
                metadata=p.project_metadata or {},
                created_at=p.created_at.isoformat() if p.created_at else "",
                updated_at=p.updated_at.isoformat() if p.updated_at else "",
            )
            for p in projects
        ],
        total=total,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    request: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new project in a group.

    Requires editor or admin access to the group.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    group_id = UUID(request.group_id)

    # Check group exists
    group = await group_repo.get_by_id(group_id)
    if not group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )

    # Check access
    await _check_group_access(group_repo, group_id, current_user, GroupRole.EDITOR)

    # Check name uniqueness within group
    existing = await project_repo.get_by_name(group_id, request.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with name '{request.name}' already exists in this group",
        )

    project = await project_repo.create(
        group_id=group_id,
        name=request.name,
        db_path=request.db_path,
        cpg_path=request.cpg_path,
        source_path=request.source_path,
        language=request.language,
        description=request.description,
        metadata=request.metadata,
    )

    await db.commit()

    return ProjectResponse(
        id=str(project.id),
        group_id=str(project.group_id),
        name=project.name,
        db_path=project.db_path,
        cpg_path=project.cpg_path,
        source_path=project.source_path,
        language=project.language,
        description=project.description,
        is_active=project.is_active,
        metadata=project.project_metadata or {},
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get project by ID.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_group_access(group_repo, project.group_id, current_user)

    return ProjectResponse(
        id=str(project.id),
        group_id=str(project.group_id),
        name=project.name,
        db_path=project.db_path,
        cpg_path=project.cpg_path,
        source_path=project.source_path,
        language=project.language,
        description=project.description,
        is_active=project.is_active,
        metadata=project.project_metadata or {},
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: UUID,
    request: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Update a project.

    Requires editor or admin access to the group.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_group_access(group_repo, project.group_id, current_user, GroupRole.EDITOR)

    # Check name uniqueness if changing
    if request.name and request.name != project.name:
        existing = await project_repo.get_by_name(project.group_id, request.name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Project with name '{request.name}' already exists in this group",
            )

    updated = await project_repo.update(
        project_id=project_id,
        name=request.name,
        db_path=request.db_path,
        cpg_path=request.cpg_path,
        source_path=request.source_path,
        language=request.language,
        description=request.description,
        metadata=request.metadata,
    )

    await db.commit()

    return ProjectResponse(
        id=str(updated.id),
        group_id=str(updated.group_id),
        name=updated.name,
        db_path=updated.db_path,
        cpg_path=updated.cpg_path,
        source_path=updated.source_path,
        language=updated.language,
        description=updated.description,
        is_active=updated.is_active,
        metadata=updated.project_metadata or {},
        created_at=updated.created_at.isoformat() if updated.created_at else "",
        updated_at=updated.updated_at.isoformat() if updated.updated_at else "",
    )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a project.

    Requires admin access to the group.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_group_access(group_repo, project.group_id, current_user, GroupRole.ADMIN)

    await project_repo.delete(project_id)
    await db.commit()


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(
    project_id: UUID,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Set a project as active in its group.

    This deactivates other projects in the same group.
    """
    project_repo = ProjectRepository(db)
    group_repo = ProjectGroupRepository(db)

    project = await project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await _check_group_access(group_repo, project.group_id, current_user, GroupRole.EDITOR)

    updated = await project_repo.set_active(project_id)
    await db.commit()

    return ProjectResponse(
        id=str(updated.id),
        group_id=str(updated.group_id),
        name=updated.name,
        db_path=updated.db_path,
        cpg_path=updated.cpg_path,
        source_path=updated.source_path,
        language=updated.language,
        description=updated.description,
        is_active=updated.is_active,
        metadata=updated.project_metadata or {},
        created_at=updated.created_at.isoformat() if updated.created_at else "",
        updated_at=updated.updated_at.isoformat() if updated.updated_at else "",
    )


@router.get("/active/current", response_model=Optional[ProjectResponse])
async def get_active_project(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Get the active project for the current user.

    Returns the first active project found across all accessible groups.
    """
    project_repo = ProjectRepository(db)

    project = await project_repo.get_active_user_project(current_user.id)
    if not project:
        return None

    return ProjectResponse(
        id=str(project.id),
        group_id=str(project.group_id),
        name=project.name,
        db_path=project.db_path,
        cpg_path=project.cpg_path,
        source_path=project.source_path,
        language=project.language,
        description=project.description,
        is_active=project.is_active,
        metadata=project.project_metadata or {},
        created_at=project.created_at.isoformat() if project.created_at else "",
        updated_at=project.updated_at.isoformat() if project.updated_at else "",
    )
