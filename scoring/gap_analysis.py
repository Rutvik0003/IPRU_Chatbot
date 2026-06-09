from scoring.scorer import feature_val


def compute_gap(
    ipru_features: dict,
    competitor_features: dict,
    profile: dict,
) -> dict:
    """
    gap_score ∈ [-100, +100]
      Positive  = IPru leads
      Negative  = Competitor leads
    """
    weights = profile.get("feature_weights", {})

    feature_gaps: dict[str, float] = {}
    for feat, w in weights.items():
        if w < 0.001:
            continue
        ipru_val = feature_val(feat, ipru_features.get(feat))
        comp_val = feature_val(feat, competitor_features.get(feat))
        feature_gaps[feat] = round((ipru_val - comp_val) * w * 100, 4)

    gap_score = round(sum(feature_gaps.values()), 2)

    advantages = sorted(
        [f for f, g in feature_gaps.items() if g > 0.5],
        key=lambda f: feature_gaps[f],
        reverse=True,
    )
    trails = sorted(
        [f for f, g in feature_gaps.items() if g < -0.5],
        key=lambda f: feature_gaps[f],
    )

    # Dimension-level gap aggregation
    from scoring.weights import FEATURE_DIM_WEIGHTS
    dimension_gaps: dict[str, float] = {}
    for dim, feat_map in FEATURE_DIM_WEIGHTS.items():
        dim_gap = sum(feature_gaps.get(f, 0.0) for f in feat_map)
        dimension_gaps[dim] = round(dim_gap, 2)

    # Radar data (0-100 scale per dimension for both products)
    radar: dict[str, dict] = {}
    for dim, feat_map in FEATURE_DIM_WEIGHTS.items():
        ipru_dim = sum(
            feature_val(f, ipru_features.get(f)) * w
            for f, w in feat_map.items()
        ) * 100
        comp_dim = sum(
            feature_val(f, competitor_features.get(f)) * w
            for f, w in feat_map.items()
        ) * 100
        radar[dim] = {
            "ipru": round(ipru_dim, 1),
            "competitor": round(comp_dim, 1),
        }

    return {
        "gap_score": gap_score,
        "feature_gaps": feature_gaps,
        "ipru_advantages": advantages[:8],
        "ipru_gaps": trails[:8],
        "dimension_gaps": dimension_gaps,
        "radar_data": radar,
        "ipru_product": ipru_features.get("product_name") or ipru_features.get("_meta", {}).get("product_name", ""),
        "competitor_product": competitor_features.get("product_name") or competitor_features.get("_meta", {}).get("product_name", ""),
        "competitor_company": competitor_features.get("insurer") or competitor_features.get("_meta", {}).get("company", ""),
    }


def compare_ipru_vs_all(
    ipru_features: dict,
    competitor_list: list[dict],
    profile: dict,
) -> list[dict]:
    """Run gap_analysis for one IPru product vs every competitor."""
    return [
        compute_gap(ipru_features, comp, profile)
        for comp in competitor_list
    ]
