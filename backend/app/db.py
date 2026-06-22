from typing import Generator

import psycopg2
import psycopg2.pool

from app.config import get_settings

pool: psycopg2.pool.ThreadedConnectionPool | None = None


def init_pool() -> None:
    global pool
    settings = get_settings()
    pool = psycopg2.pool.ThreadedConnectionPool(
        minconn=1,
        maxconn=10,
        dsn=settings.DATABASE_URL,
    )


def get_db_conn() -> Generator:
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)
