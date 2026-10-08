CREATE TABLE users (
    id text PRIMARY KEY,
    google_id text NOT NULL UNIQUE,
    email text NOT NULL,
    name text NOT NULL,
    picture text NOT NULL DEFAULT '',
    created_at timestamptz NOT NULL DEFAULT now(),
    last_seen_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE attempts (
    id text PRIMARY KEY,
    user_id text REFERENCES users(id) ON DELETE CASCADE,
    request_id uuid,
    request_hash text,
    previous_attempt_id text,
    created_at timestamptz NOT NULL DEFAULT now(),
    topic text NOT NULL,
    side text NOT NULL CHECK (side IN ('for', 'against')),
    transcript text NOT NULL DEFAULT '',
    words jsonb NOT NULL DEFAULT '[]'::jsonb,
    audio_bytes bigint NOT NULL DEFAULT 0 CHECK (audio_bytes >= 0),
    audio_type text,
    analysis jsonb,
    UNIQUE (user_id, request_id),
    UNIQUE (id, user_id),
    FOREIGN KEY (previous_attempt_id, user_id) REFERENCES attempts(id, user_id),
    CHECK (previous_attempt_id IS NULL OR user_id IS NOT NULL)
);

CREATE INDEX attempts_user_created_idx ON attempts(user_id, created_at DESC, id DESC);
CREATE INDEX attempts_previous_idx ON attempts(previous_attempt_id, user_id)
    WHERE previous_attempt_id IS NOT NULL;
