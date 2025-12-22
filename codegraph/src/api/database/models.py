"""
SQLAlchemy Database Models.

Defines all database tables for the API including users, sessions, jobs, and audit logs.
"""

import uuid
from datetime import datetime
from enum import Enum as PyEnum
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy import TypeDecorator
from sqlalchemy.ext.declarative import declarative_base


from sqlalchemy.orm import relationship

Base = declarative_base()


class PortableIPAddress(TypeDecorator):
    """A portable IP address type that works with SQLite and PostgreSQL."""

    impl = String(45)  # IPv6 max length
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(INET())
        return dialect.type_descriptor(String(45))


class PortableJSON(TypeDecorator):
    """A portable JSON type that works with SQLite and PostgreSQL."""

    impl = Text
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(JSONB())
        from sqlalchemy import JSON
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        import json
        if value is not None and dialect.name == 'sqlite':
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        import json
        if value is not None and dialect.name == 'sqlite' and isinstance(value, str):
            return json.loads(value)
        return value


class PortableArray(TypeDecorator):
    """A portable ARRAY type that works with SQLite (as JSON) and PostgreSQL (as native ARRAY)."""

    impl = Text
    cache_ok = True

    def __init__(self, item_type=None):
        super().__init__()
        self.item_type = item_type or Text

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(ARRAY(self.item_type))
        from sqlalchemy import JSON
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        import json
        if value is not None and dialect.name == 'sqlite':
            return json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        import json
        if value is not None and dialect.name == 'sqlite' and isinstance(value, str):
            return json.loads(value)
        return value


class PortableUUID(TypeDecorator):
    """A portable UUID type that works with SQLite (as String) and PostgreSQL (as native UUID)."""

    impl = String(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            # Use the PostgreSQL native UUID type
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID
            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(String(36))

    def process_bind_param(self, value, dialect):
        if value is not None:
            if dialect.name == 'sqlite':
                return str(value) if isinstance(value, uuid.UUID) else value
            return value if isinstance(value, uuid.UUID) else uuid.UUID(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            if isinstance(value, uuid.UUID):
                return value
            return uuid.UUID(value)
        return value


class AuthProvider(str, PyEnum):
    """Authentication provider types."""

    LOCAL = "local"
    OAUTH_GITHUB = "oauth_github"
    OAUTH_GOOGLE = "oauth_google"
    OAUTH_GITLAB = "oauth_gitlab"
    OAUTH_KEYCLOAK = "oauth_keycloak"
    LDAP = "ldap"


class UserRole(str, PyEnum):
    """User role types for RBAC."""

    VIEWER = "viewer"
    ANALYST = "analyst"
    REVIEWER = "reviewer"
    ADMIN = "admin"


class JobStatus(str, PyEnum):
    """Background job status types."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobType(str, PyEnum):
    """Background job types."""

    REVIEW = "review"
    BENCHMARK = "benchmark"
    QUERY = "query"
    EXPORT = "export"


class GroupRole(str, PyEnum):
    """User role within a project group."""

    VIEWER = "viewer"
    EDITOR = "editor"
    ADMIN = "admin"


class ImportStatus(str, PyEnum):
    """Import job status types."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ImportMode(str, PyEnum):
    """Import mode types."""

    FULL = "full"
    SELECTIVE = "selective"
    INCREMENTAL = "incremental"


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  # NULL for OAuth/LDAP users
    auth_provider = Column(
        Enum(AuthProvider),
        default=AuthProvider.LOCAL,
        nullable=False,
    )
    external_id = Column(String(255), nullable=True)  # OAuth/LDAP user ID
    role = Column(Enum(UserRole), default=UserRole.ANALYST, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    jobs = relationship("BackgroundJob", back_populates="user", cascade="all, delete-orphan")
    group_access = relationship("UserGroupAccess", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username={self.username}, role={self.role})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding sensitive data)."""
        return {
            "id": str(self.id),
            "username": self.username,
            "email": self.email,
            "auth_provider": self.auth_provider.value,
            "role": self.role.value,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ApiKey(Base):
    """API key model for programmatic access."""

    __tablename__ = "api_keys"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(PortableUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    scopes = Column(PortableArray(Text), default=[])  # Array of permissions
    expires_at = Column(DateTime, nullable=True)
    last_used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    is_revoked = Column(Boolean, default=False, nullable=False)

    # Relationships
    user = relationship("User", back_populates="api_keys")

    __table_args__ = (
        Index("idx_api_keys_prefix", "prefix"),
        Index("idx_api_keys_user", "user_id"),
    )

    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, name={self.name}, prefix={self.prefix})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding key_hash)."""
        return {
            "id": str(self.id),
            "name": self.name,
            "prefix": self.prefix,
            "scopes": self.scopes,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "is_revoked": self.is_revoked,
        }


class Session(Base):
    """Chat session model."""

    __tablename__ = "sessions"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(PortableUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    current_scenario = Column(String(50), nullable=True)
    session_metadata = Column("metadata", PortableJSON(), default={})  # Renamed to avoid SQLAlchemy reserved name

    # Relationships
    user = relationship("User", back_populates="sessions")
    dialogue_turns = relationship(
        "DialogueTurn",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="DialogueTurn.timestamp",
    )

    __table_args__ = (
        Index("idx_sessions_user", "user_id"),
        Index("idx_sessions_updated", "updated_at"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, user_id={self.user_id}, scenario={self.current_scenario})>"

    def to_dict(self, include_turns: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "current_scenario": self.current_scenario,
            "metadata": self.session_metadata,
        }
        if include_turns:
            data["dialogue_turns"] = [turn.to_dict() for turn in self.dialogue_turns]
        return data


class DialogueTurn(Base):
    """Dialogue turn model for chat history."""

    __tablename__ = "dialogue_turns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(PortableUUID(), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    scenario_id = Column(String(50), nullable=True)
    turn_metadata = Column("metadata", PortableJSON(), nullable=True)  # Renamed to avoid SQLAlchemy reserved name

    # Relationships
    session = relationship("Session", back_populates="dialogue_turns")

    __table_args__ = (
        Index("idx_turns_session_timestamp", "session_id", "timestamp"),
    )

    def __repr__(self) -> str:
        return f"<DialogueTurn(id={self.id}, role={self.role}, session_id={self.session_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "session_id": str(self.session_id),
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "scenario_id": self.scenario_id,
            "metadata": self.turn_metadata,
        }


class BackgroundJob(Base):
    """Background job model for async operations."""

    __tablename__ = "background_jobs"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(PortableUUID(), ForeignKey("users.id"), nullable=True)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0)
    params = Column(PortableJSON(), nullable=True)
    result = Column(PortableJSON(), nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="jobs")

    __table_args__ = (
        Index("idx_jobs_user_status", "user_id", "status"),
        Index("idx_jobs_created", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<BackgroundJob(id={self.id}, type={self.job_type}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "job_type": self.job_type.value,
            "status": self.status.value,
            "progress": self.progress,
            "params": self.params,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class TokenBlacklist(Base):
    """Blacklisted JWT tokens for revocation."""

    __tablename__ = "token_blacklist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    jti = Column(String(255), unique=True, nullable=False)  # JWT ID
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_blacklist_jti", "jti"),
        Index("idx_blacklist_expires", "expires_at"),
    )

    def __repr__(self) -> str:
        return f"<TokenBlacklist(id={self.id}, jti={self.jti})>"


class AuditLog(Base):
    """Security audit log model."""

    __tablename__ = "audit_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(PortableUUID(), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    ip_address = Column(PortableIPAddress(), nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(PortableJSON(), nullable=True)
    timestamp = Column(DateTime, default=func.now(), nullable=False)

    __table_args__ = (
        Index("idx_audit_user_timestamp", "user_id", "timestamp"),
        Index("idx_audit_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, action={self.action}, user_id={self.user_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "user_id": str(self.user_id) if self.user_id else None,
            "action": self.action,
            "resource": self.resource,
            "ip_address": str(self.ip_address) if self.ip_address else None,
            "user_agent": self.user_agent,
            "details": self.details,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


# =============================================================================
# Project Groups and Projects Models
# =============================================================================


class ProjectGroup(Base):
    """Project group model for organizing projects."""

    __tablename__ = "project_groups"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    projects = relationship("Project", back_populates="group", cascade="all, delete-orphan")
    user_access = relationship("UserGroupAccess", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ProjectGroup(id={self.id}, name={self.name})>"

    def to_dict(self, include_projects: bool = False) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_projects:
            data["projects"] = [p.to_dict() for p in self.projects]
        return data


class UserGroupAccess(Base):
    """User access to project group model."""

    __tablename__ = "user_group_access"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(PortableUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(PortableUUID(), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(GroupRole), default=GroupRole.VIEWER, nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)

    # Relationships
    user = relationship("User", back_populates="group_access")
    group = relationship("ProjectGroup", back_populates="user_access")

    __table_args__ = (
        UniqueConstraint("user_id", "group_id", name="uq_user_group"),
        Index("idx_user_group_access_user", "user_id"),
        Index("idx_user_group_access_group", "group_id"),
    )

    def __repr__(self) -> str:
        return f"<UserGroupAccess(user_id={self.user_id}, group_id={self.group_id}, role={self.role})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "group_id": str(self.group_id),
            "role": self.role.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Project(Base):
    """Project model for code analysis projects."""

    __tablename__ = "projects"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    group_id = Column(PortableUUID(), ForeignKey("project_groups.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False, index=True)
    db_path = Column(String(1024), nullable=True)  # Path to DuckDB file
    cpg_path = Column(String(1024), nullable=True)  # Path to CPG file
    source_path = Column(String(1024), nullable=True)  # Path to source code
    language = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)  # Active project in group
    project_metadata = Column("metadata", PortableJSON(), default={})
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

    # Relationships
    group = relationship("ProjectGroup", back_populates="projects")

    __table_args__ = (
        UniqueConstraint("group_id", "name", name="uq_group_project_name"),
        Index("idx_projects_group", "group_id"),
        Index("idx_projects_active", "is_active"),
    )

    def __repr__(self) -> str:
        return f"<Project(id={self.id}, name={self.name}, group_id={self.group_id})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "group_id": str(self.group_id),
            "name": self.name,
            "db_path": self.db_path,
            "cpg_path": self.cpg_path,
            "source_path": self.source_path,
            "language": self.language,
            "description": self.description,
            "is_active": self.is_active,
            "metadata": self.project_metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ImportJob(Base):
    """Import job model for project import tracking."""

    __tablename__ = "import_jobs"

    id = Column(PortableUUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(PortableUUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    group_id = Column(PortableUUID(), ForeignKey("project_groups.id", ondelete="SET NULL"), nullable=True)
    project_name = Column(String(255), nullable=False)
    source_url = Column(String(1024), nullable=True)
    language = Column(String(50), nullable=True)
    import_mode = Column(Enum(ImportMode), default=ImportMode.FULL, nullable=False)
    status = Column(Enum(ImportStatus), default=ImportStatus.PENDING, nullable=False)
    current_step = Column(String(100), nullable=True)
    progress = Column(Integer, default=0, nullable=False)
    steps = Column(PortableJSON(), default=[])  # List of step statuses
    error_message = Column(Text, nullable=True)
    result = Column(PortableJSON(), nullable=True)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_import_jobs_user", "user_id"),
        Index("idx_import_jobs_group", "group_id"),
        Index("idx_import_jobs_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ImportJob(id={self.id}, project={self.project_name}, status={self.status})>"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "group_id": str(self.group_id) if self.group_id else None,
            "project_name": self.project_name,
            "source_url": self.source_url,
            "language": self.language,
            "import_mode": self.import_mode.value,
            "status": self.status.value,
            "current_step": self.current_step,
            "progress": self.progress,
            "steps": self.steps,
            "error_message": self.error_message,
            "result": self.result,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
