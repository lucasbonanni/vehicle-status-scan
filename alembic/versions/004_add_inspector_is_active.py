"""Add is_active column to inspectors table

Revision ID: 004_add_inspector_is_active
Revises: 003_add_inspections
Create Date: 2025-11-11 20:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "004_add_inspector_is_active"
down_revision = "003_add_inspections"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add is_active column to inspectors table
    op.add_column(
        "inspectors",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
    )


def downgrade() -> None:
    # Remove is_active column
    op.drop_column("inspectors", "is_active")
