"""H-04. Рефералка сообщества против похожих без неё.

В путь флаг попадает только при разрыве доли заказов >= 5 п.п.
Разрыв открытий >= 20% без заказов остаётся в приложении.
Оба разрыва малы: отвергнута. Мало заказов в паре: заказная половина непроверяема.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import band, businesses, f0, rate
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    data["band"] = band(data["subscribers"])
    pool = data.loc[~data["referral_program"].astype(bool)]
    used: set = set()
    kept = []
    controls = []
    theme_fallback = 0
    for idx in data.index[data["referral_program"].astype(bool)]:
        row = data.loc[idx]
        base = pool.loc[
            pool["business_type"].eq(row["business_type"])
            & pool["band"].eq(row["band"])
            & ~pool.index.isin(used)
        ]
        themed = base.loc[base["theme"].astype(str).eq(str(row["theme"]))]
        src = themed if len(themed) else base
        if len(themed) == 0 and len(base):
            theme_fallback += 1
        take = list(src.index[:3])
        if not take:
            continue
        used.update(take)
        kept.append(idx)
        controls.extend(take)
    treated = data.loc[kept]
    control = data.loc[controls]
    order_t = rate(treated["checkout_orders"].gt(0))
    order_c = rate(control["checkout_orders"].gt(0))
    open_t = float(treated["product_card_opens_from_content"].median())
    open_c = float(control["product_card_opens_from_content"].median())
    order_events = int(treated["checkout_orders"].gt(0).sum() + control["checkout_orders"].gt(0).sum())
    bars(
        ["referral=1", "matched control"],
        [order_t, order_c],
        "P(order), referral match",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    order_diff = order_t - order_c
    if open_c == 0:
        open_shift = 0.0 if open_t == 0 else float("inf")
    else:
        open_shift = (open_t - open_c) / open_c
    if order_events < 20:
        order_status = "непроверяема"
    elif order_diff >= 5:
        order_status = "подтверждена"
    elif order_diff < 2:
        order_status = "отвергнута"
    else:
        order_status = "промежуточная"
    if order_status == "подтверждена":
        status = "подтверждена"
        summary = f"Доля заказов выше на {order_diff:.1f} п.п. Флаг можно обсуждать как шаг пути."
    elif order_status == "непроверяема":
        status = "непроверяема"
        summary = f"Заказов в сопоставленной паре {order_events}. Про заказы вывода нет."
    else:
        status = order_status
        summary = f"Разрыв доли заказов {order_diff:.1f} п.п. В путь рефералка не идёт."
    write(
        HERE,
        status,
        summary,
        [
            f"участников с контролем {len(treated)}, контролей {len(control)}",
            f"доля заказов {order_t:.1f}% против {order_c:.1f}%",
            f"медиана открытий {open_t:.1f} против {open_c:.1f}, относительный сдвиг {open_shift}",
            f"контроль без совпадения темы {theme_fallback}",
            "Открытия без разрыва заказов на шаг пути не ставятся.",
        ],
    )


if __name__ == "__main__":
    main()
