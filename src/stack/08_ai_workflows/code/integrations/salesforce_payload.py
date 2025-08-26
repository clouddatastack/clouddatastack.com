from __future__ import annotations

from typing import List, Dict, Any
from ..models.schemas import MappingDecision


def build_sfdc_composite_payload(
    account_external_id: str,
    opportunity_name: str,
    close_date: str,
    stage_name: str,
    pricebook2_id: str,
    decisions: List[MappingDecision],
) -> Dict[str, Any]:
    """Build a Salesforce Composite API payload to create Opportunity and Line Items.

    Assumes candidate_sku maps to a PricebookEntry via an External ID.
    Replace references with your org's External IDs and fields.
    """
    ref_opp = "refOpp"
    composite: List[Dict[str, Any]] = []

    # Create Opportunity
    composite.append(
        {
            "method": "POST",
            "url": "/services/data/v59.0/sobjects/Opportunity",
            "referenceId": ref_opp,
            "body": {
                "Name": opportunity_name,
                "StageName": stage_name,
                "CloseDate": close_date,
                "Pricebook2Id": pricebook2_id,
                "Account__c": account_external_id,  # replace with your lookup strategy
                "Source__c": "Tender Intake",
            },
        }
    )

    # Create line items for candidates with a mapping
    for idx, d in enumerate(decisions):
        if not d.get("candidate_sku"):
            continue
        composite.append(
            {
                "method": "POST",
                "url": "/services/data/v59.0/sobjects/OpportunityLineItem",
                "referenceId": f"refLine{idx}",
                "body": {
                    "OpportunityId": f"@{{{ref_opp}.id}}",
                    "PricebookEntryId": f"@{{refPbe{idx}.id}}",
                    "Quantity": d["extracted"].get("qty", 1),
                },
            }
        )
        # Resolve PricebookEntry by SKU external id
        composite.append(
            {
                "method": "GET",
                "url": f"/services/data/v59.0/query?q=SELECT+Id+FROM+PricebookEntry+WHERE+Product2.ExternalId__c='{d['candidate_sku']}'+AND+Pricebook2Id='{pricebook2_id}'+LIMIT+1",
                "referenceId": f"refPbe{idx}",
            }
        )

    return {"allOrNone": True, "compositeRequest": composite}
