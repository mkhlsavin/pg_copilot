"""LLM Audit Log

Revision ID: 002
Revises: 001
Create Date: 2024-12-09 00:00:00.000000

Creates tables for LLM security audit logging:
- llm_audit_log: Complete LLM request/response audit trail
- dlp_events: DLP match/block events

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ==========================================================================
    # LLM Audit Log Table
    # ==========================================================================
    # Stores complete audit trail of all LLM interactions
    op.create_table(
        'llm_audit_log',
        # Primary key
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Request identification
        sa.Column('request_id', sa.UUID(), nullable=False,
                  comment='Unique request identifier'),
        sa.Column('user_id', sa.UUID(), nullable=True,
                  comment='User who made the request'),
        sa.Column('session_id', sa.UUID(), nullable=True,
                  comment='Session identifier'),
        sa.Column('ip_address', postgresql.INET(), nullable=True,
                  comment='Client IP address'),

        # Provider info
        sa.Column('provider', sa.String(50), nullable=False,
                  comment='LLM provider name (GigaChat, OpenAI, etc.)'),
        sa.Column('model', sa.String(100), nullable=False,
                  comment='Model name'),

        # Request data (redacted)
        sa.Column('system_prompt_hash', sa.String(64), nullable=True,
                  comment='SHA256 hash of system prompt'),
        sa.Column('system_prompt_length', sa.Integer(), nullable=True,
                  comment='Length of system prompt'),
        sa.Column('user_prompt_preview', sa.Text(), nullable=True,
                  comment='Truncated/redacted user prompt preview'),
        sa.Column('user_prompt_length', sa.Integer(), nullable=True,
                  comment='Length of user prompt'),

        # Response data
        sa.Column('response_preview', sa.Text(), nullable=True,
                  comment='Truncated response preview'),
        sa.Column('response_length', sa.Integer(), nullable=True,
                  comment='Length of response'),
        sa.Column('status', sa.String(20), nullable=False, server_default='success',
                  comment='Request status: success, error, blocked'),

        # Token usage
        sa.Column('prompt_tokens', sa.Integer(), nullable=True,
                  comment='Tokens used in prompt'),
        sa.Column('completion_tokens', sa.Integer(), nullable=True,
                  comment='Tokens used in completion'),
        sa.Column('total_tokens', sa.Integer(), nullable=True,
                  comment='Total tokens used'),

        # Performance
        sa.Column('latency_ms', sa.Float(), nullable=True,
                  comment='Request latency in milliseconds'),

        # DLP info
        sa.Column('dlp_action', sa.String(20), nullable=True,
                  comment='DLP action taken: BLOCK, MASK, WARN, LOG_ONLY'),
        sa.Column('dlp_match_count', sa.Integer(), nullable=True,
                  comment='Number of DLP matches'),
        sa.Column('dlp_categories', postgresql.ARRAY(sa.String()), nullable=True,
                  comment='DLP categories matched'),

        # Error info
        sa.Column('error_type', sa.String(100), nullable=True,
                  comment='Error type if request failed'),
        sa.Column('error_message', sa.Text(), nullable=True,
                  comment='Error message if request failed'),

        # Timestamps
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()'),
                  comment='When the request was made'),

        # Additional metadata
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  server_default='{}',
                  comment='Additional request metadata'),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for common query patterns
    op.create_index('idx_llm_audit_request_id', 'llm_audit_log', ['request_id'])
    op.create_index('idx_llm_audit_user_time', 'llm_audit_log', ['user_id', 'timestamp'])
    op.create_index('idx_llm_audit_provider_time', 'llm_audit_log', ['provider', 'timestamp'])
    op.create_index('idx_llm_audit_dlp_action', 'llm_audit_log', ['dlp_action', 'timestamp'],
                    postgresql_where=sa.text("dlp_action IS NOT NULL"))
    op.create_index('idx_llm_audit_status', 'llm_audit_log', ['status', 'timestamp'])

    # Partial index for errors only
    op.create_index('idx_llm_audit_errors', 'llm_audit_log', ['timestamp', 'error_type'],
                    postgresql_where=sa.text("status = 'error'"))

    # ==========================================================================
    # DLP Events Table
    # ==========================================================================
    # Stores detailed DLP match events for analysis
    op.create_table(
        'dlp_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Reference to audit log
        sa.Column('audit_log_id', sa.BigInteger(), nullable=True,
                  comment='Reference to llm_audit_log entry'),
        sa.Column('request_id', sa.UUID(), nullable=False,
                  comment='Request identifier'),

        # Event details
        sa.Column('event_type', sa.String(50), nullable=False,
                  comment='DLP event type: request_scan, response_scan'),
        sa.Column('action', sa.String(20), nullable=False,
                  comment='Action taken: BLOCK, MASK, WARN, LOG_ONLY'),

        # Match details
        sa.Column('category', sa.String(50), nullable=False,
                  comment='DLP category: credentials, pii, source_code'),
        sa.Column('pattern_name', sa.String(100), nullable=False,
                  comment='Name of matched pattern'),
        sa.Column('severity', sa.String(20), nullable=False,
                  comment='Match severity: critical, high, medium, low'),

        # Context (redacted)
        sa.Column('match_preview', sa.String(200), nullable=True,
                  comment='Redacted preview of match context'),
        sa.Column('position', sa.Integer(), nullable=True,
                  comment='Position in content where match was found'),

        # User context
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),

        # Timestamps
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        # Constraints
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['audit_log_id'], ['llm_audit_log.id'],
                                ondelete='SET NULL'),
    )

    # Indexes for DLP analysis
    op.create_index('idx_dlp_events_request', 'dlp_events', ['request_id'])
    op.create_index('idx_dlp_events_category', 'dlp_events', ['category', 'timestamp'])
    op.create_index('idx_dlp_events_action', 'dlp_events', ['action', 'timestamp'])
    op.create_index('idx_dlp_events_severity', 'dlp_events', ['severity', 'timestamp'])
    op.create_index('idx_dlp_events_user', 'dlp_events', ['user_id', 'timestamp'],
                    postgresql_where=sa.text("user_id IS NOT NULL"))

    # ==========================================================================
    # Security Events Table (for SIEM integration)
    # ==========================================================================
    # Stores security events that were dispatched to SIEM
    op.create_table(
        'security_events',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),

        # Event identification
        sa.Column('event_id', sa.UUID(), nullable=False,
                  comment='Unique event identifier'),
        sa.Column('event_type', sa.String(50), nullable=False,
                  comment='Security event type'),

        # Severity (syslog severity)
        sa.Column('severity', sa.SmallInteger(), nullable=False,
                  comment='Syslog severity (0-7)'),

        # Context
        sa.Column('request_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('session_id', sa.UUID(), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),

        # Event message
        sa.Column('message', sa.Text(), nullable=False,
                  comment='Human-readable event message'),

        # Structured data
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True,
                  comment='Additional event details'),

        # SIEM dispatch status
        sa.Column('dispatched', sa.Boolean(), nullable=False, server_default='false',
                  comment='Whether event was sent to SIEM'),
        sa.Column('dispatch_error', sa.Text(), nullable=True,
                  comment='Error if dispatch failed'),

        # Timestamps
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),

        sa.PrimaryKeyConstraint('id'),
    )

    op.create_index('idx_security_events_type_time', 'security_events',
                    ['event_type', 'timestamp'])
    op.create_index('idx_security_events_severity', 'security_events',
                    ['severity', 'timestamp'])
    op.create_index('idx_security_events_user', 'security_events',
                    ['user_id', 'timestamp'],
                    postgresql_where=sa.text("user_id IS NOT NULL"))
    op.create_index('idx_security_events_not_dispatched', 'security_events',
                    ['timestamp'],
                    postgresql_where=sa.text("dispatched = false"))


def downgrade() -> None:
    op.drop_table('security_events')
    op.drop_table('dlp_events')
    op.drop_table('llm_audit_log')
