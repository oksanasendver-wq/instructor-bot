"""Attendance timestamps and client archive preserve the training history."""

from alembic import op
import sqlalchemy as sa

revision = "004_attendance"
down_revision = "003_telegram_user_id_bigint"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("bookings", sa.Column("arrived_at", sa.DateTime(), nullable=True))
    op.add_column("bookings", sa.Column("finished_at", sa.DateTime(), nullable=True))
    op.add_column(
        "clients",
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade():
    op.drop_column("clients", "is_archived")
    op.drop_column("bookings", "finished_at")
    op.drop_column("bookings", "arrived_at")
