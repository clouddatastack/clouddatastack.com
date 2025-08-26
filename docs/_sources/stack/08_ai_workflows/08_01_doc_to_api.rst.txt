8.1. Document to API Call
=========================

Overview
--------

Apply AI to handle incoming automated requests by parsing generated content and turning it into precise API calls. A common example: tenders or RFQs arrive as emails with PDF/Word attachments; the goal is to parse the message and documents, extract product lines, map them to your catalog, and automatically create Opportunities and Line Items in systems like Salesforce.

The Phased AI Solution
----------------------

- Extract Products
	→ AI identifies and pulls product names, specifications, and quantities from tender documents.
	→ Proves the core ability to read complex text.

- Map Products
	→ Matches extracted names to the official product catalog.
	→ Translates customer terminology into internal product codes/SKUs.

- Create Quotes
	→ Generates an automated quote based on the mapped products.
	→ Depends entirely on the success of the first two phases.

Two-step approach
-----------------

- Step 1: Document Processing
  • Convert tender documents (PDFs/Word) and email bodies into a structured digital format (JSON).
  • This creates a foundation of clean, searchable, and structured data.

- Step 2: Intelligent Extraction
  • Feed the JSON into a prompt template and then to an LLM.
  • Use a specialized prompt with detailed instructions to guide the model.
  • Extract specific product information with high accuracy.

Use case and scope
------------------

- Inputs: RFC-822 email (MIME) and attachments (PDF/Docx), languages such as English/German.
- Entities: Product mentions (name/spec/qty/unit/packaging/standards), optional price.
- Outputs: Structured JSON for extracted items; mapped SKUs with confidence; API payload for CRM.
- Targets: CRM objects such as Salesforce (Account/Contact, Opportunity, OpportunityLineItem, Files/Notes) or other CRMs via an adapter.
- Users: Sales Ops/Bid Desk; optional human-in-the-loop for low-confidence lines.

Architecture (POC)
------------------

- Ingest: webhook/IMAP/SES → queue → worker.
- Parsing: text + tables; OCR for scanned PDFs.
- LLM extraction: JSON-only mode, validated by schema.
- Catalog mapping: hybrid search (lexical + embeddings) + rules and unit constraints.
- Review: approve/correct low-confidence items.
- Integration: create CRM records via REST/Composite API with retries.
- Observability: logs, metrics, costs, drift.

Data flow and contracts
-----------------------

- Input: email body and attachments.
- Intermediate: structured JSON from parsing (Step 1) and refined JSON from LLM (Step 2).
- Output: mapped decisions with confidences and a ready-to-send CRM payload.

Extraction schema
-----------------

.. literalinclude:: code/models/extraction_contract.json
	:language: json
	:caption: JSON schema for extracted items

Prompt template
---------------

.. literalinclude:: code/prompts/extract_products.prompt
	:language: text
	:caption: Prompt for product extraction

Mapping logic (sketch)
----------------------

.. literalinclude:: code/mapping/catalog_mapping.py
	:language: python
	:lines: 1-200
	:caption: Hybrid mapping toy example

Salesforce payload (sketch)
---------------------------

.. literalinclude:: code/integrations/salesforce_payload.py
	:language: python
	:lines: 1-200
	:caption: Composite API payload builder example

Pipeline skeleton
-----------------

.. literalinclude:: code/pipeline/tender_to_api.py
	:language: python
	:lines: 1-999
	:caption: End-to-end POC pipeline steps

CRM adapter (select provider)
-----------------------------

.. literalinclude:: code/integrations/crm_adapter.py
	:language: python
	:lines: 1-200
	:caption: Adapter: Salesforce or vendor-agnostic quote payload

Quotes payload (generic)
------------------------

.. literalinclude:: code/integrations/quotes_payload.py
	:language: python
	:lines: 1-200
	:caption: Quote payload builder (vendor-agnostic)

Operational notes
-----------------

- Guardrails: enforce JSON-only LLM output; validate against schema; cap tokens; redact PII.
- Constraints: only map active SKUs with valid pricebook entries and unit compatibility.
- HITL: show source snippet, extracted line, candidate SKUs with confidence; approve/correct.
- Retries/backoff: handle 429/5xx from CRM APIs.
- Metrics: extraction accuracy (precision/recall/F1), mapping confidence histogram, turnaround time, API errors.

Delivery outline
----------------

- MVP: Ingest → Parse → Extract → Map → Create Opportunity/Line Items (fixed pricebook); small reviewer UI; a golden set for regression.
- Iteration: composite API, account match via domain/external ID, synonyms cache, telemetry dashboard.
- V1+: improved OCR for tables, additional languages, canary prompts, role-based reviewer.

Portability
-----------

The examples are provider-agnostic. Swap AWS components for GCP/Azure equivalents. Replace CRM integration with your target system while keeping the contracts and steps unchanged.

