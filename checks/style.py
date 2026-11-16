from pathlib import Path

import matplotlib.pyplot as plt

INK = "#243040"
BLUE = "#3D5A80"
GRAY = "#C5CDD6"
AMBER = "#C47B3A"

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.unicode_minus": False,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": "#D0D5DC",
        "text.color": INK,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
    }
)


def folder(hid: str) -> Path:
    path = Path(__file__).resolve().parent / hid
    path.mkdir(parents=True, exist_ok=True)
    return path


def _ax(ax, title, ylabel):
    ax.set_title(title, loc="left", color=INK, pad=8, fontsize=11)
    if ylabel:
        ax.set_ylabel(ylabel, fontsize=9)
    ax.tick_params(length=0, labelsize=8)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


def _headroom(ax, values):
    clean = [value for value in values if value is not None and value == value and abs(value) != float("inf")]
    if not clean:
        ax.set_ylim(0, 1)
        return
    low = min(0, min(clean))
    high = max(0, max(clean))
    span = high - low or 1
    pad = span * 0.18
    ax.set_ylim(low - (pad if low < 0 else 0), high + pad)


def save(fig, path):
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def bars(labels, values, title, ylabel, path, fmt="{:.0f}", color=BLUE):
    fig, ax = plt.subplots(figsize=(7.2, 3.6))
    drawn = ax.bar(labels, values, color=color, width=0.68)
    _ax(ax, title, ylabel)
    _headroom(ax, values)
    for bar, value in zip(drawn, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            fmt.format(value),
            ha="center",
            va="bottom" if value >= 0 else "top",
            fontsize=8,
            color=INK,
        )
    save(fig, path)


def hbars(labels, values, title, xlabel, path, fmt="{:.0f}", color=BLUE):
    fig, ax = plt.subplots(figsize=(6.4, max(3.2, 0.38 * len(labels) + 1.2)))
    drawn = ax.barh(labels, values, color=color, height=0.68)
    _ax(ax, title, None)
    ax.set_xlabel(xlabel, fontsize=9)
    top = max(values) if values else 1
    ax.set_xlim(0, top * 1.18 if top > 0 else 1)
    for bar, value in zip(drawn, values):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            "  " + fmt.format(value),
            ha="left",
            va="center",
            fontsize=8,
            color=INK,
        )
    save(fig, path)


def grouped_h(labels, series, title, xlabel, path, fmt="{:.1f}"):
    import numpy as np

    fig, ax = plt.subplots(figsize=(6.8, max(3.4, 0.55 * len(labels) + 1.1)))
    names = list(series)
    height = 0.72 / max(len(names), 1)
    y = np.arange(len(labels))
    colors = [BLUE, AMBER, GRAY]
    flat = []
    for i, name in enumerate(names):
        vals = series[name]
        flat.extend(vals)
        shift = (i - (len(names) - 1) / 2) * height
        drawn = ax.barh(y + shift, vals, height=height * 0.9, color=colors[i % 3], label=name)
        for bar, value in zip(drawn, vals):
            ax.text(
                bar.get_width(),
                bar.get_y() + bar.get_height() / 2,
                "  " + fmt.format(value),
                ha="left",
                va="center",
                fontsize=7,
                color=INK,
            )
    ax.set_yticks(y, labels)
    _ax(ax, title, None)
    ax.set_xlabel(xlabel, fontsize=9)
    top = max(flat) if flat else 1
    ax.set_xlim(0, top * 1.2 if top > 0 else 1)
    if len(names) > 1:
        ax.legend(frameon=False, fontsize=8)
    save(fig, path)


def scatter(x, y, title, xlabel, ylabel, path):
    fig, ax = plt.subplots(figsize=(6.2, 4.2))
    ax.scatter(x, y, s=10, c=BLUE, alpha=0.35, linewidths=0)
    _ax(ax, title, ylabel)
    ax.set_xlabel(xlabel, fontsize=9)
    save(fig, path)


def hist_pair(series, titles, xlabel, path):
    import numpy as np

    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6))
    for ax, values, title in zip(axes, series, titles):
        vals = np.asarray(values, dtype=float)
        vals = vals[np.isfinite(vals)]
        cap = np.quantile(vals, 0.99) if len(vals) else 1
        shown = vals[vals <= cap]
        ax.hist(shown, bins=28, color=BLUE)
        ax.axvline(np.median(vals), color=AMBER, lw=1)
        _ax(ax, title, "rows")
        ax.set_xlabel(xlabel, fontsize=9)
    save(fig, path)


def scatter_pair(pairs, titles, xlabel, ylabel, path):
    fig, axes = plt.subplots(1, 2, figsize=(7.6, 3.6))
    for ax, (x, y), title in zip(axes, pairs, titles):
        ax.scatter(x, y, s=10, c=BLUE, alpha=0.4, linewidths=0)
        ax.axhline(0, color=GRAY, lw=0.8)
        ax.axvline(0, color=GRAY, lw=0.8)
        _ax(ax, title, ylabel)
        ax.set_xlabel(xlabel, fontsize=9)
    save(fig, path)


def grouped(labels, series, title, ylabel, path, fmt="{:.1f}"):
    import numpy as np

    fig, ax = plt.subplots(figsize=(6.6, 3.6))
    names = list(series)
    width = 0.72 / max(len(names), 1)
    x = np.arange(len(labels))
    colors = [BLUE, AMBER, GRAY]
    flat = []
    for i, name in enumerate(names):
        vals = series[name]
        flat.extend(vals)
        shift = (i - (len(names) - 1) / 2) * width
        drawn = ax.bar(x + shift, vals, width=width * 0.92, color=colors[i % 3], label=name)
        for bar, value in zip(drawn, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                fmt.format(value),
                ha="center",
                va="bottom",
                fontsize=7,
                color=INK,
            )
    ax.set_xticks(x, labels)
    _ax(ax, title, ylabel)
    _headroom(ax, flat)
    if len(names) > 1:
        ax.legend(frameon=False, fontsize=8)
    save(fig, path)
