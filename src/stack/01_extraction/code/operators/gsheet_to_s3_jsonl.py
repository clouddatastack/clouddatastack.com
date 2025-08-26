"""
Generic Airflow operator to extract a Google Sheets range and write JSONL to S3.

Each data row becomes a JSON object (one per line). Optionally, serialize all
columns into a single payload string to reduce Google Sheets cell usage.
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any, List, Optional

from airflow.models.baseoperator import BaseOperator
from airflow.providers.amazon.aws.hooks.s3 import S3Hook
from airflow.providers.google.suite.hooks.sheets import GSheetsHook


class GSheetToS3JsonlOperator(BaseOperator):
    """
    Fetch data from Google Sheets, convert each row to JSONL, and upload to S3.

    Parameters:
        gcp_conn_id: Airflow connection ID for Google (e.g., "google_cloud_default").
        aws_conn_id: Airflow connection ID for AWS (e.g., "aws_default").
        spreadsheet_id: Google Spreadsheet ID.
        worksheet_name: Sheet/tab name.
        worksheet_range: Cell range, e.g., "A:Z" or "A1:Z9999". Must include headers in first row.
        s3_bucket: Destination S3 bucket.
        s3_key: Destination S3 key (object path). Can include templates like {{ ds }}.
        serialize_columns: If True, serialize all columns into a single string field.
        serialization_separator: Separator for column serialization when serialize_columns=True.
        payload_field: Field name to store serialized payload.
        extras: Optional dict to include extra fields in each JSON line.
    """

    template_fields = ("s3_key", "worksheet_name", "worksheet_range")

    def __init__(
        self,
        *,
        gcp_conn_id: str,
        aws_conn_id: str,
        spreadsheet_id: str,
        worksheet_name: str,
        worksheet_range: str,
        s3_bucket: str,
        s3_key: str,
        serialize_columns: bool = False,
        serialization_separator: str = "|",
        payload_field: str = "payload",
        extras: Optional[dict] = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.gcp_conn_id = gcp_conn_id
        self.aws_conn_id = aws_conn_id
        self.spreadsheet_id = spreadsheet_id
        self.worksheet_name = worksheet_name
        self.worksheet_range = worksheet_range
        self.s3_bucket = s3_bucket
        self.s3_key = s3_key
        self.serialize_columns = serialize_columns
        self.serialization_separator = serialization_separator
        self.payload_field = payload_field
        self.extras = extras or {}

    def _serialize_row(self, headers: List[str], row: List[Optional[str]]) -> dict:
        # pad row to headers length
        padded = list(row) + [None] * (len(headers) - len(row))
        if self.serialize_columns:
            # Join columns into a single string. Replace separators in values to avoid collisions.
            safe_values = [
                "" if v is None else str(v).replace(self.serialization_separator, f"\\{self.serialization_separator}")
                for v in padded
            ]
            return {self.payload_field: self.serialization_separator.join(safe_values)}
        else:
            return dict(zip(headers, padded))

    def execute(self, context: Any):
        logical_date = context["ds"]
        self.log.info(
            "Reading spreadsheet_id=%s sheet=%s range=%s",
            self.spreadsheet_id,
            self.worksheet_name,
            self.worksheet_range,
        )

        hook = GSheetsHook(gcp_conn_id=self.gcp_conn_id)
        values = hook.get_values(
            spreadsheet_id=self.spreadsheet_id, range_=f"{self.worksheet_name}!{self.worksheet_range}"
        )

        if not values or len(values) < 2:
            self.log.warning("No data found in worksheet '%s'. Skipping.", self.worksheet_name)
            return None

        raw_headers = values[0]
        headers = [h.strip().replace(" ", "_").lower() for h in raw_headers]
        rows = values[1:]

        date_of_transfer = datetime.fromisoformat(logical_date).strftime("%Y-%m-%d")
        file_name = f"{self.worksheet_name}.jsonl"

        json_lines: List[str] = []
        for row in rows:
            obj = self._serialize_row(headers, row)
            obj.update(
                {
                    "worksheet": self.worksheet_name,
                    "range": self.worksheet_range,
                    "file_name": file_name,
                    "date_of_file_transfer": date_of_transfer,
                }
            )
            if self.extras:
                obj.update(self.extras)
            json_lines.append(json.dumps(obj, ensure_ascii=False))

        output_data = "\n".join(json_lines)

        s3_hook = S3Hook(aws_conn_id=self.aws_conn_id)
        s3_hook.load_string(
            string_data=output_data, key=self.s3_key, bucket_name=self.s3_bucket, replace=True
        )

        self.log.info(
            "Uploaded %d rows to s3://%s/%s", len(rows), self.s3_bucket, self.s3_key
        )
        return f"s3://{self.s3_bucket}/{self.s3_key}"
