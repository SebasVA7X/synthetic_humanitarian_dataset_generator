## generate_facts.py
## Generates all facts and remaining dimension tables
## Run after generate_dims.py
##
## Execution order for fresh install (run from project root):
##   1. python -m dimensions.generate_dims   → dim_user
##   2. python -m facts.generate_facts       → dim_registration_group, dim_individual (with demographics), all facts
##
## Date business rules enforced:
##   - dim_registration_group  → any date in range
##   - dim_individual          → AFTER its rg created_at          (generate_dims.py)
##   - fact_admissibility      → AFTER its individual created_at
##   - fact_certificate        → AFTER its individual created_at
##   - fact_eligibility            → AFTER its individual created_at
##   - fact_adm_interview          → AFTER its admissibility created_at
##   - fact_adm_decision           → AFTER its admissibility created_at
##   - fact_elg_recommendation     → AFTER its eligibility created_at
##   - fact_elg_review             → AFTER its eligibility created_at
##   - fact_appeal_recommendation  → AFTER its eligibility created_at
##   - fact_appeal_decision    → AFTER its appeal_recommendation date

import uuid
import random
from datetime import date, datetime, timedelta
from faker import Faker
from core.db import get_connection, execute_batch_insert
from core.config import *
from dimensions.generate_dims import (
    generate_individuals as _generate_individuals,
    random_dob, generate_full_name,
)

fake = Faker()


# ── Helpers ───────────────────────────────────────────────────────────────────

def random_datetime(start=DATE_START, end=DATE_END):
    delta = (end - start).days
    random_days = random.randint(0, delta)
    random_secs = random.randint(0, 86399)
    return datetime.combine(start, datetime.min.time()) + timedelta(days=random_days, seconds=random_secs)


def random_date(start=DATE_START, end=DATE_END):
    return random_datetime(start, end).date()


def later_date(base_date, min_days=1, max_days=180):
    delta = random.randint(min_days, max_days)
    result = base_date + timedelta(days=delta)
    return min(result, DATE_END)


def later_datetime(base_date, min_days=1, max_days=180):
    d = later_date(base_date, min_days, max_days)
    secs = random.randint(0, 86399)
    return datetime.combine(d, datetime.min.time()) + timedelta(seconds=secs)


# ── Load reference data ───────────────────────────────────────────────────────

def load_refs(conn):
    refs = {}

    with conn.cursor() as cur:
        cur.execute("SELECT office_id, office_name FROM dim_office")
        offices = cur.fetchall()

        refs["office_ids"] = [o[0] for o in offices]
        refs["office_names"] = [o[1] for o in offices]
        refs["office_weights"] = [
            OFFICE_WEIGHTS.get(n, 1)
            for n in refs["office_names"]
        ]

        cur.execute("SELECT user_id FROM dim_user")
        refs["user_ids"] = [r[0] for r in cur.fetchall()]

    if not refs["user_ids"]:
        raise ValueError(
            "No user_ids found in dim_user. "
            "Run generate_dims.py before generate_facts.py."
        )

    if not refs["office_names"]:
        raise ValueError(
            "No office_names found in dim_office."
        )

    return refs


# ── dim_registration_group ────────────────────────────────────────────────────

def generate_registration_groups(conn, refs):
    print("Generating dim_registration_group...")
    records = []
    rg_ids  = []   # list of (rg_id, created_at)

    for _ in range(N_REGISTRATION_GROUPS):
        rg_id      = uuid.uuid4()
        created_at = random_datetime()
        rg_ids.append((rg_id, created_at))
        office_id = random.choices(refs["office_ids"], weights=refs["office_weights"], k=1)[0]
        records.append((str(rg_id), office_id, created_at))

    query = """
        INSERT INTO dim_registration_group (rg_id, office_id, created_at)
        VALUES (%s, %s, %s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} registration groups inserted.")
    return rg_ids   # list of (rg_id, created_at)


# ── dim_individual ────────────────────────────────────────────────────────────
# Delegates to generate_dims.py — includes full_name, sex, date_of_birth
# Returns: list of (ind_id, created_at)

def generate_individuals(conn, refs, rg_ids):
    return _generate_individuals(conn, rg_ids, refs["user_ids"])


# ── fact_admissibility ────────────────────────────────────────────────────────

def generate_admissibility(conn, refs, individual_ids):
    """
    individual_ids: list of (ind_id, created_at)
    Returns: list of (adm_id, ind_id, created_at)
    """
    print("Generating fact_admissibility...")

    adm_individuals  = random.sample(individual_ids, N_ADMISSIBILITY)
    records          = []
    admissibility_ids = []   # list of (adm_id, ind_id, created_at)

    status_keys = list(PROCESS_STATUS_WEIGHTS.keys())
    status_wts  = list(PROCESS_STATUS_WEIGHTS.values())
    dec_keys    = list(ADMISSIBILITY_DECISION_WEIGHTS.keys())
    dec_wts     = list(ADMISSIBILITY_DECISION_WEIGHTS.values())

    for i, (ind_id, ind_created_at) in enumerate(adm_individuals):
        adm_id = f"ADM-{str(i + 1).zfill(6)}"

        # Business rule: admissibility AFTER individual
        created_at = later_datetime(ind_created_at.date(), min_days=1, max_days=180)

        has_bps  = random.random() > 0.25
        bps      = random.choices(dec_keys, weights=dec_wts, k=1)[0] if has_bps else None
        bps_dt   = later_datetime(created_at.date()) if has_bps else None
        bps_date = bps_dt.date() if bps_dt else None

        admissibility_ids.append((adm_id, ind_id, created_at))
        records.append((
            adm_id, ind_id,
            random.choices(status_keys, weights=status_wts, k=1)[0],
            bps, bps_date, bps_dt,
            created_at, created_at.date(),
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_admissibility (
            admissibility_id, individual_id, process_status,
            business_process_status, bps_date, bps_datetime,
            created_at, created_date, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} admissibility assessments inserted.")
    return admissibility_ids   # list of (adm_id, ind_id, created_at)


# ── fact_adm_interview ────────────────────────────────────────────────────────

def generate_adm_interviews(conn, refs, admissibility_ids):
    """
    admissibility_ids: list of (adm_id, ind_id, created_at)
    """
    print("Generating fact_adm_interview...")
    sampled = random.sample(admissibility_ids, min(N_ADM_INTERVIEWS, len(admissibility_ids)))
    records = []

    for adm_id, _ind_id, adm_created_at in sampled:
        # Business rule: interview AFTER admissibility
        dt = later_datetime(adm_created_at.date(), min_days=1, max_days=90)
        records.append((
            str(uuid.uuid4()), adm_id, dt, dt.date(),
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_adm_interview (
            interview_id, admissibility_id, interview_datetime,
            interview_date, created_by
        ) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} admissibility interviews inserted.")


# ── fact_adm_decision ─────────────────────────────────────────────────────────

def generate_adm_decisions(conn, refs, admissibility_ids):
    """
    admissibility_ids: list of (adm_id, ind_id, created_at)
    """
    print("Generating fact_adm_decision...")
    sampled  = random.sample(admissibility_ids, min(N_ADM_DECISIONS, len(admissibility_ids)))
    dec_keys = list(ADMISSIBILITY_DECISION_WEIGHTS.keys())
    dec_wts  = list(ADMISSIBILITY_DECISION_WEIGHTS.values())
    basis_keys = [
        "BASIS_UNFOUNDED_B", "BASIS_ADMITTED", "BASIS_FRAUD_C",
        "BASIS_EXTEMP", "BASIS_FRAUD_A", "BASIS_UNFOUNDED_C",
        "BASIS_UNFOUNDED_A", "BASIS_FRAUD_B", "BASIS_EXTEMP_LATE",
    ]
    records = []

    for adm_id, _ind_id, adm_created_at in sampled:
        # Business rule: decision AFTER admissibility
        dt = later_datetime(adm_created_at.date(), min_days=1, max_days=120)
        records.append((
            str(uuid.uuid4()), adm_id,
            random.choices(dec_keys, weights=dec_wts, k=1)[0],
            dt.date(), dt,
            random.choice(basis_keys) if random.random() > 0.15 else None,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_adm_decision (
            decision_id, admissibility_id, decision_code,
            decision_date, decision_datetime, decision_basis_code, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} admissibility decisions inserted.")


# ── fact_eligibility ───────────────────────────────────────────────────────────

def generate_eligibilities(conn, refs, individual_ids):
    """
    individual_ids: list of (ind_id, created_at)
    Returns: list of (elg_id, ind_id, created_at)
    """
    print("Generating fact_eligibility...")
    elg_individuals = random.sample(individual_ids, N_ELIGIBILITIES)
    records          = []
    eligibility_ids   = []   # list of (elg_id, ind_id, created_at)

    proc_keys  = list(PROCESS_TYPE_WEIGHTS.keys())
    proc_wts   = list(PROCESS_TYPE_WEIGHTS.values())
    notif_keys = ["email", "hand_delivery", "mail", "phone", "self_service"]

    for i, (ind_id, ind_created_at) in enumerate(elg_individuals):
        elg_id = f"ELG-{str(i + 1).zfill(6)}"

        # Business rule: eligibility AFTER individual
        created_at = later_datetime(ind_created_at.date(), min_days=1, max_days=180)

        has_notif = random.random() > 0.20
        notif_dt  = later_datetime(created_at.date()) if has_notif else None

        eligibility_ids.append((elg_id, ind_id, created_at))
        records.append((
            elg_id, ind_id,
            random.choices(proc_keys, weights=proc_wts, k=1)[0],
            random.choice(notif_keys) if has_notif else None,
            notif_dt,
            notif_dt.date() if notif_dt else None,
            created_at,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_eligibility (
            eligibility_id, individual_id, process_type_code,
            notification_type_code, notification_date, notification_date_only,
            created_at, created_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} eligibility assessments inserted.")
    return eligibility_ids   # list of (elg_id, ind_id, created_at)


# ── fact_elg_recommendation ──────────────────────────────────────────────────

def generate_elg_recommendations(conn, refs, eligibility_ids):
    """
    eligibility_ids: list of (elg_id, ind_id, created_at)
    Returns: list of elg_id strings (for appeal chain)
    """
    print("Generating fact_elg_recommendation...")
    sampled  = random.sample(eligibility_ids, min(N_ELG_RECOMMENDATIONS, len(eligibility_ids)))
    rec_keys = list(ELG_RECOMMENDATION_WEIGHTS.keys())
    rec_wts  = list(ELG_RECOMMENDATION_WEIGHTS.values())
    reason_keys = [101001, 101002, 101003, 101004, 101005, 101006, 101007]
    records  = []
    rec_elg_ids = []   # list of (elg_id, recommendation_date) for appeal chain

    for elg_id, _ind_id, elg_created_at in sampled:
        # Business rule: recommendation AFTER eligibility
        dt = later_datetime(elg_created_at.date(), min_days=1, max_days=120)
        rec_elg_ids.append((elg_id, dt))
        records.append((
            elg_id,
            random.choices(rec_keys, weights=rec_wts, k=1)[0],
            dt, dt.date(),
            random.choice(reason_keys) if random.random() > 0.10 else None,
            None,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_elg_recommendation (
            eligibility_id, recommendation_code, recommendation_date,
            recommendation_date_only, reason_code, legal_basis, recommended_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} eligibility recommendations inserted.")
    return rec_elg_ids   # list of (elg_id, recommendation_datetime)


# ── fact_elg_review ──────────────────────────────────────────────────────────

def generate_elg_reviews(conn, refs, eligibility_ids):
    """
    eligibility_ids: list of (elg_id, ind_id, created_at)
    """
    print("Generating fact_elg_review...")
    sampled  = random.sample(eligibility_ids, min(N_ELG_REVIEWS, len(eligibility_ids)))
    rev_keys = list(REVIEW_DECISION_WEIGHTS.keys())
    rev_wts  = list(REVIEW_DECISION_WEIGHTS.values())
    cat_keys = ["officer", "senior", "supervisor", "external"]
    records  = []

    for elg_id, _ind_id, elg_created_at in sampled:
        # Business rule: review AFTER eligibility
        dt = later_datetime(elg_created_at.date(), min_days=1, max_days=120)
        records.append((
            elg_id,
            random.choices(rev_keys, weights=rev_wts, k=1)[0],
            dt, dt.date(),
            random.choice(cat_keys),
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_elg_review (
            eligibility_id, review_decision_code, review_date,
            review_date_only, reviewer_category_code, reviewed_by
        ) VALUES (%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} eligibility reviews inserted.")


# ── fact_appeal_recommendation ────────────────────────────────────────────────

def generate_appeal_recommendations(conn, refs, rec_elg_ids):
    """
    rec_elg_ids: list of (elg_id, recommendation_datetime)
    Returns: list of (elg_id, appeal_recommendation_date) for appeal_decision chain
    """
    print("Generating fact_appeal_recommendation...")
    sampled  = random.sample(rec_elg_ids, min(N_APPEAL_RECOMMENDATIONS, len(rec_elg_ids)))
    rec_keys = list(APPEAL_REC_WEIGHTS.keys())
    rec_wts  = list(APPEAL_REC_WEIGHTS.values())
    records  = []
    appeal_rec_ids = []   # list of (elg_id, appeal_date)

    for elg_id, rec_created_at in sampled:
        # Business rule: appeal recommendation AFTER eligibility recommendation
        d = later_date(rec_created_at.date(), min_days=1, max_days=180)
        appeal_rec_ids.append((elg_id, d))
        records.append((
            elg_id, True,
            random.choices(rec_keys, weights=rec_wts, k=1)[0],
            d,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_appeal_recommendation (
            eligibility_id, has_appeal, appeal_recommendation_code,
            appeal_recommendation_date, recommended_by
        ) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} appeal recommendations inserted.")
    return appeal_rec_ids   # list of (elg_id, appeal_recommendation_date)


# ── fact_appeal_decision ──────────────────────────────────────────────────────

def generate_appeal_decisions(conn, refs, appeal_rec_ids):
    """
    appeal_rec_ids: list of (elg_id, appeal_recommendation_date)
    """
    print("Generating fact_appeal_decision...")
    sampled  = random.sample(appeal_rec_ids, min(N_APPEAL_DECISIONS, len(appeal_rec_ids)))
    dec_keys = list(APPEAL_DEC_WEIGHTS.keys())
    dec_wts  = list(APPEAL_DEC_WEIGHTS.values())
    records  = []

    for elg_id, appeal_rec_date in sampled:
        # Business rule: appeal decision AFTER appeal recommendation
        d = later_date(appeal_rec_date, min_days=1, max_days=180)
        records.append((
            elg_id,
            random.choices(dec_keys, weights=dec_wts, k=1)[0],
            d,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_appeal_decision (
            eligibility_id, appeal_decision_code,
            appeal_decision_date, decided_by
        ) VALUES (%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} appeal decisions inserted.")


# ── fact_certificate ──────────────────────────────────────────────────────────

def generate_certificates(conn, refs, individual_ids):
    """
    individual_ids: list of (ind_id, created_at)
    """
    print("Generating fact_certificate...")
    cert_individuals = random.sample(individual_ids, min(N_CERTIFICATES, len(individual_ids)))
    cert_keys        = list(CERT_TYPE_WEIGHTS.keys())
    cert_wts         = list(CERT_TYPE_WEIGHTS.values())
    records          = []

    for ind_id, ind_created_at in cert_individuals:
        # Business rule: certificate AFTER individual
        dt        = later_datetime(ind_created_at.date(), min_days=1, max_days=365)
        cert_type = random.choices(cert_keys, weights=cert_wts, k=1)[0]
        records.append((
            str(uuid.uuid4()), ind_id,
            f"Certificate - {cert_type.replace('_', ' ').title()}",
            cert_type, dt, dt.date(),
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))

    query = """
        INSERT INTO fact_certificate (
            certificate_id, individual_id, cert_name,
            cert_type_code, issued_at, issued_date, issued_by
        ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} certificates inserted.")


# ── main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    conn = get_connection()
    try:
        print("Loading reference data...")
        refs = load_refs(conn)

        rg_ids         = generate_registration_groups(conn, refs)   # (rg_id, created_at)
        individual_ids = generate_individuals(conn, refs, rg_ids)   # (ind_id, created_at)

        admissibility_ids = generate_admissibility(conn, refs, individual_ids)   # (adm_id, ind_id, created_at)
        generate_adm_interviews(conn, refs, admissibility_ids)
        generate_adm_decisions(conn, refs, admissibility_ids)

        eligibility_ids  = generate_eligibilities(conn, refs, individual_ids)  # (elg_id, ind_id, created_at)
        rec_elg_ids    = generate_elg_recommendations(conn, refs, eligibility_ids)  # (elg_id, rec_datetime)
        generate_elg_reviews(conn, refs, eligibility_ids)

        appeal_rec_ids  = generate_appeal_recommendations(conn, refs, rec_elg_ids)  # (elg_id, appeal_date)
        generate_appeal_decisions(conn, refs, appeal_rec_ids)

        generate_certificates(conn, refs, individual_ids)

        print("\n✓ All facts generated successfully.")

    finally:
        conn.close()