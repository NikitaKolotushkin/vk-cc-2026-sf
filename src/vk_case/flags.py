"""Флаги качества поверх data/interim.

Строки не удаляются и не исправляются. Флаг только помечает уже
зафиксированное свойство строки. Пороги взяты из spec-ds-01.
"""

from __future__ import annotations

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml

from vk_case.paths import INTERIM_DIR, PROCESSED_DIR, PROCESSED_SCHEMA_PATH

BUSINESS_FLAGS = [
    ("is_exact_metric_clone", "Повтор той же метрической строки. Первая строка группы в порядке таблицы не помечена."),
    ("is_high_post_volume", "posts_30d ≥ 1000."),
    ("is_high_product_post_volume", "product_posts_30d ≥ 1000."),
    ("is_extreme_catalog", "goods_loaded ≥ 10000."),
    ("is_extreme_ad_spend", "ad_spend_rub ≥ 1000000."),
    ("is_price_floor_1", "median_item_price_rub = 1. Пустая цена не помечается."),
    ("is_price_zero", "median_item_price_rub = 0. Пустая цена не помечается."),
    ("is_price_cap_1060000", "median_item_price_rub = 1060000."),
    ("is_low_activity", "posts_30d = 0 и clips_30d = 0."),
    (
        "is_hard_zero",
        "Ноль постов, клипов, обычных просмотров, загруженных товаров, услуг, заказов и рекламы.",
    ),
    ("has_orders", "checkout_orders > 0."),
    ("has_orders_without_checkout", "checkout_orders > 0 и checkout_enabled = false."),
    ("has_orders_with_zero_gmv", "checkout_orders > 0 и checkout_gmv_rub = 0."),
    ("has_checkout_without_loaded_goods", "checkout_enabled и goods_loaded = 0."),
    ("has_loaded_without_active", "goods_loaded > 0 и active_goods = 0."),
    (
        "has_type_catalog_mismatch",
        "без каталога или услужное при goods_loaded > 0, либо товарное при goods_loaded = 0.",
    ),
    ("has_service_type_without_services", "business_type = услужное и active_services = 0."),
    ("has_product_posts_above_posts", "product_posts_30d > posts_30d."),
    (
        "has_engagement_above_views",
        "Лайки или репосты больше просмотров у обычного или товарного контента.",
    ),
    ("has_opens_without_product_views", "product_card_opens_from_content > 0 и product_content_views = 0."),
    (
        "has_aov_gap_gt_5pct",
        "При заказах и ненулевом GMV |средний чек − GMV / заказы| / (GMV / заказы) > 0.05.",
    ),
    ("has_ads_without_orders", "ad_spend_rub > 0 и checkout_orders = 0."),
    ("has_tool_not_nested", "delivery_enabled или payment_enabled при checkout_enabled = false."),
]

CATEGORY_FLAGS = [
    ("is_residual_category", "Категория «Другое» или «Не определена»."),
    ("is_all_goods_label", "Категория «Все товары», не итог таблицы."),
]

DEMO_FLAGS = [
    ("is_age_unknown", "age_band = н/д."),
    ("is_market_suppressed", "market_buyers пустой. Это подавление, не ноль."),
]

REGION_FLAGS = [
    ("is_unspecified_region", "region = Не указан."),
    ("is_market_suppressed", "market_buyers пустой. Это подавление, не ноль."),
]

EXPECTED_COUNTS = {
    "businesses.is_exact_metric_clone": 26,
    "businesses.is_high_post_volume": 33,
    "businesses.is_high_product_post_volume": 4,
    "businesses.is_extreme_catalog": 5,
    "businesses.is_extreme_ad_spend": 10,
    "businesses.is_price_floor_1": 94,
    "businesses.is_price_zero": 3,
    "businesses.is_price_cap_1060000": 3,
    "businesses.is_low_activity": 2373,
    "businesses.is_hard_zero": 64,
    "businesses.has_orders": 298,
    "businesses.has_orders_without_checkout": 14,
    "businesses.has_orders_with_zero_gmv": 7,
    "businesses.has_checkout_without_loaded_goods": 1907,
    "businesses.has_loaded_without_active": 818,
    "businesses.has_type_catalog_mismatch": 648,
    "businesses.has_service_type_without_services": 1611,
    "businesses.has_product_posts_above_posts": 11,
    "businesses.has_engagement_above_views": 17,
    "businesses.has_opens_without_product_views": 40,
    "businesses.has_aov_gap_gt_5pct": 215,
    "businesses.has_ads_without_orders": 501,
    "businesses.has_tool_not_nested": 168,
    "market_categories.is_residual_category": 2,
    "market_categories.is_all_goods_label": 1,
    "buyers_demo.is_age_unknown": 3,
    "buyers_region.is_unspecified_region": 1,
    "buyers_region.is_market_suppressed": 4,
    "buyers_demo.is_market_suppressed": 2,
}


def build_processed() -> int:
    businesses = _read(INTERIM_DIR / "businesses.parquet")
    categories = _read(INTERIM_DIR / "market_categories.parquet")
    demo = _read(INTERIM_DIR / "buyers_demo.parquet")
    regions = _read(INTERIM_DIR / "buyers_region.parquet")

    business_flags = _business_flags(businesses)
    category_flags = pd.DataFrame(
        {
            "is_residual_category": categories["category"].isin(["Другое", "Не определена"]),
            "is_all_goods_label": categories["category"].eq("Все товары"),
        }
    )
    demo_flags = pd.DataFrame(
        {
            "is_age_unknown": demo["age_band"].eq("н/д"),
            "is_market_suppressed": demo["market_buyers"].isna(),
        }
    )
    region_flags = pd.DataFrame(
        {
            "is_unspecified_region": regions["region"].eq("Не указан"),
            "is_market_suppressed": regions["market_buyers"].isna(),
        }
    )

    counts = _counts("businesses", business_flags)
    counts.update(_counts("market_categories", category_flags))
    counts.update(_counts("buyers_demo", demo_flags))
    counts.update(_counts("buyers_region", region_flags))
    checks = _check_counts(counts)

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    _write_with_flags(INTERIM_DIR / "businesses.parquet", business_flags, PROCESSED_DIR / "businesses.parquet")
    _write_with_flags(INTERIM_DIR / "market_categories.parquet", category_flags, PROCESSED_DIR / "market_categories.parquet")
    _write_with_flags(INTERIM_DIR / "buyers_demo.parquet", demo_flags, PROCESSED_DIR / "buyers_demo.parquet")
    _write_with_flags(INTERIM_DIR / "buyers_region.parquet", region_flags, PROCESSED_DIR / "buyers_region.parquet")
    _write_checks(checks)
    _write_schema()

    failed = checks.loc[checks["status"] == "fail"]
    print(f"flags: {len(checks) - len(failed)} pass, {len(failed)} fail")
    if len(failed):
        print(failed.to_string(index=False))
        return 1
    return 0


def _business_flags(frame: pd.DataFrame) -> pd.DataFrame:
    metric_columns = [column for column in frame.columns if column != "business_id"]
    price = frame["median_item_price_rub"]
    orders = frame["checkout_orders"]
    gmv = frame["checkout_gmv_rub"]
    aov = frame["average_order_value_rub"]
    checkout = frame["checkout_enabled"].astype(bool)
    comparable = orders.gt(0) & gmv.gt(0) & aov.notna()
    calculated = gmv.astype("float64") / orders.astype("float64")
    gap = (aov.astype("float64") - calculated).abs() / calculated
    return pd.DataFrame(
        {
            "is_exact_metric_clone": frame.duplicated(metric_columns, keep="first"),
            "is_high_post_volume": frame["posts_30d"].ge(1000),
            "is_high_product_post_volume": frame["product_posts_30d"].ge(1000),
            "is_extreme_catalog": frame["goods_loaded"].ge(10000),
            "is_extreme_ad_spend": frame["ad_spend_rub"].ge(1_000_000),
            "is_price_floor_1": price.eq(1).fillna(False),
            "is_price_zero": price.eq(0).fillna(False),
            "is_price_cap_1060000": price.eq(1_060_000).fillna(False),
            "is_low_activity": frame["posts_30d"].eq(0) & frame["clips_30d"].eq(0),
            "is_hard_zero": (
                frame["posts_30d"].eq(0)
                & frame["clips_30d"].eq(0)
                & frame["regular_content_views"].eq(0)
                & frame["goods_loaded"].eq(0)
                & frame["active_services"].eq(0)
                & orders.eq(0)
                & frame["ad_spend_rub"].eq(0)
            ),
            "has_orders": orders.gt(0),
            "has_orders_without_checkout": orders.gt(0) & ~checkout,
            "has_orders_with_zero_gmv": orders.gt(0) & gmv.eq(0),
            "has_checkout_without_loaded_goods": checkout & frame["goods_loaded"].eq(0),
            "has_loaded_without_active": frame["goods_loaded"].gt(0) & frame["active_goods"].eq(0),
            "has_type_catalog_mismatch": (
                (frame["business_type"].isin(["без каталога", "услужное"]) & frame["goods_loaded"].gt(0))
                | (frame["business_type"].eq("товарное") & frame["goods_loaded"].eq(0))
            ),
            "has_service_type_without_services": frame["business_type"].eq("услужное") & frame["active_services"].eq(0),
            "has_product_posts_above_posts": frame["product_posts_30d"].gt(frame["posts_30d"]),
            "has_engagement_above_views": (
                frame["regular_content_likes"].gt(frame["regular_content_views"])
                | frame["regular_content_reposts"].gt(frame["regular_content_views"])
                | frame["product_content_likes"].gt(frame["product_content_views"])
                | frame["product_content_reposts"].gt(frame["product_content_views"])
            ),
            "has_opens_without_product_views": frame["product_card_opens_from_content"].gt(0) & frame["product_content_views"].eq(0),
            "has_aov_gap_gt_5pct": comparable & gap.gt(0.05),
            "has_ads_without_orders": frame["ad_spend_rub"].gt(0) & orders.eq(0),
            "has_tool_not_nested": (frame["delivery_enabled"].astype(bool) | frame["payment_enabled"].astype(bool)) & ~checkout,
        }
    )


def _counts(table: str, flags: pd.DataFrame) -> dict[str, int]:
    return {f"{table}.{column}": int(flags[column].fillna(False).sum()) for column in flags.columns}


def _check_counts(counts: dict[str, int]) -> pd.DataFrame:
    rows = []
    seen = set()
    for key, expected in EXPECTED_COUNTS.items():
        actual = counts.get(key)
        seen.add(key)
        rows.append(
            {
                "check_id": key,
                "actual": actual,
                "expected": expected,
                "status": "pass" if actual == expected else "fail",
            }
        )
    for key, actual in counts.items():
        if key not in seen:
            rows.append({"check_id": key, "actual": actual, "expected": None, "status": "fail"})
    return pd.DataFrame(rows)


def _write_with_flags(source, flags: pd.DataFrame, target) -> None:
    table = pq.read_table(source)
    if table.num_rows != len(flags):
        raise SystemExit(f"{source.name}: {table.num_rows} строк против {len(flags)} флагов")
    arrays = list(table.columns)
    fields = list(table.schema)
    for name in flags.columns:
        values = [bool(item) for item in flags[name].fillna(False).tolist()]
        arrays.append(pa.array(values, type=pa.bool_()))
        fields.append(pa.field(name, pa.bool_(), nullable=False))
    pq.write_table(pa.Table.from_arrays(arrays, schema=pa.schema(fields)), target, compression="zstd")


def _write_checks(checks: pd.DataFrame) -> None:
    schema = pa.schema(
        [
            pa.field("check_id", pa.string(), nullable=False),
            pa.field("actual", pa.int64(), nullable=True),
            pa.field("expected", pa.int64(), nullable=True),
            pa.field("status", pa.string(), nullable=False),
        ]
    )
    table = pa.Table.from_pandas(checks, schema=schema, preserve_index=False)
    pq.write_table(table, PROCESSED_DIR / "flag_checks.parquet", compression="zstd")


def _write_schema() -> None:
    document = {
        "version": 1,
        "built_from": "data/interim",
        "row_policy": "Строки interim сохраняются полностью. Флаг не удаляет и не меняет значения.",
        "tables": {
            "businesses": _flagged_table(
                "Копия data/interim/businesses.parquet плюс флаги качества.",
                9754,
                ["business_id"],
                BUSINESS_FLAGS,
            ),
            "market_categories": _flagged_table(
                "Копия data/interim/market_categories.parquet плюс метки категорий.",
                18,
                ["category"],
                CATEGORY_FLAGS,
            ),
            "buyers_demo": _flagged_table(
                "Копия data/interim/buyers_demo.parquet плюс метки возраста и подавления.",
                15,
                ["gender", "age_band"],
                DEMO_FLAGS,
            ),
            "buyers_region": _flagged_table(
                "Копия data/interim/buyers_region.parquet плюс метки региона и подавления.",
                89,
                ["region"],
                REGION_FLAGS,
            ),
            "flag_checks": {
                "grain": "Одна проверка числа строк с флагом.",
                "rows": len(EXPECTED_COUNTS),
                "primary_key": ["check_id"],
                "columns": [
                    {"name": "check_id", "dtype": "string", "nullable": False},
                    {"name": "actual", "dtype": "int64", "nullable": True},
                    {"name": "expected", "dtype": "int64", "nullable": True},
                    {"name": "status", "dtype": "string", "nullable": False},
                ],
            },
        },
    }
    PROCESSED_SCHEMA_PATH.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def _flagged_table(grain: str, rows: int, primary_key: list[str], flags: list[tuple[str, str]]) -> dict:
    return {
        "grain": grain,
        "rows": rows,
        "primary_key": primary_key,
        "value_columns": "Совпадают с одноимённой таблицей data/interim и идут перед флагами.",
        "flags": [{"name": name, "dtype": "bool", "nullable": False, "rule": rule} for name, rule in flags],
    }


def _read(path) -> pd.DataFrame:
    def mapper(dtype):
        if pa.types.is_integer(dtype):
            return pd.Int64Dtype()
        if pa.types.is_boolean(dtype):
            return pd.BooleanDtype()
        return None

    return pq.read_table(path).to_pandas(types_mapper=mapper)
