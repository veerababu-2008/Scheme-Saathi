"""SchemeSaathi AI — Deterministic eligibility rule engine.

Evaluates a JSON rule tree against a user profile dict.
No LLM is used — results are fully auditable.

Rule tree format
────────────────
Branch node:  {"op": "AND"|"OR", "rules": [...children...]}
Leaf node:    {"field": "age", "cmp": "gte", "value": 18,
               "mandatory": true, "source_id": 3}

Three-valued logic
──────────────────
Leaf:   TRUE (match) | FALSE (mismatch) | UNKNOWN (field missing)
AND:    any FALSE → FALSE,  else any UNKNOWN → UNKNOWN,  else TRUE
OR:     any TRUE  → TRUE,   else any UNKNOWN → UNKNOWN,  else FALSE

Status mapping
──────────────
GREEN  "Potentially Eligible"                   top-level TRUE
AMBER  "Needs Verification"                     top-level UNKNOWN
                                                 or top-level FALSE with no mandatory FALSE
RED    "Not Eligible Based on Provided Details"  top-level FALSE with ≥1 mandatory FALSE
"""

from app.services.eligibility.operators import evaluate_operator

# ── Result constants ─────────────────────────────────────────────

TRUE = "TRUE"
FALSE = "FALSE"
UNKNOWN = "UNKNOWN"

STATUS_GREEN = "green"
STATUS_AMBER = "amber"
STATUS_RED = "red"

STATUS_LABELS = {
    STATUS_GREEN: "Potentially Eligible",
    STATUS_AMBER: "Needs Verification",
    STATUS_RED: "Not Eligible Based on Provided Details",
}


# ── Profile builder ──────────────────────────────────────────────


def build_profile_dict(profile):
    """Extract eligibility-relevant fields from a UserProfile model.

    Returns a flat dict.  ``None`` values are included so the engine
    can distinguish "provided but None" from "field not in dict" (both
    treated as UNKNOWN).
    """
    if profile is None:
        return {}
    return {
        "age": profile.age,
        "gender": profile.gender,
        "state": profile.state,
        "district": profile.district,
        "category": profile.category,
        "religion": profile.religion,
        "occupation": profile.occupation,
        "education_level": profile.education_level,
        "annual_income": profile.annual_income,
        "is_bpl": profile.is_bpl,
        "is_minority": profile.is_minority,
        "is_differently_abled": profile.is_differently_abled,
        "marital_status": profile.marital_status,
        "num_dependents": profile.num_dependents,
        "land_holding_acres": profile.land_holding_acres,
        "has_bank_account": profile.has_bank_account,
    }


# ── Tree evaluator ───────────────────────────────────────────────


def _evaluate_node(node, profile):
    """Recursively evaluate one node.

    Returns ``(result, leaf_details)`` where *result* is one of
    ``TRUE``, ``FALSE``, ``UNKNOWN`` and *leaf_details* is a list of
    per-leaf dicts describing the evaluation.
    """
    if "op" in node:
        return _evaluate_branch(node, profile)
    return _evaluate_leaf(node, profile)


def _evaluate_branch(node, profile):
    op = node["op"].upper()
    child_results = []
    all_details = []

    for child in node.get("rules", []):
        result, details = _evaluate_node(child, profile)
        child_results.append(result)
        all_details.extend(details)

    if op == "AND":
        if FALSE in child_results:
            combined = FALSE
        elif UNKNOWN in child_results:
            combined = UNKNOWN
        else:
            combined = TRUE
    elif op == "OR":
        if TRUE in child_results:
            combined = TRUE
        elif UNKNOWN in child_results:
            combined = UNKNOWN
        else:
            combined = FALSE
    else:
        combined = UNKNOWN  # unknown operator — safe fallback

    return combined, all_details


def _evaluate_leaf(node, profile):
    field = node["field"]
    cmp = node["cmp"]
    rule_value = node["value"]
    mandatory = node.get("mandatory", False)
    source_id = node.get("source_id")

    profile_value = profile.get(field)

    if profile_value is None:
        result = UNKNOWN
    else:
        try:
            passed = evaluate_operator(cmp, profile_value, rule_value)
            result = TRUE if passed else FALSE
        except (ValueError, TypeError, IndexError):
            result = FALSE

    detail = {
        "field": field,
        "cmp": cmp,
        "expected": rule_value,
        "actual": profile_value,
        "mandatory": mandatory,
        "result": result,
        "source_id": source_id,
    }
    return result, [detail]


# ── Public API ───────────────────────────────────────────────────


def check_eligibility(rules_json, profile_data):
    """Evaluate *rules_json* against *profile_data* and return a result dict.

    Parameters
    ----------
    rules_json : dict
        Root node of the eligibility rule tree (from ``EligibilityRule.rules_json``).
    profile_data : dict
        Flat dict of profile fields (from ``build_profile_dict``).

    Returns
    -------
    dict with keys: status, status_label, met, not_met, missing
    """
    if not rules_json or not rules_json.get("rules"):
        return {
            "status": STATUS_GREEN,
            "status_label": STATUS_LABELS[STATUS_GREEN],
            "met": [],
            "not_met": [],
            "missing": [],
        }

    combined, details = _evaluate_node(rules_json, profile_data)

    met = [d for d in details if d["result"] == TRUE]
    not_met = [d for d in details if d["result"] == FALSE]
    missing = [d for d in details if d["result"] == UNKNOWN]

    has_mandatory_false = any(d["mandatory"] for d in not_met)

    if combined == TRUE:
        status = STATUS_GREEN
    elif combined == UNKNOWN:
        status = STATUS_AMBER
    elif has_mandatory_false:
        status = STATUS_RED
    else:
        status = STATUS_AMBER

    return {
        "status": status,
        "status_label": STATUS_LABELS[status],
        "met": met,
        "not_met": not_met,
        "missing": missing,
    }
