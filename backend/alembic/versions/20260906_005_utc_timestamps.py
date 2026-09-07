"""Store all event timestamps with an explicit UTC timezone."""

from alembic import op
import sqlalchemy as sa

revision = "005_utc_timestamps"
down_revision = "004_attendance"
branch_labels = None
depends_on = None
COLUMNS = {
    "instructors": ["created_at", "updated_at"],
    "clients": ["created_at", "updated_at"],
    "bookings": ["created_at", "updated_at", "arrived_at", "finished_at"],
    "lesson_reports": ["created_at", "edited_until", "last_edited_at"],
    "skill_assessments": ["created_at"],
    "interventions": ["created_at"],
    "score_snapshots": ["calculated_at"],
    "attention_flags": ["opened_at", "closed_at"],
    "final_conclusions": ["created_at"],
    "ai_drafts": ["created_at"],
    "audit_logs": ["created_at"],
    "access_grants": ["valid_from", "valid_until", "created_at"],
    "exercise_catalog": ["created_at", "updated_at"],
    "skill_catalog": ["created_at", "updated_at"],
    "intervention_reason_catalog": ["created_at"],
    "verdict_catalog": ["created_at"],
    "score_formula_versions": ["valid_from", "created_at"],
}


def upgrade():
    for table, columns in COLUMNS.items():
        for column in columns:
            op.alter_column(
                table,
                column,
                type_=sa.DateTime(timezone=True),
                existing_type=sa.DateTime(),
                postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )


def downgrade():
    for table, columns in COLUMNS.items():
        for column in columns:
            op.alter_column(
                table,
                column,
                type_=sa.DateTime(),
                existing_type=sa.DateTime(timezone=True),
                postgresql_using=f"{column} AT TIME ZONE 'UTC'",
            )
