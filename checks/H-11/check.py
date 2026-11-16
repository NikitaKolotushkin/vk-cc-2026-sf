"""H-11. Доля с заказом по корзинам подписчиков, тип товарное.

Подтверждение: верхняя непустая корзина с n>=20 выше нижней с n>=20
не меньше чем на 5 п.п.
Доля заказов в верхней корзине вердикт не переворачивает.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import band, businesses, f0, rate
from style import bars
from verdict import pp_call, write

LABELS = ["0", "1–12", "13–100", "101–1000", ">1000"]


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["business_type"].eq("товарное")].copy()
    data["band"] = band(data["subscribers"])
    kept = []
    values = []
    counts = []
    order_shares = []
    total_orders = float(data["checkout_orders"].sum())
    for label in LABELS:
        subset = data.loc[data["band"].eq(label)]
        if len(subset) < 20:
            continue
        kept.append(label)
        values.append(rate(subset["checkout_orders"].gt(0)))
        counts.append(len(subset))
        order_shares.append(100 * float(subset["checkout_orders"].sum()) / total_orders if total_orders else 0)
    bars(kept, values, "P(order) by subscribers, товарное", "%", HERE / "plot.png", fmt="{:.1f}")
    if len(kept) < 2:
        status = "непроверяема"
        summary = "Нет двух корзин с 20 и более товарными сообществами."
        diff = float("nan")
    else:
        diff = values[-1] - values[0]
        status = pp_call(diff)
        summary = f"{kept[-1]} {values[-1]:.1f}% против {kept[0]} {values[0]:.1f}%. Разрыв {diff:.1f} п.п. Доля заказов верхней корзины {order_shares[-1]:.1f}%."
    write(
        HERE,
        status,
        summary,
        [f"{label}: доля сообществ {value:.1f}%, n={count}, доля заказов {share:.1f}%" for label, value, count, share in zip(kept, values, counts, order_shares)],
    )


if __name__ == "__main__":
    main()
