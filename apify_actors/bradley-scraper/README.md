## Bradley Caldwell Product Scraper

An enterprise-grade Apify Actor for scraping product data from Bradley Caldwell's website. This scraper uses advanced anti-detection techniques, comprehensive error handling, and monitoring to reliably extract product information at scale.

## Features

- **Enterprise-Grade Reliability**: Circuit breaker pattern, retry logic, and comprehensive error recovery
- **Anti-Detection Measures**: User agent rotation, viewport randomization, and browser fingerprinting
- **Smart Rate Limiting**: Exponential backoff and adaptive delays to respect site limits
- **Data Validation**: Quality scoring and completeness validation for all scraped data
- **Monitoring & Observability**: Real-time performance tracking and detailed analytics
- **Proxy Integration**: Apify proxy support with automatic rotation and failure handling
- **CAPTCHA Detection**: Automated detection and handling of anti-bot measures
- **Large Scale Testing**: Built-in performance benchmarking and scalability testing

## Input Schema

```json
{
  "skus": ["string"],
  "batch_size": 50,
  "test_name": "bradley_test"
}
```

- `skus`: Array of SKU strings to scrape (required)
- `batch_size`: Number of SKUs to process in each batch (optional, default: 50)
- `test_name`: Name for the test run (optional, used for large scale testing)

## Output Data

The scraper outputs product data in the following format:

```json
{
  "SKU": "string",
  "Name": "string",
  "Brand": "string",
  "Price": "string",
  "Weight": "string",
  "Image URLs": ["string"],
  "Category": "string",
  "Product Type": "string",
  "Product On Pages": "string",
  "Special Order": "string",
  "Product Cross Sell": "string",
  "ProductDisabled": "string"
}
```

## Included Libraries

- **Apify SDK** - Actor lifecycle management and data storage
- **Selenium WebDriver** - Browser automation with Chrome
- **Beautiful Soup** - HTML parsing and data extraction
- **Tenacity** - Retry logic with exponential backoff
- **Fake UserAgent** - Dynamic user agent rotation
- **psutil** - Memory monitoring for performance tracking

## How It Works

1. **Initialization**: Sets up browser session with anti-detection measures
2. **Rate Limiting**: Applies smart delays between requests
3. **Scraping**: Searches for products by SKU and extracts data
4. **Validation**: Ensures data completeness and quality
5. **Monitoring**: Tracks performance and handles errors
6. **CAPTCHA Handling**: Detects and manages anti-bot measures
7. **Data Storage**: Saves validated product data to Apify dataset

## Local Development

### Prerequisites

- Python 3.8+
- Google Chrome browser
- Apify CLI (optional, for deployment)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
python src/main.py
```

### Large Scale Testing

```bash
# Run performance benchmarking
python test_large_scale.py --skus 100 --batch-size 25 --test-name "production_test"
```

## Deployment

### Using Apify CLI

```bash
# Login to Apify
apify login

# Deploy to Apify Platform
apify push
```

### Using Git Integration

1. Push code to Git repository
2. Connect repository in Apify Console
3. Automatic deployment on push

## Configuration

### Environment Variables

- `APIFY_PROXY_URL`: Custom proxy URL (optional)
- `APIFY_INPUT`: JSON input for local testing (optional)

### Browser Settings

- **Headless Mode**: Configurable via `HEADLESS` variable
- **User Agent Rotation**: Automatic rotation using fake-useragent
- **Viewport Randomization**: Dynamic sizing to avoid detection
- **Session Management**: Auto-rotation every 10 requests or 5 minutes

## Error Handling

- **Circuit Breaker**: Prevents cascading failures with configurable thresholds
- **Retry Logic**: 3 attempts with exponential backoff (4-10 seconds)
- **Data Validation**: Rejects incomplete or invalid product data
- **Proxy Rotation**: Automatic fallback on proxy failures

## Monitoring

- **Performance Metrics**: Response times, throughput, success rates
- **Error Tracking**: Detailed error classification and reporting
- **Resource Usage**: Memory and CPU monitoring
- **CAPTCHA Events**: Detection and handling statistics

## Testing

### Unit Tests

```bash
python -m pytest tests/unit/ -v
```

### Integration Tests

```bash
RUN_INTEGRATION_TESTS=true python -m pytest tests/integration/ -v
```

### Large Scale Testing

```bash
python test_large_scale.py --skus 1000 --batch-size 50
```

## Success Metrics

- **Block Rate**: < 5% of requests blocked
- **Success Rate**: > 95% of valid SKUs scraped successfully
- **Data Quality**: > 98% complete records
- **Response Time**: < 30 seconds per product
- **CAPTCHA Handling**: Automatic detection and resolution

## Troubleshooting

### Common Issues

1. **Chrome Driver Issues**: Ensure Chrome browser is installed and up to date
2. **Proxy Failures**: Check `APIFY_PROXY_URL` configuration
3. **CAPTCHA Blocks**: Monitor CAPTCHA detection logs
4. **Memory Issues**: Reduce batch size for large-scale operations

### Debug Mode

Set `HEADLESS = False` in the scraper code to run with visible browser for debugging.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

This project is licensed under the MIT License.
