from storage import product_store
from scoring.scorer import score_product


IPRU_IDENTIFIERS = [
    "icici prudential",
    "icici pru",
    "ipru",
    "iciciprulife",
]


def _is_ipru(features: dict) -> bool:
    company = (
        features.get("insurer") or
        features.get("_meta", {}).get("company", "")
    ).lower()
    return any(kw in company for kw in IPRU_IDENTIFIERS)


def _is_competitor(features: dict) -> bool:
    return not _is_ipru(features)


def rank_ipru(profile: dict, top_k: int = 5) -> list[dict]:
    """
    Load all indexed IPru products, score each against the profile,
    apply hard filters, sort descending. Returns top_k scored dicts.
    """
    all_products = product_store.load_all()
    ipru_products = [p for p in all_products if _is_ipru(p)]

    scored = []
    for features in ipru_products:
        result = score_product(features, profile)
        if result is None:
            continue
        result["_raw_features"] = features
        scored.append(result)

    scored.sort(key=lambda x: x["total_score"], reverse=True)

    # Deduplicate by product name — keep the highest-scoring entry per name
    seen: set[str] = set()
    deduped = []
    for r in scored:
        name = (r.get("product_name") or "").strip().lower()
        if name and name in seen:
            continue
        seen.add(name)
        deduped.append(r)

    return deduped[:top_k]


def rank_competitors(profile: dict, top_k: int = 5) -> list[dict]:
    """
    Rank competitor products by the same scoring logic.
    Used as the pool for gap analysis.
    """
    all_products = product_store.load_all()
    competitor_products = [p for p in all_products if _is_competitor(p)]

    scored = []
    for features in competitor_products:
        result = score_product(features, profile)
        if result is None:
            continue
        result["_raw_features"] = features
        scored.append(result)

    scored.sort(key=lambda x: x["total_score"], reverse=True)
    return scored[:top_k]


def rank_all(profile: dict) -> dict:
    """
    Combined ranking: returns top IPru products + top competitors.
    """
    return {
        "ipru": rank_ipru(profile),
        "competitors": rank_competitors(profile),
    }
