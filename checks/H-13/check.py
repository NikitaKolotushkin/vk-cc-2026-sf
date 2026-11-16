"""H-13. Замок входа: главная Маркета и поиск.

Закрыт, если главная < 1% открытий market_vk и поиск < 10%.
Снимается, если главная или поиск >= 10% открытий market_vk.
"""

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from data import INTERIM, read
from style import grouped_h
from verdict import write


def main() -> None:
    sources = read(INTERIM / "market_sources.parquet")
    home = sources.loc[sources["source"].astype(str).str.startswith("Главная"), "market_share_pct"]
    search = sources.loc[sources["source"].eq("Поиск"), "market_share_pct"]
    home_share = float(home.iloc[0])
    search_share = float(search.iloc[0])
    grouped_h(
        sources["source"].astype(str).tolist(),
        {"маркет": sources["market_share_pct"].tolist(), "партнёр": sources["partner_share_pct"].tolist()},
        "card open share by source",
        "%",
        HERE / "plot.png",
        fmt="{:.1f}",
    )
    if home_share >= 10 or search_share >= 10:
        status = "снят"
        summary = f"Главная {home_share:.1f}%, поиск {search_share:.1f}%. Экран или поиск остаётся входом."
    elif home_share < 1 and search_share < 10:
        status = "закрыт"
        summary = f"Главная {home_share:.1f}%, поиск {search_share:.1f}%. Входом не являются."
    else:
        status = "промежуточная"
        summary = f"Главная {home_share:.1f}%, поиск {search_share:.1f}%."
    other = sources.loc[sources["source"].eq("Другое"), "market_share_pct"]
    write(
        HERE,
        status,
        summary,
        [
            f"Другое у Маркета {float(other.iloc[0]):.1f}% и контентом не называется",
            "Доли пересчитаны из хранимых процентов листа источников.",
        ],
    )


if __name__ == "__main__":
    main()
