"""H-10. Тема попадает в путь только с массой заказов и другим стеком.

Масса: >= 30 сообществ с заказом или >= 10% заказов.
Стек: доля чекаута или доля «товарный пост есть, заказа нет»
отличается от товарного типа не меньше чем на 5 п.п.
Подтверждение: хотя бы одна группа закрывает оба условия.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import hbars
from verdict import write


def main() -> None:
    data = f0(businesses())
    base = data.loc[data["business_type"].eq("товарное")]
    base_checkout = rate(base["checkout_enabled"].astype(bool))
    base_gap = rate(base["product_posts_30d"].gt(0) & base["checkout_orders"].eq(0))
    theme = data["theme"].astype(str)
    counts = theme.value_counts()
    big = set(counts.loc[counts.ge(200)].index)
    keep = big | {"Объявления", "Услуги"}
    data = data.copy()
    data["theme_group"] = theme.where(theme.isin(keep), "прочие")
    total_orders = float(data["checkout_orders"].sum())
    rows = []
    passed = []
    for name, group in data.groupby("theme_group", observed=True):
        orders = float(group["checkout_orders"].sum())
        sellers = int(group["checkout_orders"].gt(0).sum())
        product = group.loc[group["business_type"].eq("товарное")]
        checkout_gap = abs(rate(product["checkout_enabled"].astype(bool)) - base_checkout) if len(product) else 0
        content_gap = abs(rate(product["product_posts_30d"].gt(0) & product["checkout_orders"].eq(0)) - base_gap) if len(product) else 0
        mass = sellers >= 30 or orders >= 0.10 * total_orders
        stack = checkout_gap >= 5 or content_gap >= 5
        share = 100 * orders / total_orders
        rows.append((str(name), share))
        if mass and stack and name not in {"Объявления", "Услуги"}:
            passed.append(str(name))
    rows.sort(key=lambda item: item[1], reverse=True)
    hbars([name for name, _ in rows], [share for _, share in rows], "share of checkout_orders by theme", "%", HERE / "plot.png", fmt="{:.1f}")
    if passed:
        status = "подтверждена"
        summary = "В путь попадают: " + ", ".join(passed) + "."
    else:
        status = "отвергнута"
        summary = "Ни одна тема не закрыла массу и другой стек одновременно."
    write(HERE, status, summary, [f"{name}: {share:.1f}%" for name, share in rows])


if __name__ == "__main__":
    main()
