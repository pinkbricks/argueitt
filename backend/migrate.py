"""Run with `python migrate.py`. Each numbered SQL file runs once, atomically."""

import asyncio
import hashlib
from pathlib import Path

from database import DatabaseUnavailable, connection


async def migrate():
    async with connection(migration=True) as conn:
        # Transaction-scoped lock also works through transaction pooling.
        await conn.execute('SELECT pg_advisory_xact_lock(734819220)')
        await conn.execute('''CREATE TABLE IF NOT EXISTS schema_migrations (
            version text PRIMARY KEY,
            checksum text NOT NULL,
            applied_at timestamptz NOT NULL DEFAULT now()
        )''')
        applied = {row['version']: row['checksum'] for row in
                   await (await conn.execute('SELECT version, checksum FROM schema_migrations')).fetchall()}
        for path in sorted(Path(__file__).with_name('migrations').glob('*.sql')):
            sql = path.read_text()
            checksum = hashlib.sha256(sql.encode()).hexdigest()
            if path.name in applied:
                if applied[path.name] != checksum:
                    raise ValueError(f'Applied migration was modified: {path.name}')
                continue
            await conn.execute(sql)
            await conn.execute('INSERT INTO schema_migrations (version, checksum) VALUES (%s, %s)',
                               (path.name, checksum))
    print('Database migrations are up to date.')


if __name__ == '__main__':
    try:
        asyncio.run(migrate())
    except (DatabaseUnavailable, ValueError) as exc:
        raise SystemExit(f'Migration failed: {exc}') from None
