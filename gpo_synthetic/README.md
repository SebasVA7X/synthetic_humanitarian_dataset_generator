# GPO Synthetic Origin Generator

Generates a synthetic Excel file that mirrors the schema and data-quality
issues of the original GPO webform export.

## Setup

This stage shares the project's top-level `.env` (see the root [README](../README.md) for the `DB_*` variables) and the root `requirements.txt` (which already includes `pandas` and `openpyxl` for the Excel writer).

## Usage

Run from the project root.

### Postgres mode (default)

Reads from `dim_individual` (override schema/table via `RAN_SOURCE_SCHEMA` / `RAN_SOURCE_TABLE`):

```bash
python -m gpo_synthetic
```

### CSV fallback (offline)

For local development without a Postgres connection, point at a CSV with
columns `full_name`, `sex`, `date_of_birth`, `country_origin`:

```bash
python -m gpo_synthetic --csv path/to/dim_individual.csv
```

## Configuration

All parameters live in the project's top-level `.env` (template: [`env.example`](../.env.example)):

| Variable | Description | Default |
|---|---|---|
| `DB_*` | Postgres connection (shared with the OLTP stage) | — |
| `RAN_SOURCE_SCHEMA` | Source schema for `dim_individual` | `public` |
| `RAN_SOURCE_TABLE` | Source table | `dim_individual` |
| `RAN_NUM_ROWS` | Number of submissions to generate | 1154 |
| `RAN_MATCH_RATIO` | Fraction sourced from `dim_individual` (matchable in GPO) | 0.56 |
| `RAN_DUPLICATE_RATIO` | Fraction of intentional duplicates (split 50/50 between declarant→member and member→member) | 0.10 |
| `RAN_DOC_OVERLAP_RATIO` | Fraction of rows where `Identification Document` and `Personal Document` share the same underlying number | 0.78 |
| `GPO_OUTPUT_PATH` | Output Excel path | `./output/gpo_synthetic_origin.xlsx` |
| `RAN_RANDOM_SEED` | Seed for reproducibility | 42 |

## Output schema (18 columns)

```
Submission ID, Submission UUID, Created, Form Title,
Identification Document, Phone, Email, Full Name, Request Type,
Full Legal Name, Nationality, Ethnic Identification, Sex, Date of Birth,
Personal Document, Marital Status, Province of Residence, Family Group Members
```

## Project layout

```
gpo_synthetic/
├── README.md
├── __init__.py
├── __main__.py               # CLI entrypoint
├── config.py                 # .env loader
├── schema.py                 # Canonical column list
├── orchestrator.py           # Drives the full generation flow
├── sources/
│   └── postgres_source.py    # dim_individual loader (Postgres + CSV fallback)
├── generators/
│   ├── dates.py              # Date span (Mar–May 2024) + multi-format renderers
│   ├── contact.py            # Phone (random prefixes to avoid mirroring real numbers) + email
│   ├── documents.py          # Synthetic IDs with non-real prefixes (9X, P6, ZZ…)
│   ├── names.py              # Match/non-match pools + perturbations
│   ├── demographics.py       # Nationality (ISO→dirty), sex, marital, province
│   └── family.py             # Family group blocks with relationship coherence
└── writers/
    └── excel_writer.py       # Final Excel writer
```

## Match-tier distribution (within the 56% match pool)

| Share | Perturbation | Downstream rule fired |
|---|---|---|
| 60% | Identical | `STRONG_A_NAME_EQ_DOB_EQ` |
| 25% | One-character typo | `STRONG_B_NAME96_DOB_EQ` |
| 10% | Token reorder | Token-sort match |
| 5%  | DOB day shift | `RESCUE_NAME97_DOB_YYYYMM` |

## Synthetic ID safety

All identification numbers begin with a 2-character alphanumeric prefix that does not exist in any real-world ID system (e.g., 9X, P6, Z3) followed by a random number. Passport numbers use ZZ or XX prefixes followed by a random number. This guarantees no collision with a real person's identification.
