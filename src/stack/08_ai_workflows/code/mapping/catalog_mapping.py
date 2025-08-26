from __future__ import annotations

from typing import List, Tuple, Dict
from .models.schemas import ExtractedItem, MappingDecision


def candidate_generation(query: str) -> List[Tuple[str, str]]:
    """Return candidate (sku, name) pairs. Placeholder for BM25 + embeddings."""
    # In a real system, query Postgres/OpenSearch and pgvector for hybrid recall
    return [
        ("SKU-001", "Steel Rod EN 10060, 10mm"),
        ("SKU-002", "Steel Rod EN 10060, 12mm"),
    ]


def score_candidate(item: ExtractedItem, candidate: Tuple[str, str]) -> float:
    """Score based on lexical similarity, UoM compatibility, and standards hints."""
    sku, name = candidate
    score = 0.0
    if item.get("normalized_name") and item["normalized_name"].lower() in name.lower():
        score += 0.6
    if any(k in name.lower() for k in ["en 10060", "iso", "din"]):
        score += 0.2
    # toy heuristic for UoM presence
    if item.get("unit"):
        score += 0.2
    return min(score, 1.0)


def map_items(items: List[ExtractedItem]) -> List[MappingDecision]:
    decisions: List[MappingDecision] = []
    for item in items:
        cands = candidate_generation(item.get("normalized_name") or item.get("raw_mention", ""))
        scored = [(cand, score_candidate(item, cand)) for cand in cands]
        scored.sort(key=lambda x: x[1], reverse=True)
        best, conf = (scored[0][0], scored[0][1]) if scored else ((None, None), 0.0)
        decision: MappingDecision = {
            "extracted": item,
            "candidate_sku": best[0] if best[0] else None,
            "candidate_name": best[1] if best[1] else None,
            "confidence": conf,
            "rationale": "toy matcher: lexical + hints",
        }
        decisions.append(decision)
    return decisions
