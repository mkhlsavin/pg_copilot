"""Initial leads schema

Revision ID: 001
Revises:
Create Date: 2024-12-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create leads table
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("company", sa.String(200), nullable=False),
        sa.Column("position", sa.String(100), nullable=True),
        sa.Column("team_size", sa.String(20), nullable=True),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="new"),
        sa.Column("source", sa.String(50), nullable=False, server_default="landing"),
        sa.Column("ip_address", postgresql.INET, nullable=True),
        sa.Column("user_agent", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index("idx_leads_email", "leads", ["email"])
    op.create_index("idx_leads_company", "leads", ["company"])
    op.create_index("idx_leads_status", "leads", ["status"])
    op.create_index("idx_leads_created", "leads", ["created_at"])


def downgrade() -> None:
    # Drop indexes
    op.drop_index("idx_leads_created", table_name="leads")
    op.drop_index("idx_leads_status", table_name="leads")
    op.drop_index("idx_leads_company", table_name="leads")
    op.drop_index("idx_leads_email", table_name="leads")

    # Drop table
    op.drop_table("leads")
