"""
GPO synthetic origin file generator — CLI entrypoint.

Usage:
    python -m gpo_synthetic                         # uses Postgres from .env
    python -m gpo_synthetic --csv path/to/dim.csv   # CSV fallback (offline)
"""
import argparse
import sys
from pathlib import Path

from gpo_synthetic.config import load_gen_config, load_pg_config
from gpo_synthetic.orchestrator import generate_dataset
from gpo_synthetic.writers.excel_writer import write_excel


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the GPO synthetic origin Excel file."
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional CSV path to use instead of Postgres (must contain "
             "full_name, sex, date_of_birth, country_origin).",
    )
    args = parser.parse_args(argv)

    gen_cfg = load_gen_config()
    pg_cfg = load_pg_config()

    rows = generate_dataset(gen_cfg, pg_cfg, csv_fallback=args.csv)

    output_path = Path(gen_cfg.output_path)
    write_excel(rows, output_path)
    print(f"\n✔ Wrote {len(rows)} rows to: {output_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
