"""Taxonomy definitions for enforcement case analysis.

The dictionaries map stable machine-readable codes to human-readable labels.
Extend these dictionaries as the tracker taxonomy grows.
"""

from __future__ import annotations


TAXONOMY_COLUMNS = [
    "Regulatory Domain",
    "Failure Type",
    "Root Cause Driver",
    "Failure Mechanism",
    "Lifecycle Stage",
    "Outcome Severity",
    "Punishment",
]


TAG_DICTIONARIES: dict[str, dict[str, str]] = {
    "Regulatory Domain": {
        "RD_AML": "Anti-money laundering and financial crime",
        "RD_CONDUCT_GOVERNANCE": "Conduct governance",
        "RD_PRUDENTIAL": "Prudential regulation",
        "RD_MARKET_ABUSE": "Market abuse",
        "RD_CLIENT_ASSETS": "Client assets",
        "RD_DATA_PROTECTION": "Data protection",
        "RD_DISCLOSURE_LISTING": "Disclosure and listing rules",
        "RD_OPERATIONAL_RESILIENCE": "Operational resilience",
        "RD_CONSUMER_DUTY": "Consumer duty and customer outcomes",
        "RD_DISCLOSURE": "Disclosure and reporting",
        "RD_MARKETING_CONSENT": "Marketing consent",
        "RD_REG_REPORTING": "Regulatory reporting",
        "RD_SYSTEMS_CONTROLS": "Systems and controls",
    },
    "Failure Type": {
        "FT_DESIGN": "Control or process design failure",
        "FT_EXECUTION": "Execution failure",
        "FT_GOVERNANCE": "Governance failure",
        "FT_OVERSIGHT": "Oversight or supervision failure",
        "FT_DISCLOSURE": "Disclosure failure",
        "FT_MONITORING": "Monitoring failure",
        "FT_RECORDKEEPING": "Recordkeeping failure",
        "FT_TRAINING": "Training or competence failure",
        "FT_CULTURE": "Culture or incentives failure",
        "FT_INTEGRITY": "Integrity failure",
        "FT_STRATEGIC": "Strategic failure",
    },
    "Root Cause Driver": {
        "RC_DATA_QUALITY": "Poor data quality",
        "RC_KNOWN_RISK": "Known risk not remediated",
        "RC_UNCLEAR_OWNERSHIP": "Unclear ownership or accountability",
        "RC_RESOURCING": "Insufficient resourcing",
        "RC_TECH_DEBT": "Legacy technology or technical debt",
        "RC_POLICY_GAP": "Policy or framework gap",
        "RC_THIRD_PARTY": "Third-party dependency",
        "RC_INCENTIVES": "Misaligned incentives",
        "RC_INCENTIVES_CULTURE": "Incentives or culture weakness",
        "RC_CHANGE_MANAGEMENT": "Poor change management",
        "RC_CONCENTRATED_CONTROL": "Concentrated control or key-person dependency",
        "RC_MANUAL_PROCESS": "Manual process dependency",
        "RC_POOR_DOCUMENTATION": "Poor documentation",
        "RC_REG_UNDERSTANDING": "Poor regulatory understanding",
        "RC_SYSTEM_INTEGRATION": "Poor system integration",
        "RC_WEAK_RISK_FRAMEWORK": "Weak risk management framework",
    },
    "Failure Mechanism": {
        "FM_CDD_FAILURE": "Customer due diligence failure",
        "FM_TRANSACTION_MONITORING_FAILURE": "Transaction monitoring failure",
        "FM_CUSTOMER_RISK_ASSESSMENT_FAILURE": "Customer risk assessment failure",
        "FM_EDD_FAILURE": "Enhanced due diligence failure",
        "FM_INADEQUATE_MI": "Inadequate management information",
        "FM_ESCALATION_FAILURE": "Escalation failure",
        "FM_FAILURE_TO_ESCALATE": "Failure to escalate",
        "FM_POLICY_NOT_IMPLEMENTED": "Policy not implemented",
        "FM_CONTROL_NOT_IMPLEMENTED": "Control not implemented",
        "FM_CONTROL_TESTING_GAP": "Control testing gap",
        "FM_MODEL_OR_RULE_DEFECT": "Model or rule defect",
        "FM_RECORDS_INCOMPLETE": "Incomplete records",
        "FM_RECORDKEEPING_FAILURE": "Recordkeeping failure",
        "FM_COMPLAINT_HANDLING_FAILURE": "Complaint handling failure",
        "FM_OUTSOURCING_CONTROL_FAILURE": "Outsourcing control failure",
        "FM_CONSENT_CAPTURE_FAILURE": "Consent capture failure",
        "FM_DATA_DUPLICATION": "Data duplication",
        "FM_DATA_INACCURACY": "Data inaccuracy",
        "FM_DATA_PROCESSING_ERROR": "Data processing error",
        "FM_INCOMPLETE_DATA_CAPTURE": "Incomplete data capture",
        "FM_MISAPPROPRIATION_OF_FUNDS": "Misappropriation of funds",
        "FM_MISLEADING_REGULATOR": "Misleading the regulator",
        "FM_ONBOARDING_KYC_FAILURE": "Onboarding or KYC failure",
        "FM_REPORTING_MISCONFIGURATION": "Reporting misconfiguration",
        "FM_SURVEILLANCE_FAILURE": "Surveillance failure",
        "FM_UNAUTHORISED_ACTIVITY": "Unauthorised activity",
        "FM_UNLAWFUL_DATA_USAGE": "Unlawful data usage",
    },
    "Lifecycle Stage": {
        "LS_PRODUCT_DESIGN": "Product or control design",
        "LS_ONBOARDING": "Customer onboarding",
        "LS_MONITORING": "Ongoing monitoring",
        "LS_ADVICE_OR_SALE": "Advice or sale",
        "LS_SERVICING": "Customer servicing",
        "LS_REPORTING": "Regulatory reporting",
        "LS_REMEDIATION": "Remediation",
        "LS_GOVERNANCE_REVIEW": "Governance review",
        "LS_CUSTOMER_COMMUNICATION": "Customer communication",
        "LS_DATA_PROCESSING": "Data processing",
        "LS_GOVERNANCE_OVERSIGHT": "Governance and oversight",
    },
    "Outcome Severity": {
        "OS_LOW": "Low severity",
        "OS_MEDIUM": "Medium severity",
        "OS_HIGH": "High severity",
        "OS_VERY_HIGH": "Very high severity",
        "OS_SYSTEMIC": "Systemic severity",
        "OS_ACTUAL_FINANCIAL_LOSS": "Actual financial loss",
        "OS_FINANCIAL_CRIME_FACILITATED": "Financial crime facilitated",
        "OS_MARKET_INTEGRITY_IMPACT": "Market integrity impact",
        "OS_NO_REALISED_HARM": "No realised harm",
        "OS_POTENTIAL_CONSUMER_DETRIMENT": "Potential consumer detriment",
    },
    "Punishment": {
        "P_FINE": "Financial penalty",
        "P_PUBLIC_CENSURE": "Public censure",
        "P_RESTITUTION": "Restitution or redress",
        "P_BUSINESS_RESTRICTION": "Business restriction",
        "P_AUTH_WITHDRAWAL": "Authorisation withdrawal",
        "P_INDIVIDUAL_BAN": "Individual prohibition or ban",
        "P_REQUIREMENTS": "Regulatory requirements imposed",
        "P_NO_ACTION": "No formal penalty",
        "ENF_FINANCIAL_PENALTY": "Financial penalty",
        "ENF_INDIVIDUAL_SANCTION": "Individual sanction",
        "ENF_LEGAL_ACTION": "Legal action",
        "ENF_PERMISSION_REVOKED": "Permission revoked",
        "ENF_PUBLIC_CENSURE": "Public censure",
        "ENF_PUBLIC_SANCTION": "Public sanction",
        "ENF_REGULATORY_NOTICE": "Regulatory notice",
        "ENF_REMEDIATION": "Remediation required",
        "ENF_RESTRICTION_IMPOSED": "Restriction imposed",
    },
}


def get_label(column: str, code: str) -> str:
    """Return a readable label for a taxonomy code, falling back to the code."""
    return TAG_DICTIONARIES.get(column, {}).get(code, code)


def unknown_codes_by_column(observed_codes: dict[str, set[str]]) -> dict[str, set[str]]:
    """Identify observed taxonomy codes that are not defined in TAG_DICTIONARIES."""
    unknown: dict[str, set[str]] = {}
    for column, codes in observed_codes.items():
        known = set(TAG_DICTIONARIES.get(column, {}))
        missing = set(codes) - known
        if missing:
            unknown[column] = missing
    return unknown
