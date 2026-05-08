"""Phone and email generators with realistic noise."""
import random
import string

from faker import Faker

_fake = Faker("en_US")

# Fictional prefixes — never start with real prefixes
PHONE_PREFIXES_FICTIONAL = ["+5878", "+5892", "+5834", "042", "072", "+5810", "+5820"]

EMAIL_DOMAINS_FICTIONAL = [
    "mailbox.zz", "correo.xy", "inbox.qx", "personal.vv",
    "webmail.zt", "mifamilia.ww", "hogar.xq", "netmail.yy",
]


def random_phone() -> str:
    """Generate a phone string with realistic noise. Never starts with real prefixes."""
    r = random.random()

    if r < 0.08:
        return ""

    if r < 0.15:
        return "".join(random.choices(string.ascii_letters + "  ", k=8))

    if r < 0.20:
        prefix = random.choice(PHONE_PREFIXES_FICTIONAL)
        digits = "".join(random.choices(string.digits, k=random.randint(4, 7)))
        return f"{prefix}{digits}"

    if r < 0.25:
        return f"++{random.randint(10, 99)}{random.randint(1000000, 9999999)}"

    if r < 0.30:
        first = random.choice("12345678")
        rest = "".join(random.choices(string.digits, k=8))
        return f"0{first}{rest}"

    prefix = random.choice(PHONE_PREFIXES_FICTIONAL)
    digits = "".join(random.choices(string.digits, k=random.randint(6, 9)))
    return f"{prefix}{digits}"


def random_email() -> str:
    user = _fake.user_name().replace(".", random.choice(["_", ".", ""]))
    return f"{user}@{random.choice(EMAIL_DOMAINS_FICTIONAL)}"
