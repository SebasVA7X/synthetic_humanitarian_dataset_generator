# Refugee and Asylum Network and Generic Partner Organization — Synthetic Dataset


A two-stage synthetic data generator built around a fictional social-services agency's Refugee Status Determination (RSD) workflow and a generic partner organization parallel registration webform, designed to drive portfolio-grade BI and Data Engineering projects while ensuring no real individual, case, or operational record can be identified or reconstructed from it.

The dataset is generated in two stages: Stage 1 populates a PostgreSQL OLTP database covering the full RSD case lifecycle; Stage 2 consumes that database to produce a synthetic Excel webform export. The schema and business logic are inspired by domain experience with humanitarian case-management systems (anonymized).

---

## Pipeline overview

```
┌──────────────────────┐      ┌────────────────────────┐      ┌──────────────────────┐      ┌──────────────────────┐
│ Stage 1: OLTP        │      │ Postgres               │      │ Stage 2:             │      │ Excel origin file    │
│ generators           │ ───▶ │ ran_system database    │ ───▶ │ gpo_synthetic        │ ───▶ │ (GPO webform export  │
│ (sql/ + python -m …) │      │ (~55 K rows, 12 tables)│      │ origin generator     │      │  simulation)         │
└──────────────────────┘      └────────────────────────┘      └──────────────────────┘      └──────────────────────┘
```

- **Stage 1** builds the source-of-truth OLTP database — registration groups, individuals, admissibility assessments, eligibility assessments, recommendations, reviews, appeals, and certificates — with causally ordered timestamps and configurable volumes/distributions.
- **Stage 2** reads `dim_individual` and emits a synthetic Excel webform file that the schema and data-quality issues of field humanitarian organizations GPO export (typos, document-overlap noise, intentional duplicates).

The two stages share a single `.env` and one root `requirements.txt`. Stage 2 is a pure consumer of Stage 1's output — the dependency runs in one direction only.
The objective of stage 2 is to generate a parallel registration process, which is commonly found on the field. 

---

## Project structure

```
.
├── env.example                  Template — copy to .env (covers both stages)
├── requirements.txt             Combined deps for stage 1 + stage 2
├── README.md
├── reset_and_seed.py            One-shot reset: drops all tables, re-applies sql/, runs Stage 1
├── sql/
│   ├── 01_schema.sql            DDL: tables, indexes, deferred FK constraints
│   └── 02_catalogs.sql          Static lookup data (offices, statuses, decision codes)
├── core/                        Shared helpers (used by stage 1)
│   ├── config.py                Tuneable parameters — volumes, weights, date range
│   └── db.py                    PostgreSQL connection + batch-insert helper
├── dimensions/                  Stage 1 dimensions
│   └── generate_dims.py         Generates dim_user; exposes generate_individuals
├── facts/                       Stage 1 facts
│   └── generate_facts.py        Generates remaining dims and all fact tables
├── incremental/                 Stage 1 incremental loader
│   └── insert_incremental.py    Adds new records without duplicating existing rows
└── gpo_synthetic/               Stage 2 — see gpo_synthetic/README.md for full details
    ├── __main__.py              CLI entrypoint
    ├── config.py                .env loader (DB_* + RAN_*)
    ├── orchestrator.py          Drives the full generation flow
    ├── schema.py                Canonical 20-column output schema
    ├── generators/              Per-field generators (names, dates, docs, etc.)
    ├── sources/                 dim_individual loader (Postgres + CSV fallback)
    └── writers/                 Excel writer
```

Each Python folder is a package — scripts run as modules from the project root (`python -m <package>.<module>`), so package-relative imports resolve correctly.

---

## Prerequisites

- Python 3.9+
- PostgreSQL 13+ (local or remote)
- All Python dependencies are listed in [`requirements.txt`](requirements.txt) (`psycopg2-binary`, `faker`, `python-dotenv`, `pandas`, `openpyxl`)

---

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp env.example .env
# Edit .env with your PostgreSQL credentials and (optionally) generation parameters
```

`.env` variables:

| Variable | Default                              | Description |
|---|--------------------------------------|---|
| `DB_HOST` | `localhost`                          | PostgreSQL host |
| `DB_PORT` | `5432`                               | PostgreSQL port |
| `DB_NAME` | `your_psql_database`                 | Database name |
| `DB_USER` | `postgres`                           | Database user |
| `DB_PASSWORD` | _(required)_                         | Database password — no default |
| `RAN_SOURCE_SCHEMA` | `public`                             | Stage 2 — schema where `dim_individual` lives |
| `RAN_SOURCE_TABLE` | `dim_individual`                     | Stage 2 — source table name |
| `RAN_NUM_ROWS` | `1154`                               | Stage 2 — number of synthetic submissions |
| `RAN_MATCH_RATIO` | `0.56`                               | Stage 2 — fraction sourced from `dim_individual` |
| `RAN_DUPLICATE_RATIO` | `0.10`                               | Stage 2 — duplicate-injection rate |
| `RAN_DOC_OVERLAP_RATIO` | `0.78`                               | Stage 2 — fraction of rows where ID and personal-doc share a number |
| `GPO_OUTPUT_PATH` | `./output/gpo_synthetic_origin.xlsx` | Stage 2 — Excel output path |
| `RAN_RANDOM_SEED` | `42`                                 | Stage 2 — reproducibility seed |

---

## End-to-end workflow

For a full run from a clean machine:

```bash
# 0. Clone, venv, install, configure
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp env.example .env                           # edit DB_PASSWORD

# 1. Stage 1 — populate Postgres (one-shot)
python reset_and_seed.py                      # drops + recreates schema + catalogs + all dims/facts

# 2. Stage 2 — generate the origin Excel
python -m gpo_synthetic                       # writes GPO_OUTPUT_PATH
```

`reset_and_seed.py` is the recommended path for a clean run: it drops every table in the public schema, re-applies `sql/01_schema.sql` and `sql/02_catalogs.sql`, then runs the full Stage 1 pipeline in one command. If you'd rather drive each step manually, see [Stage 1 — Generate the OLTP database](#stage-1--generate-the-oltp-database) below.

After this, you'll have:
- A populated `ran_system` Postgres database (~55 K rows across 12 tables).
- `output/gpo_synthetic_origin.xlsx` — the synthetic webform export.

---

## Stage 1 — Generate the OLTP database

### Step 1.0. (Recommended) Reset and seed in one command

```bash
python reset_and_seed.py
```

Runs steps 1.1 → 1.3 below in sequence: prompts for confirmation, drops every table in the `public` schema, re-applies `sql/01_schema.sql` and `sql/02_catalogs.sql`, then generates users, registration groups, individuals, and all facts. Use this whenever you want a clean database from scratch.

> **Destructive.** It deletes every table in the schema before recreating them. Intended for local/dev use only. Never to be used in a production database.

If you'd rather run each step yourself (e.g. to inspect intermediate state), follow steps 1.1–1.3 below.

### Step 1.1. Create the schema

```bash
psql -d ran_system -f sql/01_schema.sql
psql -d ran_system -f sql/02_catalogs.sql
```

`sql/01_schema.sql` enables the `uuid-ossp` extension and creates all tables and indexes. `sql/02_catalogs.sql` seeds the static lookup tables (offices, legal statuses, decision codes, etc.).

### Step 1.2. Generate users

```bash
python -m dimensions.generate_dims
```

Creates ~50 case-worker users in `dim_user`, weighted by office.

### Step 1.3. Generate dimensions and facts

```bash
python -m facts.generate_facts
```

Creates `dim_registration_group`, `dim_individual` (with demographics), and all fact tables in dependency order. Each generator enforces causal date ordering — every record's `created_at` falls strictly after its parent's.

> **Order matters.** `facts.generate_facts` reads `dim_user` on startup and will raise an error if step 1.2 hasn't run.

### Step 1.4. (Optional) Incremental inserts

`incremental/insert_incremental.py` appends new records to an already-populated database without touching existing rows. All inserts use `ON CONFLICT DO NOTHING`, and sequential IDs (`IND-`, `ADM-`, `ELG-`) continue from the current database maximum.

**Note:** This pipeline generates inconsistencies on purpose, e.g., an admitted case could have an appellation recommendation and decision. This is to reflect inconsistencies that are commonly found in the field due to migrations or incorrect data entry. 

```bash
python -m incremental.insert_incremental                          # ~10 % of initial load (defaults)
python -m incremental.insert_incremental --rg 500 --ind 1000      # custom registration groups + individuals
python -m incremental.insert_incremental --adm 300 --elg 200 --cert 400
```

Available flags: `--rg`, `--ind`, `--adm`, `--adm-int`, `--adm-dec`, `--elg`, `--elg-rec`, `--elg-rev`, `--app-rec`, `--app-dec`, `--cert`.

---

## Stage 2 — Generate the GPO origin Excel

`gpo_synthetic` reads `dim_individual` (or a CSV fallback) and writes a synthetic 20-column Excel webform export. See [`gpo_synthetic/README.md`](gpo_synthetic/README.md) for the full output schema, match-tier distribution, and synthetic-ID safety rules.

### Step 2.1. Run the generator

```bash
# Postgres mode (default — reads from dim_individual via DB_* env vars)
python -m gpo_synthetic

# CSV fallback (offline, no Postgres needed)
python -m gpo_synthetic --csv path/to/dim_individual.csv
```

Output is written to `GPO_OUTPUT_PATH` (default: `./output/gpo_synthetic_origin.xlsx`).

### Step 2.2. Tune generation knobs

All Stage 2 behaviour is controlled by `RAN_*` env vars (see the table in [Setup](#2-configure-environment)). Key levers:

- **`RAN_NUM_ROWS`** — how many submissions to emit.
- **`RAN_MATCH_RATIO`** — split between `dim_individual`-sourced rows (matchable downstream) and pure-Faker non-matches.
- **`RAN_DUPLICATE_RATIO`** — fraction of rows participating in intentional duplicate scenarios (declarant→member or member→member across submissions).
- **`RAN_DOC_OVERLAP_RATIO`** — how often `Identification Document` and `Personal Document` columns share the same underlying number (a real-world data-quality issue).
- **`GPO_OUTPUT_PATH`** — output Excel file path.
- **`RAN_RANDOM_SEED`** — fix this for reproducible runs.

---

## Data Model (Stage 1)

### Lifecycle ordering

```
Registration Group Registration → Individual Registration
                                → Certificate Issuance
                                → Admissibility Assessment → Interview / Decision
                                    → Eligibility Assessment → Recommendation → Review
                                                                                       → Appeal Recommendation → Appeal Decision
```

To not overcomplicate the dataset, all dates respect this causal ordering. Each record is created **after** its parent. The two-phase structure (admissibility → eligibility) follows established practice: admissibility determines whether a claim should be examined in substance; eligibility is that substantive examination. See [UNHCR & IPU, *A Guide to International Refugee Protection and Building State Asylum Systems* (2011), §7.6](https://www.unhcr.org/sites/default/files/legacy-pdf/3d4aba564.pdf) for more information.

**Note:** The admissibility → eligibility ordering is a logical dependency, not a referential one. The schema intentionally omits a FK between `fact_eligibility` and `fact_admissibility` to reflect operational realities in humanitarian settings, where this link cannot always be guaranteed.

### Dimensions

| Table | Key format | Description |
|---|---|---|
| `dim_office` | SERIAL | Seven regional offices in Ecuador |
| `dim_user` | UUID | Case workers assigned to an office |
| `dim_registration_group` | UUID | Household/family registration units |
| `dim_individual` | `IND-000001` | Persons of concern; SCD Type 1 |

### Catalog Tables (`cat_*`)

Closed-list lookup tables for all coded fields: process status, country of origin, legal status, admissibility decisions, decision basis, notification types, process types, eligibility recommendations, recommendation reasons, review decisions, appeal recommendations, appeal decisions, certificate types, and reviewer categories.

### Facts

| Table                        | Key format | Description                                         |
|------------------------------|---|-----------------------------------------------------|
| `fact_admissibility`         | `ADM-000001` | Initial admissibility assessment                    |
| `fact_adm_interview`         | UUID | Interview conducted during admissibility assessment |
| `fact_adm_decision`          | UUID | Formal admissibility decision                       |
| `fact_eligibility`           | `ELG-000001` | Full Refugee Status Determination case              |
| `fact_elg_recommendation`    | `ELG-*` (1-to-1) | Examiner's recommendation on the case               |
| `fact_elg_review`            | `ELG-*` (1-to-1) | Supervisor review of the recommendation             |
| `fact_appeal_recommendation` | `ELG-*` (1-to-1) | Appeal body recommendation                          |
| `fact_appeal_decision`       | `ELG-*` (1-to-1) | Final appeal decision                               |
| `fact_certificate`           | UUID | Documents issued to individuals                     |

---

## Default Volumes

Configured in [`core/config.py`](core/config.py):

| Entity                    | Count |
|---------------------------|---|
| Users                     | 50 |
| Registration groups       | 3 000 |
| Individuals               | 12 000 |
| Admissibility assessments | 8 000 |
| Adm. interviews           | 7 500 |
| Adm. decisions            | 5 000 |
| Eligibility assessments   | 4 500 |
| Elg. recommendations      | 3 800 |
| Elg. reviews              | 2 500 |
| Appeal recommendations    | 550 |
| Appeal decisions          | 300 |
| Certificates              | 5 500 |

Date range: **2019-01-01 → 2025-12-31**

---

## Population Weights

All distributions can be tuned in `core/config.py`.

**Country of origin**

| Country   | Weight |
|-----------|---|
| Venezuela | 62% |
| Colombia  | 25% |
| Stateless | 4% |
| Cuba      | 3% |
| Peru      | 2% |
| Haiti     | 2% |
| Syria     | 1% |
| Lebanon    | 1% |

**Office caseload**

| Office    | Weight |
|-----------|---|
| Quito     | 45% |
| Guayaquil | 20% |
| Manta     | 9% |
| El Puyo   | 9% |
| Cuenca    | 8% |
| Riobamba  | 6% |
| Macara    | 3% |

**Legal status** — ~54% asylum seekers, ~29% recognized refugees, remainder spread across other categories.

**Demographics** — 52% female / 48% male; age distribution weighted toward working-age adults (60%) and minors (35%).

---

## Design Notes

- **Two-stage pipeline** — Stage 1 owns the operational truth (Postgres OLTP); Stage 2 owns the data-quality simulation (Excel origin). The unidirectional dependency keeps each stage's responsibilities clear.
- **SCD Type 1 for `dim_individual`** — `dim_individual` always reflects current state; historical snapshots are not tracked.
- **One admissibility assessment per individual** — the process assumes a single assessment per individual as the operative record.
- **Causal date ordering** — every fact generator enforces that its timestamps fall strictly after the parent record's timestamp, preventing impossible timelines in analysis.
- **`ON CONFLICT DO NOTHING`** — all stage-1 inserts are idempotent; re-running a generator adds only new records without duplicates.
- **CSV fallback in Stage 2** — `python -m gpo_synthetic --csv …` lets you generate the origin Excel without spinning up Postgres, useful for portable demos and CI.

---

## Extending the Dataset

**Stage 1 volumes/distributions:** edit the `N_*` constants and `*_WEIGHTS` dictionaries in [`core/config.py`](core/config.py). No code changes needed.

**Stage 2 generation knobs:** adjust `RAN_*` env vars in `.env` (number of rows, match ratio, duplicate ratio, doc overlap, seed).

**To add a new fact table (Stage 1):**

1. Add the DDL to `sql/01_schema.sql` and any lookup rows to `sql/02_catalogs.sql`.
2. Write a `generate_<table>(conn, refs, parent_ids)` function in `facts/generate_facts.py` following the existing pattern (sample from parent IDs → enforce date ordering → batch insert).
3. Call it in the `if __name__ == "__main__"` block after its dependencies.

---

## Ethical Constraints and Data Anonymization

This dataset is entirely synthetic. The following measures were taken to ensure it cannot be linked to any real individuals, cases, or organizations.

### No real personal data

All personally identifiable information is generated by the [Faker](https://faker.readthedocs.io/) library at runtime:

- **Full names** (`dim_individual.full_name`, `dim_user.username`, all Stage 2 names) are random English-locale names produced by `Faker('en_US')`. They bear no relation to any actual refugee, asylum seeker, or case worker.
- **Dates of birth** are computed from randomized age buckets relative to a fixed reference date; no real birth dates are used.
- **Case IDs** (`IND-`, `ADM-`, `ELG-`) are sequential counters that start at 1 with each fresh generation. They are not derived from, nor do they resemble, any real case or file number.
- **User IDs** are random UUIDs; none correspond to real staff identifiers from any organization.
- **Stage 2 identification documents** begin with synthetic 2-character prefixes (e.g. `9X`, `P6`, `Z3`) that do not exist in real LATAM ID systems; passports use `ZZ`/`XX` prefixes. See [`gpo_synthetic/README.md`](gpo_synthetic/README.md) for full details on synthetic-ID safety.

### Source system thoroughly anonymized

The schema structure and workflow logic are adapted from observations of a real humanitarian data system. The following steps were taken during that adaptation:

- **This database does not recreate real document ID numbers, phones, names, addresses, or any potential individual identifier.**
- **Office names** are real Ecuadorian cities used publicly by humanitarian organizations; no internal office codes, unit names, or organizational identifiers from the source system are reproduced.
- **Decision and status codes** (e.g., `ADM`, `INAD`, `BASIS_ADMITTED`) are generic labels derived from publicly documented RSD procedure categories. They do not reproduce any proprietary code tables, internal terminology, or system-specific enumerations from the source.
- **Numeric catalog codes** are opaque integers with no semantic meaning beyond uniquely identifying each catalog entry.
- No case narratives, interview transcripts, legal findings, sensitive data, or any free-text content from the source system are present or referenced.

### Statistical distributions based on public information

Population weights for country of origin, legal status, decision outcomes, and demographics are informed by **publicly available aggregate statistics** from [UNHCR's Operational Data Portal](https://data.unhcr.org/en/country/ecu), [UNHCR's Refugee Statistics](https://www.unhcr.org/refugee-statistics) and open academic literature regarding Ecuador. No individual-level or operational dataset was used as a source.

### Intended use

This dataset is published for **educational and portfolio purposes only** (BI dashboards, data engineering pipelines, SQL practice). It must not be used to draw conclusions about actual refugee or asylum-seeker populations, real case outcomes, or the policies of any government or humanitarian organization.

---

## License

This project is released under the [MIT License](LICENSE).
