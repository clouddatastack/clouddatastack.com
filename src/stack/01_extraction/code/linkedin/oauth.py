"""
LinkedIn OAuth Module

This module contains OAuth authentication functionality for LinkedIn API.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional
from urllib.parse import urlencode

from utils.auth.aws import create_aws_client
from utils.aws.secrets import get_aws_secret
from utils.clients.http_client import HTTPClient
from utils.constants.marketing.paid_digital.linkedin import (
    LINKEDIN_CLIENT_ID,
    LINKEDIN_CLIENT_TOKEN_ID,
    LINKEDIN_OAUTH_INTROSPECT_TOKEN_ENDPOINT,
    LINKEDIN_OAUTH_TOKEN_ENDPOINT,
    LINKEDIN_REFRESH_TOKEN_ID,
    LINKEDIN_SECRET_ID,
)

logger = logging.getLogger(__name__)


class LinkedInOAuthClient:
    """Client for handling LinkedIn OAuth authentication with refresh tokens."""

    def __init__(self):
        self.client = HTTPClient()
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

    def get_refresh_token(self) -> Optional[str]:
        """Get the refresh token from AWS Secrets Manager as plain text."""
        try:
            refresh_token = get_aws_secret(LINKEDIN_REFRESH_TOKEN_ID, return_str=True)
            if not refresh_token:
                logger.warning("No refresh token found in AWS Secrets Manager")
                return None
            return refresh_token
        except Exception as e:
            logger.error(f"Failed to get refresh token: {e}")
            return None

    def get_client_secret(self) -> str:
        """Get the client secret from AWS Secrets Manager as plain text."""
        try:
            client_secret = get_aws_secret(LINKEDIN_SECRET_ID, return_str=True)
            if not client_secret:
                raise ValueError("No client secret found in AWS Secrets Manager")
            return client_secret
        except Exception as e:
            logger.error(f"Failed to get client secret: {e}")
            raise

    def _introspect_token(self, token: str) -> Dict[str, Any]:
        """Introspect the access token using LinkedIn's token introspection endpoint."""
        try:
            client_secret = self.get_client_secret()

            payload = {
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": client_secret,
                "token": token,
            }

            encoded_payload = urlencode(payload)
            response = self.client.post(
                LINKEDIN_OAUTH_INTROSPECT_TOKEN_ENDPOINT, data=encoded_payload, headers=self.headers
            )
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to introspect token: {e}")
            raise

    def _is_token_expired(self, token: str) -> bool:
        """Check if the access token is expired using LinkedIn's token introspection."""
        try:
            introspection_result = self._introspect_token(token)

            # Check if token is active
            if not introspection_result.get("active", False):
                logger.info("Access token is not active")
                return True

            # Check token status
            status = introspection_result.get("status")
            if status == "expired":
                logger.info("Access token is expired")
                return True
            elif status == "revoked":
                logger.info("Access token has been revoked")
                return True
            elif status == "active":
                logger.info("Access token is active and valid")
                return False

            # If we have expires_at, check if it's in the past
            expires_at = introspection_result.get("expires_at")
            if expires_at:
                current_time = datetime.now().timestamp()
                if current_time >= expires_at:
                    logger.info(f"Access token expired at {expires_at}")
                    return True
                else:
                    logger.info(f"Access token is valid until {expires_at}")
                    return False

            # If we can't determine expiration, assume it's valid
            logger.warning("Could not determine token expiration, assuming valid")
            return False

        except Exception as e:
            logger.warning(f"Error introspecting token: {e}")
            # If we can't introspect the token, assume it's expired to be safe
            return True

    def get_valid_access_token(self) -> str:
        """Get a valid access token, refreshing if necessary."""
        try:
            # Get the current access token as plain text
            current_token = get_aws_secret(LINKEDIN_CLIENT_TOKEN_ID, return_str=True)

            if not current_token:
                logger.warning("No current access token found, attempting to refresh")
                return self._refresh_and_get_token()

            # Check if the current token is expired using LinkedIn's introspection
            if self._is_token_expired(current_token):
                logger.info("Current access token is expired, refreshing")
                return self._refresh_and_get_token()

            logger.info("Using existing valid access token")
            return current_token

        except Exception as e:
            logger.error(f"Failed to get valid access token: {e}")
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh the access token using the provided refresh token."""
        try:
            client_secret = self.get_client_secret()

            payload = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": LINKEDIN_CLIENT_ID,
                "client_secret": client_secret,
            }

            logger.info("Refreshing LinkedIn access token")
            token_response = self._make_token_request(payload)

            # Update the stored tokens
            self._update_stored_tokens(token_response)

            logger.info("Successfully refreshed LinkedIn access token")
            return token_response

        except Exception as e:
            logger.error(f"Failed to refresh access token: {e}")
            raise

    def _make_token_request(self, payload: Dict[str, str]) -> Dict[str, Any]:
        """Make a token request to LinkedIn OAuth endpoint."""
        try:
            encoded_payload = urlencode(payload)
            response = self.client.post(LINKEDIN_OAUTH_TOKEN_ENDPOINT, data=encoded_payload, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to make token request: {e}")
            raise

    def _update_secret(self, secret_id: str, new_value: str) -> None:
        """Update a secret in AWS Secrets Manager."""
        try:
            client = create_aws_client(service="secretsmanager")
            response = client.update_secret(SecretId=secret_id, SecretString=new_value)
            logger.info(f"Successfully updated secret: {secret_id}")
            return response
        except Exception as e:
            logger.error(f"Failed to update secret {secret_id}: {e}")
            raise

    def _update_stored_tokens(self, token_response: Dict[str, Any]) -> None:
        """Update the stored access token and refresh token in AWS Secrets Manager as plain text."""
        try:
            # Update access token as plain text
            if "access_token" in token_response:
                self._update_secret(LINKEDIN_CLIENT_TOKEN_ID, token_response["access_token"])
                logger.info("Successfully updated access token in AWS Secrets Manager")

            # Update refresh token if a new one was provided
            if "refresh_token" in token_response:
                self._update_secret(LINKEDIN_REFRESH_TOKEN_ID, token_response["refresh_token"])
                logger.info("Successfully updated refresh token in AWS Secrets Manager")

        except Exception as e:
            logger.error(f"Failed to update stored tokens: {e}")
            raise

    def _refresh_and_get_token(self) -> str:
        """Refresh the token and return the new access token."""
        refresh_token = self.get_refresh_token()
        if not refresh_token:
            raise ValueError("No refresh token available. Manual authentication required.")

        token_response = self.refresh_access_token(refresh_token)
        access_token = token_response.get("access_token")

        if not access_token:
            raise ValueError("No access token received from refresh request")

        return access_token
