from scoring.weights import PROFILE_MULTIPLIERS, DIMENSION_WEIGHTS, FEATURE_DIM_WEIGHTS, HARD_FILTER_RULES


VALID_GOALS       = {"protect_family", "wealth_growth", "retirement", "child_future"}
VALID_RISK        = {"conservative", "moderate", "aggressive", "capital_safe"}
VALID_HORIZON     = {"under_5", "5_to_10", "10_to_20", "20_plus"}
VALID_DEPENDENTS  = {"spouse", "children", "parents", "none"}
VALID_LIQUIDITY   = {"anytime", "after_5_years", "none"}
VALID_HEALTH_RISK = {"critical_illness", "accident", "both", "neither"}
VALID_PAY_MODE    = {"single", "limited", "regular", "monthly"}
VALID_MATURITY    = {"rop", "income", "lump_sum", "legacy"}


def map_profile(answers: dict) -> dict:
    goal        = answers.get("q1_goal", "protect_family")
    risk        = answers.get("q2_risk", "moderate")
    horizon     = answers.get("q3_horizon", "10_to_20")
    dependents  = answers.get("q4_dependents", [])
    liquidity   = answers.get("q5_liquidity", "none")
    health_risk = answers.get("q6_health_risk", [])
    pay_mode    = answers.get("q7_pay_mode", "regular")
    maturity    = answers.get("q8_maturity", "lump_sum")

    if isinstance(dependents, str):
        dependents = [dependents]
    if isinstance(health_risk, str):
        health_risk = [health_risk]

    hard_filters = _build_hard_filters(risk, maturity, pay_mode, horizon)
    product_type_filter = _infer_product_types(goal, risk)
    weights = _compute_weights(goal, risk, dependents, liquidity, health_risk, maturity)
    label = _build_label(goal, risk, horizon, dependents)

    return {
        "answers": answers,
        "goal": goal,
        "risk": risk,
        "horizon": horizon,
        "dependents": dependents,
        "liquidity": liquidity,
        "health_risk": health_risk,
        "pay_mode": pay_mode,
        "maturity": maturity,
        "hard_filters": hard_filters,
        "product_type_filter": product_type_filter,
        "feature_weights": weights,
        "profile_label": label,
    }


def _build_hard_filters(risk: str, maturity: str, pay_mode: str, horizon: str) -> dict:
    filters = {}

    if risk == "conservative":
        filters["is_linked"] = False
    if risk == "aggressive":
        filters["guaranteed_returns_exclude"] = True

    if maturity == "rop":
        filters["return_of_premium"] = True
    if maturity == "income":
        filters["income_payout_option"] = True

    if pay_mode == "single":
        filters["premium_pay_modes_includes"] = "single"
    elif pay_mode == "monthly":
        filters["premium_pay_modes_includes"] = "regular"

    if horizon == "under_5":
        filters["max_policy_term_gte"] = 5

    return filters


def _infer_product_types(goal: str, risk: str) -> list[str]:
    if goal == "protect_family":
        return ["term"]
    if goal == "wealth_growth":
        return ["ulip"] if risk in ("aggressive", "moderate") else ["savings"]
    if goal == "retirement":
        return ["savings", "annuity"]
    if goal == "child_future":
        return ["child", "ulip", "savings"]
    return []


def _compute_weights(
    goal: str,
    risk: str,
    dependents: list,
    liquidity: str,
    health_risk: list,
    maturity: str,
) -> dict:
    effective: dict[str, float] = {}

    # Flatten FEATURE_DIM_WEIGHTS into per-feature base weights
    for dim, feat_map in FEATURE_DIM_WEIGHTS.items():
        dim_w = DIMENSION_WEIGHTS.get(dim, 0.0)
        for feat, feat_w in feat_map.items():
            effective[feat] = dim_w * feat_w

    # Apply goal multiplier (on dimension level)
    goal_mult = PROFILE_MULTIPLIERS["goal"].get(goal, {})
    for dim, mult in goal_mult.items():
        for feat in FEATURE_DIM_WEIGHTS.get(dim, {}):
            effective[feat] = effective.get(feat, 0.0) * mult

    # Apply risk multiplier (feature level)
    for feat, mult in PROFILE_MULTIPLIERS["risk"].get(risk, {}).items():
        effective[feat] = effective.get(feat, 0.0) * mult

    # Apply dependent multipliers
    for dep in dependents:
        for feat, mult in PROFILE_MULTIPLIERS["dependents"].get(dep, {}).items():
            effective[feat] = effective.get(feat, 0.0) * mult

    # Apply liquidity multiplier
    for feat, mult in PROFILE_MULTIPLIERS["liquidity"].get(liquidity, {}).items():
        effective[feat] = effective.get(feat, 0.0) * mult

    # Apply health_risk multiplier
    for hr in health_risk:
        for feat, mult in PROFILE_MULTIPLIERS["health_risk"].get(hr, {}).items():
            effective[feat] = effective.get(feat, 0.0) * mult

    # Apply maturity multiplier
    for feat, mult in PROFILE_MULTIPLIERS["maturity"].get(maturity, {}).items():
        effective[feat] = effective.get(feat, 0.0) * mult

    # Normalise to sum = 1
    total = sum(effective.values())
    if total > 0:
        effective = {k: v / total for k, v in effective.items()}

    return effective


def _build_label(goal: str, risk: str, horizon: str, dependents: list) -> str:
    goal_labels = {
        "protect_family": "Family protection",
        "wealth_growth":  "Wealth growth",
        "retirement":     "Retirement planning",
        "child_future":   "Child's future",
    }
    risk_labels = {
        "conservative": "conservative investor",
        "moderate":     "moderate risk taker",
        "aggressive":   "growth-oriented investor",
        "capital_safe": "capital-safe investor",
    }
    horizon_labels = {
        "under_5":   "short-term",
        "5_to_10":   "medium-term",
        "10_to_20":  "long-term",
        "20_plus":   "very long-term",
    }
    dep_str = (
        f" with dependents ({', '.join(dependents)})"
        if dependents and "none" not in dependents
        else ""
    )
    return (
        f"{goal_labels.get(goal, goal)}, "
        f"{risk_labels.get(risk, risk)}, "
        f"{horizon_labels.get(horizon, horizon)} horizon"
        f"{dep_str}"
    )
