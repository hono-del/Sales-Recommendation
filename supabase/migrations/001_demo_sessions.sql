-- Decision Intelligence デモセッション（Phase 0）
-- Supabase SQL Editor または supabase db push で適用

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- updated_at 自動更新
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TABLE IF NOT EXISTS demo_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  delegation_level VARCHAR(20) CHECK (delegation_level IN ('guide', 'co_pilot', 'auto')),
  status VARCHAR(20) NOT NULL DEFAULT 'active'
    CHECK (status IN ('active', 'completed', 'aborted')),
  demo_fallback_used BOOLEAN NOT NULL DEFAULT false,
  metadata JSONB
);

CREATE TRIGGER trg_demo_sessions_updated
  BEFORE UPDATE ON demo_sessions
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE INDEX IF NOT EXISTS idx_demo_sessions_created_at
  ON demo_sessions (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_demo_sessions_status
  ON demo_sessions (status);

CREATE TABLE IF NOT EXISTS session_answers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
  question_index INT NOT NULL CHECK (question_index BETWEEN 1 AND 5),
  question_id VARCHAR(50) NOT NULL,
  answer_key VARCHAR(50) NOT NULL,
  answered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_session_question
  ON session_answers (session_id, question_index);

CREATE TABLE IF NOT EXISTS session_profiles (
  session_id UUID PRIMARY KEY REFERENCES demo_sessions(id) ON DELETE CASCADE,
  score_safety DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score_safety BETWEEN 0 AND 100),
  score_family DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score_family BETWEEN 0 AND 100),
  score_efficiency DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score_efficiency BETWEEN 0 AND 100),
  score_enjoyment DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score_enjoyment BETWEEN 0 AND 100),
  score_adventure DOUBLE PRECISION NOT NULL DEFAULT 0 CHECK (score_adventure BETWEEN 0 AND 100),
  mapped_needs JSONB DEFAULT '[]'::jsonb,
  mapped_capabilities JSONB DEFAULT '[]'::jsonb,
  detected_loads JSONB DEFAULT '[]'::jsonb,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TRIGGER trg_session_profiles_updated
  BEFORE UPDATE ON session_profiles
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS session_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID NOT NULL REFERENCES demo_sessions(id) ON DELETE CASCADE,
  screen_id VARCHAR(30) NOT NULL,
  event_type VARCHAR(30) NOT NULL,
  payload JSONB,
  duration_ms INT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_session_events_session
  ON session_events (session_id, created_at);

-- デモフェーズ: RLS 無効（社内デモのみ想定）
ALTER TABLE demo_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_answers ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE session_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "demo_anon_all_demo_sessions" ON demo_sessions FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "demo_anon_all_session_answers" ON session_answers FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "demo_anon_all_session_profiles" ON session_profiles FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "demo_anon_all_session_events" ON session_events FOR ALL USING (true) WITH CHECK (true);
