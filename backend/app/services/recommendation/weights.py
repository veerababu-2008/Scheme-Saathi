"""SchemeSaathi AI — Recommendation weight constants.

Scoring formula (all weights sum to 1.0):
  total = (W_PROFILE * profile_score)
        + (W_CATEGORY * category_score)
        + (W_LOCATION * location_score)
        + (W_FRESHNESS * freshness_score)
        + (W_BENEFIT * benefit_score)

Each component score is in [0.0, 1.0].

NOT a trained model — these are hand-tuned heuristic weights.
Adjust here to rebalance; no retraining required.
"""

# ── Core weights (must sum to 1.0) ───────────────────────────────

W_PROFILE = 0.35       # Eligibility profile match
W_CATEGORY = 0.25      # Category affinity to user's occupation/profile
W_LOCATION = 0.20      # State/central relevance
W_FRESHNESS = 0.10     # Recently verified schemes rank higher
W_BENEFIT = 0.10       # Higher benefit amounts rank higher

assert abs(W_PROFILE + W_CATEGORY + W_LOCATION + W_FRESHNESS + W_BENEFIT - 1.0) < 1e-9

# ── Category affinity map ────────────────────────────────────────
# Maps profile field values → relevant scheme categories.

OCCUPATION_CATEGORIES = {
    "farmer": ["agriculture"],
    "agri_labour": ["agriculture", "employment"],
    "student": ["education"],
    "teacher": ["education"],
    "self_employed": ["employment", "startup"],
    "street_vendor": ["employment", "startup"],
    "hawker": ["employment", "startup"],
    "daily_wage": ["employment", "social_security"],
    "salaried": ["employment"],
    "homemaker": ["women", "social_security"],
    "retired": ["pension", "social_security"],
    "unemployed": ["employment", "social_security"],
}

CATEGORY_FROM_PROFILE = {
    "is_bpl": ["housing", "social_security", "health"],
    "is_differently_abled": ["social_security", "health"],
    "is_minority": ["minority", "education"],
}

EDUCATION_CATEGORIES = {
    "higher_secondary": ["education"],
    "diploma": ["education"],
    "graduate": ["education"],
    "post_graduate": ["education"],
    "doctorate": ["education"],
}

# ── Freshness decay ─────────────────────────────────────────────

FRESHNESS_DECAY_DAYS = 365    # Schemes verified within this many days get max score
FRESHNESS_MIN_SCORE = 0.3     # Floor score for schemes with no verification date

# ── Benefit normalisation ────────────────────────────────────────

BENEFIT_CAP = 500_000         # Amounts above this all get score 1.0
