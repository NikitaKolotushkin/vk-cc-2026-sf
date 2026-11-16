"""H-16. Конверсия Партнёра с прямыми переходами и граница с сообществом.

Карточная конверсия не годится для сравнения с Маркетом, если
заказы / открытия и заказы / (открытия + прямые переходы)
различаются не меньше чем на 25% относительных.
Реферальная строка Партнёра не есть referral_program сообществ.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import contour, contour_int, read, INTERIM
from style import grouped
from verdict import write


def main() -> None:
    metrics = contour()
    sources = read(INTERIM / "market_sources.parquet")
    nested = read(INTERIM / "market_source_nested.parquet")
    orders = contour_int(metrics, "placed_orders", "partner_1")
    opens = contour_int(metrics, "card_opens", "partner_1")
    direct = contour_int(metrics, "direct_partner_transitions", "partner_1")
    card_rate = 100 * orders / opens
    wide_rate = 100 * orders / (opens + direct)
    relative = abs(card_rate - wide_rate) / card_rate
    clips = int(sources.loc[sources["source"].isin(["Клипы", "Лента"]), "partner_card_opens"].sum())
    referral = int(nested["partner_card_opens"].iloc[0])
    grouped(
        ["orders/opens", "orders/(opens+direct)"],
        {"конверсия, %": [card_rate, wide_rate]},
        "partner conversion",
        "%",
        HERE / "plot.png",
        fmt="{:.2f}",
    )
    if relative >= 0.25:
        status = "подтверждена"
        summary = f"Карточная конверсия {card_rate:.2f}%, с прямыми переходами {wide_rate:.2f}%. Относительная разница {100 * relative:.0f}%."
    else:
        status = "отвергнута"
        summary = f"Добавление прямых переходов меняет конверсию меньше чем на 25%: {card_rate:.2f}% и {wide_rate:.2f}%."
    write(
        HERE,
        status,
        summary,
        [
            f"прямые переходы {direct}",
            f"открытия карточки {opens}",
            f"реферал Партнёра {referral}, клипы+лента {clips}",
            "Доля заказов именно из прямых переходов файлом не разрезана.",
        ],
    )


if __name__ == "__main__":
    main()
