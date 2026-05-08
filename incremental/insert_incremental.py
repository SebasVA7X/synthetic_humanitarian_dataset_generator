## insert_incremental.py
## Adds new registration groups, individuals, and facts without touching existing data.
##
## Safe to run multiple times — never modifies existing rows.
##
## Usage (run from project root):
##   python -m incremental.insert_incremental                    # uses defaults from INCREMENTAL_VOLUMES
##   python -m incremental.insert_incremental --rg 500           # add 500 registration groups
##   python -m incremental.insert_incremental --ind 1000         # add 1000 individuals
##   python -m incremental.insert_incremental --rg 200 --ind 500 --adm 300 --elg 200 --cert 400
##
## Notes:
##   - New individuals are assigned to EXISTING + new registration groups
##   - New facts can reference EXISTING + new individuals/admissibility assessments/eligibility assessments
##   - Sequential IDs (IND-, ADM-, ELG-) continue from the current max in DB

import argparse
from core.db import get_connection, execute_batch_insert
from facts.generate_facts import (
    load_refs,
    generate_registration_groups,
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
from dimensions.generate_dims import (
    generate_individuals as _generate_individuals,
)
from core.config import (
    N_REGISTRATION_GROUPS, N_INDIVIDUALS,
    N_ADMISSIBILITY, N_ADM_INTERVIEWS, N_ADM_DECISIONS,
    N_ELIGIBILITIES, N_ELG_RECOMMENDATIONS, N_ELG_REVIEWS,
    N_APPEAL_RECOMMENDATIONS, N_APPEAL_DECISIONS, N_CERTIFICATES,
    COUNTRY_WEIGHTS, PROCESS_STATUS_WEIGHTS, LEGAL_STATUS_WEIGHTS,
    BIOMETRICS_RATE, DATE_END,
)

# ── Default volumes for incremental runs ─────────────────────────────────────
# Set to ~10% of initial load by default — adjust freely.

INCREMENTAL_VOLUMES = {
    "rg":        300,
    "ind":     1_200,
    "adm":       800,
    "adm_int":   750,
    "adm_dec":   500,
    "elg":       450,
    "elg_rec":   380,
    "elg_rev":   250,
    "app_rec":    55,
    "app_dec":    30,
    "cert":      550,
}


# ── Load existing PKs from DB ─────────────────────────────────────────────────

def load_existing_rg_ids(conn):
    """Returns list of (rg_id, created_at) for all existing registration groups."""
    with conn.cursor() as cur:
        cur.execute("SELECT rg_id, created_at FROM dim_registration_group")
        return [(str(row[0]), row[1]) for row in cur.fetchall()]


def load_existing_individual_ids(conn):
    """Returns list of (individual_id, created_at) for all existing individuals."""
    with conn.cursor() as cur:
        cur.execute("SELECT individual_id, created_at FROM dim_individual")
        return [(row[0], row[1]) for row in cur.fetchall()]


def load_existing_admissibility_ids(conn):
    """Returns list of (admissibility_id, individual_id, created_at) for all existing admissibility assessments."""
    with conn.cursor() as cur:
        cur.execute("SELECT admissibility_id, individual_id, created_at FROM fact_admissibility")
        return [(row[0], row[1], row[2]) for row in cur.fetchall()]


def load_existing_eligibility_ids(conn):
    """Returns list of (eligibility_id, individual_id, created_at) for all existing eligibility assessments."""
    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id, individual_id, created_at FROM fact_eligibility")
        return [(row[0], row[1], row[2]) for row in cur.fetchall()]


def load_existing_elg_recommendation_ids(conn):
    """Returns list of (eligibility_id, recommendation_date) for all existing eligibility recommendations."""
    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id, recommendation_date FROM fact_elg_recommendation")
        return [(row[0], row[1]) for row in cur.fetchall()]


def load_existing_appeal_recommendation_ids(conn):
    """Returns list of (eligibility_id, appeal_recommendation_date) for existing appeal recommendations."""
    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id, appeal_recommendation_date FROM fact_appeal_recommendation")
        return [(row[0], row[1]) for row in cur.fetchall()]


# ── Sequential ID helpers ─────────────────────────────────────────────────────

def get_next_ind_offset(conn):
    """Returns the next integer offset for IND- IDs."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(CAST(SUBSTRING(individual_id FROM 5) AS INTEGER)) FROM dim_individual")
        result = cur.fetchone()[0]
        return (result or 0) + 1


def get_next_adm_offset(conn):
    """Returns the next integer offset for ADM- IDs."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(CAST(SUBSTRING(admissibility_id FROM 5) AS INTEGER)) FROM fact_admissibility")
        result = cur.fetchone()[0]
        return (result or 0) + 1


def get_next_elg_offset(conn):
    """Returns the next integer offset for ELG- IDs."""
    with conn.cursor() as cur:
        cur.execute("SELECT MAX(CAST(SUBSTRING(eligibility_id FROM 5) AS INTEGER)) FROM fact_eligibility")
        result = cur.fetchone()[0]
        return (result or 0) + 1


# ── Patched generators that accept ID offsets ─────────────────────────────────
# These replace the generate_* functions from generate_facts.py for incremental
# use, since those functions hardcode i+1 as the ID sequence start.

def generate_individuals_incremental(conn, rg_ids, user_ids, id_offset):
    """
    Like generate_dims.generate_individuals but starts IDs at id_offset.
    rg_ids: list of (rg_id, created_at) — can include existing + new RGs
    Returns: list of (ind_id, created_at)
    """
    import random
    from dimensions.generate_dims import random_dob, generate_full_name, later_datetime, SEX_WEIGHTS

    country_keys    = list(COUNTRY_WEIGHTS.keys())
    country_weights = list(COUNTRY_WEIGHTS.values())
    status_keys     = list(PROCESS_STATUS_WEIGHTS.keys())
    status_weights  = list(PROCESS_STATUS_WEIGHTS.values())
    legal_keys      = list(LEGAL_STATUS_WEIGHTS.keys())
    legal_weights   = list(LEGAL_STATUS_WEIGHTS.values())

    n              = volumes["ind"]
    records        = []
    individual_ids = []

    for i in range(n):
        ind_id = f"IND-{str(id_offset + i).zfill(6)}"

        sex            = random.choice(SEX_WEIGHTS)
        country_code   = random.choices(country_keys,  weights=country_weights,  k=1)[0]
        process_status = random.choices(status_keys,   weights=status_weights,   k=1)[0]
        legal_status   = random.choices(legal_keys,    weights=legal_weights,    k=1)[0]

        rg_id, rg_created_at = random.choice(rg_ids)
        created_at = later_datetime(rg_created_at.date(), min_days=1, max_days=365)

        created_by = random.choice(user_ids) if random.random() > 0.05 else None

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
    return individual_ids


def generate_admissibility_incremental(conn, refs, individual_ids, id_offset):
    """
    Like generate_facts.generate_admissibility but starts ADM- IDs at id_offset
    and limits to volumes["adm"] records.
    individual_ids: list of (ind_id, created_at) — can be existing + new
    Returns: list of (adm_id, ind_id, created_at)
    """
    import random
    from facts.generate_facts import later_datetime
    from core.config import PROCESS_STATUS_WEIGHTS, ADMISSIBILITY_DECISION_WEIGHTS

    n            = volumes["adm"]
    sampled      = random.sample(individual_ids, min(n, len(individual_ids)))
    records      = []
    adm_ids      = []

    status_keys = list(PROCESS_STATUS_WEIGHTS.keys())
    status_wts  = list(PROCESS_STATUS_WEIGHTS.values())
    dec_keys    = list(ADMISSIBILITY_DECISION_WEIGHTS.keys())
    dec_wts     = list(ADMISSIBILITY_DECISION_WEIGHTS.values())

    for i, (ind_id, ind_created_at) in enumerate(sampled):
        adm_id     = f"ADM-{str(id_offset + i).zfill(6)}"
        created_at = later_datetime(ind_created_at.date(), min_days=1, max_days=180)

        has_bps  = random.random() > 0.25
        bps      = random.choices(dec_keys, weights=dec_wts, k=1)[0] if has_bps else None
        bps_dt   = later_datetime(created_at.date()) if has_bps else None
        bps_date = bps_dt.date() if bps_dt else None

        adm_ids.append((adm_id, ind_id, created_at))
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
    return adm_ids


def generate_eligibilities_incremental(conn, refs, individual_ids, id_offset):
    """
    Like generate_facts.generate_eligibilities but starts ELG- IDs at id_offset
    and limits to volumes["elg"] records.
    Returns: list of (elg_id, ind_id, created_at)
    """
    import random
    from facts.generate_facts import later_datetime
    from core.config import PROCESS_TYPE_WEIGHTS

    n                = volumes["elg"]
    elg_individuals = random.sample(individual_ids, min(n, len(individual_ids)))
    records          = []
    eligibility_ids   = []

    proc_keys  = list(PROCESS_TYPE_WEIGHTS.keys())
    proc_wts   = list(PROCESS_TYPE_WEIGHTS.values())
    notif_keys = ["email", "hand_delivery", "mail", "phone", "self_service"]

    for i, (ind_id, ind_created_at) in enumerate(elg_individuals):
        elg_id    = f"ELG-{str(id_offset + i).zfill(6)}"
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
    return eligibility_ids


# ── Patched volume-aware wrappers for child facts ─────────────────────────────
# generate_facts.py uses N_* constants directly; here we override via volumes[].

def _adm_interviews(conn, refs, admissibility_ids):
    import random
    import uuid
    from facts.generate_facts import later_datetime
    n       = volumes["adm_int"]
    sampled = random.sample(admissibility_ids, min(n, len(admissibility_ids)))
    records = []
    for adm_id, _ind_id, adm_created_at in sampled:
        dt = later_datetime(adm_created_at.date(), min_days=1, max_days=90)
        records.append((
            str(uuid.uuid4()), adm_id, dt, dt.date(),
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))
    query = """
        INSERT INTO fact_adm_interview (
            interview_id, admissibility_id, interview_datetime, interview_date, created_by
        ) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} adm interviews inserted.")


def _adm_decisions(conn, refs, admissibility_ids):
    import random
    import uuid
    from facts.generate_facts import later_datetime
    from core.config import ADMISSIBILITY_DECISION_WEIGHTS
    n        = volumes["adm_dec"]
    sampled  = random.sample(admissibility_ids, min(n, len(admissibility_ids)))
    dec_keys = list(ADMISSIBILITY_DECISION_WEIGHTS.keys())
    dec_wts  = list(ADMISSIBILITY_DECISION_WEIGHTS.values())
    basis_keys = [
        "BASIS_UNFOUNDED_B", "BASIS_ADMITTED", "BASIS_FRAUD_C",
        "BASIS_EXTEMP", "BASIS_FRAUD_A", "BASIS_UNFOUNDED_C",
        "BASIS_UNFOUNDED_A", "BASIS_FRAUD_B", "BASIS_EXTEMP_LATE",
    ]
    records = []
    for adm_id, _ind_id, adm_created_at in sampled:
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
    print(f"  → {len(records)} adm decisions inserted.")


def _elg_recommendations(conn, refs, eligibility_ids):
    import random
    from facts.generate_facts import later_datetime
    from core.config import ELG_RECOMMENDATION_WEIGHTS
    n        = volumes["elg_rec"]
    sampled  = random.sample(eligibility_ids, min(n, len(eligibility_ids)))
    rec_keys = list(ELG_RECOMMENDATION_WEIGHTS.keys())
    rec_wts  = list(ELG_RECOMMENDATION_WEIGHTS.values())
    reason_keys = [101001, 101002, 101003, 101004, 101005, 101006, 101007]
    records  = []
    rec_ids  = []

    # Exclude elg_ids that already have a recommendation
    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id FROM fact_elg_recommendation")
        already_has_rec = {row[0] for row in cur.fetchall()}

    eligible = [(eid, iid, cat) for eid, iid, cat in sampled if eid not in already_has_rec]

    for elg_id, _ind_id, elg_created_at in eligible:
        dt = later_datetime(elg_created_at.date(), min_days=1, max_days=120)
        rec_ids.append((elg_id, dt))
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
    return rec_ids


def _elg_reviews(conn, refs, eligibility_ids):
    import random
    from facts.generate_facts import later_datetime
    from core.config import REVIEW_DECISION_WEIGHTS
    n        = volumes["elg_rev"]
    sampled  = random.sample(eligibility_ids, min(n, len(eligibility_ids)))
    rev_keys = list(REVIEW_DECISION_WEIGHTS.keys())
    rev_wts  = list(REVIEW_DECISION_WEIGHTS.values())
    cat_keys = ["officer", "senior", "supervisor", "external"]
    records  = []

    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id FROM fact_elg_review")
        already_has_review = {row[0] for row in cur.fetchall()}

    eligible = [(eid, iid, cat) for eid, iid, cat in sampled if eid not in already_has_review]

    for elg_id, _ind_id, elg_created_at in eligible:
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


def _appeal_recommendations(conn, refs, rec_elg_ids):
    import random
    from facts.generate_facts import later_date
    from core.config import APPEAL_REC_WEIGHTS
    n        = volumes["app_rec"]
    sampled  = random.sample(rec_elg_ids, min(n, len(rec_elg_ids)))
    rec_keys = list(APPEAL_REC_WEIGHTS.keys())
    rec_wts  = list(APPEAL_REC_WEIGHTS.values())
    records  = []
    app_ids  = []

    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id FROM fact_appeal_recommendation")
        already_has_appeal_rec = {row[0] for row in cur.fetchall()}

    eligible = [(eid, rdt) for eid, rdt in sampled if eid not in already_has_appeal_rec]

    for elg_id, rec_created_at in eligible:
        d = later_date(rec_created_at.date(), min_days=1, max_days=180)
        app_ids.append((elg_id, d))
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
    return app_ids


def _appeal_decisions(conn, refs, appeal_rec_ids):
    import random
    from facts.generate_facts import later_date
    from core.config import APPEAL_DEC_WEIGHTS
    n        = volumes["app_dec"]
    sampled  = random.sample(appeal_rec_ids, min(n, len(appeal_rec_ids)))
    dec_keys = list(APPEAL_DEC_WEIGHTS.keys())
    dec_wts  = list(APPEAL_DEC_WEIGHTS.values())
    records  = []

    with conn.cursor() as cur:
        cur.execute("SELECT eligibility_id FROM fact_appeal_decision")
        already_has_appeal_dec = {row[0] for row in cur.fetchall()}

    eligible = [(eid, adt) for eid, adt in sampled if eid not in already_has_appeal_dec]

    for elg_id, appeal_rec_date in eligible:
        d = later_date(appeal_rec_date, min_days=1, max_days=180)
        records.append((
            elg_id,
            random.choices(dec_keys, weights=dec_wts, k=1)[0],
            d,
            random.choice(refs["user_ids"]) if random.random() > 0.05 else None,
        ))
    query = """
        INSERT INTO fact_appeal_decision (
            eligibility_id, appeal_decision_code, appeal_decision_date, decided_by
        ) VALUES (%s,%s,%s,%s)
        ON CONFLICT DO NOTHING
    """
    execute_batch_insert(conn, query, records)
    print(f"  → {len(records)} appeal decisions inserted.")


def _certificates(conn, refs, individual_ids):
    import random
    import uuid
    from facts.generate_facts import later_datetime
    from core.config import CERT_TYPE_WEIGHTS
    n                = volumes["cert"]
    cert_individuals = random.sample(individual_ids, min(n, len(individual_ids)))
    cert_keys        = list(CERT_TYPE_WEIGHTS.keys())
    cert_wts         = list(CERT_TYPE_WEIGHTS.values())
    records          = []
    for ind_id, ind_created_at in cert_individuals:
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


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Insert incremental data into ran_system without duplicating PKs/FKs."
    )
    parser.add_argument("--rg",       type=int, help="Registration groups to add")
    parser.add_argument("--ind",      type=int, help="Individuals to add")
    parser.add_argument("--adm",      type=int, help="Admissibility assessments to add")
    parser.add_argument("--adm-int",  type=int, help="Adm interviews to add")
    parser.add_argument("--adm-dec",  type=int, help="Adm decisions to add")
    parser.add_argument("--elg",      type=int, help="Eligibility assessments to add")
    parser.add_argument("--elg-rec",  type=int, help="Eligibility recommendations to add")
    parser.add_argument("--elg-rev",  type=int, help="Eligibility reviews to add")
    parser.add_argument("--app-rec",  type=int, help="Appeal recommendations to add")
    parser.add_argument("--app-dec",  type=int, help="Appeal decisions to add")
    parser.add_argument("--cert",     type=int, help="Certificates to add")
    return parser.parse_args()


# ── Main ──────────────────────────────────────────────────────────────────────

volumes = {}   # populated in main, used by patched generators

if __name__ == "__main__":
    args = parse_args()

    volumes = {
        "rg":       args.rg       or INCREMENTAL_VOLUMES["rg"],
        "ind":      args.ind      or INCREMENTAL_VOLUMES["ind"],
        "adm":      args.adm      or INCREMENTAL_VOLUMES["adm"],
        "adm_int":  args.adm_int  or INCREMENTAL_VOLUMES["adm_int"],
        "adm_dec":  args.adm_dec  or INCREMENTAL_VOLUMES["adm_dec"],
        "elg":      args.elg      or INCREMENTAL_VOLUMES["elg"],
        "elg_rec":  args.elg_rec  or INCREMENTAL_VOLUMES["elg_rec"],
        "elg_rev":  args.elg_rev  or INCREMENTAL_VOLUMES["elg_rev"],
        "app_rec":  args.app_rec  or INCREMENTAL_VOLUMES["app_rec"],
        "app_dec":  args.app_dec  or INCREMENTAL_VOLUMES["app_dec"],
        "cert":     args.cert     or INCREMENTAL_VOLUMES["cert"],
    }

    print("Volumes for this run:")
    for k, v in volumes.items():
        print(f"  {k:>10}: {v:,}")
    print()

    conn = get_connection()
    try:
        refs = load_refs(conn)

        # ── Registration groups ───────────────────────────────────────────────
        print("Adding registration groups...")
        existing_rg_ids = load_existing_rg_ids(conn)
        new_rg_ids      = generate_registration_groups(conn, refs)
        all_rg_ids      = existing_rg_ids + new_rg_ids

        # ── Individuals ───────────────────────────────────────────────────────
        print("\nAdding individuals...")
        ind_offset         = get_next_ind_offset(conn)
        existing_ind_ids   = load_existing_individual_ids(conn)
        new_ind_ids        = generate_individuals_incremental(conn, all_rg_ids, refs["user_ids"], ind_offset)
        all_ind_ids        = existing_ind_ids + new_ind_ids

        # ── Admissibility ─────────────────────────────────────────────────────
        print("\nAdding admissibility assessments...")
        adm_offset         = get_next_adm_offset(conn)
        existing_adm_ids   = load_existing_admissibility_ids(conn)
        new_adm_ids        = generate_admissibility_incremental(conn, refs, all_ind_ids, adm_offset)
        all_adm_ids        = existing_adm_ids + new_adm_ids

        print("\nAdding adm interviews and decisions...")
        _adm_interviews(conn, refs, all_adm_ids)
        _adm_decisions(conn, refs, all_adm_ids)

        # ── Eligibility ───────────────────────────────────────────────────────
        print("\nAdding eligibility assessments...")
        elg_offset         = get_next_elg_offset(conn)
        existing_elg_ids   = load_existing_eligibility_ids(conn)
        new_elg_ids        = generate_eligibilities_incremental(conn, refs, all_ind_ids, elg_offset)
        all_elg_ids        = existing_elg_ids + new_elg_ids

        print("\nAdding eligibility recommendations and reviews...")
        existing_rec_ids   = load_existing_elg_recommendation_ids(conn)
        new_rec_ids        = _elg_recommendations(conn, refs, all_elg_ids)
        all_rec_ids        = existing_rec_ids + new_rec_ids

        _elg_reviews(conn, refs, all_elg_ids)

        print("\nAdding appeal recommendations and decisions...")
        existing_app_rec_ids = load_existing_appeal_recommendation_ids(conn)
        new_app_rec_ids      = _appeal_recommendations(conn, refs, all_rec_ids)
        all_app_rec_ids      = existing_app_rec_ids + new_app_rec_ids

        _appeal_decisions(conn, refs, all_app_rec_ids)

        # ── Certificates ──────────────────────────────────────────────────────
        print("\nAdding certificates...")
        _certificates(conn, refs, all_ind_ids)

        print("\n✓ Incremental insert completed successfully.")

    except Exception as e:
        conn.rollback()
        print(f"\n✗ Error: {e}")
        raise

    finally:
        conn.close()