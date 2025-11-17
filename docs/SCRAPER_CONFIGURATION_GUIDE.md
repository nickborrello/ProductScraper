# Scraper Configuration Guide

This guide provides comprehensive documentation for configuring scrapers using the modular YAML-based system.

## YAML Schema Reference

### Root Configuration

```yaml
name: string              # Required: Unique scraper identifier
base_url: string          # Required: Base URL for the scraper
timeout: integer          # Optional: Default timeout in seconds (default: 30)
retries: integer          # Optional: Number of retries on failure (default: 3)
selectors: list           # Optional: List of data extraction selectors
workflows: list           # Optional: List of workflow steps
login: object             # Optional: Login configuration
anti_detection: object    # Optional: Anti-detection configuration
```

### Selector Configuration

```yaml
selectors:
  - name: string          # Required: Field name for extracted data
    selector: string      # Required: CSS selector for the element
    attribute: string     # Optional: Attribute to extract ('text', 'href', 'src', etc.)
    multiple: boolean     # Optional: Extract multiple elements (default: false)
```

### Workflow Step Configuration

```yaml
workflows:
  - action: string        # Required: Action type
    params: object        # Optional: Action parameters
```

### Login Configuration

```yaml
login:
  url: string             # Required: Login page URL
  username_field: string  # Required: CSS selector for username input
  password_field: string  # Required: CSS selector for password input
  submit_button: string   # Required: CSS selector for submit button
  success_indicator: string # Optional: CSS selector indicating successful login
```

### Anti-Detection Configuration

```yaml
anti_detection:
  enable_captcha_detection: boolean     # Optional: Enable CAPTCHA detection (default: true)
  enable_rate_limiting: boolean         # Optional: Enable rate limiting (default: true)
  enable_human_simulation: boolean      # Optional: Enable human behavior simulation (default: true)
  enable_session_rotation: boolean      # Optional: Enable session rotation (default: true)
  enable_blocking_handling: boolean     # Optional: Enable blocking page handling (default: true)
  captcha_selectors: list               # Optional: Custom CAPTCHA selectors
  blocking_selectors: list              # Optional: Custom blocking selectors
  rate_limit_min_delay: float           # Optional: Minimum delay between requests (default: 1.0)
  rate_limit_max_delay: float           # Optional: Maximum delay between requests (default: 5.0)
  session_rotation_interval: integer    # Optional: Requests before session rotation (default: 100)
  max_retries_on_detection: integer     # Optional: Max retries on detection (default: 3)
```

## Workflow Actions

### Navigation Actions

#### navigate
Navigate to a URL.

```yaml
- action: "navigate"
  params:
    url: "https://example.com/search?q={query}"  # URL with template variables
    wait_after: 2                                # Optional: Wait time after navigation
```

#### wait_for
Wait for an element to be present.

```yaml
- action: "wait_for"
  params:
    selector: ".search-results"  # CSS selector to wait for
    timeout: 10                  # Optional: Timeout in seconds
```

### Interaction Actions

#### click
Click on an element.

```yaml
- action: "click"
  params:
    selector: ".submit-button"   # CSS selector for element to click
    wait_after: 1                # Optional: Wait time after click
```

#### input_text
Input text into a form field.

```yaml
- action: "input_text"
  params:
    selector: "#search-input"    # CSS selector for input field
    text: "{search_term}"        # Text to input (supports template variables)
    clear_first: true            # Optional: Clear field before input (default: true)
```

### Timing Actions

#### wait
Simple wait/delay.

```yaml
- action: "wait"
  params:
    seconds: 2                   # Wait time in seconds
```

### Data Extraction Actions

#### extract_single
Extract a single value using a named selector.

```yaml
- action: "extract_single"
  params:
    field: "product_name"        # Result field name
    selector: "title_selector"   # Name of selector from selectors list
```

#### extract_multiple
Extract multiple values using a named selector.

```yaml
- action: "extract_multiple"
  params:
    field: "image_urls"          # Result field name
    selector: "image_selector"   # Name of selector from selectors list
```

#### extract
Extract multiple fields at once (legacy compatibility).

```yaml
- action: "extract"
  params:
    fields: ["name", "price", "description"]  # List of field names
```

### Authentication Actions

#### login
Execute login workflow with credentials.

```yaml
- action: "login"
  params:
    username: "{username}"       # Username (supports template variables)
    password: "{password}"       # Password (supports template variables)
```

### Anti-Detection Actions

#### detect_captcha
Detect CAPTCHA presence on current page.

```yaml
- action: "detect_captcha"
  params: {}  # No parameters required
```

#### handle_blocking
Handle blocking pages.

```yaml
- action: "handle_blocking"
  params: {}  # No parameters required
```

#### rate_limit
Apply rate limiting delay.

```yaml
- action: "rate_limit"
  params:
    delay: 3.0  # Optional: Custom delay in seconds
```

#### simulate_human
Simulate human-like behavior.

```yaml
- action: "simulate_human"
  params:
    behavior: "reading"  # Optional: 'reading', 'typing', 'navigation', or 'random'
    duration: 2.0        # Optional: Duration in seconds
```

#### rotate_session
Force session rotation.

```yaml
- action: "rotate_session"
  params: {}  # No parameters required
```

## Selector Configuration Examples

### Basic Text Extraction

```yaml
selectors:
  - name: "product_title"
    selector: "#productTitle"
    attribute: "text"
```

### Link URL Extraction

```yaml
selectors:
  - name: "product_url"
    selector: ".product-link"
    attribute: "href"
```

### Image Source Extraction

```yaml
selectors:
  - name: "main_image"
    selector: "#main-image"
    attribute: "src"
```

### Multiple Element Extraction

```yaml
selectors:
  - name: "gallery_images"
    selector: ".gallery img"
    attribute: "src"
    multiple: true
```

### Fallback Selectors

```yaml
selectors:
  - name: "product_name"
    selector: "#productTitle, .product-title, h1.product-name"
    attribute: "text"
```

## Complete Configuration Examples

### Example 1: E-commerce Product Scraper

```yaml
name: "ecommerce_scraper"
base_url: "https://www.example-shop.com"
timeout: 30
retries: 3

selectors:
  - name: "product_name"
    selector: "#product-title, .product-name, h1"
    attribute: "text"
  - name: "price"
    selector: ".price, #price, .product-price"
    attribute: "text"
  - name: "description"
    selector: "#product-description, .description"
    attribute: "text"
  - name: "images"
    selector: ".product-gallery img, #main-image"
    attribute: "src"
    multiple: true
  - name: "specifications"
    selector: ".specs-table tr, #specifications li"
    attribute: "text"
    multiple: true

workflows:
  - action: "navigate"
    params:
      url: "https://www.example-shop.com/products/{product_id}"
  - action: "wait_for"
    params:
      selector: "#product-title"
      timeout: 15
  - action: "extract"
    params:
      fields: ["product_name", "price", "description", "images", "specifications"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  rate_limit_min_delay: 1.5
  rate_limit_max_delay: 4.0
```

### Example 2: Search and Extract Workflow

```yaml
name: "search_scraper"
base_url: "https://www.example.com"
timeout: 45
retries: 5

selectors:
  - name: "search_result_title"
    selector: ".search-result h3, .result-title"
    attribute: "text"
    multiple: true
  - name: "search_result_url"
    selector: ".search-result a, .result-link"
    attribute: "href"
    multiple: true
  - name: "result_snippet"
    selector: ".search-result .snippet, .result-description"
    attribute: "text"
    multiple: true

workflows:
  - action: "navigate"
    params:
      url: "https://www.example.com/search"
  - action: "wait_for"
    params:
      selector: "#search-input"
      timeout: 10
  - action: "input_text"
    params:
      selector: "#search-input"
      text: "{search_query}"
  - action: "click"
    params:
      selector: "#search-button, .search-submit"
  - action: "wait_for"
    params:
      selector: ".search-results"
      timeout: 20
  - action: "extract"
    params:
      fields: ["search_result_title", "search_result_url", "result_snippet"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_blocking_handling: true
  captcha_selectors:
    - "[class*='captcha']"
    - "#captcha-container"
    - ".recaptcha"
  blocking_selectors:
    - "[class*='blocked']"
    - ".access-denied"
    - "#blocked-message"
```

### Example 3: Login Required Scraper

```yaml
name: "authenticated_scraper"
base_url: "https://www.members-only.com"
timeout: 60
retries: 3

login:
  url: "https://www.members-only.com/login"
  username_field: "#username, #email"
  password_field: "#password"
  submit_button: "#login-btn, .login-submit"
  success_indicator: ".dashboard, #user-menu"

selectors:
  - name: "member_data"
    selector: ".member-info, #profile-data"
    attribute: "text"
  - name: "premium_content"
    selector: ".premium-section"
    attribute: "text"
    multiple: true

workflows:
  - action: "login"
    params:
      username: "{username}"
      password: "{password}"
  - action: "wait_for"
    params:
      selector: ".dashboard"
      timeout: 30
  - action: "navigate"
    params:
      url: "https://www.members-only.com/member-area"
  - action: "wait_for"
    params:
      selector: ".member-info"
      timeout: 15
  - action: "extract"
    params:
      fields: ["member_data", "premium_content"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: true
  session_rotation_interval: 50
  max_retries_on_detection: 5
```

### Example 4: Complex Multi-Step Workflow

```yaml
name: "complex_workflow_scraper"
base_url: "https://www.complex-site.com"
timeout: 90
retries: 5

selectors:
  - name: "category_links"
    selector: ".category-list a"
    attribute: "href"
    multiple: true
  - name: "product_links"
    selector: ".product-grid a.product-link"
    attribute: "href"
    multiple: true
  - name: "product_details"
    selector: ".product-details"
    attribute: "text"

workflows:
  # Step 1: Navigate to main page and extract categories
  - action: "navigate"
    params:
      url: "https://www.complex-site.com"
  - action: "wait_for"
    params:
      selector: ".category-list"
      timeout: 20
  - action: "extract_multiple"
    params:
      field: "category_urls"
      selector: "category_links"

  # Step 2: Process first category
  - action: "navigate"
    params:
      url: "{category_urls[0]}"  # Use first category URL
  - action: "wait_for"
    params:
      selector: ".product-grid"
      timeout: 25
  - action: "extract_multiple"
    params:
      field: "product_urls"
      selector: "product_links"

  # Step 3: Extract product details
  - action: "navigate"
    params:
      url: "{product_urls[0]}"  # Use first product URL
  - action: "wait_for"
    params:
      selector: ".product-details"
      timeout: 15
  - action: "extract_single"
    params:
      field: "details"
      selector: "product_details"

  # Step 4: Simulate human reading
  - action: "simulate_human"
    params:
      behavior: "reading"
      duration: 3.0

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_blocking_handling: true
  enable_session_rotation: true
  rate_limit_min_delay: 2.0
  rate_limit_max_delay: 8.0
  session_rotation_interval: 25
  max_retries_on_detection: 3
```

## Template Variables

The system supports template variables in workflow parameters:

- `{sku}`, `{product_id}`, `{search_query}`: Dynamic values passed at runtime
- `{username}`, `{password}`: Credentials for login
- `{category_urls[0]}`, `{product_urls[0]}`: Access array elements from previous extractions

## Best Practices

### Selector Design

1. **Use Specific Selectors**: Prefer IDs over classes, classes over generic tags
2. **Include Fallbacks**: Multiple selectors separated by commas
3. **Avoid Brittle Selectors**: Don't rely on exact DOM structure
4. **Test Selectors**: Verify selectors work across different page states

### Workflow Design

1. **Add Wait Conditions**: Always wait for elements before interacting
2. **Handle Timing**: Include appropriate delays for page loads
3. **Error Recovery**: Configure retries and anti-detection measures
4. **Modular Steps**: Break complex workflows into clear steps

### Anti-Detection Configuration

1. **Enable Appropriately**: Only enable needed anti-detection features
2. **Tune Delays**: Adjust rate limiting based on site restrictions
3. **Monitor Effectiveness**: Track success rates and adjust configuration
4. **Site-Specific Tuning**: Customize selectors for specific sites

### Performance Optimization

1. **Optimize Timeouts**: Set appropriate timeouts for different operations
2. **Batch Operations**: Group similar extractions when possible
3. **Resource Management**: Configure session rotation for long-running scrapers
4. **Caching**: Use appropriate caching strategies for static content

## Validation

### Schema Validation

The system validates YAML configurations against the schema. Common validation errors:

- Missing required fields (`name`, `base_url`)
- Invalid action types
- Malformed selector configurations
- Incorrect parameter types

### Runtime Validation

- Selector existence checks
- Element interaction validation
- Data extraction verification
- Anti-detection effectiveness monitoring

## Troubleshooting

### Common Issues

1. **Selector Not Found**: Update CSS selectors, check page structure changes
2. **Timeout Errors**: Increase timeout values, add wait conditions
3. **Anti-Detection Failures**: Adjust anti-detection configuration
4. **Data Extraction Issues**: Verify selector attributes and multiple settings

### Debugging Tips

1. **Test Selectors Individually**: Use browser dev tools to verify selectors
2. **Enable Debug Logging**: Check workflow execution logs
3. **Step-by-Step Testing**: Test workflow steps incrementally
4. **Compare with Legacy**: Validate results against legacy scrapers