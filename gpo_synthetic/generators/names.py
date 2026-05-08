"""
Name generator.

Two pools of names:
  - MATCH pool: drawn from dim_individual (Postgres). These will land in the
    output with optional perturbations (typos, reordering, DOB shifts) so the
    fuzzy matching step downstream can be exercised across all confidence
    tiers.
  - NON-MATCH pool: generated with Faker (en_US). These will never appear in
    dim_individual, and must be discarded by the matcher.

Match-tier distribution (within the 56% that comes from the MATCH pool):
  60% identical            → STRONG_A_NAME_EQ_DOB_EQ
  25% name typo (≤1 char)  → STRONG_B_NAME96_DOB_EQ
  10% token reorder        → MEDIUM/STRONG via token_sort_ratio
   5% DOB day-typo         → RESCUE_NAME97_DOB_YYYYMM
"""
import random
import string
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from faker import Faker

_fake = Faker("en_US")


# ────────────────────────────────────────────────────────────────────────────
# Data classes for typed flow
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class PersonRecord:
    """A single individual selected from a name pool."""
    full_name: str
    sex: str               # 'M' / 'F' / 'Other'
    date_of_birth: date
    country_origin: str    # ISO-ish code: VEN, COL, CUB, HTI, PER, SYR, STA, OTHER
    is_match_pool: bool    # True if drawn from dim_individual
    perturbation: str = "none"  # 'none' | 'typo' | 'reorder' | 'dob_shift'


# ────────────────────────────────────────────────────────────────────────────
# Pool builders
# ────────────────────────────────────────────────────────────────────────────

def parse_dob(value) -> date:
    if isinstance(value, date):
        return value
    return pd.to_datetime(value).date()


def build_match_pool(df: pd.DataFrame) -> list[PersonRecord]:
    """Build a list of PersonRecord from a dim_individual DataFrame."""
    records = []
    for _, row in df.iterrows():
        try:
            dob = parse_dob(row["date_of_birth"])
        except Exception:
            continue
        records.append(PersonRecord(
            full_name=str(row["full_name"]).strip(),
            sex=str(row["sex"]).strip(),
            date_of_birth=dob,
            country_origin=str(row["country_origin"]).strip().upper(),
            is_match_pool=True,
        ))
    random.shuffle(records)
    return records


def generate_nonmatch_person(target_country: str | None = None) -> PersonRecord:
    """Generate a fresh anglo-style person that is NOT in the match pool."""
    sex = random.choices(["M", "F", "Other"], weights=[47, 52, 1])[0]
    if sex == "M":
        first1 = _fake.first_name_male()
    elif sex == "F":
        first1 = _fake.first_name_female()
    else:
        first1 = _fake.first_name()

    first2 = _fake.first_name_male() if sex == "M" else _fake.first_name_female()
    last1 = _fake.last_name()
    last2 = _fake.last_name()
    full_name = f"{first1} {first2} {last1} {last2}"

    age = random.randint(18, 70)
    today = date.today()
    dob = today - timedelta(days=age * 365 + random.randint(-200, 200))

    country = target_country or random.choice(
        ["VEN", "COL", "CUB", "HTI", "PER", "OTHER", "STA", "SYR"]
    )

    return PersonRecord(
        full_name=full_name,
        sex=sex,
        date_of_birth=dob,
        country_origin=country,
        is_match_pool=False,
    )


# ────────────────────────────────────────────────────────────────────────────
# Perturbations
# ────────────────────────────────────────────────────────────────────────────

def apply_typo(name: str) -> str:
    """Single-character substitution at a non-edge position."""
    if len(name) < 4:
        return name
    chars = list(name)
    candidates = [i for i, c in enumerate(chars)
                  if c.isalpha() and 0 < i < len(chars) - 1]
    if not candidates:
        return name
    idx = random.choice(candidates)
    new_char = random.choice(string.ascii_lowercase)
    while new_char.upper() == chars[idx].upper():
        new_char = random.choice(string.ascii_lowercase)
    chars[idx] = new_char if chars[idx].islower() else new_char.upper()
    return "".join(chars)


def apply_reorder(name: str) -> str:
    """Shuffle name tokens (still recoverable via token_sort_ratio)."""
    tokens = name.split()
    if len(tokens) < 2:
        return name
    shuffled = tokens[:]
    while shuffled == tokens:
        random.shuffle(shuffled)
    return " ".join(shuffled)


def apply_dob_shift(dob: date) -> date:
    """Shift day-of-month while keeping year and month — survives RESCUE rule."""
    delta = random.choice([-3, -2, -1, 1, 2, 3])
    new_day = max(1, min(28, dob.day + delta))
    return dob.replace(day=new_day)


def perturb(person: PersonRecord) -> PersonRecord:
    """
    Apply a perturbation to a match-pool person according to the agreed
    distribution. Non-match persons are returned unchanged.
    """
    if not person.is_match_pool:
        return person

    r = random.random()
    if r < 0.60:
        return person  # identical
    if r < 0.85:
        return PersonRecord(
            full_name=apply_typo(person.full_name),
            sex=person.sex,
            date_of_birth=person.date_of_birth,
            country_origin=person.country_origin,
            is_match_pool=True,
            perturbation="typo",
        )
    if r < 0.95:
        return PersonRecord(
            full_name=apply_reorder(person.full_name),
            sex=person.sex,
            date_of_birth=person.date_of_birth,
            country_origin=person.country_origin,
            is_match_pool=True,
            perturbation="reorder",
        )
    return PersonRecord(
        full_name=person.full_name,
        sex=person.sex,
        date_of_birth=apply_dob_shift(person.date_of_birth),
        country_origin=person.country_origin,
        is_match_pool=True,
        perturbation="dob_shift",
    )


# ────────────────────────────────────────────────────────────────────────────
# Variants for "Full Legal Name" column (91% similar, 9% noise)
# ────────────────────────────────────────────────────────────────────────────

def render_full_legal_name(primary: str) -> str:
    r = random.random()
    if r >= 0.91:
        return random.choice([
            "SIN DATO", "N/A", "---", "", "VER DOCUMENTO",
            "IGUAL QUE ARRIBA", "No aplica", "idem",
            str(random.randint(1000, 99999)),
        ])
    v = random.random()
    if v < 0.50:
        return primary
    if v < 0.70:
        return primary.upper()
    if v < 0.85:
        return primary.lower()
    if v < 0.93:
        return apply_reorder(primary)
    return apply_typo(primary)
