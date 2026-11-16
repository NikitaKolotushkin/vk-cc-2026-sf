"""H-08. Открытия карточки и живая витрина.

Часть A подтверждается, если среди открытий карточки доля с заказом < 50%.
Часть B подтверждается, если прирост от открытий при живой витрине >= 5 п.п.,
а без витрины < 2 п.п.
Общий вердикт только если обе части верны.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses, f0, rate
from style import bars
from verdict import write


def main() -> None:
    data = f0(businesses())
    data = data.loc[data["business_type"].isin(["товарное", "товарное и услужное", "без каталога"])]
    opens = data["product_card_opens_from_content"].gt(0)
    infra = data["active_goods"].gt(0) & data["checkout_enabled"].astype(bool)
    orders = data["checkout_orders"].gt(0)
    cells = {
        "infra+opens": infra & opens,
        "infra": infra & ~opens,
        "opens": ~infra & opens,
        "neither": ~infra & ~opens,
    }
    values = {name: rate(orders.loc[mask]) for name, mask in cells.items()}
    among = rate(orders.loc[opens])
    lift_infra = values["infra+opens"] - values["infra"]
    lift_open = values["opens"] - values["neither"]
    part_a = among < 50
    part_b = lift_infra >= 5 and lift_open < 2
    if part_a and part_b:
        status = "подтверждена"
        summary = f"Среди открытий заказ у {among:.1f}%. Прирост при витрине {lift_infra:.1f} п.п., без неё {lift_open:.1f} п.п."
    elif part_a:
        status = "промежуточная"
        summary = f"Заказа нет у большинства с открытиями ({100 - among:.1f}%), но витрина этот обрыв не отделяет чисто: прирост без неё {lift_open:.1f} п.п."
    else:
        status = "отвергнута"
        summary = f"Среди открытий заказ у {among:.1f}%. Формулировка «нет у большинства» не держится."
    bars(list(values), list(values.values()), "P(order), infra × card opens", "%", HERE / "plot.png", fmt="{:.1f}")
    write(
        HERE,
        status,
        summary,
        [f"{name}: {value:.1f}%, n={int(cells[name].sum())}" for name, value in values.items()],
    )


if __name__ == "__main__":
    main()
