"""Add project groups, projects, and import jobs tables

Revision ID: 003
Revises: 002
Create Date: 2024-12-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create project_groups table
    op.create_table(
        'project_groups',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )
    op.create_index('idx_project_groups_name', 'project_groups', ['name'])

    # Create user_group_access table
    op.create_table(
        'user_group_access',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('group_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(50), nullable=False, server_default='viewer'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['project_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'group_id', name='uq_user_group'),
    )
    op.create_index('idx_user_group_access_user', 'user_group_access', ['user_id'])
    op.create_index('idx_user_group_access_group', 'user_group_access', ['group_id'])

    # Create projects table
    op.create_table(
        'projects',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('group_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('db_path', sa.String(1024), nullable=True),
        sa.Column('cpg_path', sa.String(1024), nullable=True),
        sa.Column('source_path', sa.String(1024), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='{}'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['group_id'], ['project_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'name', name='uq_group_project_name'),
    )
    op.create_index('idx_projects_group', 'projects', ['group_id'])
    op.create_index('idx_projects_name', 'projects', ['name'])
    op.create_index('idx_projects_active', 'projects', ['is_active'])

    # Create import_jobs table
    op.create_table(
        'import_jobs',
        sa.Column('id', sa.UUID(), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('group_id', sa.UUID(), nullable=True),
        sa.Column('project_name', sa.String(255), nullable=False),
        sa.Column('source_url', sa.String(1024), nullable=True),
        sa.Column('language', sa.String(50), nullable=True),
        sa.Column('import_mode', sa.String(50), nullable=False, server_default='full'),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('current_step', sa.String(100), nullable=True),
        sa.Column('progress', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['group_id'], ['project_groups.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_import_jobs_user', 'import_jobs', ['user_id'])
    op.create_index('idx_import_jobs_group', 'import_jobs', ['group_id'])
    op.create_index('idx_import_jobs_status', 'import_jobs', ['status'])


def downgrade() -> None:
    op.drop_table('import_jobs')
    op.drop_table('projects')
    op.drop_table('user_group_access')
    op.drop_table('project_groups')
