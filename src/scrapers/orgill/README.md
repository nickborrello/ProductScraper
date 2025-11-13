# Orgill Product Scraper

Enterprise-grade web scraper for extracting product data from Orgill's website with login authentication, comprehensive error handling, and reliability features.

## 🚀 Features

### Core Scraping Capabilities

- **Login Authentication**: Automated login with cookie consent handling and session management
- **Product Search & Discovery**: Direct SKU-based product search with result validation
- **Data Extraction**: Comprehensive product information including name, brand, weight, and images
- **Multi-Image Support**: Extracts all product images from Orgill's image galleries
- **SKU-Based Processing**: Processes products by SKU for precise targeting

### Enterprise-Grade Features

- **Session Management**: Smart browser session handling with automatic cleanup
- **Cookie Consent Handling**: Advanced detection and handling of various cookie banners
- **Rate Limiting**: Configurable delays with randomized timing to avoid detection
- **Retry Logic**: Exponential backoff with configurable retry attempts for failed requests
- **Data Validation**: Multi-layer validation ensuring data completeness and quality

### Monitoring & Observability

- **Comprehensive Metrics**: Success rates, response times, error tracking
- **Real-time Monitoring**: Live performance dashboards and alerting
- **Data Quality Validation**: Automated validation with quality scoring
- **Detailed Logging**: Structured logging for debugging and monitoring

### Reliability Features

- **Error Recovery**: Graceful handling of network issues and site changes
- **Browser Rotation**: Automatic browser session rotation to avoid blocking
- **Timeout Handling**: Intelligent timeout management for different operations
- **Circuit Breaker Pattern**: Prevents cascade failures with automatic recovery

## 📊 Input Schema

```json
{
  "skus": ["string"],
  "large_scale_test": false,
  "batch_size": 50,
  "test_name": "performance_test"
}
```

### Input Parameters

| Parameter          | Type       | Required | Description                                      |
| ------------------ | ---------- | -------- | ------------------------------------------------ |
| `skus`             | `string[]` | ✅       | Array of product SKUs to scrape                  |
| `large_scale_test` | `boolean`  | ❌       | Enable large-scale performance testing mode      |
| `batch_size`       | `number`   | ❌       | Batch size for large-scale testing (default: 50) |
| `test_name`        | `string`   | ❌       | Name for the performance test run                |

## 📤 Output Schema

```json
{
  "SKU": "string",
  "Name": "string",
  "Brand": "string",
  "Weight": "string",
  "Image URLs": ["string"]
}
```

### Output Fields

| Field        | Type       | Description                                     |
| ------------ | ---------- | ----------------------------------------------- |
| `SKU`        | `string`   | Product SKU identifier                          |
| `Name`       | `string`   | Full product name with model numbers removed    |
| `Brand`      | `string`   | Product brand/manufacturer                      |
| `Weight`     | `string`   | Product weight (normalized to consistent units) |
| `Image URLs` | `string[]` | Array of product image URLs                     |

## 🏗️ Architecture

### Core Components

1. **BrowserSession**: Manages Chrome browser instances with automatic rotation
2. **RateLimiter**: Implements intelligent rate limiting with randomized delays
3. **OrgillScraper**: Main scraper class handling login and product extraction
4. **DataValidator**: Multi-layer data validation with quality scoring
5. **Monitoring**: Comprehensive metrics collection and reporting

### Data Flow

```
Input SKUs → Login Authentication → Browser Session → Product Search → Data Extraction → Validation → Output
```

## 🛠️ Configuration

### Environment Variables

| Variable          | Description                            | Default |
| ----------------- | -------------------------------------- | ------- |
| `ORGILL_USERNAME` | Orgill account username                | None    |
| `ORGILL_PASSWORD` | Orgill account password                | None    |
| `APIFY_PROXY_URL` | Apify proxy URL for enhanced anonymity | None    |
| `APIFY_INPUT`     | JSON input for local testing           | None    |

### Module-Level Configuration

```python
# Orgill scraper configuration
HEADLESS = True  # Set to False only if troubleshooting requires visible browser
TEST_SKU = "755625011305"  # SKU for testing
```

## 🚀 Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export ORGILL_USERNAME="your_username"
export ORGILL_PASSWORD="your_password"

# Run with test SKU
python src/main.py

# Run with custom SKUs
python src/main.py '{"skus": ["SKU1", "SKU2"]}'
```

### Apify Platform Deployment

```bash
# Login to Apify
apify login

# Deploy to Apify
apify push
```

### Docker Deployment

```bash
# Build Docker image
docker build -t orgill-scraper .

# Run locally
docker run -e ORGILL_USERNAME="your_username" -e ORGILL_PASSWORD="your_password" orgill-scraper
```

## 📈 Performance & Scaling

### Recommended Configurations

| Use Case     | Batch Size | Rate Limit | Expected Throughput |
| ------------ | ---------- | ---------- | ------------------- |
| Small Batch  | 10-25      | 2-5 sec    | 10-20 SKUs/min      |
| Medium Batch | 25-50      | 3-8 sec    | 5-15 SKUs/min       |
| Large Scale  | 50-100     | 5-15 sec   | 3-10 SKUs/min       |

### Monitoring Metrics

- **Success Rate**: Percentage of successfully scraped products
- **Response Time**: Average time per product scrape
- **Error Rate**: Breakdown of failure types and frequencies
- **Login Success**: Authentication success rate
- **Resource Usage**: Memory and CPU utilization trends

## 🔧 Troubleshooting

### Common Issues

#### Login Failures

- **Cause**: Invalid credentials or account issues
- **Solution**: Verify ORGILL_USERNAME and ORGILL_PASSWORD environment variables

#### Cookie Consent Issues

- **Cause**: Site updated cookie banner selectors
- **Solution**: Update consent selectors in `_handle_cookie_consent()` method

#### High Block Rate

- **Cause**: Aggressive scraping patterns detected
- **Solution**: Increase delays in RateLimiter, reduce batch size

#### Memory Issues

- **Cause**: Large-scale testing with insufficient resources
- **Solution**: Reduce batch size, implement session rotation

#### Data Quality Issues

- **Cause**: Site layout changes or selector updates
- **Solution**: Update CSS selectors in `_extract_product_data()` method

### Debug Mode

Enable detailed logging for troubleshooting:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🧪 Testing

### Unit Tests

```bash
python -m pytest tests/
```

### Integration Testing

```bash
# Test with real credentials
export ORGILL_USERNAME="your_username"
export ORGILL_PASSWORD="your_password"
python src/main.py '{"skus": ["755625011305"]}'
```

### Performance Benchmarking

The scraper includes built-in performance testing that measures:

- Throughput (SKUs per minute)
- Success rates over time
- Resource utilization
- Bottleneck identification

## 📋 Dependencies

### Core Dependencies

- `apify` - Apify SDK for actor lifecycle management
- `selenium` - Web browser automation
- `beautifulsoup4` - HTML parsing and data extraction
- `fake-useragent` - Dynamic user agent rotation
- `tenacity` - Retry logic with exponential backoff

### Optional Dependencies

- `psutil` - System resource monitoring (for large-scale testing)

## 🔒 Security & Compliance

- **Credential Management**: Secure environment variable handling for login credentials
- **Session Security**: Automatic session cleanup and rotation
- **Rate Limiting**: Respects site performance and avoids overloading
- **Data Validation**: Ensures output data integrity and completeness

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Implement changes with comprehensive tests
4. Update documentation
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section above
2. Review the monitoring logs for error details
3. Test with a single SKU in non-headless mode for debugging
4. Ensure all environment variables are properly set

## 🔄 Version History

- **v1.0.0**: Initial enterprise-grade Orgill scraper implementation
- Login authentication with cookie consent handling
- Comprehensive error handling and retry logic
- Production-ready deployment configuration
