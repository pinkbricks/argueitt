"""Short async transactions; DATABASE_URL should use Neon's pooled endpoint."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv(Path(__file__).with_name('.env'))


class DatabaseUnavailable(Exception):
    pass


@asynccontextmanager
async def connection(*, migration=False):
    url = (os.getenv('DATABASE_MIGRATION_URL') if migration else None) or os.getenv('DATABASE_URL')
    if not url:
        raise DatabaseUnavailable('DATABASE_URL is not configured')
    try:
        async with await psycopg.AsyncConnection.connect(
            url, row_factory=dict_row, connect_timeout=10, prepare_threshold=None,
        ) as conn:
            await conn.execute("SET LOCAL statement_timeout = '15s'")
            yield conn
    except psycopg.Error as exc:
        # Database errors can contain credentials or private row contents.
        raise DatabaseUnavailable(type(exc).__name__) from None
