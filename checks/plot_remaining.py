"""Графики H-34–H-83 рядом с вердиктом. H-01–H-33 уже нарисованы своими check.py."""

from pathlib import Path
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from data import INTERIM, businesses, f0, mh_or, partial_spearman, read, spearman
from style import AMBER, BLUE, GRAY, INK, _ax, bars, grouped, grouped_h, hbars, save

OUT = HERE


def dest(n):
    path = OUT / f"H-{n:02d}"
    path.mkdir(parents=True, exist_ok=True)
    return path / "plot.png"


def lines(xs, series, title, ylabel, path, hline=None):
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    colors = [BLUE, AMBER, GRAY]
    for i, (name, ys) in enumerate(series.items()):
        ax.plot(xs, ys, color=colors[i % 3], lw=1.6, marker="o", ms=3, label=name)
    if hline is not None:
        ax.axhline(hline, color=GRAY, lw=0.8, ls="--")
    _ax(ax, title, ylabel)
    ax.legend(frameon=False, fontsize=8)
    save(fig, path)


def bars_mark(labels, values, title, ylabel, path, marks):
    bars(labels, values, title, ylabel, path, fmt="{:.2f}")
    # redraw is already saved; marks are separate via a local chart
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    drawn = ax.bar(labels, values, color=BLUE, width=0.68)
    _ax(ax, title, ylabel)
    for level in marks:
        ax.axhline(level, color=GRAY, lw=0.8, ls="--")
    low = min(0, min(values), min(marks))
    high = max(max(values), max(marks))
    span = high - low or 1
    ax.set_ylim(low - span * 0.05, high + span * 0.22)
    for bar, value in zip(drawn, values):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.2f}", ha="center", va="bottom", fontsize=8, color=INK)
    save(fig, path)


def partial_multi(frame, y, x, controls):
    f = frame[[y, x, *controls]].dropna()
    ry = f[y].rank().to_numpy()
    rx = f[x].rank().to_numpy()
    z = np.column_stack([np.ones(len(f))] + [f[c].rank().to_numpy() for c in controls])
    by, *_ = np.linalg.lstsq(z, ry, rcond=None)
    bx, *_ = np.linalg.lstsq(z, rx, rcond=None)
    return float(pd.Series(ry - z @ by).corr(pd.Series(rx - z @ bx)))


def main():
    b = f0(businesses())
    b["hit"] = b["checkout_orders"].gt(0)
    demo = read(INTERIM / "buyers_demo.parquet")
    reg = read(INTERIM / "buyers_region.parquet")
    daily = read(INTERIM / "market_daily.parquet")
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    daily["day"] = np.arange(1, len(daily) + 1)
    daily["dow"] = daily["date"].dt.day_of_week
    cat = read(INTERIM / "market_categories.parquet")
    src = read(INTERIM / "market_sources.parquet")

    mdemo = demo.dropna(subset=["market_buyers"]).copy()
    pdemo = demo.dropna(subset=["partner_buyers"]).copy()

    def gender_share(frame, col):
        total = frame[col].sum()
        women = frame.loc[frame["gender"].eq("Ж"), col].sum()
        return 100 * float(women / total)

    bars(
        ["Маркет", "Партнёр"],
        [gender_share(mdemo, "market_buyers"), gender_share(pdemo, "partner_buyers")],
        "Доля женщин среди покупателей",
        "%",
        dest(34),
        fmt="{:.1f}",
    )

    def opb(frame, buyers, orders, gender):
        sub = frame.loc[frame["gender"].eq(gender)]
        return float(sub[orders].sum() / sub[buyers].sum())

    grouped(
        ["Женщины", "Мужчины"],
        {
            "Маркет": [opb(mdemo, "market_buyers", "market_orders", "Ж"), opb(mdemo, "market_buyers", "market_orders", "М")],
            "Партнёр": [opb(pdemo, "partner_buyers", "partner_orders", "Ж"), opb(pdemo, "partner_buyers", "partner_orders", "М")],
        },
        "Заказов на одного покупателя",
        "заказов",
        dest(35),
        fmt="{:.2f}",
    )

    def women_band(frame, buyers, ages):
        total = frame[buyers].sum()
        num = frame.loc[frame["gender"].eq("Ж") & frame["age_band"].isin(ages), buyers].sum()
        return 100 * float(num / total)

    ages = ["35–44", "45–54"]
    bars(
        ["Маркет", "Партнёр"],
        [women_band(mdemo, "market_buyers", ages), women_band(pdemo, "partner_buyers", ages)],
        "Женщины 35–54, доля покупателей",
        "%",
        dest(36),
        fmt="{:.1f}",
    )

    order_age = ["до 18", "18–24", "25–34", "35–44", "45–54", "55+"]

    def age_shares(frame, col):
        sub = frame.loc[frame["age_band"].isin(order_age)]
        total = sub[col].sum()
        got = sub.groupby("age_band")[col].sum()
        return [100 * float(got.get(name, 0) / total) for name in order_age]

    grouped_h(
        order_age,
        {"Маркет": age_shares(mdemo, "market_buyers"), "Партнёр": age_shares(pdemo, "partner_buyers")},
        "Возраст покупателей",
        "% покупателей",
        dest(37),
    )

    preg = reg.dropna(subset=["partner_orders"])
    unnamed = float(preg.loc[preg["region"].eq("Не указан"), "partner_orders"].sum())
    named_orders = float(preg.loc[~preg["region"].eq("Не указан"), "partner_orders"].sum())
    total_p = unnamed + named_orders
    bars(
        ["Не указан", "Регион назван"],
        [100 * unnamed / total_p, 100 * named_orders / total_p],
        "Заказы Партнёра по заполненности региона",
        "%",
        dest(38),
        fmt="{:.1f}",
    )

    mreg = reg.dropna(subset=["market_orders"])
    mtotal = float(mreg["market_orders"].sum())
    top = (
        mreg.loc[~mreg["region"].eq("Не указан")]
        .sort_values("market_orders", ascending=False)
        .head(5)
    )
    hbars(
        list(top["region"]),
        [100 * float(v) / mtotal for v in top["market_orders"]],
        "Пять регионов, доля заказов Маркета",
        "% всех заказов Маркета",
        dest(39),
        fmt="{:.1f}",
    )

    both = reg.dropna(subset=["market_orders", "partner_orders"])
    both = both.loc[~both["region"].eq("Не указан")]
    both = both.loc[both["market_orders"].gt(0) & both["partner_orders"].gt(0)]
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(both["market_orders"], both["partner_orders"], s=16, c=BLUE, alpha=0.7, linewidths=0)
    ax.set_xscale("log")
    ax.set_yscale("log")
    _ax(ax, "Заказы по регионам", "Партнёр")
    ax.set_xlabel("Маркет", fontsize=9)
    save(fig, dest(40))

    weekend = daily["dow"].ge(5)
    day_share = 100 * float(weekend.mean())
    grouped(
        ["Доля дней", "Маркет", "Партнёр"],
        {"выходные": [
            day_share,
            100 * float(daily.loc[weekend, "market_orders"].sum() / daily["market_orders"].sum()),
            100 * float(daily.loc[weekend, "partner_orders"].sum() / daily["partner_orders"].sum()),
        ]},
        "Выходные в заказах",
        "%",
        dest(41),
        fmt="{:.1f}",
    )

    dow_name = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    med = [float(daily.loc[daily["dow"].eq(i), "market_orders"].median()) for i in range(7)]
    bars(dow_name, med, "Медиана заказов Маркета по дню недели", "заказов", dest(42), fmt="{:.0f}")

    lines(daily["day"], {"Заказы Маркета": daily["market_orders"]}, "Заказы Маркета по дням сентября", "заказов", dest(43))
    lines(daily["day"], {"Заказы Партнёра": daily["partner_orders"]}, "Заказы Партнёра по дням сентября", "заказов", dest(44))

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(daily["market_orders"], daily["partner_orders"], s=18, c=BLUE, alpha=0.75, linewidths=0)
    _ax(ax, "Заказы двух контуров в один день", "Партнёр")
    ax.set_xlabel("Маркет", fontsize=9)
    save(fig, dest(45))

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(daily["market_impressions"], daily["partner_impressions"], s=18, c=BLUE, alpha=0.75, linewidths=0)
    _ax(ax, "Показы двух контуров в один день", "Партнёр")
    ax.set_xlabel("Маркет", fontsize=9)
    save(fig, dest(46))

    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(daily["market_card_opens"], daily["partner_card_opens"], s=18, c=BLUE, alpha=0.75, linewidths=0)
    _ax(ax, "Открытия карточки в один день", "Партнёр")
    ax.set_xlabel("Маркет", fontsize=9)
    save(fig, dest(47))

    paid = 100 * daily["market_paid_orders"] / daily["market_orders"]
    lines(daily["day"], {"Доля оплаты": paid}, "Оплаченные заказы Маркета, % от оформленных", "%", dest(48))

    base = b.loc[b["business_type"].eq("товарное") & b["active_goods"].gt(0) & b["subscribers"].gt(1000)].copy()

    def rates(mask):
        mask = mask.fillna(False).astype(bool)
        yes = 100 * float(base.loc[mask, "hit"].mean())
        no = 100 * float(base.loc[~mask, "hit"].mean())
        return [yes, no]

    bars(["Доставка есть", "Доставки нет"], rates(base["delivery_enabled"]), "Доля с заказом, крупный активный каталог", "%", dest(49), fmt="{:.1f}")
    bars(["Товарный пост", "Поста нет"], rates(base["product_posts_30d"].gt(0)), "Доля с заказом, крупный активный каталог", "%", dest(50), fmt="{:.1f}")

    cells = []
    labels = []
    for delivery, post, label in (
        (False, False, "ни одного"),
        (True, False, "только доставка"),
        (False, True, "только пост"),
        (True, True, "оба"),
    ):
        mask = base["delivery_enabled"].eq(delivery) & base["product_posts_30d"].gt(0).eq(post)
        cells.append(100 * float(base.loc[mask, "hit"].mean()))
        labels.append(label)
    bars(labels, cells, "Доля с заказом: доставка и товарный пост", "%", dest(51), fmt="{:.1f}")

    bars(["Оплата есть", "Оплаты нет"], rates(base["payment_enabled"]), "Доля с заказом, крупный активный каталог", "%", dest(52), fmt="{:.1f}")
    bars(["Траты есть", "Трат нет"], rates(base["ad_spend_rub"].gt(0)), "Доля с заказом, крупный активный каталог", "%", dest(53), fmt="{:.1f}")

    prod = b.loc[b["business_type"].eq("товарное")].copy()
    prod["pay"] = prod["payment_enabled"].astype(int)
    prod["del"] = prod["delivery_enabled"].astype(int)
    bars_mark(
        ["Посты", "Клипы"],
        [
            partial_multi(prod, "checkout_orders", "product_posts_30d", ["subscribers", "active_goods"]),
            partial_spearman(prod["product_clips_30d"], prod["checkout_orders"], prod["subscribers"]),
        ],
        "Связь числа публикаций и заказов",
        "частичный Спирмен",
        dest(54),
        [0.10, 0.20],
    )
    bars(
        ["Рефералка есть", "Рефералки нет"],
        rates(base["referral_program"]),
        "Доля с заказом, крупный активный каталог",
        "%",
        dest(55),
        fmt="{:.1f}",
    )

    auth = base["original_content_author"]
    auth_rates = []
    for mask in (auth.map(lambda v: v is True), auth.map(lambda v: v is False), auth.isna()):
        auth_rates.append(100 * float(base.loc[mask, "hit"].mean()))
    bars(["Да", "Нет", "Пусто"], auth_rates, "Флаг автора и доля с заказом", "%", dest(56), fmt="{:.1f}")
    bars(["Товарный клип", "Клипа нет"], rates(base["product_clips_30d"].gt(0)), "Доля с заказом, крупный активный каталог", "%", dest(57), fmt="{:.1f}")
    bars(["Услуги есть", "Услуг нет"], rates(base["active_services"].gt(0)), "Доля с заказом, крупный активный каталог", "%", dest(58), fmt="{:.1f}")

    price = base["median_item_price_rub"]
    sample = base.loc[price.notna() & ~price.isin([0, 1, 1_060_000])].copy()
    sample["q"] = pd.qcut(sample["median_item_price_rub"], 4, labels=["Q1", "Q2", "Q3", "Q4"])
    q_rates = [100 * float(sample.loc[sample["q"].eq(q), "hit"].mean()) for q in ["Q1", "Q2", "Q3", "Q4"]]
    bars(["Q1 дешёвый", "Q2", "Q3", "Q4 дорогой"], q_rates, "Доля с заказом по квартилю цены", "%", dest(59), fmt="{:.1f}")

    u = b.loc[b["business_type"].isin(["товарное", "товарное и услужное", "без каталога"])].copy()
    from data import band

    u["band"] = band(u["subscribers"])
    u["hit"] = u["checkout_orders"].gt(0)
    u["checkout"] = u["checkout_enabled"].astype(bool)
    u["opens"] = u["product_card_opens_from_content"].gt(0)
    u["active_flag"] = u["posts_30d"].gt(0) | u["clips_30d"].gt(0)
    u["ads_flag"] = u["ad_spend_rub"].gt(0)
    grouped(
        ["Тип и размер", "+ активность", "+ реклама"],
        {
            "чекаут": [
                mh_or(u, "checkout", "hit", ["business_type", "band"]),
                mh_or(u, "checkout", "hit", ["business_type", "band", "active_flag"]),
                mh_or(u, "checkout", "hit", ["business_type", "band", "active_flag", "ads_flag"]),
            ],
            "открытия": [
                mh_or(u, "opens", "hit", ["business_type", "band"]),
                mh_or(u, "opens", "hit", ["business_type", "band", "active_flag"]),
                mh_or(u, "opens", "hit", ["business_type", "band", "active_flag", "ads_flag"]),
            ],
        },
        "Связь с заказом после контролей",
        "OR",
        dest(60),
        fmt="{:.2f}",
    )
    bars_mark(
        ["Активные | размер", "Загруженные | активные", "Размер | активные"],
        [
            partial_spearman(prod["active_goods"], prod["checkout_orders"], prod["subscribers"]),
            partial_spearman(prod["goods_loaded"], prod["checkout_orders"], prod["active_goods"]),
            partial_spearman(prod["subscribers"], prod["checkout_orders"], prod["active_goods"]),
        ],
        "Что связано с числом заказов",
        "частичный Спирмен",
        dest(61),
        [0.10, 0.20],
    )
    bars_mark(
        ["После постов", "После размера и постов"],
        [
            partial_spearman(prod["product_card_opens_from_content"], prod["checkout_orders"], prod["product_posts_30d"]),
            partial_multi(prod, "checkout_orders", "product_card_opens_from_content", ["subscribers", "product_posts_30d"]),
        ],
        "Открытия карточки и заказы",
        "частичный Спирмен",
        dest(62),
        [0.10, 0.20],
    )

    sellers = b.loc[b["hit"] & b["checkout_gmv_rub"].gt(0) & b["median_item_price_rub"].notna() & ~b["median_item_price_rub"].isin([0, 1, 1_060_000])].copy()
    ratio = (sellers["checkout_gmv_rub"] / sellers["checkout_orders"]) / sellers["median_item_price_rub"]
    shown = ratio.clip(upper=ratio.quantile(0.95))
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    ax.hist(shown, bins=24, color=BLUE)
    ax.axvline(1, color=AMBER, lw=1.2)
    _ax(ax, "Чек заказа / ценник карточки", "сообществ")
    ax.set_xlabel("отношение, хвост выше 95% срезан", fontsize=9)
    save(fig, dest(63))

    valid = prod.loc[prod["median_item_price_rub"].notna() & ~prod["median_item_price_rub"].isin([0, 1, 1_060_000])].copy()
    mult = valid["median_item_price_rub"] % 530 == 0
    bars(
        ["Кратна 530", "Другая цена"],
        [100 * float(valid.loc[mult, "hit"].mean()), 100 * float(valid.loc[~mult, "hit"].mean())],
        "Доля с заказом и шаг цены",
        "%",
        dest(64),
        fmt="{:.1f}",
    )

    theme_rows = []
    for theme, g in b.loc[b["hit"]].groupby("theme"):
        total = float(g["checkout_orders"].sum())
        if total < 30:
            continue
        theme_rows.append((str(theme), 100 * float(g["checkout_orders"].max() / total)))
    theme_rows.sort(key=lambda item: item[1])
    hbars([name for name, _ in theme_rows], [value for _, value in theme_rows], "Доля заказов темы у одного сообщества", "% заказов темы", dest(65), fmt="{:.0f}")

    shell = b["subscribers"].gt(1000) & b["posts_30d"].eq(0) & b["clips_30d"].eq(0)
    alive = b["subscribers"].gt(1000) & (b["posts_30d"].gt(0) | b["clips_30d"].gt(0))
    bars(
        ["Стена пустая", "Есть пост или клип"],
        [100 * float(b.loc[shell, "hit"].mean()), 100 * float(b.loc[alive, "hit"].mean())],
        "Крупные сообщества, доля с заказом",
        "%",
        dest(66),
        fmt="{:.1f}",
    )
    bars(
        ["Чекаут выключен", "Загрузка нулевая"],
        [
            int(b.loc[~b["checkout_enabled"] & b["hit"], "checkout_orders"].sum()),
            int(b.loc[b["goods_loaded"].eq(0) & b["hit"], "checkout_orders"].sum()),
        ],
        "Заказы на краю поля",
        "заказов",
        dest(67),
        fmt="{:.0f}",
    )

    skip = {"Другое", "Не определена", "Все товары"}
    clean = cat.loc[~cat["category"].isin(skip)].copy()
    msum = float(cat["market_orders"].sum())
    psum = float(cat["partner_orders"].sum())
    clean["m_share"] = 100 * clean["market_orders"] / msum
    clean["p_share"] = 100 * clean["partner_orders"] / psum
    clean = clean.loc[clean[["m_share", "p_share"]].max(axis=1).ge(2)]
    clean = clean.sort_values("market_orders", ascending=True)
    grouped_h(
        list(clean["category"]),
        {
            "Маркет": [100 * float(v) / msum for v in clean["market_orders"]],
            "Партнёр": [100 * float(v) / psum for v in clean["partner_orders"]],
        },
        "Доля заказов категории внутри своего листа",
        "%",
        dest(68),
    )

    fig, ax = plt.subplots(figsize=(6.4, 4.4))
    other = cat["category"].eq("Другое")
    rest = cat.loc[~other & cat["market_card_opens"].gt(0) & cat["market_orders"].gt(0)]
    odd = cat.loc[other]
    ax.scatter(rest["market_card_opens"], rest["market_orders"], s=22, c=BLUE, alpha=0.8, linewidths=0, label="категория")
    ax.scatter(odd["market_card_opens"], odd["market_orders"], s=36, c=AMBER, alpha=0.95, linewidths=0, label="Другое")
    ax.set_xscale("log")
    ax.set_yscale("log")
    _ax(ax, "Открытия и заказы категорий Маркета", "заказов")
    ax.set_xlabel("открытий карточки", fontsize=9)
    ax.legend(frameon=False, fontsize=8)
    save(fig, dest(69))

    comm_total = float(b["checkout_orders"].sum())
    culinary = float(b.loc[b["theme"].eq("Кулинария и еда"), "checkout_orders"].sum())
    beauty_c = float(b.loc[b["theme"].eq("Красота и здоровье"), "checkout_orders"].sum())
    beauty_p = float(cat.loc[cat["category"].eq("Красота и здоровье"), "partner_orders"].sum())
    food_m = float(cat.loc[cat["category"].eq("Продукты питания"), "market_orders"].sum())
    bars(
        ["Кулинария\nсообществ", "Красота\nсообществ", "Красота\nшопсов", "Еда\nМаркета"],
        [100 * culinary / comm_total, 100 * beauty_c / comm_total, 100 * beauty_p / psum, 100 * food_m / msum],
        "Доля внутри своего листа, не одни люди",
        "%",
        dest(70),
        fmt="{:.1f}",
    )

    def index_to_first(col):
        base_value = float(daily[col].iloc[0])
        return 100 * daily[col] / base_value

    lines(
        daily["day"],
        {"Открытия карточки": index_to_first("market_card_opens"), "Заказы": index_to_first("market_orders")},
        "Маркет, 1 сентября = 100",
        "индекс",
        dest(71),
    )
    lines(
        daily["day"],
        {"Дневная аудитория": index_to_first("market_dau"), "Заказы": index_to_first("market_orders")},
        "Маркет, 1 сентября = 100",
        "индекс",
        dest(72),
    )
    lines(
        daily["day"],
        {"Поисковые запросы": index_to_first("search_queries"), "Заказы": index_to_first("market_orders")},
        "Маркет, 1 сентября = 100",
        "индекс",
        dest(73),
    )

    cols = {
        "Заказы": "market_orders",
        "GMV": "market_gmv_rub",
        "Клики": "market_card_button_clicks",
        "Поиск": "search_queries",
    }
    bars(
        list(cols),
        [100 * float(daily.loc[weekend, col].sum() / daily[col].sum()) for col in cols.values()],
        "Доля сентября, пришедшаяся на выходные",
        "%",
        dest(74),
        fmt="{:.1f}",
    )

    comm_aov = float(sellers["checkout_gmv_rub"].sum() / sellers["checkout_orders"].sum())
    market_aov = float(daily["market_gmv_rub"].sum() / daily["market_orders"].sum())
    partner_aov = float(daily["partner_gmv_rub"].sum() / daily["partner_orders"].sum())
    bars(
        ["Сообщества", "Маркет, оформленный", "Партнёр"],
        [comm_aov, market_aov, partner_aov],
        "Рублей на один заказ",
        "₽",
        dest(75),
        fmt="{:.0f}",
    )
    lines(
        daily["day"],
        {"GMV Маркета": index_to_first("market_gmv_rub"), "GMV Партнёра": index_to_first("partner_gmv_rub")},
        "Оборот, 1 сентября = 100",
        "индекс",
        dest(76),
    )

    def cell_opb(gender, bands):
        sub = mdemo.loc[mdemo["gender"].eq(gender) & mdemo["age_band"].isin(bands)]
        return float(sub["market_orders"].sum() / sub["market_buyers"].sum())

    bars(
        ["Ж 18–34", "Ж 35–54", "М 18–34", "М 35–54"],
        [
            cell_opb("Ж", ["18–24", "25–34"]),
            cell_opb("Ж", ["35–44", "45–54"]),
            cell_opb("М", ["18–24", "25–34"]),
            cell_opb("М", ["35–44", "45–54"]),
        ],
        "Заказов на покупателя Маркета",
        "заказов",
        dest(77),
        fmt="{:.2f}",
    )
    named = reg.dropna(subset=["market_buyers", "market_orders"])
    named = named.loc[~named["region"].eq("Не указан")]
    moscow = named.loc[named["region"].str.contains("Москва")]
    rest = named.loc[~named["region"].str.contains("Москва")]
    bars(
        ["Москва", "Остальные регионы"],
        [
            float(moscow["market_orders"].sum() / moscow["market_buyers"].sum()),
            float(rest["market_orders"].sum() / rest["market_buyers"].sum()),
        ],
        "Заказов на покупателя Маркета",
        "заказов",
        dest(78),
        fmt="{:.3f}",
    )

    feed = {"Лента", "Клипы"}
    bars(
        ["Маркет", "Партнёр"],
        [
            float(src.loc[src["source"].isin(feed), "market_share_pct"].sum()),
            float(src.loc[src["source"].isin(feed), "partner_share_pct"].sum()),
        ],
        "Открытия карточки из ленты и клипов",
        "%",
        dest(79),
        fmt="{:.1f}",
    )
    bars_mark(
        ["Сырой", "После номера дня"],
        [
            spearman(daily["market_impressions"], daily["market_orders"]),
            partial_spearman(daily["market_impressions"], daily["market_orders"], daily["day"]),
        ],
        "Показы и заказы Маркета",
        "Спирмен",
        dest(80),
        [0.10, 0.20],
    )
    bars_mark(
        ["Товарные\nпросмотры", "Обычные\nпросмотры", "Товарные\nлайки"],
        [
            partial_spearman(prod["product_content_views"], prod["checkout_orders"], prod["subscribers"]),
            partial_spearman(prod["regular_content_views"], prod["checkout_orders"], prod["subscribers"]),
            partial_spearman(prod["product_content_likes"], prod["checkout_orders"], prod["subscribers"]),
        ],
        "Охват и заказы после размера",
        "частичный Спирмен",
        dest(81),
        [0.10, 0.20],
    )
    bars(
        ["Чекаут включён", "Чекаут выключен"],
        rates(base["checkout_enabled"]),
        "Доля с заказом, крупный активный каталог",
        "%",
        dest(82),
        fmt="{:.1f}",
    )
    bars(
        ["Обычный пост есть", "Поста нет"],
        rates(base["posts_30d"].gt(0)),
        "Доля с заказом, крупный активный каталог",
        "%",
        dest(83),
        fmt="{:.1f}",
    )
    print("plots", 34, "to", 83)


if __name__ == "__main__":
    main()
