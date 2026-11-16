"""H-17. Замок: повтор и чек контура не переносятся на сообщества.

Закрыт, пока в businesses нет колонки повтора и оплаты.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, contour, contour_num
from style import bars
from verdict import write


def main() -> None:
    columns = set(businesses().columns)
    missing = [name for name in ("repeat_buyers_share_pct", "paid_orders", "orders_per_buyer") if name not in columns]
    metrics = contour()
    market = contour_num(metrics, "repeat_buyers_share_pct", "market_vk")
    partner = contour_num(metrics, "repeat_buyers_share_pct", "partner_1")
    bars(["market_vk", "partner_1"], [market, partner], "repeat_buyers_share_pct", "%", HERE / "plot.png", fmt="{:.1f}")
    status = "закрыт" if missing else "снят"
    write(
        HERE,
        status,
        "В листе сообществ нет повтора, оплаты и заказов на покупателя. Числа контура в модель сообществ не переносятся.",
        [f"repeat market_vk {market}", f"repeat partner_1 {partner}", "нет колонок: " + ", ".join(missing)],
    )


if __name__ == "__main__":
    main()
