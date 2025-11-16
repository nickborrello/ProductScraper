# Central Pet Product Scraper

Enterprise-grade web scraper for extracting product data from Central Pet's website with advanced anti-detection measures, monitoring, and reliability features.

## 🚀 Features

### Core Scraping Capabilities

- **Product Search & Discovery**: Automated search using Central Pet's search functionality
- **Data Extraction**: Comprehensive product information including name, brand, weight, and images
- **Multi-Image Support**: Extracts all product images from carousels and galleries
- **SKU-Based Processing**: Processes products by SKU for precise targeting

### Enterprise-Grade Features

- **Anti-Detection Measures**: Randomized user agents, viewport sizes, and browser fingerprints
- **CAPTCHA Handling**: Advanced detection and resolution for various CAPTCHA types
- **Proxy Rotation**: Automatic proxy switching with failure detection and recovery
- **Circuit Breaker Pattern**: Intelligent failure handling with automatic recovery
- **Session Management**: Smart browser session rotation to avoid blocking
- **Rate Limiting**: Configurable delays with exponential backoff

### Monitoring & Observability

- **Comprehensive Metrics**: Success rates, response times, error tracking
- **Real-time Monitoring**: Live performance dashboards and alerting
- **Data Quality Validation**: Automated validation with quality scoring
- **Large-Scale Testing**: Performance benchmarking and capacity planning

### Reliability Features

- **Retry Logic**: Exponential backoff with configurable retry attempts
- **Error Recovery**: Graceful handling of network issues and site changes
- **Data Validation**: Multi-layer validation ensuring data completeness
- **Circuit Breaker**: Prevents cascade failures with automatic recovery

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
| `Name`       | `string`   | Full product name with color/size variants      |
| `Brand`      | `string`   | Product brand/manufacturer                      |
| `Weight`     | `string`   | Product weight (normalized to consistent units) |
| `Image URLs` | `string[]` | Array of product image URLs                     |

## 🏗️ Architecture

### Core Components

1. **BrowserSession**: Manages Chrome browser instances with automatic rotation
2. **RateLimiter**: Implements intelligent rate limiting with randomized delays
3. **CaptchaDetector**: Advanced CAPTCHA detection and handling system
4. **ProxyManager**: Automatic proxy rotation and health monitoring
5. **DataValidator**: Multi-layer data validation with quality scoring
6. **Monitoring**: Comprehensive metrics collection and reporting
7. **CircuitBreaker**: Failure prevention and automatic recovery

### Data Flow

```
Input SKUs → Search URL Generation → Browser Automation → CAPTCHA Handling → Data Extraction → Validation → Output
```

## 🛠️ Configuration

### Environment Variables

| Variable          | Description                            | Default |
| ----------------- | -------------------------------------- | ------- |
| `APIFY_PROXY_URL` | Apify proxy URL for enhanced anonymity | None    |
| `APIFY_INPUT`     | JSON input for local testing           | None    |

### Module-Level Configuration

```python
# Central Pet scraper configuration
HEADLESS = True  # Set to False only if CAPTCHA solving requires visible browser
TEST_SKU = "your_test_sku_here"  # SKU for testing
```

## 🚀 Deployment

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

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
docker build -t central-pet-scraper .

# Run locally
docker run central-pet-scraper
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
- **CAPTCHA Events**: Frequency and resolution success rate
- **Resource Usage**: Memory and CPU utilization trends

## 🔧 Troubleshooting

### Common Issues

#### High Block Rate

- **Cause**: Aggressive scraping patterns detected
- **Solution**: Increase delays, enable proxy rotation, reduce batch size

#### CAPTCHA Challenges

- **Cause**: Site protection mechanisms triggered
- **Solution**: Set `HEADLESS = False` for manual intervention, increase delays

#### Memory Issues

- **Cause**: Large-scale testing with insufficient resources
- **Solution**: Reduce batch size, implement session rotation

#### Data Quality Issues

- **Cause**: Site layout changes or selector updates
- **Solution**: Update CSS selectors in `extract_product_data()` function

### Debug Mode

To run the scraper in debug mode, you can use the `HEADLESS` and `DEBUG_MODE` environment variables. This will run the browser in a visible window and pause the script at certain points for manual inspection.

```bash
# Run the Central Pet scraper in debug mode
HEADLESS=False DEBUG_MODE=True python src/scrapers/central_pet/src/main.py
```

This is useful for observing the scraper's behavior and debugging issues with selectors or site changes.

## 🧪 Testing

### Unit Tests

```bash
python -m pytest tests/
```

### Large-Scale Testing

```bash
python src/main.py '{"skus": ["sku1", "sku2", ...], "large_scale_test": true, "batch_size": 50}'
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

- **User Agent Rotation**: Avoids detection through varied browser fingerprints
- **Proxy Support**: Optional proxy rotation for enhanced anonymity
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
4. Ensure all dependencies are properly installed

## 🔄 Version History

- **v1.0.0**: Initial enterprise-grade Central Pet scraper implementation
- Advanced anti-detection measures
- Comprehensive monitoring and error handling
- Large-scale testing framework
- Production-ready deployment configuration
