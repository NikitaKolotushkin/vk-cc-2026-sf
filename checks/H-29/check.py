"""H-29. Доля заказов на флагах поломок.

Подтверждение: объединение флагов держит < 10% заказов и < 10% GMV.
Не входят несовпадение типа и каталога, чекаут без товаров и заказы при выключенном чекауте.
"""

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses
from style import bars
from verdict import write

FLAGS = [
    "is_exact_metric_clone",
    "has_orders_with_zero_gmv",
    "is_extreme_ad_spend",
    "is_extreme_catalog",
    "is_high_post_volume",
]


def main() -> None:
    frame = businesses()
    bad = np.zeros(len(frame), dtype=bool)
    for name in FLAGS:
        bad |= frame[name].astype(bool).to_numpy()
    orders = float(frame["checkout_orders"].sum())
    gmv = float(frame["checkout_gmv_rub"].sum())
    order_share = 100 * float(frame.loc[bad, "checkout_orders"].sum()) / orders
    gmv_share = 100 * float(frame.loc[bad, "checkout_gmv_rub"].sum()) / gmv
    bars(
        ["checkout_orders", "checkout_gmv"],
        [order_share, gmv_share],
        "share on quality flags",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    if order_share < 10 and gmv_share < 10:
        status = "подтверждена"
    elif order_share >= 10 or gmv_share >= 10:
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"На флагах {order_share:.1f}% заказов и {gmv_share:.1f}% GMV.",
        ["На слайд как находка не выносится."] + [f"{name}: {int(frame[name].astype(bool).sum())}" for name in FLAGS],
    )


if __name__ == "__main__":
    main()
