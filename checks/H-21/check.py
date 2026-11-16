"""H-21. Замок: оформленный GMV Маркета не является выручкой VK.

Закрыт, пока оплаченные / оформленные < 20%.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import contour, contour_int
from style import bars
from verdict import write


def main() -> None:
    metrics = contour()
    placed = contour_int(metrics, "placed_orders", "market_vk")
    paid = contour_int(metrics, "paid_orders", "market_vk")
    share = 100 * paid / placed
    bars(["paid/placed"], [share], "market_vk paid_orders / placed_orders", "%", HERE / "plot.png", fmt="{:.2f}")
    status = "закрыт" if share < 20 else "снят"
    write(
        HERE,
        status,
        f"Оплачено {paid} из {placed}, {share:.3f}%.",
        [
            "Ниже 20% оформленный GMV не называется выручкой VK.",
            "Заказы Партнёра в этот числитель не входят.",
        ],
    )


if __name__ == "__main__":
    main()
