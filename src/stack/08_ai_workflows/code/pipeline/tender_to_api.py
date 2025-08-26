from __future__ import annotations

from typing import Dict, Any

from ..models.schemas import TenderExtraction, ExtractedItem
from ..mapping.catalog_mapping import map_items
from ..integrations.crm_adapter import build_crm_payload


def parse_email_and_docs_to_json(email_body: str, attachments: bytes) -> TenderExtraction:
    """Step 1: Document Processing. Placeholder converting email/PDF into structured JSON.
    Replace with real parsing: MIME processing, PDF table extraction, OCR if needed.
    """
    # Toy output for illustration
    return {
        "items": [
            {
                "raw_mention": "Steel Rod EN 10060 10mm qty 100",
                "normalized_name": "Steel Rod EN 10060 10mm",
                "qty": 100,
                "unit": "pcs",
                "packaging": None,
                "standards": ["EN 10060"],
                "price": None,
                "context_span": "Table row 4",
                "notes": None,
            }
        ],
        "source_language": "en",
    }


def extract_with_llm(parsed_json: TenderExtraction, prompt_template: str) -> TenderExtraction:
    """Step 2: Intelligent Extraction. Placeholder that would call an LLM in production.
    Here we simply return the parsed_json to illustrate the flow.
    """
    return parsed_json



def run_pipeline(email_body: str, attachments: bytes, prompt: str, *, crm_provider: str = "salesforce") -> Dict[str, Any]:
    """End-to-end orchestration following the Phased AI Solution.

    Phase 1: Extract Products (parse + LLM)
    Phase 2: Map Products (catalog mapping)
    Phase 3: Create Quotes (quote payload) and/or CRM payload
    """
    # Phase 1
    parsed = parse_email_and_docs_to_json(email_body, attachments)
    extracted = extract_with_llm(parsed, prompt)

    # Phase 2
    decisions = map_items(extracted["items"])  # mapping results with confidence

    # Phase 3 — vendor-agnostic adapter (Salesforce is one option)
    crm_payload = build_crm_payload(
        provider=crm_provider,
        decisions=decisions,
        customer_id="ACME-EXT-123",
        currency="EUR",
        sfdc_opportunity_name="Tender Intake - ACME",
        sfdc_close_date="2025-09-30",
        sfdc_stage_name="Qualification",
        sfdc_pricebook2_id="01sXXXXXXXXXXXX",
    )

    return {"crm": crm_payload}
