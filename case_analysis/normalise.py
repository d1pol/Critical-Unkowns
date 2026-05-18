"""Helpers for parsing and normalising multi-tag taxonomy columns."""

from __future__ import annotations

import pandas as pd

from .taxonomy import TAXONOMY_COLUMNS, get_label


def split_pipe_tags(value: object) -> list[str]:
    """Split a pipe-separated tag cell into clean tag codes."""
    if pd.isna(value):
        return []
    return [tag.strip() for tag in str(value).split("|") if tag.strip()]


def add_tag_list_columns(
    df: pd.DataFrame,
    taxonomy_columns: list[str] | None = None,
    suffix: str = " Tags",
) -> pd.DataFrame:
    """Return a copy of df with parsed list columns for each taxonomy field."""
    result = df.copy()
    for column in taxonomy_columns or TAXONOMY_COLUMNS:
        if column in result.columns:
            result[f"{column}{suffix}"] = result[column].apply(split_pipe_tags)
    return result


def normalise_tags_long(
    df: pd.DataFrame,
    taxonomy_columns: list[str] | None = None,
    id_column: str = "Case ID",
) -> pd.DataFrame:
    """Convert multi-tag taxonomy columns into one row per case/tag.

    Output columns:
    - Case ID
    - Taxonomy Field
    - Tag Code
    - Tag Label
    """
    rows: list[dict[str, object]] = []
    columns = taxonomy_columns or TAXONOMY_COLUMNS

    for _, case in df.iterrows():
        case_id = case[id_column]
        for column in columns:
            if column not in df.columns:
                continue
            for tag in split_pipe_tags(case[column]):
                rows.append(
                    {
                        id_column: case_id,
                        "Taxonomy Field": column,
                        "Tag Code": tag,
                        "Tag Label": get_label(column, tag),
                    }
                )

    return pd.DataFrame(
        rows,
        columns=[id_column, "Taxonomy Field", "Tag Code", "Tag Label"],
    )


def filter_cases_by_tags(
    df: pd.DataFrame,
    selected_tags: dict[str, list[str] | set[str] | tuple[str, ...]],
    match: str = "any",
    taxonomy_columns: list[str] | None = None,
) -> pd.DataFrame:
    """Filter cases by selected taxonomy tag codes.

    Args:
        df: Case dataframe.
        selected_tags: Mapping of taxonomy column name to selected tag codes.
        match: "any" returns cases matching at least one selected field. "all"
            returns cases matching every selected field.
        taxonomy_columns: Optional whitelist of taxonomy fields.
    """
    if match not in {"any", "all"}:
        raise ValueError("match must be either 'any' or 'all'")

    allowed_columns = set(taxonomy_columns or TAXONOMY_COLUMNS)
    masks = []

    for column, codes in selected_tags.items():
        if column not in allowed_columns:
            raise ValueError(f"{column!r} is not a recognised taxonomy field")
        if column not in df.columns:
            raise ValueError(f"{column!r} is not present in the dataframe")

        code_set = {str(code).strip() for code in codes if str(code).strip()}
        if not code_set:
            continue

        masks.append(df[column].apply(lambda value: bool(set(split_pipe_tags(value)) & code_set)))

    if not masks:
        return df.copy()

    combined = masks[0]
    for mask in masks[1:]:
        combined = combined & mask if match == "all" else combined | mask

    return df[combined].copy()


def collect_observed_codes(
    df: pd.DataFrame,
    taxonomy_columns: list[str] | None = None,
) -> dict[str, set[str]]:
    """Return all observed tag codes by taxonomy column."""
    observed: dict[str, set[str]] = {}
    for column in taxonomy_columns or TAXONOMY_COLUMNS:
        if column in df.columns:
            codes: set[str] = set()
            df[column].apply(lambda value: codes.update(split_pipe_tags(value)))
            observed[column] = codes
    return observed


def summary_counts(
    df: pd.DataFrame,
    column: str,
    normalise_taxonomy: bool = True,
) -> pd.DataFrame:
    """Produce count summaries for ordinary columns or pipe-separated tags."""
    if column not in df.columns:
        raise ValueError(f"{column!r} is not present in the dataframe")

    if normalise_taxonomy and column in TAXONOMY_COLUMNS:
        tag_rows = []
        for tags in df[column].apply(split_pipe_tags):
            tag_rows.extend(tags)
        counts = pd.Series(tag_rows, dtype="string").value_counts(dropna=False)
    else:
        counts = df[column].value_counts(dropna=False)

    return counts.rename_axis(column).reset_index(name="Case Count")

