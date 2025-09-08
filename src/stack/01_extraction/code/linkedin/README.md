# LinkedIn Marketing Data Pipeline Package

This package contains all LinkedIn-related functionality for marketing data ingestion, including OAuth authentication, API clients, data processing, and storage operations.

## 📁 Package Structure

```
linkedin/
├── client.py            # API client and data classes
├── oauth.py             # OAuth authentication
├── processor.py         # Data processing
├── service.py           # Main service class
└── README.md           # This documentation
```

## 🚀 Quick Start

### Basic Usage

```python
from utils.pipelines.marketing.paid_digital.linkedin.service import LinkedInService
import pendulum

# Create service instance
linkedin_service = LinkedInService()

# Extract and store LinkedIn marketing data
linkedin_service.extract_and_store_reports(
    raw_output_path="s3://your-bucket/raw/linkedin_ads_reports",
    start_day=pendulum.datetime(2024, 1, 1),
    end_day=pendulum.datetime(2024, 1, 31)
)
```

## 📋 Modules Overview

### 🔐 `oauth.py` - OAuth Authentication

Handles LinkedIn OAuth authentication with automatic token refresh.

**Key Classes:**
- `LinkedInOAuthClient`: Manages OAuth authentication and token refresh

**Features:**
- Automatic access token refresh using refresh tokens
- Plain text token storage in AWS Secrets Manager
- Comprehensive error handling and logging

### 🎯 `client.py` - API Client

Contains the LinkedIn API client and data classes.

**Key Classes:**
- `LinkedInAPIClient`: Main API client for LinkedIn Marketing API
- `LinkedInAccount`: Data class for account information
- `LinkedInCampaignGroup`: Data class for campaign group information
- `LinkedInCampaign`: Data class for campaign information
- `LinkedInPerformanceData`: Data class for performance metrics

**Features:**
- Fetch marketing accounts
- Fetch campaign groups for accounts
- Fetch campaigns for accounts
- Fetch performance data for campaigns
- Comprehensive error handling

### 🔄 `processor.py` - Data Processing

Handles data processing and transformation.

**Key Classes:**
- `LinkedInDataProcessor`: Processes and transforms LinkedIn data

**Features:**
- Fetch complete marketing data from LinkedIn API
- Convert performance data to pandas DataFrame
- Batch processing of accounts and campaigns

### 🎛️ `service.py` - Main Service

Main service class that orchestrates all operations.

**Key Classes:**
- `LinkedInService`: Main service class

**Features:**
- High-level interface for data extraction and storage
- Automatic token management
- End-to-end data pipeline

## 🔧 Setup

### 1. Store Refresh Token

Store your LinkedIn refresh token in AWS Secrets Manager:

```
Secret ID: airflow/variables/marketing/linkedin_refresh_token
Format: Plain text string
```

### 2. Store Client Secret

Store your LinkedIn client secret in AWS Secrets Manager:

```
Secret ID: airflow/variables/marketing/linkedin_client_secret
Format: Plain text string
```

## 📊 Data Flow

1. **Authentication**: `LinkedInOAuthClient` gets/refreshes access token
2. **Data Fetching**: `LinkedInAPIClient` fetches accounts, campaigns, and performance data
3. **Processing**: `LinkedInDataProcessor` processes and transforms the data
4. **Storage**: Data is stored to S3 using the base storage functionality
5. **Orchestration**: `LinkedInService` coordinates all operations using inherited base logic
