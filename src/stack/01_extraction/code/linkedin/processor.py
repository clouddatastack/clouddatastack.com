"""
LinkedIn Data Processor Module

This module contains data processing functionality for LinkedIn marketing data.
"""

import logging
from typing import List

import pendulum

from ..base import BaseMarketingDataProcessor
from .client import LinkedInAPIClient, LinkedInPerformanceData

logger = logging.getLogger(__name__)


class LinkedInDataProcessor(BaseMarketingDataProcessor):
    """Process and transform LinkedIn marketing data."""

    @staticmethod
    def fetch_marketing_data(
        access_token: str, start_dt: pendulum.DateTime, end_dt: pendulum.DateTime
    ) -> List[LinkedInPerformanceData]:
        """Fetch complete marketing data from LinkedIn API."""
        try:
            logger.info(f"Fetching LinkedIn marketing data between: {start_dt} and {end_dt}")

            api_client = LinkedInAPIClient(access_token)
            accounts = api_client.get_accounts()

            all_performance_data = []

            for account in accounts:
                campaigns = api_client.get_campaigns(account)

                for campaign in campaigns:
                    performance_data = api_client.get_campaign_performance(campaign, start_dt, end_dt)

                    all_performance_data.extend(performance_data)

            logger.info(f"Retrieved {len(all_performance_data)} performance records from LinkedIn API")
            return all_performance_data

        except Exception as e:
            logger.error(f"Failed to fetch LinkedIn marketing data: {e}")
            raise
