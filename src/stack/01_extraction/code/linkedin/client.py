"""
LinkedIn API Client Module

This module contains the LinkedIn API client and related data classes for
interacting with LinkedIn Marketing API.
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

import pendulum

from utils.clients.http_client import HTTPClient
from utils.constants.marketing.paid_digital.linkedin import (
    LINKEDIN_ACCOUNTS_ENDPOINT,
    LINKEDIN_ANALYTICS_ENDPOINT,
    LINKEDIN_API_BASE_URL,
)

from ..base import BaseMarketingAPIClient

logger = logging.getLogger(__name__)


@dataclass
class LinkedInAccount:
    """Data class for LinkedIn account information."""

    id: str
    name: str


@dataclass
class LinkedInCampaignGroup:
    """Data class for LinkedIn campaign group information."""

    id: str
    name: str
    account_id: str
    account_name: str


@dataclass
class LinkedInCampaign:
    """Data class for LinkedIn campaign information."""

    id: str
    name: str
    account_id: str
    account_name: str
    campaign_group_id: str
    campaign_group_name: str


@dataclass
class LinkedInPerformanceData:
    """Data class for LinkedIn performance metrics."""

    event_date: str
    account_id: str
    account_name: str
    campaign_id: str
    campaign_name: str
    campaign_group_id: str
    campaign_group_name: str
    impressions: int
    clicks: int
    spend: float


class LinkedInAPIClient(BaseMarketingAPIClient):
    """Client for interacting with LinkedIn Marketing API."""

    def __init__(self, access_token: str):
        super().__init__(access_token)
        self.client = HTTPClient()

    def _build_headers(self) -> Dict[str, str]:
        """Build headers for LinkedIn API requests."""
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "LinkedIn-Version": "202411",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    def get_accounts(self) -> List[LinkedInAccount]:
        """Fetch all LinkedIn marketing accounts."""
        params = {"q": "search"}
        accounts_data = self._make_request(LINKEDIN_ACCOUNTS_ENDPOINT, params, result_key="elements")

        accounts = []
        for account_data in accounts_data:
            account = LinkedInAccount(id=account_data.get("id"), name=account_data.get("name", "Unknown Account"))
            accounts.append(account)

        logger.info(f"Retrieved {len(accounts)} LinkedIn marketing accounts")
        return accounts

    def get_campaign_groups(self, account: LinkedInAccount) -> List[LinkedInCampaignGroup]:
        """Fetch campaign groups for a specific account."""
        campaign_groups_endpoint = f"{LINKEDIN_API_BASE_URL}/adAccounts/{account.id}/adCampaignGroups"
        params = {"q": "search"}
        campaign_groups_data = self._make_request(campaign_groups_endpoint, params, result_key="elements")

        campaign_groups = []
        for campaign_group_data in campaign_groups_data:
            campaign_group = LinkedInCampaignGroup(
                id=campaign_group_data.get("id"),
                name=campaign_group_data.get("name", "Unknown Campaign Group"),
                account_id=account.id,
                account_name=account.name,
            )
            campaign_groups.append(campaign_group)

        logger.info(f"Retrieved {len(campaign_groups)} LinkedIn marketing campaign groups for account `{account.name}`")
        return campaign_groups

    def get_campaigns(self, account: LinkedInAccount) -> List[LinkedInCampaign]:
        """Fetch campaigns for a specific account."""
        campaign_endpoint = f"{LINKEDIN_API_BASE_URL}/adAccounts/{account.id}/adCampaigns"
        params = {"q": "search"}
        campaigns_data = self._make_request(campaign_endpoint, params, result_key="elements")

        # Fetch campaign groups to get names
        campaign_groups = self.get_campaign_groups(account)
        campaign_groups_dict = {cg.id: cg for cg in campaign_groups}

        campaigns = []
        for campaign_data in campaigns_data:
            campaign_group_id = campaign_data.get("campaignGroup", "Unknown Campaign Group ID")
            # Extract ID from URN if present (e.g., "urn:li:sponsoredCampaignGroup:123456")
            if campaign_group_id and ":" in campaign_group_id:
                campaign_group_id = int(campaign_group_id.split(":")[-1])

            if campaign_group_id in campaign_groups_dict:
                campaign_group_name = campaign_groups_dict[campaign_group_id].name
            else:
                campaign_group_name = "Unknown Campaign Group Name"

            campaign = LinkedInCampaign(
                id=campaign_data.get("id"),
                name=campaign_data.get("name", "Unknown Campaign"),
                account_id=account.id,
                account_name=account.name,
                campaign_group_id=campaign_group_id,
                campaign_group_name=campaign_group_name,
            )
            campaigns.append(campaign)

        logger.info(f"Retrieved {len(campaigns)} LinkedIn marketing campaigns for account `{account.name}`")
        return campaigns

    def get_campaign_performance(
        self, campaign: LinkedInCampaign, start_dt: pendulum.DateTime, end_dt: pendulum.DateTime
    ) -> List[LinkedInPerformanceData]:
        """Fetch performance data for a specific campaign."""
        analytics_url = (
            f"{LINKEDIN_ANALYTICS_ENDPOINT}?"
            f"q=analytics&pivot=CAMPAIGN&"
            f"dateRange=(start:(year:{start_dt.year},month:{start_dt.month},day:{start_dt.day}),end:(year:{end_dt.year},month:{end_dt.month},day:{end_dt.day}))&"
            f"timeGranularity=DAILY&"
            f"campaigns=List(urn%3Ali%3AsponsoredCampaign%3A{campaign.id})&"
            f"fields=dateRange,impressions,clicks,costInLocalCurrency"
        )

        daily_reports = self._make_request(analytics_url, {}, result_key="elements")

        performance_data = []
        for report in daily_reports:
            date_range = report.get("dateRange", {}).get("start", {})
            event_date = f"{date_range.get('year')}-" f"{date_range.get('month'):02d}-" f"{date_range.get('day'):02d}"

            performance = LinkedInPerformanceData(
                event_date=event_date,
                account_id=campaign.account_id,
                account_name=campaign.account_name,
                campaign_id=campaign.id,
                campaign_name=campaign.name,
                campaign_group_id=campaign.campaign_group_id,
                campaign_group_name=campaign.campaign_group_name,
                impressions=report.get("impressions", 0),
                clicks=report.get("clicks", 0),
                spend=round(float(report.get("costInLocalCurrency", 0.0)), 2),
            )
            performance_data.append(performance)

        logger.info(
            f"Retrieved {len(performance_data)} LinkedIn marketing campaigns for campaign `{campaign.name}` "
            f"and account `{campaign.account_name}`"
        )
        return performance_data
