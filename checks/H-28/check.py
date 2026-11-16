"""H-28. Связь чекаута и открытий с заказом после типа и размера.

Подтверждение ложной причины: оба скорректированных OR < 1.5.
Отвержение: оба скорректированных OR >= 1.5.
Интервал не строится: в спеке при малом числе событий на коэффициент
вместо логита стоит Мантель–Хензель. Высокий OR не возвращает чекаут в KPI.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import band, businesses, crude_or, f0, mh_or
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["business_type"].isin(["товарное", "товарное и услужное", "без каталога"])].copy()
    data["band"] = band(data["subscribers"])
    data["hit"] = data["checkout_orders"].gt(0)
    data["checkout"] = data["checkout_enabled"].astype(bool)
    data["opens"] = data["product_card_opens_from_content"].gt(0)
    crude_checkout = crude_or(data["checkout"], data["hit"])
    adj_checkout = mh_or(data, "checkout", "hit", ["business_type", "band"])
    crude_opens = crude_or(data["opens"], data["hit"])
    adj_opens = mh_or(data, "opens", "hit", ["business_type", "band"])
    bars(
        ["checkout", "checkout MH", "opens", "opens MH"],
        [crude_checkout, adj_checkout, crude_opens, adj_opens],
        "OR of checkout_orders>0",
        "odds ratio",
        HERE / "plot.png",
        fmt="{:.2f}",
    )
    if adj_checkout < 1.5 and adj_opens < 1.5:
        status = "подтверждена"
        summary = "После типа и размера оба OR ниже 1.5. Чекаут и открытия причиной заказа не называются."
    elif adj_checkout >= 1.5 and adj_opens >= 1.5:
        status = "отвергнута"
        summary = "Связь остаётся после контроля. Это не разрешение написать «чекаут создаёт заказы»."
    else:
        status = "промежуточная"
        summary = "После контроля один OR остаётся >= 1.5, другой нет."
    write(
        HERE,
        status,
        summary,
        [
            f"чекаут сырой {crude_checkout:.2f}, MH {adj_checkout:.2f}",
            f"открытия сырые {crude_opens:.2f}, MH {adj_opens:.2f}",
        ],
    )


if __name__ == "__main__":
    main()
