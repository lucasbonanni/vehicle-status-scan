"""Change booking status from ENUM to VARCHAR

Revision ID: 005_change_booking_status_to_string
Revises: 004_add_inspector_is_active
Create Date: 2025-11-12 21:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "005_change_booking_status_to_string"
down_revision = "004_add_inspector_is_active"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Change booking status column from ENUM to VARCHAR."""
    # First, alter the column type
    op.alter_column(
        "bookings",
        "status",
        existing_type=sa.Enum(
            "PENDING", "CONFIRMED", "COMPLETED", "CANCELLED", name="bookingstatus"
        ),
        type_=sa.String(50),
        existing_nullable=False,
    )

    # Drop the old enum type if it exists
    op.execute("DROP TYPE IF EXISTS bookingstatus CASCADE")


def downgrade() -> None:
    """Revert booking status column back to ENUM."""
    # Create the enum type again
    op.execute(
        "CREATE TYPE bookingstatus AS ENUM ('PENDING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')"
    )

    # Alter the column back to ENUM
    op.alter_column(
        "bookings",
        "status",
        existing_type=sa.String(50),
        type_=sa.Enum(
            "PENDING", "CONFIRMED", "COMPLETED", "CANCELLED", name="bookingstatus"
        ),
        existing_nullable=False,
    )
