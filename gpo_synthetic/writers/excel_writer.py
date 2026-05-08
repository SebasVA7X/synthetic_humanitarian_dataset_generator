"""Write the synthetic dataset to Excel respecting the canonical schema."""
from pathlib import Path

import pandas as pd

from gpo_synthetic.schema import COLUMNS


def write_excel(rows: list[dict], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_excel(output_path, index=False, sheet_name="GPO_Origin")
