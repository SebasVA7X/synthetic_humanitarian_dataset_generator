"""
Family group generator.

Each declarant may have 0–6 family members. Each member is rendered as a
fixed-format text block. Multiple members are joined by '\\n---\\n'.

Block format (labels exactly as required, no variations):

  First Name: <given>
  Last Name: <surnames>
  Relationship: <relationship>
  Nationality: <dirty nationality>
  Sex: <MALE|FEMALE|OTHER>
  Date of Birth: <date or noise>
  ID Type and number: <doc string>
  Entry date to Ecuador: <date or noise>

Family member ages are coherent with the declarant's age (children are at
least 15 years younger; parents at least 18 years older).
"""
import random
from dataclasses import dataclass, field
from datetime import date, timedelta

from gpo_synthetic.generators.dates import format_date
from gpo_synthetic.generators.demographics import render_nationality
from gpo_synthetic.generators.documents import render_family_member_document
from gpo_synthetic.generators.names import (
    PersonRecord, generate_nonmatch_person, parse_dob,
)

RELATIONSHIPS = [
    "Spouse", "Son/Daughter", "Mother", "Father",
    "Brother/Sister", "Grandparent", "Uncle/Aunt", "Nephew/Niece",
    "Cousin", "Brother-in-law/Sister-in-law", "Grandchild",
]

# Number of members distribution (0 to 6)
MEMBER_COUNT_WEIGHTS = [20, 15, 25, 20, 12, 6, 2]


@dataclass
class FamilyMember:
    """A single member with all the data needed to render the block."""
    given_name: str
    surname: str
    relationship: str
    nationality_raw: str
    sex_label: str             # MALE / FEMALE / OTHER
    date_of_birth: date | None
    dob_rendered: str
    doc_clean: str             # underlying clean number (may be empty)
    doc_rendered: str          # full rendered string for the block
    entry_date_rendered: str
    # Bookkeeping for duplicate linking
    source_person: PersonRecord | None = None


@dataclass
class FamilyGroup:
    members: list[FamilyMember] = field(default_factory=list)

    @property
    def has_spouse(self) -> bool:
        return any("Esposo" in m.relationship for m in self.members)

    @property
    def has_children(self) -> bool:
        return any(m.relationship in ("Hijo/a", "Hija") for m in self.members)


# ────────────────────────────────────────────────────────────────────────────
# Helpers
# ────────────────────────────────────────────────────────────────────────────

def _split_full_name(full_name: str) -> tuple[str, str]:
    """
    Split 'First Second Last1 Last2' into ('First Second', 'Last1 Last2').
    Falls back gracefully for shorter names.
    """
    tokens = full_name.split()
    if len(tokens) >= 4:
        return " ".join(tokens[:2]), " ".join(tokens[2:])
    if len(tokens) == 3:
        return " ".join(tokens[:2]), tokens[2]
    if len(tokens) == 2:
        return tokens[0], tokens[1]
    return full_name, ""


def _coherent_dob_for_relationship(
    declarant_age: int,
    declarant_dob: date,
    relationship: str,
) -> date | None:
    """Return a DOB consistent with the relationship, or None if 'unknown'."""
    if random.random() < 0.08:
        return None  # rendered as 'S/I' or similar

    today = date.today()

    if relationship in ("Hijo/a", "Hija", "Sobrino/a", "Nieto/a"):
        # Children/grandchildren are at least N years younger than declarant
        gap = 30 if relationship == "Nieto/a" else 15
        max_child_age = declarant_age - gap
        if max_child_age <= 0:
            # Declarant too young for this relationship — give a baby
            age = 0
        else:
            age = random.randint(0, max_child_age)

    elif relationship in ("Padre", "Madre", "Abuelo/a"):
        min_offset = 18 if relationship in ("Padre", "Madre") else 35
        age = declarant_age + random.randint(min_offset, min_offset + 25)
        if age > 95:
            age = random.randint(60, 95)

    elif relationship.startswith("Esposo"):
        # Spouse: ±10 years from declarant
        age = max(18, declarant_age + random.randint(-10, 10))

    elif relationship.startswith("Hermano") or relationship == "Hermana":
        age = max(0, declarant_age + random.randint(-15, 15))

    else:
        age = max(1, declarant_age + random.randint(-25, 25))

    candidate = today - timedelta(days=age * 365 + random.randint(-180, 180))
    # Hard guard: never return a future DOB
    if candidate >= today:
        candidate = today - timedelta(days=random.randint(30, 365))
    return candidate


def _render_dob(d: date | None) -> str:
    if d is None:
        return random.choice(["S/I", "no sabe", "aprox 2010", ""])
    return format_date(d, random.randint(0, 4))


def _render_entry_date(creation_date: date) -> str:
    if random.random() < 0.10:
        return random.choice(["S/I", "", "reciente"])
    days_ago = random.randint(30, 700)
    d = creation_date - timedelta(days=days_ago)
    return format_date(d, random.randint(0, 2))


def _sex_label(internal_code: str) -> str:
    return {"M": "MALE", "F": "FEMALE", "Other": "OTHER"}.get(internal_code, "OTHER")


# ────────────────────────────────────────────────────────────────────────────
# Member builder
# ────────────────────────────────────────────────────────────────────────────

def _build_member_from_person(
    person: PersonRecord,
    *,
    relationship: str,
    declarant_age: int,
    declarant_dob: date,
    creation_date: date,
) -> FamilyMember:
    """Build a FamilyMember using an existing PersonRecord (used for duplicates)."""
    given, surname = _split_full_name(person.full_name)

    # Use the person's actual DOB rather than a relationship-derived one,
    # because this is meant to *match* a declarant elsewhere.
    dob = person.date_of_birth

    doc_clean, doc_rendered = render_family_member_document()

    return FamilyMember(
        given_name=given,
        surname=surname,
        relationship=relationship,
        nationality_raw=render_nationality(person.country_origin),
        sex_label=_sex_label(person.sex),
        date_of_birth=dob,
        dob_rendered=_render_dob(dob),
        doc_clean=doc_clean,
        doc_rendered=doc_rendered,
        entry_date_rendered=_render_entry_date(creation_date),
        source_person=person,
    )


def _build_random_member(
    *,
    declarant_age: int,
    declarant_dob: date,
    declarant_country: str,
    creation_date: date,
    relationship: str,
) -> FamilyMember:
    """Build a synthetic family member (not linked to any declarant)."""
    person = generate_nonmatch_person(target_country=declarant_country)
    given, surname = _split_full_name(person.full_name)

    dob = _coherent_dob_for_relationship(declarant_age, declarant_dob, relationship)
    doc_clean, doc_rendered = render_family_member_document()

    return FamilyMember(
        given_name=given,
        surname=surname,
        relationship=relationship,
        nationality_raw=render_nationality(declarant_country),
        sex_label=_sex_label(person.sex),
        date_of_birth=dob,
        dob_rendered=_render_dob(dob),
        doc_clean=doc_clean,
        doc_rendered=doc_rendered,
        entry_date_rendered=_render_entry_date(creation_date),
        source_person=None,
    )


# ────────────────────────────────────────────────────────────────────────────
# Public: build a family group for a declarant
# ────────────────────────────────────────────────────────────────────────────

def build_family_group(
    *,
    declarant_age: int,
    declarant_dob: date,
    declarant_country: str,
    creation_date: date,
    n_members: int | None = None,
) -> FamilyGroup:
    """
    Build a family group for a given declarant.
    Optional injected members (for duplicate scenarios) can be appended later
    by the orchestrator using `inject_member`.
    """
    if n_members is None:
        n_members = random.choices(range(7), weights=MEMBER_COUNT_WEIGHTS)[0]

    members = []
    has_spouse = False

    for _ in range(n_members):
        if not has_spouse and random.random() < 0.40:
            relationship = "Esposo/a"
            has_spouse = True
        else:
            relationship = random.choice(RELATIONSHIPS)

        members.append(_build_random_member(
            declarant_age=declarant_age,
            declarant_dob=declarant_dob,
            declarant_country=declarant_country,
            creation_date=creation_date,
            relationship=relationship,
        ))

    return FamilyGroup(members=members)


def inject_member_from_person(
    fg: FamilyGroup,
    person: PersonRecord,
    *,
    relationship: str,
    declarant_age: int,
    declarant_dob: date,
    creation_date: date,
) -> None:
    """Append an externally provided person to a family group (duplicate link)."""
    fg.members.append(_build_member_from_person(
        person,
        relationship=relationship,
        declarant_age=declarant_age,
        declarant_dob=declarant_dob,
        creation_date=creation_date,
    ))


# ────────────────────────────────────────────────────────────────────────────
# Render to free-text block
# ────────────────────────────────────────────────────────────────────────────

def render_family_group(fg: FamilyGroup) -> str:
    if not fg.members:
        return ""

    blocks = []
    for m in fg.members:
        blocks.append(
            f"First Name: {m.given_name}\n"
            f"Last Name: {m.surname}\n"
            f"Relationship: {m.relationship}\n"
            f"Nationality: {m.nationality_raw}\n"
            f"Sex: {m.sex_label}\n"
            f"Date of Birth: {m.dob_rendered}\n"
            f"ID Type and Number: {m.doc_rendered}\n"
            f"Entry Date to Ecuador: {m.entry_date_rendered}"
        )
    return "\n---\n".join(blocks)
