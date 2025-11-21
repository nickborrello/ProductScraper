# Scraper Guide

## Configuration

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

### Validation Configuration

```yaml
validation:
  no_results_selectors: list            # Optional: Selectors to detect 'no results' pages
  no_results_text_patterns: list        # Optional: Text patterns to detect 'no results' pages
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
Wait for one or more elements to be present.

```yaml
- action: "wait_for"
  params:
    selector: [".product-details", ".no-results-message"] # Can be a single selector string or a list of selectors
    timeout: 10                  # Optional: Timeout in seconds
```

### Interaction Actions

#### click
Click on an element, with optional filtering. This is useful for clicking the first non-sponsored link in a list of search results.

```yaml
- action: "click"
  params:
    selector: ".search-result a"
    filter_text_exclude: "sponsored" # Optional: regex to exclude elements by text
    index: 0 # Optional: index of the element to click in the filtered list
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

### Control Flow Actions

#### check_no_results
Explicitly check if the current page is a "no results" page. This action uses the selectors and patterns defined in the `validation` section. It sets a `no_results_found` flag in the results.

```yaml
- action: "check_no_results"
  params: {}
```

#### conditional_skip
Conditionally skip the rest of the workflow based on a flag from a previous step.

```yaml
- action: "conditional_skip"
  params:
    if_flag: "no_results_found"  # Skip if the 'no_results_found' flag is true
```

#### verify
Verify a value on the page against an expected value. Can be used to ensure the correct product page is being scraped.

```yaml
- action: "verify"
  params:
    selector: ".product-upc"
    attribute: "text"
    expected_value: "{sku}"
    match_mode: "fuzzy_number"  # "exact", "contains", or "fuzzy_number"
    on_failure: "fail_workflow" # "fail_workflow" or "log_warning"
```

#### scroll
Scroll the page to load lazy-loaded content or bring elements into view.

```yaml
- action: "scroll"
  params:
    direction: "down"  # "up", "down", "to_top", or "to_bottom"
    amount: 500      # Optional: pixels to scroll for "up" or "down"
    selector: "#load_more_button" # Optional: scroll a specific element into view
```

#### conditional_click
Click on an element only if it exists. Useful for optional elements like cookie banners.

```yaml
- action: "conditional_click"
  params:
    selector: "#cookie-consent-button"
    timeout: 5 # Optional: how long to wait for the element before skipping
```

### Data Extraction Actions

#### extract_from_json
Extract data from a JSON object embedded in a `<script>` tag.

```yaml
- action: "extract_from_json"
  params:
    selector: "script[type='application/ld+json']"
    field: "product_name"
    json_path: "name" # dot-notation path to the desired value (e.g., 'details.price')
```

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

#### parse_weight
Parse and normalize weight strings from extracted data.

```yaml
- action: "parse_weight"
  params:
    field: "weight"              # Field containing weight string
    target_unit: "lb"            # Optional: target unit ("lb", "kg", "oz", "g")
```

#### process_images
Process, filter, and upgrade image URLs.

```yaml
- action: "process_images"
  params:
    field: "images"              # Field containing image URLs
    quality_patterns:            # Optional: URL transformation patterns
      - regex: "(\\.jpg)$"
        replacement: "_large.jpg"
    filters:                     # Optional: filtering rules
      - type: "exclude_text"
        text: "thumbnail"
    deduplicate: true            # Optional: remove duplicates (default: true)
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

### Weight Extraction

```yaml
selectors:
  - name: "weight"
    selector: ".product-weight, #weight, .specs-weight"
    attribute: "text"
```

### Images Field Extraction

```yaml
selectors:
  - name: "images"
    selector: ".product-gallery img, #main-image, .additional-images img"
    attribute: "src"
    multiple: true
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
  - name: "weight"
    selector: ".product-weight, #weight, .specs-weight"
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
      fields: ["product_name", "price", "description", "weight", "images", "specifications"]
  - action: "parse_weight"
    params:
      field: "weight"
  - action: "process_images"
    params:
      field: "images"

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  rate_limit_min_delay: 1.5
  rate_limit_max_delay: 4.0
```

### Example 2: Search and Extract Workflow with No-Results Handling

```yaml
name: "search_scraper"
base_url: "https://www.example.com"
timeout: 45
retries: 5

validation:
  no_results_selectors:
    - ".no-results"
    - "div.search-empty"
  no_results_text_patterns:
    - "no results found"
    - "your search returned no matches"

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
  - action: "check_no_results"
  - action: "conditional_skip"
    params:
      if_flag: "no_results_found"
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

## Development

## Architecture Overview

The modular scraper system consists of several key components:

- **YAML Configuration Files**: Declarative scraper definitions
- **WorkflowExecutor**: Core execution engine
- **Actions Framework**: Registry-based system for workflow actions with base action classes, handler registry, and extensible action types
- **AntiDetectionManager**: Anti-detection capabilities
- **YAMLParser**: Configuration parsing and validation
- **Selector Storage**: Reusable selector management

## Creating New Scrapers

### Step 1: Analyze Target Website

Before creating a scraper, thoroughly analyze the target website:

1. **Identify Data Sources**: Determine what data needs to be extracted
2. **Map Page Structure**: Understand HTML structure and CSS selectors
3. **Check Authentication**: Determine if login is required
4. **Assess Anti-Detection**: Evaluate bot detection measures
5. **Test Selectors**: Verify selectors work across different scenarios

### Step 2: Create YAML Configuration

Create a new YAML configuration file in `src/scrapers/configs/`:

```yaml
# src/scrapers/configs/my_new_scraper.yaml
name: "my_new_scraper"
base_url: "https://www.example.com"
timeout: 30
retries: 3

selectors:
  - name: "product_title"
    selector: "#product-title, .product-name"
    attribute: "text"
  - name: "product_price"
    selector: ".price, #price"
    attribute: "text"
  - name: "product_images"
    selector: ".product-gallery img"
    attribute: "src"
    multiple: true

workflows:
  - action: "navigate"
    params:
      url: "https://www.example.com/products/{product_id}"
  - action: "wait_for"
    params:
      selector: "#product-title"
      timeout: 15
  - action: "extract"
    params:
      fields: ["product_title", "product_price", "product_images"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  rate_limit_min_delay: 1.5
  rate_limit_max_delay: 4.0
```

### Step 3: Test Configuration

Test the new scraper configuration:

```python
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

# Parse configuration
parser = YAMLParser()
config = parser.parse("src/scrapers/configs/my_new_scraper.yaml")

# Test execution
executor = WorkflowExecutor(config, headless=False)  # headless=False for debugging
results = executor.execute_workflow()

print("Results:", results)
```

### Step 4: Add Test Data

Add test data to the test fixtures:

```json
// tests/fixtures/scraper_test_data.json
{
  "my_new_scraper": [
    {
      "sku": "TEST001",
      "expected_fields": ["product_title", "product_price"],
      "validation_rules": {
        "product_title": {"type": "string", "min_length": 3},
        "product_price": {"type": "string", "pattern": "\\$\\d+\\.\\d{2}"}
      }
    }
  ]
}
```

## Extending WorkflowExecutor

### Adding New Workflow Actions

To add a new workflow action using the Actions Framework, create a new action class that inherits from BaseAction and register it with the ActionRegistry:

```python
# src/scrapers/actions/handlers/custom_action.py
from typing import Dict, Any
from src.scrapers.actions.base import BaseAction
from src.scrapers.actions.registry import ActionRegistry

@ActionRegistry.register("custom_action")
class CustomAction(BaseAction):
    """Custom workflow action example."""

    def validate_params(self, params: Dict[str, Any]) -> bool:
        """Validate action parameters."""
        required_params = ["custom_param"]
        return all(param in params for param in required_params)

    def execute(self, context: Dict[str, Any], params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the custom action."""
        custom_param = params.get("custom_param")

        # Implement custom logic here
        self.logger.info(f"Executing custom action with param: {custom_param}")

        # Example: Custom browser interaction
        if hasattr(context.get('browser', {}), 'driver'):
            context['browser'].driver.execute_script("console.log('Custom action executed');")

        # Store results
        result = f"Processed: {custom_param}"
        context.setdefault('results', {})["custom_result"] = result

        return {"success": True, "result": result}
```

### Usage Example

```yaml
# Configuration using custom action
workflows:
  - action: "custom_action"
    params:
      custom_param: "example_value"
```

### Best Practices for Custom Actions

1. **Follow Naming Conventions**: Use lowercase action names with underscores
2. **Parameter Validation**: Implement validate_params method to check required parameters
3. **Error Handling**: Implement proper exception handling and return error status
4. **Logging**: Add appropriate logging for debugging
5. **Documentation**: Document custom actions in the configuration guide
6. **Registry Usage**: Always use @ActionRegistry.register decorator for automatic registration

## Adding New Anti-Detection Modules

### Extending AntiDetectionManager

Create a new anti-detection module:

```python
# src/core/custom_anti_detection.py
from src.core.anti_detection_manager import AntiDetectionManager, AntiDetectionConfig

class CustomAntiDetectionConfig(AntiDetectionConfig):
    def __init__(self, enable_custom_module: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.enable_custom_module = enable_custom_module

class CustomDetectionModule:
    """Custom anti-detection module."""

    def __init__(self, config: CustomAntiDetectionConfig):
        self.config = config

    def detect_threat(self, driver) -> bool:
        """Detect custom threats."""
        # Implement detection logic
        return False

    def handle_threat(self, driver) -> bool:
        """Handle detected threats."""
        # Implement handling logic
        return True

class CustomAntiDetectionManager(AntiDetectionManager):

    def __init__(self, browser, config: CustomAntiDetectionConfig):
        super().__init__(browser, config)

        # Add custom module
        if config.enable_custom_module:
            self.custom_module = CustomDetectionModule(config)

    def pre_action_hook(self, action: str, params: Dict[str, Any]) -> bool:
        """Extended pre-action hook."""
        # Call parent implementation
        if not super().pre_action_hook(action, params):
            return False

        # Add custom logic
        if hasattr(self, 'custom_module'):
            if self.custom_module.detect_threat(self.browser.driver):
                self.logger.info("Custom threat detected, handling...")
                return self.custom_module.handle_threat(self.browser.driver)

        return True
```

### Configuration Integration

```yaml
# YAML configuration with custom anti-detection
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_custom_module: true
  custom_module_param: "value"
```

## Extending Selector System

### Creating Reusable Selector Libraries

```python
# src/scrapers/selectors/ecommerce_selectors.py
class EcommerceSelectors:
    """Reusable selectors for e-commerce sites."""

    @staticmethod
    def product_title_selectors():
        return [
            "#productTitle",
            ".product-title",
            "h1.product-name",
            "[data-testid='product-title']"
        ]

    @staticmethod
    def price_selectors():
        return [
            ".a-price .a-offscreen",
            "#priceblock_ourprice",
            ".product-price",
            "[data-cy='price-recipe']"
        ]

    @staticmethod
    def image_selectors():
        return [
            "#altImages li.imageThumbnail img",
            ".product-gallery img",
            "#main-image"
        ]
```

### Dynamic Selector Resolution

```python
# src/scrapers/selector_resolver.py
class SelectorResolver:
    """Dynamic selector resolution based on site analysis."""

    def __init__(self, site_name: str):
        self.site_name = site_name
        self.selector_cache = {}

    def resolve_selector(self, field_name: str, driver) -> str:
        """Dynamically resolve best selector for a field."""
        if field_name in self.selector_cache:
            return self.selector_cache[field_name]

        # Analyze page and determine best selector
        candidates = self._get_candidate_selectors(field_name)

        best_selector = None
        best_score = 0

        for selector in candidates:
            try:
                elements = driver.find_elements(By.CSS_SELECTOR, selector)
                if elements:
                    score = self._score_selector(selector, elements)
                    if score > best_score:
                        best_score = score
                        best_selector = selector
            except:
                continue

        if best_selector:
            self.selector_cache[field_name] = best_selector

        return best_selector

    def _score_selector(self, selector: str, elements) -> float:
        """Score selector based on specificity and element count."""
        # Implement scoring logic
        return len(elements) * self._calculate_specificity(selector)
```

## Testing and Validation

### Unit Testing

Create comprehensive unit tests:

```python
# tests/unit/test_custom_workflow_executor.py
import pytest
from unittest.mock import Mock, patch
from src.scrapers.executor.custom_workflow_executor import CustomWorkflowExecutor

class TestCustomWorkflowExecutor:

    @pytest.fixture
    def mock_config(self):
        config = Mock()
        config.name = "test_scraper"
        config.timeout = 30
        return config

    @pytest.fixture
    def mock_browser(self):
        browser = Mock()
        browser.driver = Mock()
        return browser

    def test_custom_action_execution(self, mock_config, mock_browser):
        """Test custom action execution."""
        executor = CustomWorkflowExecutor(mock_config, headless=True)
        executor.browser = mock_browser
        executor.results = {}

        # Mock browser methods
        mock_browser.driver.execute_script = Mock()

        # Execute custom action
        step = Mock()
        step.action = "custom_action"
        step.params = {"custom_param": "test_value"}

        executor._execute_step(step)

        # Verify custom logic was executed
        mock_browser.driver.execute_script.assert_called_once_with(
            "console.log('Custom action executed');"
        )
        assert executor.results["custom_result"] == "Processed: test_value"

    def test_parse_weight_action(self):
        """Test parse_weight action execution."""
        from src.scrapers.actions.handlers.weight import ParseWeightAction

        action = ParseWeightAction()
        context = {"results": {}}
        params = {"field": "weight", "source_field": "raw_weight"}

        # Mock context with weight data
        context["results"]["raw_weight"] = "10 oz"

        result = action.execute(context, params)

        assert result["success"] is True
        assert context["results"]["weight"] == "0.625 lb"

    def test_process_images_action(self):
        """Test process_images action execution."""
        from src.scrapers.actions.handlers.image import ProcessImagesAction

        action = ProcessImagesAction()
        context = {"results": {}}
        params = {
            "field": "images",
            "source_field": "raw_images",
            "quality_patterns": [{"regex": r"\._AC_.*", "replacement": "._AC_SL1500_"}]
        }

        # Mock context with image URLs
        context["results"]["raw_images"] = [
            "https://example.com/image._AC_US200_.jpg",
            "https://example.com/image2._AC_US400_.jpg"
        ]

        result = action.execute(context, params)

        assert result["success"] is True
        assert len(context["results"]["images"]) == 2
        assert "._AC_SL1500_" in context["results"]["images"][0]
```

### Integration Testing

```python
# tests/integration/test_scraper_integration.py
import pytest
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

class TestScraperIntegration:

    def test_full_scraper_workflow(self):
        """Test complete scraper workflow."""
        parser = YAMLParser()
        config = parser.parse("src/scrapers/configs/test_scraper.yaml")

        executor = WorkflowExecutor(config, headless=True)
        results = executor.execute_workflow()

        assert results["success"] is True
        assert "extracted_data" in results["results"]

    def test_anti_detection_integration(self):
        """Test anti-detection integration."""
        parser = YAMLParser()
        config = parser.parse("src/scrapers/configs/test_scraper.yaml")

        # Ensure anti-detection is enabled
        assert config.anti_detection is not None

        executor = WorkflowExecutor(config, headless=True)

        # Verify anti-detection manager is initialized
        assert executor.anti_detection_manager is not None
```

### Performance Testing

```python
# tests/performance/test_scraper_performance.py
import time
import pytest
from src.scrapers.executor.workflow_executor import WorkflowExecutor

class TestScraperPerformance:

    def test_execution_time(self):
        """Test scraper execution performance."""
        parser = YAMLParser()
        config = parser.parse("src/scrapers/configs/performance_test.yaml")

        start_time = time.time()
        executor = WorkflowExecutor(config, headless=True)
        results = executor.execute_workflow()
        execution_time = time.time() - start_time

        # Assert performance requirements
        assert execution_time < 30.0  # Should complete within 30 seconds
        assert results["success"] is True

    def test_memory_usage(self):
        """Test memory usage during scraping."""
        import psutil
        import os

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Execute scraper
        parser = YAMLParser()
        config = parser.parse("src/scrapers/configs/memory_test.yaml")
        executor = WorkflowExecutor(config, headless=True)
        results = executor.execute_workflow()

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Assert memory usage is reasonable
        assert memory_increase < 500  # Less than 500MB increase
```

## Debugging and Troubleshooting

### Common Issues and Solutions

#### Selector Not Found
```python
# Debug selector issues
def debug_selector(selector: str, driver):
    """Debug CSS selector issues."""
    try:
        elements = driver.find_elements(By.CSS_SELECTOR, selector)
        print(f"Selector '{selector}' found {len(elements)} elements")

        for i, element in enumerate(elements[:3]):  # Show first 3
            print(f"  Element {i}: {element.text[:100]}...")
            print(f"    Attributes: {driver.execute_script('return arguments[0].attributes;', element)}")

    except Exception as e:
        print(f"Error with selector '{selector}': {e}")
```

#### Workflow Execution Failures
```python
# Add detailed logging to workflow execution
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable browser logs
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

caps = DesiredCapabilities.CHROME
caps['goog:loggingPrefs'] = {'browser': 'ALL'}

# Monitor workflow execution
executor = WorkflowExecutor(config, headless=False)
try:
    results = executor.execute_workflow()
except Exception as e:
    print(f"Workflow failed: {e}")
    # Check browser logs
    logs = executor.browser.driver.get_log('browser')
    for log in logs:
        print(f"Browser log: {log}")
```

#### Anti-Detection Issues
```python
# Debug anti-detection
anti_detection = executor.anti_detection_manager

# Check module status
print(f"CAPTCHA detector: {anti_detection.captcha_detector is not None}")
print(f"Rate limiter: {anti_detection.rate_limiter is not None}")
print(f"Human simulator: {anti_detection.human_simulator is not None}")

# Monitor request counts
print(f"Request count: {anti_detection.request_count}")
print(f"Session start time: {anti_detection.session_start_time}")
```

### Development Tools

#### Scraper Development CLI

```python

import click
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

@click.group()
def scraper_dev():
    """Scraper development tools."""
    pass

@scraper_dev.command()
@click.argument('config_file')
@click.option('--headless', is_flag=True, default=False)
def test_config(config_file, headless):
    """Test a scraper configuration."""
    parser = YAMLParser()
    config = parser.parse(config_file)

    executor = WorkflowExecutor(config, headless=headless)
    results = executor.execute_workflow()

    click.echo(f"Success: {results['success']}")
    click.echo(f"Results: {results['results']}")

@scraper_dev.command()
@click.argument('config_file')
@click.argument('selector_name')
def test_selector(config_file, selector_name):
    """Test a specific selector."""
    parser = YAMLParser()
    config = parser.parse(config_file)

    executor = WorkflowExecutor(config, headless=False)

    # Navigate to test page
    executor.browser.get(config.base_url)

    # Find selector in config
    selector_config = next(
        (s for s in config.selectors if s.name == selector_name), None
    )

    if not selector_config:
        click.echo(f"Selector '{selector_name}' not found")
        return

    # Test selector
    try:
        if selector_config.multiple:
            elements = executor.browser.driver.find_elements(
                By.CSS_SELECTOR, selector_config.selector
            )
            click.echo(f"Found {len(elements)} elements")
        else:
            element = executor.browser.driver.find_element(
                By.CSS_SELECTOR, selector_config.selector
            )
            value = executor._extract_value_from_element(
                element, selector_config.attribute
            )
            click.echo(f"Extracted value: {value}")
    except Exception as e:
        click.echo(f"Selector test failed: {e}")

if __name__ == '__main__':
    scraper_dev()
```

#### Selector Discovery Tool

```python
# src/utils/scraping/selector_discovery.py
from selenium.webdriver.common.by import By

class SelectorDiscovery:
    """Tool for discovering CSS selectors on web pages."""

    def __init__(self, driver):
        self.driver = driver

    def discover_selectors(self, target_text: str = None):
        """Discover potential selectors for elements containing target text."""
        selectors = []

        # Common selector patterns
        patterns = [
            f"*[contains(text(), '{target_text}')]" if target_text else "*",
            "*.price", "#price", ".product-price",
            "*.title", "#title", ".product-title",
            "img", "*.image", "#main-image"
        ]

        for pattern in patterns:
            try:
                elements = self.driver.find_elements(By.CSS_SELECTOR, pattern)
                if elements:
                    selectors.append({
                        'pattern': pattern,
                        'count': len(elements),
                        'sample_text': elements[0].text[:50] if elements[0].text else None
                    })
            except:
                continue

        return selectors

    def suggest_selectors(self, field_name: str):
        """Suggest appropriate selectors based on field name."""
        suggestions = {
            'price': ['.price', '#price', '.a-price', '[data-cy*="price"]'],
            'title': ['.title', '#title', 'h1', '[data-testid*="title"]'],
            'image': ['img', '.image', '#main-image', '[data-image]'],
            'description': ['.description', '#description', '[data-testid*="description"]']
        }

        return suggestions.get(field_name.lower(), [])
```

## Best Practices

### Code Organization

1. **Modular Design**: Keep components loosely coupled
2. **Single Responsibility**: Each class/method should have one purpose
3. **Configuration-Driven**: Avoid hardcoding values
4. **Error Resilience**: Implement proper error handling

### Actions Framework Best Practices

1. **Action Naming**: Use descriptive, lowercase names with underscores (e.g., `parse_weight`, `process_images`)
2. **Parameter Validation**: Always implement `validate_params()` method to check required parameters and their types
3. **Error Handling**: Return appropriate error status and messages, never throw unhandled exceptions
4. **Registry Usage**: Always use `@ActionRegistry.register()` decorator for automatic action registration
5. **Modular Design**: Keep actions focused on single responsibilities, compose complex workflows from simple actions
6. **Context Management**: Use the context dictionary for sharing data between actions, avoid global state
7. **Logging**: Implement comprehensive logging for debugging and monitoring action execution
8. **Testing**: Write unit tests for each action covering success and error scenarios

### Performance Optimization

1. **Selector Efficiency**: Use specific selectors to avoid full DOM scans
2. **Caching**: Cache compiled selectors and parsed configurations
3. **Resource Management**: Properly clean up browser instances
4. **Async Operations**: Use async/await for I/O operations where possible

### Security Considerations

1. **Credential Management**: Never hardcode credentials
2. **Data Sanitization**: Validate and sanitize extracted data
3. **Rate Limiting**: Respect site limits to avoid being blocked
4. **Legal Compliance**: Ensure compliance with terms of service

### Testing Strategy

1. **Unit Tests**: Test individual components in isolation
2. **Integration Tests**: Test component interactions
3. **End-to-End Tests**: Test complete workflows
4. **Performance Tests**: Monitor resource usage and timing
5. **Regression Tests**: Ensure changes don't break existing functionality

## Contributing Guidelines

### Pull Request Process

1. **Fork and Branch**: Create a feature branch from main
2. **Code Standards**: Follow PEP 8 and project conventions
3. **Testing**: Add comprehensive tests for new features
4. **Documentation**: Update documentation for changes
5. **Review**: Request code review before merging

### Code Review Checklist

- [ ] Code follows project conventions
- [ ] Unit tests added/updated
- [ ] Integration tests pass
- [ ] Documentation updated
- [ ] Performance impact assessed
- [ ] Security implications reviewed
- [ ] Backwards compatibility maintained

### Release Process

1. **Version Bump**: Update version numbers in relevant files
2. **Changelog**: Document changes in CHANGELOG.md
3. **Testing**: Run full test suite
4. **Documentation**: Update user-facing documentation
5. **Deployment**: Deploy to staging, then production

## Migration

## Overview

The new modular scraper system replaces the old monolithic Python files with:

- **YAML Configuration Files**: Declarative scraper definitions
- **WorkflowExecutor**: Unified execution engine
- **Anti-Detection Manager**: Built-in anti-detection capabilities
- **Modular Architecture**: Reusable components and easier maintenance

## Migration Process

### Step 1: Analyze Legacy Scraper

Identify the key components of your legacy scraper:

```python
# Legacy scraper structure (example from src/scrapers_archive/archive/amazon.py)
def scrape_amazon(skus, log_callback=None, progress_tracker=None, status_callback=None):
    # Browser initialization
    browser_context = init_browser_optimized("amazon_batch", headless=HEADLESS)

    # Main scraping loop
    for sku in skus:
        product_info = scrape_single_product(sku, driver, log_callback=log_callback)
        # Process results...

def scrape_single_product(UPC_or_ASIN, driver, max_retries=0, log_callback=None):
    # Navigation logic
    search_url = f"https://www.amazon.com/s?k={UPC_or_ASIN}"
    driver.get(search_url)

    # Element interaction
    _click_first_search_result(driver, log_callback=log_callback)

    # Data extraction
    _extract_product_data(driver, product_info, log_callback=log_callback)
```

### Step 2: Create YAML Configuration

Convert the legacy logic into a YAML configuration file:

```yaml
# New modular configuration (src/scrapers/configs/amazon.yaml)
name: "amazon"
base_url: "https://www.amazon.com"
timeout: 30
retries: 3

selectors:
  - name: "product_name"
    selector: "#productTitle"
    attribute: "text"
  - name: "brand"
    selector: "#bylineInfo, #brand, .a-brand"
    attribute: "text"
  - name: "images"
    selector: "#altImages li.imageThumbnail img"
    attribute: "src"
    multiple: true

workflows:
  - action: "navigate"
    params:
      url: "https://www.amazon.com/s?k={sku}"
  - action: "wait_for"
    params:
      selector: ".s-result-item"
      timeout: 10
  - action: "click"
    params:
      selector: ".s-result-item a.a-link-normal[href*='/dp/']"
  - action: "wait_for"
    params:
      selector: "#productTitle"
      timeout: 10
  - action: "extract"
    params:
      fields: ["product_name", "brand", "images"]

anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_blocking_handling: true
  rate_limit_min_delay: 1.0
  rate_limit_max_delay: 5.0
```

### Step 3: Update Integration Code

Replace legacy scraper calls with the new WorkflowExecutor:

```python
# Before: Legacy scraper usage
from src.scrapers_archive.archive.amazon import scrape_amazon

results = scrape_amazon(skus, log_callback=log_callback)

# After: New modular scraper usage
from src.scrapers.parser.yaml_parser import YAMLParser
from src.scrapers.executor.workflow_executor import WorkflowExecutor

# Load configuration
parser = YAMLParser()
config = parser.parse("src/scrapers/configs/amazon.yaml")

# Execute workflow
executor = WorkflowExecutor(config, headless=True)
results = executor.execute_workflow()
```

### Step 4: Handle Anti-Detection Features

The new system includes built-in anti-detection capabilities. Configure them in the YAML:

```yaml
anti_detection:
  enable_captcha_detection: true
  enable_rate_limiting: true
  enable_human_simulation: true
  enable_session_rotation: false
  enable_blocking_handling: true
  captcha