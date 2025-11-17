# Anti-Detection Guide

This guide provides comprehensive documentation for the anti-detection system that helps scrapers avoid being blocked by websites.

## Overview

The anti-detection system consists of multiple integrated modules that work together to make scraping activities appear more human-like and avoid common detection mechanisms.

## Core Modules

### CAPTCHA Detection & Handling

**Purpose**: Detects and handles CAPTCHA challenges automatically.

**Configuration**:
```yaml
anti_detection:
  enable_captcha_detection: true
  captcha_selectors:
    - "[class*='captcha']"
    - "[id*='captcha']"
    - "[class*='recaptcha']"
    - "[id*='recaptcha']"
    - ".g-recaptcha"
    - "#captcha-container"
  max_retries_on_detection: 3
```

**How it works**:
- Scans the page for CAPTCHA-related elements using configurable selectors
- When detected, applies waiting strategies or integrates with CAPTCHA solving services
- Automatically retries failed operations after CAPTCHA resolution

**Best Practices**:
- Use site-specific CAPTCHA selectors
- Monitor CAPTCHA encounter rates
- Consider integrating with third-party CAPTCHA solving services for production use

### Rate Limiting

**Purpose**: Prevents overwhelming servers with requests by introducing intelligent delays.

**Configuration**:
```yaml
anti_detection:
  enable_rate_limiting: true
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 5.0
```

**Features**:
- **Intelligent Delays**: Random delays between min and max values
- **Exponential Backoff**: Increases delays after consecutive failures
- **Success-Based Adjustment**: Reduces delays when requests succeed

**Delay Calculation**:
```
base_delay = random.uniform(min_delay, max_delay)
if consecutive_failures > 0:
    final_delay = base_delay * (2 ** consecutive_failures)
else:
    final_delay = base_delay
```

**Best Practices**:
- Start with conservative delays (1-5 seconds)
- Monitor site response times and adjust accordingly
- Use longer delays during peak hours
- Implement different delay strategies for different site sections

### Human Behavior Simulation

**Purpose**: Makes browser interactions appear more human-like.

**Configuration**:
```yaml
anti_detection:
  enable_human_simulation: true
```

**Simulated Behaviors**:

| Action | Pre-Action Delay | Post-Action Delay | Description |
|--------|------------------|-------------------|-------------|
| `navigate` | - | 1-3 seconds | Simulate page reading time |
| `click` | 0.1-0.5 seconds | 0.5-2 seconds | Mouse movement and reaction time |
| `input_text` | 0.05-0.2 seconds | - | Typing delays between characters |
| `wait` | - | - | Explicit pauses for processing |

**Best Practices**:
- Enable for sites with sophisticated bot detection
- Adjust timing based on observed human behavior patterns
- Combine with random mouse movements for enhanced realism

### Session Rotation

**Purpose**: Rotates browser sessions to avoid long-term tracking.

**Configuration**:
```yaml
anti_detection:
  enable_session_rotation: true
  session_rotation_interval: 100
```

**How it works**:
- Tracks the number of requests in the current session
- Automatically creates a new browser instance when the interval is reached
- Preserves cookies and session data when beneficial
- Uses unique profile suffixes to avoid conflicts

**Best Practices**:
- Set intervals based on site session limits
- Use shorter intervals for heavily monitored sites
- Monitor session success rates
- Consider IP rotation in conjunction with session rotation

### Blocking Page Detection & Recovery

**Purpose**: Detects blocking pages and attempts automatic recovery.

**Configuration**:
```yaml
anti_detection:
  enable_blocking_handling: true
  blocking_selectors:
    - "[class*='blocked']"
    - "[id*='blocked']"
    - "[class*='banned']"
    - "[id*='banned']"
    - "[class*='access-denied']"
    - "[id*='access-denied']"
```

**Detection Methods**:
- **CSS Selector Matching**: Scans for blocking-related elements
- **Page Title Analysis**: Checks for blocking keywords in page title
- **Content Analysis**: Looks for blocking messages in page content

**Recovery Strategies**:
- **Waiting**: Applies longer delays before retrying
- **Session Rotation**: Creates new browser session
- **Proxy Rotation**: Changes IP address (when integrated)

## Integration with WorkflowExecutor

The anti-detection system integrates seamlessly with the WorkflowExecutor:

```python
from src.scrapers.executor.workflow_executor import WorkflowExecutor
from src.scrapers.parser.yaml_parser import YAMLParser

# Load configuration with anti-detection
parser = YAMLParser()
config = parser.parse("scraper_config.yaml")

# Execute with anti-detection
executor = WorkflowExecutor(config, headless=True)
results = executor.execute_workflow()
```

### Hook System

The system uses pre-action and post-action hooks:

- **Pre-action Hook**: Executes before each workflow step
  - Applies rate limiting
  - Simulates human behavior
  - Checks for blocking pages
  - Detects CAPTCHAs

- **Post-action Hook**: Executes after each workflow step
  - Updates rate limiting based on success/failure
  - Simulates post-action human behavior

### Error Handling Integration

When workflow steps fail, the anti-detection system attempts recovery:

```python
try:
    # Execute workflow step
    self._execute_step(step)
except Exception as e:
    # Try anti-detection recovery
    if self.anti_detection_manager:
        if self.anti_detection_manager.handle_error(e, action, retry_count):
            # Recovery successful, retry the step
            return self._execute_step(step)
    # Recovery failed, re-raise exception
    raise
```

## Configuration Examples

### Basic Anti-Detection Setup

```yaml
name: "basic_scraper"
base_url: "https://www.example.com"
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 3.0
```

### High-Security Site Configuration

```yaml
name: "secure_site_scraper"
base_url: "https://www.high-security-site.com"
timeout: 60
retries: 5
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: true
  enable_blocking_handling: true
  captcha_selectors:
    - ".custom-captcha-class"
    - "#site-specific-captcha"
  blocking_selectors:
    - ".site-blocked-message"
    - "#access-denied"
  rate_limit_min_delay: 3.0
  rate_limit_max_delay: 10.0
  session_rotation_interval: 25
  max_retries_on_detection: 5
```

### Minimal Configuration for Fast Scraping

```yaml
name: "fast_scraper"
base_url: "https://www.fast-site.com"
anti_detection:
  enable_captcha_detection: false
  enable_rate_limiting: true
  enable_human_simulation: false
  enable_session_rotation: false
  enable_blocking_handling: false
  rate_limit_min_delay: 0.5
  rate_limit_max_delay: 1.5
```

## Best Practices by Site Type

### E-commerce Sites (Amazon, eBay)

```yaml
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: true
  rate_limit_min_delay: 2.0
  rate_limit_max_delay: 8.0
  session_rotation_interval: 50
```

**Rationale**:
- High bot detection sophistication
- Frequent CAPTCHA challenges
- Session-based tracking
- Product data is valuable target

### News/Media Sites

```yaml
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_blocking_handling: true
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 4.0
```

**Rationale**:
- Content protection measures
- Traffic monitoring
- Ad revenue protection
- Less aggressive than e-commerce

### Government/Public Sites

```yaml
anti_detection:
  enable_captcha_detection: false
  enable_rate_limiting: true
  enable_human_simulation: false
  enable_blocking_handling: false
  rate_limit_min_delay: 0.5
  rate_limit_max_delay: 2.0
```

**Rationale**:
- Usually less sophisticated bot detection
- Focus on rate limiting rather than advanced detection
- Public data with fewer restrictions

### Social Media Platforms

```yaml
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: true
  enable_blocking_handling: true
  rate_limit_min_delay: 3.0
  rate_limit_max_delay: 15.0
  session_rotation_interval: 20
  max_retries_on_detection: 3
```

**Rationale**:
- Advanced bot detection systems
- Account-based tracking
- API rate limits
- Legal restrictions on automated access

## Monitoring and Tuning

### Key Metrics to Monitor

1. **Success Rate**: Percentage of successful requests
2. **CAPTCHA Encounter Rate**: How often CAPTCHAs are encountered
3. **Average Request Time**: Including anti-detection delays
4. **Session Longevity**: How long sessions last before rotation
5. **Blocking Frequency**: How often blocking pages are encountered

### Tuning Strategies

#### High CAPTCHA Rate
- Increase delays between requests
- Enable session rotation more frequently
- Add more human-like behavior simulation
- Consider using residential proxies

#### Frequent Blocking
- Reduce request frequency
- Implement longer backoff periods
- Use different user agents and fingerprints
- Distribute requests across different IP addresses

#### Slow Performance
- Optimize delay ranges for the specific site
- Disable unnecessary anti-detection features
- Use faster proxy connections
- Implement parallel scraping with different sessions

### Logging and Debugging

Enable detailed logging to monitor anti-detection effectiveness:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Monitor anti-detection events
logger = logging.getLogger('anti_detection')
```

## Troubleshooting Common Issues

### CAPTCHA Detection Not Working

**Symptoms**: CAPTCHAs not being detected despite being present

**Solutions**:
1. Update CAPTCHA selectors for the specific site
2. Check if CAPTCHAs use non-standard HTML structures
3. Enable debug logging to see detection attempts
4. Consider iframe-based CAPTCHAs

### Rate Limiting Too Aggressive

**Symptoms**: Scraping too slow, missing time-sensitive data

**Solutions**:
1. Reduce min/max delay values
2. Monitor site response times and adjust accordingly
3. Use different delay strategies for different operations
4. Implement adaptive rate limiting based on success rates

### Session Rotation Failing

**Symptoms**: Browser creation errors during session rotation

**Solutions**:
1. Check browser driver compatibility
2. Ensure sufficient system resources
3. Verify profile directory permissions
4. Reduce concurrent browser instances

### Blocking Detection False Positives

**Symptoms**: Legitimate pages being flagged as blocked

**Solutions**:
1. Refine blocking selectors to be more specific
2. Add exceptions for known legitimate pages
3. Adjust content analysis keywords
4. Implement confidence scoring for detection

### Human Simulation Ineffective

**Symptoms**: Still being detected despite human simulation

**Solutions**:
1. Increase timing variability
2. Add mouse movement simulation
3. Implement more realistic interaction patterns
4. Use behavioral fingerprints from real user sessions

## Advanced Configuration

### Custom Anti-Detection Modules

Extend the system with custom modules:

```python
from src.core.anti_detection_manager import AntiDetectionManager

class CustomAntiDetectionManager(AntiDetectionManager):
    def custom_pre_action_hook(self, action, params):
        # Custom logic
        pass

    def custom_post_action_hook(self, action, params, success):
        # Custom logic
        pass
```

### Integration with External Services

#### CAPTCHA Solving Services

```python
class CaptchaSolver:
    def solve_captcha(self, site_key, url):
        # Integrate with 2Captcha, Anti-Captcha, etc.
        pass
```

#### Proxy Rotation

```python
class ProxyManager:
    def rotate_proxy(self):
        # Implement proxy rotation logic
        pass
```

### Performance Optimization

#### Concurrent Scraping

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

async def scrape_concurrent(configs, proxy_list):
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Distribute across different proxies/sessions
        pass
```

#### Caching Strategies

```python
class ResponseCache:
    def __init__(self, ttl=3600):
        self.cache = {}
        self.ttl = ttl

    def get(self, url):
        # Implement caching logic
        pass
```

## Security Considerations

### Data Privacy
- Avoid logging sensitive information
- Implement proper credential management
- Use encrypted storage for session data

### Legal Compliance
- Respect robots.txt files
- Adhere to website terms of service
- Implement rate limiting to avoid DDoS-like behavior
- Monitor for legal changes in scraping regulations

### Resource Management
- Limit concurrent browser instances
- Implement proper cleanup of browser sessions
- Monitor memory and CPU usage
- Set reasonable timeouts to prevent hanging

## Future Enhancements

### Planned Features
- Machine learning-based behavior simulation
- Advanced fingerprint randomization
- Integration with residential proxy networks
- Real-time adaptation to detection changes
- Cross-session learning and optimization

### Research Areas
- Advanced browser fingerprinting techniques
- AI-powered CAPTCHA recognition
- Predictive rate limiting algorithms
- Behavioral pattern analysis and replication