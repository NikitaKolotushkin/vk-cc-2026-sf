"""H-22. База рекламы и база оплаты не совпадают с базой заказов.

Подтверждение: меньше половины рекламных рублей на сообществах с заказом
и оплата включена меньше чем у половины сообществ с заказом.
Отвержение: обе доли >= 50%.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    spend = float(data["ad_spend_rub"].sum())
    on_orders = float(data.loc[data["checkout_orders"].gt(0), "ad_spend_rub"].sum())
    sellers = data.loc[data["checkout_orders"].gt(0)]
    ad_share = 100 * on_orders / spend
    pay_share = rate(sellers["payment_enabled"].astype(bool))
    bars(
        ["ad ₽ on orders>0", "payment=1 | orders>0"],
        [ad_share, pay_share],
        "share of spend and payment coverage",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    if ad_share < 50 and pay_share < 50:
        status = "подтверждена"
    elif ad_share >= 50 and pay_share >= 50:
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"На сообществах с заказом {ad_share:.1f}% рекламных рублей. Оплата есть у {pay_share:.1f}% сообществ с заказом.",
        [f"сообществ с заказом {len(sellers)}"],
    )


if __name__ == "__main__":
    main()
