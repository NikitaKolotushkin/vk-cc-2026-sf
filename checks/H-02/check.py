"""H-02. Клипы товарного сообщества и доля с заказом.

Подтверждение: доля с заказом у product_clips>0 выше, чем у постов без клипов, на >= 5 п.п.
Отвержение: разрыв < 2 п.п. Иначе промежуточно.
Любая группа < 20 сообществ: непроверяема.
Сравнение внутри корзин размера, в вердикт идёт взвешенная разница.
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
    data = data.loc[data["business_type"].eq("товарное")].copy()
    data["band"] = band(data["subscribers"])
    clips = data["product_clips_30d"].gt(0)
    posts = data["product_posts_30d"].gt(0) & data["product_clips_30d"].eq(0)
    n_clips = int(clips.sum())
    n_posts = int(posts.sum())
    left = rate(data.loc[clips, "checkout_orders"].gt(0))
    right = rate(data.loc[posts, "checkout_orders"].gt(0))
    weighted_num = 0.0
    weighted_den = 0
    skipped = []
    for name, group in data.groupby("band", observed=True):
        a = group.loc[group["product_clips_30d"].gt(0)]
        b = group.loc[group["product_posts_30d"].gt(0) & group["product_clips_30d"].eq(0)]
        if min(len(a), len(b)) < 20:
            skipped.append(f"{name}: {len(a)}/{len(b)}")
            continue
        diff = rate(a["checkout_orders"].gt(0)) - rate(b["checkout_orders"].gt(0))
        weight = len(a) + len(b)
        weighted_num += diff * weight
        weighted_den += weight
    bars(
        ["product_clips>0", "posts only"],
        [left, right],
        "P(order), товарное",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    if min(n_clips, n_posts) < 20 or weighted_den == 0:
        status = "непроверяема"
        summary = f"Группы {n_clips} и {n_posts}. Внутри корзин размера пар с n>=20 нет или группа меньше 20."
    else:
        diff = weighted_num / weighted_den
        status = pp_call(diff)
        summary = f"Взвешенный разрыв доли с заказом {diff:.1f} п.п. Сырой разрыв {left - right:.1f} п.п."
    write(
        HERE,
        status,
        summary,
        [
            f"клипы {n_clips}, доля {left:.1f}%",
            f"только посты {n_posts}, доля {right:.1f}%",
            "Корзины без пары n>=20: " + (", ".join(skipped) if skipped else "нет"),
        ],
    )


if __name__ == "__main__":
    main()
