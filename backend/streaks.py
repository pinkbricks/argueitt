"""Calendar-day streaks derived from completed practice, never from scores."""

from datetime import date, timedelta


def summarize_streak(practice_days: list[date], today: date) -> dict:
    days = sorted({day for day in practice_days if day <= today})
    day_set = set(days)
    longest = run = 0
    previous = None
    for day in days:
        run = run + 1 if previous and day == previous + timedelta(days=1) else 1
        longest = max(longest, run)
        previous = day

    # Yesterday's streak remains alive until the user has had all of today
    # to practise. A missed full calendar day resets only the current streak.
    current = 0
    day = today if today in day_set else today - timedelta(days=1)
    while day in day_set:
        current += 1
        day -= timedelta(days=1)

    return {
        'current_streak': current,
        'longest_streak': longest,
        'total_practice_days': len(days),
        'practiced_today': today in day_set,
        'today': today.isoformat(),
        'last_practice_date': days[-1].isoformat() if days else None,
        'week': [
            {'date': (today - timedelta(days=offset)).isoformat(),
             'practiced': today - timedelta(days=offset) in day_set}
            for offset in range(6, -1, -1)
        ],
    }
