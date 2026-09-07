"""Initial schema

Revision ID: 001_initial
Revises: 
Create Date: 2026-09-04 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Создание enum типов (с проверкой существования)
    op.execute("DO $$ BEGIN CREATE TYPE transmissiontype AS ENUM ('МКПП', 'АКПП'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE bookingstatus AS ENUM ('planned', 'arrival_window', 'in_progress', 'no_show', 'assessment_required', 'completed', 'admin_review_required'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE context AS ENUM ('Учебная площадка', 'Город'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE paymenttype AS ENUM ('наличные', 'пакет', 'сертификат', 'уже оплачено', 'другое'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE paymentstatus AS ENUM ('pending', 'received', 'not_required'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE autonomylevel AS ENUM ('A0 — постоянная помощь', 'A1 — частые подсказки', 'A2 — редкие подсказки', 'A3 — самостоятельно'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    op.execute("DO $$ BEGIN CREATE TYPE interventiontype AS ENUM ('нет', 'словесная подсказка', 'физическое вмешательство'); EXCEPTION WHEN duplicate_object THEN null; END $$;")
    
    # instructors
    op.create_table('instructors',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('telegram_user_id', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('transmission', postgresql.ENUM('МКПП', 'АКПП', name='transmissiontype', create_type=False), nullable=True),
        sa.Column('avatar_url', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('phone'),
        sa.UniqueConstraint('telegram_user_id')
    )
    op.create_index('ix_instructors_phone', 'instructors', ['phone'])
    op.create_index('ix_instructors_telegram_user_id', 'instructors', ['telegram_user_id'])
    
    # clients
    op.create_table('clients',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('phone', sa.String(length=20), nullable=False),
        sa.Column('notes_internal', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_clients_full_name', 'clients', ['full_name'])
    
    # bookings
    op.create_table('bookings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('start_at', sa.Time(), nullable=False),
        sa.Column('end_at', sa.Time(), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('context', postgresql.ENUM('Учебная площадка', 'Город', name='context', create_type=False), nullable=False),
        sa.Column('transmission', postgresql.ENUM('МКПП', 'АКПП', name='transmissiontype', create_type=False), nullable=False),
        sa.Column('vehicle_id', sa.Integer(), nullable=True),
        sa.Column('payment_type', postgresql.ENUM('наличные', 'пакет', 'сертификат', 'уже оплачено', 'другое', name='paymenttype', create_type=False), nullable=False),
        sa.Column('amount_due', sa.Numeric(precision=10, scale=2), nullable=False, server_default='0'),
        sa.Column('payment_status', postgresql.ENUM('pending', 'received', 'not_required', name='paymentstatus', create_type=False), nullable=False, server_default='pending'),
        sa.Column('status', postgresql.ENUM('planned', 'arrival_window', 'in_progress', 'no_show', 'assessment_required', 'completed', 'admin_review_required', name='bookingstatus', create_type=False), nullable=False, server_default='planned'),
        sa.Column('admin_comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['instructors.id'], ondelete='CASCADE')
    )
    op.create_index('ix_bookings_client_id', 'bookings', ['client_id'])
    op.create_index('ix_bookings_instructor_id', 'bookings', ['instructor_id'])
    op.create_index('ix_bookings_date', 'bookings', ['date'])
    op.create_index('ix_bookings_status', 'bookings', ['status'])
    
    # lesson_reports
    op.create_table('lesson_reports',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('context', postgresql.ENUM('Учебная площадка', 'Город', name='context', create_type=False), nullable=False),
        sa.Column('overall_grade_1_5', sa.SmallInteger(), nullable=False),
        sa.Column('autonomy_level', postgresql.ENUM('A0 — постоянная помощь', 'A1 — частые подсказки', 'A2 — редкие подсказки', 'A3 — самостоятельно', name='autonomylevel', create_type=False), nullable=False),
        sa.Column('quick_verdict', sa.String(length=255), nullable=True),
        sa.Column('comment_internal', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('edited_until', sa.DateTime(), nullable=True),
        sa.Column('last_edited_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['instructor_id'], ['instructors.id']),
        sa.UniqueConstraint('booking_id')
    )
    op.create_index('ix_lesson_reports_booking_id', 'lesson_reports', ['booking_id'])
    op.create_index('ix_lesson_reports_instructor_id', 'lesson_reports', ['instructor_id'])
    
    # exercise_catalog
    op.create_table('exercise_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=50), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=False),
        sa.Column('official_name', sa.String(length=500), nullable=False),
        sa.Column('paper_section', sa.String(length=255), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_exercise_catalog_context', 'exercise_catalog', ['context'])
    op.create_index('ix_exercise_catalog_active', 'exercise_catalog', ['active'])
    
    # skill_catalog
    op.create_table('skill_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('weight', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('is_core', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_skill_catalog_context', 'skill_catalog', ['context'])
    op.create_index('ix_skill_catalog_active', 'skill_catalog', ['active'])
    
    # lesson_exercises
    op.create_table('lesson_exercises',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('exercise_id', sa.Integer(), nullable=False),
        sa.Column('official_name_snapshot', sa.String(length=500), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['lesson_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['exercise_id'], ['exercise_catalog.id'])
    )
    op.create_index('ix_lesson_exercises_report_id', 'lesson_exercises', ['report_id'])
    
    # skill_assessments
    op.create_table('skill_assessments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=False),
        sa.Column('value_0_4', sa.SmallInteger(), nullable=False),
        sa.Column('skill_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['lesson_reports.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skill_catalog.id'])
    )
    op.create_index('ix_skill_assessments_report_id', 'skill_assessments', ['report_id'])
    op.create_index('ix_skill_assessments_skill_id', 'skill_assessments', ['skill_id'])
    
    # interventions
    op.create_table('interventions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('report_id', sa.Integer(), nullable=False),
        sa.Column('type', postgresql.ENUM('нет', 'словесная подсказка', 'физическое вмешательство', name='interventiontype', create_type=False), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['report_id'], ['lesson_reports.id'], ondelete='CASCADE')
    )
    op.create_index('ix_interventions_report_id', 'interventions', ['report_id'])
    
    # score_snapshots
    op.create_table('score_snapshots',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('formula_version', sa.Integer(), nullable=False),
        sa.Column('inputs_json', sa.JSON(), nullable=False),
        sa.Column('caps_json', sa.JSON(), nullable=True),
        sa.Column('calculated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE')
    )
    op.create_index('ix_score_snapshots_client_id', 'score_snapshots', ['client_id'])
    op.create_index('ix_score_snapshots_context', 'score_snapshots', ['context'])
    op.create_index('ix_score_snapshots_calculated_at', 'score_snapshots', ['calculated_at'])
    
    # attention_flags
    op.create_table('attention_flags',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=50), nullable=False),
        sa.Column('skill_id', sa.Integer(), nullable=True),
        sa.Column('reason', sa.String(length=500), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('opened_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('closed_at', sa.DateTime(), nullable=True),
        sa.Column('closed_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skill_catalog.id'])
    )
    op.create_index('ix_attention_flags_client_id', 'attention_flags', ['client_id'])
    op.create_index('ix_attention_flags_active', 'attention_flags', ['active'])
    
    # ai_drafts
    op.create_table('ai_drafts',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=False),
        sa.Column('prompt_version', sa.String(length=50), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('generated_text', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE')
    )
    op.create_index('ix_ai_drafts_client_id', 'ai_drafts', ['client_id'])
    
    # final_conclusions
    op.create_table('final_conclusions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=255), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('ai_draft_id', sa.Integer(), nullable=True),
        sa.Column('approved_by_type', sa.String(length=50), nullable=False),
        sa.Column('approved_by_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['ai_draft_id'], ['ai_drafts.id'])
    )
    op.create_index('ix_final_conclusions_client_id', 'final_conclusions', ['client_id'])
    
    # audit_logs
    op.create_table('audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('actor_type', sa.String(length=50), nullable=False),
        sa.Column('actor_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(length=100), nullable=False),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(length=50), nullable=False),
        sa.Column('old_json', sa.JSON(), nullable=True),
        sa.Column('new_json', sa.JSON(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_audit_logs_entity_type', 'audit_logs', ['entity_type'])
    op.create_index('ix_audit_logs_entity_id', 'audit_logs', ['entity_id'])
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'])
    
    # access_grants
    op.create_table('access_grants',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('instructor_id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.Integer(), nullable=False),
        sa.Column('booking_id', sa.Integer(), nullable=True),
        sa.Column('valid_from', sa.DateTime(), nullable=False),
        sa.Column('valid_until', sa.DateTime(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('granted_by_admin_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['instructor_id'], ['instructors.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['booking_id'], ['bookings.id'], ondelete='SET NULL')
    )
    op.create_index('ix_access_grants_instructor_id', 'access_grants', ['instructor_id'])
    op.create_index('ix_access_grants_client_id', 'access_grants', ['client_id'])
    op.create_index('ix_access_grants_valid_until', 'access_grants', ['valid_until'])
    
    # verdict_catalog
    op.create_table('verdict_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_verdict_catalog_active', 'verdict_catalog', ['active'])
    
    # intervention_reason_catalog
    op.create_table('intervention_reason_catalog',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('context', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('criticality', sa.String(length=50), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_intervention_reason_catalog_context', 'intervention_reason_catalog', ['context'])
    op.create_index('ix_intervention_reason_catalog_active', 'intervention_reason_catalog', ['active'])
    
    # score_formula_versions
    op.create_table('score_formula_versions',
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('valid_from', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('ground_weights_json', sa.JSON(), nullable=False),
        sa.Column('city_weights_json', sa.JSON(), nullable=False),
        sa.Column('overall_weights_json', sa.JSON(), nullable=False),
        sa.Column('caps_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('version')
    )


def downgrade() -> None:
    # Удаление таблиц
    op.drop_table('score_formula_versions')
    op.drop_table('intervention_reason_catalog')
    op.drop_table('verdict_catalog')
    op.drop_table('access_grants')
    op.drop_table('audit_logs')
    op.drop_table('final_conclusions')
    op.drop_table('ai_drafts')
    op.drop_table('attention_flags')
    op.drop_table('score_snapshots')
    op.drop_table('interventions')
    op.drop_table('skill_assessments')
    op.drop_table('lesson_exercises')
    op.drop_table('skill_catalog')
    op.drop_table('exercise_catalog')
    op.drop_table('lesson_reports')
    op.drop_table('bookings')
    op.drop_table('clients')
    op.drop_table('instructors')
    
    # Удаление enum типов
    op.execute('DROP TYPE IF EXISTS interventiontype')
    op.execute('DROP TYPE IF EXISTS autonomylevel')
    op.execute('DROP TYPE IF EXISTS paymentstatus')
    op.execute('DROP TYPE IF EXISTS paymenttype')
    op.execute('DROP TYPE IF EXISTS context')
    op.execute('DROP TYPE IF EXISTS bookingstatus')
    op.execute('DROP TYPE IF EXISTS transmissiontype')
