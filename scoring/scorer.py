from scoring.taxonomy import FEATURE_TAXONOMY
from scoring.weights import FEATURE_DIM_WEIGHTS


def feature_val(field: str, raw_value) -> float:
    """Map a raw extracted value to 0.0 / 0.5 / 1.0."""
    if raw_value is None:
        return 0.0

    meta = FEATURE_TAXONOMY.get(field, {})
    ftype = meta.get("type", "str")

    if ftype == "bool":
        return 1.0 if raw_value else 0.0

    if ftype in ("int", "float"):
        return _score_numeric(field, raw_value)

    if ftype == "list":
        return 1.0 if raw_value else 0.0

    if ftype == "enum":
        return 1.0 if raw_value else 0.0

    if ftype in ("int_or_str", "float_or_str"):
        if raw_value == "no_limit" or raw_value == "whole_life" or raw_value == "unlimited":
            return 1.0
        try:
            return _score_numeric(field, float(raw_value))
        except (TypeError, ValueError):
            return 0.5

    # str / unknown
    return 1.0 if raw_value else 0.0


def _score_numeric(field: str, value: float) -> float:
    """Heuristic normalisation per field."""
    charge_fields = {
        "premium_allocation_charge_pct",
        "fund_management_charge_pct",
        "policy_admin_charge_monthly",
    }
    if field in charge_fields:
        # Lower charge → better
        if value <= 0:
            return 1.0
        if value <= 2.0:
            return 0.8
        if value <= 5.0:
            return 0.5
        return 0.2

    field_lower = field.lower()
    if "min" in field_lower:
        # Lower minimum → more accessible → better
        return 1.0 if value <= 0 else max(0.2, 1.0 - value / 100)

    if "max" in field_lower:
        # Higher maximum → better (open-ended)
        return 1.0 if value >= 99 else min(1.0, value / 30)

    if field == "ci_illnesses_covered":
        if value >= 40:
            return 1.0
        if value >= 20:
            return 0.5
        return 0.2 if value > 0 else 0.0

    if "irr" in field_lower or "pct" in field_lower or "percentage" in field_lower:
        return min(1.0, value / 15)

    if field == "claim_settlement_ratio":
        return min(1.0, value / 100)

    return 1.0 if value > 0 else 0.0


def passes_hard_filters(features: dict, hard_filters: dict) -> bool:
    for field, expected in hard_filters.items():
        if field == "guaranteed_returns_exclude":
            if features.get("guaranteed_returns"):
                return False
            continue
        if field == "premium_pay_modes_includes":
            modes = features.get("premium_pay_modes") or []
            if isinstance(modes, str):
                modes = [modes]
            if expected not in modes:
                return False
            continue
        if field == "max_policy_term_gte":
            val = features.get("max_policy_term")
            if val is None:
                return False
            try:
                if float(val) < expected:
                    return False
            except (TypeError, ValueError):
                pass
            continue
        actual = features.get(field)
        if actual != expected:
            return False
    return True


def score_product(features: dict, profile: dict) -> dict:
    """
    Returns:
      total_score (0-100), dimension_scores, feature_scores,
      matched_features, missing_features
    """
    hard_filters = profile.get("hard_filters", {})
    if not passes_hard_filters(features, hard_filters):
        return None  # hard filter fail — exclude

    effective_weights = profile.get("feature_weights", {})

    feature_scores: dict[str, float] = {}
    for feat, w in effective_weights.items():
        raw = features.get(feat)
        val = feature_val(feat, raw)
        feature_scores[feat] = val * w

    total = sum(feature_scores.values()) * 100

    # Per-dimension breakdown
    dimension_scores: dict[str, float] = {}
    for dim, feat_map in FEATURE_DIM_WEIGHTS.items():
        dim_total = sum(
            feature_scores.get(f, 0.0)
            for f in feat_map
        )
        dimension_scores[dim] = round(dim_total * 100, 2)

    # Top features the product has vs is missing
    matched = [
        f for f, w in effective_weights.items()
        if feature_val(f, features.get(f)) >= 0.8 and w > 0.005
    ]
    missing = [
        f for f, w in effective_weights.items()
        if feature_val(f, features.get(f)) == 0.0 and w > 0.01
    ]

    # Sort matched by contribution descending
    matched.sort(key=lambda f: feature_scores.get(f, 0), reverse=True)
    missing.sort(key=lambda f: effective_weights.get(f, 0), reverse=True)

    return {
        "total_score": round(total, 2),
        "dimension_scores": dimension_scores,
        "feature_scores": {k: round(v * 100, 4) for k, v in feature_scores.items()},
        "matched_features": matched[:10],
        "missing_features": missing[:10],
        "product_name": features.get("product_name") or features.get("_meta", {}).get("product_name", ""),
        "company": features.get("insurer") or features.get("_meta", {}).get("company", ""),
        "insurance_type": features.get("product_type") or features.get("_meta", {}).get("insurance_type", ""),
    }
