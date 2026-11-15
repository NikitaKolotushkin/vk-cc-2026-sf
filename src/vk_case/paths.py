from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
INTERIM_DIR = ROOT / "data" / "interim"
PROCESSED_DIR = ROOT / "data" / "processed"
SCHEMA_PATH = INTERIM_DIR / "schema.yml"
PROCESSED_SCHEMA_PATH = PROCESSED_DIR / "schema.yml"

EM_DASH = "\u2014"
NOT_APPLICABLE = "not_applicable"
PERIOD_TEXT = f"2026-09-01 {EM_DASH} 2026-09-30"


def raw_workbook() -> Path:
    files = sorted(RAW_DIR.glob("*.xlsx"))
    if len(files) != 1:
        found = ", ".join(path.name for path in files) or "none"
        raise SystemExit(f"В data/raw ожидается ровно один xlsx, найдено: {found}")
    return files[0]
