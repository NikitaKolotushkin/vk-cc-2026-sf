"""Сырой xlsx → типизированные таблицы data/interim.

Строки не удаляются и не исправляются. Пустой Маркет в разрезах не
заполняется нулём. Прочерк U+2014 становится пустым значением с причиной
not_applicable. Контур сообществ и контур Маркета не соединяются.
"""

from __future__ import annotations

import math

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import yaml
from openpyxl import load_workbook

from vk_case.paths import EM_DASH, INTERIM_DIR, NOT_APPLICABLE, PERIOD_TEXT, SCHEMA_PATH, raw_workbook
from vk_case.flags import build_processed
from vk_case.reconcile import RECONCILIATION_COLUMNS, run_reconciliation

CONTOUR_MARKET = "market_vk"
CONTOUR_PARTNER = "partner_1"
SECTION_HEADER = "Общие метрики Маркета Вконтакте (без деления на сегменты)"

# Пары, где в книге стоит прочерк, а не число и не пустая ячейка.
DASH_CELLS = {
    ("direct_partner_transitions", CONTOUR_MARKET),
    ("paid_orders", CONTOUR_PARTNER),
}

CONTOUR_METRICS = [
    ("impressions", "count", "Показы товаров"),
    ("card_opens", "count", "Открытия карточки товара"),
    ("card_button_clicks", "count", "Нажатия на кнопку в карточке"),
    ("direct_partner_transitions", "count", "Прямые переходы к Партнёру 1 (без открытия карточки)"),
    ("placed_orders", "count", "Оформленные заказы"),
    ("paid_orders", "count", "Оплаченные заказы"),
    ("gmv_rub", "rub", "GMV, ₽"),
    ("average_order_value_rub", "rub", "Средний чек, ₽"),
    ("unique_buyers_30d", "count", "Уникальные покупатели за 30 дней"),
    ("orders_per_buyer", "ratio", "Заказов на покупателя"),
    ("repeat_buyers_share_pct", "pct", "Доля повторных покупателей (2+ заказа), %"),
    ("impression_to_card_open_pct", "pct", "Конверсия: показ → открытие карточки, %"),
    ("card_open_to_order_pct", "pct", "Конверсия: открытие карточки → заказ, %"),
    ("impression_to_order_pct", "pct", "Конверсия: показ → заказ, %"),
    (
        "buyers_on_breakdown_sheets",
        "count",
        "Покупатели на листах «Покупатели» и «Покупатели по регионам» (без групп меньше 100)",
    ),
    (
        "orders_on_breakdown_sheets",
        "count",
        "Заказы на листах «Покупатели» и «Покупатели по регионам» (без групп меньше 100)",
    ),
]

PLATFORM_METRICS = [
    ("period", "date_range", "Период", False),
    ("market_dau_avg", "count", "DAU Маркета Вконтакте (среднее за день)", False),
    ("market_mau", "count", "MAU Маркета Вконтакте (уникальные за 30 дней)", False),
    ("users_saw_goods_30d", "count", "Пользователи, видевшие товары за 30 дней", False),
    ("users_opened_card_30d", "count", "Пользователи, открывавшие карточку товара за 30 дней", False),
    ("card_opens_from_posts_and_clips", "count", "Открытия карточки товара из постов и клипов", False),
    ("card_opens_from_referral_posts_and_clips", "count", "в т.ч. из реферальных постов и клипов", True),
    ("product_search_queries", "count", "Запросы в товарном поиске", False),
    ("product_search_queries_with_card_open_pct", "pct", "Доля поисковых запросов с открытием карточки, %", False),
]

BUSINESS_COLUMNS = [
    ("business_id", "ID бизнеса", "int64", False, "id", "Плотный суррогат этой выгрузки, значения 1…N без пропусков."),
    ("theme", "Тематика", "dictionary", False, "category", "42 значения листа, без перевода и без склейки с типом."),
    ("business_type", "Тип бизнеса (товары / услуги)", "dictionary", False, "category", "Четыре значения листа как есть."),
    ("subscribers", "Число подписчиков", "int64", False, "count", "На листе все значения чётные. Значения не выше 100 кратны 12."),
    ("posts_30d", "Посты за 30 дней", "int64", False, "count", None),
    ("clips_30d", "Клипы за 30 дней", "int64", False, "count", None),
    ("product_posts_30d", "Посты с товаром за 30 дней", "int64", False, "count", None),
    ("product_clips_30d", "Клипы с товаром за 30 дней", "int64", False, "count", None),
    ("regular_content_views", "Просмотры обычного контента", "int64", False, "count", "На листе все значения чётные. Колонка не помечена «за 30 дней», в отличие от постов."),
    ("regular_content_likes", "Лайки обычного контента", "int64", False, "count", None),
    ("regular_content_reposts", "Репосты обычного контента", "int64", False, "count", None),
    ("product_content_views", "Просмотры товарного контента", "int64", False, "count", "Отдельная лестница значений. Минимальное положительное значение на листе — 13."),
    ("product_content_likes", "Лайки товарного контента", "int64", False, "count", None),
    ("product_content_reposts", "Репосты товарного контента", "int64", False, "count", None),
    ("product_card_opens_from_content", "Открытия карточки товара из контента", "int64", False, "count", None),
    ("goods_loaded", "Товары загружены", "int64", False, "count", "Ведёт себя как число позиций, не как флаг."),
    ("active_goods", "Число активных товаров в каталоге", "int64", False, "count", None),
    ("checkout_enabled", "Подключён чекаут", "bool", False, "flag", None),
    ("delivery_enabled", "Подключена доставка", "bool", False, "flag", None),
    ("payment_enabled", "Подключена оплата", "bool", False, "flag", None),
    ("original_content_author", "Автор оригинального контента (оценка модели)", "bool", True, "flag", "Пустое значение не равно false."),
    ("referral_program", "Участие в реферальной программе", "bool", False, "flag", None),
    ("checkout_orders", "Заказы через чекаут", "int64", False, "count", None),
    ("checkout_gmv_rub", "GMV через чекаут, ₽", "int64", False, "rub", None),
    ("average_order_value_rub", "Средний чек, ₽", "int64", True, "rub", "Пусто ровно при GMV = 0. На GMV / заказы не заменяется."),
    ("ad_spend_rub", "Траты на рекламу всего, ₽", "int64", False, "rub", None),
    ("active_services", "Число активных услуг", "int64", False, "count", None),
    ("median_item_price_rub", "Медианная цена товара, ₽", "int64", True, "rub", "Заметная доля значений кратна 530. Ноль на листе встречается отдельно от пустоты и сохраняется."),
]

DAILY_COLUMNS = [
    ("date", "Дата", "date", False, "date", None),
    ("market_dau", "DAU Маркета Вконтакте", "int64", False, "count", "Дневной уник. Сумма дней не равна MAU."),
    ("users_saw_goods", "Видели товары (уник.)", "int64", False, "count", "Дневной уник. Сумма дней не равна месячному унику."),
    ("users_opened_card", "Открывали карточку (уник.)", "int64", False, "count", "Дневной уник. Сумма дней не равна месячному унику."),
    ("search_queries", "Поисковые запросы", "int64", False, "count", None),
    ("search_queries_with_card_open", "Поисковые запросы с открытием карточки", "int64", False, "count", None),
    ("market_impressions", "Показы товаров: Маркет Вконтакте", "int64", False, "count", None),
    ("partner_impressions", "Показы товаров: Партнёр 1", "int64", False, "count", None),
    ("market_card_opens", "Открытия карточки: Маркет Вконтакте", "int64", False, "count", None),
    ("partner_card_opens", "Открытия карточки: Партнёр 1", "int64", False, "count", None),
    ("market_card_button_clicks", "Нажатия на кнопку: Маркет Вконтакте", "int64", False, "count", None),
    ("partner_card_button_clicks", "Нажатия на кнопку: Партнёр 1", "int64", False, "count", None),
    ("market_orders", "Заказы: Маркет Вконтакте", "int64", False, "count", None),
    ("partner_orders", "Заказы: Партнёр 1", "int64", False, "count", None),
    ("market_paid_orders", "Оплаченные заказы: Маркет Вконтакте", "int64", False, "count", None),
    ("market_gmv_rub", "GMV, ₽: Маркет Вконтакте", "int64", False, "rub", None),
    ("partner_gmv_rub", "GMV, ₽: Партнёр 1", "int64", False, "rub", None),
    ("market_buyers", "Покупатели: Маркет Вконтакте", "int64", False, "count", "Дневной уник. Сумма дней больше месячного уника."),
    ("partner_buyers", "Покупатели: Партнёр 1", "int64", False, "count", "Дневной уник. Сумма дней больше месячного уника."),
]

DAILY_NON_ADDITIVE = [
    "market_dau",
    "users_saw_goods",
    "users_opened_card",
    "market_buyers",
    "partner_buyers",
]


def main() -> int:
    source = raw_workbook()
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    tables = build_tables(source)
    for name, table in tables.items():
        pq.write_table(table, INTERIM_DIR / f"{name}.parquet", compression="zstd")
    write_schema(source.name, {name: table.num_rows for name, table in tables.items()})
    code = run_reconciliation()
    if code != 0:
        return code
    return build_processed()


def build_tables(source) -> dict[str, pa.Table]:
    excel = pd.ExcelFile(source, engine="openpyxl")
    names = list(excel.sheet_names)
    return {
        "businesses": businesses_table(pd.read_excel(excel, sheet_name=_sheet(names, "Бизнесы"))),
        "market_contour_metrics": contour_table(source, _sheet(names, "итоги")),
        "market_platform_metrics": platform_table(source, _sheet(names, "итоги")),
        "market_daily": daily_table(pd.read_excel(excel, sheet_name=_sheet(names, "по дням"))),
        "market_sources": sources_table(pd.read_excel(excel, sheet_name=_sheet(names, "источники"))),
        "market_source_nested": nested_source_table(pd.read_excel(excel, sheet_name=_sheet(names, "источники"))),
        "market_categories": categories_table(pd.read_excel(excel, sheet_name=_sheet(names, "категории"))),
        "buyers_demo": people_table(
            pd.read_excel(excel, sheet_name=_exact(names, "Покупатели")),
            key=("gender", "Пол"),
            second=("age_band", "Возраст"),
            rows=15,
        ),
        "buyers_region": people_table(
            pd.read_excel(excel, sheet_name=_exact(names, "Покупатели по регионам")),
            key=("region", "Регион"),
            second=None,
            rows=89,
        ),
    }


def _sheet(names: list[str], needle: str) -> str:
    hits = [name for name in names if needle in name]
    if len(hits) != 1:
        raise SystemExit(f"Лист по фрагменту {needle!r} найден не один раз: {hits}")
    return hits[0]


def _exact(names: list[str], title: str) -> str:
    hits = [name for name in names if name == title]
    if len(hits) != 1:
        raise SystemExit(f"Лист {title!r} не найден. В книге: {names}")
    return hits[0]


def businesses_table(frame: pd.DataFrame) -> pa.Table:
    expected = [item[1] for item in BUSINESS_COLUMNS]
    if list(frame.columns) != expected:
        raise SystemExit(f"Шапка листа «Бизнесы» не совпала с контрактом:\n{list(frame.columns)}")
    if len(frame) != 9754:
        raise SystemExit(f"На листе «Бизнесы» {len(frame)} строк, в контракте 9754")

    arrays: list[pa.Array] = []
    fields: list[pa.Field] = []
    for name, ru, dtype, nullable, _unit, _note in BUSINESS_COLUMNS:
        series = frame[ru]
        if dtype == "int64" and not nullable:
            arrays.append(_int_array(series, name))
            fields.append(pa.field(name, pa.int64(), nullable=False))
        elif dtype == "int64" and nullable:
            arrays.append(_nullable_int_array(series, name))
            fields.append(pa.field(name, pa.int64(), nullable=True))
        elif dtype == "bool" and not nullable:
            arrays.append(_bool_array(series, name))
            fields.append(pa.field(name, pa.bool_(), nullable=False))
        elif dtype == "bool" and nullable:
            arrays.append(_nullable_bool_array(series, name))
            fields.append(pa.field(name, pa.bool_(), nullable=True))
        elif dtype == "dictionary":
            if series.isna().any():
                raise SystemExit(f"{name} содержит пустые значения")
            arrays.append(pa.array(series.astype(str).tolist(), type=pa.dictionary(pa.int32(), pa.string())))
            fields.append(pa.field(name, pa.dictionary(pa.int32(), pa.string()), nullable=False))
        else:
            raise SystemExit(f"Неизвестный тип колонки {name}")
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def contour_table(source, sheet_name: str) -> pa.Table:
    rows = _totals_rows(source, sheet_name)
    body = rows[1:]
    if len(body) != 26:
        raise SystemExit(f"На листе итогов {len(body)} строк данных, ожидается 26")
    section = body[16]
    if section[0] != SECTION_HEADER or any(cell is not None for cell in section[1:]):
        raise SystemExit(f"Строка-разделитель итогов не на месте: {section}")
    contour_rows = body[:16]
    records_id: list[str] = []
    records_ru: list[str] = []
    records_contour: list[str] = []
    records_int: list[int | None] = []
    records_num: list[float | None] = []
    records_unit: list[str] = []
    records_reason: list[str | None] = []
    for (metric_id, unit, label), row in zip(CONTOUR_METRICS, contour_rows, strict=True):
        if row[0] != label:
            raise SystemExit(f"Метрика итогов {row[0]!r} вместо {label!r}")
        if row[3] is not None:
            raise SystemExit(f"В воронке колонка «Всего» заполнена у {label!r}: {row[3]!r}")
        for contour, cell in ((CONTOUR_MARKET, row[1]), (CONTOUR_PARTNER, row[2])):
            value_int, value_num, reason = _parse_metric_cell(metric_id, contour, unit, cell)
            records_id.append(metric_id)
            records_ru.append(label)
            records_contour.append(contour)
            records_int.append(value_int)
            records_num.append(value_num)
            records_unit.append(unit)
            records_reason.append(reason)
    schema = pa.schema(
        [
            pa.field("metric_id", pa.string(), nullable=False),
            pa.field("metric_ru", pa.string(), nullable=False),
            pa.field("contour", pa.string(), nullable=False),
            pa.field("value_int", pa.int64(), nullable=True),
            pa.field("value_num", pa.float64(), nullable=True),
            pa.field("unit", pa.string(), nullable=False),
            pa.field("null_reason", pa.string(), nullable=True),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array(records_id, type=pa.string()),
            pa.array(records_ru, type=pa.string()),
            pa.array(records_contour, type=pa.string()),
            pa.array(records_int, type=pa.int64()),
            pa.array(records_num, type=pa.float64()),
            pa.array(records_unit, type=pa.string()),
            pa.array(records_reason, type=pa.string()),
        ],
        schema=schema,
    )


def platform_table(source, sheet_name: str) -> pa.Table:
    rows = _totals_rows(source, sheet_name)
    platform_rows = rows[1:][17:]
    if len(platform_rows) != len(PLATFORM_METRICS):
        raise SystemExit(f"Блок общих метрик: {len(platform_rows)} строк")
    ids: list[str] = []
    labels: list[str] = []
    ints: list[int | None] = []
    nums: list[float | None] = []
    texts: list[str | None] = []
    units: list[str] = []
    nested: list[bool] = []
    for (metric_id, unit, label, is_nested), row in zip(PLATFORM_METRICS, platform_rows, strict=True):
        if row[0] != label:
            raise SystemExit(f"Общая метрика {row[0]!r} вместо {label!r}")
        if row[1] is not None or row[2] is not None:
            raise SystemExit(f"У общей метрики {label!r} заполнен контур: {row[1]!r}, {row[2]!r}")
        value_int, value_num, value_text = _parse_platform_cell(metric_id, unit, row[3])
        ids.append(metric_id)
        labels.append(label)
        ints.append(value_int)
        nums.append(value_num)
        texts.append(value_text)
        units.append(unit)
        nested.append(is_nested)
    schema = pa.schema(
        [
            pa.field("metric_id", pa.string(), nullable=False),
            pa.field("metric_ru", pa.string(), nullable=False),
            pa.field("value_int", pa.int64(), nullable=True),
            pa.field("value_num", pa.float64(), nullable=True),
            pa.field("value_text", pa.string(), nullable=True),
            pa.field("unit", pa.string(), nullable=False),
            pa.field("is_nested", pa.bool_(), nullable=False),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array(ids, type=pa.string()),
            pa.array(labels, type=pa.string()),
            pa.array(ints, type=pa.int64()),
            pa.array(nums, type=pa.float64()),
            pa.array(texts, type=pa.string()),
            pa.array(units, type=pa.string()),
            pa.array(nested, type=pa.bool_()),
        ],
        schema=schema,
    )


def daily_table(frame: pd.DataFrame) -> pa.Table:
    expected = [item[1] for item in DAILY_COLUMNS]
    if list(frame.columns) != expected:
        raise SystemExit(f"Шапка листа «по дням» не совпала:\n{list(frame.columns)}")
    if len(frame) != 30:
        raise SystemExit(f"На листе «по дням» {len(frame)} строк, ожидается 30")
    dates = pd.to_datetime(frame["Дата"])
    if dates.dt.tz is not None:
        raise SystemExit("Даты дневного листа содержат таймзону")
    if not ((dates.dt.hour == 0) & (dates.dt.minute == 0) & (dates.dt.second == 0)).all():
        raise SystemExit("На дневном листе есть время не полночь")
    expected_days = pd.date_range("2026-09-01", "2026-09-30", freq="D")
    if not dates.reset_index(drop=True).equals(pd.Series(expected_days)):
        raise SystemExit("Дневной ряд не равен 1–30 сентября 2026 без пропусков")
    arrays: list[pa.Array] = []
    fields: list[pa.Field] = []
    for name, ru, dtype, _nullable, _unit, _note in DAILY_COLUMNS:
        if dtype == "date":
            arrays.append(pa.array(dates.dt.date.tolist(), type=pa.date32()))
            fields.append(pa.field(name, pa.date32(), nullable=False))
        else:
            arrays.append(_int_array(frame[ru], name))
            fields.append(pa.field(name, pa.int64(), nullable=False))
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def sources_table(frame: pd.DataFrame) -> pa.Table:
    _require_source_header(frame)
    if len(frame) != 7:
        raise SystemExit(f"На листе источников {len(frame)} строк, ожидается 7")
    main = frame.iloc[:6]
    nested_label = str(frame.iloc[6]["Источник"])
    if not nested_label.startswith("в т.ч."):
        raise SystemExit(f"Последняя строка источников не вложенная: {nested_label!r}")
    schema = pa.schema(
        [
            pa.field("source", pa.string(), nullable=False),
            pa.field("market_card_opens", pa.int64(), nullable=False),
            pa.field("market_share_pct", pa.float64(), nullable=False),
            pa.field("partner_card_opens", pa.int64(), nullable=False),
            pa.field("partner_share_pct", pa.float64(), nullable=False),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array(main["Источник"].astype(str).tolist(), type=pa.string()),
            _int_array(main["Маркет Вконтакте"], "market_card_opens"),
            pa.array(main["Доля, %: Маркет Вконтакте"].astype(float).tolist(), type=pa.float64()),
            _int_array(main["Партнёр 1"], "partner_card_opens"),
            pa.array(main["Доля, %: Партнёр 1"].astype(float).tolist(), type=pa.float64()),
        ],
        schema=schema,
    )


def nested_source_table(frame: pd.DataFrame) -> pa.Table:
    _require_source_header(frame)
    row = frame.iloc[6]
    if pd.notna(row["Маркет Вконтакте"]) or pd.notna(row["Доля, %: Маркет Вконтакте"]):
        raise SystemExit("У вложенной строки источников заполнен Маркет")
    schema = pa.schema(
        [
            pa.field("source", pa.string(), nullable=False),
            pa.field("partner_card_opens", pa.int64(), nullable=False),
            pa.field("partner_share_pct", pa.float64(), nullable=False),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array([str(row["Источник"])], type=pa.string()),
            _int_array(pd.Series([row["Партнёр 1"]]), "nested_partner_card_opens"),
            pa.array([float(row["Доля, %: Партнёр 1"])], type=pa.float64()),
        ],
        schema=schema,
    )


def categories_table(frame: pd.DataFrame) -> pa.Table:
    expected = [
        "Категория",
        "Открытия карточки: Маркет Вконтакте",
        "Заказы: Маркет Вконтакте",
        "Открытия карточки: Партнёр 1",
        "Заказы: Партнёр 1",
    ]
    if list(frame.columns) != expected:
        raise SystemExit(f"Шапка категорий не совпала: {list(frame.columns)}")
    if len(frame) != 18 or frame["Категория"].duplicated().any():
        raise SystemExit(f"Категорий {len(frame)}, дублей {int(frame['Категория'].duplicated().sum())}")
    schema = pa.schema(
        [
            pa.field("category", pa.string(), nullable=False),
            pa.field("market_card_opens", pa.int64(), nullable=False),
            pa.field("market_orders", pa.int64(), nullable=False),
            pa.field("partner_card_opens", pa.int64(), nullable=False),
            pa.field("partner_orders", pa.int64(), nullable=False),
        ]
    )
    return pa.Table.from_arrays(
        [
            pa.array(frame["Категория"].astype(str).tolist(), type=pa.string()),
            _int_array(frame[expected[1]], "market_card_opens"),
            _int_array(frame[expected[2]], "market_orders"),
            _int_array(frame[expected[3]], "partner_card_opens"),
            _int_array(frame[expected[4]], "partner_orders"),
        ],
        schema=schema,
    )


def people_table(frame: pd.DataFrame, key: tuple[str, str], second: tuple[str, str] | None, rows: int) -> pa.Table:
    metrics = [
        "Покупатели: Маркет Вконтакте",
        "Заказы: Маркет Вконтакте",
        "Покупатели: Партнёр 1",
        "Заказы: Партнёр 1",
    ]
    expected = [key[1]] + ([second[1]] if second else []) + metrics
    if list(frame.columns) != expected:
        raise SystemExit(f"Шапка разреза {key[1]!r} не совпала: {list(frame.columns)}")
    if len(frame) != rows:
        raise SystemExit(f"В разрезе {key[1]!r} {len(frame)} строк, ожидается {rows}")
    fields = [pa.field(key[0], pa.string(), nullable=False)]
    arrays: list[pa.Array] = [pa.array(frame[key[1]].astype(str).tolist(), type=pa.string())]
    if second:
        fields.append(pa.field(second[0], pa.string(), nullable=False))
        arrays.append(pa.array(frame[second[1]].astype(str).tolist(), type=pa.string()))
    nullable_metrics = {
        "market_buyers": metrics[0],
        "market_orders": metrics[1],
    }
    required_metrics = {
        "partner_buyers": metrics[2],
        "partner_orders": metrics[3],
    }
    for name, ru in nullable_metrics.items():
        fields.append(pa.field(name, pa.int64(), nullable=True))
        arrays.append(_nullable_int_array(frame[ru], name))
    for name, ru in required_metrics.items():
        fields.append(pa.field(name, pa.int64(), nullable=False))
        arrays.append(_int_array(frame[ru], name))
    return pa.Table.from_arrays(arrays, schema=pa.schema(fields))


def write_schema(source_name: str, row_counts: dict[str, int]) -> None:
    document = {
        "version": 1,
        "source_file": f"data/raw/{source_name}",
        "storage": "parquet",
        "joins": {"businesses_to_market": "none"},
        "null_policy": {
            "excel_em_dash": "Пустое значение и null_reason = not_applicable. Ноль не подставляется.",
            "suppressed_breakdown": "Пустое значение без причины. Это скрытая малая группа, не ноль.",
            "author_blank": "Пустой автор остаётся пустым и не читается как false.",
            "percents": "Шкала 0…100, как в файле. Отдельной колонки 0…1 нет.",
        },
        "tables": {
            "businesses": _table_doc(
                grain="Одно сообщество. Окно листа помечено как 30 дней и календарём с Маркетом не связано.",
                rows=row_counts["businesses"],
                primary_key=["business_id"],
                columns=_column_docs(BUSINESS_COLUMNS),
            ),
            "market_contour_metrics": {
                "grain": "Одна метрика одного контура за 1–30 сентября 2026. Колонка «Всего» сюда не входит и суммой контуров не является.",
                "rows": row_counts["market_contour_metrics"],
                "primary_key": ["metric_id", "contour"],
                "contours": {
                    CONTOUR_MARKET: "Маркет Вконтакте",
                    CONTOUR_PARTNER: "Партнёр 1",
                },
                "value_columns": "Целые count и rub лежат в value_int. Доли и проценты лежат в value_num. Заполнена ровно одна из двух, кроме строки с null_reason.",
                "columns": [
                    _field("metric_id", "string", False, "id", "Латинский код метрики."),
                    _field("metric_ru", "string", False, "label", "Подпись из листа итогов."),
                    _field("contour", "string", False, "id", "market_vk или partner_1."),
                    _field("value_int", "int64", True, "number", "Целые счетчики и рубли."),
                    _field("value_num", "float64", True, "number", "Отношения и проценты в шкале файла."),
                    _field("unit", "string", False, "unit", "count, rub, ratio или pct."),
                    _field("null_reason", "string", True, "code", "not_applicable только у прочерка."),
                ],
            },
            "market_platform_metrics": {
                "grain": "Скаляр из колонки «Всего» нижнего блока листа итогов. Это не сумма Маркета и Партнёра.",
                "rows": row_counts["market_platform_metrics"],
                "primary_key": ["metric_id"],
                "columns": [
                    _field("metric_id", "string", False, "id", None),
                    _field("metric_ru", "string", False, "label", None),
                    _field("value_int", "int64", True, "count", "Целые скаляры."),
                    _field("value_num", "float64", True, "pct", "Процент в шкале 0…100."),
                    _field("value_text", "string", True, "text", "Период строкой."),
                    _field("unit", "string", False, "unit", "count, pct или date_range."),
                    _field("is_nested", "bool", False, "flag", "true только у «в т.ч. из реферальных постов и клипов». Эту строку не складывают с соседней."),
                ],
            },
            "market_daily": _table_doc(
                grain="Один календарный день, 1–30 сентября 2026. Время отброшено.",
                rows=row_counts["market_daily"],
                primary_key=["date"],
                columns=_column_docs(DAILY_COLUMNS),
                extra={"non_additive": DAILY_NON_ADDITIVE},
            ),
            "market_sources": {
                "grain": "Один источник открытий карточки. Шесть строк составляют полную сумму открытий. Вложенная реферальная строка сюда не входит.",
                "rows": row_counts["market_sources"],
                "primary_key": ["source"],
                "columns": [
                    _field("source", "string", False, "label", "Подпись источника как в файле."),
                    _field("market_card_opens", "int64", False, "count", None),
                    _field("market_share_pct", "float64", False, "pct", "Шкала 0…100."),
                    _field("partner_card_opens", "int64", False, "count", None),
                    _field("partner_share_pct", "float64", False, "pct", "Шкала 0…100."),
                ],
            },
            "market_source_nested": {
                "grain": "Вложенная строка «в т.ч. из реферальных постов и клипов». Не седьмой источник.",
                "rows": row_counts["market_source_nested"],
                "primary_key": ["source"],
                "columns": [
                    _field("source", "string", False, "label", None),
                    _field("partner_card_opens", "int64", False, "count", "Число больше суммы «Клипы + Лента» Партнёра."),
                    _field("partner_share_pct", "float64", False, "pct", "Доля от всех открытий карточки Партнёра, шкала 0…100."),
                ],
            },
            "market_categories": {
                "grain": "Одна товарная категория. «Все товары», «Другое» и «Не определена» сохранены как категории.",
                "rows": row_counts["market_categories"],
                "primary_key": ["category"],
                "columns": [
                    _field("category", "string", False, "label", None),
                    _field("market_card_opens", "int64", False, "count", None),
                    _field("market_orders", "int64", False, "count", "Сумма по категориям не равна оформленным заказам."),
                    _field("partner_card_opens", "int64", False, "count", None),
                    _field("partner_orders", "int64", False, "count", "Сумма по категориям не равна оформленным заказам."),
                ],
            },
            "buyers_demo": _people_doc(
                "Одна ячейка пол × возраст. Пустой Маркет — подавленная группа, не ноль.",
                row_counts["buyers_demo"],
                ["gender", "age_band"],
                [("gender", "Пол"), ("age_band", "Возраст")],
            ),
            "buyers_region": _people_doc(
                "Один регион, включая «Не указан». Пустой Маркет у четырёх регионов — подавление, не ноль.",
                row_counts["buyers_region"],
                ["region"],
                [("region", "Регион")],
            ),
            "reconciliation": {
                "grain": "Одна арифметическая сверка. Расхождение записывается, исходные числа из-за него не правятся.",
                "rows": "по числу проверок",
                "primary_key": ["check_id"],
                "columns": [
                    _field(
                        name,
                        dtype,
                        name in {"lhs_value", "rhs_value", "delta", "expected_delta", "tolerance"},
                        "meta",
                        note,
                    )
                    for name, dtype, note in RECONCILIATION_COLUMNS
                ],
            },
        },
    }
    SCHEMA_PATH.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False, width=100),
        encoding="utf-8",
    )


def _table_doc(grain: str, rows: int, primary_key: list[str], columns: list[dict], extra: dict | None = None) -> dict:
    document = {"grain": grain, "rows": rows, "primary_key": primary_key, "columns": columns}
    if extra:
        document.update(extra)
    return document


def _column_docs(spec: list[tuple]) -> list[dict]:
    return [_field(name, dtype, nullable, unit, note) for name, _ru, dtype, nullable, unit, note in spec]


def _field(name: str, dtype: str, nullable: bool, unit: str, note: str | None) -> dict:
    field = {"name": name, "dtype": dtype, "nullable": nullable, "unit": unit}
    if note:
        field["note"] = note
    return field


def _people_doc(grain: str, rows: int, primary_key: list[str], keys: list[tuple[str, str]]) -> dict:
    columns = [_field(name, "string", False, "label", f"Как в файле: {ru}.") for name, ru in keys]
    columns.extend(
        [
            _field("market_buyers", "int64", True, "count", "Пусто означает подавление малой группы."),
            _field("market_orders", "int64", True, "count", "Пусто в тех же строках, что и market_buyers."),
            _field("partner_buyers", "int64", False, "count", None),
            _field("partner_orders", "int64", False, "count", None),
        ]
    )
    return _table_doc(grain, rows, primary_key, columns)


def _totals_rows(source, sheet_name: str) -> list[tuple]:
    workbook = load_workbook(source, read_only=True, data_only=False)
    try:
        sheet = workbook[sheet_name]
        rows = [tuple(row) for row in sheet.iter_rows(values_only=True)]
    finally:
        workbook.close()
    header = rows[0]
    if header[:4] != ("Метрика", "Маркет Вконтакте", "Партнёр 1", "Всего"):
        raise SystemExit(f"Шапка итогов не совпала: {header}")
    return rows


def _parse_metric_cell(metric_id: str, contour: str, unit: str, cell):
    dashed = (metric_id, contour) in DASH_CELLS
    if isinstance(cell, str) and cell.strip() == EM_DASH:
        if not dashed:
            raise SystemExit(f"Неожиданный прочерк у {metric_id}/{contour}")
        return None, None, NOT_APPLICABLE
    if dashed:
        raise SystemExit(f"У {metric_id}/{contour} вместо прочерка стоит {cell!r}")
    if cell is None:
        raise SystemExit(f"Пустая ячейка воронки у {metric_id}/{contour}")
    if unit in {"count", "rub"}:
        return _as_exact_int(cell, f"{metric_id}/{contour}"), None, None
    if unit in {"pct", "ratio"}:
        return None, _as_float(cell, f"{metric_id}/{contour}"), None
    raise SystemExit(f"Неизвестная единица {unit}")


def _parse_platform_cell(metric_id: str, unit: str, cell):
    if unit == "date_range":
        if cell != PERIOD_TEXT:
            raise SystemExit(f"Период {cell!r} не равен {PERIOD_TEXT!r}")
        return None, None, PERIOD_TEXT
    if unit == "count":
        return _as_exact_int(cell, metric_id), None, None
    if unit == "pct":
        return None, _as_float(cell, metric_id), None
    raise SystemExit(f"Неизвестная единица общей метрики {unit}")


def _as_exact_int(cell, label: str) -> int:
    if isinstance(cell, bool) or cell is None:
        raise SystemExit(f"{label}: ожидалось целое, пришло {cell!r}")
    if isinstance(cell, int):
        return cell
    if isinstance(cell, float) and math.isfinite(cell) and cell.is_integer():
        return int(cell)
    raise SystemExit(f"{label}: ожидалось целое, пришло {cell!r}")


def _as_float(cell, label: str) -> float:
    if isinstance(cell, bool) or isinstance(cell, str) or cell is None:
        raise SystemExit(f"{label}: ожидалось число, пришло {cell!r}")
    value = float(cell)
    if not math.isfinite(value):
        raise SystemExit(f"{label}: нечисловое значение {cell!r}")
    return value


def _int_array(series: pd.Series, name: str) -> pa.Array:
    if series.isna().any():
        raise SystemExit(f"{name} содержит пустые значения")
    if pd.api.types.is_float_dtype(series) and ((series % 1) != 0).any():
        raise SystemExit(f"{name} содержит дробные значения")
    values = [int(item) for item in series.tolist()]
    return pa.array(values, type=pa.int64())


def _nullable_int_array(series: pd.Series, name: str) -> pa.Array:
    present = series.dropna()
    if len(present) and pd.api.types.is_float_dtype(present) and ((present % 1) != 0).any():
        raise SystemExit(f"{name} содержит дробные значения")
    values = [None if pd.isna(item) else int(item) for item in series.tolist()]
    return pa.array(values, type=pa.int64())


def _bool_array(series: pd.Series, name: str) -> pa.Array:
    if series.isna().any() or not series.isin([0, 1]).all():
        raise SystemExit(f"{name} выходит за 0/1")
    return pa.array([bool(item) for item in series.tolist()], type=pa.bool_())


def _nullable_bool_array(series: pd.Series, name: str) -> pa.Array:
    present = series.dropna()
    if not present.isin([0, 1, 0.0, 1.0]).all():
        raise SystemExit(f"{name} содержит значения кроме 0, 1 и пустоты")
    mask = [bool(pd.isna(item)) for item in series.tolist()]
    values = [False if pd.isna(item) else bool(int(item)) for item in series.tolist()]
    return pa.array(values, type=pa.bool_(), mask=pa.array(mask))


def _require_source_header(frame: pd.DataFrame) -> None:
    expected = [
        "Источник",
        "Маркет Вконтакте",
        "Доля, %: Маркет Вконтакте",
        "Партнёр 1",
        "Доля, %: Партнёр 1",
    ]
    if list(frame.columns) != expected:
        raise SystemExit(f"Шапка источников не совпала: {list(frame.columns)}")
