"""H-31. Какой из трёх обрывов крупнейший у товарных сообществ.

Подтверждение: «нет заказа» больше соседнего обрыва не меньше чем на 5 п.п.
Если два верхних различаются меньше чем на 5 п.п., один первый шаг называть нельзя.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["business_type"].eq("товарное")]
    active = data["posts_30d"].gt(0) | data["clips_30d"].gt(0) | data["regular_content_views"].gt(0)
    data = data.loc[active]
    has_order = data["checkout_orders"].gt(0)
    has_open = data["product_card_opens_from_content"].gt(0)
    has_product = data["product_posts_30d"].gt(0) | data["product_clips_30d"].gt(0)
    groups = {
        "нет заказа": ~has_order & has_open,
        "нет открытия": ~has_order & ~has_open & has_product,
        "нет товара": ~has_order & ~has_open & ~has_product,
    }
    counts = {name: int(mask.sum()) for name, mask in groups.items()}
    total = sum(counts.values())
    shares = {name: 100 * count / total for name, count in counts.items()}
    ranked = sorted(shares, key=shares.get, reverse=True)
    gap = shares[ranked[0]] - shares[ranked[1]]
    bars(list(counts), [shares[name] for name in counts], "break share, товарное", "%", HERE / "plot.png", fmt="{:.1f}")
    if gap < 5:
        status = "промежуточная"
        summary = f"Верхние обрывы «{ranked[0]}» {shares[ranked[0]]:.1f}% и «{ranked[1]}» {shares[ranked[1]]:.1f}%. Один первый шаг не называется."
    elif ranked[0] == "нет заказа":
        status = "подтверждена"
        summary = f"Крупнейший обрыв «нет заказа», {shares['нет заказа']:.1f}%. Зазор со следующим {gap:.1f} п.п."
    else:
        status = "отвергнута"
        summary = f"Крупнейший обрыв «{ranked[0]}», {shares[ranked[0]]:.1f}%. Первый шаг не оформление заказа."
    write(
        HERE,
        status,
        summary,
        [f"{name}: {counts[name]} сообществ, {shares[name]:.1f}%" for name in counts] + [f"уже с заказом, не обрыв: {int(has_order.sum())}"],
    )


if __name__ == "__main__":
    main()
