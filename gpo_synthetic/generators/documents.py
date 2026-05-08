"""
Identification document generator.

All synthetic IDs start with a 2-character alphanumeric prefix that does NOT
correspond to any real-world ID issuer (e.g., '9X', 'P6', 'Z3'). Combined with
random digits, this guarantees that no synthetic ID can collide with a real
person's identification.

Passports use 'ZZ' or 'XX' prefixes (also non-real).
"""
import random
import string

# Letter set excluding ones that look like digits (I, O) or are too common
_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ"
_DIGITS = string.digits


def _random_cedula_prefix() -> str:
    """Two chars: letter+digit or digit+letter, never a real-world pattern."""
    if random.random() < 0.5:
        return random.choice("9876") + random.choice(_LETTERS)
    return random.choice(_LETTERS) + random.choice("9876")


def random_cedula_number() -> str:
    """Synthetic id card: prefix (2 chars) + 7-9 digits."""
    prefix = _random_cedula_prefix()
    digits = "".join(random.choices(_DIGITS, k=random.randint(7, 9)))
    return f"{prefix}{digits}"


def random_passport_number() -> str:
    """Synthetic passport: 'ZZ' or 'XX' + 6-8 digits."""
    prefix = random.choice(["ZZ", "XX"])
    digits = "".join(random.choices(_DIGITS, k=random.randint(6, 8)))
    return f"{prefix}{digits}"


def random_clean_doc() -> str:
    """A clean, well-formed synthetic document (cedula or passport)."""
    if random.random() < 0.75:
        return random_cedula_number()
    return random_passport_number()


# ────────────────────────────────────────────────────────────────────────────
# "Identification Document" column — mostly raw numbers, some noise
# ────────────────────────────────────────────────────────────────────────────

def render_identification_document(clean_doc: str) -> str:
    """
    Render the value for the 'Identification Document' column.
    This column tends to hold the raw number with light noise.
    """
    r = random.random()
    if r < 0.05:
        return ""
    if r < 0.12:
        return random.choice(["S/D", "SIN DOCUMENTO", "N/A", "PASAPORTE"])
    if r < 0.20:
        # Some leading/trailing whitespace
        return f"  {clean_doc} "
    return clean_doc


# ────────────────────────────────────────────────────────────────────────────
# "Personal Document" column — open text with type and number
# ────────────────────────────────────────────────────────────────────────────

DOC_TYPES = [
    "CEDULA", "Cédula", "PASAPORTE", "Pasaporte", "DNI",
    "CARNET", "CC", "CI", "Cédula Extranjera",
]

SEPARATORS = [" // ", " / ", "//", " - ", ": ", " "]


def render_personal_document(clean_doc: str, *, force_match: bool) -> str:
    """
    Render the value for the 'Personal Document' column.

    If force_match=True, the underlying number is the same as the one passed in
    (clean_doc), but wrapped in noisy formatting (type label, separator, etc.).

    If force_match=False, the value will *not* contain the same number as
    clean_doc — it will hold noise, a different number, or be empty. This is
    used to simulate the ~22% mismatch rate between the two document columns.
    """
    if force_match:
        return _wrap_with_type(clean_doc)

    r = random.random()
    if r < 0.30:
        return ""
    if r < 0.45:
        return random.choice(DOC_TYPES)
    if r < 0.65:
        return f"{random.choice(DOC_TYPES)} {random.choice(['S/D', 'N/A', 'NO TIENE'])}"
    # A different (also synthetic) number
    return _wrap_with_type(random_clean_doc())


def _wrap_with_type(doc: str) -> str:
    tipo = random.choice(DOC_TYPES)
    sep = random.choice(SEPARATORS)

    if random.random() < 0.10:
        return f"{tipo}{sep}{doc} ACTA {random.randint(1, 500)}"

    if random.random() < 0.05:
        return f"{tipo}{sep}{doc.lower()}"

    return f"{tipo}{sep}{doc}"


# ────────────────────────────────────────────────────────────────────────────
# Family member document — the same logic but as a single string
# ────────────────────────────────────────────────────────────────────────────

def render_family_member_document() -> tuple[str, str]:
    """
    Returns a tuple (clean_doc, rendered_string) for a family member.

    The rendered string has heavy noise (typical of free-text input) but the
    clean_doc is the canonical underlying number (used for duplicate linking
    when this member is also a declarant elsewhere).
    """
    r = random.random()

    if r < 0.12:
        return "", ""
    if r < 0.20:
        return "", random.choice(["S/D", "SIN DOCUMENTO", "N/A", "MENOR", "NINGUNO"])

    clean = random_clean_doc()

    if r < 0.65:
        sep = random.choice(["/", " ", "/ ", " / ", "-"])
        return clean, f"CEDULA{sep}{clean}"

    if r < 0.80:
        sep = random.choice(["/", " ", ""])
        prefix = random.choice(["PASAPORTE", "Pasaporte", "PAS"])
        return clean, f"{prefix}{sep}{clean}"

    if r < 0.90:
        return clean, clean

    return clean, f"CC{clean}"
