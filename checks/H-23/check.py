"""H-23. Верхние 10% сообществ с заказами.

Подтверждение: они держат > 40% заказов.
Отвержение: <= 25%.
"""

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["checkout_orders"].gt(0) & data["checkout_gmv_rub"].gt(0)].sort_values("checkout_orders", ascending=False)
    k = max(1, int(np.ceil(len(data) * 0.1)))
    top = data.iloc[:k]
    order_share = 100 * float(top["checkout_orders"].sum()) / float(data["checkout_orders"].sum())
    gmv_share = 100 * float(top["checkout_gmv_rub"].sum()) / float(data["checkout_gmv_rub"].sum())
    bars(["checkout_orders", "checkout_gmv"], [order_share, gmv_share], "top decile share", "%", HERE / "plot.png", fmt="{:.1f}")
    if order_share > 40:
        status = "подтверждена"
    elif order_share <= 25:
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"Верхние {k} из {len(data)} держат {order_share:.1f}% заказов и {gmv_share:.1f}% GMV.",
        ["Среднее по продавцам в план не берётся, пока доля заказов выше 40%."],
    )


if __name__ == "__main__":
    main()
