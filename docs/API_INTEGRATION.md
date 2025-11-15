# API Integration Guide

This guide covers the integration between the ProductScraper testing framework and the Apify platform API.

## Table of Contents

- [Platform API Overview](#platform-api-overview)
- [Authentication](#authentication)
- [Dataset Management](#dataset-management)
- [Actor Runs](#actor-runs)
- [Testing Integration](#testing-integration)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Monitoring](#monitoring)

## Platform API Overview

The Apify Platform API provides programmatic access to platform features:

- **Actor Management**: Deploy, run, and monitor actors
- **Dataset Management**: Create, upload, and retrieve datasets
- **Run Management**: Start, monitor, and control actor runs
- **Storage**: Key-value stores, request queues, and datasets

### API Endpoints

```python
BASE_URL = "https://api.apify.com/v2"

# Actor endpoints
GET    /acts/{actorId}/runs          # List actor runs
POST   /acts/{actorId}/runs          # Start actor run
GET    /acts/{actorId}/runs/{runId}  # Get run details

# Dataset endpoints
GET    /datasets                     # List datasets
POST   /datasets                     # Create dataset
POST   /datasets/{datasetId}/items   # Upload items
GET    /datasets/{datasetId}/items   # Retrieve items

# Run endpoints
GET    /actor-runs/{runId}           # Get run status
POST   /actor-runs/{runId}/abort     # Abort run
```

## Authentication

### API Token Configuration

The platform API uses Bearer token authentication:

```python
import httpx

headers = {"Authorization": f"Bearer {api_token}"}

async with httpx.AsyncClient(headers=headers) as client:
    response = await client.get("https://api.apify.com/v2/datasets")
```

### Token Management

```python
from src.core.settings_manager import settings

class ApifyPlatformClient:
    def __init__(self, api_token: Optional[str] = None):
        self.api_token = api_token or settings.get("apify_api_token")
        if not self.api_token:
            raise ApifyPlatformAuthError("Apify API token not configured")
```

### Token Scopes

Required token permissions:
- **Read**: Access to datasets and runs
- **Write**: Create datasets and start runs
- **Admin**: Deploy and manage actors

## Dataset Management

### Creating Datasets

```python
async def create_dataset(self, name: str) -> str:
    """Create a new dataset."""
    data = {"name": name}
    response = await self._make_request("POST", "datasets", json=data)
    return response["data"]["id"]
```

### Uploading Data

```python
async def upload_dataset_items(self, dataset_id: str, items: List[Dict]) -> None:
    """Upload items to dataset in batches."""
    batch_size = 1000
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        await self._make_request("POST", f"datasets/{dataset_id}/items", json=batch)
```

### Retrieving Data

```python
async def get_dataset_items(self, dataset_id: str) -> List[Dict]:
    """Retrieve all items from dataset."""
    response = await self._make_request("GET", f"datasets/{dataset_id}/items")
    return response if isinstance(response, list) else []
```

## Actor Runs

### Starting Runs

```python
async def run_actor(self, actor_id: str, input_data: Dict) -> str:
    """Start an actor run."""
    data = {"input": input_data}
    response = await self._make_request("POST", f"acts/{actor_id}/runs", json=data)
    return response["data"]["id"]
```

### Monitoring Runs

```python
async def get_run_status(self, run_id: str) -> Dict:
    """Get current run status."""
    response = await self._make_request("GET", f"actor-runs/{run_id}")
    return response["data"]

async def wait_for_completion(self, run_id: str, timeout: int = 300) -> Dict:
    """Wait for run to complete."""
    start_time = asyncio.get_event_loop().time()

    while True:
        status_data = await self.get_run_status(run_id)
        status = status_data["status"]

        if status == "SUCCEEDED":
            return status_data
        elif status in ["FAILED", "TIMED-OUT", "ABORTED"]:
            raise ApifyPlatformJobError(f"Run failed with status: {status}")

        if asyncio.get_event_loop().time() - start_time > timeout:
            raise ApifyPlatformTimeoutError("Run timed out")

        await asyncio.sleep(5)
```

### Aborting Runs

```python
async def abort_run(self, run_id: str) -> bool:
    """Abort a running actor."""
    try:
        response = await self._make_request("POST", f"actor-runs/{run_id}/abort")
        return response["data"]["status"] in ["ABORTING", "ABORTED"]
    except ApifyPlatformError:
        return False
```

## Testing Integration

### Unified Testing Interface

The testing framework provides a unified interface for local and platform testing:

```python
from src.core.platform_testing_client import PlatformTestingClient, TestingMode

# Local testing
async with PlatformTestingClient(TestingMode.LOCAL) as client:
    result = await client.run_scraper("amazon", ["B07G5J5FYP"])

# Platform testing
async with PlatformTestingClient(TestingMode.PLATFORM) as client:
    result = await client.run_scraper("amazon", ["B07G5J5FYP"])
```

### Platform Testing Flow

1. **Authentication**: Verify API token and connectivity
2. **Actor Validation**: Ensure actor is deployed and accessible
3. **Run Execution**: Start actor run with input data
4. **Monitoring**: Poll run status until completion
5. **Result Retrieval**: Download results from dataset
6. **Validation**: Apply data quality checks

### Local Testing Flow

1. **Scraper Discovery**: Find and validate scraper structure
2. **Execution**: Run scraper using local Apify simulation
3. **Result Processing**: Format results consistently
4. **Validation**: Apply same quality checks as platform

## Error Handling

### Exception Hierarchy

```python
class ApifyPlatformError(Exception):
    """Base exception for platform API errors."""
    pass

class ApifyPlatformAuthError(ApifyPlatformError):
    """Authentication failures."""
    pass

class ApifyPlatformTimeoutError(ApifyPlatformError):
    """Request timeouts."""
    pass

class ApifyPlatformJobError(ApifyPlatformError):
    """Actor run failures."""
    pass
```

### Error Handling Patterns

```python
async def run_scraper_with_retry(self, scraper_name: str, skus: List[str], max_retries: int = 3):
    """Run scraper with retry logic."""
    for attempt in range(max_retries):
        try:
            return await self.run_scraper(scraper_name, skus)
        except ApifyPlatformTimeoutError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            raise
        except ApifyPlatformAuthError:
            # Don't retry auth errors
            raise
```

### Error Mapping

Platform errors are mapped to testing framework errors:

```python
try:
    run_id = await self._platform_client.run_actor(actor_id, input_data)
except ApifyPlatformAuthError as e:
    raise PlatformTestingAuthError(str(e)) from e
except ApifyPlatformTimeoutError as e:
    raise PlatformTestingTimeoutError(str(e)) from e
except ApifyPlatformJobError as e:
    raise PlatformTestingJobError(str(e)) from e
```

## Rate Limiting

### Understanding Limits

Apify platform has rate limits:
- **Requests per minute**: Varies by plan
- **Concurrent runs**: Limited by account
- **Data transfer**: Bandwidth limits
- **Storage**: Dataset size limits

### Rate Limit Handling

```python
async def _make_request_with_retry(self, method: str, endpoint: str, **kwargs) -> Dict:
    """Make request with rate limit handling."""
    max_retries = 3
    base_delay = 1

    for attempt in range(max_retries):
        try:
            return await self._make_request(method, endpoint, **kwargs)
        except ApifyPlatformError as e:
            if "rate limit" in str(e).lower():
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Rate limited, retrying in {delay}s")
                await asyncio.sleep(delay)
                continue
            raise
```

### Best Practices

1. **Batch Operations**: Group multiple operations
2. **Exponential Backoff**: Increase delay between retries
3. **Concurrent Limits**: Limit simultaneous requests
4. **Caching**: Cache frequently accessed data

## Monitoring

### Platform Metrics

Track key platform metrics:

```python
async def get_platform_metrics(self) -> Dict[str, Any]:
    """Get platform usage metrics."""
    # This would integrate with Apify billing/usage APIs
    return {
        "runs_today": 0,
        "data_processed": 0,
        "credits_used": 0,
        "rate_limits": {}
    }
```

### Integration Monitoring

Monitor API integration health:

- **Response Times**: Track API call latency
- **Success Rates**: Monitor request success/failure
- **Error Patterns**: Identify common failure modes
- **Resource Usage**: Track memory and CPU usage

### Logging

Comprehensive logging for API interactions:

```python
logger.info(f"Starting actor run for '{actor_id}' with {len(input_data)} SKUs")
logger.debug(f"Run input: {json.dumps(input_data, indent=2)}")
logger.info(f"Started actor run with ID: {run_id}")
logger.warning(f"Rate limited on {endpoint}, retrying...")
logger.error(f"API request failed: {response.status_code} - {response.text}")
```

## Advanced Integration

### Custom Webhooks

Set up webhooks for real-time notifications:

```python
# Webhook payload structure
webhook_payload = {
    "eventType": "ACTOR.RUN.SUCCEEDED",
    "eventData": {
        "actorId": "actor_id",
        "actorRunId": "run_id",
        "datasetId": "dataset_id",
        "status": "SUCCEEDED"
    }
}
```

### Batch Processing

Handle large datasets efficiently:

```python
async def process_large_dataset(self, items: List[Dict], batch_size: int = 1000):
    """Process items in batches to avoid memory issues."""
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        await self.upload_dataset_items(dataset_id, batch)
        await asyncio.sleep(0.1)  # Rate limiting
```

### Connection Pooling

Optimize HTTP connections:

```python
# Configure connection pooling
limits = httpx.Limits(max_keepalive_connections=20, max_connections=100)
timeout = httpx.Timeout(30.0, connect=10.0)

async with httpx.AsyncClient(
    limits=limits,
    timeout=timeout,
    headers=self._headers
) as client:
    # Use client for requests
```

## Troubleshooting

### Common Issues

**Authentication Failures**
```
ApifyPlatformAuthError: Authentication failed: 401
```
- Verify API token validity
- Check token permissions
- Confirm account status

**Rate Limiting**
```
ApifyPlatformError: Rate limit exceeded
```
- Implement exponential backoff
- Reduce request frequency
- Upgrade Apify plan

**Timeout Errors**
```
ApifyPlatformTimeoutError: Request timeout
```
- Increase timeout values
- Check network connectivity
- Optimize request size

**Actor Not Found**
```
ApifyPlatformError: Actor not found
```
- Verify actor ID spelling
- Confirm actor is deployed
- Check actor visibility settings

### Debug Tools

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Enable httpx debug logging
logging.getLogger("httpx").setLevel(logging.DEBUG)
```

Test API connectivity:

```bash
# Test basic API access
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.apify.com/v2/datasets

# Test actor access
curl -H "Authorization: Bearer YOUR_TOKEN" https://api.apify.com/v2/acts/YOUR_ACTOR_ID
```

## Best Practices

### Security
- Store API tokens securely
- Rotate tokens regularly
- Use least-privilege access
- Monitor token usage

### Performance
- Use connection pooling
- Implement caching
- Batch operations
- Monitor resource usage

### Reliability
- Implement retry logic
- Handle rate limits gracefully
- Monitor error patterns
- Set up alerts

### Maintainability
- Document API integrations
- Version API clients
- Test integrations regularly
- Keep dependencies updated

This integration guide ensures reliable and efficient interaction with the Apify platform API for the ProductScraper testing framework.