"""H-25 снята. Региональный рейтинг Партнёра не развилка пути сообщества."""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from verdict import write


def main() -> None:
    write(
        HERE,
        "снята",
        "«Не указан» не регион. У сообществ региона нет, барьер доставки из этого листа не проверяется.",
        ["Скрипт не строит рейтинг регионов."],
    )


if __name__ == "__main__":
    main()
