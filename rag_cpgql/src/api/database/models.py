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
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB, UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


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


class User(Base):
    """User account model."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    key_hash = Column(String(255), nullable=False)  # Hashed API key
    prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    scopes = Column(ARRAY(Text), default=[])  # Array of permissions
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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)
    current_scenario = Column(String(50), nullable=True)
    session_metadata = Column("metadata", JSONB, default={})  # Renamed to avoid SQLAlchemy reserved name

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
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), nullable=False)
    scenario_id = Column(String(50), nullable=True)
    turn_metadata = Column("metadata", JSONB, nullable=True)  # Renamed to avoid SQLAlchemy reserved name

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

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    job_type = Column(Enum(JobType), nullable=False)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING, nullable=False)
    progress = Column(Integer, default=0)
    params = Column(JSONB, nullable=True)
    result = Column(JSONB, nullable=True)
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
    user_id = Column(UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    details = Column(JSONB, nullable=True)
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
