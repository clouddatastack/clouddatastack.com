1.6. Extraction from Facebook
================================

.. import time
.. from datetime import datetime
.. from typing import Any, Optional

.. import pandas as pd
.. import pendulum
.. from awswrangler.s3 import to_csv as wr_to_csv
.. from facebook_business.adobjects.adaccount import AdAccount
.. from facebook_business.adobjects.adreportrun import AdReportRun
.. from facebook_business.adobjects.adsinsights import AdsInsights
.. from facebook_business.adobjects.user import User
.. from facebook_business.api import FacebookAdsApi
.. from pydantic import BaseModel, Field, field_validator

.. from utils.aws.secrets import get_aws_secret
.. from utils.constants.marketing.paid_digital.facebook import ADINSIGHTS_FIELDS


.. class AdsInsightsModel(BaseModel):
..     date_stop: str = Field(exclude=True)
..     event_date: str = Field(alias="date_start")
..     currency: str = Field(alias="account_currency")
..     account_name: Optional[str]
..     account_id: Optional[str]
..     campaign_name: Optional[str]
..     campaign_id: Optional[str]
..     adset_name: Optional[str]
..     adset_id: Optional[str]
..     ad_name: Optional[str]
..     ad_id: Optional[str]
..     impressions: int | None = Field(default=None)
..     clicks: int | None = Field(default=None)
..     click_through_rate: float | None = Field(alias="ctr", default=None)
..     cost_per_mille: float | None = Field(alias="cpm", default=None)
..     cost_per_click: float | None = Field(alias="cpc", default=None)
..     spend: float | None = Field(default=None)
..     reach: int | None = Field(default=None)
..     frequency: float | None = Field(default=None)
..     video_15_sec_watched_actions: int | None = Field(default=None)
..     video_30_sec_watched_actions: int | None = Field(default=None)
..     video_p25_watched_actions: int | None = Field(default=None)
..     video_p50_watched_actions: int | None = Field(default=None)
..     video_p75_watched_actions: int | None = Field(default=None)
..     video_p95_watched_actions: int | None = Field(default=None)
..     video_p100_watched_actions: int | None = Field(default=None)
..     inline_link_clicks: int | None = Field(default=None)
..     video_play_actions: int | None = Field(default=None)
..     impression_device: str
..     device_platform: str

..     @field_validator(
..         "video_15_sec_watched_actions",
..         "video_30_sec_watched_actions",
..         "video_p25_watched_actions",
..         "video_p50_watched_actions",
..         "video_p75_watched_actions",
..         "video_p95_watched_actions",
..         "video_p100_watched_actions",
..         "video_play_actions",
..         mode="before",
..     )
..     @classmethod
..     def extract_first_value(cls, value: Any) -> Optional[int]:
..         if isinstance(value, list) and len(value) > 0:
..             return int(value[0].get("value", 0))

..         if value:
..             raise NotImplementedError

..         return None

..     @field_validator("event_date", mode="after")
..     @classmethod
..     def validate_event_date(cls, value: str) -> str:
..         try:
..             datetime.strptime(value, "%Y-%m-%d")
..             return value
..         except ValueError:
..             raise ValueError(f'Date "{value}" is not in the format YYYY-MM-DD')


.. def get_filtered_account_ids() -> list[str]:
..     """
..     Retrieve Facebook account IDs via API and filter for accounts containing 'Kleinanzeigen'
..     but not containing 'eBay' in their names.

..     Note: FacebookAdsApi must be initialized before calling this function.

..     Returns:
..         List of filtered account IDs in the format 'act_<account_id>'
..     """
..     # Get the current user (business)
..     me = User(fbid="me")

..     # Get all ad accounts accessible to this user
..     ad_accounts = me.get_ad_accounts(fields=["id", "name"])

..     filtered_account_ids = []

..     for account in ad_accounts:
..         account_name = account.get("name", "")
..         account_id = account.get("id", "")

..         # Filter: include if contains 'Kleinanzeigen' and does NOT contain 'eBay'
..         if "Kleinanzeigen" in account_name and "eBay" not in account_name:
..             # Ensure the account ID has the 'act_' prefix
..             if not account_id.startswith("act_"):
..                 account_id = f"act_{account_id}"
..             filtered_account_ids.append(account_id)
..             print(f"Including account: {account_name} (ID: {account_id})")
..         else:
..             print(f"Excluding account: {account_name} (ID: {account_id})")

..     print(f"Found {len(filtered_account_ids)} matching accounts")
..     return filtered_account_ids


.. def parse_object(data: dict) -> dict:
..     model = AdsInsightsModel(**data)
..     rt = model.model_dump(mode="python")
..     return rt


.. def convert_to_pandas(data: list[dict]) -> pd.DataFrame:
..     df = pd.DataFrame(data, index=None)
..     int_cols = [
..         "impressions",
..         "clicks",
..         "reach",
..         "video_15_sec_watched_actions",
..         "video_30_sec_watched_actions",
..         "video_p25_watched_actions",
..         "video_p50_watched_actions",
..         "video_p75_watched_actions",
..         "video_p95_watched_actions",
..         "video_p100_watched_actions",
..         "inline_link_clicks",
..         "video_play_actions",
..     ]
..     df[int_cols] = df[int_cols].astype("Int64")
..     return df


.. def facebook_ads_report_function(raw_output_path: str, start_day: pendulum.DateTime, end_day: pendulum.DateTime):
..     secret = get_aws_secret(id="airflow/variables/marketing/facebook_marketing_api", return_str=False)
..     access_token = secret["access_token"]
..     app_secret = secret["app_secret"]
..     app_id = secret["app_id"]
..     FacebookAdsApi.init(app_id, app_secret, access_token)

..     account_ids = get_filtered_account_ids()

..     if not account_ids:
..         raise Exception("No matching Facebook accounts found.")

..     params = {
..         "level": "ad",
..         "breakdowns": ["impression_device", "device_platform"],
..         "action_breakdowns": ["action_type"],
..         "date_preset": AdsInsights.DatePreset.last_year,
..         "time_range": {"since": start_day.to_date_string(), "until": end_day.to_date_string()},
..         "time_increment": 1,
..     }
..     results = []
..     for acc in account_ids:
..         ad_account = AdAccount(acc)

..         # according to https://github.com/facebook/facebook-python-business-sdk/blob/main/examples/async.py
..         async_job = ad_account.get_insights(fields=ADINSIGHTS_FIELDS, params=params, is_async=True)

..         while True:
..             job = async_job.api_get()
..             print("Percent of async job done: " + str(job[AdReportRun.Field.async_percent_completion]))
..             time.sleep(1)
..             if job and job[AdReportRun.Field.async_status] == "Job Completed":
..                 print("The job has completed and data can be accessed.")
..                 break

..         insights = async_job.get_result()

..         for insight in insights:
..             data = insight.export_all_data()
..             results.append(parse_object(data))

..     if results:
..         print(f"Found {len(results)} records")
..         df = convert_to_pandas(results)
..         wr_to_csv(
..             df=df,
..             path=raw_output_path,
..             dataset=True,
..             partition_cols=["event_date"],
..             mode="overwrite_partitions",
..             index=False,
..         )
..         return

..     print("No records found")
