from typing import List, Optional, TypedDict


class ExtractedItem(TypedDict, total=False):
    raw_mention: str
    normalized_name: str
    qty: float
    unit: str
    packaging: Optional[str]
    standards: Optional[List[str]]
    price: Optional[float]
    context_span: str
    notes: Optional[str]


class MappingDecision(TypedDict, total=False):
    extracted: ExtractedItem
    candidate_sku: Optional[str]
    candidate_name: Optional[str]
    confidence: float  # 0..1
    rationale: Optional[str]


class TenderExtraction(TypedDict, total=False):
    items: List[ExtractedItem]
    source_language: Optional[str]
