import unittest
from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import storage
from streaks import summarize_streak


class StreakTests(unittest.TestCase):
    today = date(2026, 10, 9)

    def summary(self, *offsets):
        return summarize_streak([self.today - timedelta(days=n) for n in offsets], self.today)

    def test_new_user(self):
        result = self.summary()
        self.assertEqual(result['current_streak'], 0)
        self.assertEqual(result['longest_streak'], 0)
        self.assertEqual(result['total_practice_days'], 0)
        self.assertIsNone(result['last_practice_date'])
        self.assertFalse(result['practiced_today'])

    def test_first_practice_and_same_day_retries(self):
        result = self.summary(0, 0, 0)
        self.assertEqual(result['current_streak'], 1)
        self.assertEqual(result['longest_streak'], 1)
        self.assertEqual(result['total_practice_days'], 1)
        self.assertTrue(result['practiced_today'])

    def test_consecutive_days_are_order_independent(self):
        result = self.summary(2, 0, 1, 2)
        self.assertEqual(result['current_streak'], 3)
        self.assertEqual(result['longest_streak'], 3)

    def test_yesterday_streak_survives_until_end_of_today(self):
        result = self.summary(3, 2, 1)
        self.assertEqual(result['current_streak'], 3)
        self.assertFalse(result['practiced_today'])
        self.assertEqual(result['last_practice_date'], '2026-10-08')

    def test_missing_a_whole_day_breaks_streak_but_preserves_best(self):
        result = self.summary(5, 4, 3, 2)
        self.assertEqual(result['current_streak'], 0)
        self.assertEqual(result['longest_streak'], 4)
        self.assertEqual(self.summary(5, 4, 3, 2, 0)['current_streak'], 1)

    def test_best_can_be_an_older_streak(self):
        result = self.summary(12, 11, 10, 9, 2, 1, 0)
        self.assertEqual(result['current_streak'], 3)
        self.assertEqual(result['longest_streak'], 4)
        self.assertEqual(result['total_practice_days'], 7)

    def test_long_history_is_not_limited_to_one_page(self):
        result = self.summary(*range(45))
        self.assertEqual(result['current_streak'], 45)
        self.assertEqual(result['longest_streak'], 45)

    def test_calendar_boundaries(self):
        for today in (date(2026, 1, 1), date(2024, 3, 1), date(2026, 3, 9), date(2026, 11, 2)):
            with self.subTest(today=today):
                result = summarize_streak([today - timedelta(days=n) for n in range(3)], today)
                self.assertEqual(result['current_streak'], 3)

    def test_week_is_seven_days_ending_today(self):
        result = self.summary(0, 2, 6, 7)
        self.assertEqual(len(result['week']), 7)
        self.assertEqual(result['week'][0], {'date': '2026-10-03', 'practiced': True})
        self.assertEqual(result['week'][-1], {'date': '2026-10-09', 'practiced': True})
        self.assertEqual(sum(d['practiced'] for d in result['week']), 3)

    def test_future_dates_do_not_earn_a_streak(self):
        result = self.summary(-1, -2)
        self.assertEqual(result['current_streak'], 0)
        self.assertEqual(result['total_practice_days'], 0)


class TimezoneTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_zone_rejected_before_query(self):
        with patch('storage.connection') as connection:
            for zone in ('Not/A_Zone', '../etc/passwd', '/etc/passwd'):
                with self.subTest(zone=zone), self.assertRaises(ValueError):
                    await storage.get_streak('alice', zone)
            connection.assert_not_called()

    async def test_local_date_not_server_date(self):
        from datetime import datetime, timezone
        instant = datetime(2026, 10, 8, 21, 30, tzinfo=timezone.utc)
        conn = AsyncMock()
        conn.execute.return_value.fetchall.return_value = [{'practice_day': date(2026, 10, 9)}]
        with patch('storage.connection') as connection, patch('storage.datetime') as clock:
            connection.return_value.__aenter__.return_value = conn
            clock.now.side_effect = lambda zone: instant.astimezone(zone)
            result = await storage.get_streak('alice', 'Africa/Nairobi')
        self.assertEqual(result['today'], '2026-10-09')
        self.assertTrue(result['practiced_today'])
        self.assertEqual(conn.execute.call_args.args[1], ('Africa/Nairobi', 'alice'))
