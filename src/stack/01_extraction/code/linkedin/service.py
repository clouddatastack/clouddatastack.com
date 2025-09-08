"""
LinkedIn Service Module

This module contains the main service class for LinkedIn marketing data operations.
"""

import logging

import pendulum

from ..base import BaseMarketingService
from .oauth import LinkedInOAuthClient
from .processor import LinkedInDataProcessor

logger = logging.getLogger(__name__)


class LinkedInService(BaseMarketingService):
    """Main service class for LinkedIn marketing data operations."""

    def get_access_token(self) -> str:
        """Get LinkedIn access token from AWS Secrets Manager, refreshing if necessary."""
        try:
            oauth_client = LinkedInOAuthClient()
            access_token = oauth_client.get_valid_access_token()

            if not access_token:
                raise ValueError("No access token received from LinkedIn API")

            logger.info("Successfully obtained LinkedIn access token")
            return access_token

        except Exception as e:
            logger.error(f"Failed to get LinkedIn access token: {e}")
            raise

    def extract_and_store_reports(
        self, raw_output_path: str, start_day: pendulum.DateTime, end_day: pendulum.DateTime
    ) -> None:
        """Extract LinkedIn data, transform it and save to S3."""
        super().extract_and_store_reports(
            raw_output_path=raw_output_path,
            start_day=start_day,
            end_day=end_day,
            processor_class=LinkedInDataProcessor,
        )
