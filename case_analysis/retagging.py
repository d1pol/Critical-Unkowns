"""Retag root-cause drivers into primary and contributing causes.

This module keeps the original tags intact and adds revised fields. The rules
are deliberately transparent rather than model-based, so the output can be
reviewed and challenged case by case.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import re

import pandas as pd

from .normalise import split_pipe_tags
from .taxonomy import get_label


SOURCE_WORKBOOK = Path("Initial Case Tagging (Macro).xlsm")
OUTPUT_DIR = Path("outputs/retagging")

PRIMARY_COLUMN = "Primary Root Cause Driver"
CONTRIBUTING_COLUMN = "Contributing Root Cause Drivers"
REVISED_COLUMN = "Root Cause Driver Revised"
ORIGINAL_COLUMN = "Root Cause Driver Original"
NOTES_COLUMN = "Retagging Notes"
CONFIDENCE_COLUMN = "Retagging Confidence"

WEAK_RISK = "RC_WEAK_RISK_FRAMEWORK"


EVIDENCE_PATTERNS = {
    "RC_KNOWN_RISK": re.compile(
        r"known|aware|warning|warned|repeated|long-standing|persist|remediat|"
        r"despite|previous|historic|backlog|failed to respond",
        re.I,
    ),
    "RC_DATA_QUALITY": re.compile(
        r"data quality|inaccurate data|incorrect data|flawed data|duplicate|"
        r"incomplete data|data capture|risk assessment data|management information|MI",
        re.I,
    ),
    "RC_SYSTEM_INTEGRATION": re.compile(
        r"system|platform|integration|configuration|misconfiguration|migration|"
        r"logic|calibration|interface|automated",
        re.I,
    ),
    "RC_MANUAL_PROCESS": re.compile(
        r"manual|spreadsheet|workaround|manual process|manual control",
        re.I,
    ),
    "RC_THIRD_PARTY": re.compile(
        r"third[- ]party|outsourc|supplier|vendor|introducer|agent|appointed representative",
        re.I,
    ),
    "RC_CONCENTRATED_CONTROL": re.compile(
        r"sole director|single director|founder|key person|concentrated|"
        r"unilateral|connected entity|individual|senior individual|dominant",
        re.I,
    ),
    "RC_INCENTIVES_CULTURE": re.compile(
        r"incentive|culture|misconduct|deliberate|reckless|dishonest|"
        r"sales pressure|commercial pressure|profit|pricing|remuneration|collusion",
        re.I,
    ),
    "RC_CHANGE_MANAGEMENT": re.compile(
        r"change management|change programme|implementation|transition|migration|"
        r"remediation programme|rollout|introduced|new system",
        re.I,
    ),
    "RC_POOR_DOCUMENTATION": re.compile(
        r"documentation|documented|records?|recordkeeping|audit trail|minutes|evidence",
        re.I,
    ),
    "RC_REG_UNDERSTANDING": re.compile(
        r"regulatory understanding|regulatory obligation|rules?|requirement|"
        r"fees|levies|permission|authorisation|regime|MIFID|MLR|listing rule",
        re.I,
    ),
    WEAK_RISK: re.compile(
        r"risk framework|risk management framework|control framework|governance framework|"
        r"systems and controls|risk-based|enterprise-wide|firm-wide|three lines|"
        r"board oversight|senior management oversight|risk appetite",
        re.I,
    ),
}


ROOT_CAUSE_PRIORITY = [
    "RC_KNOWN_RISK",
    "RC_CONCENTRATED_CONTROL",
    "RC_INCENTIVES_CULTURE",
    "RC_THIRD_PARTY",
    "RC_SYSTEM_INTEGRATION",
    "RC_DATA_QUALITY",
    "RC_CHANGE_MANAGEMENT",
    "RC_MANUAL_PROCESS",
    "RC_POOR_DOCUMENTATION",
    "RC_REG_UNDERSTANDING",
    WEAK_RISK,
]


def retag_mapping_sheet(
    source_path: str | Path = SOURCE_WORKBOOK,
    output_dir: str | Path = OUTPUT_DIR,
) -> dict[str, Path]:
    """Read the Mapping sheet and write revised tagging outputs."""
    source = Path(source_path)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    df = pd.read_excel(source, sheet_name="Mapping")
    revised = apply_root_cause_retagging(df)

    csv_path = output / "case_database_retagged.csv"
    review_path = output / "root_cause_retagging_review.csv"
    summary_path = output / "root_cause_retagging_summary.md"

    revised.to_csv(csv_path, index=False, encoding="utf-8-sig")
    _review_table(revised).to_csv(review_path, index=False, encoding="utf-8-sig")
    summary_path.write_text(_summary_markdown(revised), encoding="utf-8")

    return {
        "retagged_csv": csv_path,
        "review_csv": review_path,
        "summary_markdown": summary_path,
    }


def apply_root_cause_retagging(df: pd.DataFrame) -> pd.DataFrame:
    """Return a dataframe with revised root-cause tagging columns added."""
    result = df.copy()
    result = result.map(_clean_text)
    result[ORIGINAL_COLUMN] = result["Root Cause Driver"]

    retagged_rows = result.apply(_retag_row, axis=1, result_type="expand")
    for column in [
        PRIMARY_COLUMN,
        CONTRIBUTING_COLUMN,
        REVISED_COLUMN,
        CONFIDENCE_COLUMN,
        NOTES_COLUMN,
    ]:
        result[column] = retagged_rows[column]

    result["Root Cause Driver"] = result[REVISED_COLUMN]

    return result


def _retag_row(row: pd.Series) -> dict[str, str]:
    original_tags = split_pipe_tags(row.get("Root Cause Driver"))
    text = _combined_text(row)

    if not original_tags:
        return {
            PRIMARY_COLUMN: "",
            CONTRIBUTING_COLUMN: "",
            REVISED_COLUMN: "",
            CONFIDENCE_COLUMN: "Low",
            NOTES_COLUMN: "No original root-cause tags supplied.",
        }

    scores = _score_tags(original_tags, text, row)
    primary = _choose_primary(original_tags, scores)
    contributing = _choose_contributing(original_tags, primary, scores, text)
    revised_tags = [primary] + contributing if primary else contributing

    notes = _notes(original_tags, primary, contributing, scores, text)
    confidence = _confidence(original_tags, primary, scores)

    return {
        PRIMARY_COLUMN: primary,
        CONTRIBUTING_COLUMN: "|".join(contributing),
        REVISED_COLUMN: "|".join(revised_tags),
        CONFIDENCE_COLUMN: confidence,
        NOTES_COLUMN: notes,
    }


def _score_tags(original_tags: list[str], text: str, row: pd.Series) -> dict[str, int]:
    mechanisms = set(split_pipe_tags(row.get("Failure Mechanism")))
    domains = set(split_pipe_tags(row.get("Regulatory Domain")))
    failure_types = set(split_pipe_tags(row.get("Failure Type")))

    scores: dict[str, int] = {}
    for tag in original_tags:
        score = 2 if tag != WEAK_RISK else 1
        pattern = EVIDENCE_PATTERNS.get(tag)
        if pattern and pattern.search(text):
            score += 3 if tag != WEAK_RISK else 2

        if tag == "RC_KNOWN_RISK" and "FM_FAILURE_TO_ESCALATE" in mechanisms:
            score += 2
        if tag == "RC_DATA_QUALITY" and mechanisms & {
            "FM_DATA_INACCURACY",
            "FM_INCOMPLETE_DATA_CAPTURE",
            "FM_DATA_DUPLICATION",
        }:
            score += 2
        if tag == "RC_SYSTEM_INTEGRATION" and mechanisms & {
            "FM_REPORTING_MISCONFIGURATION",
            "FM_SURVEILLANCE_FAILURE",
        }:
            score += 2
        if tag == "RC_POOR_DOCUMENTATION" and "FM_RECORDKEEPING_FAILURE" in mechanisms:
            score += 2
        if tag == "RC_REG_UNDERSTANDING" and "RD_REG_REPORTING" in domains:
            score += 1
        if tag == "RC_INCENTIVES_CULTURE" and "FT_INTEGRITY" in failure_types:
            score += 2
        if tag == "RC_CONCENTRATED_CONTROL" and "FT_INTEGRITY" in failure_types:
            score += 1
        if tag == WEAK_RISK and "FT_GOVERNANCE" in failure_types:
            score += 1

        scores[tag] = score

    return scores


def _choose_primary(original_tags: list[str], scores: dict[str, int]) -> str:
    non_weak = [tag for tag in original_tags if tag != WEAK_RISK]
    if non_weak:
        ranked = sorted(
            non_weak,
            key=lambda tag: (scores.get(tag, 0), -ROOT_CAUSE_PRIORITY.index(tag) if tag in ROOT_CAUSE_PRIORITY else -99),
            reverse=True,
        )
        best_specific = ranked[0]
        weak_score = scores.get(WEAK_RISK, 0)
        if WEAK_RISK in original_tags and weak_score >= scores.get(best_specific, 0) + 2:
            return WEAK_RISK
        return best_specific

    return original_tags[0]


def _choose_contributing(
    original_tags: list[str],
    primary: str,
    scores: dict[str, int],
    text: str,
) -> list[str]:
    contributing: list[str] = []
    for tag in original_tags:
        if tag == primary:
            continue
        if tag == WEAK_RISK and not _strong_weak_risk_evidence(text):
            continue
        if scores.get(tag, 0) >= 3:
            contributing.append(tag)

    contributing.sort(key=lambda tag: ROOT_CAUSE_PRIORITY.index(tag) if tag in ROOT_CAUSE_PRIORITY else 99)
    return contributing


def _strong_weak_risk_evidence(text: str) -> bool:
    pattern = EVIDENCE_PATTERNS[WEAK_RISK]
    return bool(pattern.search(text))


def _notes(
    original_tags: list[str],
    primary: str,
    contributing: list[str],
    scores: dict[str, int],
    text: str,
) -> str:
    notes = []
    if WEAK_RISK in original_tags and primary != WEAK_RISK:
        notes.append("Weak risk framework demoted from primary in favour of a more specific driver.")
    if WEAK_RISK in original_tags and WEAK_RISK not in [primary] + contributing:
        notes.append("Weak risk framework removed from revised tags due to limited explicit framework evidence.")
    if WEAK_RISK not in original_tags and _strong_weak_risk_evidence(text):
        notes.append("Potential weak-risk-framework evidence present, but original tag was not added.")
    if len(original_tags) >= 3:
        notes.append("Original row had three or more root-cause tags; review for over-tagging.")
    if _score_gap_is_small(primary, scores):
        notes.append("Primary tag selected on a narrow evidence margin; manual review recommended.")
    return " ".join(notes)


def _confidence(original_tags: list[str], primary: str, scores: dict[str, int]) -> str:
    if not primary:
        return "Low"
    if len(original_tags) == 1:
        return "Medium"
    sorted_scores = sorted(scores.values(), reverse=True)
    if len(sorted_scores) > 1 and sorted_scores[0] - sorted_scores[1] <= 1:
        return "Medium"
    return "High"


def _score_gap_is_small(primary: str, scores: dict[str, int]) -> bool:
    if not primary or len(scores) < 2:
        return False
    ranked = sorted(scores.values(), reverse=True)
    return ranked[0] - ranked[1] <= 1


def _combined_text(row: pd.Series) -> str:
    columns = ["Case Name", "Description", "Issue cause", "What went wrong", "Legal Consequence"]
    return " ".join(str(row.get(column, "")) for column in columns if pd.notna(row.get(column, "")))


def _review_table(df: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "Case ID",
        "Case Name",
        "Agency",
        "Year",
        "Regulatory Domain",
        "Failure Type",
        ORIGINAL_COLUMN,
        PRIMARY_COLUMN,
        CONTRIBUTING_COLUMN,
        REVISED_COLUMN,
        CONFIDENCE_COLUMN,
        NOTES_COLUMN,
        "Issue cause",
        "What went wrong",
    ]
    return df[[column for column in columns if column in df.columns]]


def _summary_markdown(df: pd.DataFrame) -> str:
    original_counts = _count_tags(df[ORIGINAL_COLUMN])
    revised_counts = _count_tags(df[REVISED_COLUMN])
    primary_counts = Counter(df[PRIMARY_COLUMN].dropna())
    weak_original = original_counts.get(WEAK_RISK, 0)
    weak_revised = revised_counts.get(WEAK_RISK, 0)
    weak_primary = primary_counts.get(WEAK_RISK, 0)

    lines = [
        "# Root Cause Retagging Summary",
        "",
        f"Rows reviewed: {len(df)}",
        "",
        "## Weak Risk Framework",
        "",
        f"- Original rows tagged `{WEAK_RISK}`: {weak_original}",
        f"- Revised rows retaining `{WEAK_RISK}` as primary or contributing: {weak_revised}",
        f"- Rows where `{WEAK_RISK}` is the primary root cause: {weak_primary}",
        "",
        "## Primary Root Cause Distribution",
        "",
    ]
    for tag, count in primary_counts.most_common():
        if tag:
            lines.append(f"- `{tag}` - {get_label('Root Cause Driver', tag)}: {count}")

    lines.extend(["", "## Review Flags", ""])
    confidence_counts = Counter(df[CONFIDENCE_COLUMN].dropna())
    for label, count in confidence_counts.most_common():
        lines.append(f"- {label}: {count}")

    flagged = df[df[NOTES_COLUMN].str.contains("manual review|removed|not added", case=False, na=False)]
    lines.extend(["", "## Cases Recommended For Manual Review", ""])
    for _, row in flagged.iterrows():
        lines.append(
            f"- {row.get('Case ID')}: {row.get('Case Name')} - {row.get(NOTES_COLUMN)}"
        )

    return "\n".join(lines) + "\n"


def _count_tags(series: pd.Series) -> Counter[str]:
    counter: Counter[str] = Counter()
    for value in series.dropna():
        counter.update(split_pipe_tags(value))
    return counter


def _clean_text(value: object) -> object:
    """Clean common mojibake and typographic characters in workbook text."""
    if not isinstance(value, str):
        return value

    text = value.strip()
    try:
        text = text.encode("cp1252").decode("utf-8")
    except UnicodeError:
        pass

    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text


if __name__ == "__main__":
    paths = retag_mapping_sheet()
    for label, path in paths.items():
        print(f"{label}: {path}")
