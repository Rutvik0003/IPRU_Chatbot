"""
Hybrid retrieval: vector similarity (ChromaDB) + BM25 (keyword).
Scores are merged via Reciprocal Rank Fusion (RRF).

Usage:
    engine = QueryEngine()
    hits = engine.retrieve("what is the critical illness cover?", top_k=5)
    hits = engine.retrieve("term plan for 30 year old", profile=user_profile, top_k=8)
"""

from rag import embedder, vector_store
from storage import product_store

try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False
    print("[query_engine] rank_bm25 not installed — BM25 disabled, using vector only")


RRF_K = 60  # standard RRF constant


def _rrf_score(rank: int) -> float:
    return 1.0 / (RRF_K + rank + 1)


class QueryEngine:

    def __init__(self):
        self._bm25 = None
        self._bm25_docs: list[dict] = []
        self._built = False

    def _build_bm25(self):
        if not BM25_AVAILABLE:
            return
        all_features = product_store.load_all()
        if not all_features:
            return

        # Index product-level summaries (not PDF chunks) for keyword search
        docs = []
        for feat in all_features:
            parts = []
            for key in ("product_name", "insurer", "product_type", "insurance_type"):
                v = feat.get(key) or feat.get("_meta", {}).get(key, "")
                if v:
                    parts.append(str(v))
            # Add boolean feature names as keywords for better matching
            for field, val in feat.items():
                if field.startswith("_"):
                    continue
                if val is True:
                    parts.append(field.replace("_", " "))
            docs.append({
                "text": " ".join(parts),
                "features": feat,
            })

        self._bm25_docs = docs
        tokenized = [d["text"].lower().split() for d in docs]
        self._bm25 = BM25Okapi(tokenized)
        self._built = True

    def retrieve(
        self,
        query: str,
        top_k: int = 8,
        profile: dict = None,
        company_filter: str = None,
        insurance_type_filter: str = None,
    ) -> list[dict]:

        if not self._built:
            self._build_bm25()

        where_clause = {}
        if company_filter:
            where_clause["company"] = {"$eq": company_filter}
        if insurance_type_filter:
            where_clause["insurance_type"] = {"$eq": insurance_type_filter}

        # ── Vector retrieval ─────────────────────────────────────────────────
        query_emb = embedder.embed_one(query)
        vector_hits = vector_store.query(
            query_emb,
            top_k=top_k * 2,
            where=where_clause if where_clause else None,
        )

        # ── BM25 retrieval ───────────────────────────────────────────────────
        bm25_hits = []
        if self._bm25 and self._bm25_docs:
            scores = self._bm25.get_scores(query.lower().split())
            ranked = sorted(
                enumerate(scores),
                key=lambda x: x[1],
                reverse=True,
            )[:top_k * 2]
            for idx, score in ranked:
                if score > 0:
                    bm25_hits.append({
                        "text": self._bm25_docs[idx]["text"][:500],
                        "metadata": {
                            "company":          self._bm25_docs[idx]["features"].get("insurer", ""),
                            "product_name":     self._bm25_docs[idx]["features"].get("product_name", ""),
                            "source_file":      self._bm25_docs[idx]["features"].get("_meta", {}).get("source_file", ""),
                        },
                        "score": score,
                        "bm25": True,
                        "_features": self._bm25_docs[idx]["features"],
                    })

        # ── RRF merge ────────────────────────────────────────────────────────
        rrf: dict[str, float] = {}
        hit_map: dict[str, dict] = {}

        for rank, hit in enumerate(vector_hits):
            key = hit["metadata"].get("source_file", hit["text"][:80])
            rrf[key] = rrf.get(key, 0) + _rrf_score(rank)
            hit_map[key] = hit

        for rank, hit in enumerate(bm25_hits):
            key = hit["metadata"].get("source_file", hit["text"][:80])
            rrf[key] = rrf.get(key, 0) + _rrf_score(rank)
            if key not in hit_map:
                hit_map[key] = hit

        # Sort by combined RRF score
        merged = sorted(rrf.items(), key=lambda x: x[1], reverse=True)

        results = []
        for key, combined_score in merged[:top_k]:
            hit = hit_map[key]
            hit["rrf_score"] = round(combined_score, 6)
            results.append(hit)

        return results
