# Scraper Developer Guide

This guide provides comprehensive instructions for developers working with the modular scraper system, including creating new scrapers, extending functionality, and testing procedures.

## Architecture Overview

The modular scraper system consists of several key components:

- **YAML Configuration Files**: Declarative scraper definitions
- **WorkflowExecutor**: Core execution engine
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

To add a new workflow action, extend the WorkflowExecutor class:

```python
# src/scrapers/executor/custom_workflow_executor.py
from src.scrapers.executor.workflow_executor import WorkflowExecutor
from src.scrapers.models.config import WorkflowStep

class CustomWorkflowExecutor(WorkflowExecutor):

    def _execute_step(self, step: WorkflowStep):
        """Override to add custom actions."""
        action = step.action.lower()

        # Check for custom actions first
        if action == "custom_action":
            self._action_custom_action(step.params)
            return

        # Call parent implementation for built-in actions
        super()._execute_step(step)

    def _action_custom_action(self, params: Dict[str, Any]):
        """Implement custom workflow action."""
        custom_param = params.get("custom_param")

        # Implement custom logic here
        self.logger.info(f"Executing custom action with param: {custom_param}")

        # Example: Custom browser interaction
        self.browser.driver.execute_script("console.log('Custom action executed');")

        # Store results
        self.results["custom_result"] = f"Processed: {custom_param}"
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
2. **Parameter Validation**: Validate required parameters
3. **Error Handling**: Implement proper exception handling
4. **Logging**: Add appropriate logging for debugging
5. **Documentation**: Document custom actions in the configuration guide

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
# src/utils/scraping/dev_cli.py
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