"""
Demographic categorical generators: nationality (with ISO mapping to dirty
strings), marital status (correlated with family group), and province.
"""
import random


# ────────────────────────────────────────────────────────────────────────────
# Nationality: map country_origin (ISO-ish) to dirty free-text variants
# ────────────────────────────────────────────────────────────────────────────

NATIONALITY_VARIANTS: dict[str, list[str]] = {
    "VEN": [
        "VENEZOLANA", "Venezolana", "venezolana", "VENEZUELA", "Venezuela",
        "Venezolano", "VENEZOLANO", "venezolano", "VEN", "venez.",
        "Venezolana (VEN)", "República Bolivariana de Venezuela",
    ],
    "COL": [
        "COLOMBIANA", "Colombiana", "colombiana", "COLOMBIA", "Colombia",
        "Colombiano", "COL", "colomb.", "colombiana.",
    ],
    "CUB": [
        "CUBANA", "cubana", "CUBA", "Cuba", "Cubano", "CUBANO",
    ],
    "HTI": [
        "HAITIANA", "haitiana", "HAITI", "Haiti", "Haití", "Haitiano",
        "HAITIANO",
    ],
    "PER": [
        "PERUANA", "peruana", "PERU", "Perú", "Peruano", "PER",
    ],
    "SYR": [
        "SIRIA", "Siria", "siria", "SYRIA", "Syria", "Sirio", "SIRIO",
    ],
    "STA": [
        "APATRIDA", "Apatrida", "Apátrida", "APÁTRIDA", "Sin nacionalidad",
        "S/N", "STATELESS", "Stateless",
    ],
    "OTHER": [
        "BOLIVIANA", "Boliviana", "BOLIVIA",
        "NICARAGÜENSE", "Nicaragüense", "NICARAGUA",
        "DOMINICANA", "Dominicana",
        "HONDUREÑA", "Hondureña",
        "CHILENA", "Chilena",
        "ARGENTINA", "Argentina",
        "SALVADOREÑA", "PANAMEÑA",
        "extranjero",
    ],
}

# Generic noise that can replace any value
NATIONALITY_NOISE = ["No sé", "S/I", "N/A", "", "no sabe"]


def render_nationality(country_origin: str) -> str:
    """Map an ISO code to a dirty free-text nationality value."""
    if random.random() < 0.04:
        return random.choice(NATIONALITY_NOISE)

    pool = NATIONALITY_VARIANTS.get(country_origin)
    if not pool:
        pool = NATIONALITY_VARIANTS["OTHER"]
    return random.choice(pool)


# ────────────────────────────────────────────────────────────────────────────
# Sex
# ────────────────────────────────────────────────────────────────────────────

SEX_DISPLAY = {
    "M": "Male",
    "F": "Female",
    "Other": "Other",
}


def render_sex(internal_code: str) -> str:
    return SEX_DISPLAY.get(internal_code, "Otro")


def random_sex() -> str:
    """Generate a sex code respecting the 47/52/1 distribution."""
    return random.choices(["M", "F", "Other"], weights=[47, 52, 1])[0]


# ────────────────────────────────────────────────────────────────────────────
# Marital Status — correlated with family group + age
# ────────────────────────────────────────────────────────────────────────────

MARITAL_STATUSES = [
    "Single", "Married", "Cohabiting",
    "Divorced", "Widowed", "Separated",
]


def render_marital_status(
    *,
    age: int,
    has_spouse_in_family: bool,
    has_children_in_family: bool,
) -> str:
    """
    Pick a marital status that is consistent with the declared family group.

    Rules:
      - If a spouse appears in the family group → Married or Cohabiting
      - If children but no spouse → Single/Divorced/Separated/Widowed (older)
      - Single declarant → broad demographic distribution by age
    """
    if has_spouse_in_family:
        return random.choices(
            ["Married", "Cohabiting"],
            weights=[60, 40],
        )[0]

    if has_children_in_family:
        if age >= 50:
            return random.choices(
                ["Divorced", "Widowed", "Separated", "Single"],
                weights=[40, 25, 25, 10],
            )[0]
        return random.choices(
            ["Single", "Divorced", "Separated", "Cohabiting"],
            weights=[40, 25, 25, 10],
        )[0]

    # No family group declared
    if age < 25:
        return random.choices(
            ["Single", "Cohabiting", "Married"],
            weights=[75, 20, 5],
        )[0]
    if age < 50:
        return random.choices(
            ["Single", "Married", "Cohabiting", "Divorced", "Separated"],
            weights=[35, 30, 20, 10, 5],
        )[0]
    return random.choices(
        ["Married", "Widowed", "Divorced", "Separated", "Single"],
        weights=[40, 25, 15, 10, 10],
    )[0]

# ────────────────────────────────────────────────────────────────────────────
# Province of Residence
# ────────────────────────────────────────────────────────────────────────────

PROVINCES = [
    "Pichincha", "Guayas", "El Oro", "Azuay", "Manabí",
    "Tungurahua", "Imbabura", "Loja", "Carchi", "Esmeraldas",
    "Santo Domingo de los Tsáchilas", "Santa Elena", "Sucumbíos",
    "Orellana", "Los Ríos", "Bolívar", "Chimborazo", "Cotopaxi",
    "Morona Santiago", "Pastaza", "Napo", "Zamora Chinchipe",
    "Galápagos", "Cañar",
]
PROVINCE_WEIGHTS = [
    25, 20, 8, 7, 6,
    4, 4, 3, 3, 3,
    3, 2, 2,
    2, 2, 1, 1, 1,
    1, 1, 1, 1,
    0.5, 0.5,
]


def render_province() -> str:
    return random.choices(PROVINCES, weights=PROVINCE_WEIGHTS)[0]
