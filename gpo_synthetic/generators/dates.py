"""Date generation and multi-format string rendering."""
import random
from datetime import date, datetime, timedelta

# Creation date span: March-May 2024
CREATED_MIN = date(2024, 3, 1)
CREATED_MAX = date(2024, 5, 31)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
    "%Y-%m-%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
]


def random_date_in_range(min_d: date, max_d: date) -> date:
    delta = (max_d - min_d).days
    return min_d + timedelta(days=random.randint(0, delta))


def format_date(d: date, style: int | None = None) -> str:
    """Render a date in one of the supported messy formats."""
    if style is None:
        style = random.randint(0, len(DATE_FORMATS) - 1)
    fmt = DATE_FORMATS[style % len(DATE_FORMATS)]

    if "%H" in fmt:
        dt = datetime(d.year, d.month, d.day,
                      random.randint(7, 22), random.randint(0, 59))
        return dt.strftime(fmt)
    return d.strftime(fmt)


def random_creation_date() -> date:
    return random_date_in_range(CREATED_MIN, CREATED_MAX)


def adult_dob_for(creation: date, min_age: int = 18, max_age: int = 65) -> date:
    """Random adult DOB consistent with a creation date reference."""
    age = random.randint(min_age, max_age)
    base = creation.replace(year=creation.year - age)
    jitter = random.randint(-365, 365)
    return base + timedelta(days=jitter)
