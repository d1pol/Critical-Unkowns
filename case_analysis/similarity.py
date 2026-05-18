"""Similarity scoring for enforcement cases based on taxonomy overlap."""

from __future__ import annotations

import pandas as pd

from .normalise import split_pipe_tags


TAG_WEIGHTS = {
    "Regulatory Domain": 3,
    "Failure Type": 3,
    "Root Cause Driver": 2,
    "Failure Mechanism": 2,
    "Lifecycle Stage": 1,
    "Outcome Severity": 1,
    "Punishment": 1,
}


def _tag_set(row: pd.Series, column: str) -> set[str]:
    return set(split_pipe_tags(row.get(column)))


def score_case_similarity(
    source_case: pd.Series,
    candidate_case: pd.Series,
    weights: dict[str, int] | None = None,
) -> tuple[int, dict[str, list[str]]]:
    """Score two cases by weighted overlap across taxonomy fields."""
    score = 0
    overlaps: dict[str, list[str]] = {}

    for column, weight in (weights or TAG_WEIGHTS).items():
        shared = sorted(_tag_set(source_case, column) & _tag_set(candidate_case, column))
        if shared:
            overlaps[column] = shared
            score += len(shared) * weight

    return score, overlaps


def find_similar_cases(
    df: pd.DataFrame,
    case_id: str,
    top_n: int = 10,
    id_column: str = "Case ID",
    weights: dict[str, int] | None = None,
) -> pd.DataFrame:
    """Find cases most similar to the selected case by weighted tag overlap."""
    matches = df[df[id_column].astype(str) == str(case_id)]
    if matches.empty:
        raise ValueError(f"No case found with {id_column}={case_id!r}")

    source_case = matches.iloc[0]
    rows: list[dict[str, object]] = []

    for _, candidate in df.iterrows():
        if str(candidate[id_column]) == str(case_id):
            continue

        score, overlaps = score_case_similarity(source_case, candidate, weights=weights)
        if score <= 0:
            continue

        rows.append(
            {
                id_column: candidate[id_column],
                "Case Name": candidate.get("Case Name"),
                "Agency": candidate.get("Agency"),
                "Year": candidate.get("Year"),
                "Similarity Score": score,
                "Shared Tags": overlaps,
            }
        )

    similar = pd.DataFrame(rows)
    if similar.empty:
        return pd.DataFrame(
            columns=[
                id_column,
                "Case Name",
                "Agency",
                "Year",
                "Similarity Score",
                "Shared Tags",
            ]
        )

    return (
        similar.sort_values(
            by=["Similarity Score", "Year", "Case Name"],
            ascending=[False, False, True],
            na_position="last",
        )
        .head(top_n)
        .reset_index(drop=True)
    )

