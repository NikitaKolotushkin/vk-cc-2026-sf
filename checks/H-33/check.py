"""H-33. Чекаут без загруженных товаров.

Подтверждение скрытого товара: доля заказов или доля открытий
отличается от группы с активным товаром меньше чем на 5 п.п.
Отвержение: обе доли ниже не меньше чем на 5 п.п.
Группа меньше 20 сообществ: непроверяема.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import grouped
from verdict import write


def main() -> None:
    data = f0(businesses())
    checkout = data["checkout_enabled"].astype(bool)
    hidden = data.loc[checkout & data["goods_loaded"].eq(0)]
    active = data.loc[checkout & data["active_goods"].gt(0)]
    if len(hidden) < 20:
        write(HERE, "непроверяема", f"В группе без загруженных товаров {len(hidden)} сообществ.", [])
        return
    order_h = rate(hidden["checkout_orders"].gt(0))
    order_a = rate(active["checkout_orders"].gt(0))
    open_h = rate(hidden["product_card_opens_from_content"].gt(0))
    open_a = rate(active["product_card_opens_from_content"].gt(0))
    grouped(
        ["goods_loaded=0", "active_goods>0"],
        {"заказ, %": [order_h, order_a], "открытие, %": [open_h, open_a]},
        "checkout on",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    order_gap = order_a - order_h
    open_gap = open_a - open_h
    if order_gap >= 5 and open_gap >= 5:
        status = "отвергнута"
        summary = "И заказов, и открытий заметно меньше. Это пустой флаг, не скрытый магазин."
    elif order_gap < 5 or open_gap < 5:
        status = "подтверждена"
        summary = "Хотя бы одна доля близка к сообществам с активным товаром. Группу не называем пустой."
    else:
        status = "промежуточная"
        summary = "Ни подтверждение, ни отвержение не собрались."
    write(
        HERE,
        status,
        summary,
        [
            f"без загрузки n={len(hidden)}, заказ {order_h:.1f}%, открытие {open_h:.1f}%",
            f"активный товар n={len(active)}, заказ {order_a:.1f}%, открытие {open_a:.1f}%",
            f"разрыв заказа {order_gap:.1f} п.п., разрыв открытия {open_gap:.1f} п.п.",
        ],
    )


if __name__ == "__main__":
    main()
