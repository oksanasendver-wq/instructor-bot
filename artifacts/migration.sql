BEGIN;

CREATE TABLE alembic_version (
    version_num VARCHAR(32) NOT NULL, 
    CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
);

-- Running upgrade  -> 001_initial

DO $$ BEGIN CREATE TYPE transmissiontype AS ENUM ('МКПП', 'АКПП'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE bookingstatus AS ENUM ('planned', 'arrival_window', 'in_progress', 'no_show', 'assessment_required', 'completed', 'admin_review_required'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE context AS ENUM ('Учебная площадка', 'Город'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE paymenttype AS ENUM ('наличные', 'пакет', 'сертификат', 'уже оплачено', 'другое'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE paymentstatus AS ENUM ('pending', 'received', 'not_required'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE autonomylevel AS ENUM ('A0 — постоянная помощь', 'A1 — частые подсказки', 'A2 — редкие подсказки', 'A3 — самостоятельно'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

DO $$ BEGIN CREATE TYPE interventiontype AS ENUM ('нет', 'словесная подсказка', 'физическое вмешательство'); EXCEPTION WHEN duplicate_object THEN null; END $$;;

CREATE TABLE instructors (
    id SERIAL NOT NULL, 
    full_name VARCHAR(255) NOT NULL, 
    phone VARCHAR(20) NOT NULL, 
    telegram_user_id INTEGER, 
    is_active BOOLEAN DEFAULT 'true' NOT NULL, 
    transmission transmissiontype, 
    avatar_url VARCHAR(500), 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (phone), 
    UNIQUE (telegram_user_id)
);

CREATE INDEX ix_instructors_phone ON instructors (phone);

CREATE INDEX ix_instructors_telegram_user_id ON instructors (telegram_user_id);

CREATE TABLE clients (
    id SERIAL NOT NULL, 
    full_name VARCHAR(255) NOT NULL, 
    phone VARCHAR(20) NOT NULL, 
    notes_internal TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_clients_full_name ON clients (full_name);

CREATE TABLE bookings (
    id SERIAL NOT NULL, 
    client_id INTEGER NOT NULL, 
    instructor_id INTEGER NOT NULL, 
    date DATE NOT NULL, 
    start_at TIME WITHOUT TIME ZONE NOT NULL, 
    end_at TIME WITHOUT TIME ZONE NOT NULL, 
    duration_minutes INTEGER DEFAULT '60' NOT NULL, 
    context context NOT NULL, 
    transmission transmissiontype NOT NULL, 
    vehicle_id INTEGER, 
    payment_type paymenttype NOT NULL, 
    amount_due NUMERIC(10, 2) DEFAULT '0' NOT NULL, 
    payment_status paymentstatus DEFAULT 'pending' NOT NULL, 
    status bookingstatus DEFAULT 'planned' NOT NULL, 
    admin_comment TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE, 
    FOREIGN KEY(instructor_id) REFERENCES instructors (id) ON DELETE CASCADE
);

CREATE INDEX ix_bookings_client_id ON bookings (client_id);

CREATE INDEX ix_bookings_instructor_id ON bookings (instructor_id);

CREATE INDEX ix_bookings_date ON bookings (date);

CREATE INDEX ix_bookings_status ON bookings (status);

CREATE TABLE lesson_reports (
    id SERIAL NOT NULL, 
    booking_id INTEGER NOT NULL, 
    instructor_id INTEGER NOT NULL, 
    context context NOT NULL, 
    overall_grade_1_5 SMALLINT NOT NULL, 
    autonomy_level autonomylevel NOT NULL, 
    quick_verdict VARCHAR(255), 
    comment_internal TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    edited_until TIMESTAMP WITHOUT TIME ZONE, 
    last_edited_at TIMESTAMP WITHOUT TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE CASCADE, 
    FOREIGN KEY(instructor_id) REFERENCES instructors (id), 
    UNIQUE (booking_id)
);

CREATE INDEX ix_lesson_reports_booking_id ON lesson_reports (booking_id);

CREATE INDEX ix_lesson_reports_instructor_id ON lesson_reports (instructor_id);

CREATE TABLE exercise_catalog (
    id SERIAL NOT NULL, 
    context VARCHAR(50) NOT NULL, 
    short_name VARCHAR(100) NOT NULL, 
    official_name VARCHAR(500) NOT NULL, 
    paper_section VARCHAR(255), 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_exercise_catalog_context ON exercise_catalog (context);

CREATE INDEX ix_exercise_catalog_active ON exercise_catalog (active);

CREATE TABLE skill_catalog (
    id SERIAL NOT NULL, 
    context VARCHAR(50) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    weight NUMERIC(5, 2) NOT NULL, 
    is_core BOOLEAN DEFAULT 'false' NOT NULL, 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_skill_catalog_context ON skill_catalog (context);

CREATE INDEX ix_skill_catalog_active ON skill_catalog (active);

CREATE TABLE lesson_exercises (
    id SERIAL NOT NULL, 
    report_id INTEGER NOT NULL, 
    exercise_id INTEGER NOT NULL, 
    official_name_snapshot VARCHAR(500) NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(report_id) REFERENCES lesson_reports (id) ON DELETE CASCADE, 
    FOREIGN KEY(exercise_id) REFERENCES exercise_catalog (id)
);

CREATE INDEX ix_lesson_exercises_report_id ON lesson_exercises (report_id);

CREATE TABLE skill_assessments (
    id SERIAL NOT NULL, 
    report_id INTEGER NOT NULL, 
    skill_id INTEGER NOT NULL, 
    value_0_4 SMALLINT NOT NULL, 
    skill_version INTEGER DEFAULT '1' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(report_id) REFERENCES lesson_reports (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skill_catalog (id)
);

CREATE INDEX ix_skill_assessments_report_id ON skill_assessments (report_id);

CREATE INDEX ix_skill_assessments_skill_id ON skill_assessments (skill_id);

CREATE TABLE interventions (
    id SERIAL NOT NULL, 
    report_id INTEGER NOT NULL, 
    type interventiontype NOT NULL, 
    reason VARCHAR(255), 
    is_critical BOOLEAN DEFAULT 'false' NOT NULL, 
    description TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(report_id) REFERENCES lesson_reports (id) ON DELETE CASCADE
);

CREATE INDEX ix_interventions_report_id ON interventions (report_id);

CREATE TABLE score_snapshots (
    id SERIAL NOT NULL, 
    client_id INTEGER NOT NULL, 
    context VARCHAR(50) NOT NULL, 
    score NUMERIC(5, 2) NOT NULL, 
    status VARCHAR(50) NOT NULL, 
    formula_version INTEGER NOT NULL, 
    inputs_json JSON NOT NULL, 
    caps_json JSON, 
    calculated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE
);

CREATE INDEX ix_score_snapshots_client_id ON score_snapshots (client_id);

CREATE INDEX ix_score_snapshots_context ON score_snapshots (context);

CREATE INDEX ix_score_snapshots_calculated_at ON score_snapshots (calculated_at);

CREATE TABLE attention_flags (
    id SERIAL NOT NULL, 
    client_id INTEGER NOT NULL, 
    context VARCHAR(50) NOT NULL, 
    skill_id INTEGER, 
    reason VARCHAR(500) NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    opened_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    closed_at TIMESTAMP WITHOUT TIME ZONE, 
    closed_reason TEXT, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE, 
    FOREIGN KEY(skill_id) REFERENCES skill_catalog (id)
);

CREATE INDEX ix_attention_flags_client_id ON attention_flags (client_id);

CREATE INDEX ix_attention_flags_active ON attention_flags (active);

CREATE TABLE ai_drafts (
    id SERIAL NOT NULL, 
    client_id INTEGER NOT NULL, 
    provider VARCHAR(50) NOT NULL, 
    model VARCHAR(100) NOT NULL, 
    prompt_version VARCHAR(50) NOT NULL, 
    input_hash VARCHAR(64) NOT NULL, 
    generated_text TEXT NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE
);

CREATE INDEX ix_ai_drafts_client_id ON ai_drafts (client_id);

CREATE TABLE final_conclusions (
    id SERIAL NOT NULL, 
    client_id INTEGER NOT NULL, 
    status VARCHAR(255) NOT NULL, 
    text TEXT NOT NULL, 
    ai_draft_id INTEGER, 
    approved_by_type VARCHAR(50) NOT NULL, 
    approved_by_id INTEGER NOT NULL, 
    version INTEGER DEFAULT '1' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE, 
    FOREIGN KEY(ai_draft_id) REFERENCES ai_drafts (id)
);

CREATE INDEX ix_final_conclusions_client_id ON final_conclusions (client_id);

CREATE TABLE audit_logs (
    id SERIAL NOT NULL, 
    actor_type VARCHAR(50) NOT NULL, 
    actor_id INTEGER NOT NULL, 
    entity_type VARCHAR(100) NOT NULL, 
    entity_id INTEGER NOT NULL, 
    action VARCHAR(50) NOT NULL, 
    old_json JSON, 
    new_json JSON, 
    reason TEXT, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_audit_logs_entity_type ON audit_logs (entity_type);

CREATE INDEX ix_audit_logs_entity_id ON audit_logs (entity_id);

CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

CREATE TABLE access_grants (
    id SERIAL NOT NULL, 
    instructor_id INTEGER NOT NULL, 
    client_id INTEGER NOT NULL, 
    booking_id INTEGER, 
    valid_from TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    valid_until TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
    reason TEXT NOT NULL, 
    granted_by_admin_id INTEGER NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(instructor_id) REFERENCES instructors (id) ON DELETE CASCADE, 
    FOREIGN KEY(client_id) REFERENCES clients (id) ON DELETE CASCADE, 
    FOREIGN KEY(booking_id) REFERENCES bookings (id) ON DELETE SET NULL
);

CREATE INDEX ix_access_grants_instructor_id ON access_grants (instructor_id);

CREATE INDEX ix_access_grants_client_id ON access_grants (client_id);

CREATE INDEX ix_access_grants_valid_until ON access_grants (valid_until);

CREATE TABLE verdict_catalog (
    id SERIAL NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    sort_order INTEGER DEFAULT '0' NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_verdict_catalog_active ON verdict_catalog (active);

CREATE TABLE intervention_reason_catalog (
    id SERIAL NOT NULL, 
    context VARCHAR(50) NOT NULL, 
    name VARCHAR(255) NOT NULL, 
    criticality VARCHAR(50) NOT NULL, 
    active BOOLEAN DEFAULT 'true' NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_intervention_reason_catalog_context ON intervention_reason_catalog (context);

CREATE INDEX ix_intervention_reason_catalog_active ON intervention_reason_catalog (active);

CREATE TABLE score_formula_versions (
    version SERIAL NOT NULL, 
    valid_from TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    ground_weights_json JSON NOT NULL, 
    city_weights_json JSON NOT NULL, 
    overall_weights_json JSON NOT NULL, 
    caps_json JSON NOT NULL, 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (version)
);

INSERT INTO alembic_version (version_num) VALUES ('001_initial') RETURNING alembic_version.version_num;

-- Running upgrade 001_initial -> 20260905_1400_002

DELETE FROM clients WHERE full_name = 'Петров Петр Петрович' AND phone = '+77007654321';

DELETE FROM instructors WHERE full_name = 'Иванов Иван Иванович' AND phone = '+77001234567';

UPDATE alembic_version SET version_num='20260905_1400_002' WHERE alembic_version.version_num = '001_initial';

-- Running upgrade 20260905_1400_002 -> 003_telegram_user_id_bigint

ALTER TABLE instructors ALTER COLUMN telegram_user_id TYPE BIGINT;

UPDATE alembic_version SET version_num='003_telegram_user_id_bigint' WHERE alembic_version.version_num = '20260905_1400_002';

-- Running upgrade 003_telegram_user_id_bigint -> 004_attendance

ALTER TABLE bookings ADD COLUMN arrived_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE bookings ADD COLUMN finished_at TIMESTAMP WITHOUT TIME ZONE;

ALTER TABLE clients ADD COLUMN is_archived BOOLEAN DEFAULT false NOT NULL;

UPDATE alembic_version SET version_num='004_attendance' WHERE alembic_version.version_num = '003_telegram_user_id_bigint';

-- Running upgrade 004_attendance -> 005_utc_timestamps

ALTER TABLE instructors ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE instructors ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE clients ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE clients ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE bookings ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE bookings ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE bookings ALTER COLUMN arrived_at TYPE TIMESTAMP WITH TIME ZONE USING arrived_at AT TIME ZONE 'UTC';

ALTER TABLE bookings ALTER COLUMN finished_at TYPE TIMESTAMP WITH TIME ZONE USING finished_at AT TIME ZONE 'UTC';

ALTER TABLE lesson_reports ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE lesson_reports ALTER COLUMN edited_until TYPE TIMESTAMP WITH TIME ZONE USING edited_until AT TIME ZONE 'UTC';

ALTER TABLE lesson_reports ALTER COLUMN last_edited_at TYPE TIMESTAMP WITH TIME ZONE USING last_edited_at AT TIME ZONE 'UTC';

ALTER TABLE skill_assessments ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE interventions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE score_snapshots ALTER COLUMN calculated_at TYPE TIMESTAMP WITH TIME ZONE USING calculated_at AT TIME ZONE 'UTC';

ALTER TABLE attention_flags ALTER COLUMN opened_at TYPE TIMESTAMP WITH TIME ZONE USING opened_at AT TIME ZONE 'UTC';

ALTER TABLE attention_flags ALTER COLUMN closed_at TYPE TIMESTAMP WITH TIME ZONE USING closed_at AT TIME ZONE 'UTC';

ALTER TABLE final_conclusions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE ai_drafts ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE audit_logs ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE access_grants ALTER COLUMN valid_from TYPE TIMESTAMP WITH TIME ZONE USING valid_from AT TIME ZONE 'UTC';

ALTER TABLE access_grants ALTER COLUMN valid_until TYPE TIMESTAMP WITH TIME ZONE USING valid_until AT TIME ZONE 'UTC';

ALTER TABLE access_grants ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE exercise_catalog ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE exercise_catalog ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE skill_catalog ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE skill_catalog ALTER COLUMN updated_at TYPE TIMESTAMP WITH TIME ZONE USING updated_at AT TIME ZONE 'UTC';

ALTER TABLE intervention_reason_catalog ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE verdict_catalog ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

ALTER TABLE score_formula_versions ALTER COLUMN valid_from TYPE TIMESTAMP WITH TIME ZONE USING valid_from AT TIME ZONE 'UTC';

ALTER TABLE score_formula_versions ALTER COLUMN created_at TYPE TIMESTAMP WITH TIME ZONE USING created_at AT TIME ZONE 'UTC';

UPDATE alembic_version SET version_num='005_utc_timestamps' WHERE alembic_version.version_num = '004_attendance';

COMMIT;

