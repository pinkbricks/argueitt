"""Import legacy records atomically; dry run unless --apply is supplied."""

import argparse
import asyncio
import json
from pathlib import Path

from psycopg.types.json import Jsonb

from database import DatabaseUnavailable, connection


def read_records(path):
    if not path.exists():
        raise ValueError(f'Missing source file: {path.name}')
    records = json.loads(path.read_text())
    if not isinstance(records, list):
        raise ValueError(f'{path.name} must contain a JSON array')
    return records


async def import_records(directory, apply=False):
    users = read_records(directory / 'users.json')
    attempts = read_records(directory / 'transcripts.json')
    counts = {'users': 0, 'attempts': 0}
    async with connection(migration=True) as conn:
        for user in users:
            # Preserve IDs and fail on conflicting Google identities; never
            # reassign another person's history to resolve a collision.
            existing = await (await conn.execute(
                'SELECT id, google_id FROM users WHERE id = %s OR google_id = %s',
                (user['id'], user['google_id']),
            )).fetchall()
            if existing:
                if len(existing) != 1 or existing[0] != {'id': user['id'], 'google_id': user['google_id']}:
                    raise ValueError('A user ID conflicts with an existing Google identity; import rolled back')
                continue
            await conn.execute('''INSERT INTO users
                (id, google_id, email, name, picture, created_at, last_seen_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (user['id'], user['google_id'], user.get('email', ''), user.get('name', ''),
                 user.get('picture', ''), user['created_at'], user['last_seen_at']))
            counts['users'] += 1
        for record in attempts:
            existing = await (await conn.execute(
                'SELECT user_id FROM attempts WHERE id = %s', (record['id'],),
            )).fetchone()
            if existing:
                if existing['user_id'] != record.get('user_id'):
                    raise ValueError('An attempt ID conflicts with an existing owner; import rolled back')
                continue
            await conn.execute('''INSERT INTO attempts
                (id, user_id, created_at, topic, side, transcript, words,
                 audio_bytes, audio_type, analysis)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)''',
                (record['id'], record.get('user_id'), record['created_at'], record['topic'],
                 record['side'], record.get('transcript', ''), Jsonb(record.get('words', [])),
                 record.get('audio_bytes', 0), record.get('audio_type'),
                 Jsonb(record['analysis']) if record.get('analysis') is not None else None))
            counts['attempts'] += 1
        if not apply:
            await conn.rollback()
    return counts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(__file__).with_name('data'))
    parser.add_argument('--apply', action='store_true', help='Commit the import (default: rollback/dry run)')
    args = parser.parse_args()
    try:
        counts = asyncio.run(import_records(args.data_dir, args.apply))
        print(f"{'Imported' if args.apply else 'Dry run; would import'}: "
              f"{counts['users']} users, {counts['attempts']} attempts. Existing IDs skipped.")
    except (DatabaseUnavailable, ValueError, KeyError, OSError) as exc:
        # Avoid printing source records or database diagnostics containing private data.
        raise SystemExit(f'Import failed ({type(exc).__name__}); no records committed.') from None
