"""SchemeSaathi AI — Recommendation scorer.

Deterministic, explainable scoring engine that ranks schemes
for a user based on profile match, category affinity, location
relevance, freshness, and benefit amount.

NOT a trained model — purely heuristic. Each score component is
in [0.0, 1.0]; the final score is a weighted sum.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from app.services.eligibility.engine import (
    build_profile_dict,
    check_eligibility,
    STATUS_GREEN,
    STATUS_AMBER,
    STATUS_RED,
)
from app.services.recommendation.weights import (
    W_PROFILE,
    W_CATEGORY,
    W_LOCATION,
    W_FRESHNESS,
    W_BENEFIT,
    OCCUPATION_CATEGORIES,
    CATEGORY_FROM_PROFILE,
    EDUCATION_CATEGORIES,
    FRESHNESS_DECAY_DAYS,
    FRESHNESS_MIN_SCORE,
    BENEFIT_CAP,
)


# ── Component scorers ────────────────────────────────────────────


def _profile_score(eligibility_result: dict) -> tuple[float, str]:
    """Score based on eligibility rule match ratio.

    Returns (score, reason).
    """
    met = len(eligibility_result.get("met", []))
    not_met = len(eligibility_result.get("not_met", []))
    missing = len(eligibility_result.get("missing", []))
    total = met + not_met + missing

    if total == 0:
        return 1.0, "No specific eligibility criteria"

    status = eligibility_result["status"]
    if status == STATUS_GREEN:
        score = 0.8 + 0.2 * (met / total)
        return score, f"Meets all {met} checked criteria"
    elif status == STATUS_AMBER:
        score = 0.4 + 0.4 * (met / total)
        reason_parts = []
        if met:
            reason_parts.append(f"meets {met} criteria")
        if missing:
            reason_parts.append(f"{missing} need verification")
        return score, "; ".join(reason_parts) or "Some criteria need verification"
    else:  # RED
        score = 0.1 * (met / total) if met else 0.0
        return score, f"Does not meet {not_met} mandatory criteria"


def _category_score(
    scheme_categories: list[str],
    user_categories: set[str],
) -> tuple[float, str]:
    """Score based on overlap between scheme categories and user affinities.

    Returns (score, reason).
    """
    if not scheme_categories or not user_categories:
        return 0.3, "General scheme"

    overlap = set(scheme_categories) & user_categories
    if overlap:
        score = min(1.0, 0.5 + 0.5 * len(overlap) / len(scheme_categories))
        cats = ", ".join(sorted(overlap))
        return score, f"Matches your profile: {cats}"

    return 0.2, "Different category"


def _location_score(
    scheme_level: str,
    scheme_state: Optional[str],
    user_state: Optional[str],
) -> tuple[float, str]:
    """Score based on geographic relevance.

    Returns (score, reason).
    """
    if scheme_level == "central":
        return 0.8, "Available nationwide"

    if scheme_state and user_state:
        if scheme_state.lower() == user_state.lower():
            return 1.0, f"Available in your state ({scheme_state})"
        else:
            return 0.0, f"Only available in {scheme_state}"

    if scheme_state and not user_state:
        return 0.3, f"State scheme ({scheme_state}) — update your profile"

    return 0.5, "Location relevance unknown"


def _freshness_score(
    last_verified_at: Optional[datetime],
) -> tuple[float, str]:
    """Score based on recency of verification.

    Returns (score, reason).
    """
    if not last_verified_at:
        return FRESHNESS_MIN_SCORE, "Verification date pending"

    now = datetime.now(timezone.utc)
    if last_verified_at.tzinfo is None:
        last_verified_at = last_verified_at.replace(tzinfo=timezone.utc)

    days_ago = (now - last_verified_at).days
    if days_ago <= 0:
        return 1.0, "Verified today"

    score = max(
        FRESHNESS_MIN_SCORE,
        1.0 - (days_ago / FRESHNESS_DECAY_DAYS),
    )
    if days_ago <= 30:
        return score, "Recently verified"
    elif days_ago <= 180:
        return score, f"Verified {days_ago} days ago"
    else:
        return score, "Needs re-verification"


def _benefit_score(
    max_benefit_amount: Optional[int],
) -> tuple[float, str]:
    """Score based on benefit amount.

    Returns (score, reason).
    """
    if not max_benefit_amount:
        return 0.5, "Benefit amount varies"

    score = min(1.0, max_benefit_amount / BENEFIT_CAP)
    if max_benefit_amount >= 100000:
        return score, f"Up to ₹{max_benefit_amount:,}"
    elif max_benefit_amount >= 10000:
        return score, f"Up to ₹{max_benefit_amount:,}"
    else:
        return score, f"₹{max_benefit_amount:,} benefit"


# ── User category builder ───────────────────────────────────────


def _build_user_categories(profile_data: dict) -> set[str]:
    """Derive scheme category affinities from user profile data."""
    cats: set[str] = set()

    occupation = profile_data.get("occupation")
    if occupation and occupation in OCCUPATION_CATEGORIES:
        cats.update(OCCUPATION_CATEGORIES[occupation])

    education = profile_data.get("education_level")
    if education and education in EDUCATION_CATEGORIES:
        cats.update(EDUCATION_CATEGORIES[education])

    for field, categories in CATEGORY_FROM_PROFILE.items():
        if profile_data.get(field):
            cats.update(categories)

    if profile_data.get("gender") == "female":
        cats.add("women")

    if profile_data.get("age") and profile_data["age"] >= 57:
        cats.add("pension")

    return cats


# ── Main scorer ──────────────────────────────────────────────────


def score_scheme(scheme, profile_data: dict) -> dict:
    """Score a single scheme for a user profile.

    Parameters
    ----------
    scheme : Scheme model
        The scheme to score.
    profile_data : dict
        Flat profile dict from ``build_profile_dict()``.

    Returns
    -------
    dict with keys: scheme_id, total_score, status, components, reasons
    """
    # 1. Run eligibility
    active_rule = scheme.active_rules
    rules_json = active_rule.rules_json if active_rule else None
    eligibility = check_eligibility(rules_json, profile_data)

    # 2. Component scores
    p_score, p_reason = _profile_score(eligibility)

    scheme_cats = [c.category for c in scheme.categories]
    user_cats = _build_user_categories(profile_data)
    c_score, c_reason = _category_score(scheme_cats, user_cats)

    l_score, l_reason = _location_score(
        scheme.level, scheme.state, profile_data.get("state")
    )

    f_score, f_reason = _freshness_score(scheme.last_verified_at)

    b_score, b_reason = _benefit_score(scheme.max_benefit_amount)

    # 3. Weighted total
    total = (
        W_PROFILE * p_score
        + W_CATEGORY * c_score
        + W_LOCATION * l_score
        + W_FRESHNESS * f_score
        + W_BENEFIT * b_score
    )

    # 4. Build reasons list (top reasons why recommended)
    components = [
        ("profile_match", p_score, p_reason, W_PROFILE),
        ("category_affinity", c_score, c_reason, W_CATEGORY),
        ("location_relevance", l_score, l_reason, W_LOCATION),
        ("freshness", f_score, f_reason, W_FRESHNESS),
        ("benefit_value", b_score, b_reason, W_BENEFIT),
    ]
    # Sort by weighted contribution (descending)
    components.sort(key=lambda x: x[1] * x[3], reverse=True)

    reasons = [
        reason for _, score, reason, _ in components
        if score >= 0.5
    ][:3]  # Top 3 positive reasons

    return {
        "scheme_id": scheme.id,
        "total_score": round(total, 4),
        "eligibility_status": eligibility["status"],
        "eligibility_label": eligibility["status_label"],
        "components": {
            name: {"score": round(sc, 4), "reason": reason}
            for name, sc, reason, _ in components
        },
        "reasons": reasons,
    }


def rank_schemes(
    schemes,
    profile_data: dict,
    *,
    exclude_red: bool = False,
    limit: Optional[int] = None,
) -> list[dict]:
    """Score and rank a list of schemes for a user.

    Parameters
    ----------
    schemes : list[Scheme]
        Candidate schemes.
    profile_data : dict
        From ``build_profile_dict()``.
    exclude_red : bool
        If True, RED (ineligible) schemes are removed entirely.
        If False, they are sorted to the bottom.
    limit : int, optional
        Max results to return.

    Returns
    -------
    list[dict] — scored schemes, sorted best-first.
    """
    scored = [score_scheme(s, profile_data) for s in schemes]

    if exclude_red:
        scored = [s for s in scored if s["eligibility_status"] != STATUS_RED]

    # Sort: RED last, then by total_score descending
    status_order = {STATUS_GREEN: 0, STATUS_AMBER: 1, STATUS_RED: 2}
    scored.sort(
        key=lambda s: (
            status_order.get(s["eligibility_status"], 3),
            -s["total_score"],
        )
    )

    if limit:
        scored = scored[:limit]

    return scored
