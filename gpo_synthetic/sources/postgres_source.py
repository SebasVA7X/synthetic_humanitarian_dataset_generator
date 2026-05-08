"""Postgres source: fetches person records from dim_individual."""
from typing import List, Dict, Any

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor

from gpo_synthetic.config import PostgresConfig


def fetch_dim_individual(cfg: PostgresConfig) -> pd.DataFrame:
    """
    Fetch the full dim_individual table from Postgres.
    Expected columns: full_name, sex, date_of_birth, country_origin.
    Other columns are kept as-is.
    """
    query = f"SELECT * FROM {cfg.fqtn};"

    conn = psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        dbname=cfg.database,
        user=cfg.user,
        password=cfg.password,
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query)
            rows: List[Dict[str, Any]] = cur.fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(rows)

    required = {"full_name", "sex", "date_of_birth", "country_origin"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"dim_individual is missing required columns: {missing}")

    return df


def fetch_dim_individual_from_csv(csv_path: str) -> pd.DataFrame:
    """
    Fallback loader for local development without Postgres.
    Expects a CSV with at least: full_name, sex, date_of_birth, country_origin.
    """
    df = pd.read_csv(csv_path)

    required = {"full_name", "sex", "date_of_birth", "country_origin"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    return df
