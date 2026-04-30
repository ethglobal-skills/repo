-- Run this in the Supabase SQL editor to create all tables.
-- Order matters due to foreign key dependencies.

CREATE TABLE IF NOT EXISTS events (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  url         TEXT,
  logo_url    TEXT,
  city        TEXT,
  country     TEXT,
  start_date  DATE,
  end_date    DATE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sponsors (
  id          SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  image_url   TEXT UNIQUE,   -- source of truth for deduplication
  about       TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS sponsor_docs (
  id          SERIAL PRIMARY KEY,
  sponsor_id  INTEGER NOT NULL REFERENCES sponsors(id) ON DELETE CASCADE,
  event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  name        TEXT NOT NULL,
  url         TEXT NOT NULL,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS prizes (
  id          SERIAL PRIMARY KEY,
  event_id    INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  sponsor_id  INTEGER NOT NULL REFERENCES sponsors(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  description TEXT,
  amount      INTEGER,
  prize_pool  BOOLEAN DEFAULT FALSE,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS projects (
  id            SERIAL PRIMARY KEY,
  event_id      INTEGER REFERENCES events(id),
  title         TEXT NOT NULL,
  url           TEXT UNIQUE,
  tagline       TEXT,
  description   TEXT,
  how_its_made  TEXT,
  github        TEXT,
  live_demo     TEXT,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS project_prizes (
  id          SERIAL PRIMARY KEY,
  project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  prize_id    INTEGER NOT NULL REFERENCES prizes(id) ON DELETE CASCADE,
  UNIQUE(project_id, prize_id),
  created_at  TIMESTAMPTZ DEFAULT NOW()
);
