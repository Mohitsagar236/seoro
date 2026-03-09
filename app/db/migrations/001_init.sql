-- ============================================================
-- Seoro — Initial Schema
-- Run this in Supabase SQL Editor (or via psql)
-- ============================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ── Meetings ────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS meetings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title           TEXT,
    audio_url       TEXT,
    transcript      TEXT,
    duration_seconds FLOAT,
    status          TEXT NOT NULL DEFAULT 'pending'
                        CHECK (status IN (
                            'pending','transcribing','extracting','analyzing','completed','failed'
                        )),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ── Events ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS events (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    event_type      TEXT NOT NULL,
    speaker_role    TEXT,
    topic           TEXT,
    content         TEXT,
    timestamp_start TEXT,
    timestamp_end   TEXT,
    raw_text        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_events_meeting_id ON events(meeting_id);

-- ── Intents ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS intents (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id        UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    intent_type     TEXT NOT NULL
                        CHECK (intent_type IN (
                            'feature_request','bug_report','customer_feedback',
                            'strategy_discussion','task_assignment',
                            'integrations','data_fusion','general'
                        )),
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('critical','high','medium','low')),
    confidence      FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    reasoning       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_intents_meeting_id ON intents(meeting_id);
CREATE INDEX IF NOT EXISTS idx_intents_event_id ON intents(event_id);

-- ── Integration insights ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS integration_insights (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id          UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    event_id            UUID REFERENCES events(id) ON DELETE SET NULL,
    integration_name    TEXT NOT NULL,
    integration_type    TEXT NOT NULL
                            CHECK (integration_type IN (
                                'api', 'webhook', 'crm', 'erp', 'data_pipeline',
                                'messaging', 'analytics', 'auth', 'storage', 'custom'
                            )),
    direction           TEXT NOT NULL
                            CHECK (direction IN ('inbound', 'outbound', 'bidirectional', 'unknown')),
    systems_involved    TEXT[],
    use_case            TEXT,
    status              TEXT NOT NULL DEFAULT 'requested'
                            CHECK (status IN ('requested', 'planned', 'in_progress', 'existing')),
    priority            TEXT NOT NULL DEFAULT 'medium'
                            CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    confidence          FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    raw_text            TEXT,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_integration_insights_meeting_id ON integration_insights(meeting_id);

-- ── Data fusion insights ─────────────────────────────────────
CREATE TABLE IF NOT EXISTS data_fusion_insights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    meeting_id      UUID NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    event_id        UUID REFERENCES events(id) ON DELETE SET NULL,
    fusion_goal     TEXT NOT NULL,
    sources         TEXT[],
    output_target   TEXT,
    technique       TEXT NOT NULL
                        CHECK (technique IN (
                            'join', 'union', 'aggregate', 'ETL', 'CDC',
                            'streaming', 'batch', 'ML', 'unknown'
                        )),
    complexity      TEXT NOT NULL DEFAULT 'medium'
                        CHECK (complexity IN ('low', 'medium', 'high')),
    priority        TEXT NOT NULL DEFAULT 'medium'
                        CHECK (priority IN ('critical', 'high', 'medium', 'low')),
    confidence      FLOAT NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    raw_text        TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_data_fusion_insights_meeting_id ON data_fusion_insights(meeting_id);

-- ── Updated-at trigger ──────────────────────────────────────
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS meetings_updated_at ON meetings;
CREATE TRIGGER meetings_updated_at
    BEFORE UPDATE ON meetings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
