## reset_and_seed.py
## Drops every table in the public schema, recreates it from sql/01_schema.sql,
## seeds catalogs from sql/02_catalogs.sql, then runs the full Stage 1 pipeline.
##
## Usage (from project root):
##   python reset_and_seed.py
##
## WARNING: DESTROYS all data in the configured database. Local/dev only.

import sys
from pathlib import Path

from core.db import get_connection
from dimensions.generate_dims import generate_dim_users
from facts.generate_facts import (
    load_refs,
    generate_registration_groups,
    generate_individuals,
    generate_admissibility,
    generate_adm_interviews,
    generate_adm_decisions,
    generate_eligibilities,
    generate_elg_recommendations,
    generate_elg_reviews,
    generate_appeal_recommendations,
    generate_appeal_decisions,
    generate_certificates,
)

ROOT       = Path(__file__).resolve().parent
SCHEMA_SQL = ROOT / "sql" / "01_schema.sql"
CATALOG_SQL = ROOT / "sql" / "02_catalogs.sql"


def confirm_reset(dbname):
    print("=" * 60)
    print(f"  WARNING: This will DELETE ALL DATA in '{dbname}'.")
    print("=" * 60)
    if input("  Type 'yes' to continue: ").strip().lower() != "yes":
        print("Aborted.")
        sys.exit(0)


def drop_all_tables(conn):
    print("Dropping all tables in public schema...")
    with conn.cursor() as cur:
        cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
        tables = [r[0] for r in cur.fetchall()]
        if tables:
            quoted = ", ".join(f'"{t}"' for t in tables)
            cur.execute(f"DROP TABLE IF EXISTS {quoted} CASCADE")
    conn.commit()
    print(f"  ✓ Dropped {len(tables)} tables.")


def run_sql_file(conn, path, label):
    print(f"{label} ({path.name})...")
    sql = path.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()
    print("  ✓ Done.")


if __name__ == "__main__":
    from core.config import DB
    confirm_reset(DB["dbname"])

    conn = get_connection()
    try:
        drop_all_tables(conn)
        run_sql_file(conn, SCHEMA_SQL,  "Recreating schema")
        run_sql_file(conn, CATALOG_SQL, "Seeding catalogs")

        print("\nGenerating dimensions...")
        generate_dim_users(conn)

        print("\nLoading reference data...")
        refs = load_refs(conn)

        print("\nGenerating facts...")
        rg_ids         = generate_registration_groups(conn, refs)
        individual_ids = generate_individuals(conn, refs, rg_ids)

        admissibility_ids = generate_admissibility(conn, refs, individual_ids)
        generate_adm_interviews(conn, refs, admissibility_ids)
        generate_adm_decisions(conn, refs, admissibility_ids)

        eligibility_ids = generate_eligibilities(conn, refs, individual_ids)
        rec_elg_ids     = generate_elg_recommendations(conn, refs, eligibility_ids)
        generate_elg_reviews(conn, refs, eligibility_ids)

        appeal_rec_ids = generate_appeal_recommendations(conn, refs, rec_elg_ids)
        generate_appeal_decisions(conn, refs, appeal_rec_ids)

        generate_certificates(conn, refs, individual_ids)

        print("\n✓ Database reset and seeded successfully.")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        raise
    finally:
        conn.close()
