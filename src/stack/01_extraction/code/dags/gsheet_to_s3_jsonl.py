"""
Example Airflow DAG: extract a Google Sheets worksheet range to S3 as JSONL
using a custom operator that normalizes row-wise and adds metadata.

Generalized (no project-specific names). Requires Airflow + providers installed.
"""
from __future__ import annotations

from airflow import DAG
from airflow.operators.empty import EmptyOperator
import pendulum

# Adjust import to your Airflow project structure (e.g., plugins/operators)
try:
    from operators.gsheet_to_s3_jsonl import GSheetToS3JsonlOperator  # type: ignore
except Exception:  # pragma: no cover - example import fallback
    GSheetToS3JsonlOperator = None  # type: ignore


with DAG(
    dag_id="example_gsheet_to_s3_jsonl",
    description="Copy a Google Sheets range to S3 as JSONL (one object per row)",
    schedule="0 3 * * *",  # Daily 03:00 UTC
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["google-sheets", "s3", "jsonl"],
    default_args={"retries": 2},
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    if GSheetToS3JsonlOperator is None:
        raise ImportError(
            "GSheetToS3JsonlOperator not importable. Place operators/gsheet_to_s3_jsonl.py in your Airflow project and adjust the import."
        )

    copy_gsheet_to_s3 = GSheetToS3JsonlOperator(
        task_id="copy_worksheet_to_s3",
        gcp_conn_id="google_cloud_default",
        aws_conn_id="aws_default",
        spreadsheet_id="<YOUR_SPREADSHEET_ID>",
        worksheet_name="<WORKSHEET_NAME>",
        worksheet_range="A:Z",
        s3_bucket="<YOUR_BUCKET>",
        s3_key="raw/google_sheets/<WORKSHEET_NAME>/data_{{ ds_nodash }}.jsonl",
        # set serialize_columns=True to collapse all columns into one payload string
        serialize_columns=False,
        serialization_separator="|",
        payload_field="payload",
        extras={"source": "google_sheets"},
    )

    start >> copy_gsheet_to_s3 >> end
