from collections.abc import Generator
from contextlib import contextmanager

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from bioma_worker.config import get_settings


@contextmanager
def connect() -> Generator[Connection, None, None]:
    with psycopg.connect(
        get_settings().database_url,
        row_factory=dict_row,
        connect_timeout=5,
    ) as conn:
        yield conn
