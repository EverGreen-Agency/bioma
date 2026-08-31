from collections.abc import Generator
from contextlib import contextmanager

import psycopg
from psycopg import Connection
from psycopg.rows import dict_row

from bioma_api.config import get_settings


@contextmanager
def connect() -> Generator[Connection, None, None]:
    settings = get_settings()
    with psycopg.connect(settings.database_url, row_factory=dict_row, connect_timeout=5) as conn:
        yield conn
