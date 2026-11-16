"""H-15. Конверсия Маркета без остаточных категорий.

Подтверждение: заказы / открытия без «Другое», «Не определена» и «Все товары» < 1%.
Снятие: очищенная конверсия >= 1%.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import PROCESSED, read
from style import bars
from verdict import write


def main() -> None:
    categories = read(PROCESSED / "market_categories.parquet")
    keep = ~categories["is_residual_category"].astype(bool) & ~categories["is_all_goods_label"].astype(bool)
    raw = 100 * categories["market_orders"].sum() / categories["market_card_opens"].sum()
    clean_orders = categories.loc[keep, "market_orders"].sum()
    clean_opens = categories.loc[keep, "market_card_opens"].sum()
    clean = 100 * clean_orders / clean_opens
    bars(["all categories", "drop residual+all"], [raw, clean], "market orders/opens", "%", HERE / "plot.png", fmt="{:.2f}")
    status = "подтверждена" if clean < 1 else "отвергнута"
    write(
        HERE,
        status,
        f"Очищенная конверсия {clean:.2f}%. По всем категориям {raw:.2f}%.",
        [
            f"открытия в знаменателе {int(clean_opens)}",
            f"заказы в числителе {int(clean_orders)}",
            "С конверсией Партнёра не сравнивается.",
        ],
    )


if __name__ == "__main__":
    main()
