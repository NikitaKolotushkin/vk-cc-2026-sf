"""H-03. Флаг автора и доля заказов при ненулевых товарных просмотрах.

Подтверждение: author=1 выше author=0 не меньше чем на 5 п.п. внутри корзин.
Отвержение: разрыв < 2 п.п. Группа < 20: непроверяема.
Пустой автор не считается нулём.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import band, businesses, f0, rate
from style import bars
from verdict import pp_call, write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["product_content_views"].gt(0)].copy()
    data["band"] = band(data["subscribers"])
    yes = data["original_content_author"].eq(True)
    no = data["original_content_author"].eq(False)
    n_yes = int(yes.sum())
    n_no = int(no.sum())
    crude_yes = rate(data.loc[yes, "checkout_orders"].gt(0))
    crude_no = rate(data.loc[no, "checkout_orders"].gt(0))
    weighted_num = 0.0
    weighted_den = 0
    for _, group in data.groupby("band", observed=True):
        a = group.loc[group["original_content_author"].eq(True)]
        b = group.loc[group["original_content_author"].eq(False)]
        if min(len(a), len(b)) < 20:
            continue
        diff = rate(a["checkout_orders"].gt(0)) - rate(b["checkout_orders"].gt(0))
        weight = len(a) + len(b)
        weighted_num += diff * weight
        weighted_den += weight
    bars(
        ["author=1", "author=0"],
        [crude_yes, crude_no],
        "P(order) | product_views>0",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    if min(n_yes, n_no) < 20 or weighted_den == 0:
        status = "непроверяема"
        summary = f"author=1 {n_yes}, author=0 {n_no}. Сравнить внутри корзин нельзя."
    else:
        diff = weighted_num / weighted_den
        status = pp_call(diff)
        summary = f"Взвешенный разрыв {diff:.1f} п.п. Сырой {crude_yes - crude_no:.1f} п.п."
    write(
        HERE,
        status,
        summary,
        [
            f"author=1 {crude_yes:.1f}% из {n_yes}",
            f"author=0 {crude_no:.1f}% из {n_no}",
            f"пусто {int(data['original_content_author'].isna().sum())}, в сравнение не входит",
        ],
    )


if __name__ == "__main__":
    main()
