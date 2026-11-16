"""H-30. Замок колонки среднего чека сообщества.

Закрыт, если строк с разрывом больше 5% снова 215.
Иначе сборка слоя сломана и проверка останавливается.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import businesses
from style import bars
from verdict import write


def main() -> None:
    frame = businesses()
    mask = frame["checkout_orders"].gt(0) & frame["checkout_gmv_rub"].gt(0) & frame["average_order_value_rub"].notna()
    comparable = frame.loc[mask]
    calc = comparable["checkout_gmv_rub"] / comparable["checkout_orders"]
    gap = (comparable["average_order_value_rub"] - calc).abs() / calc
    wide = int(gap.gt(0.05).sum())
    bars(
        ["gap>5%", "gap<=5%"],
        [wide, len(comparable) - wide],
        "average_order_value_rub vs gmv/orders",
        "rows",
        HERE / "plot.png",
    )
    if wide != 215:
        raise SystemExit(f"H-30 contract broken: {wide} != 215")
    write(
        HERE,
        "закрыт",
        f"Разрыв больше 5% у {wide} из {len(comparable)}. Готовую колонку не используем.",
        ["Чек, где он нужен, считается как checkout_gmv_rub / checkout_orders."],
    )


if __name__ == "__main__":
    main()
