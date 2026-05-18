"""Load and validate the enforcement case tracker."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


DEFAULT_DATA_PATH = Path("data/case_database.csv")

# Backwards-compatible alias for older imports. Prefer DEFAULT_DATA_PATH.
DEFAULT_EXCEL_PATH = DEFAULT_DATA_PATH

REQUIRED_COLUMNS = [
    "Case ID",
    "Link",
    "Agency",
    "Case Name",
    "Year",
    "Institution Type",
    "Description",
    "Issue cause",
    "What went wrong",
    "Legal Consequence",
    "Regulatory Domain",
    "Failure Type",
    "Root Cause Driver",
    "Failure Mechanism",
    "Lifecycle Stage",
    "Outcome Severity",
    "Punishment",
]


def validate_required_columns(
    df: pd.DataFrame,
    required_columns: list[str] | None = None,
) -> None:
    """Raise ValueError if the dataframe is missing expected tracker columns."""
    required = required_columns or REQUIRED_COLUMNS
    missing = [column for column in required if column not in df.columns]
    if missing:
        missing_text = ", ".join(missing)
        raise ValueError(f"Missing required column(s): {missing_text}")


def load_cases(
    path: str | Path = DEFAULT_DATA_PATH,
    sheet_name: str | int = 0,
    validate: bool = True,
) -> pd.DataFrame:
    """Load the case tracker CSV or Excel file into a pandas dataframe.

    Text-like fields are kept as strings where possible. The Year column is
    converted to pandas' nullable integer dtype when present.
    """
    data_path = Path(path)
    if not data_path.exists():
        raise FileNotFoundError(
            f"Could not find case tracker at {data_path}. "
            "Place the file at data/case_database.csv or pass a custom path."
        )
    if not data_path.is_file():
        raise IsADirectoryError(
            f"Expected a CSV or Excel file at {data_path}, but found a directory."
        )

    try:
        # Probe the file before pandas reads it so locked/permission errors are
        # reported with a clearer message.
        with data_path.open("rb") as handle:
            handle.read(1)
        df = _read_case_file(data_path, sheet_name=sheet_name)
    except PermissionError as exc:
        raise PermissionError(
            f"Cannot read {data_path}. The file may be open in another app, "
            "locked by OneDrive, or blocked by Windows permissions. Close the file "
            "and try again."
        ) from exc

    if validate:
        validate_required_columns(df)

    for column in df.columns:
        if column != "Year":
            df[column] = df[column].astype("string").str.strip()

    if "Year" in df.columns:
        df["Year"] = pd.to_numeric(df["Year"], errors="coerce").astype("Int64")

    return df


def _read_case_file(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    """Read a supported case database file by extension."""
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig")
    if suffix in {".xlsx", ".xlsm", ".xls"}:
        return pd.read_excel(path, sheet_name=sheet_name)
    raise ValueError(
        f"Unsupported case database file type {suffix!r}. "
        "Use .csv, .xlsx, .xlsm, or .xls."
    )
