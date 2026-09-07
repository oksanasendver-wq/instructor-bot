"""Store Telegram user IDs without the PostgreSQL 32-bit integer limit."""
from alembic import op
import sqlalchemy as sa

revision = "003_telegram_user_id_bigint"
down_revision = "20260905_1400_002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("instructors", "telegram_user_id", existing_type=sa.Integer(),
                    type_=sa.BigInteger(), existing_nullable=True)


def downgrade() -> None:
    # PostgreSQL rejects this downgrade if any ID would overflow; do not truncate.
    op.alter_column("instructors", "telegram_user_id", existing_type=sa.BigInteger(),
                    type_=sa.Integer(), existing_nullable=True)
