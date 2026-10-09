"""API regression tests: no network, Google credentials, or Gemini calls."""

import os
import unittest
import uuid
from unittest.mock import AsyncMock, patch

os.environ['SESSION_SECRET'] = 'test-only-session-secret'
os.environ['ENV'] = 'test'

from httpx import ASGITransport, AsyncClient

import main
from database import DatabaseUnavailable


USER = {'id': 'alice', 'email': 'alice@example.test', 'name': 'Alice', 'picture': ''}
WORDS = [{'text': 'Hello', 'start_offset': '0.1s', 'end_offset': '0.8s'}]
SCORE = {
    'challenge_type': 'answer_the_unexpected', 'framework_name': 'SPONTANEOUS_ANSWER',
    'model_version': 'test', 'functions': {}, 'total_score': 0, 'passed': False,
    'strongest_moment': '', 'weakest_function_id': '', 'feedback_pointer': 'Try again',
    'next_focus': 'State your point',
}


class ApiTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.client = AsyncClient(transport=ASGITransport(app=main.app), base_url="http://testserver")
        self.addAsyncCleanup(self.client.aclose)
        self.rows = {}
        self.get_request = self.start_patch('main.storage.get_request', AsyncMock(side_effect=self.lookup))
        self.save = self.start_patch('main.storage.save_attempt', AsyncMock(side_effect=self.store))
        self.transcribe = self.start_patch('main.transcribe_words', AsyncMock(return_value=('Hello', WORDS)))
        self.score = self.start_patch('main.score_response', AsyncMock(return_value=SCORE))
        self.start_patch('main.get_client', return_value=object())

    def start_patch(self, target, *args, **kwargs):
        patcher = patch(target, *args, **kwargs)
        result = patcher.start()
        self.addCleanup(patcher.stop)
        return result

    async def lookup(self, user_id, request_id):
        return self.rows.get((user_id, request_id))

    async def store(self, record):
        key = (record['user_id'], record['request_id'])
        return self.rows.setdefault(key, {**record, 'id': uuid.uuid4().hex})

    async def sign_in(self):
        with patch('main.auth.verify_credential', return_value={'sub': 'google-alice'}), \
             patch('main.auth.upsert_user', AsyncMock(return_value=USER)):
            response = await self.client.post('/api/auth/google', json={'credential': 'test'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), USER)

    async def analyze(self, request_id=None, **fields):
        return await self.client.post('/api/analyze', data={
            'topic': 'Example topic', 'side': 'for',
            'request_id': request_id or str(uuid.uuid4()), **fields,
        }, files={'audio': ('speech.wav', b'test audio', 'audio/wav')})

    async def test_guest_practice_does_not_require_database(self):
        self.get_request.side_effect = DatabaseUnavailable('offline')
        response = await self.analyze()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['persistence_status'], 'guest')
        self.get_request.assert_not_awaited()
        self.save.assert_not_awaited()
        self.assertEqual((await self.client.get('/api/attempts')).status_code, 401)

    async def test_replayed_request_returns_saved_result_without_model_call(self):
        await self.sign_in()
        request_id = str(uuid.uuid4())
        first = await self.analyze(request_id)
        second = await self.analyze(request_id)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(first.json()['persistence_status'], 'saved')
        self.assertTrue(first.json()['attempt_id'])
        self.transcribe.assert_awaited_once()
        self.assertEqual(len(self.rows), 1)

    async def test_same_key_different_payload_rejected(self):
        await self.sign_in()
        request_id = str(uuid.uuid4())
        await self.analyze(request_id)
        response = await self.analyze(request_id, topic='A different topic')
        self.assertEqual(response.status_code, 409)
        self.transcribe.assert_awaited_once()

    async def test_database_failure_still_returns_feedback(self):
        await self.sign_in()
        self.get_request.side_effect = DatabaseUnavailable('offline')
        self.save.side_effect = DatabaseUnavailable('offline')
        response = await self.analyze()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['transcript'], 'Hello')
        self.assertEqual(response.json()['persistence_status'], 'not_saved')
        self.assertIsNone(response.json()['attempt_id'])

    async def test_empty_speech_is_saved(self):
        await self.sign_in()
        self.transcribe.return_value = ('', [])
        response = await self.analyze()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['persistence_status'], 'saved')
        self.assertEqual(response.json()['delivery_metrics']['word_count'], 0)
        self.score.assert_not_awaited()

    async def test_retry_uses_owned_attempt_and_stored_focus(self):
        await self.sign_in()
        with patch('main.storage.get_attempt', AsyncMock(return_value={
            'id': 'previous', 'topic': 'Example topic', 'side': 'for',
            'analysis': {'next_focus': 'Stored focus'},
        })) as lookup:
            response = await self.analyze(previous_attempt_id='previous', previous_next_focus='Untrusted focus')
        self.assertEqual(response.status_code, 200)
        lookup.assert_awaited_once_with('alice', 'previous')
        self.assertEqual(self.score.call_args.kwargs['previous_next_focus'], 'Stored focus')
        self.assertEqual(self.save.call_args.args[0]['previous_attempt_id'], 'previous')

    async def test_other_users_retry_is_not_accessible(self):
        await self.sign_in()
        with patch('main.storage.get_attempt', AsyncMock(return_value=None)):
            response = await self.analyze(previous_attempt_id='someone-elses-attempt')
        self.assertEqual(response.status_code, 404)
        self.transcribe.assert_not_awaited()

    async def test_retry_lookup_outage_does_not_silently_drop_link(self):
        await self.sign_in()
        with patch('main.storage.get_attempt', AsyncMock(side_effect=DatabaseUnavailable('offline'))):
            response = await self.analyze(previous_attempt_id='previous')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['persistence_status'], 'not_saved')
        self.save.assert_not_awaited()

    async def test_history_uses_cookie_owner_and_pagination(self):
        await self.sign_in()
        with patch('main.storage.list_attempts', AsyncMock(return_value={'attempts': [], 'next_cursor': None})) as listing:
            response = await self.client.get('/api/attempts?limit=5&cursor=example&user_id=bob')
        self.assertEqual(response.status_code, 200)
        listing.assert_awaited_once_with('alice', 5, 'example')
        self.assertEqual((await self.client.get('/api/attempts?limit=101')).status_code, 422)

    async def test_streak_requires_sign_in_and_uses_cookie_owner(self):
        self.assertEqual((await self.client.get('/api/streak')).status_code, 401)
        await self.sign_in()
        with patch('main.storage.get_streak', AsyncMock(return_value={'current_streak': 3})) as lookup:
            response = await self.client.get('/api/streak?timezone=Africa/Nairobi&user_id=bob')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['current_streak'], 3)
        lookup.assert_awaited_once_with('alice', 'Africa/Nairobi')

    async def test_streak_validates_timezone_and_handles_database_outage(self):
        await self.sign_in()
        self.assertEqual((await self.client.get('/api/streak?timezone=Invalid/Zone')).status_code, 400)
        with patch('main.storage.get_streak', AsyncMock(side_effect=DatabaseUnavailable('offline'))):
            self.assertEqual((await self.client.get('/api/streak')).status_code, 503)

    async def test_invalid_cursor_and_history_outage(self):
        await self.sign_in()
        self.assertEqual((await self.client.get('/api/attempts?cursor=bad!')).status_code, 400)
        with patch('main.storage.list_attempts', AsyncMock(side_effect=DatabaseUnavailable('offline'))):
            response = await self.client.get('/api/attempts')
        self.assertEqual(response.status_code, 503)

    async def test_cookie_survives_database_outage_but_signout_clears_it(self):
        await self.sign_in()
        with patch('main.storage.get_user', AsyncMock(side_effect=DatabaseUnavailable('offline'))):
            self.assertEqual((await self.client.get('/api/auth/me')).status_code, 503)
        with patch('main.storage.get_user', AsyncMock(return_value=USER)):
            self.assertEqual((await self.client.get('/api/auth/me')).json()['user'], USER)
        await self.client.post('/api/auth/sign-out')
        self.assertEqual((await self.client.get('/api/auth/me')).json(), {'user': None})

    async def test_rejects_invalid_side_and_request_id(self):
        self.assertEqual((await self.analyze(side='other')).status_code, 422)
        self.assertEqual((await self.analyze(request_id='not-a-uuid')).status_code, 422)
        self.transcribe.assert_not_awaited()


if __name__ == '__main__':
    unittest.main()
