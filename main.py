"""Example backend workflow for the enforcement case analysis tool."""

from __future__ import annotations

from pathlib import Path

from case_analysis.charts import (
    plot_cases_by_year,
    plot_cooccurrence_heatmap,
    plot_count_bar,
    save_figure,
)
from case_analysis.clusters import export_cluster_outputs
from case_analysis.filters import filter_cases
from case_analysis.loader import DEFAULT_DATA_PATH, load_cases
from case_analysis.normalise import (
    add_tag_list_columns,
    collect_observed_codes,
    filter_cases_by_tags,
    normalise_tags_long,
    summary_counts,
)
from case_analysis.similarity import find_similar_cases
from case_analysis.taxonomy import unknown_codes_by_column


def main() -> None:
    data_path = DEFAULT_DATA_PATH
    if not Path(data_path).exists():
        print(f"Case database file not found at {data_path}")
        print("Place your tracker there, then run: python main.py")
        return

    cases = load_cases(data_path)
    cases_with_tags = add_tag_list_columns(cases)
    tags_long = normalise_tags_long(cases)

    print(f"Loaded {len(cases)} cases")
    print(f"Normalised {len(tags_long)} case/tag rows")

    unknown_codes = unknown_codes_by_column(collect_observed_codes(cases))
    if unknown_codes:
        print("\nUnknown taxonomy codes found:")
        for column, codes in unknown_codes.items():
            print(f"- {column}: {', '.join(sorted(codes))}")

    print("\nCases by agency:")
    print(summary_counts(cases, "Agency", normalise_taxonomy=False).to_string(index=False))

    print("\nTop regulatory domains:")
    print(summary_counts(cases, "Regulatory Domain").head(10).to_string(index=False))

    filtered = filter_cases_by_tags(
        cases,
        {
            "Regulatory Domain": ["RD_AML"],
            "Failure Mechanism": ["FM_CDD_FAILURE", "FM_TRANSACTION_MONITORING_FAILURE"],
        },
        match="any",
    )
    print(f"\nExample filter returned {len(filtered)} AML/CDD/transaction-monitoring related cases")

    metadata_and_tag_filtered = filter_cases(
        cases,
        agency=["FCA"],
        selected_tags={
            "Outcome Severity": [
                "OS_ACTUAL_FINANCIAL_LOSS",
                "OS_FINANCIAL_CRIME_FACILITATED",
                "OS_MARKET_INTEGRITY_IMPACT",
                "OS_POTENTIAL_CONSUMER_DETRIMENT",
            ]
        },
        tag_match="any",
    )
    print(
        "\nExample FCA material-impact filter returned "
        f"{len(metadata_and_tag_filtered)} cases"
    )

    if not cases_with_tags.empty:
        example_case_id = str(cases_with_tags.iloc[0]["Case ID"])
        similar = find_similar_cases(cases_with_tags, example_case_id, top_n=5)
        print(f"\nMost similar cases to {example_case_id}:")
        if similar.empty:
            print("No overlapping taxonomy tags found.")
        else:
            print(similar.to_string(index=False))

    try:
        chart_dir = Path("outputs/charts")
        saved_charts = [
            save_figure(
                plot_count_bar(cases, "Regulatory Domain", title="Top Regulatory Domains"),
                chart_dir / "regulatory_domains.png",
            ),
            save_figure(
                plot_count_bar(cases, "Failure Type", title="Top Failure Types"),
                chart_dir / "failure_types.png",
            ),
            save_figure(
                plot_cases_by_year(cases),
                chart_dir / "cases_by_year.png",
            ),
            save_figure(
                plot_cooccurrence_heatmap(
                    cases,
                    "Regulatory Domain",
                    "Failure Type",
                    top_rows=8,
                    top_columns=8,
                    title="Regulatory Domain vs Failure Type",
                ),
                chart_dir / "regulatory_domain_vs_failure_type.png",
            ),
            save_figure(
                plot_cooccurrence_heatmap(
                    cases,
                    "Issue cause",
                    "Failure Type",
                    top_rows=10,
                    top_columns=8,
                    title="Issue Cause vs Failure Type",
                ),
                chart_dir / "issue_cause_vs_failure_type.png",
            ),
        ]
    except ModuleNotFoundError as exc:
        print(f"\nCharts skipped: {exc}")
    else:
        print("\nSaved charts:")
        for path in saved_charts:
            print(f"- {path}")

    cluster_paths = export_cluster_outputs(cases)
    print("\nSaved cluster outputs:")
    for path in cluster_paths.values():
        print(f"- {path}")


if __name__ == "__main__":
    main()
