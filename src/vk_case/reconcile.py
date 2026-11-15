"""Сверки уже записанных таблиц data/interim.

Проверки сравнивают листы между собой и с числами, снятыми при аудите файла.
Расхождение, которое в файле есть, помечается как ожидаемое и не чинится.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from vk_case.paths import INTERIM_DIR, PERIOD_TEXT, SCHEMA_PATH

RECONCILIATION_COLUMNS = [
    ("seq", "int64", "Порядок проверки."),
    ("check_id", "string", "Стабильный код проверки."),
    ("kind", "string", "shape, census, cross_sheet, rounding или invariant."),
    ("lhs_label", "string", "Левая величина."),
    ("rhs_label", "string", "Правая величина."),
    ("lhs_value", "float64", "Левое число. Пусто у текстовой сверки."),
    ("rhs_value", "float64", "Правое число. Пусто у текстовой сверки."),
    ("delta", "float64", "lhs − rhs. Пусто у текстовой сверки."),
    ("expected_delta", "float64", "Какая дельта считается верной для этого файла."),
    ("tolerance", "float64", "Допуск вокруг expected_delta."),
    ("status", "string", "pass или fail."),
    ("detail", "string", "Короткое пояснение, если оно нужно."),
]

# Целые числа воронки, снятые с листа итогов при аудите.
CONTOUR_INT = {
    ("impressions", "market_vk"): 4_777_750_023,
    ("impressions", "partner_1"): 5_729_628_790,
    ("card_opens", "market_vk"): 193_512_461,
    ("card_opens", "partner_1"): 86_882_822,
    ("card_button_clicks", "market_vk"): 5_969_063,
    ("card_button_clicks", "partner_1"): 36_626_075,
    ("direct_partner_transitions", "partner_1"): 106_914_679,
    ("placed_orders", "market_vk"): 413_740,
    ("placed_orders", "partner_1"): 4_927_525,
    ("paid_orders", "market_vk"): 4_903,
    ("gmv_rub", "market_vk"): 1_564_546_740,
    ("gmv_rub", "partner_1"): 5_119_514_685,
    ("average_order_value_rub", "market_vk"): 3_781,
    ("average_order_value_rub", "partner_1"): 1_039,
    ("unique_buyers_30d", "market_vk"): 296_148,
    ("unique_buyers_30d", "partner_1"): 2_901_334,
    ("buyers_on_breakdown_sheets", "market_vk"): 295_850,
    ("buyers_on_breakdown_sheets", "partner_1"): 2_901_162,
    ("orders_on_breakdown_sheets", "market_vk"): 413_334,
    ("orders_on_breakdown_sheets", "partner_1"): 4_557_253,
}

CONTOUR_NUM = {
    ("orders_per_buyer", "market_vk"): 1.4,
    ("orders_per_buyer", "partner_1"): 1.7,
    ("repeat_buyers_share_pct", "market_vk"): 19.0,
    ("repeat_buyers_share_pct", "partner_1"): 26.6,
    ("impression_to_card_open_pct", "market_vk"): 4.05,
    ("impression_to_card_open_pct", "partner_1"): 1.52,
    ("card_open_to_order_pct", "market_vk"): 0.21,
    ("card_open_to_order_pct", "partner_1"): 5.67,
    ("impression_to_order_pct", "market_vk"): 0.009,
    ("impression_to_order_pct", "partner_1"): 0.086,
}

PLATFORM_INT = {
    "market_dau_avg": 127_406,
    "market_mau": 2_997_341,
    "users_saw_goods_30d": 66_617_967,
    "users_opened_card_30d": 27_333_960,
    "card_opens_from_posts_and_clips": 86_321_893,
    "card_opens_from_referral_posts_and_clips": 82_324_081,
    "product_search_queries": 28_585_243,
}


@dataclass
class Check:
    check_id: str
    kind: str
    lhs_label: str
    rhs_label: str
    lhs_value: float | None = None
    rhs_value: float | None = None
    expected_delta: float = 0.0
    tolerance: float = 0.0
    lhs_text: str | None = None
    rhs_text: str | None = None
    detail: str = ""

    def resolve(self) -> tuple[str, float | None]:
        if self.lhs_text is not None or self.rhs_text is not None:
            status = "pass" if self.lhs_text == self.rhs_text else "fail"
            return status, None
        delta = float(self.lhs_value) - float(self.rhs_value)
        status = "pass" if abs(delta - self.expected_delta) <= self.tolerance else "fail"
        return status, delta


def run_reconciliation() -> int:
    tables = {path.stem: _read(path) for path in sorted(INTERIM_DIR.glob("*.parquet")) if path.stem != "reconciliation"}
    checks = build_checks(tables)
    frame = _frame(checks)
    _write(frame)
    _check_schema_columns(frame)
    failed = frame.loc[frame["status"] == "fail"]
    print(f"reconciliation: {len(frame) - len(failed)} pass, {len(failed)} fail")
    if len(failed):
        print(failed.to_string(index=False))
        return 1
    return 0


def build_checks(tables: dict[str, pd.DataFrame]) -> list[Check]:
    businesses = tables["businesses"]
    contour = tables["market_contour_metrics"]
    platform = tables["market_platform_metrics"]
    daily = tables["market_daily"]
    sources = tables["market_sources"]
    nested = tables["market_source_nested"]
    categories = tables["market_categories"]
    demo = tables["buyers_demo"]
    regions = tables["buyers_region"]
    checks: list[Check] = []

    def add(check: Check) -> None:
        checks.append(check)

    add(Check("businesses_rows", "shape", "rows", "audit", len(businesses), 9754))
    add(Check("business_id_unique", "shape", "nunique business_id", "rows", businesses["business_id"].nunique(), len(businesses)))
    add(Check("business_id_min", "shape", "min business_id", "1", int(businesses["business_id"].min()), 1))
    add(Check("business_id_max", "shape", "max business_id", "9754", int(businesses["business_id"].max()), 9754))
    add(Check("businesses_first_id", "shape", "first business_id", "file order", int(businesses["business_id"].iloc[0]), 9308, detail="Порядок строк файла сохранён"))
    add(Check("daily_rows", "shape", "rows", "30", len(daily), 30))
    add(Check("contour_rows", "shape", "rows", "32", len(contour), 32))
    add(Check("platform_rows", "shape", "rows", "9", len(platform), 9))
    add(Check("source_rows", "shape", "rows", "6", len(sources), 6))
    add(Check("nested_source_rows", "shape", "rows", "1", len(nested), 1))
    add(Check("category_rows", "shape", "rows", "18", len(categories), 18))
    add(Check("demo_rows", "shape", "rows", "15", len(demo), 15))
    add(Check("region_rows", "shape", "rows", "89", len(regions), 89))

    day_values = [value.date() if hasattr(value, "date") else value for value in daily["date"].tolist()]
    expected_days = pd.date_range("2026-09-01", "2026-09-30", freq="D").date.tolist()
    add(
        Check(
            "daily_calendar",
            "shape",
            "dates",
            "2026-09-01..2026-09-30",
            lhs_text=",".join(str(item) for item in day_values),
            rhs_text=",".join(str(item) for item in expected_days),
        )
    )

    for (metric_id, contour_id), expected in CONTOUR_INT.items():
        actual = _contour_int(contour, metric_id, contour_id)
        add(Check(f"census_{metric_id}_{contour_id}", "census", f"{metric_id}.{contour_id}", "audit", actual, expected))
    for (metric_id, contour_id), expected in CONTOUR_NUM.items():
        actual = _contour_num(contour, metric_id, contour_id)
        add(
            Check(
                f"census_{metric_id}_{contour_id}",
                "census",
                f"{metric_id}.{contour_id}",
                "audit",
                actual,
                expected,
                tolerance=1e-9,
            )
        )
    dashes = contour.loc[contour["null_reason"].notna(), ["metric_id", "contour", "null_reason", "value_int", "value_num"]]
    dash_key = sorted(f"{row.metric_id}:{row.contour}:{row.null_reason}" for row in dashes.itertuples())
    add(
        Check(
            "contour_dashes",
            "shape",
            "not_applicable cells",
            "two em dashes",
            lhs_text="|".join(dash_key),
            rhs_text="direct_partner_transitions:market_vk:not_applicable|paid_orders:partner_1:not_applicable",
            detail="Значения этих ячеек пустые",
        )
    )
    if len(dashes) and (dashes["value_int"].notna().any() or dashes["value_num"].notna().any()):
        add(Check("contour_dash_values_empty", "invariant", "filled dash cells", "0", 1, 0))
    else:
        add(Check("contour_dash_values_empty", "invariant", "filled dash cells", "0", 0, 0))

    for metric_id, expected in PLATFORM_INT.items():
        actual = int(platform.loc[platform["metric_id"] == metric_id, "value_int"].iloc[0])
        add(Check(f"census_platform_{metric_id}", "census", metric_id, "audit", actual, expected))
    search_pct = float(platform.loc[platform["metric_id"] == "product_search_queries_with_card_open_pct", "value_num"].iloc[0])
    add(Check("census_platform_search_pct", "census", "search pct", "audit 18.4", search_pct, 18.4, tolerance=1e-9))
    period = platform.loc[platform["metric_id"] == "period", "value_text"].iloc[0]
    add(Check("platform_period_text", "census", "period", "audit", lhs_text=str(period), rhs_text=PERIOD_TEXT))
    nested_flags = int(platform["is_nested"].sum())
    add(Check("platform_nested_flag_count", "shape", "is_nested true", "1", nested_flags, 1))

    both_values = contour["value_int"].notna() & contour["value_num"].notna()
    neither_without_reason = contour["value_int"].isna() & contour["value_num"].isna() & contour["null_reason"].isna()
    add(Check("contour_both_value_columns", "invariant", "rows with int and num", "0", int(both_values.sum()), 0))
    add(Check("contour_empty_without_reason", "invariant", "rows without value or reason", "0", int(neither_without_reason.sum()), 0))

    pairs = [
        ("market_impressions", "impressions", "market_vk", 0),
        ("partner_impressions", "impressions", "partner_1", 0),
        ("market_card_opens", "card_opens", "market_vk", 0),
        ("partner_card_opens", "card_opens", "partner_1", 0),
        ("market_card_button_clicks", "card_button_clicks", "market_vk", 0),
        ("partner_card_button_clicks", "card_button_clicks", "partner_1", 0),
        ("market_orders", "placed_orders", "market_vk", 0),
        ("partner_orders", "placed_orders", "partner_1", 0),
        ("market_paid_orders", "paid_orders", "market_vk", 0),
        ("market_gmv_rub", "gmv_rub", "market_vk", 0),
        ("partner_gmv_rub", "gmv_rub", "partner_1", -1),
    ]
    for column, metric_id, contour_id, expected_delta in pairs:
        add(
            Check(
                f"daily_sum_{column}",
                "cross_sheet",
                f"sum(market_daily.{column})",
                f"contour.{metric_id}.{contour_id}",
                int(daily[column].sum()),
                _contour_int(contour, metric_id, contour_id),
                expected_delta=expected_delta,
                detail="Ожидаемая дельта −1 ₽ только у GMV Партнёра" if expected_delta else "",
            )
        )
    add(
        Check(
            "daily_search_vs_platform",
            "cross_sheet",
            "sum(search_queries)",
            "platform.product_search_queries",
            int(daily["search_queries"].sum()),
            int(platform.loc[platform["metric_id"] == "product_search_queries", "value_int"].iloc[0]),
        )
    )
    search_with_open = int(daily["search_queries_with_card_open"].sum())
    search_total = int(daily["search_queries"].sum())
    add(
        Check(
            "search_share_rounding",
            "rounding",
            "round(opens / queries, 1)",
            "platform pct",
            round(search_with_open / search_total * 100, 1),
            search_pct,
            tolerance=1e-9,
        )
    )
    add(
        Check(
            "dau_mean_vs_platform",
            "rounding",
            "mean(market_dau)",
            "platform market_dau_avg",
            float(daily["market_dau"].mean()),
            float(platform.loc[platform["metric_id"] == "market_dau_avg", "value_int"].iloc[0]),
            tolerance=0.5,
            detail="В файле среднее записано целым 127406 при точном среднем 127406.33",
        )
    )

    add(
        Check(
            "sources_market_opens",
            "cross_sheet",
            "sum(sources.market_card_opens)",
            "contour.card_opens.market_vk",
            int(sources["market_card_opens"].sum()),
            _contour_int(contour, "card_opens", "market_vk"),
        )
    )
    add(
        Check(
            "sources_partner_opens",
            "cross_sheet",
            "sum(sources.partner_card_opens)",
            "contour.card_opens.partner_1",
            int(sources["partner_card_opens"].sum()),
            _contour_int(contour, "card_opens", "partner_1"),
        )
    )
    add(Check("sources_market_share_sum", "cross_sheet", "sum(market_share_pct)", "100", float(sources["market_share_pct"].sum()), 100, tolerance=1e-6))
    add(Check("sources_partner_share_sum", "cross_sheet", "sum(partner_share_pct)", "100", float(sources["partner_share_pct"].sum()), 100, tolerance=1e-6))
    market_share_error, market_share_where = _share_error(sources, "market_card_opens", "market_share_pct")
    partner_share_error, partner_share_where = _share_error(sources, "partner_card_opens", "partner_share_pct")
    add(Check("sources_market_share_rounding", "rounding", "max |stored − rounded|", "0", market_share_error, 0, tolerance=1e-6, detail=market_share_where))
    add(Check("sources_partner_share_rounding", "rounding", "max |stored − rounded|", "0", partner_share_error, 0, tolerance=1e-6, detail=partner_share_where))
    nested_opens = int(nested["partner_card_opens"].iloc[0])
    nested_share = float(nested["partner_share_pct"].iloc[0])
    partner_opens = int(sources["partner_card_opens"].sum())
    add(
        Check(
            "nested_matches_platform_referral",
            "cross_sheet",
            "nested.partner_card_opens",
            "platform referral",
            nested_opens,
            int(platform.loc[platform["metric_id"] == "card_opens_from_referral_posts_and_clips", "value_int"].iloc[0]),
        )
    )
    add(
        Check(
            "nested_share_rounding",
            "rounding",
            "round(nested / partner opens, 1)",
            "stored share",
            round(nested_opens / partner_opens * 100, 1),
            nested_share,
            tolerance=1e-9,
        )
    )

    add(
        Check(
            "categories_market_opens_delta",
            "cross_sheet",
            "sum(category market opens)",
            "contour card opens",
            int(categories["market_card_opens"].sum()),
            _contour_int(contour, "card_opens", "market_vk"),
            expected_delta=-39_949,
        )
    )
    add(
        Check(
            "categories_market_orders_delta",
            "cross_sheet",
            "sum(category market orders)",
            "contour placed orders",
            int(categories["market_orders"].sum()),
            _contour_int(contour, "placed_orders", "market_vk"),
            expected_delta=21_545,
        )
    )
    add(
        Check(
            "categories_partner_opens_delta",
            "cross_sheet",
            "sum(category partner opens)",
            "contour card opens",
            int(categories["partner_card_opens"].sum()),
            _contour_int(contour, "card_opens", "partner_1"),
            expected_delta=-2_220,
        )
    )
    add(
        Check(
            "categories_partner_orders_delta",
            "cross_sheet",
            "sum(category partner orders)",
            "contour placed orders",
            int(categories["partner_orders"].sum()),
            _contour_int(contour, "placed_orders", "partner_1"),
            expected_delta=-370_008,
        )
    )
    kept = sorted(categories["category"].tolist())
    for label in ("Все товары", "Другое", "Не определена"):
        add(Check(f"category_kept_{label}", "shape", label, "present", lhs_text=label if label in kept else "", rhs_text=label))

    for column, metric_id in (
        ("market_buyers", "buyers_on_breakdown_sheets"),
        ("market_orders", "orders_on_breakdown_sheets"),
        ("partner_buyers", "buyers_on_breakdown_sheets"),
        ("partner_orders", "orders_on_breakdown_sheets"),
    ):
        contour_id = "market_vk" if column.startswith("market") else "partner_1"
        add(
            Check(
                f"demo_sum_{column}",
                "cross_sheet",
                f"sum(buyers_demo.{column})",
                f"contour.{metric_id}.{contour_id}",
                int(demo[column].sum()),
                _contour_int(contour, metric_id, contour_id),
            )
        )
        add(
            Check(
                f"region_equals_demo_{column}",
                "cross_sheet",
                f"sum(buyers_region.{column})",
                f"sum(buyers_demo.{column})",
                int(regions[column].sum()),
                int(demo[column].sum()),
            )
        )
    add(Check("demo_market_null_buyers", "shape", "null market_buyers", "2", int(demo["market_buyers"].isna().sum()), 2))
    add(Check("region_market_null_buyers", "shape", "null market_buyers", "4", int(regions["market_buyers"].isna().sum()), 4))
    add(
        Check(
            "demo_market_nulls_aligned",
            "invariant",
            "buyer/order null mismatch",
            "0",
            int((demo["market_buyers"].isna() != demo["market_orders"].isna()).sum()),
            0,
        )
    )
    add(
        Check(
            "region_market_nulls_aligned",
            "invariant",
            "buyer/order null mismatch",
            "0",
            int((regions["market_buyers"].isna() != regions["market_orders"].isna()).sum()),
            0,
        )
    )

    add(Check("business_orders_sum", "census", "sum checkout_orders", "audit", int(businesses["checkout_orders"].sum()), 3478))
    add(Check("business_gmv_sum", "census", "sum checkout_gmv_rub", "audit", int(businesses["checkout_gmv_rub"].sum()), 9_973_027))
    add(Check("business_ad_spend_sum", "census", "sum ad_spend_rub", "audit", int(businesses["ad_spend_rub"].sum()), 92_363_414))
    add(Check("businesses_with_orders", "census", "orders > 0", "audit", int((businesses["checkout_orders"] > 0).sum()), 298))
    add(Check("businesses_with_ads", "census", "ad spend > 0", "audit", int((businesses["ad_spend_rub"] > 0).sum()), 542))
    add(Check("checkout_enabled_count", "census", "checkout true", "audit", int(businesses["checkout_enabled"].sum()), 5737))
    add(Check("delivery_enabled_count", "census", "delivery true", "audit", int(businesses["delivery_enabled"].sum()), 919))
    add(Check("payment_enabled_count", "census", "payment true", "audit", int(businesses["payment_enabled"].sum()), 255))
    add(Check("referral_count", "census", "referral true", "audit", int(businesses["referral_program"].sum()), 201))
    author = businesses["original_content_author"]
    add(Check("author_true", "census", "author true", "audit", int((author == True).sum()), 1794))  # noqa: E712
    add(Check("author_false", "census", "author false", "audit", int((author == False).sum()), 5390))  # noqa: E712
    add(Check("author_null", "census", "author null", "audit", int(author.isna().sum()), 2570))
    add(Check("aov_null", "census", "aov null", "audit", int(businesses["average_order_value_rub"].isna().sum()), 9463))
    add(Check("price_null", "census", "median price null", "audit", int(businesses["median_item_price_rub"].isna().sum()), 5412))
    add(Check("theme_nunique", "census", "themes", "42", businesses["theme"].nunique(), 42))
    for label, expected in (
        ("без каталога", 3168),
        ("товарное", 3150),
        ("услужное", 2428),
        ("товарное и услужное", 1008),
    ):
        add(Check(f"business_type_{label}", "census", label, "audit", int((businesses["business_type"] == label).sum()), expected))

    add(Check("active_goods_above_loaded", "invariant", "rows active > loaded", "0", int((businesses["active_goods"] > businesses["goods_loaded"]).sum()), 0))
    add(Check("product_clips_above_clips", "invariant", "rows product clips > clips", "0", int((businesses["product_clips_30d"] > businesses["clips_30d"]).sum()), 0))
    add(Check("gmv_without_orders", "invariant", "rows gmv > 0 and orders = 0", "0", int(((businesses["checkout_gmv_rub"] > 0) & (businesses["checkout_orders"] == 0)).sum()), 0))
    aov_mismatch = businesses["average_order_value_rub"].isna() != (businesses["checkout_gmv_rub"] == 0)
    add(Check("aov_null_iff_gmv_zero", "invariant", "rows breaking the null rule", "0", int(aov_mismatch.sum()), 0))
    numeric = [column for column in businesses.columns if pd.api.types.is_numeric_dtype(businesses[column])]
    negatives = int(sum(int((businesses[column].dropna() < 0).sum()) for column in numeric))
    add(Check("business_negatives", "invariant", "negative cells", "0", negatives, 0))

    daily_breaks = {
        "daily_market_opens_above_impressions": daily["market_card_opens"] > daily["market_impressions"],
        "daily_partner_opens_above_impressions": daily["partner_card_opens"] > daily["partner_impressions"],
        "daily_market_clicks_above_opens": daily["market_card_button_clicks"] > daily["market_card_opens"],
        "daily_partner_clicks_above_opens": daily["partner_card_button_clicks"] > daily["partner_card_opens"],
        "daily_market_orders_above_opens": daily["market_orders"] > daily["market_card_opens"],
        "daily_partner_orders_above_opens": daily["partner_orders"] > daily["partner_card_opens"],
        "daily_paid_above_orders": daily["market_paid_orders"] > daily["market_orders"],
        "daily_market_buyers_above_orders": daily["market_buyers"] > daily["market_orders"],
        "daily_partner_buyers_above_orders": daily["partner_buyers"] > daily["partner_orders"],
        "daily_search_opens_above_queries": daily["search_queries_with_card_open"] > daily["search_queries"],
        "daily_openers_above_viewers": daily["users_opened_card"] > daily["users_saw_goods"],
    }
    for check_id, mask in daily_breaks.items():
        add(Check(check_id, "invariant", "days breaking the funnel", "0", int(mask.sum()), 0))

    derived = _derived_rounding_checks(contour)
    checks.extend(derived)
    return checks


def _derived_rounding_checks(contour: pd.DataFrame) -> list[Check]:
    def num(metric_id: str, contour_id: str) -> float:
        return _contour_num(contour, metric_id, contour_id)

    def whole(metric_id: str, contour_id: str) -> int:
        return _contour_int(contour, metric_id, contour_id)

    checks = []
    specs = [
        ("market_vk", 0, "average_order_value_rub", lambda c: round(whole("gmv_rub", c) / whole("placed_orders", c))),
        ("partner_1", 0, "average_order_value_rub", lambda c: round(whole("gmv_rub", c) / whole("placed_orders", c))),
        ("market_vk", 1, "orders_per_buyer", lambda c: round(whole("placed_orders", c) / whole("unique_buyers_30d", c), 1)),
        ("partner_1", 1, "orders_per_buyer", lambda c: round(whole("placed_orders", c) / whole("unique_buyers_30d", c), 1)),
        ("market_vk", 2, "impression_to_card_open_pct", lambda c: round(whole("card_opens", c) / whole("impressions", c) * 100, 2)),
        ("partner_1", 2, "impression_to_card_open_pct", lambda c: round(whole("card_opens", c) / whole("impressions", c) * 100, 2)),
        ("market_vk", 2, "card_open_to_order_pct", lambda c: round(whole("placed_orders", c) / whole("card_opens", c) * 100, 2)),
        ("partner_1", 2, "card_open_to_order_pct", lambda c: round(whole("placed_orders", c) / whole("card_opens", c) * 100, 2)),
        ("market_vk", 3, "impression_to_order_pct", lambda c: round(whole("placed_orders", c) / whole("impressions", c) * 100, 3)),
        ("partner_1", 3, "impression_to_order_pct", lambda c: round(whole("placed_orders", c) / whole("impressions", c) * 100, 3)),
    ]
    for contour_id, _digits, metric_id, formula in specs:
        stored = num(metric_id, contour_id) if metric_id != "average_order_value_rub" else float(whole(metric_id, contour_id))
        recomputed = float(formula(contour_id))
        checks.append(
            Check(
                f"rounding_{metric_id}_{contour_id}",
                "rounding",
                f"recomputed {metric_id}",
                f"stored {contour_id}",
                recomputed,
                stored,
                tolerance=1e-9,
            )
        )
    return checks


def _share_error(frame: pd.DataFrame, opens: str, share: str) -> tuple[float, str]:
    total = int(frame[opens].sum())
    worst = 0.0
    where = ""
    for row in frame.itertuples(index=False):
        error = abs(float(getattr(row, share)) - round(int(getattr(row, opens)) / total * 100, 1))
        if error > worst:
            worst = error
            where = str(row.source)
    return worst, where


def _contour_int(frame: pd.DataFrame, metric_id: str, contour_id: str) -> int:
    rows = frame.loc[(frame["metric_id"] == metric_id) & (frame["contour"] == contour_id), "value_int"]
    if len(rows) != 1 or pd.isna(rows.iloc[0]):
        raise SystemExit(f"Нет целого значения {metric_id}/{contour_id}")
    return int(rows.iloc[0])


def _contour_num(frame: pd.DataFrame, metric_id: str, contour_id: str) -> float:
    rows = frame.loc[(frame["metric_id"] == metric_id) & (frame["contour"] == contour_id), "value_num"]
    if len(rows) != 1 or pd.isna(rows.iloc[0]):
        raise SystemExit(f"Нет числового значения {metric_id}/{contour_id}")
    return float(rows.iloc[0])


def _frame(checks: list[Check]) -> pd.DataFrame:
    records = []
    for seq, check in enumerate(checks, start=1):
        status, delta = check.resolve()
        records.append(
            {
                "seq": seq,
                "check_id": check.check_id,
                "kind": check.kind,
                "lhs_label": check.lhs_label,
                "rhs_label": check.rhs_label,
                "lhs_value": check.lhs_value,
                "rhs_value": check.rhs_value,
                "delta": delta,
                "expected_delta": None if check.lhs_text is not None or check.rhs_text is not None else check.expected_delta,
                "tolerance": None if check.lhs_text is not None or check.rhs_text is not None else check.tolerance,
                "status": status,
                "detail": check.detail or ("" if status == "pass" else f"{check.lhs_text!r} != {check.rhs_text!r}"),
            }
        )
    return pd.DataFrame.from_records(records)


def _write(frame: pd.DataFrame) -> None:
    schema = pa.schema(
        [
            pa.field("seq", pa.int64(), nullable=False),
            pa.field("check_id", pa.string(), nullable=False),
            pa.field("kind", pa.string(), nullable=False),
            pa.field("lhs_label", pa.string(), nullable=False),
            pa.field("rhs_label", pa.string(), nullable=False),
            pa.field("lhs_value", pa.float64(), nullable=True),
            pa.field("rhs_value", pa.float64(), nullable=True),
            pa.field("delta", pa.float64(), nullable=True),
            pa.field("expected_delta", pa.float64(), nullable=True),
            pa.field("tolerance", pa.float64(), nullable=True),
            pa.field("status", pa.string(), nullable=False),
            pa.field("detail", pa.string(), nullable=False),
        ]
    )
    table = pa.Table.from_pandas(frame, schema=schema, preserve_index=False)
    pq.write_table(table, INTERIM_DIR / "reconciliation.parquet", compression="zstd")


def _check_schema_columns(frame: pd.DataFrame) -> None:
    document = yaml.safe_load(SCHEMA_PATH.read_text(encoding="utf-8"))
    for name, spec in document["tables"].items():
        path = INTERIM_DIR / f"{name}.parquet"
        if name == "reconciliation":
            actual = list(frame.columns)
        elif path.exists():
            actual = list(pq.read_schema(path).names)
        else:
            raise SystemExit(f"В схеме есть {name}, файла нет")
        expected = [column["name"] for column in spec["columns"]]
        if actual != expected:
            raise SystemExit(f"Колонки {name} не совпали со schema.yml:\n{actual}\n{expected}")


def _read(path) -> pd.DataFrame:
    def mapper(dtype):
        if pa.types.is_integer(dtype):
            return pd.Int64Dtype()
        if pa.types.is_boolean(dtype):
            return pd.BooleanDtype()
        return None

    return pq.read_table(path).to_pandas(types_mapper=mapper)
