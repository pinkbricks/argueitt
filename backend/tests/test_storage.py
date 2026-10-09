"""Real Postgres tests, isolated in a disposable schema on TEST_DATABASE_URL."""

import asyncio
import json
import os
import tempfile
import unittest
import uuid
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import patch

from psycopg import sql

import database
import import_json
import migrate
import storage


@unittest.skipUnless(os.getenv('TEST_DATABASE_URL'), 'Set TEST_DATABASE_URL to run Postgres integration tests')
class StorageTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.schema = 'argueitt_test_' + uuid.uuid4().hex
        env = patch.dict(os.environ, {'DATABASE_URL': os.environ['TEST_DATABASE_URL'],
                                      'DATABASE_MIGRATION_URL': ''})
        env.start()
        self.addCleanup(env.stop)
        async with database.connection() as conn:
            await conn.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        self.addAsyncCleanup(self.drop_schema)

        @asynccontextmanager
        async def isolated_connection(**kwargs):
            async with database.connection(**kwargs) as conn:
                await conn.execute(sql.SQL('SET LOCAL search_path TO {}').format(sql.Identifier(self.schema)))
                yield conn

        self.connection = isolated_connection
        for module in (storage, migrate, import_json):
            mock = patch.object(module, 'connection', isolated_connection)
            mock.start()
            self.addCleanup(mock.stop)
        await migrate.migrate()

    async def drop_schema(self):
        async with database.connection() as conn:
            await conn.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    async def user(self, sub='alice'):
        return await storage.upsert_user({'sub': sub, 'name': sub, 'email': f'{sub}@example.test'})

    def record(self, user_id, **updates):
        return {'user_id': user_id, 'request_id': uuid.uuid4(), 'request_hash': 'hash',
                'previous_attempt_id': None, 'topic': 'Test', 'side': 'for', 'transcript': 'Hello',
                'words': [], 'audio_bytes': 100, 'audio_type': 'audio/wav',
                'analysis': {'next_focus': 'Focus'}, **updates}

    async def test_migration_repeat_and_user_upsert(self):
        await migrate.migrate()
        users = await asyncio.gather(*(self.user() for _ in range(3)))
        self.assertEqual(len({u['id'] for u in users}), 1)
        updated = await storage.upsert_user({'sub': 'alice', 'name': 'New name', 'email': 'new@example.test'})
        self.assertEqual(updated['id'], users[0]['id'])
        self.assertEqual((await storage.get_user(updated['id']))['name'], 'New name')

    async def test_concurrent_duplicate_saves_and_owner_isolation(self):
        alice, bob = await self.user(), await self.user('bob')
        record = self.record(alice['id'])
        rows = await asyncio.gather(*(storage.save_attempt(record) for _ in range(3)))
        self.assertEqual(len({r['id'] for r in rows}), 1)
        self.assertIsNone(await storage.get_attempt(bob['id'], rows[0]['id']))
        self.assertIsNone(await storage.get_request(bob['id'], record['request_id']))
        self.assertEqual((await storage.list_attempts(bob['id'], 20))['attempts'], [])

    async def test_pagination_with_equal_timestamps(self):
        user = await self.user()
        rows = [await storage.save_attempt(self.record(user['id'])) for _ in range(5)]
        async with self.connection() as conn:
            await conn.execute("UPDATE attempts SET created_at = '2026-01-01T00:00:00Z'")
        seen, cursor = [], None
        while True:
            page = await storage.list_attempts(user['id'], 2, cursor)
            seen.extend(row['id'] for row in page['attempts'])
            cursor = page['next_cursor']
            if cursor is None:
                break
        self.assertEqual(seen, sorted([r['id'] for r in rows], reverse=True))

    async def test_retry_foreign_key_rejects_other_owner(self):
        alice, bob = await self.user(), await self.user('bob')
        parent = await storage.save_attempt(self.record(alice['id']))
        child = await storage.save_attempt(self.record(alice['id'], previous_attempt_id=parent['id']))
        self.assertEqual(child['previous_attempt_id'], parent['id'])
        with self.assertRaises(database.DatabaseUnavailable):
            await storage.save_attempt(self.record(bob['id'], previous_attempt_id=parent['id']))

    async def test_streak_counts_local_days_and_only_completed_owned_practice(self):
        alice, bob = await self.user(), await self.user('bob')
        entries = [
            (alice['id'], '2026-10-08T20:30:00Z', 'Speech', {'passed': False}),
            (alice['id'], '2026-10-08T21:30:00Z', 'Speech', {'passed': False}),
            (alice['id'], '2026-10-08T22:30:00Z', 'Retry', {'passed': True}),
            (alice['id'], '2026-10-10T08:00:00Z', '', {'passed': False}),
            (alice['id'], '2026-10-10T09:00:00Z', 'Unfinished', None),
            (bob['id'], '2026-10-10T08:00:00Z', 'Other user', {'passed': True}),
        ]
        for owner, timestamp, transcript, analysis in entries:
            record = await storage.save_attempt(self.record(owner, transcript=transcript, analysis=analysis))
            async with self.connection() as conn:
                await conn.execute('UPDATE attempts SET created_at = %s WHERE id = %s', (timestamp, record['id']))
        instant = datetime(2026, 10, 10, 12, tzinfo=timezone.utc)
        with patch('storage.datetime') as clock:
            clock.now.side_effect = lambda zone: instant.astimezone(zone)
            result = await storage.get_streak(alice['id'], 'Africa/Nairobi')
            utc = await storage.get_streak(alice['id'], 'UTC')
        self.assertEqual(result['current_streak'], 2)
        self.assertEqual(result['total_practice_days'], 2)
        self.assertFalse(result['practiced_today'])
        self.assertEqual(utc['current_streak'], 0)
        self.assertEqual(utc['total_practice_days'], 1)

    async def test_streak_dst_transition_counts_calendar_days(self):
        user = await self.user()
        for timestamp in ['2026-03-07T17:00:00Z', '2026-03-08T06:30:00Z', '2026-03-08T07:30:00Z']:
            record = await storage.save_attempt(self.record(user['id']))
            async with self.connection() as conn:
                await conn.execute('UPDATE attempts SET created_at = %s WHERE id = %s', (timestamp, record['id']))
        with patch('storage.datetime') as clock:
            clock.now.side_effect = lambda zone: datetime(2026, 3, 9, 12, tzinfo=timezone.utc).astimezone(zone)
            result = await storage.get_streak(user['id'], 'America/New_York')
        self.assertEqual(result['current_streak'], 2)
        self.assertEqual(result['total_practice_days'], 2)

    async def test_import_dry_run_repeat_and_atomic_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            user = {'id': 'legacy-user', 'google_id': 'legacy-google', 'name': 'Legacy',
                    'email': 'legacy@example.test', 'created_at': '2026-01-01T00:00:00Z',
                    'last_seen_at': '2026-01-01T00:00:00Z'}
            record = {'id': 'legacy-attempt', 'user_id': user['id'], 'topic': 'Test',
                      'side': 'for', 'created_at': user['created_at'], 'analysis': None}
            (path / 'users.json').write_text(json.dumps([user]))
            (path / 'transcripts.json').write_text(json.dumps([record]))
            self.assertEqual(await import_json.import_records(path), {'users': 1, 'attempts': 1})
            self.assertIsNone(await storage.get_user(user['id']))
            await import_json.import_records(path, apply=True)
            self.assertEqual(await import_json.import_records(path, apply=True), {'users': 0, 'attempts': 0})
            self.assertEqual((await storage.get_attempt(user['id'], record['id']))['id'], record['id'])
            # A missing owner fails the entire batch, including earlier inserts.
            (path / 'transcripts.json').write_text(json.dumps([
                {**record, 'id': 'would-insert'},
                {**record, 'id': 'invalid-owner', 'user_id': 'missing'},
            ]))
            with self.assertRaises(database.DatabaseUnavailable):
                await import_json.import_records(path, apply=True)
            self.assertIsNone(await storage.get_attempt(user['id'], 'would-insert'))


class CursorTests(unittest.TestCase):
    def test_rejects_malformed_cursors(self):
        for value in ('bad!', 'e30=', 'WzEsMl0=', 'bnVsbA=='):
            with self.subTest(value=value), self.assertRaises(ValueError):
                storage.decode_cursor(value)
