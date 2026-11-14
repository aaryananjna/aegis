-- Aegis TigerDB schema, option D: family members log in; the grandparent never does.
-- The grandparent's laptop is paired once, so every call is filed under the right grandparent.
--
-- Stored: login info (hashed), who watches whom, and per-call numbers over time.
-- Never stored: audio, caption text, quotes, tactics or the family code word.
--
-- Safe to run on an empty database or on one that already has some of these tables
-- (everything is IF NOT EXISTS), so it never drops or rewrites existing data.

CREATE EXTENSION IF NOT EXISTS citext;

-- Family members who log in.
CREATE TABLE IF NOT EXISTS users (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  email         citext UNIQUE NOT NULL,
  password_hash text NOT NULL,                       -- argon2, never the password
  display_name  text NOT NULL,
  created_at    timestamptz NOT NULL DEFAULT now()
);

-- The grandparent being protected. No login.
CREATE TABLE IF NOT EXISTS elders (
  id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  display_name text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);

-- Which family members watch which grandparent. Call history is filtered through this.
CREATE TABLE IF NOT EXISTS elder_members (
  elder_id uuid NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  user_id  uuid NOT NULL REFERENCES users(id)  ON DELETE CASCADE,
  role     text NOT NULL CHECK (role IN ('owner', 'viewer')),
  PRIMARY KEY (elder_id, user_id)
);
CREATE INDEX IF NOT EXISTS elder_members_user_idx ON elder_members (user_id);

-- The grandparent's paired laptop. Only a hash of the device token is stored.
CREATE TABLE IF NOT EXISTS elder_devices (
  token_hash bytea PRIMARY KEY,                      -- sha256 of the device token
  elder_id   uuid NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen  timestamptz
);
CREATE INDEX IF NOT EXISTS elder_devices_elder_idx ON elder_devices (elder_id);

-- Who is logged in. Only a hash of the login token is stored.
CREATE TABLE IF NOT EXISTS login_sessions (
  token_hash bytea PRIMARY KEY,                      -- sha256 of the cookie token
  user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL
);
CREATE INDEX IF NOT EXISTS login_sessions_user_idx ON login_sessions (user_id);

-- One row per call.
CREATE TABLE IF NOT EXISTS calls (
  id         text PRIMARY KEY,                       -- the server's session_id
  elder_id   uuid NOT NULL REFERENCES elders(id) ON DELETE CASCADE,
  started_at timestamptz NOT NULL,
  ended_at   timestamptz,
  max_score  real,
  max_level  text CHECK (max_level IN ('low', 'elevated', 'high')),
  flagged_at timestamptz,                            -- first time the call reached HIGH
  card       text CHECK (card IN ('codeword', 'verify', 'hangup'))
);
CREATE INDEX IF NOT EXISTS calls_elder_started_idx ON calls (elder_id, started_at DESC);

-- The risk score over time (Timescale hypertable). Numbers only.
CREATE TABLE IF NOT EXISTS risk_points (
  time    timestamptz NOT NULL,
  call_id text NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
  score   real NOT NULL,
  level   text NOT NULL
);
-- Timescale-only parts are skipped on plain Postgres, so anyone can run this locally.
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
    PERFORM create_hypertable('risk_points', by_range('time'), if_not_exists => true);
  END IF;
END $$;
CREATE INDEX IF NOT EXISTS risk_points_call_time_idx ON risk_points (call_id, time DESC);

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'risk_points_score_range') THEN
    ALTER TABLE risk_points ADD CONSTRAINT risk_points_score_range CHECK (score >= 0 AND score <= 1);
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'risk_points_level_valid') THEN
    ALTER TABLE risk_points ADD CONSTRAINT risk_points_level_valid
      CHECK (level IN ('low', 'elevated', 'high'));
  END IF;
END $$;

-- Keep risk history for 30 days only (Timescale).
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
    PERFORM add_retention_policy('risk_points', INTERVAL '30 days', if_not_exists => true);
  END IF;
END $$;
