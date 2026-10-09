"""Database operations used by authentication and practice history."""

import base64
import binascii
import json
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from psycopg.types.json import Jsonb

from database import connection
from streaks import summarize_streak


async def get_streak(user_id, timezone_name):
    try:
        zone = ZoneInfo(timezone_name)
    except (ValueError, ZoneInfoNotFoundError):
        raise ValueError('Invalid timezone') from None
    async with connection() as conn:
        # Distinct days across the complete history, independent of pagination.
        # Silent recordings and unfinished legacy attempts do not earn a day.
        rows = await (await conn.execute('''
            SELECT DISTINCT (created_at AT TIME ZONE %s)::date AS practice_day
            FROM attempts
            WHERE user_id = %s AND analysis IS NOT NULL
              AND analysis <> 'null'::jsonb AND btrim(transcript) <> ''
        ''', (timezone_name, user_id))).fetchall()
    return {**summarize_streak([row['practice_day'] for row in rows],
                              datetime.now(zone).date()),
            'timezone': timezone_name}


async def upsert_user(claims):
    async with connection() as conn:
        row = await conn.execute('''
            INSERT INTO users (id, google_id, email, name, picture)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (google_id) DO UPDATE SET
                email = EXCLUDED.email, name = EXCLUDED.name,
                picture = EXCLUDED.picture, last_seen_at = now()
            RETURNING *
        ''', (uuid.uuid4().hex, claims['sub'], claims.get('email', ''),
              claims.get('name', ''), claims.get('picture', '')))
        return await row.fetchone()


async def get_user(user_id):
    async with connection() as conn:
        return await (await conn.execute('SELECT * FROM users WHERE id = %s', (user_id,))).fetchone()


async def get_attempt(user_id, attempt_id):
    async with connection() as conn:
        return await (await conn.execute(
            'SELECT * FROM attempts WHERE user_id = %s AND id = %s',
            (user_id, attempt_id),
        )).fetchone()


async def get_request(user_id, request_id):
    async with connection() as conn:
        return await (await conn.execute(
            'SELECT * FROM attempts WHERE user_id = %s AND request_id = %s',
            (user_id, request_id),
        )).fetchone()


async def save_attempt(record):
    async with connection() as conn:
        cursor = await conn.execute('''
            INSERT INTO attempts (id, user_id, request_id, request_hash, previous_attempt_id,
                topic, side, transcript, words, audio_bytes, audio_type, analysis)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, request_id) DO NOTHING
            RETURNING *
        ''', (uuid.uuid4().hex, record['user_id'], record['request_id'], record['request_hash'],
              record['previous_attempt_id'], record['topic'], record['side'],
              record['transcript'], Jsonb(record['words']), record['audio_bytes'],
              record['audio_type'], Jsonb(record['analysis'])))
        saved = await cursor.fetchone()
        if saved is None:
            saved = await (await conn.execute(
                'SELECT * FROM attempts WHERE user_id = %s AND request_id = %s',
                (record['user_id'], record['request_id']),
            )).fetchone()
        return saved


def encode_cursor(record):
    value = json.dumps([record['created_at'].isoformat(), record['id']]).encode()
    return base64.urlsafe_b64encode(value).decode()


def decode_cursor(value):
    try:
        created_at, attempt_id = json.loads(base64.b64decode(value, altchars=b'-_', validate=True))
        timestamp = datetime.fromisoformat(created_at)
        if timestamp.tzinfo is None or not isinstance(attempt_id, str) or not 1 <= len(attempt_id) <= 128:
            raise ValueError
        return timestamp, attempt_id
    except (ValueError, TypeError, binascii.Error, UnicodeError):
        raise ValueError('Invalid history cursor') from None


async def list_attempts(user_id, limit, cursor=None):
    after = decode_cursor(cursor) if cursor else None
    params = [user_id]
    condition = ''
    if after:
        condition = 'AND (created_at, id) < (%s, %s)'
        params.extend(after)
    params.append(limit + 1)
    async with connection() as conn:
        rows = await (await conn.execute(f'''
            SELECT id, created_at, topic, side, transcript, analysis, previous_attempt_id
            FROM attempts WHERE user_id = %s {condition}
            ORDER BY created_at DESC, id DESC LIMIT %s
        ''', params)).fetchall()
    return {'attempts': rows[:limit],
            'next_cursor': encode_cursor(rows[limit - 1]) if len(rows) > limit else None}
