## config.py
## Data generation parameters for ran_system portfolio database

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ── Database ──────────────────────────────────────────────────────────────────
DB = {
    "host":     os.environ["DB_HOST"],
    "port":     int(os.environ["DB_PORT"]),
    "dbname":   os.environ["DB_NAME"],
    "user":     os.environ["DB_USER"],
    "password": os.environ["DB_PASSWORD"],
}

# ── Date range ────────────────────────────────────────────────────────────────
DATE_START = date(2019, 1, 1)
DATE_END = date(2025, 12, 31)

# ── Volumes ───────────────────────────────────────────────────────────────────
N_USERS = 50
N_REGISTRATION_GROUPS = 3_000
N_INDIVIDUALS = 12_000
N_ADMISSIBILITY = 8_000
N_ADM_INTERVIEWS = 7_500
N_ADM_DECISIONS = 5_000
N_ELIGIBILITIES = 4_500
N_ELG_RECOMMENDATIONS = 3_800
N_ELG_REVIEWS = 2_500
N_APPEAL_RECOMMENDATIONS = 550
N_APPEAL_DECISIONS = 300
N_CERTIFICATES = 5_500

# ── Office weights ────────────────────────────────────────────────────────────
OFFICE_WEIGHTS = {
    "Quito": 0.45,
    "Guayaquil": 0.20,
    "Manta": 0.09,
    "El Puyo": 0.09,
    "Cuenca": 0.08,
    "Riobamba": 0.06,
    "Macara": 0.03,
}

# ── Country distribution ──────────────────────────────────────────────────────
COUNTRY_WEIGHTS = {
    "VEN": 0.62,
    "COL": 0.25,
    "STA": 0.04,
    "CUB": 0.03,
    "PER": 0.02,
    "HTI": 0.02,
    "SYR": 0.01,
    "LEB": 0.01,
}

# ── Individual process status distribution ────────────────────────────────────
PROCESS_STATUS_WEIGHTS = {
    "active": 0.33,
    "inactive": 0.15,
    "hold": 0.12,
    "closed": 0.40,
}

# ── Legal status distribution ─────────────────────────────────────────────────
LEGAL_STATUS_WEIGHTS = {
    "asylum_seeker": 0.54,
    "refugee": 0.29,
    "other_of_concern": 0.09,
    "not_of_concern": 0.04,
    "idp": 0.01,
    "stateless": 0.01,
    "refugee_like": 0.01,
    "returned_idp": 0.005,
    "returnee": 0.005,
}

# ── Biometrics rate ───────────────────────────────────────────────────────────
BIOMETRICS_RATE = 0.15

# ── Admissibility decision distribution ──────────────────────────────────────
ADMISSIBILITY_DECISION_WEIGHTS = {
    "ADM": 0.35,
    "ADM_AP": 0.05,
    "ADM_NOT": 0.05,
    "INAD": 0.25,
    "INAD_AP": 0.08,
    "INAD_NOT": 0.05,
    "INAD_SOL": 0.05,
    "INAD_PROJ": 0.05,
    "INAD_REV": 0.03,
    "OTHER": 0.04,
}

# ── Eligibility recommendation distribution ───────────────────────────────────
ELG_RECOMMENDATION_WEIGHTS = {
    101001: 0.45,  # Recognized
    101002: 0.30,  # Rejected
    101003: 0.10,  # Maintained
    101004: 0.08,  # Cancelled
    101005: 0.04,  # Revoked
    101006: 0.03,  # Ceased
}

# ── Review decision distribution ──────────────────────────────────────────────
REVIEW_DECISION_WEIGHTS = {
    101001: 0.60,  # Recommendation Accepted
    101002: 0.15,  # Returned for Review
    101003: 0.10,  # Returned for Complementary Interview
    101004: 0.15,  # Pending Review
}

# ── Appeal recommendation distribution ───────────────────────────────────────
APPEAL_REC_WEIGHTS = {
    "Recognition": 0.50,
    "Rejection": 0.35,
    "Ceased": 0.15,
}

# ── Appeal decision distribution ──────────────────────────────────────────────
APPEAL_DEC_WEIGHTS = {
    101001: 0.55,  # Recommendation Accepted
    101002: 0.25,  # Returned for Complementary Interview
    101003: 0.20,  # Pending Review
}

# ── Certificate type distribution ─────────────────────────────────────────────
CERT_TYPE_WEIGHTS = {
    "CERT_REG": 0.40,
    "CERT_INTERVIEW": 0.35,
    "CERT_APPT": 0.20,
    "OTHER": 0.05,
}

# ── Process type distribution for eligibility assessments ─────────────────────
PROCESS_TYPE_WEIGHTS = {
    5001: 0.70,  # Status Determination
    5002: 0.15,  # Derivative  (RF cases)
    5003: 0.05,  # Reopening
    5004: 0.04,  # Cancellation
    5005: 0.03,  # Cessation
    5006: 0.03,  # Revocation
}