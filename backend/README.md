# Argueitt backend and Neon setup

This repository is linked to Neon project `solitary-sun-90415762` (ArgueItt),
branch `production`. Root `neon.ts` declares `auth: true`. Neon Auth is provisioned,
but the app still uses its existing Google ID-token and signed-cookie login;
enabling the Neon service does not migrate the app's authentication.

The root `package.json` contains Neon configuration tooling only. The React app
remains in `frontend/`. Neon CLI skill/MCP setup requires Node 22.20 or newer.
`neon deploy` applies the Neon service configuration; it does not publish the
React/FastAPI website or run the Python SQL migrations below.

`neon env pull` refreshes ignored root `.env.local`. The Python backend reads
`backend/.env`: copy `DATABASE_URL` there and map `DATABASE_URL_UNPOOLED` to
`DATABASE_MIGRATION_URL` when deliberately switching branches or rotating credentials.
Keep both URLs pointed at the same database and branch.

The FastAPI backend uses Neon Postgres for Google accounts and signed-in practice
history. New guest attempts remain temporary; their feedback needs no database.
Audio is uploaded for transcription but is not stored in Postgres. Playback and
downloads use the recording in the current browser page.

## Configure and run

From `backend/`:

```bash
python3 -m venv venv
venv/bin/python -m pip install -r requirements.txt
```

Add the settings in `.env.example` to your existing `backend/.env` (do not overwrite
existing keys). In Neon's **Connect** dialog, enable connection pooling and copy
the Postgres URL into `DATABASE_URL`. Keep its SSL and channel binding parameters.
Only the backend receives this secret; never use a `VITE_` database variable.

Optionally set `DATABASE_MIGRATION_URL` to the direct connection URL for the same
database. Migration/import commands use it when present, otherwise `DATABASE_URL`.
The app uses Psycopg async connections and short transactions through Neon's
pooler; it holds no database connection open while Gemini is running.

```bash
venv/bin/python migrate.py
venv/bin/python -m uvicorn main:app --reload --port 8000
```

Keep `SESSION_SECRET` stable across deployments so existing signed cookies remain
valid. Google login still requires `GOOGLE_CLIENT_ID` here and the matching
`VITE_GOOGLE_CLIENT_ID` in the frontend. Gemini requires `GEMINI_API_KEY`.

For deployment, configure these backend environment variables on the hosting
platform and set `ENV=production` for HTTPS cookies. Run `migrate.py` against the
target database before deploying the updated backend and frontend together.
Migrations are explicit, not run on every function invocation or cold start.

## Schema and behavior

- `users`: stable app ID, unique Google `sub`, profile, creation and last-seen times.
- `attempts`: owner, topic and side, transcript, word timings, analysis JSON
  (including delivery metrics), audio metadata, timestamps, optional previous attempt.
- A composite foreign key keeps linked retries under the same owner. History has
  an index on `(user_id, created_at DESC, id DESC)`.
- `schema_migrations` records applied SQL filenames and checksums. Add a new
  numbered migration for future changes; do not edit already-applied migrations.

`POST /api/analyze` now requires a UUID `request_id` in its multipart form. The
frontend reuses it for network retries of the same recording and makes a new one
for each new recording. `(user_id, request_id)` is unique. Saved replays return the
original feedback; changing the payload under an existing key returns HTTP 409.
Concurrent requests can still perform duplicate model work, but save one history
record. This is duplicate-save protection, not a background job queue.

Responses include `attempt_id` and `persistence_status`:

- `saved`: the attempt is committed to history.
- `not_saved`: feedback is available, but persistence failed; the UI explains this.
- `guest`: temporary feedback, no history record.

Optional `previous_attempt_id` links a retry. The backend verifies ownership,
topic and side and uses the saved coaching focus. Guest attempts cannot be claimed
by signing in later. The browser's current retry comparison still resets on reload;
the database retains links for future comparison/resume features.

`GET /api/attempts?limit=20&cursor=...` returns `{attempts, next_cursor}`. It always
uses the signed cookie's user, never an owner ID supplied by the browser. Limits
are 1–100. Cursor pagination uses timestamp and ID to handle equal timestamps.

## Daily practice streaks

`GET /api/streak?timezone=Africa/Nairobi` returns the signed-in user's current
streak, longest streak, total practice days, today's completion, and the last seven
calendar days. The browser supplies its IANA timezone; omitted zones default to
UTC and invalid zones return HTTP 400. Guests receive HTTP 401.

A day counts when at least one saved attempt has a nonempty transcript and an
analysis, regardless of score. Multiple attempts on that day count once. Silent,
unfinished, unsaved, and guest attempts do not count. A streak ending yesterday
remains active until today ends; missing a full day resets the current streak but
preserves the personal best.

Streaks are derived from the entire attempt history, including existing records,
so no new database migration is needed. They use attempt completion/save time.
Calendar dates are recalculated in the viewer's current timezone (including when
travelling), rather than storing a fixed account timezone. The card appears on
Progress and after saved feedback, and refreshes at local midnight or when the
page regains focus.

## Import existing JSON data

Back up `data/users.json` and `data/transcripts.json`, then run migrations first.
Import before accepting new sign-ins to preserve the original account IDs and
cookies. Pause legacy writes during the import and switch to the database backend
after it completes.

```bash
venv/bin/python import_json.py          # checks inserts, then rolls back
venv/bin/python import_json.py --apply  # commits the complete batch
```

Use `--data-dir /path/to/backup` for another source directory. Both files must
exist; an empty array is valid. Existing IDs are skipped, existing profiles are
not overwritten, and identity/ownership conflicts or missing referenced users
roll back the entire import. IDs, timestamps, nullable analyses, and historical
guest records are preserved. Re-running an import does not duplicate records.
Guest records remain unowned and are not exposed through account history.

## Verification

```bash
venv/bin/python -m unittest discover -s tests -v
```

API tests mock Google, Gemini and storage and make no external calls. For the
real Postgres integration tests, set `TEST_DATABASE_URL` to a development database
before running the same command. These tests create and delete only a uniquely
named test schema. They exercise migrations, concurrent upserts/saves, ownership,
retry constraints, pagination, import dry runs, and rollback. Without that variable
the Postgres tests are skipped.

Connection references: [Neon connection guide](https://neon.com/docs/get-started/connect-neon)
and [Psycopg async connections](https://www.psycopg.org/psycopg3/docs/advanced/async.html).
