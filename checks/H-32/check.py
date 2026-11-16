"""H-32. Товарный контент «без каталога» против «товарного» с чекаутом.

Подтверждение: у группы без каталога больше товарных постов и открытий,
доля заказов всего типа «без каталога» < 5%,
и доля сообществ с заказом ниже не меньше чем на 5 п.п.
Отвержение: у «без каталога» >= 25% заказов или разрыв долей < 5 п.п.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import grouped
from verdict import write


def main() -> None:
    data = f0(businesses())
    bare = data.loc[data["business_type"].eq("без каталога")]
    group_n = bare.loc[bare["product_posts_30d"].gt(0) | bare["product_clips_30d"].gt(0)]
    group_t = data.loc[data["business_type"].eq("товарное") & data["checkout_enabled"].astype(bool)]
    posts_n = int(group_n["product_posts_30d"].sum())
    posts_t = int(group_t["product_posts_30d"].sum())
    opens_n = int(group_n["product_card_opens_from_content"].sum())
    opens_t = int(group_t["product_card_opens_from_content"].sum())
    rate_n = rate(group_n["checkout_orders"].gt(0))
    rate_t = rate(group_t["checkout_orders"].gt(0))
    bare_orders = float(bare["checkout_orders"].sum())
    all_orders = float(data["checkout_orders"].sum())
    bare_share = 100 * bare_orders / all_orders
    grouped(
        ["без каталога", "товарное+чекаут"],
        {"доля с заказом, %": [rate_n, rate_t]},
        "order rate",
        "%",
        HERE / "plot.png",
        fmt="{:.2f}",
    )
    more_content = posts_n > posts_t and opens_n > opens_t
    rate_gap = rate_t - rate_n
    if bare_share >= 25 or rate_gap < 5:
        status = "отвергнута"
        summary = f"Доля заказов «без каталога» {bare_share:.1f}%. Разрыв долей с заказом {rate_gap:.1f} п.п."
    elif more_content and bare_share < 5 and rate_gap >= 5:
        status = "подтверждена"
        summary = "Контента больше у «без каталога», заказы почти все не там. Ядро остаётся товарным с чекаутом."
    else:
        status = "промежуточная"
        summary = "Условия подтверждения выполнены не все."
    write(
        HERE,
        status,
        summary,
        [
            f"N n={len(group_n)}, посты {posts_n}, открытия {opens_n}, доля с заказом {rate_n:.2f}%",
            f"T n={len(group_t)}, посты {posts_t}, открытия {opens_t}, доля с заказом {rate_t:.2f}%",
            f"все заказы типа «без каталога» {bare_share:.2f}%",
        ],
    )


if __name__ == "__main__":
    main()
