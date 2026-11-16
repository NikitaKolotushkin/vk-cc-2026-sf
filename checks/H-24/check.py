"""H-24 снята. Пол и возраст покупателей контуров не отвечают, какой бизнес берём."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from verdict import write


def main() -> None:
    write(
        HERE,
        "снята",
        "Пирамиды Маркета и Партнёра не являются сегментом бизнес-сообществ. У сообществ пола и возраста нет.",
        ["Скрипт не сравнивает доли покупателей."],
    )


if __name__ == "__main__":
    main()
