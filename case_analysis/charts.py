"""Simple charting helpers for enforcement case analysis."""

from __future__ import annotations

from pathlib import Path
from textwrap import wrap

import pandas as pd

from .normalise import split_pipe_tags, summary_counts
from .taxonomy import TAXONOMY_COLUMNS, get_label

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:  # pragma: no cover - depends on local environment.
    plt = None


def _require_matplotlib() -> None:
    if plt is None:
        raise ModuleNotFoundError(
            "matplotlib is required for chart output. Run: pip install -r requirements.txt"
        )


def save_figure(fig: object, output_path: str | Path) -> Path:
    """Save a matplotlib figure and close it to free resources."""
    _require_matplotlib()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight", dpi=160)
    plt.close(fig)
    return path


def plot_count_bar(
    df: pd.DataFrame,
    column: str,
    top_n: int = 15,
    title: str | None = None,
    normalise_taxonomy: bool = True,
) -> object:
    """Plot a horizontal count bar chart for a metadata or taxonomy column."""
    _require_matplotlib()
    counts = summary_counts(df, column, normalise_taxonomy=normalise_taxonomy).head(top_n)
    labels = [
        get_label(column, value) if column in TAXONOMY_COLUMNS else str(value)
        for value in counts[column]
    ]
    labels = ["\n".join(wrap(label, width=34)) for label in labels]

    fig, ax = plt.subplots(figsize=(9, max(4, len(counts) * 0.42)))
    ax.barh(labels, counts["Case Count"], color="#315f72")
    ax.invert_yaxis()
    ax.set_xlabel("Case count")
    ax.set_ylabel("")
    ax.set_title(title or f"Cases by {column}")
    ax.grid(axis="x", alpha=0.2)

    return fig


def plot_cases_by_year(df: pd.DataFrame, title: str = "Cases by Year") -> object:
    """Plot case counts by year."""
    _require_matplotlib()
    if "Year" not in df.columns:
        raise ValueError("'Year' is not present in the dataframe")

    counts = (
        df.dropna(subset=["Year"])
        .assign(Year=lambda data: data["Year"].astype(int))
        .groupby("Year")
        .size()
        .reset_index(name="Case Count")
        .sort_values("Year")
    )

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(counts["Year"], counts["Case Count"], marker="o", color="#315f72")
    ax.set_xlabel("Year")
    ax.set_ylabel("Case count")
    ax.set_title(title)
    ax.grid(axis="y", alpha=0.2)
    ax.set_xticks(counts["Year"])
    ax.tick_params(axis="x", rotation=45)

    return fig


def categorical_cooccurrence(
    df: pd.DataFrame,
    row_column: str,
    column_column: str,
    top_rows: int = 12,
    top_columns: int = 12,
    normalise: str | None = None,
) -> pd.DataFrame:
    """Build a co-occurrence table between two categorical fields.

    Pipe-separated taxonomy fields are exploded before counting, so a case with
    two regulatory domains and three failure types contributes to each relevant
    pair. Set normalise to "row" or "column" for percentage-style comparisons.
    """
    if row_column not in df.columns:
        raise ValueError(f"{row_column!r} is not present in the dataframe")
    if column_column not in df.columns:
        raise ValueError(f"{column_column!r} is not present in the dataframe")
    if normalise not in {None, "row", "column"}:
        raise ValueError("normalise must be None, 'row', or 'column'")

    rows: list[dict[str, str]] = []
    for _, case in df.iterrows():
        row_values = _values_for_crosstab(case[row_column], row_column)
        column_values = _values_for_crosstab(case[column_column], column_column)
        for row_value in row_values:
            for column_value in column_values:
                rows.append({"row": row_value, "column": column_value})

    if not rows:
        return pd.DataFrame()

    pairs = pd.DataFrame(rows)
    table = pd.crosstab(pairs["row"], pairs["column"])

    row_order = table.sum(axis=1).sort_values(ascending=False).head(top_rows).index
    column_order = table.sum(axis=0).sort_values(ascending=False).head(top_columns).index
    table = table.loc[row_order, column_order]

    if normalise == "row":
        table = table.div(table.sum(axis=1).replace(0, pd.NA), axis=0).fillna(0)
    elif normalise == "column":
        table = table.div(table.sum(axis=0).replace(0, pd.NA), axis=1).fillna(0)

    return table


def plot_cooccurrence_heatmap(
    df: pd.DataFrame,
    row_column: str,
    column_column: str,
    top_rows: int = 12,
    top_columns: int = 12,
    normalise: str | None = None,
    title: str | None = None,
) -> object:
    """Plot a heatmap showing how two categorical fields overlap."""
    _require_matplotlib()
    table = categorical_cooccurrence(
        df,
        row_column=row_column,
        column_column=column_column,
        top_rows=top_rows,
        top_columns=top_columns,
        normalise=normalise,
    )
    if table.empty:
        raise ValueError("No values available to plot")

    fig, ax = plt.subplots(figsize=(max(8, len(table.columns) * 0.85), max(5, len(table) * 0.5)))
    image = ax.imshow(table.to_numpy(), cmap="YlGnBu", aspect="auto")

    ax.set_xticks(range(len(table.columns)))
    ax.set_yticks(range(len(table.index)))
    ax.set_xticklabels(["\n".join(wrap(str(label), width=18)) for label in table.columns])
    ax.set_yticklabels(["\n".join(wrap(str(label), width=26)) for label in table.index])
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_xlabel(column_column)
    ax.set_ylabel(row_column)
    ax.set_title(title or f"{row_column} vs {column_column}")

    for row_idx in range(table.shape[0]):
        for col_idx in range(table.shape[1]):
            value = table.iloc[row_idx, col_idx]
            label = f"{value:.0%}" if normalise else f"{int(value)}"
            ax.text(col_idx, row_idx, label, ha="center", va="center", fontsize=8)

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    fig.tight_layout()
    return fig


def _values_for_crosstab(value: object, column: str) -> list[str]:
    """Return readable categorical values for a crosstab dimension."""
    if column in TAXONOMY_COLUMNS:
        return [get_label(column, tag) for tag in split_pipe_tags(value)]
    if pd.isna(value):
        return []
    text = str(value).strip()
    return [text] if text else []
