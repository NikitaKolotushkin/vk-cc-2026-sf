"""Запускает check.py каждой карточки. Логика проверки живёт в карточке, не здесь."""

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> None:
    failed = []
    for script in sorted(HERE.glob("H-*/check.py")):
        result = subprocess.run([sys.executable, str(script)], check=False)
        if result.returncode != 0:
            failed.append(script.parent.name)
    if failed:
        raise SystemExit("не прошли: " + ", ".join(failed))


if __name__ == "__main__":
    main()
