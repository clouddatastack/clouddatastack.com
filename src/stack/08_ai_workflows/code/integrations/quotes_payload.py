from __future__ import annotations

from typing import List, Dict, Any
from ..models.schemas import MappingDecision


def build_quote_payload(
    customer_id: str,
    currency: str,
    decisions: List[MappingDecision],
) -> Dict[str, Any]:
    """Generic quote payload independent of any specific CRM.

    The payload contains the customer reference, currency, and quote line items
    with SKU, name, qty, unit, and price if available.
    """
    items: List[Dict[str, Any]] = []
    for d in decisions:
        if not d.get("candidate_sku"):
            continue
        ext = d["extracted"]
        items.append(
            {
                "sku": d["candidate_sku"],
                "name": d.get("candidate_name"),
                "qty": ext.get("qty", 1),
                "unit": ext.get("unit", "pcs"),
                "price": ext.get("price"),  # may be null; pricing can be resolved later
                "confidence": d.get("confidence", 0.0),
            }
        )

    return {
        "customer_id": customer_id,
        "currency": currency,
        "items": items,
        "notes": "Auto-generated from tender intake",
    }
