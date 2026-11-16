"""H-26 снята. День недели сентября не задаёт стратегию."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from verdict import write


def main() -> None:
    write(
        HERE,
        "снята",
        "Четыре-пять синтетических точек на день недели не меняют сегмент и путь.",
        ["Скрипт не сравнивает медианы по дням недели."],
    )


if __name__ == "__main__":
    main()
