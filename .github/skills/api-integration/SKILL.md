---
name: api-integration
description: Integrate with new external APIs. Use when asked to add support for ESPN, Yahoo, or other fantasy football APIs.
---

# API Integration

Use this skill to integrate with new external APIs following project conventions.

## Steps

1. **Create new activity file** at `src/activities/{api_name}_client.py`

2. **Create API client class** with singleton pattern

3. **Define activity functions** for each API endpoint

4. **Add configuration** to `src/utils/config.py`

5. **Create API response models** in `src/models/api_models.py`

## API Client Template

```python
"""
{API Name} API client activities.

Provides Temporal activities for interacting with {API Name} API.
"""

import requests
import asyncio
from typing import Dict, List, Any, Optional
from temporalio import activity

from src.utils.config import get_config


class {API}Client:
    """
    Singleton client for {API Name} API.
    
    Handles authentication, rate limiting, and request execution.
    """
    
    _instance: Optional["{API}Client"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the API client."""
        config = get_config()
        self.base_url = config.{api}_base_url
        self.api_key = config.{api}_api_key
        self.session = requests.Session()
        
        # Set default headers
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "sleeper-mock-draft-agent/1.0",
        })
        
        # Add authentication if required
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
    
    def _make_request(
        self,
        endpoint: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Make HTTP request to API.
        
        Args:
            endpoint: API endpoint path (without base URL)
            method: HTTP method (GET, POST, PUT, DELETE)
            params: Query parameters
            json: JSON body for POST/PUT requests
            
        Returns:
            Response data (dict or list)
            
        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.base_url}/{endpoint}"
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json,
            timeout=30,
        )
        
        response.raise_for_status()
        return response.json()


# Singleton instance
_client = {API}Client()


# Activity Functions

@activity.defn
async def fetch_{resource}(resource_id: str) -> Dict[str, Any]:
    """
    Fetch {resource} from {API Name} API.
    
    Args:
        resource_id: ID of {resource} to fetch
        
    Returns:
        {Resource} data as dictionary
    """
    activity.logger.info(f"Fetching {resource}: {resource_id}")
    
    try:
        data = await asyncio.to_thread(
            _client._make_request,
            f"{resource}/{resource_id}"
        )
        activity.logger.info(f"Successfully fetched {resource}: {resource_id}")
        return data
    except Exception as e:
        activity.logger.error(f"Failed to fetch {resource} {resource_id}: {str(e)}")
        raise


@activity.defn
async def list_{resources}(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    List {resources} from {API Name} API.
    
    Args:
        params: Query parameters (filters, pagination, etc.)
        
    Returns:
        List of {resource} dictionaries
    """
    activity.logger.info(f"Listing {resources} with params: {params}")
    
    try:
        data = await asyncio.to_thread(
            _client._make_request,
            "{resources}",
            params=params
        )
        activity.logger.info(f"Found {len(data)} {resources}")
        return data
    except Exception as e:
        activity.logger.error(f"Failed to list {resources}: {str(e)}")
        raise
```

## Configuration Setup

Add API configuration to `src/utils/config.py`:

```python
@dataclass
class Config:
    """Application configuration"""
    
    # Existing fields...
    
    # {API Name} API
    {api}_base_url: str = "{default_base_url}"
    {api}_api_key: Optional[str] = None
    {api}_rate_limit: int = 100  # requests per minute
    
    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables"""
        return cls(
            # Existing fields...
            
            # {API Name} API
            {api}_base_url=os.getenv("{API}_BASE_URL", "{default_base_url}"),
            {api}_api_key=os.getenv("{API}_API_KEY"),
            {api}_rate_limit=int(os.getenv("{API}_RATE_LIMIT", "100")),
        )
```

Add to `.env.example`:

```bash
# {API Name} API Configuration
{API}_BASE_URL=https://api.{domain}.com/v1
{API}_API_KEY=your_api_key_here
{API}_RATE_LIMIT=100
```

## API Response Models

Create response models in `src/models/api_models.py`:

```python
from dataclasses import dataclass
from typing import Optional, Dict, List, Any


@dataclass
class {Resource}Response:
    """
    {API Name} API {resource} response.
    
    Represents a {resource} from the {API Name} API.
    """
    # Required fields first
    id: str
    name: str
    status: str
    
    # Optional fields with defaults
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
```

## API-Specific Patterns

### Read-Only APIs (like Sleeper)

```python
# No authentication needed
class SleeperAPIClient:
    def _initialize(self):
        self.base_url = "https://api.sleeper.app/v1"
        self.session = requests.Session()
        # No auth headers

# Only implement GET methods
@activity.defn
async def fetch_league(league_id: str) -> Dict[str, Any]:
    # Only fetch, no create/update/delete
    pass
```

### Authenticated APIs (ESPN, Yahoo)

```python
# OAuth or API key authentication
class ESPNAPIClient:
    def _initialize(self):
        config = get_config()
        self.session.headers.update({
            "Authorization": f"Bearer {config.espn_api_key}"
        })

# May need OAuth flow
async def authenticate_espn(auth_code: str) -> str:
    """Exchange auth code for access token"""
    pass
```

### Rate-Limited APIs

```python
import time
from datetime import datetime, timedelta

class RateLimitedClient:
    def __init__(self):
        self.requests_per_minute = 100
        self.request_times = []
    
    def _make_request(self, endpoint: str) -> Any:
        # Check rate limit
        now = datetime.now()
        cutoff = now - timedelta(minutes=1)
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        if len(self.request_times) >= self.requests_per_minute:
            sleep_time = (self.request_times[0] - cutoff).total_seconds()
            activity.logger.info(f"Rate limit reached, sleeping {sleep_time}s")
            time.sleep(sleep_time)
        
        # Make request
        response = self.session.get(f"{self.base_url}/{endpoint}", timeout=30)
        self.request_times.append(datetime.now())
        
        return response.json()
```

## Export New Activities

Add to `src/activities/__init__.py`:

```python
from src.activities.{api_name}_client import (
    fetch_{resource},
    list_{resources},
)

__all__ = [
    # Existing exports...
    "fetch_{resource}",
    "list_{resources}",
]
```

## Usage in Workflows

```python
with workflow.unsafe.imports_passed_through():
    from src.activities.{api_name}_client import fetch_{resource}

@workflow.defn
class MyWorkflow:
    @workflow.run
    async def run(self, input_data):
        data = await workflow.execute_activity(
            fetch_{resource},
            input_data.resource_id,
            start_to_close_timeout=timedelta(seconds=30),
        )
        return data
```
