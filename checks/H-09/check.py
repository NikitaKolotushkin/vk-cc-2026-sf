"""H-09. Где сидят заказы по типу бизнеса.

Подтверждение: товарное >= 50% заказов, услужное < 5%,
смежный тип не забирает ядро.
Ядро уезжает в смежный тип, если его доля заказов >= 25%
и доля сообществ с заказом выше товарного не меньше чем на 5 п.п.
Ядро уезжает в «без каталога», если там >= 25% заказов.
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
    total = float(data["checkout_orders"].sum())
    rows = []
    for name, group in data.groupby("business_type", observed=True):
        share = 100 * float(group["checkout_orders"].sum()) / total
        rows.append((str(name), share, rate(group["checkout_orders"].gt(0))))
    rows.sort(key=lambda item: item[1], reverse=True)
    shares = {name: share for name, share, _ in rows}
    rates = {name: value for name, _, value in rows}
    hbars([name for name, _, _ in rows], [share for _, share, _ in rows], "share of checkout_orders", "%", HERE / "plot.png", fmt="{:.1f}")
    product = shares.get("товарное", 0)
    service = shares.get("услужное", 0)
    mixed = shares.get("товарное и услужное", 0)
    bare = shares.get("без каталога", 0)
    mixed_takes = mixed >= 25 and rates["товарное и услужное"] >= rates["товарное"] + 5
    bare_takes = bare >= 25
    if product >= 50 and service < 5 and not mixed_takes and not bare_takes:
        status = "подтверждена"
        summary = f"Товарное держит {product:.1f}% заказов. Услуги {service:.1f}%. Ядро не переносится."
    elif mixed_takes or bare_takes:
        status = "отвергнута"
        summary = "Ядро уезжает из типа «товарное»."
    else:
        status = "промежуточная"
        summary = f"Товарное {product:.1f}%, услуги {service:.1f}%, смежный {mixed:.1f}%, без каталога {bare:.1f}%."
    write(
        HERE,
        status,
        summary,
        [f"{name}: заказы {share:.1f}%, сообщества с заказом {rates[name]:.1f}%" for name, share, _ in rows],
    )


if __name__ == "__main__":
    main()
