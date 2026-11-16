"""H-19. Реклама и заказы чекаута.

Подтверждение: |ρ| < 0.10 по всем строкам и среди тратящих,
и больше половины рекламных рублей сидит на нуле заказов.
Отвержение: |ρ| среди тратящих >= 0.20 и доля рублей на нуле заказов <= 50%.
"""

from pathlib import Path
import sys

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, spearman
from style import scatter
from verdict import write


def main() -> None:
    data = f0(businesses())
    spenders = data.loc[data["ad_spend_rub"].gt(0)]
    rho_all = spearman(data["ad_spend_rub"], data["checkout_orders"])
    rho_spend = spearman(spenders["ad_spend_rub"], spenders["checkout_orders"])
    zero = float(spenders.loc[spenders["checkout_orders"].eq(0), "ad_spend_rub"].sum())
    total = float(spenders["ad_spend_rub"].sum())
    share = 100 * zero / total
    scatter(
        np.log10(spenders["ad_spend_rub"]),
        spenders["checkout_orders"],
        f"ad_spend>0, ρ={rho_spend:.2f}",
        "log10(ad_spend_rub)",
        "checkout_orders",
        HERE / "plot.png",
    )
    confirms = abs(rho_all) < 0.10 and abs(rho_spend) < 0.10 and share > 50
    rejects = abs(rho_spend) >= 0.20 and share <= 50
    if confirms:
        status = "подтверждена"
    elif rejects:
        status = "отвергнута"
    else:
        status = "промежуточная"
    write(
        HERE,
        status,
        f"ρ всех {rho_all:.3f}, ρ тратящих {rho_spend:.3f}. На нуле заказов {share:.1f}% рекламных рублей.",
        [f"тратящих {len(spenders)}", "Связь не говорит, что реклама не приводит продажи вне чекаута."],
    )


if __name__ == "__main__":
    main()
