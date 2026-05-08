"""Configuration loader from .env file."""
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class PostgresConfig:
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str
    table: str

    @property
    def fqtn(self) -> str:
        return f'"{self.schema}"."{self.table}"'


@dataclass
class GenerationConfig:
    num_rows: int
    match_ratio: float
    duplicate_ratio: float
    doc_overlap_ratio: float
    output_path: Path
    random_seed: int


def load_pg_config() -> PostgresConfig:
    return PostgresConfig(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5432")),
        database=os.getenv("DB_NAME", ""),
        user=os.getenv("DB_USER", ""),
        password=os.getenv("DB_PASSWORD", ""),
        schema=os.getenv("RAN_SOURCE_SCHEMA", "public"),
        table=os.getenv("RAN_SOURCE_TABLE", "dim_individual"),
    )


def load_gen_config() -> GenerationConfig:
    return GenerationConfig(
        num_rows=int(os.getenv("RAN_NUM_ROWS", "1154")),
        match_ratio=float(os.getenv("RAN_MATCH_RATIO", "0.56")),
        duplicate_ratio=float(os.getenv("RAN_DUPLICATE_RATIO", "0.10")),
        doc_overlap_ratio=float(os.getenv("RAN_DOC_OVERLAP_RATIO", "0.78")),
        output_path=Path(os.getenv("GPO_OUTPUT_PATH", "./output/gpo_synthetic_origin.xlsx")),
        random_seed=int(os.getenv("RAN_RANDOM_SEED", "42")),
    )
