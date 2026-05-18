"""Cluster-style summaries for qualitative enforcement case analysis.

These helpers avoid opaque ML clustering. They group cases through explainable
taxonomy overlap, then produce research-oriented summaries that can be used in
notebooks, scripts, or a later Streamlit front end.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pandas as pd

from .normalise import filter_cases_by_tags, split_pipe_tags
from .taxonomy import TAXONOMY_COLUMNS, get_label


CASE_COLUMNS = ["Case ID", "Case Name", "Agency", "Year"]


LEGAL_ISSUE_DEFINITIONS: list[dict[str, object]] = [
    {
        "name": "AML onboarding and monitoring failures",
        "thesis": (
            "Cases where firms failed to identify, assess, monitor, or escalate "
            "financial crime risk across onboarding and ongoing monitoring."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_AML"],
            "Failure Mechanism": [
                "FM_CDD_FAILURE",
                "FM_EDD_FAILURE",
                "FM_CUSTOMER_RISK_ASSESSMENT_FAILURE",
                "FM_ONBOARDING_KYC_FAILURE",
                "FM_TRANSACTION_MONITORING_FAILURE",
            ],
        },
        "legal_use": (
            "Useful for comparing systems and controls expectations around "
            "financial crime frameworks, customer risk assessment, CDD/EDD, and "
            "transaction monitoring."
        ),
    },
    {
        "name": "Prudential governance and regulatory reporting",
        "thesis": (
            "Cases involving weak prudential governance, inadequate oversight, "
            "or inaccurate regulatory reporting."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_PRUDENTIAL", "RD_REG_REPORTING"],
            "Failure Mechanism": ["FM_REPORTING_MISCONFIGURATION", "FM_DATA_INACCURACY"],
        },
        "legal_use": (
            "Useful for assessing governance, senior oversight, data controls, "
            "and the reliability of regulatory submissions."
        ),
    },
    {
        "name": "Market abuse surveillance and trading controls",
        "thesis": (
            "Cases where trading, surveillance, or market controls failed to "
            "identify or prevent market integrity risk."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_MARKET_ABUSE"],
            "Failure Mechanism": ["FM_SURVEILLANCE_FAILURE"],
            "Outcome Severity": ["OS_MARKET_INTEGRITY_IMPACT"],
        },
        "legal_use": (
            "Useful for analysing trading-control expectations, surveillance "
            "calibration, escalation, and market integrity harm."
        ),
    },
    {
        "name": "Conduct governance and consumer harm",
        "thesis": (
            "Cases where governance, sales, servicing, or control weaknesses "
            "created consumer detriment or poor customer outcomes."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_CONDUCT_GOVERNANCE"],
            "Failure Mechanism": ["FM_COMPLAINT_HANDLING_FAILURE"],
            "Outcome Severity": ["OS_POTENTIAL_CONSUMER_DETRIMENT", "OS_ACTUAL_FINANCIAL_LOSS"],
        },
        "legal_use": (
            "Useful for conduct-risk analysis, customer-outcome reviews, and "
            "comparison of remediation or redress themes."
        ),
    },
    {
        "name": "Data protection and marketing consent",
        "thesis": (
            "Cases involving failures in consent capture, data processing, or "
            "lawful use of customer data."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_DATA_PROTECTION", "RD_MARKETING_CONSENT"],
            "Failure Mechanism": [
                "FM_CONSENT_CAPTURE_FAILURE",
                "FM_DATA_PROCESSING_ERROR",
                "FM_UNLAWFUL_DATA_USAGE",
            ],
        },
        "legal_use": (
            "Useful for privacy, direct marketing, consent, and operational data "
            "handling reviews."
        ),
    },
    {
        "name": "Integrity and misleading the regulator",
        "thesis": (
            "Cases where inaccurate, incomplete, or misleading information to "
            "the regulator is part of the enforcement pattern."
        ),
        "selected_tags": {
            "Failure Type": ["FT_INTEGRITY"],
            "Failure Mechanism": ["FM_MISLEADING_REGULATOR"],
        },
        "legal_use": (
            "Useful for analysing openness with regulators, integrity concerns, "
            "notification duties, and aggravating conduct."
        ),
    },
]


def build_failure_pathway_clusters(
    df: pd.DataFrame,
    min_cases: int = 2,
    top_n: int = 20,
) -> pd.DataFrame:
    """Group cases by Root Cause -> Failure Mechanism -> Failure Type pathways."""
    rows: list[dict[str, object]] = []

    for _, case in df.iterrows():
        root_causes = split_pipe_tags(case.get("Root Cause Driver"))
        mechanisms = split_pipe_tags(case.get("Failure Mechanism"))
        failure_types = split_pipe_tags(case.get("Failure Type"))

        for root_cause in root_causes:
            for mechanism in mechanisms:
                for failure_type in failure_types:
                    rows.append(
                        {
                            "Root Cause Driver": root_cause,
                            "Failure Mechanism": mechanism,
                            "Failure Type": failure_type,
                            "Case ID": case.get("Case ID"),
                        }
                    )

    if not rows:
        return pd.DataFrame()

    pathway_rows = pd.DataFrame(rows).drop_duplicates()
    grouped = (
        pathway_rows.groupby(["Root Cause Driver", "Failure Mechanism", "Failure Type"])
        ["Case ID"]
        .nunique()
        .reset_index(name="Case Count")
        .query("`Case Count` >= @min_cases")
        .sort_values("Case Count", ascending=False)
        .head(top_n)
    )

    summaries = []
    for _, pathway in grouped.iterrows():
        cases = _cases_for_pathway(df, pathway)
        summaries.append(
            {
                "Cluster Name": (
                    f"{get_label('Root Cause Driver', pathway['Root Cause Driver'])} -> "
                    f"{get_label('Failure Mechanism', pathway['Failure Mechanism'])} -> "
                    f"{get_label('Failure Type', pathway['Failure Type'])}"
                ),
                "Case Count": int(pathway["Case Count"]),
                "Root Cause Driver": pathway["Root Cause Driver"],
                "Failure Mechanism": pathway["Failure Mechanism"],
                "Failure Type": pathway["Failure Type"],
                "Common Regulatory Domains": _top_labels(cases, "Regulatory Domain", 4),
                "Common Outcomes": _top_labels(cases, "Outcome Severity", 4),
                "Common Punishments": _top_labels(cases, "Punishment", 4),
                "Representative Cases": _representative_cases(cases),
                "Thesis": _pathway_thesis(pathway),
                "Legal Use": (
                    "Use this pathway to compare how a recurring root cause and "
                    "control mechanism translate into a particular regulatory "
                    "failure type across cases."
                ),
                "Review Questions": _review_questions_for_pathway(pathway),
            }
        )

    return pd.DataFrame(summaries)


def build_control_failure_clusters(
    df: pd.DataFrame,
    min_cases: int = 2,
    top_n: int = 20,
) -> pd.DataFrame:
    """Group cases by Failure Mechanism and summarise related legal patterns."""
    counts = _tag_case_counts(df, "Failure Mechanism")
    counts = counts[counts["Case Count"] >= min_cases].head(top_n)

    summaries = []
    for _, row in counts.iterrows():
        mechanism = row["Tag Code"]
        cases = filter_cases_by_tags(df, {"Failure Mechanism": [mechanism]}, match="any")
        summaries.append(
            {
                "Cluster Name": get_label("Failure Mechanism", mechanism),
                "Case Count": int(row["Case Count"]),
                "Failure Mechanism": mechanism,
                "Common Failure Types": _top_labels(cases, "Failure Type", 5),
                "Common Root Causes": _top_labels(cases, "Root Cause Driver", 5),
                "Common Regulatory Domains": _top_labels(cases, "Regulatory Domain", 5),
                "Common Outcomes": _top_labels(cases, "Outcome Severity", 5),
                "Common Punishments": _top_labels(cases, "Punishment", 5),
                "Representative Cases": _representative_cases(cases),
                "Thesis": _control_failure_thesis(mechanism),
                "Legal Use": (
                    "Use this cluster to understand how one operational or "
                    "control mechanism appears across different regulatory "
                    "domains and enforcement outcomes."
                ),
                "Review Questions": _review_questions_for_mechanism(mechanism),
            }
        )

    return pd.DataFrame(summaries)


def build_legal_issue_packs(
    df: pd.DataFrame,
    definitions: list[dict[str, object]] | None = None,
    max_cases: int = 8,
) -> pd.DataFrame:
    """Create lawyer-friendly packs for predefined legal issue themes."""
    packs = []

    for definition in definitions or LEGAL_ISSUE_DEFINITIONS:
        selected_tags = definition["selected_tags"]
        cases = filter_cases_by_tags(df, selected_tags, match="any")
        if cases.empty:
            continue

        packs.append(
            {
                "Issue Pack": definition["name"],
                "Case Count": int(len(cases)),
                "Thesis": definition["thesis"],
                "Representative Cases": _representative_cases(cases, limit=max_cases),
                "Common Regulatory Domains": _top_labels(cases, "Regulatory Domain", 5),
                "Common Failure Types": _top_labels(cases, "Failure Type", 5),
                "Common Root Causes": _top_labels(cases, "Root Cause Driver", 5),
                "Common Failure Mechanisms": _top_labels(cases, "Failure Mechanism", 6),
                "Common Outcomes": _top_labels(cases, "Outcome Severity", 5),
                "Common Punishments": _top_labels(cases, "Punishment", 5),
                "Distinctions": _distinctions(cases),
                "Legal Use": definition["legal_use"],
                "Suggested Questions": _legal_pack_questions(str(definition["name"])),
            }
        )

    return pd.DataFrame(packs).sort_values("Case Count", ascending=False).reset_index(drop=True)


def export_cluster_outputs(
    df: pd.DataFrame,
    output_dir: str | Path = "outputs/clusters",
) -> dict[str, Path]:
    """Build and export all cluster outputs as CSV and Markdown files."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)

    outputs = {
        "failure_pathways": build_failure_pathway_clusters(df),
        "control_failures": build_control_failure_clusters(df),
        "legal_issue_packs": build_legal_issue_packs(df),
    }

    paths: dict[str, Path] = {}
    for name, table in outputs.items():
        csv_path = directory / f"{name}.csv"
        md_path = directory / f"{name}.md"
        table.to_csv(csv_path, index=False)
        md_path.write_text(_to_markdown(name, table), encoding="utf-8")
        paths[f"{name}_csv"] = csv_path
        paths[f"{name}_markdown"] = md_path

    return paths


def _cases_for_pathway(df: pd.DataFrame, pathway: pd.Series) -> pd.DataFrame:
    return filter_cases_by_tags(
        df,
        {
            "Root Cause Driver": [pathway["Root Cause Driver"]],
            "Failure Mechanism": [pathway["Failure Mechanism"]],
            "Failure Type": [pathway["Failure Type"]],
        },
        match="all",
    )


def _tag_case_counts(df: pd.DataFrame, column: str) -> pd.DataFrame:
    rows = []
    for _, case in df.iterrows():
        for tag in set(split_pipe_tags(case.get(column))):
            rows.append({"Tag Code": tag, "Case ID": case.get("Case ID")})

    if not rows:
        return pd.DataFrame(columns=["Tag Code", "Case Count"])

    return (
        pd.DataFrame(rows)
        .groupby("Tag Code")["Case ID"]
        .nunique()
        .reset_index(name="Case Count")
        .sort_values("Case Count", ascending=False)
    )


def _top_labels(df: pd.DataFrame, column: str, limit: int = 5) -> str:
    counter: Counter[str] = Counter()
    for _, case in df.iterrows():
        for tag in set(split_pipe_tags(case.get(column))):
            counter[get_label(column, tag)] += 1

    return "; ".join(f"{label} ({count})" for label, count in counter.most_common(limit))


def _representative_cases(df: pd.DataFrame, limit: int = 6) -> str:
    if df.empty:
        return ""

    sort_columns = [column for column in ["Year", "Agency", "Case ID"] if column in df.columns]
    cases = df.sort_values(sort_columns, ascending=[False, True, True][: len(sort_columns)])

    values = []
    for _, case in cases.head(limit).iterrows():
        case_id = _clean(case.get("Case ID"))
        name = _clean(case.get("Case Name"))
        agency = _clean(case.get("Agency"))
        year = _clean(case.get("Year"))
        values.append(f"{case_id}: {name} ({agency}, {year})")

    return "; ".join(values)


def _distinctions(df: pd.DataFrame) -> str:
    domains = _top_labels(df, "Regulatory Domain", 3)
    outcomes = _top_labels(df, "Outcome Severity", 3)
    punishments = _top_labels(df, "Punishment", 3)
    return (
        "Compare differences in domain emphasis, realised harm, and enforcement "
        f"response. Leading domains: {domains}. Leading outcomes: {outcomes}. "
        f"Leading punishments: {punishments}."
    )


def _pathway_thesis(pathway: pd.Series) -> str:
    root_cause = get_label("Root Cause Driver", pathway["Root Cause Driver"]).lower()
    mechanism = get_label("Failure Mechanism", pathway["Failure Mechanism"]).lower()
    failure_type = get_label("Failure Type", pathway["Failure Type"]).lower()
    return (
        f"This pathway suggests that {root_cause} can manifest through "
        f"{mechanism}, producing {_article_for(failure_type)} {failure_type} pattern."
    )


def _control_failure_thesis(mechanism: str) -> str:
    mechanism_label = get_label("Failure Mechanism", mechanism).lower()
    return (
        f"These cases share {mechanism_label}. The cluster is useful for comparing "
        "how the same control weakness appears across institutions, domains, and "
        "sanctions."
    )


def _review_questions_for_pathway(pathway: pd.Series) -> str:
    root_cause = get_label("Root Cause Driver", pathway["Root Cause Driver"])
    mechanism = get_label("Failure Mechanism", pathway["Failure Mechanism"])
    return (
        f"Was {root_cause.lower()} known to management?; "
        f"What evidence shows {mechanism.lower()}?; "
        "Did the firm remediate promptly?; "
        "Was harm realised or only risk exposure identified?"
    )


def _review_questions_for_mechanism(mechanism: str) -> str:
    mechanism_label = get_label("Failure Mechanism", mechanism).lower()
    return (
        f"What facts evidence {mechanism_label}?; "
        "Was the weakness design-related, execution-related, or governance-related?; "
        "Was the issue known before intervention?; "
        "Which sanctions followed similar facts?"
    )


def _legal_pack_questions(issue_name: str) -> str:
    return (
        f"Which cases are closest analogues for {issue_name.lower()}?; "
        "What facts distinguish higher-severity cases?; "
        "Which aggravating or mitigating factors recur?; "
        "Which cases best support a concise legal memo?"
    )


def _to_markdown(name: str, table: pd.DataFrame) -> str:
    title = name.replace("_", " ").title()
    lines = [f"# {title}", ""]
    if table.empty:
        lines.append("No clusters found.")
        return "\n".join(lines)

    name_column = "Issue Pack" if "Issue Pack" in table.columns else "Cluster Name"
    for _, row in table.iterrows():
        lines.extend(
            [
                f"## {_clean(row.get(name_column))}",
                "",
                f"**Case count:** {_clean(row.get('Case Count'))}",
                "",
            ]
        )
        for column in table.columns:
            if column in {name_column, "Case Count"}:
                continue
            value = _clean(row.get(column))
            if value:
                lines.extend([f"**{column}:** {value}", ""])

    return "\n".join(lines).strip() + "\n"


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    text = str(value).strip()
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


def _article_for(text: str) -> str:
    return "an" if text[:1].lower() in {"a", "e", "i", "o", "u"} else "a"
