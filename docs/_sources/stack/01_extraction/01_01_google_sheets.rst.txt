1.1. Extraction from Google Sheets
==================================

This article explains how to extract tables from Google Sheets to AWS S3 with Apache Airflow. We start with a simple approach for small tables, then scale up as your data grows. Along the way, we cover the 10M cells limit, secrets/configuration, code examples, and a design that stays robust as requirements evolve.

.. contents:: Article Outline
	:local:
	:depth: 2

Overview
--------

Many teams keep small-to-medium datasets in Google Sheets and need a dependable way to land that data in S3 for downstream analytics (dbt, Spark, Trino, Athena). This article focuses on a low-friction path to operationalize that flow with Airflow—starting simple for quick wins and growing into a robust pattern as volume and complexity increase. You’ll see how to schedule secure extractions, choose the right file format, and evolve the design without rework as your needs scale.

Design overview
---------------

Two complementary approaches:

1) Small tables: use ``GoogleApiToS3Operator`` (Sheets API values.get) → nested JSON (fastest to set up).
2) Growing tables: use a custom operator to write JSONL (one JSON row per line) → easier querying and scaling.

Contract (inputs/outputs)
-------------------------

- Inputs:
	- Google Spreadsheet ID, worksheet name, and range (first row must contain headers).
	- Airflow connections for Google and AWS.
	- S3 bucket and destination path.
- Outputs:
	- Files in S3 (JSON or JSONL), versioned by date if desired.
- Success criteria:
	- All expected rows are extracted.
	- Files are written to the configured S3 path and can be queried.
- Error modes:
	- Missing/invalid credentials (GCP/AWS), incorrect range or sheet name, API quota errors.

Limitations and implications
----------------------------

- Google Sheets hard limit: ~10 million cells per spreadsheet.
	- As tables grow (columns × rows), you may hit this cap.
	- Mitigations: split by time (multiple worksheets/spreadsheets) or serialize columns into a single cell per row (see below).
- The Sheets API values.get returns a nested values array that is less convenient to query directly.

Setup and secrets
-----------------

- Install Airflow providers:
	- ``apache-airflow``
	- ``apache-airflow-providers-google``
	- ``apache-airflow-providers-amazon``
- Create Airflow connections:
	- ``google_cloud_default``: service account with Sheets API enabled (keyfile JSON or secret backend).
	- ``aws_default``: IAM with write access to the S3 bucket.
- Prepare configuration:
	- Spreadsheet ID, worksheet name(s), range (e.g., ``A:Z`` or ``A1:Z10000`` including headers).
	- S3 bucket and prefix (e.g., ``s3://your-bucket/raw/google_sheets/<sheet>/``).

Approach A — Simple JSON (best for small tables)
------------------------------------------------
This uses ``GoogleApiToS3Operator`` to call ``spreadsheets.values.get`` and store the response JSON in S3.

.. literalinclude:: code/dags/gsheet_to_s3_basic.py
	:language: python
	:linenos:

**Code walkthrough**

- ``google_api_endpoint_params`` supplies ``spreadsheetId`` and ``range``.
- Output is a JSON object containing ``range``, ``majorDimension``, and ``values`` (list-of-lists).
- Suitable for small tables and quick wins; you can normalize later in SQL/ETL.

**Loading the nested JSON**

.. code-block:: sql

   CREATE EXTERNAL TABLE IF NOT EXISTS raw.google_sheet_values (
	   range STRING,
	   majorDimension STRING,
	   values ARRAY<ARRAY<STRING>>
   )
   STORED AS JSON
   LOCATION 's3://your-bucket/raw/google_sheets/worksheet_name/';

**Trade-offs**

- Pros: minimal setup, leverages built-in operator.
- Cons: nested format is harder to query; not ideal as data grows.

Approach B — JSONL per row (better for growth)
----------------------------------------------

We switch to row-wise JSON Lines so each row is a separate JSON object (easier for dbt/Spark/Trino).

**Operator (generic)**

.. literalinclude:: code/operators/gsheet_to_s3_jsonl.py
	:language: python
	:linenos:

**Example DAG**

.. literalinclude:: code/dags/gsheet_to_s3_jsonl.py
	:language: python
	:linenos:

**Code walkthrough**

- Reads headers and data via ``GSheetsHook``; creates one JSON per row.
- Adds metadata: ``worksheet``, ``range``, ``file_name``, ``date_of_file_transfer``.
- Writes to S3 as ``.jsonl`` so downstream tools can process line-by-line.

**Schema for JSONL**

.. code-block:: sql

   CREATE EXTERNAL TABLE IF NOT EXISTS raw.google_sheet_jsonl (
	   -- your columns inferred from headers
	   col1 STRING,
	   col2 STRING,
	   -- metadata
	   worksheet STRING,
	   range STRING,
	   file_name STRING,
	   date_of_file_transfer DATE
   )
   ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
   LOCATION 's3://your-bucket/raw/google_sheets/worksheet_name/';

Dealing with the 10M cells limit: column serialization
------------------------------------------------------

If you are constrained by the Sheets cell limit, store all columns as a single serialized field per row in the sheet, and reconstruct downstream. The operator supports this via ``serialize_columns=True``.

Example (conceptual):

.. code-block:: python

   copy_gsheet_to_s3 = GSheetToS3JsonlOperator(
	   task_id="copy_worksheet_to_s3_serialized",
	   gcp_conn_id="google_cloud_default",
	   aws_conn_id="aws_default",
	   spreadsheet_id="<YOUR_SPREADSHEET_ID>",
	   worksheet_name="<WORKSHEET_NAME>",
	   worksheet_range="A:Z",
	   s3_bucket="<YOUR_BUCKET>",
	   s3_key="raw/google_sheets/<WORKSHEET_NAME>/data_{{ ds_nodash }}.jsonl",
	   serialize_columns=True,
	   serialization_separator="|",   # escape handled in operator
	   payload_field="payload",
   )

Downstream, split ``payload`` by the chosen separator to reconstruct columns. This reduces sheet cell usage (one cell per row instead of many), at the cost of manual parsing later.

Scheduling, monitoring, and reliability
---------------------------------------

- Schedule aligns with the manual update window; use retries (2–4) and alerting on failure.
- Version outputs (e.g., ``data_{{ ds_nodash }}.jsonl``) for reproducibility.
- Consider sensors if you depend on other upstream tasks.

Security and configuration
--------------------------

- Keep credentials in Airflow Connections or a secret backend (e.g., AWS Secrets Manager) — not in code.
- Scope IAM minimally: S3 write-only where possible; Sheets read-only.
- Limit spreadsheet access to service accounts used by Airflow.

Summary of trade-offs
---------------------

- Simple JSON (values.get): fastest start; harder to query later.
- JSONL per row: slightly more setup; far easier for downstream tools and scale.
- Column serialization: mitigates Sheets limits; requires parsing in the lake.

References
----------

- `Google Sheets API (values.get) <https://developers.google.com/sheets/api/reference/rest/v4/spreadsheets.values/get>`_
- `Airflow GoogleApiToS3Operator docs <https://airflow.apache.org/docs/apache-airflow-providers-amazon/stable/_api/airflow/providers/amazon/aws/transfers/google_api_to_s3/index.html>`_
- `Airflow GSheetsHook docs <https://airflow.apache.org/docs/apache-airflow-providers-google/stable/_api/airflow/providers/google/suite/hooks/sheets/index.html>`_

.. raw:: html

   <script>
   var links = document.querySelectorAll('a[href^="http"]');
   links.forEach(function(link) {
	   link.setAttribute('target', '_blank');
   });
   </script>

