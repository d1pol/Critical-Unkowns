"""Filtering helpers for case metadata and taxonomy tags."""

from __future__ import annotations

import pandas as pd

from .normalise import filter_cases_by_tags


def _filter_in(df: pd.DataFrame, column: str, values: list[object] | set[object] | tuple[object, ...]) -> pd.DataFrame:
    """Filter a dataframe to rows where column is one of values."""
    if column not in df.columns:
        raise ValueError(f"{column!r} is not present in the dataframe")
    selected = {str(value) for value in values}
    return df[df[column].astype(str).isin(selected)].copy()


def filter_cases(
    df: pd.DataFrame,
    agency: list[str] | set[str] | tuple[str, ...] | None = None,
    years: list[int] | set[int] | tuple[int, ...] | None = None,
    institution_types: list[str] | set[str] | tuple[str, ...] | None = None,
    selected_tags: dict[str, list[str] | set[str] | tuple[str, ...]] | None = None,
    tag_match: str = "any",
) -> pd.DataFrame:
    """Filter cases by common metadata fields and taxonomy tag selections."""
    result = df.copy()

    if agency:
        result = _filter_in(result, "Agency", agency)
    if years:
        result = _filter_in(result, "Year", years)
    if institution_types:
        result = _filter_in(result, "Institution Type", institution_types)
    if selected_tags:
        result = filter_cases_by_tags(result, selected_tags, match=tag_match)

    return result

