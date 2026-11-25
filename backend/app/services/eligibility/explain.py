"""SchemeSaathi AI — Plain-language eligibility explanations.

Turns the structured evaluation result into human-readable text.
Never says "guaranteed" or "approved".
"""

# ── Field labels ─────────────────────────────────────────────────

FIELD_LABELS = {
    "age": "Age",
    "gender": "Gender",
    "state": "State of residence",
    "district": "District",
    "category": "Social category",
    "religion": "Religion",
    "occupation": "Occupation",
    "education_level": "Education level",
    "annual_income": "Annual household income",
    "is_bpl": "Below Poverty Line (BPL) status",
    "is_minority": "Minority community status",
    "is_differently_abled": "Differently abled status",
    "marital_status": "Marital status",
    "num_dependents": "Number of dependents",
    "land_holding_acres": "Land holding",
    "has_bank_account": "Bank account",
}

CMP_PHRASES = {
    "eq": "must be",
    "neq": "must not be",
    "gt": "must be greater than",
    "gte": "must be at least",
    "lt": "must be less than",
    "lte": "must not exceed",
    "in": "must be one of",
    "between": "must be between",
}


# ── Value formatting ─────────────────────────────────────────────


def _fmt(field, value):
    """Format a single value for display."""
    if value is None:
        return "not provided"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if field == "annual_income" and isinstance(value, (int, float)):
        return f"₹{int(value):,}"
    if field == "land_holding_acres" and isinstance(value, (int, float)):
        return f"{value:.1f} acres"
    return str(value)


def _fmt_expected(field, cmp, value):
    """Format the expected/rule value."""
    if cmp == "between" and isinstance(value, (list, tuple)):
        return f"{_fmt(field, value[0])} and {_fmt(field, value[1])}"
    if cmp == "in" and isinstance(value, list):
        return ", ".join(_fmt(field, v) for v in value)
    return _fmt(field, value)


# ── Explanation generators ───────────────────────────────────────


def explain_leaf(detail):
    """Return a one-line human-readable explanation for one evaluated rule."""
    field = detail["field"]
    cmp = detail["cmp"]
    expected = detail["expected"]
    actual = detail["actual"]
    result = detail["result"]
    mandatory = detail.get("mandatory", False)

    label = FIELD_LABELS.get(field, field.replace("_", " ").title())
    phrase = CMP_PHRASES.get(cmp, cmp)
    exp_str = _fmt_expected(field, cmp, expected)
    act_str = _fmt(field, actual)
    req_tag = " (required)" if mandatory else ""

    if result == "UNKNOWN":
        return f"⚠ {label}{req_tag}: Information not provided. Please update your profile."
    if result == "TRUE":
        return f"✓ {label}{req_tag}: Your value ({act_str}) meets the requirement ({phrase} {exp_str})."
    # FALSE
    return f"✗ {label}{req_tag}: Your value ({act_str}) does not meet the requirement ({phrase} {exp_str})."


def build_explanation(check_result):
    """Build a full explanation from a ``check_eligibility`` result dict.

    Returns a dict with 'summary' (str) and 'details' (list[str]).
    """
    status = check_result["status"]
    label = check_result["status_label"]

    if status == "green":
        summary = (
            f"Based on the information you provided, you appear to be "
            f"potentially eligible for this scheme. This is not a guarantee — "
            f"please verify with the official department."
        )
    elif status == "amber":
        n_missing = len(check_result["missing"])
        summary = (
            f"We could not determine full eligibility because "
            f"{n_missing} piece(s) of information are missing or "
            f"some non-mandatory criteria were not met. "
            f"Please complete your profile for a more accurate result."
        )
    else:  # red
        n_failed = sum(
            1 for d in check_result["not_met"] if d.get("mandatory")
        )
        summary = (
            f"Based on the details you provided, you do not appear to meet "
            f"{n_failed} mandatory requirement(s) for this scheme. "
            f"If you believe this is incorrect, please verify your profile "
            f"details or contact the concerned department."
        )

    details = []
    for d in check_result["met"]:
        details.append(explain_leaf(d))
    for d in check_result["not_met"]:
        details.append(explain_leaf(d))
    for d in check_result["missing"]:
        details.append(explain_leaf(d))

    return {
        "summary": summary,
        "status": status,
        "status_label": label,
        "details": details,
    }
