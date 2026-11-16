"""H-12. Медианная цена и доля с заказом.

Подтверждение: верхний квартиль ниже нижнего не меньше чем на 5 п.п.
Отвержение: разрыв < 2 п.п.
Если покрытие анализа меньше половины товарных и смежных с активным товаром,
ценовой слайд не делается даже при подтверждении.
"""

from pathlib import Path
import sys

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import bars
from verdict import pp_call, write


def main() -> None:
    data = f0(businesses())
    universe = data.loc[
        data["active_goods"].gt(0) & data["business_type"].isin(["товарное", "товарное и услужное"])
    ]
    price = data["median_item_price_rub"]
    sample = data.loc[
        price.notna()
        & ~price.isin([0, 1, 1_060_000])
        & data["active_goods"].gt(0)
        & data["business_type"].isin(["товарное", "товарное и услужное"])
    ].copy()
    sample["q"] = pd.qcut(sample["median_item_price_rub"], 4, labels=["Q1", "Q2", "Q3", "Q4"], duplicates="drop")
    labels = [str(label) for label in sample["q"].cat.categories]
    values = [rate(sample.loc[sample["q"].eq(label), "checkout_orders"].gt(0)) for label in labels]
    bars(labels, values, "P(order) by median_item_price quartile", "%", HERE / "plot.png", fmt="{:.1f}")
    coverage = len(sample) / len(universe) if len(universe) else 0
    if "Q1" not in labels or labels[-1] == "Q1":
        status = "непроверяема"
        summary = "Квартили не построились."
    else:
        diff = values[0] - values[-1]
        status = pp_call(diff)
        summary = f"{labels[0]} {values[0]:.1f}% против {labels[-1]} {values[-1]:.1f}%. Разрыв {diff:.1f} п.п. Покрытие {100 * coverage:.0f}%."
        if status == "подтверждена" and coverage < 0.5:
            status = "промежуточная"
            summary += " Покрытие ниже 50%, ценовой слайд не делается."
    write(HERE, status, summary, [f"n анализа {len(sample)} из {len(universe)}"])


if __name__ == "__main__":
    main()
