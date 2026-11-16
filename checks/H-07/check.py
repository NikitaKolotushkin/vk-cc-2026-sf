"""H-07. Оплата при уже включённом чекауте.

Подтверждение: доля заказов при payment=1 выше не меньше чем на 5 п.п.
Отвержение: разрыв < 2 п.п.
Меньше 20 сообществ с оплатой или меньше 20 заказов в этой клетке: непроверяема.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import bars
from verdict import pp_call, write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["checkout_enabled"].astype(bool)]
    pay = data["payment_enabled"].astype(bool)
    n_pay = int(pay.sum())
    orders_pay = int(data.loc[pay, "checkout_orders"].gt(0).sum())
    left = rate(data.loc[pay, "checkout_orders"].gt(0))
    right = rate(data.loc[~pay, "checkout_orders"].gt(0))
    bars(["payment=1", "payment=0"], [left, right], "P(order) | checkout=1", "%", HERE / "plot.png", fmt="{:.1f}")
    if n_pay < 20 or orders_pay < 20:
        status = "непроверяема"
        summary = f"С оплатой {n_pay} сообществ, заказов в клетке {orders_pay}."
    else:
        status = pp_call(left - right)
        summary = f"Доля с заказом {left:.1f}% при оплате и {right:.1f}% без неё. Разрыв {left - right:.1f} п.п."
    write(HERE, status, summary, ["Это совпадение, не эффект кнопки."])


if __name__ == "__main__":
    main()
