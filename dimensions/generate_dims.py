## generate_dims.py
## Generates dim_user (used later to build dim_individual via generate_facts.py)
## Must be executed BEFORE generate_facts.py
##

import uuid
import random
from datetime import date, datetime, timedelta
from faker import Faker
from core.db import get_connection, execute_batch_insert
from core.config import (
    N_USERS, OFFICE_WEIGHTS,
    N_INDIVIDUALS, COUNTRY_WEIGHTS, PROCESS_STATUS_WEIGHTS,
    LEGAL_STATUS_WEIGHTS, BIOMETRICS_RATE,
    DATE_START, DATE_END,
)

fake_en = Faker('en_US')   # English names for individuals
fake    = Faker()           # General faker for users


# ── dim_user ──────────────────────────────────────────────────────────────────

def generate_dim_users(conn):
    print("Generating dim_user...")

    with conn.cursor() as cur:
        cur.execute("SELECT office_id, office_name FROM dim_office ORDER BY office_id")
        offices = cur.fetchall()

    office_ids   = [o[0] for o in offices]
    office_names = [o[1] for o in offices]
    weights      = [OFFICE_WEIGHTS[name] for name in office_names]

    records = []
    for _ in range(N_USERS):
        office_id = random.choices(office_ids, weights=weights, k=1)[0]
        records.append((
            str(uuid.uuid4()).upper(),
            fake.name(),
            office_id,
        ))

    query = """
        INSERT INTO dim_user (user_id, username, office_id)
        VALUES (%s, %s, %s)
        ON CONFLICT (user_id) DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} users inserted.")
    return [r[0] for r in records]


# ── Demographics helpers ──────────────────────────────────────────────────────

SEX_WEIGHTS = ['F'] * 52 + ['M'] * 48

AGE_BUCKETS = [
    (18, 50,  0.60),
    (5,  17,  0.25),
    (0,  4,   0.10),
    (51, 80,  0.05),
]

REFERENCE_DATE = date(2022, 6, 15)


def random_dob():
    bucket = random.choices(AGE_BUCKETS, weights=[b[2] for b in AGE_BUCKETS], k=1)[0]
    age_days = random.randint(bucket[0] * 365, bucket[1] * 365)
    return REFERENCE_DATE - timedelta(days=age_days)


def generate_full_name(sex):
    if sex == 'F':
        first  = fake_en.first_name_female()
        middle = fake_en.first_name_female()
    else:
        first  = fake_en.first_name_male()
        middle = fake_en.first_name_male()
    last1 = fake_en.last_name()
    last2 = fake_en.last_name()
    return f"{first} {middle} {last1} {last2}"


def later_datetime(base_date, min_days=1, max_days=180):
    """Returns a random datetime strictly after base_date, capped at DATE_END."""
    delta = random.randint(min_days, max_days)
    result_date = base_date + timedelta(days=delta)
    result_date = min(result_date, DATE_END)
    secs = random.randint(0, 86399)
    return datetime.combine(result_date, datetime.min.time()) + timedelta(seconds=secs)


# ── dim_individual ────────────────────────────────────────────────────────────

def generate_individuals(conn, rg_ids, user_ids):
    """
    Called from generate_facts.py — exposed here so fresh installs
    can also populate demographics in a single pass.

    rg_ids: list of (rg_id, rg_created_at) tuples
    Returns: list of (ind_id, created_at) tuples
    """
    print("Generating dim_individual...")

    country_keys    = list(COUNTRY_WEIGHTS.keys())
    country_weights = list(COUNTRY_WEIGHTS.values())
    status_keys     = list(PROCESS_STATUS_WEIGHTS.keys())
    status_weights  = list(PROCESS_STATUS_WEIGHTS.values())
    legal_keys      = list(LEGAL_STATUS_WEIGHTS.keys())
    legal_weights   = list(LEGAL_STATUS_WEIGHTS.values())

    records        = []
    individual_ids = []   # list of (ind_id, created_at)

    for i in range(N_INDIVIDUALS):
        ind_id = f"IND-{str(i + 1).zfill(6)}"

        sex            = random.choice(SEX_WEIGHTS)
        country_code   = random.choices(country_keys,  weights=country_weights,  k=1)[0]
        process_status = random.choices(status_keys,   weights=status_weights,   k=1)[0]
        legal_status   = random.choices(legal_keys,    weights=legal_weights,    k=1)[0]

        # ── Business rule: individual created AFTER its registration group ──
        rg_id, rg_created_at = random.choice(rg_ids)
        created_at = later_datetime(rg_created_at.date(), min_days=1, max_days=365)

        created_by = random.choice(user_ids) if random.random() > 0.05 else None

        # Append AFTER created_at is defined
        individual_ids.append((ind_id, created_at))

        records.append((
            ind_id,
            str(rg_id),
            process_status,
            country_code,
            legal_status,
            random.random() < BIOMETRICS_RATE,
            generate_full_name(sex),
            sex,
            random_dob(),
            created_at,
            created_at.date(),
            created_by,
        ))

    query = """
        INSERT INTO dim_individual (
            individual_id, rg_id, process_status, country_origin,
            legal_status, has_biometrics,
            full_name, sex, date_of_birth,
            created_at, created_date, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} individuals inserted.")
    return individual_ids   # list of (ind_id, created_at)


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = get_connection()
    try:
        user_ids = generate_dim_users(conn)
        print("\nDimensions generated successfully.")
        print("Note: run generate_facts.py next to create registration groups and all facts.")
    finally:
        conn.close()