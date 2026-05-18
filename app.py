"""Streamlit front end for the regulatory case analysis workbench."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from case_analysis.loader import DEFAULT_DATA_PATH, load_cases
from case_analysis.similarity import find_similar_cases
from case_analysis.taxonomy import TAXONOMY_COLUMNS, get_label
from case_analysis.normalise import split_pipe_tags
from case_analysis.topic_packs import (
    case_display_name,
    case_narrative_fields,
    firm_type_names,
    firm_type_overview,
    get_firm_type_pack,
    get_topic_pack,
    readable_shared_tags,
    topic_names,
)


st.set_page_config(
    page_title="Regulatory Case Finder",
    page_icon=None,
    layout="wide",
)


TILE_COLORS = {
    "root": "49, 95, 114",
    "mechanism": "64, 126, 137",
    "failure": "99, 132, 83",
    "outcome": "143, 105, 63",
    "enforcement": "116, 92, 138",
    "domain": "73, 107, 143",
    "stage": "102, 110, 116",
}


st.markdown(
    """
    <style>
    .pattern-row {
        border: 1px solid #d7dee3;
        border-radius: 8px;
        padding: 14px 16px;
        margin: 12px 0;
        background: #ffffff;
    }
    .pattern-body {
        display: flex;
        gap: 14px;
        align-items: flex-start;
        justify-content: space-between;
        flex-wrap: wrap;
    }
    .tile-path {
        display: flex;
        gap: 8px;
        align-items: stretch;
        flex-wrap: wrap;
        flex: 1 1 680px;
    }
    .case-tag-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 10px;
        margin-top: 8px;
    }
    .case-tag-column {
        border: 1px solid #d7dee3;
        border-radius: 8px;
        padding: 9px;
        background: #fbfcfd;
    }
    .case-tag-title {
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #4f5b63;
        font-weight: 700;
        margin-bottom: 7px;
    }
    .case-tag-stack {
        display: flex;
        flex-direction: column;
        gap: 7px;
    }
    .tile {
        color: #ffffff;
        border-radius: 7px;
        padding: 9px 11px;
        min-width: 135px;
        max-width: 210px;
        box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.18);
    }
    .tile-label {
        font-size: 0.70rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        opacity: 0.82;
        margin-bottom: 4px;
    }
    .tile-value {
        font-weight: 650;
        line-height: 1.18;
        font-size: 0.92rem;
    }
    .arrow {
        align-self: center;
        color: #64717a;
        font-weight: 700;
        padding: 0 2px;
    }
    .pattern-examples {
        flex: 0 1 330px;
        color: #303940;
        font-size: 0.90rem;
        line-height: 1.35;
        border-left: 3px solid #d7dee3;
        padding-left: 12px;
    }
    .pattern-count {
        color: #5c6870;
        font-size: 0.86rem;
        margin-bottom: 8px;
    }
    .profile-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(275px, 1fr));
        gap: 12px;
        margin-top: 8px;
    }
    .profile-card {
        border: 1px solid #d7dee3;
        border-radius: 8px;
        padding: 12px 13px;
        background: #fbfcfd;
    }
    .profile-title {
        font-weight: 700;
        color: #26323a;
        margin-bottom: 8px;
    }
    .profile-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 80px 30px;
        gap: 8px;
        align-items: center;
        margin: 7px 0;
    }
    .profile-label {
        font-size: 0.86rem;
        color: #26323a;
        line-height: 1.2;
    }
    .profile-bar-track {
        height: 8px;
        border-radius: 999px;
        background: #e8edf0;
        overflow: hidden;
    }
    .profile-bar-fill {
        height: 100%;
        border-radius: 999px;
        background: #315f72;
    }
    .profile-count {
        font-size: 0.82rem;
        color: #4f5b63;
        text-align: right;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_case_data(path: str) -> pd.DataFrame:
    """Load case data for Streamlit, cached between reruns."""
    return load_cases(Path(path))


def main() -> None:
    st.title("Regulatory Case Finder")
    st.caption("Plain-English entry points into FCA, PRA, and ICO enforcement cases.")

    try:
        cases = load_case_data(str(DEFAULT_DATA_PATH))
    except Exception as exc:  # pragma: no cover - Streamlit display path.
        st.error(f"Could not load case database: {exc}")
        st.stop()

    topic_tab, firm_type_tab = st.tabs(["Issue Topics", "Firm Types"])

    with topic_tab:
        topic = st.selectbox(
            "What are you looking into?",
            topic_names(),
            index=0,
        )

        pack = get_topic_pack(cases, topic)

        _render_topic_summary_section(pack)
        _render_topic_failure_profile_section(pack)
        _render_example_cases(pack, cases, score_label="Topic score")
        _render_case_lookup(cases, pack)

    with firm_type_tab:
        firm_type = st.selectbox(
            "What type of firm are you interested in?",
            firm_type_names(cases),
            index=0,
        )

        firm_pack = get_firm_type_pack(cases, firm_type)
        _render_firm_type_summary_section(firm_pack)
        _render_firm_type_failure_profile_section(firm_pack, cases)
        _render_example_cases(firm_pack, cases, title="Example Cases For This Firm Type", score_label="Firm type")


def _render_topic_summary_section(pack: dict[str, object]) -> None:
    with st.container(border=True):
        st.subheader(str(pack["name"]))
        st.caption("Selected category summary")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Relevant cases", int(pack["case_count"]))
        metric_cols[1].metric("Common mechanisms", len(pack["common_failure_mechanisms"]))
        metric_cols[2].metric("Common outcomes", len(pack["common_outcomes"]))

        summary_col, pattern_col = st.columns([1, 1])
        with summary_col:
            st.markdown("**What this topic usually involves**")
            st.markdown(f"- {str(pack['summary'])}")
            st.markdown("**Useful for**")
            st.markdown(f"- {str(pack['useful_for'])}")

        with pattern_col:
            st.markdown("**Common pattern**")
            st.markdown(f"- {str(pack['pattern'])}")


def _render_topic_failure_profile_section(pack: dict[str, object]) -> None:
    with st.container(border=True):
        st.subheader("Regulatory action pathways and failure profile")
        st.caption("Top pathways show common threads within the selected issue topic; darker tiles mean more matching cases.")
        _render_pattern_cards(pack["pattern_cards"], empty_message="No recurring pathways available for this issue topic.")

        st.markdown("**Failure profile overview**")
        st.caption("Compact bars show relative strength within each category.")
        _render_profile_grid(
            [
                ("Regulatory domains", pack.get("common_regulatory_domains", [])),
                ("Root causes", pack["common_root_causes"]),
                ("Control failures", pack["common_failure_mechanisms"]),
                ("Failure types", pack["common_failure_types"]),
                ("Outcomes", pack["common_outcomes"]),
                ("Enforcement", pack["common_punishments"]),
            ]
        )


def _render_firm_type_summary_section(pack: dict[str, object]) -> None:
    with st.container(border=True):
        st.subheader(str(pack["name"]))
        st.caption("Selected firm type summary")

        metric_cols = st.columns(3)
        metric_cols[0].metric("Cases", int(pack["case_count"]))
        metric_cols[1].metric("Common failure types", len(pack["common_failure_types"]))
        metric_cols[2].metric("Common control failures", len(pack["common_failure_mechanisms"]))

        st.markdown("**Profile**")
        st.markdown(f"- {str(pack['interpretation'])}")


def _render_firm_type_failure_profile_section(pack: dict[str, object], all_cases: pd.DataFrame) -> None:
    with st.container(border=True):
        st.subheader("Regulatory action pathways and failure profile")
        st.caption("Top pathways show common threads for this firm type; darker tiles mean more matching cases.")
        _render_pattern_cards(pack["pattern_cards"])

        st.markdown("**Failure profile overview**")
        st.caption("Compact bars show relative strength within each category.")
        _render_profile_grid(
            [
                ("Regulatory domains", pack["common_regulatory_domains"]),
                ("Root causes", pack["common_root_causes"]),
                ("Control failures", pack["common_failure_mechanisms"]),
                ("Failure types", pack["common_failure_types"]),
                ("Outcomes", pack["common_outcomes"]),
                ("Enforcement", pack["common_punishments"]),
            ]
        )

        with st.expander("Detailed institution labels inside this group", expanded=False):
            _render_top_list(st.container(), "Institution types", pack["institution_types"])

        with st.expander("Firm type overview across the whole dataset", expanded=False):
            st.dataframe(firm_type_overview(all_cases), hide_index=True, width="stretch")


def _render_example_cases(
    pack: dict[str, object],
    all_cases: pd.DataFrame,
    title: str = "Example Cases",
    score_label: str = "Topic score",
) -> None:
    with st.container(border=True):
        st.subheader(title)
        st.caption("These are ranked by broad relevance, then recency.")

        example_cases = pack["example_cases"]
        if not isinstance(example_cases, pd.DataFrame) or example_cases.empty:
            st.info("No matching cases found.")
            return

        for _, row in example_cases.iterrows():
            _render_case_card(row, all_cases, score_label=score_label)


def _render_case_lookup(cases: pd.DataFrame, pack: dict[str, object]) -> None:
    with st.container(border=True):
        st.subheader("Find Similar Cases")
        st.caption("Choose one case and the app will find the closest analogues using shared taxonomy tags.")

        topic_cases = pack["cases"]
        if not isinstance(topic_cases, pd.DataFrame) or topic_cases.empty:
            st.info("No cases available for similarity search.")
            return

        options = {
            case_display_name(row): str(row["Case ID"])
            for _, row in topic_cases.iterrows()
        }
        selected_label = st.selectbox("Select a case", list(options), index=0)
        selected_case_id = options[selected_label]

        similar = find_similar_cases(cases, selected_case_id, top_n=6)
        if similar.empty:
            st.info("No similar cases found.")
            return

        for _, row in similar.iterrows():
            with st.expander(f"{row['Case ID']} - {row['Case Name']} | score {row['Similarity Score']}"):
                st.write(f"**Regulator:** {row.get('Agency', '')}")
                st.write(f"**Year:** {row.get('Year', '')}")
                shared = readable_shared_tags(row.get("Shared Tags", {}))
                for column, labels in shared.items():
                    st.write(f"**Shared {column.lower()}:** {', '.join(labels)}")


def _render_case_card(row: pd.Series, all_cases: pd.DataFrame, score_label: str = "Topic score") -> None:
    title = f"{row.get('Case ID', '')} - {row.get('Case Name', '')}"
    with st.expander(title, expanded=False):
        meta_cols = st.columns(4)
        meta_cols[0].write(f"**Regulator:** {row.get('Agency', '')}")
        meta_cols[1].write(f"**Year:** {row.get('Year', '')}")
        meta_cols[2].write(f"**Institution:** {row.get('Institution Type', '')}")
        meta_cols[3].write(f"**{score_label}:** {row.get('Topic Relevance', row.get('Firm Type Group', ''))}")

        link = str(row.get("Link", "")).strip()
        if link and link.lower() != "nan":
            st.link_button("Open source", link)

        for heading, text in case_narrative_fields(row).items():
            if text:
                st.markdown(f"**{heading}**")
                st.write(text)

        st.markdown("**Key tags**")
        _render_case_tags(row)

        similar = find_similar_cases(all_cases, str(row["Case ID"]), top_n=3)
        if not similar.empty:
            st.markdown("**Closest analogues**")
            for _, similar_row in similar.iterrows():
                st.write(
                    f"{similar_row['Case ID']} - {similar_row['Case Name']} "
                    f"(score {similar_row['Similarity Score']})"
                )


def _render_case_tags(row: pd.Series) -> None:
    columns_html = []
    for column in TAXONOMY_COLUMNS:
        tags = split_pipe_tags(row.get(column))
        if tags:
            labels = [get_label(column, tag) for tag in tags]
            category = _tile_category_for_column(column)
            tiles = "".join(
                _tile_html("", label, category, opacity=0.9)
                for label in labels
            )
            columns_html.append(
                '<div class="case-tag-column">'
                f'<div class="case-tag-title">{escape(column)}</div>'
                f'<div class="case-tag-stack">{tiles}</div>'
                "</div>"
            )

    if columns_html:
        st.markdown(
            f'<div class="case-tag-grid">{"".join(columns_html)}</div>',
            unsafe_allow_html=True,
        )


def _render_pattern_cards(
    cards: list[dict[str, object]],
    empty_message: str = "No recurring pattern cards available for this firm type.",
) -> None:
    if not cards:
        st.info(empty_message)
        return

    max_count = max(int(card.get("case_count", 0) or 0) for card in cards) or 1
    for card in cards:
        case_count = int(card.get("case_count", 0) or 0)
        opacity = 0.32 + (0.58 * (case_count / max_count))
        pathway_tiles = [
            _tile_html("Root cause", str(card.get("root_cause", "")), "root", opacity),
            _tile_html("Control failure", str(card.get("mechanism", "")), "mechanism", opacity),
            _tile_html("Failure type", str(card.get("failure_type", "")), "failure", opacity),
            _tile_html("Outcome", str(card.get("outcome", "")), "outcome", opacity),
            _tile_html("Enforcement", str(card.get("punishment", "")), "enforcement", opacity),
        ]
        examples = card.get("example_cases", [])
        example_html = "".join(f"<li>{escape(str(example))}</li>" for example in examples)
        st.markdown(
            f"""
            <div class="pattern-row">
                <div class="pattern-count"><strong>{case_count}</strong> matching cases</div>
                <div class="pattern-body">
                    <div class="tile-path">
                        {pathway_tiles[0]}
                        <div class="arrow">&rarr;</div>
                        {pathway_tiles[1]}
                        <div class="arrow">&rarr;</div>
                        {pathway_tiles[2]}
                        <div class="arrow">&rarr;</div>
                        {pathway_tiles[3]}
                        <div class="arrow">&rarr;</div>
                        {pathway_tiles[4]}
                    </div>
                    <div class="pattern-examples">
                        <strong>Example cases</strong>
                        <ul>{example_html}</ul>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _tile_html(label: str, value: str, category: str, opacity: float = 0.88) -> str:
    safe_label = escape(label)
    safe_value = escape(value or "Not specified")
    rgb = TILE_COLORS.get(category, TILE_COLORS["stage"])
    alpha = max(0.18, min(0.95, opacity))
    return (
        f'<div class="tile" style="background: rgba({rgb}, {alpha:.2f});">'
        f'<div class="tile-label">{safe_label}</div>'
        f'<div class="tile-value">{safe_value}</div>'
        "</div>"
    )


def _tile_category_for_column(column: str) -> str:
    if column == "Root Cause Driver":
        return "root"
    if column == "Failure Mechanism":
        return "mechanism"
    if column == "Failure Type":
        return "failure"
    if column == "Outcome Severity":
        return "outcome"
    if column == "Punishment":
        return "enforcement"
    if column == "Regulatory Domain":
        return "domain"
    return "stage"


def _render_profile_grid(sections: list[tuple[str, list[tuple[str, int]]]]) -> None:
    cards = "".join(_profile_card_html(title, values) for title, values in sections)
    st.markdown(f'<div class="profile-grid">{cards}</div>', unsafe_allow_html=True)


def _profile_card_html(title: str, values: list[tuple[str, int]]) -> str:
    category = _profile_category_for_title(title)
    rgb = TILE_COLORS.get(category, TILE_COLORS["stage"])
    border = f"rgba({rgb}, 0.62)"
    background = f"rgba({rgb}, 0.045)"
    bar = f"rgba({rgb}, 0.82)"

    if not values:
        rows = '<div class="profile-label">No data</div>'
    else:
        max_count = max(count for _, count in values) or 1
        rows = ""
        for label, count in values:
            width = max(4, min(100, round((count / max_count) * 100)))
            rows += (
                '<div class="profile-row">'
                f'<div class="profile-label">{escape(str(label))}</div>'
                '<div class="profile-bar-track">'
                f'<div class="profile-bar-fill" style="width: {width}%; background: {bar};"></div>'
                '</div>'
                f'<div class="profile-count">{int(count)}</div>'
                '</div>'
            )

    return (
        f'<div class="profile-card" style="border-color: {border}; background: {background};">'
        f'<div class="profile-title">{escape(title)}</div>'
        f"{rows}"
        '</div>'
    )


def _profile_category_for_title(title: str) -> str:
    key = title.lower()
    if "root" in key:
        return "root"
    if "control" in key:
        return "mechanism"
    if "failure type" in key:
        return "failure"
    if "outcome" in key:
        return "outcome"
    if "enforcement" in key:
        return "enforcement"
    if "domain" in key:
        return "domain"
    return "stage"


def _render_bar_profile(title: str, values: list[tuple[str, int]]) -> None:
    st.markdown(f"**{title}**")
    if not values:
        st.write("No data")
        return

    max_count = max(count for _, count in values) or 1
    for label, count in values:
        row = st.columns([3, 4, 1])
        row[0].write(label)
        row[1].progress(min(100, int(round((count / max_count) * 100))))
        row[2].write(str(count))


def _render_top_list(container, title: str, values: list[tuple[str, int]]) -> None:
    with container:
        st.markdown(f"**{title}**")
        if not values:
            st.write("No data")
            return
        for label, count in values:
            st.write(f"{label} ({count})")


if __name__ == "__main__":
    main()
