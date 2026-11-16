"""H-20. Реклама и просмотры после контроля подписчиков.

Подтверждение: частичный Спирмен >= 0.20 хотя бы с одним видом просмотров.
Отвержение: оба |ρ| < 0.10.
От H-19 не зависит.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

import numpy as np
import pandas as pd

from data import businesses, f0, partial_spearman
from style import scatter_pair
from verdict import write


def resid(x, y, z):
    frame = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    rx, ry, rz = frame["x"].rank(), frame["y"].rank(), frame["z"].rank()
    bx = np.polyfit(rz, rx, 1)
    by = np.polyfit(rz, ry, 1)
    return rx - np.polyval(bx, rz), ry - np.polyval(by, rz)


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["ad_spend_rub"].gt(0)]
    regular = partial_spearman(data["ad_spend_rub"], data["regular_content_views"], data["subscribers"])
    product = partial_spearman(data["ad_spend_rub"], data["product_content_views"], data["subscribers"])
    scatter_pair(
        [
            resid(data["ad_spend_rub"], data["regular_content_views"], data["subscribers"]),
            resid(data["ad_spend_rub"], data["product_content_views"], data["subscribers"]),
        ],
        [f"regular_views, ρ={regular:.2f}", f"product_views, ρ={product:.2f}"],
        "resid rank ad_spend | subscribers",
        "resid rank views",
        HERE / "plot.png",
    )
    if regular >= 0.20 or product >= 0.20:
        status = "подтверждена"
    elif abs(regular) < 0.10 and abs(product) < 0.10:
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"Частичный ρ с обычными просмотрами {regular:.3f}, с товарными {product:.3f}.",
        [f"n тратящих {len(data)}"],
    )


if __name__ == "__main__":
    main()
