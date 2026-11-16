"""H-01. Медиана отношения товарного контента к обычному.

Подтверждение «доходит хуже»: медиана <= 0.80.
Нет разницы: медиана в [0.90, 1.10].
Два отдельных вердикта, просмотры и ER.
"""

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0
from style import hist_pair
from verdict import write


def _call(median: float) -> str:
    if median <= 0.80:
        return "подтверждена"
    if 0.90 <= median <= 1.10:
        return "отвергнута"
    if median > 1.10:
        return "отвергнута"
    return "промежуточная"


def main() -> None:
    data = f0(businesses())
    den_r = data["posts_30d"] + data["clips_30d"]
    den_p = data["product_posts_30d"] + data["product_clips_30d"]
    reach = data.loc[
        den_r.gt(0)
        & den_p.gt(0)
        & data["regular_content_views"].gt(0)
        & data["product_content_views"].gt(0)
        & ~data["has_product_posts_above_posts"].astype(bool)
    ]
    views = (reach["product_content_views"] / den_p.loc[reach.index]) / (
        reach["regular_content_views"] / den_r.loc[reach.index]
    )
    er = data.loc[
        data["regular_content_views"].gt(0)
        & data["product_content_views"].gt(0)
        & ~data["has_engagement_above_views"].astype(bool)
    ]
    er_r = (er["regular_content_likes"] + er["regular_content_reposts"]) / er["regular_content_views"]
    er_p = (er["product_content_likes"] + er["product_content_reposts"]) / er["product_content_views"]
    er_ratio = (er_p / er_r).replace([np.inf, -np.inf], np.nan)
    er_ratio = er_ratio.loc[er_r.gt(0)].dropna()
    view_med = float(views.median())
    er_med = float(er_ratio.median())
    view_status = _call(view_med)
    er_status = _call(er_med)
    hist_pair(
        [views, er_ratio],
        [f"views, median {view_med:.2f}", f"ER, median {er_med:.2f}"],
        "product / regular",
        HERE / "plot.png",
    )
    if view_status == "подтверждена" and er_status == "подтверждена":
        status = "подтверждена"
    elif view_status == "отвергнута" and er_status == "отвергнута":
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"Просмотры: медиана {view_med:.2f}, {view_status}. ER: медиана {er_med:.2f}, {er_status}.",
        [
            f"n просмотров {len(views)}",
            f"n ER {len(er_ratio)}",
            "База просмотров: оба знаменателя и оба числителя > 0, без product_posts > posts.",
            "База ER: оба вида просмотров > 0, обычный ER > 0, без лайков или репостов выше просмотров.",
            "Медиана > 1.10 отвергает «доходит хуже»: товарный интенсивнее обычного.",
        ],
    )


if __name__ == "__main__":
    main()
