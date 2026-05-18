"""Plain-English topic packs for the Streamlit research workbench."""

from __future__ import annotations

from collections import Counter

import pandas as pd

from .normalise import filter_cases_by_tags, split_pipe_tags
from .taxonomy import TAXONOMY_COLUMNS, get_label


ALL_TOPIC_NAME = "All issue topics"
ALL_FIRM_TYPE_NAME = "All firm types"


FIRM_TYPE_RULES: list[tuple[str, tuple[str, ...]]] = [
    (
        "Banks, building societies and banking groups",
        ("bank", "building society", "banking group", "bank branch"),
    ),
    (
        "Investment, brokerage and trading firms",
        (
            "broker",
            "brokerage",
            "investment bank",
            "investment firm",
            "investment services",
            "interdealer",
            "commodities",
            "trading",
            "asset manager",
        ),
    ),
    (
        "Financial advisers and wealth managers",
        ("financial adviser", "ifa", "wealth", "investment manager"),
    ),
    (
        "Insurance firms and intermediaries",
        ("insurer", "insurance", "reinsurance"),
    ),
    (
        "Payments, e-money, crypto and money transfer",
        ("payment", "payments", "e-money", "crypto", "money transfer"),
    ),
    (
        "Consumer credit, claims and debt firms",
        ("claims", "motor finance", "debt management"),
    ),
    (
        "Market infrastructure and exchanges",
        ("exchange", "payment infrastructure"),
    ),
    (
        "Listed companies, audit and professional bodies",
        ("listed", "audit firm", "professional body"),
    ),
    (
        "Individuals and senior managers",
        ("individual", "senior manager", "ceo"),
    ),
]


TOPIC_DEFINITIONS: dict[str, dict[str, object]] = {
    "AML / Financial Crime": {
        "summary": (
            "Cases involving weaknesses in customer due diligence, enhanced due "
            "diligence, customer risk assessment, transaction monitoring, and "
            "financial crime controls."
        ),
        "pattern": (
            "Known or identifiable financial crime risk tends to appear through "
            "CDD, EDD, onboarding, or transaction-monitoring weaknesses, leading "
            "to execution and governance failures."
        ),
        "useful_for": (
            "Understanding FCA expectations around AML systems and controls, "
            "risk assessment, monitoring, escalation, and remediation."
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
            "Outcome Severity": ["OS_FINANCIAL_CRIME_FACILITATED"],
        },
    },
    "Market Abuse": {
        "summary": (
            "Cases concerning market integrity, trading controls, surveillance, "
            "benchmark or pricing misconduct, and misleading market activity."
        ),
        "pattern": (
            "Market abuse cases often involve surveillance or escalation gaps, "
            "poor records, weak supervision, or incentives that allow problematic "
            "trading conduct to continue."
        ),
        "useful_for": (
            "Comparing how regulators frame trading-control, supervision, "
            "surveillance, and market-integrity failures."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_MARKET_ABUSE"],
            "Failure Mechanism": ["FM_SURVEILLANCE_FAILURE"],
            "Outcome Severity": ["OS_MARKET_INTEGRITY_IMPACT"],
        },
    },
    "Poor Governance": {
        "summary": (
            "Cases where oversight, accountability, escalation, board or senior "
            "management control, or basic governance arrangements were central."
        ),
        "pattern": (
            "Governance issues tend to involve a failure to own, escalate, "
            "challenge, document, or remediate known weaknesses."
        ),
        "useful_for": (
            "Understanding how regulators describe governance weakness across "
            "different regulatory domains."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_CONDUCT_GOVERNANCE"],
            "Failure Type": ["FT_GOVERNANCE"],
            "Lifecycle Stage": ["LS_GOVERNANCE_OVERSIGHT"],
        },
    },
    "Regulatory Reporting": {
        "summary": (
            "Cases involving inaccurate, late, incomplete, or unreliable "
            "regulatory submissions and reporting controls."
        ),
        "pattern": (
            "Reporting cases often combine data quality, system configuration, "
            "recordkeeping, and escalation failures."
        ),
        "useful_for": (
            "Analysing reporting-control expectations and how inaccurate "
            "information becomes an enforcement issue."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_REG_REPORTING"],
            "Failure Mechanism": [
                "FM_REPORTING_MISCONFIGURATION",
                "FM_DATA_INACCURACY",
                "FM_RECORDKEEPING_FAILURE",
            ],
        },
    },
    "Customer Harm": {
        "summary": (
            "Cases where consumers or clients were exposed to poor outcomes, "
            "financial loss, unsuitable treatment, or inadequate support."
        ),
        "pattern": (
            "Customer-harm cases often involve poor servicing, weak controls, "
            "inadequate records, unsuitable processes, or failure to identify and "
            "remediate affected customers."
        ),
        "useful_for": (
            "Reviewing consumer outcome themes and examples of actual or "
            "potential detriment."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_CONDUCT_GOVERNANCE", "RD_CONSUMER_DUTY"],
            "Outcome Severity": ["OS_POTENTIAL_CONSUMER_DETRIMENT", "OS_ACTUAL_FINANCIAL_LOSS"],
        },
    },
    "Data Protection": {
        "summary": (
            "Cases involving consent, lawful use of customer data, direct "
            "marketing, data processing, or data-handling controls."
        ),
        "pattern": (
            "Data-protection cases tend to turn on whether the firm had a lawful "
            "basis, adequate consent evidence, and sufficient controls over data "
            "sources and processing."
        ),
        "useful_for": (
            "Understanding privacy, consent, marketing, and operational data "
            "control failures."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_DATA_PROTECTION", "RD_MARKETING_CONSENT"],
            "Failure Mechanism": [
                "FM_CONSENT_CAPTURE_FAILURE",
                "FM_DATA_PROCESSING_ERROR",
                "FM_UNLAWFUL_DATA_USAGE",
            ],
        },
    },
    "Misleading The Regulator": {
        "summary": (
            "Cases involving inaccurate, incomplete, misleading, or inadequately "
            "escalated information provided to a regulator."
        ),
        "pattern": (
            "These cases often involve integrity concerns, poor escalation, "
            "incomplete records, or a failure to correct inaccurate regulatory "
            "information promptly."
        ),
        "useful_for": (
            "Comparing openness, cooperation, regulatory notification, and "
            "integrity themes."
        ),
        "selected_tags": {
            "Failure Type": ["FT_INTEGRITY"],
            "Failure Mechanism": ["FM_MISLEADING_REGULATOR"],
        },
    },
    "Prudential Weakness": {
        "summary": (
            "Cases involving capital, liquidity, governance, operational "
            "resilience, prudential reporting, or safety-and-soundness concerns."
        ),
        "pattern": (
            "Prudential cases often connect governance, data quality, reporting, "
            "systems, and senior oversight weaknesses."
        ),
        "useful_for": (
            "Understanding how PRA and FCA cases frame prudential controls and "
            "governance expectations."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_PRUDENTIAL", "RD_REG_REPORTING"],
        },
    },
    "Client Asset / Money Issues": {
        "summary": (
            "Cases involving client money, client assets, unauthorised activity, "
            "misappropriation, or failures to protect client positions."
        ),
        "pattern": (
            "These cases often involve concentrated control, poor records, weak "
            "segregation or oversight, and urgent restrictions where client harm "
            "or asset dissipation is possible."
        ),
        "useful_for": (
            "Identifying cases where regulators intervene to protect client "
            "assets, client money, or client positions."
        ),
        "selected_tags": {
            "Regulatory Domain": ["RD_CLIENT_ASSETS", "RD_CONDUCT_GOVERNANCE"],
            "Failure Mechanism": [
                "FM_MISAPPROPRIATION_OF_FUNDS",
                "FM_UNAUTHORISED_ACTIVITY",
                "FM_RECORDKEEPING_FAILURE",
            ],
            "Punishment": ["ENF_RESTRICTION_IMPOSED"],
        },
    },
}


def topic_names() -> list[str]:
    """Return display names for supported topic packs."""
    return [ALL_TOPIC_NAME] + list(TOPIC_DEFINITIONS)


def add_firm_type_group(df: pd.DataFrame) -> pd.DataFrame:
    """Return df with a broad Firm Type Group column added."""
    result = df.copy()
    result["Firm Type Group"] = result["Institution Type"].apply(firm_type_group)
    return result


def firm_type_group(institution_type: object) -> str:
    """Map a detailed Institution Type value to a broad firm type group."""
    text = _text(institution_type).lower()
    for group, keywords in FIRM_TYPE_RULES:
        if any(keyword in text for keyword in keywords):
            return group
    return "Other financial services firms"


def firm_type_names(df: pd.DataFrame) -> list[str]:
    """Return firm type group names present in the data, ordered by case count."""
    grouped = add_firm_type_group(df)
    return [ALL_FIRM_TYPE_NAME] + grouped["Firm Type Group"].value_counts().index.tolist()


def get_firm_type_cases(df: pd.DataFrame, firm_type_name: str) -> pd.DataFrame:
    """Return cases belonging to one broad firm type group."""
    grouped = add_firm_type_group(df)
    if firm_type_name == ALL_FIRM_TYPE_NAME:
        cases = grouped.copy()
    else:
        cases = grouped[grouped["Firm Type Group"] == firm_type_name].copy()
    if cases.empty:
        return cases
    return (
        cases.sort_values(
            by=["Year", "Agency", "Case ID"],
            ascending=[False, True, True],
            na_position="last",
        )
        .reset_index(drop=True)
    )


def get_firm_type_pack(df: pd.DataFrame, firm_type_name: str, example_limit: int = 8) -> dict[str, object]:
    """Build a firm-type pack showing what failures appear for that group."""
    cases = get_firm_type_cases(df, firm_type_name)
    raw_types = []
    if not cases.empty:
        type_column = "Firm Type Group" if firm_type_name == ALL_FIRM_TYPE_NAME else "Institution Type"
        raw_types = cases[type_column].value_counts().head(8).items()

    return {
        "name": firm_type_name,
        "case_count": len(cases),
        "cases": cases,
        "example_cases": cases.head(example_limit),
        "institution_types": [(str(label), int(count)) for label, count in raw_types],
        "common_regulatory_domains": top_tag_labels(cases, "Regulatory Domain", limit=5),
        "common_failure_types": top_tag_labels(cases, "Failure Type", limit=5),
        "common_root_causes": top_tag_labels(cases, "Root Cause Driver", limit=5),
        "common_failure_mechanisms": top_tag_labels(cases, "Failure Mechanism", limit=6),
        "common_outcomes": top_tag_labels(cases, "Outcome Severity", limit=5),
        "common_punishments": top_tag_labels(cases, "Punishment", limit=5),
        "pattern_cards": firm_type_pattern_cards(cases, limit=3),
        "interpretation": firm_type_interpretation(cases, firm_type_name),
    }


def firm_type_overview(df: pd.DataFrame) -> pd.DataFrame:
    """Summarise the dominant failure profile for each broad firm type."""
    rows = []
    for firm_type_name in firm_type_names(df):
        pack = get_firm_type_pack(df, firm_type_name, example_limit=0)
        rows.append(
            {
                "Firm Type": firm_type_name,
                "Cases": pack["case_count"],
                "Common Domains": _compact_list(pack["common_regulatory_domains"], limit=3),
                "Common Failure Types": _compact_list(pack["common_failure_types"], limit=3),
                "Common Control Failures": _compact_list(pack["common_failure_mechanisms"], limit=3),
                "Common Root Causes": _compact_list(pack["common_root_causes"], limit=3),
                "Common Outcomes": _compact_list(pack["common_outcomes"], limit=3),
            }
        )
    return pd.DataFrame(rows)


def firm_type_interpretation(cases: pd.DataFrame, firm_type_name: str) -> str:
    """Create a short, template-based interpretation of a firm type profile."""
    if cases.empty:
        return "No cases found for this firm type."

    failure = _first_label(top_tag_labels(cases, "Failure Type", limit=1))
    mechanism = _first_label(top_tag_labels(cases, "Failure Mechanism", limit=1))
    root_cause = _first_label(top_tag_labels(cases, "Root Cause Driver", limit=1))
    outcome = _first_label(top_tag_labels(cases, "Outcome Severity", limit=1))

    subject = "all firm types" if firm_type_name == ALL_FIRM_TYPE_NAME else firm_type_name.lower()
    return (
        f"In this dataset, {subject} most often appear with "
        f"{failure.lower() if failure else 'recurring failure patterns'}, commonly "
        f"through {mechanism.lower() if mechanism else 'control weaknesses'}. The "
        f"leading root-cause signal is {root_cause.lower() if root_cause else 'not clear'}, "
        f"with {outcome.lower() if outcome else 'mixed outcomes'} as a recurring outcome."
    )


def firm_type_pattern_cards(cases: pd.DataFrame, limit: int = 3) -> list[dict[str, object]]:
    """Build top pattern cards for a firm type, anchored on root causes."""
    if cases.empty:
        return []

    root_causes = top_tag_labels(cases, "Root Cause Driver", limit=limit)
    cards: list[dict[str, object]] = []

    for root_cause_label, _ in root_causes:
        root_cause_code = _code_for_label("Root Cause Driver", root_cause_label)
        subset = cases[
            cases["Root Cause Driver"].apply(
                lambda value: root_cause_code in split_pipe_tags(value)
            )
        ]
        if subset.empty:
            continue

        mechanism = _first_label(top_tag_labels(subset, "Failure Mechanism", limit=1))
        failure_type = _first_label(top_tag_labels(subset, "Failure Type", limit=1))
        outcome = _first_label(top_tag_labels(subset, "Outcome Severity", limit=1))
        punishment = _first_label(top_tag_labels(subset, "Punishment", limit=1))

        cards.append(
            {
                "root_cause": root_cause_label,
                "case_count": len(subset),
                "mechanism": mechanism,
                "failure_type": failure_type,
                "outcome": outcome,
                "punishment": punishment,
                "example_cases": [
                    case_display_name(row)
                    for _, row in subset.sort_values(
                        by=["Year", "Agency", "Case ID"],
                        ascending=[False, True, True],
                        na_position="last",
                    )
                    .head(3)
                    .iterrows()
                ],
            }
        )

    return cards


def get_topic_cases(df: pd.DataFrame, topic_name: str) -> pd.DataFrame:
    """Return cases matching a topic definition."""
    if topic_name == ALL_TOPIC_NAME:
        cases = df.copy()
        cases["Topic Relevance"] = "Whole dataset"
        return (
            cases.sort_values(
                by=["Year", "Agency", "Case ID"],
                ascending=[False, True, True],
                na_position="last",
            )
            .reset_index(drop=True)
        )

    definition = TOPIC_DEFINITIONS[topic_name]
    selected_tags = definition["selected_tags"]
    cases = filter_cases_by_tags(df, selected_tags, match="any")
    return rank_cases_for_topic(cases, selected_tags)


def rank_cases_for_topic(
    df: pd.DataFrame,
    selected_tags: dict[str, list[str]],
) -> pd.DataFrame:
    """Rank topic cases by tag overlap and recency."""
    if df.empty:
        return df.copy()

    ranked = df.copy()
    ranked["Topic Relevance"] = ranked.apply(
        lambda row: _topic_relevance_score(row, selected_tags),
        axis=1,
    )
    return (
        ranked.sort_values(
            by=["Topic Relevance", "Year", "Agency", "Case ID"],
            ascending=[False, False, True, True],
            na_position="last",
        )
        .reset_index(drop=True)
    )


def get_topic_pack(df: pd.DataFrame, topic_name: str, example_limit: int = 8) -> dict[str, object]:
    """Build a topic pack with summary statistics and example cases."""
    if topic_name == ALL_TOPIC_NAME:
        definition = {
            "summary": (
                "All cases in the tracker, across FCA, PRA, and ICO enforcement "
                "themes."
            ),
            "pattern": (
                "This view shows the broad recurring enforcement pathways across "
                "the whole dataset rather than one selected issue category."
            ),
            "useful_for": (
                "Getting a whole-dataset view before moving into a specific issue "
                "topic or firm type."
            ),
        }
    else:
        definition = TOPIC_DEFINITIONS[topic_name]

    cases = get_topic_cases(df, topic_name)
    return {
        "name": topic_name,
        "summary": definition["summary"],
        "pattern": definition["pattern"],
        "useful_for": definition["useful_for"],
        "case_count": len(cases),
        "cases": cases,
        "example_cases": cases.head(example_limit),
        "common_regulatory_domains": top_tag_labels(cases, "Regulatory Domain", limit=5),
        "common_root_causes": top_tag_labels(cases, "Root Cause Driver", limit=5),
        "common_failure_mechanisms": top_tag_labels(cases, "Failure Mechanism", limit=6),
        "common_failure_types": top_tag_labels(cases, "Failure Type", limit=5),
        "common_outcomes": top_tag_labels(cases, "Outcome Severity", limit=5),
        "common_punishments": top_tag_labels(cases, "Punishment", limit=5),
        "pattern_cards": firm_type_pattern_cards(cases, limit=3),
    }


def top_tag_labels(df: pd.DataFrame, column: str, limit: int = 5) -> list[tuple[str, int]]:
    """Return top readable labels for a pipe-separated taxonomy column."""
    counter: Counter[str] = Counter()
    if df.empty or column not in df.columns:
        return []
    for _, case in df.iterrows():
        for tag in set(split_pipe_tags(case.get(column))):
            counter[get_label(column, tag)] += 1
    return counter.most_common(limit)


def case_display_name(row: pd.Series) -> str:
    """Return a compact display name for a case row."""
    return f"{_text(row.get('Case ID'))} - {_text(row.get('Case Name'))}"


def case_narrative_fields(row: pd.Series) -> dict[str, str]:
    """Return the human-readable case fields used in case cards."""
    return {
        "Description": _text(row.get("Description")),
        "Issue cause": _text(row.get("Issue cause")),
        "What went wrong": _text(row.get("What went wrong")),
        "Legal consequence": _text(row.get("Legal Consequence")),
    }


def readable_shared_tags(shared_tags: dict[str, list[str]]) -> dict[str, list[str]]:
    """Convert shared similarity tags from codes to readable labels."""
    readable: dict[str, list[str]] = {}
    for column, codes in shared_tags.items():
        readable[column] = [get_label(column, code) for code in codes]
    return readable


def _topic_relevance_score(row: pd.Series, selected_tags: dict[str, list[str]]) -> int:
    score = 0
    for column, codes in selected_tags.items():
        case_tags = set(split_pipe_tags(row.get(column)))
        score += len(case_tags & set(codes))
    return score


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _compact_list(values: list[tuple[str, int]], limit: int = 3) -> str:
    return "; ".join(f"{label} ({count})" for label, count in values[:limit])


def _first_label(values: list[tuple[str, int]]) -> str:
    return values[0][0] if values else ""


def _code_for_label(column: str, label: str) -> str:
    for code in _codes_for_column(column):
        if get_label(column, code) == label:
            return code
    return label


def _codes_for_column(column: str) -> list[str]:
    # Imported lazily to keep TAG_DICTIONARIES out of the public API of this file.
    from .taxonomy import TAG_DICTIONARIES

    return list(TAG_DICTIONARIES.get(column, {}))
