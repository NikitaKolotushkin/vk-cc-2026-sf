"""H-05. Точность флага чекаута против заказа.

Вердикт: точность одного чекаута ниже точности «чекаут и активный товар»
не меньше чем на 5 п.п. Иначе флаг можно оставить прокси.
Строки без загруженных товаров и заказы при выключенном флаге показываются
и из вердикта не вычитаются.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0
from style import bars
from verdict import pp_call, write


def precision(orders, mask) -> float:
    flagged = int(mask.sum())
    if flagged == 0:
        return float("nan")
    return 100 * float(orders.loc[mask].mean())


def main() -> None:
    full = businesses()
    checkout_n = int(full["checkout_enabled"].astype(bool).sum())
    order_n = int(full["checkout_orders"].gt(0).sum())
    if checkout_n != 5737 or order_n != 298:
        raise SystemExit(f"census broken: checkout {checkout_n}, orders {order_n}")
    data = f0(full)
    orders = data["checkout_orders"].gt(0)
    checkout = data["checkout_enabled"].astype(bool)
    rules = {
        "checkout": checkout,
        "+loaded": checkout & data["goods_loaded"].gt(0),
        "+active": checkout & data["active_goods"].gt(0),
        "all 3 flags": checkout & data["delivery_enabled"].astype(bool) & data["payment_enabled"].astype(bool),
    }
    values = {name: precision(orders, mask) for name, mask in rules.items()}
    diff = values["+active"] - values["checkout"]
    status = pp_call(diff)
    bars(list(values), list(values.values()), "precision vs checkout_orders>0", "%", HERE / "plot.png", fmt="{:.1f}")
    write(
        HERE,
        status,
        f"Точность чекаута {values['checkout']:.1f}%, с активным товаром {values['+active']:.1f}%. Разрыв {diff:.1f} п.п.",
        [
            f"полный лист: чекаут {checkout_n}, с заказом {order_n}",
            f"+loaded {values['+loaded']:.1f}%",
            f"все три флага {values['all 3 flags']:.1f}%",
            f"чекаут и goods_loaded=0: {int((checkout & data['goods_loaded'].eq(0)).sum())}",
            f"заказы при выключенном чекауте: {int((orders & ~checkout).sum())}",
            "Эти две группы в вердикт точности не входят.",
        ],
    )


if __name__ == "__main__":
    main()
