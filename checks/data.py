from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
INTERIM = ROOT / "data" / "interim"
PROCESSED = ROOT / "data" / "processed"


def read(path):
    return pd.read_parquet(path)


def businesses():
    return read(PROCESSED / "businesses.parquet")


def f0(frame):
    return frame.loc[~frame["is_exact_metric_clone"].astype(bool)].copy()


def band(subscribers):
    out = pd.Series(index=subscribers.index, dtype="object")
    out.loc[subscribers.eq(0)] = "0"
    out.loc[subscribers.between(1, 12)] = "1–12"
    out.loc[subscribers.between(13, 100)] = "13–100"
    out.loc[subscribers.between(101, 1000)] = "101–1000"
    out.loc[subscribers.gt(1000)] = ">1000"
    return out


def spearman(left, right):
    pair = pd.DataFrame({"l": left, "r": right}).dropna()
    if len(pair) < 3:
        return np.nan
    return pair["l"].rank().corr(pair["r"].rank())


def partial_spearman(x, y, z):
    frame = pd.DataFrame({"x": x, "y": y, "z": z}).dropna()
    if len(frame) < 5:
        return np.nan
    rx, ry, rz = frame["x"].rank(), frame["y"].rank(), frame["z"].rank()
    bx = np.polyfit(rz, rx, 1)
    by = np.polyfit(rz, ry, 1)
    return pd.Series(rx - np.polyval(bx, rz)).corr(pd.Series(ry - np.polyval(by, rz)))


def rate(mask):
    mask = mask.astype(bool)
    if len(mask) == 0:
        return np.nan
    return 100 * float(mask.mean())


def mh_or(frame, exposure, outcome, strata):
    num = 0.0
    den = 0.0
    for _, group in frame.groupby(strata, observed=True):
        exposed = group[exposure].astype(bool)
        hit = group[outcome].astype(bool)
        n = len(group)
        if n == 0:
            continue
        a = int((exposed & hit).sum())
        b = int((exposed & ~hit).sum())
        c = int((~exposed & hit).sum())
        d = int((~exposed & ~hit).sum())
        num += a * d / n
        den += b * c / n
    if den == 0:
        return np.nan
    return num / den


def crude_or(exposed, hit):
    exposed = exposed.astype(bool)
    hit = hit.astype(bool)
    a = int((exposed & hit).sum())
    b = int((exposed & ~hit).sum())
    c = int((~exposed & hit).sum())
    d = int((~exposed & ~hit).sum())
    if b == 0 or c == 0:
        return np.nan
    return (a * d) / (b * c)


def contour():
    return read(INTERIM / "market_contour_metrics.parquet")


def contour_int(frame, metric, name):
    rows = frame.loc[(frame["metric_id"] == metric) & (frame["contour"] == name), "value_int"]
    return int(rows.iloc[0])


def contour_num(frame, metric, name):
    rows = frame.loc[(frame["metric_id"] == metric) & (frame["contour"] == name), "value_num"]
    return float(rows.iloc[0])


def platform_int(metric):
    frame = read(INTERIM / "market_platform_metrics.parquet")
    return int(frame.loc[frame["metric_id"] == metric, "value_int"].iloc[0])
