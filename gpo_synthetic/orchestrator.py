"""
Orchestrator: drives the full generation flow.

Pipeline:
  1. Load source pool (Postgres or CSV fallback) and build PersonRecord pool.
  2. Decide composition: 56% match-pool, 44% non-match (Faker en_US).
  3. Plan duplicates:
       - 5% of rows: a match-pool declarant is also injected as a family member
         in another (later-created) submission.
       - 5% of rows: a synthetic non-match family member is shared between two
         submissions (kept simpler — same name and doc reused as a member in a
         second submission).
  4. For each row, render the 20-column record using the canonical schema.
  5. Write to Excel.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd

from gpo_synthetic.config import GenerationConfig, PostgresConfig
from gpo_synthetic.generators.contact import random_email, random_phone
from gpo_synthetic.generators.dates import (
    format_date,
    random_creation_date,
)
from gpo_synthetic.generators.demographics import (
    render_marital_status,
    render_nationality,
    render_province,
    render_sex,
    random_sex,
)
from gpo_synthetic.generators.documents import (
    random_clean_doc,
    render_identification_document,
    render_personal_document,
)
from gpo_synthetic.generators.family import (
    FamilyGroup,
    build_family_group,
    inject_member_from_person,
    render_family_group,
)
from gpo_synthetic.generators.names import (
    PersonRecord,
    build_match_pool,
    generate_nonmatch_person,
    perturb,
    render_full_legal_name,
)
from gpo_synthetic.schema import COLUMNS, FORM_TITLE
from gpo_synthetic.sources.postgres_source import (
    fetch_dim_individual,
    fetch_dim_individual_from_csv,
)


# ────────────────────────────────────────────────────────────────────────────
# Internal row representation
# ────────────────────────────────────────────────────────────────────────────

@dataclass
class Submission:
    """Holds all data needed to render one synthetic submission row."""
    submission_id: int
    creation_date: date
    person: PersonRecord            # the (possibly perturbed) declarant
    declarant_doc: str              # canonical clean doc number
    family_group: FamilyGroup
    age: int


def _calc_age(dob: date, on: date) -> int:
    return on.year - dob.year - ((on.month, on.day) < (dob.month, dob.day))


# ────────────────────────────────────────────────────────────────────────────
# Source loader
# ────────────────────────────────────────────────────────────────────────────

def load_match_pool(pg_cfg: PostgresConfig, csv_fallback: str | None = None) -> list[PersonRecord]:
    """Load dim_individual from Postgres, falling back to CSV if requested."""
    if csv_fallback:
        df = fetch_dim_individual_from_csv(csv_fallback)
    else:
        df = fetch_dim_individual(pg_cfg)
    return build_match_pool(df)


# ────────────────────────────────────────────────────────────────────────────
# Composition planning
# ────────────────────────────────────────────────────────────────────────────

def plan_composition(
    n_rows: int,
    match_ratio: float,
    duplicate_ratio: float,
    match_pool: list[PersonRecord],
) -> tuple[list[PersonRecord], list[PersonRecord]]:
    """
    Decide which rows come from the match pool and which are non-match.
    Returns (declarant_persons_in_order, separate_pool_for_duplicate_injection).

    A subset of match-pool persons is reserved for *duplicate injection* — they
    become declarants AND are later injected as family members in a different
    submission.
    """
    n_match = int(round(n_rows * match_ratio))
    n_nonmatch = n_rows - n_match

    if n_match > len(match_pool):
        raise ValueError(
            f"Match pool too small: need {n_match}, have {len(match_pool)}"
        )

    # Sample without replacement for declarants from match pool
    match_declarants = random.sample(match_pool, n_match)

    # The duplicate-injection pool is a subset of match_declarants
    n_dup_match = int(round(n_rows * duplicate_ratio * 0.5))
    duplicate_injection_pool = random.sample(match_declarants, min(n_dup_match, len(match_declarants)))

    # Generate non-match declarants on the fly
    nonmatch_declarants = [generate_nonmatch_person() for _ in range(n_nonmatch)]

    declarants = match_declarants + nonmatch_declarants
    random.shuffle(declarants)

    return declarants, duplicate_injection_pool


# ────────────────────────────────────────────────────────────────────────────
# Submission builder
# ────────────────────────────────────────────────────────────────────────────

def build_submission(
    submission_id: int,
    declarant_person: PersonRecord,
) -> Submission:
    """Build a Submission for a given declarant person (no perturbation yet)."""
    creation_date = random_creation_date()
    age = _calc_age(declarant_person.date_of_birth, creation_date)
    if age < 18:
        age = 18

    family_group = build_family_group(
        declarant_age=age,
        declarant_dob=declarant_person.date_of_birth,
        declarant_country=declarant_person.country_origin,
        creation_date=creation_date,
    )

    declarant_doc = random_clean_doc()

    return Submission(
        submission_id=submission_id,
        creation_date=creation_date,
        person=declarant_person,
        declarant_doc=declarant_doc,
        family_group=family_group,
        age=age,
    )


# ────────────────────────────────────────────────────────────────────────────
# Duplicate injection
# ────────────────────────────────────────────────────────────────────────────

DUP_RELATIONSHIPS = ["Esposo/a", "Hermano/a", "Hijo/a", "Madre", "Padre"]


def inject_declarant_duplicates(
    submissions: list[Submission],
    duplicate_injection_pool: list[PersonRecord],
) -> int:
    """
    Take each person from the duplicate_injection_pool (who is already a
    declarant somewhere) and inject them as a family member in a *different*
    submission with a coherent relationship.

    Returns the number of injections performed.
    """
    # Index: person -> submission they declared in
    person_to_sub: dict[int, Submission] = {}
    for s in submissions:
        person_to_sub[id(s.person)] = s

    injected = 0
    for person in duplicate_injection_pool:
        own_sub = person_to_sub.get(id(person))
        # Pick a different submission to host them
        candidates = [s for s in submissions if s is not own_sub]
        if not candidates:
            continue
        host = random.choice(candidates)

        relationship = random.choice(DUP_RELATIONSHIPS)
        inject_member_from_person(
            host.family_group,
            person,
            relationship=relationship,
            declarant_age=host.age,
            declarant_dob=host.person.date_of_birth,
            creation_date=host.creation_date,
        )
        injected += 1
    return injected


def inject_member_duplicates(submissions: list[Submission], n: int) -> int:
    """
    Pick `n` family members and replicate each into a second submission.
    These are simpler synthetic duplicates (same name + doc, no declarant link).
    """
    # Pool of (submission, member) pairs we can sample from
    member_pool = [
        (s, m) for s in submissions for m in s.family_group.members
        if m.source_person is None  # non-injected members only
    ]
    if not member_pool:
        return 0

    n = min(n, len(member_pool), len(submissions) // 2)
    injected = 0
    for _ in range(n):
        src_sub, src_member = random.choice(member_pool)
        # Pick a different host submission
        candidates = [s for s in submissions if s is not src_sub]
        if not candidates:
            continue
        host = random.choice(candidates)
        # Append a copy with possibly different relationship
        copy = type(src_member)(**{**src_member.__dict__,
                                   "relationship": random.choice(DUP_RELATIONSHIPS)})
        host.family_group.members.append(copy)
        injected += 1
    return injected


# ────────────────────────────────────────────────────────────────────────────
# Row rendering
# ────────────────────────────────────────────────────────────────────────────

def render_row(sub: Submission, *, doc_overlap_ratio: float) -> dict:
    """Convert a Submission into the final 20-column dict for the Excel row."""
    # Apply name perturbation at the row level (not at planning time, so the
    # canonical person remains intact for duplicate matching)
    perturbed = perturb(sub.person)

    creation_str = format_date(sub.creation_date, random.randint(0, 6))

    sex_internal = perturbed.sex if perturbed.sex in ("M", "F", "Other") else random_sex()
    sex_display = render_sex(sex_internal)

    nationality = render_nationality(perturbed.country_origin)
    province = render_province()

    dob_str = format_date(perturbed.date_of_birth, random.randint(0, 6))

    full_legal = render_full_legal_name(perturbed.full_name)

    # Document columns: with probability `doc_overlap_ratio` they share the
    # same underlying number; otherwise they diverge.
    force_match = random.random() < doc_overlap_ratio
    id_doc = render_identification_document(sub.declarant_doc)
    personal_doc = render_personal_document(sub.declarant_doc, force_match=force_match)

    marital = render_marital_status(
        age=sub.age,
        has_spouse_in_family=sub.family_group.has_spouse,
        has_children_in_family=sub.family_group.has_children,
    )

    family_text = render_family_group(sub.family_group)

    return {
        "Submission ID": sub.submission_id,
        "Submission UUID": "",
        "Created": creation_str,
        "Completed": creation_str,
        "Modified": creation_str,
        "Form Title": FORM_TITLE,
        "Identification Document": id_doc,
        "Phone": random_phone(),
        "Email": random_email(),
        "Full Name": perturbed.full_name,
        "Request Type": "Asylum",
        "Full Legal Name": full_legal,
        "Nationality": nationality,
        "Ethnic Identification": "",
        "Sex": sex_display,
        "Date of Birth": dob_str,
        "Personal Document": personal_doc,
        "Marital Status": marital,
        "Province of Residence": province,
        "Family Group Members": family_text,
    }


# ────────────────────────────────────────────────────────────────────────────
# Top-level entrypoint
# ────────────────────────────────────────────────────────────────────────────

def generate_dataset(
    gen_cfg: GenerationConfig,
    pg_cfg: PostgresConfig,
    *,
    csv_fallback: str | None = None,
) -> list[dict]:
    random.seed(gen_cfg.random_seed)

    print(f"[1/5] Loading match pool ({'CSV fallback' if csv_fallback else 'Postgres'})...")
    match_pool = load_match_pool(pg_cfg, csv_fallback=csv_fallback)
    print(f"      Loaded {len(match_pool)} persons.")

    print(f"[2/5] Planning composition for {gen_cfg.num_rows} rows "
          f"(match_ratio={gen_cfg.match_ratio:.0%}, dup_ratio={gen_cfg.duplicate_ratio:.0%})...")
    declarants, dup_pool = plan_composition(
        gen_cfg.num_rows,
        gen_cfg.match_ratio,
        gen_cfg.duplicate_ratio,
        match_pool,
    )
    print(f"      Match declarants: {sum(1 for p in declarants if p.is_match_pool)}")
    print(f"      Non-match declarants: {sum(1 for p in declarants if not p.is_match_pool)}")
    print(f"      Reserved for declarant→member duplication: {len(dup_pool)}")

    print("[3/5] Building submissions...")
    base_id = 90_000
    submissions = [
        build_submission(base_id + i * random.randint(1, 1), p)
        for i, p in enumerate(declarants)
    ]

    print("[4/5] Injecting duplicates...")
    n_decl_dups = inject_declarant_duplicates(submissions, dup_pool)
    n_member_dups = inject_member_duplicates(
        submissions,
        n=int(round(gen_cfg.num_rows * gen_cfg.duplicate_ratio * 0.5)),
    )
    print(f"      Declarant→member injections: {n_decl_dups}")
    print(f"      Member→member injections:    {n_member_dups}")

    print("[5/5] Rendering rows...")
    rows = [render_row(s, doc_overlap_ratio=gen_cfg.doc_overlap_ratio) for s in submissions]

    return rows
