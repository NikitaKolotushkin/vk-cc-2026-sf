"""H-27 снята. Наклон тридцати дней не есть рост числа бизнесов."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from verdict import write


def main() -> None:
    write(
        HERE,
        "снята",
        "Один синтетический месяц не экстраполируется в коэффициент модели.",
        ["Скрипт не считает Спирмен номера дня и конверсии."],
    )


if __name__ == "__main__":
    main()
