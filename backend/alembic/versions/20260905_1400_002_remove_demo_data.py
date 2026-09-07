"""Remove development-only people created by older seed script.

Revision ID: 20260905_1400_002
Revises: 001_initial
"""
from alembic import op

revision = "20260905_1400_002"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Exact identifiers make this safe for real customer records.
    op.execute("DELETE FROM clients WHERE full_name = 'Петров Петр Петрович' AND phone = '+77007654321'")
    op.execute("DELETE FROM instructors WHERE full_name = 'Иванов Иван Иванович' AND phone = '+77001234567'")


def downgrade() -> None:
    pass
