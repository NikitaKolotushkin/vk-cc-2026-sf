"""H-18 снята с очереди. Статистика не считается."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from verdict import write


def main() -> None:
    write(
        HERE,
        "снята",
        "Каннибализация Маркета и Партнёра не входит в пять вопросов кейса. Ключа пересечения людей нет.",
        ["Скрипт не строит корреляцию дневных рядов."],
    )


if __name__ == "__main__":
    main()
