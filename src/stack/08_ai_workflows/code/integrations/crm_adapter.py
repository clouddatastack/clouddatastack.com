from __future__ import annotations

from typing import Any, Dict, List, Optional
from ..models.schemas import MappingDecision
from .salesforce_payload import build_sfdc_composite_payload
from .quotes_payload import build_quote_payload


def build_crm_payload(
    provider: str,
    decisions: List[MappingDecision],
    *,
    customer_id: str,
    currency: str = "EUR",
    # Salesforce-specific (optional)
    sfdc_opportunity_name: Optional[str] = None,
    sfdc_close_date: Optional[str] = None,
    sfdc_stage_name: Optional[str] = None,
    sfdc_pricebook2_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return a payload for the selected CRM provider.

    - provider='salesforce': returns a Composite API payload to create Opp + Line Items.
    - other: returns a generic quote payload suitable for custom or alternate CRMs.
    """
    if provider.lower() == "salesforce":
        if not (sfdc_opportunity_name and sfdc_close_date and sfdc_stage_name and sfdc_pricebook2_id):
            raise ValueError("Missing Salesforce parameters for CRM adapter")
        return build_sfdc_composite_payload(
            account_external_id=customer_id,
            opportunity_name=sfdc_opportunity_name,
            close_date=sfdc_close_date,
            stage_name=sfdc_stage_name,
            pricebook2_id=sfdc_pricebook2_id,
            decisions=decisions,
        )

    # Default: vendor-agnostic quote payload
    return build_quote_payload(customer_id=customer_id, currency=currency, decisions=decisions)
