"""H-14. Замок масштаба экрана.

Закрыт, если users_saw_goods_30d / market_mau >= 3.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import platform_int
from style import bars
from verdict import write


def main() -> None:
    saw = platform_int("users_saw_goods_30d")
    mau = platform_int("market_mau")
    ratio = saw / mau
    bars(
        ["users_saw_goods_30d", "market_mau"],
        [saw / 1e6, mau / 1e6],
        "reach vs market mau",
        "млн",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    status = "закрыт" if ratio >= 3 else "снят"
    write(
        HERE,
        status,
        f"Видевшие товар / MAU Маркета = {ratio:.2f}.",
        [
            f"users_saw_goods_30d {saw}",
            f"market_mau {mau}",
            "Отношение не называет поверхность, на которой товар увидели.",
        ],
    )


if __name__ == "__main__":
    main()
