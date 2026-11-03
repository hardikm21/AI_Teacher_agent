-- AI Teacher Agent — persistence schema (Postgres-flavoured)
--
-- The running backend uses an in-memory store (app.api.store) so the demo
-- requires no database. This schema is the target shape when you're ready
-- to swap the in-memory dict for a real Postgres instance.
--
-- Convention: every row carries created_at / updated_at; soft deletes only.

BEGIN;

-- ── reference tables ─────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS users (
    id           TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    email        TEXT UNIQUE,
    role         TEXT NOT NULL DEFAULT 'student'
                 CHECK (role IN ('student', 'teacher', 'admin')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deleted_at   TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS projects (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name         TEXT NOT NULL,
    description  TEXT NOT NULL,
    tech_stack   TEXT[] NOT NULL DEFAULT '{}',
    difficulty   TEXT NOT NULL DEFAULT 'medium'
                 CHECK (difficulty IN ('easy', 'medium', 'hard')),
    created_by   TEXT REFERENCES users(id) ON DELETE SET NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── per-student learning session ─────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id               TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id            UUID REFERENCES projects(id) ON DELETE SET NULL,
    project_snapshot      JSONB NOT NULL,           -- {name, description}
    known_stack           TEXT[] NOT NULL DEFAULT '{}',
    unknown_stack         TEXT[] NOT NULL DEFAULT '{}',
    repo_url              TEXT,
    github_branch         TEXT NOT NULL DEFAULT 'main',
    start_date            DATE NOT NULL,
    end_date              DATE NOT NULL,
    blackout_dates        DATE[] NOT NULL DEFAULT '{}',
    current_concept_index INT  NOT NULL DEFAULT 0,
    current_week          INT  NOT NULL DEFAULT 1,
    project_complete      BOOLEAN NOT NULL DEFAULT FALSE,
    state                 JSONB NOT NULL,           -- full AgentState mirror
    created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sessions_user      ON sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_sessions_project   ON sessions (project_id);
CREATE INDEX IF NOT EXISTS ix_sessions_open      ON sessions (user_id) WHERE project_complete = FALSE;

-- ── prereq + weekly quiz results (flattened for easy querying) ───────────────

CREATE TABLE IF NOT EXISTS quiz_results (
    id           BIGSERIAL PRIMARY KEY,
    session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    kind         TEXT NOT NULL CHECK (kind IN ('prereq', 'weekly')),
    week         INT,                              -- null for prereq quizzes
    concept      TEXT NOT NULL,
    questions    JSONB NOT NULL,
    score        INT  NOT NULL,
    passed       BOOLEAN NOT NULL,
    submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_quiz_results_session ON quiz_results (session_id);

-- ── weekly evaluations ───────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS evaluations (
    id             BIGSERIAL PRIMARY KEY,
    session_id     UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    week_number    INT  NOT NULL,
    score          NUMERIC(4, 1) NOT NULL,         -- -5.0 .. +5.0
    score_display  NUMERIC(4, 1) NOT NULL,         --  0.0 .. 10.0
    breakdown      JSONB,
    feedback       JSONB NOT NULL,
    evaluated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (session_id, week_number)
);

CREATE INDEX IF NOT EXISTS ix_evaluations_session ON evaluations (session_id);

-- ── GitHub activity snapshots (optional, for later analytics) ────────────────

CREATE TABLE IF NOT EXISTS github_checks (
    id           BIGSERIAL PRIMARY KEY,
    session_id   UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    week_number  INT  NOT NULL,
    commit_sha   TEXT,
    files        TEXT[] NOT NULL DEFAULT '{}',
    completed    BOOLEAN NOT NULL,
    reason       TEXT,
    checked_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- ── keep updated_at honest ───────────────────────────────────────────────────

CREATE OR REPLACE FUNCTION touch_updated_at() RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_users_touch    ON users;
DROP TRIGGER IF EXISTS trg_projects_touch ON projects;
DROP TRIGGER IF EXISTS trg_sessions_touch ON sessions;

CREATE TRIGGER trg_users_touch    BEFORE UPDATE ON users    FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER trg_projects_touch BEFORE UPDATE ON projects FOR EACH ROW EXECUTE FUNCTION touch_updated_at();
CREATE TRIGGER trg_sessions_touch BEFORE UPDATE ON sessions FOR EACH ROW EXECUTE FUNCTION touch_updated_at();

COMMIT;
