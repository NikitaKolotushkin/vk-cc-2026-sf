"""H-06. Активные товары и заказы.

Подтверждение: Спирмен active_goods и checkout_orders >= 0.20
при goods_loaded>0 у товарного и смежного типа,
и мёртвый каталог не выше пустой загрузки на 2 п.п. и более.
Если частичный Спирмен загруженных при фиксированных активных >= 0.20,
фраза «достаточно активных» не принимается.
"""

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, partial_spearman, rate, spearman
from style import scatter
from verdict import write


def main() -> None:
    data = f0(businesses())
    core = data.loc[data["business_type"].isin(["товарное", "товарное и услужное"]) & data["goods_loaded"].gt(0)]
    rho = spearman(core["active_goods"], core["checkout_orders"])
    partial = partial_spearman(core["goods_loaded"], core["checkout_orders"], core["active_goods"])
    dead = rate(data.loc[data["goods_loaded"].gt(0) & data["active_goods"].eq(0), "checkout_orders"].gt(0))
    empty = rate(data.loc[data["goods_loaded"].eq(0), "checkout_orders"].gt(0))
    scatter(
        np.log1p(core["active_goods"]),
        np.log1p(core["checkout_orders"]),
        f"active_goods vs orders, ρ={rho:.2f}",
        "log1p(active_goods)",
        "log1p(checkout_orders)",
        HERE / "plot.png",
    )
    link = rho >= 0.20
    dead_ok = (dead - empty) < 2
    if link and dead_ok and not (partial >= 0.20):
        status = "подтверждена"
        summary = f"ρ={rho:.2f}. Мёртвый каталог {dead:.1f}% против пустой загрузки {empty:.1f}%. Загрузка отдельно от активных не держится."
    elif link and dead_ok and partial >= 0.20:
        status = "промежуточная"
        summary = f"ρ активных {rho:.2f}, но частичный ρ загруженных {partial:.2f}. Оба поля остаются."
    else:
        status = "отвергнута"
        summary = f"ρ={rho:.2f}. Мёртвый каталог {dead:.1f}%, пустая загрузка {empty:.1f}%."
    write(
        HERE,
        status,
        summary,
        [
            f"n {len(core)}",
            f"частичный ρ goods_loaded | active_goods = {partial:.3f}",
        ],
    )


if __name__ == "__main__":
    main()
