"""SchemeSaathi AI — Eligibility comparator operators.

Each function takes (profile_value, rule_value) and returns bool.
The engine handles UNKNOWN (missing profile data) before calling these.
"""


def op_eq(profile_value, rule_value):
    """Exact equality (works for str, int, float, bool)."""
    return profile_value == rule_value


def op_neq(profile_value, rule_value):
    """Not equal."""
    return profile_value != rule_value


def op_gt(profile_value, rule_value):
    """Strictly greater than (numeric)."""
    return float(profile_value) > float(rule_value)


def op_gte(profile_value, rule_value):
    """Greater than or equal (numeric)."""
    return float(profile_value) >= float(rule_value)


def op_lt(profile_value, rule_value):
    """Strictly less than (numeric)."""
    return float(profile_value) < float(rule_value)


def op_lte(profile_value, rule_value):
    """Less than or equal (numeric)."""
    return float(profile_value) <= float(rule_value)


def op_in(profile_value, rule_value):
    """Profile value is a member of the rule's list."""
    return profile_value in rule_value


def op_between(profile_value, rule_value):
    """Profile value falls within [low, high] inclusive."""
    low, high = float(rule_value[0]), float(rule_value[1])
    return low <= float(profile_value) <= high


# ── Operator registry ────────────────────────────────────────────

OPERATORS = {
    "eq": op_eq,
    "neq": op_neq,
    "gt": op_gt,
    "gte": op_gte,
    "lt": op_lt,
    "lte": op_lte,
    "in": op_in,
    "between": op_between,
}


def evaluate_operator(cmp, profile_value, rule_value):
    """Dispatch to the right operator.  Raises ValueError for unknowns."""
    fn = OPERATORS.get(cmp)
    if fn is None:
        raise ValueError(f"Unknown comparator: {cmp}")
    return fn(profile_value, rule_value)
