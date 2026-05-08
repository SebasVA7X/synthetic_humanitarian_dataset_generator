## db.py
## PostgreSQL connection using psycopg2

import psycopg2
from psycopg2.extras import execute_batch
from core.config import DB


def get_connection():
    return psycopg2.connect(**DB)


def execute_batch_insert(conn, query, records, page_size=500):
    """Batch insert with progress output."""
    with conn.cursor() as cur:
        execute_batch(cur, query, records, page_size=page_size)
    conn.commit()