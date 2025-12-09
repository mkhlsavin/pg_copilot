"""Initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('username', sa.String(100), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('password_hash', sa.String(255), nullable=True),
        sa.Column('auth_provider', sa.String(50), nullable=False, server_default='local'),
        sa.Column('external_id', sa.String(255), nullable=True),
        sa.Column('role', sa.String(50), nullable=False, server_default='analyst'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username'),
        sa.UniqueConstraint('email'),
    )
    op.create_index('idx_users_auth_provider', 'users', ['auth_provider', 'external_id'])

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(255), nullable=False),
        sa.Column('prefix', sa.String(10), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('is_revoked', sa.Boolean(), nullable=False, server_default='false'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_api_keys_prefix', 'api_keys', ['prefix'])
    op.create_index('idx_api_keys_user', 'api_keys', ['user_id'])

    # Create sessions table
    op.create_table(
        'sessions',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('current_scenario', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_sessions_user', 'sessions', ['user_id'])

    # Create dialogue_turns table
    op.create_table(
        'dialogue_turns',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('session_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('scenario_id', sa.String(50), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_turns_session_timestamp', 'dialogue_turns', ['session_id', 'timestamp'])

    # Create background_jobs table
    op.create_table(
        'background_jobs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_jobs_user_status', 'background_jobs', ['user_id', 'status'])

    # Create token_blacklist table
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('jti', sa.String(255), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jti'),
    )
    op.create_index('idx_blacklist_expires', 'token_blacklist', ['expires_at'])

    # Create audit_log table
    op.create_table(
        'audit_log',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('action', sa.String(100), nullable=False),
        sa.Column('resource', sa.String(255), nullable=True),
        sa.Column('ip_address', postgresql.INET(), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_audit_user', 'audit_log', ['user_id', 'timestamp'])


def downgrade() -> None:
    op.drop_table('audit_log')
    op.drop_table('token_blacklist')
    op.drop_table('background_jobs')
    op.drop_table('dialogue_turns')
    op.drop_table('sessions')
    op.drop_table('api_keys')
    op.drop_table('users')
