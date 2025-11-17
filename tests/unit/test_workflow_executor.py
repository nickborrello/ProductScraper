import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add project root to sys.path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
sys.path.insert(0, PROJECT_ROOT)

from src.scrapers.executor.workflow_executor import (WorkflowExecutionError,
                                                     WorkflowExecutor)
from src.scrapers.models.config import (ScraperConfig, SelectorConfig,
                                        WorkflowStep)


@pytest.fixture
def sample_config():
    """Create a sample ScraperConfig for testing."""
    return ScraperConfig(
        name="Test Scraper",
        base_url="https://example.com",
        timeout=30,
        retries=3,
        selectors=[
            SelectorConfig(
                name="product_name",
                selector=".product-title",
                attribute="text",
                multiple=False,
            ),
            SelectorConfig(
                name="price", selector=".price", attribute="text", multiple=False
            ),
            SelectorConfig(
                name="image_urls",
                selector=".product-image img",
                attribute="src",
                multiple=True,
            ),
        ],
        workflows=[
            WorkflowStep(
                action="navigate", params={"url": "https://example.com/products"}
            ),
            WorkflowStep(
                action="wait_for", params={"selector": ".product-list", "timeout": 10}
            ),
            WorkflowStep(
                action="extract",
                params={"fields": ["product_name", "price", "image_urls"]},
            ),
        ],
        login=None,
        anti_detection=None,
    )


@pytest.fixture
def mock_browser():
    """Create a mock browser instance."""
    browser = Mock()
    browser.driver = Mock()
    browser.quit = Mock()
    return browser


@pytest.fixture
def mock_create_browser(mock_browser):
    """Mock the create_browser function."""
    with patch("src.scrapers.executor.workflow_executor.create_browser") as mock:
        mock.return_value = mock_browser
        yield mock


class TestWorkflowExecutor:
    """Test cases for WorkflowExecutor class."""

    def test_init_success(self, sample_config, mock_create_browser):
        """Test successful initialization of WorkflowExecutor."""
        executor = WorkflowExecutor(sample_config, headless=True)

        assert executor.config == sample_config
        # Timeout should be 60s in CI, 30s locally
        expected_timeout = 60 if executor.is_ci else 30
        assert executor.timeout == expected_timeout
        assert executor.results == {}
        assert len(executor.selectors) == 3
        mock_create_browser.assert_called_once()
        call_args = mock_create_browser.call_args
        assert call_args[1]["site_name"] == "Test Scraper"
        assert call_args[1]["headless"] is True
        assert "profile_suffix" in call_args[1]

    def test_init_custom_timeout(self, sample_config, mock_create_browser):
        """Test initialization with custom timeout."""
        executor = WorkflowExecutor(sample_config, headless=True, timeout=60)

        assert executor.timeout == 60

    def test_init_browser_failure(self, sample_config):
        """Test initialization failure when browser creation fails."""
        with patch(
            "src.scrapers.executor.workflow_executor.create_browser",
            side_effect=Exception("Browser failed"),
        ):
            with pytest.raises(
                WorkflowExecutionError, match="Failed to initialize browser"
            ):
                WorkflowExecutor(sample_config)

    def test_execute_workflow_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful workflow execution."""
        # Setup mock elements
        mock_element = Mock()
        mock_element.text = "Test Product"
        mock_browser.driver.find_element.return_value = mock_element

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "image1.jpg"
        mock_elements[1].get_attribute.return_value = "image2.jpg"
        mock_browser.driver.find_elements.return_value = mock_elements

        executor = WorkflowExecutor(sample_config, headless=True)

        result = executor.execute_workflow()

        assert result["success"] is True
        assert result["config_name"] == "Test Scraper"
        assert result["steps_executed"] == 3
        assert "results" in result

        # Verify browser was quit
        mock_browser.quit.assert_called_once()

    def test_execute_workflow_step_failure(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test workflow execution failure on a step."""
        # Make navigate action fail
        mock_browser.get.side_effect = Exception("Navigation failed")

        executor = WorkflowExecutor(sample_config, headless=True)

        with pytest.raises(
            WorkflowExecutionError, match="Failed to execute step 'navigate'"
        ):
            executor.execute_workflow()

        # Browser should still be quit
        mock_browser.quit.assert_called_once()

    def test_action_navigate(self, sample_config, mock_create_browser, mock_browser):
        """Test navigate action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        params = {"url": "https://test.com", "wait_after": 2}
        executor._action_navigate(params)

        mock_browser.get.assert_called_once_with("https://test.com")

    def test_action_navigate_no_url(self, sample_config, mock_create_browser):
        """Test navigate action without URL parameter."""
        executor = WorkflowExecutor(sample_config, headless=True)

        with pytest.raises(
            WorkflowExecutionError, match="Navigate action requires 'url' parameter"
        ):
            executor._action_navigate({})

    def test_action_wait_for_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful wait_for action."""
        from selenium.webdriver.support.ui import WebDriverWait

        executor = WorkflowExecutor(sample_config, headless=True)

        params = {"selector": ".test", "timeout": 5}
        executor._action_wait_for(params)

        # Verify WebDriverWait was called correctly
        # This is tricky to test directly, but we can verify no exception was raised

    def test_action_wait_for_timeout(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test wait_for action that times out."""
        from selenium.common.exceptions import TimeoutException

        executor = WorkflowExecutor(sample_config, headless=True)

        # Mock WebDriverWait to raise TimeoutException
        with patch(
            "src.scrapers.executor.workflow_executor.WebDriverWait"
        ) as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            # Error message should reflect actual timeout (60s in CI, 30s locally)
            expected_timeout = 60 if executor.is_ci else 30
            with pytest.raises(
                WorkflowExecutionError, match=f"Element not found within {expected_timeout}s"
            ):
                executor._action_wait_for({"selector": ".missing"})

    def test_action_wait_for_no_selector(self, sample_config, mock_create_browser):
        """Test wait_for action without selector parameter."""
        executor = WorkflowExecutor(sample_config, headless=True)

        with pytest.raises(
            WorkflowExecutionError,
            match="Wait_for action requires 'selector' parameter",
        ):
            executor._action_wait_for({})

    def test_action_extract_single_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful extract_single action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Product Name"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"field": "product_name", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["product_name"] == "Product Name"
        mock_browser.driver.find_element.assert_called_once_with(
            "css selector", ".product-title"
        )

    def test_action_extract_single_element_not_found(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_single when element is not found."""
        from selenium.common.exceptions import NoSuchElementException

        executor = WorkflowExecutor(sample_config, headless=True)

        mock_browser.driver.find_element.side_effect = NoSuchElementException()

        params = {"field": "product_name", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["product_name"] is None

    def test_action_extract_multiple_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful extract_multiple action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "url1.jpg"
        mock_elements[1].get_attribute.return_value = "url2.jpg"
        mock_browser.driver.find_elements.return_value = mock_elements

        params = {"field": "image_urls", "selector": "image_urls"}
        executor._action_extract_multiple(params)

        assert executor.results["image_urls"] == ["url1.jpg", "url2.jpg"]
        mock_browser.driver.find_elements.assert_called_once_with(
            "css selector", ".product-image img"
        )

    def test_action_input_text_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful input_text action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": "#username", "text": "testuser", "clear_first": True}
        executor._action_input_text(params)

        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("testuser")

    def test_action_input_text_no_clear(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test input_text action without clearing first."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": "#username", "text": "testuser", "clear_first": False}
        executor._action_input_text(params)

        mock_element.clear.assert_not_called()
        mock_element.send_keys.assert_called_once_with("testuser")

    def test_action_click_success(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test successful click action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": ".button", "wait_after": 1}
        executor._action_click(params)

        mock_element.click.assert_called_once()

    def test_extract_value_from_element_text(self, sample_config, mock_create_browser):
        """Test extracting text from element."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Sample Text"

        result = executor._extract_value_from_element(mock_element, "text")
        assert result == "Sample Text"

    def test_extract_value_from_element_attribute(
        self, sample_config, mock_create_browser
    ):
        """Test extracting attribute from element."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.get_attribute.return_value = "https://example.com/image.jpg"

        result = executor._extract_value_from_element(mock_element, "src")
        assert result == "https://example.com/image.jpg"
        mock_element.get_attribute.assert_called_once_with("src")

    def test_extract_value_from_element_none_attribute(
        self, sample_config, mock_create_browser
    ):
        """Test extracting text when attribute is None."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Default Text"

        result = executor._extract_value_from_element(mock_element, None)
        assert result == "Default Text"

    def test_get_results(self, sample_config, mock_create_browser):
        """Test getting execution results."""
        executor = WorkflowExecutor(sample_config, headless=True)
        executor.results = {"test": "value"}

        results = executor.get_results()
        assert results == {"test": "value"}
        assert results is not executor.results  # Should return a copy
