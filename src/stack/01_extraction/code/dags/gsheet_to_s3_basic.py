"""
Example Airflow DAG: extract a Google Sheets worksheet range to S3 using
GoogleApiToS3Operator (row-major JSON from Sheets API).

Generalized (no project-specific names). Requires Airflow + providers installed:
  - apache-airflow
  - apache-airflow-providers-google
  - apache-airflow-providers-amazon
"""
from __future__ import annotations

from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.providers.amazon.aws.transfers.google_api_to_s3 import (
    GoogleApiToS3Operator,
)
import pendulum


with DAG(
    dag_id="example_gsheet_to_s3_basic",
    description="Copy a Google Sheets range to S3 as JSON using GoogleApiToS3Operator",
    schedule="0 8-15 * * 1,2",  # Hourly Mon-Tue 08:00-15:00 UTC
    start_date=pendulum.datetime(2025, 1, 1, tz="UTC"),
    catchup=False,
    tags=["google-sheets", "s3", "extraction"],
    default_args={"retries": 2},
) as dag:
    start = EmptyOperator(task_id="start")
    end = EmptyOperator(task_id="end")

    copy_gsheet_to_s3 = GoogleApiToS3Operator(
        task_id="copy_worksheet_to_s3",
        gcp_conn_id="google_cloud_default",  # Configure in Airflow
        google_api_service_name="sheets",
        google_api_service_version="v4",
        google_api_endpoint_path="sheets.spreadsheets.values.get",
        google_api_endpoint_params={
            "spreadsheetId": "<YOUR_SPREADSHEET_ID>",
            "range": "<WORKSHEET_NAME>!A:Z",  # Includes headers in first row
        },
        aws_conn_id="aws_default",
        s3_destination_key="s3://<YOUR_BUCKET>/raw/google_sheets/<WORKSHEET_NAME>/data.json",
        s3_overwrite=True,
    )

    start >> copy_gsheet_to_s3 >> end
