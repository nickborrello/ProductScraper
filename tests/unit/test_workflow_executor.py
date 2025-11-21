from unittest.mock import Mock, patch

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By

from src.core.failure_classifier import FailureType
from src.scrapers.executor.workflow_executor import WorkflowExecutionError, WorkflowExecutor
from src.scrapers.models.config import LoginConfig, ScraperConfig, SelectorConfig, WorkflowStep


@pytest.fixture
def sample_config():
    """Create a sample ScraperConfig for testing."""
    timeout = 30
    retries = 3
    wait_timeout = 10
    return ScraperConfig(
        name="Test Scraper",
        base_url="https://example.com",
        timeout=timeout,
        retries=retries,
        selectors=[
            SelectorConfig(
                name="product_name",
                selector=".product-title",
                attribute="text",
                multiple=False,
            ),
            SelectorConfig(name="price", selector=".price", attribute="text", multiple=False),
            SelectorConfig(
                name="image_urls",
                selector=".product-image img",
                attribute="src",
                multiple=True,
            ),
        ],
        workflows=[
            WorkflowStep(action="navigate", params={"url": "https://example.com/products"}),
            WorkflowStep(action="wait_for", params={"selector": ".product-list", "timeout": wait_timeout}),
            WorkflowStep(
                action="extract",
                params={"fields": ["product_name", "price", "image_urls"]},
            ),
        ],
        login=None,
        anti_detection=None,
        http_status=None,
        test_skus=["035585499741"],
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


@pytest.fixture
def test_skus():
    """Test SKUs for testing."""
    return ["035585499741"]


class TestWorkflowExecutor:
    """Test cases for WorkflowExecutor class."""

    def test_init_success(self, sample_config, mock_create_browser):
        """Test successful initialization of WorkflowExecutor."""
        executor = WorkflowExecutor(sample_config, headless=True)
        expected_selector_count = 3

        assert executor.config == sample_config
        # Timeout should be 60s in CI, 30s locally
        expected_timeout = 60 if executor.is_ci else 30
        assert executor.timeout == expected_timeout
        assert executor.results == {}
        assert len(executor.selectors) == expected_selector_count
        mock_create_browser.assert_called_once()
        call_args = mock_create_browser.call_args
        assert call_args[1]["site_name"] == "Test Scraper"
        assert call_args[1]["headless"] is True
        assert "profile_suffix" in call_args[1]

    def test_init_custom_timeout(self, sample_config, mock_create_browser):
        """Test initialization with custom timeout."""
        custom_timeout = 60
        executor = WorkflowExecutor(sample_config, headless=True, timeout=custom_timeout)

        assert executor.timeout == custom_timeout

    def test_init_browser_failure(self, sample_config):
        """Test initialization failure when browser creation fails."""
        with patch(
            "src.scrapers.executor.workflow_executor.create_browser",
            side_effect=Exception("Browser failed"),
        ):
            with pytest.raises(WorkflowExecutionError, match="Failed to initialize browser"):
                WorkflowExecutor(sample_config)

    def test_execute_workflow_success(
        self, sample_config, mock_create_browser, mock_browser, test_skus
    ):
        """Test successful workflow execution."""
        # Setup mock elements
        mock_element = Mock()
        mock_element.text = "Test Product"
        mock_browser.driver.find_element.return_value = mock_element
        expected_steps_executed = 3

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "image1.jpg"
        mock_elements[1].get_attribute.return_value = "image2.jpg"
        mock_browser.driver.find_elements.return_value = mock_elements

        executor = WorkflowExecutor(sample_config, headless=True)

        result = executor.execute_workflow(test_skus=test_skus)

        assert result["success"] is True
        assert result["config_name"] == "Test Scraper"
        assert result["steps_executed"] == expected_steps_executed
        assert "results" in result

        # Verify browser was quit
        mock_browser.quit.assert_called_once()

    def test_execute_workflow_step_failure(self, sample_config, mock_create_browser, mock_browser):
        """Test workflow execution failure on a step."""
        # Make navigate action fail
        mock_browser.get.side_effect = Exception("Navigation failed")

        executor = WorkflowExecutor(sample_config, headless=True)

        with pytest.raises(WorkflowExecutionError, match="Failed to execute step 'navigate'"):
            executor.execute_workflow()

        # Browser should still be quit
        mock_browser.quit.assert_called_once()

    def test_action_navigate(self, sample_config, mock_create_browser, mock_browser):
        """Test navigate action."""
        executor = WorkflowExecutor(sample_config, headless=True)
        wait_after = 2
        params = {"url": "https://test.com", "wait_after": wait_after}
        executor._action_navigate(params)

        mock_browser.get.assert_called_once_with("https://test.com")

    def test_action_navigate_no_url(self, sample_config, mock_create_browser):
        """Test navigate action without URL parameter."""
        executor = WorkflowExecutor(sample_config, headless=True)

        with pytest.raises(
            WorkflowExecutionError, match="Navigate action requires 'url' parameter"
        ):
            executor._action_navigate({})

    def test_action_wait_for_success(self, sample_config, mock_create_browser, mock_browser):
        """Test successful wait_for action."""
        timeout = 5
        executor = WorkflowExecutor(sample_config, headless=True)

        params = {"selector": ".test", "timeout": timeout}
        executor._action_wait_for(params)

        # Verify WebDriverWait was called correctly
        # This is tricky to test directly, but we can verify no exception was raised

    def test_action_wait_for_timeout(self, sample_config, mock_create_browser, mock_browser):
        """Test wait_for action that times out."""
        executor = WorkflowExecutor(sample_config, headless=True)
        expected_timeout = 60 if executor.is_ci else 30

        # Mock WebDriverWait to raise TimeoutException
        with patch("src.scrapers.executor.workflow_executor.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.side_effect = TimeoutException()

            # Error message should reflect actual timeout (60s in CI, 30s locally)
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

    def test_action_extract_single_success(self, sample_config, mock_create_browser, mock_browser):
        """Test successful extract_single action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Product Name"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"field": "product_name", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["product_name"] == "Product Name"
        mock_browser.driver.find_element.assert_called_once_with("css selector", ".product-title")

    def test_action_extract_single_element_not_found(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_single when element is not found."""
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

    def test_action_input_text_success(self, sample_config, mock_create_browser, mock_browser):
        """Test successful input_text action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": "#username", "text": "testuser", "clear_first": True}
        executor._action_input_text(params)

        mock_element.clear.assert_called_once()
        mock_element.send_keys.assert_called_once_with("testuser")

    def test_action_input_text_no_clear(self, sample_config, mock_create_browser, mock_browser):
        """Test input_text action without clearing first."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": "#username", "text": "testuser", "clear_first": False}
        executor._action_input_text(params)

        mock_element.clear.assert_not_called()
        mock_element.send_keys.assert_called_once_with("testuser")

    def test_action_click_success(self, sample_config, mock_create_browser, mock_browser):
        """Test successful click action."""
        executor = WorkflowExecutor(sample_config, headless=True)
        wait_after = 1
        mock_element = Mock()
        mock_element.is_displayed.return_value = True
        mock_element.is_enabled.return_value = True
        mock_browser.driver.find_element.return_value = mock_element

        params = {"selector": ".button", "wait_after": wait_after}

        with (
            patch("src.scrapers.executor.workflow_executor.WebDriverWait") as mock_wait,
            patch.object(executor.browser.driver, "execute_script") as mock_script,
        ):
            mock_wait.return_value.until.return_value = mock_element
            mock_script.return_value = None

            executor._action_click(params)

        mock_element.click.assert_called_once()

    def test_extract_value_from_element_text(self, sample_config, mock_create_browser):
        """Test extracting text from element."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Sample Text"

        result = executor._extract_value_from_element(mock_element, "text")
        assert result == "Sample Text"

    def test_extract_value_from_element_attribute(self, sample_config, mock_create_browser):
        """Test extracting attribute from element."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.get_attribute.return_value = "https://example.com/image.jpg"

        result = executor._extract_value_from_element(mock_element, "src")
        assert result == "https://example.com/image.jpg"
        mock_element.get_attribute.assert_called_once_with("src")

    def test_extract_value_from_element_none_attribute(self, sample_config, mock_create_browser):
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

    def test_execute_steps_success(self, sample_config, mock_create_browser, mock_browser):
        """Test executing specific workflow steps."""
        mock_element = Mock()
        mock_element.text = "Test Product"
        mock_browser.driver.find_element.return_value = mock_element
        steps_executed = 2
        executor = WorkflowExecutor(sample_config, headless=True)

        steps = [
            WorkflowStep(action="navigate", params={"url": "https://example.com"}),
            WorkflowStep(
                action="extract_single",
                params={"field": "product_name", "selector": "product_name"},
            ),
        ]

        result = executor.execute_steps(steps)

        assert result["success"] is True
        assert result["steps_executed"] == steps_executed
        assert "product_name" in executor.results

    def test_execute_steps_failure(self, sample_config, mock_create_browser, mock_browser):
        """Test executing steps with failure."""
        mock_browser.get.side_effect = Exception("Navigation failed")

        executor = WorkflowExecutor(sample_config, headless=True)

        steps = [WorkflowStep(action="navigate", params={"url": "https://example.com"})]

        with pytest.raises(WorkflowExecutionError, match="Failed to execute step 'navigate'"):
            executor.execute_steps(steps)

    def test_action_wait_success(self, sample_config, mock_create_browser):
        """Test wait action."""
        executor = WorkflowExecutor(sample_config, headless=True)
        wait_seconds = 2
        with patch("time.sleep") as mock_sleep:
            executor._action_wait({"seconds": wait_seconds})
            mock_sleep.assert_called_once_with(wait_seconds)

    def test_action_wait_default(self, sample_config, mock_create_browser):
        """Test wait action with default timeout."""
        executor = WorkflowExecutor(sample_config, headless=True)
        default_wait = 1
        with patch("time.sleep") as mock_sleep:
            executor._action_wait({})
            mock_sleep.assert_called_once_with(default_wait)

    def test_action_extract_brand_processing(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_single with brand field processing."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Visit Premium Foods Store"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"field": "Brand", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["Brand"] == "Premium Foods"

    def test_action_extract_weight_processing(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_single with weight field processing."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "25 pounds"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"field": "Weight", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["Weight"] == "25.00 lbs"

    def test_action_extract_weight_ounces_conversion(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_single with weight ounces to pounds conversion."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "32 ounces"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"field": "Weight", "selector": "product_name"}
        executor._action_extract_single(params)

        assert executor.results["Weight"] == "2.00 lbs"

    def test_action_extract_multiple_brand_processing(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_multiple with brand field processing."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "Visit Store A Store"
        mock_elements[1].get_attribute.return_value = "Visit Store B Store"
        mock_browser.driver.find_elements.return_value = mock_elements

        params = {"field": "Brand", "selector": "image_urls"}
        executor._action_extract_multiple(params)

        assert executor.results["Brand"] == ["Store A", "Store B"]

    def test_action_extract_multiple_weight_processing(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test extract_multiple with weight field processing."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "10 pounds"
        mock_elements[1].get_attribute.return_value = "20 ounces"
        mock_browser.driver.find_elements.return_value = mock_elements

        params = {"field": "Weight", "selector": "image_urls"}
        executor._action_extract_multiple(params)

        assert executor.results["Weight"] == ["10.00 lbs", "1.25 lbs"]

    def test_action_extract_legacy(self, sample_config, mock_create_browser, mock_browser):
        """Test legacy extract action."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "Test Product"
        mock_browser.driver.find_element.return_value = mock_element

        params = {"fields": ["product_name"]}
        executor._action_extract(params)

        assert executor.results["product_name"] == "Test Product"

    def test_action_extract_multiple_legacy(self, sample_config, mock_create_browser, mock_browser):
        """Test legacy extract action with multiple elements."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_elements = [Mock(), Mock()]
        mock_elements[0].get_attribute.return_value = "url1.jpg"
        mock_elements[1].get_attribute.return_value = "url2.jpg"
        mock_browser.driver.find_elements.return_value = mock_elements

        # Update selector config to be multiple
        executor.selectors["image_urls"].multiple = True
        params = {"fields": ["image_urls"]}
        executor._action_extract(params)

        assert executor.results["image_urls"] == ["url1.jpg", "url2.jpg"]

    def test_action_login_success(self, sample_config, mock_create_browser, mock_browser):
        """Test successful login action."""
        timeout = 30
        retries = 3
        login_config = ScraperConfig(
            name="phillips",
            base_url="https://example.com",
            timeout=timeout,
            retries=retries,
            login=LoginConfig(
                url="https://example.com/login",
                username_field="#username",
                password_field="#password",
                submit_button="#submit",
                success_indicator=".dashboard",
                failure_indicators=None,
            ),
            anti_detection=None,
            http_status=None,
            test_skus=None,
        )

        with patch("src.scrapers.executor.workflow_executor.WebDriverWait") as mock_wait:
            mock_wait.return_value.until.return_value = None  # Success indicator found

            executor = WorkflowExecutor(login_config, headless=True)

            # Mock settings manager get method for credentials
            with patch.object(
                executor.settings,
                "get",
                side_effect=lambda key, default="": {
                    "phillips_username": "testuser",
                    "phillips_password": "testpass",
                }.get(key, default),
            ):
                params = {"scraper_name": "phillips"}
                executor._action_login(params)

    def test_action_login_missing_credentials(self, sample_config, mock_create_browser):
        """Test login action with missing credentials."""
        executor = WorkflowExecutor(sample_config, headless=True)

        params = {
            "username": "",
            "password": "",
            "url": "https://example.com/login",
            "username_field": "#user",
            "password_field": "#pass",
            "submit_button": "#submit",
        }

        with pytest.raises(
            WorkflowExecutionError, match="Login action requires username, password"
        ):
            executor._action_login(params)

    def test_action_detect_captcha_no_manager(self, sample_config, mock_create_browser):
        """Test detect_captcha action without anti-detection manager."""
        executor = WorkflowExecutor(sample_config, headless=True)

        executor._action_detect_captcha({})

        assert executor.results.get("captcha_detected") is None

    def test_action_handle_blocking_no_manager(self, sample_config, mock_create_browser):
        """Test handle_blocking action without anti-detection manager."""
        executor = WorkflowExecutor(sample_config, headless=True)

        executor._action_handle_blocking({})

        assert executor.results.get("blocking_handled") is None

    def test_action_rate_limit_no_manager(self, sample_config, mock_create_browser):
        """Test rate_limit action without anti-detection manager."""
        executor = WorkflowExecutor(sample_config, headless=True)

        executor._action_rate_limit({})

        assert executor.results.get("session_rotated") is None

    def test_action_simulate_human_no_manager(self, sample_config, mock_create_browser):
        """Test simulate_human action without anti-detection manager."""
        executor = WorkflowExecutor(sample_config, headless=True)

        executor._action_simulate_human({})

        assert executor.results.get("session_rotated") is None

    def test_action_rotate_session_no_manager(self, sample_config, mock_create_browser):
        """Test rotate_session action without anti-detection manager."""
        executor = WorkflowExecutor(sample_config, headless=True)

        executor._action_rotate_session({})

        assert executor.results.get("session_rotated") is None

    def test_unknown_action(self, sample_config, mock_create_browser):
        """Test unknown action raises error."""
        executor = WorkflowExecutor(sample_config, headless=True)

        step = WorkflowStep(action="unknown_action", params={})

        with pytest.raises(WorkflowExecutionError, match="Unknown action: unknown_action"):
            executor._execute_step(step)

    def test_anti_detection_pre_action_hook_failure(self, sample_config, mock_create_browser):
        """Test pre-action anti-detection hook failure."""
        mock_anti_detection = Mock()
        mock_anti_detection.pre_action_hook.return_value = False

        executor = WorkflowExecutor(sample_config, headless=True)
        executor.anti_detection_manager = mock_anti_detection

        step = WorkflowStep(action="navigate", params={"url": "https://example.com"})

        with pytest.raises(WorkflowExecutionError, match="Pre-action anti-detection check failed"):
            executor._execute_step(step)

    def test_anti_detection_error_handling_retry(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test anti-detection error handling with retry."""
        mock_anti_detection = Mock()
        mock_anti_detection.handle_error.return_value = True  # Retry
        mock_anti_detection.pre_action_hook.return_value = True
        mock_anti_detection.post_action_hook.return_value = None
        call_count = 2
        executor = WorkflowExecutor(sample_config, headless=True)
        executor.anti_detection_manager = mock_anti_detection

        # Make navigate fail initially
        mock_browser.get.side_effect = [Exception("Network error"), None]

        step = WorkflowStep(action="navigate", params={"url": "https://example.com"})

        executor._execute_step(step)

        # Should have called handle_error and retried
        mock_anti_detection.handle_error.assert_called_once()
        assert mock_browser.get.call_count == call_count

    def test_get_locator_type_xpath(self, sample_config, mock_create_browser):
        """Test locator type detection for XPath."""
        executor = WorkflowExecutor(sample_config, headless=True)

        assert executor._get_locator_type("//div[@class='test']") == By.XPATH
        assert executor._get_locator_type(".//div") == By.XPATH

    def test_get_locator_type_css(self, sample_config, mock_create_browser):
        """Test locator type detection for CSS."""
        executor = WorkflowExecutor(sample_config, headless=True)

        assert executor._get_locator_type(".test") == By.CSS_SELECTOR
        assert executor._get_locator_type("#test") == By.CSS_SELECTOR
        assert executor._get_locator_type("div.test") == By.CSS_SELECTOR

    def test_extract_value_from_element_href(self, sample_config, mock_create_browser):
        """Test extracting href attribute."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.get_attribute.return_value = "https://example.com"

        result = executor._extract_value_from_element(mock_element, "href")
        assert result == "https://example.com"
        mock_element.get_attribute.assert_called_once_with("href")

    def test_extract_value_from_element_src(self, sample_config, mock_create_browser):
        """Test extracting src attribute."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.get_attribute.return_value = "image.jpg"

        result = executor._extract_value_from_element(mock_element, "src")
        assert result == "image.jpg"

    def test_extract_value_from_element_custom_attribute(self, sample_config, mock_create_browser):
        """Test extracting custom attribute."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.get_attribute.return_value = "custom-value"

        result = executor._extract_value_from_element(mock_element, "data-custom")
        assert result == "custom-value"

    def test_extract_value_from_element_exception(self, sample_config, mock_create_browser):
        """Test extracting value when element throws exception."""
        executor = WorkflowExecutor(sample_config, headless=True)

        mock_element = Mock()
        mock_element.text = "test"
        mock_element.get_attribute.side_effect = Exception("Attribute error")

        result = executor._extract_value_from_element(mock_element, "href")
        assert result is None

    def test_no_results_failure_no_retry(self, sample_config, mock_create_browser, mock_browser):
        """Test that NO_RESULTS failures are properly classified and handled without retries."""
        # Mock the failure classifier to return NO_RESULTS
        mock_failure_context = Mock()
        mock_failure_context.failure_type = FailureType.NO_RESULTS
        mock_failure_context.confidence = 0.8
        mock_failure_context.details = {"no_results_detected": True}
        mock_failure_context.recovery_strategy = "retry_with_different_query"
        max_retries = 3
        delay = 1.0
        call_count = 1
        executor = WorkflowExecutor(sample_config, headless=True)

        # Mock the failure classifier
        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=mock_failure_context
        ):
            # Mock adaptive retry strategy to return config that would normally allow retries
            mock_config = Mock()
            mock_config.max_retries = max_retries
            with patch.object(
                executor.adaptive_retry_strategy, "get_adaptive_config", return_value=mock_config
            ):
                with patch.object(
                    executor.adaptive_retry_strategy, "calculate_delay", return_value=delay
                ):
                    # Make extract_single fail
                    mock_browser.driver.find_element.side_effect = Exception("No results found")

                    step = WorkflowStep(
                        action="extract_single",
                        params={"field": "product_name", "selector": "product_name"},
                    )

                    # Should not retry and should raise exception
                    with pytest.raises(WorkflowExecutionError):
                        executor._execute_step(step)

                    # Verify browser.get was not called again (no retry)
                    assert mock_browser.driver.find_element.call_count == call_count

    def test_no_results_failure_context_storage(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test that failure context is correctly stored in workflow results for NO_RESULTS."""
        # Mock the failure classifier to return NO_RESULTS
        mock_failure_context = Mock()
        mock_failure_context.failure_type = FailureType.NO_RESULTS
        confidence = 0.9
        mock_failure_context.confidence = confidence
        mock_failure_context.details = {"selector_match": True, "text_match": True}
        mock_failure_context.recovery_strategy = "retry_with_different_query"
        retries = 0
        executor = WorkflowExecutor(sample_config, headless=True)

        # Mock the failure classifier
        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=mock_failure_context
        ):
            # Mock adaptive retry strategy to prevent retries
            mock_config = Mock()
            mock_config.max_retries = retries
            with patch.object(
                executor.adaptive_retry_strategy, "get_adaptive_config", return_value=mock_config
            ):
                # Make extract_single fail
                mock_browser.driver.find_element.side_effect = Exception("No results found")

                step = WorkflowStep(
                    action="extract_single",
                    params={"field": "product_name", "selector": "product_name"},
                )

                with pytest.raises(WorkflowExecutionError):
                    executor._execute_step(step)

                # Verify failure context is stored in results
                assert "failure_context" in executor.results
                failure_context = executor.results["failure_context"]
                assert failure_context["type"] == "no_results"
                assert failure_context["confidence"] == confidence
                assert failure_context["details"]["selector_match"] is True
                assert failure_context["recovery_strategy"] == "retry_with_different_query"
                assert failure_context["retries_attempted"] == retries

    def test_no_results_analytics_recording(self, sample_config, mock_create_browser, mock_browser):
        """Test that NO_RESULTS failures trigger appropriate analytics recording."""
        # Mock the failure classifier to return NO_RESULTS
        mock_failure_context = Mock()
        mock_failure_context.failure_type = FailureType.NO_RESULTS
        mock_failure_context.confidence = 0.7
        mock_failure_context.details = {"no_results_detected": True}
        retries = 0
        executor = WorkflowExecutor(sample_config, headless=True)

        # Mock the failure classifier and analytics
        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=mock_failure_context
        ):
            with patch.object(executor.failure_analytics, "record_failure") as mock_record_failure:
                # Mock adaptive retry strategy to prevent retries
                mock_config = Mock()
                mock_config.max_retries = retries
                with patch.object(
                    executor.adaptive_retry_strategy,
                    "get_adaptive_config",
                    return_value=mock_config,
                ):
                    # Make extract_single fail
                    mock_browser.driver.find_element.side_effect = Exception("No results found")

                    step = WorkflowStep(
                        action="extract_single",
                        params={"field": "product_name", "selector": "product_name"},
                    )

                    with pytest.raises(WorkflowExecutionError):
                        executor._execute_step(step)

                    # Verify analytics recording was called
                    mock_record_failure.assert_called_once()
                    call_args = mock_record_failure.call_args
                    assert call_args[1]["site_name"] == "Test Scraper"
                    assert call_args[1]["failure_type"] == FailureType.NO_RESULTS
                    assert call_args[1]["action"] == "extract_single"
                    assert call_args[1]["retry_count"] == retries
                    assert "exception" in call_args[1]["context"]
                    assert "failure_details" in call_args[1]["context"]
                    assert call_args[1]["context"]["failure_details"]["no_results_detected"] is True

    def test_no_results_vs_other_failures_retry_logic(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test differentiation between NO_RESULTS and other failure types in retry logic."""
        executor = WorkflowExecutor(sample_config, headless=True)
        max_retries = 3
        confidence = 0.8
        delay = 0.1
        call_count = 2
        # Test 1: NO_RESULTS should NOT be retried
        no_results_context = Mock()
        no_results_context.failure_type = FailureType.NO_RESULTS
        no_results_context.confidence = confidence

        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=no_results_context
        ):
            with patch.object(
                executor.adaptive_retry_strategy, "get_adaptive_config"
            ) as mock_get_config:
                mock_config = Mock()
                mock_config.max_retries = max_retries  # Would normally retry
                mock_get_config.return_value = mock_config

                mock_browser.driver.find_element.side_effect = Exception("No results")

                step = WorkflowStep(
                    action="extract_single",
                    params={"field": "product_name", "selector": "product_name"},
                )

                with pytest.raises(WorkflowExecutionError):
                    executor._execute_step(step)

                # Verify get_adaptive_config was called (but should not retry due to NO_RESULTS)
                mock_get_config.assert_called_once()

        # Reset browser mock
        mock_browser.driver.find_element.reset_mock()

        # Test 2: NETWORK_ERROR should be retried
        network_context = Mock()
        network_context.failure_type = FailureType.NETWORK_ERROR
        network_context.confidence = confidence

        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=network_context
        ):
            with patch.object(
                executor.adaptive_retry_strategy, "get_adaptive_config"
            ) as mock_get_config:
                with patch.object(
                    executor.adaptive_retry_strategy, "calculate_delay", return_value=delay
                ):
                    mock_config = Mock()
                    mock_config.max_retries = 1
                    mock_get_config.return_value = mock_config

                    # Make it fail once, then succeed
                    mock_browser.driver.find_element.side_effect = [
                        Exception("Network error"),
                        Mock(),
                    ]

                    step = WorkflowStep(
                        action="extract_single",
                        params={"field": "product_name", "selector": "product_name"},
                    )

                    # Should succeed after retry
                    executor._execute_step(step)

                    # Verify it was called twice (initial + 1 retry)
                    assert mock_browser.driver.find_element.call_count == call_count

    def test_no_results_detection_integration(
        self, sample_config, mock_create_browser, mock_browser
    ):
        """Test integration with failure classifier for NO_RESULTS detection during extraction actions."""
        executor = WorkflowExecutor(sample_config, headless=True)
        confidence = 0.85
        max_retries = 0
        # Mock the failure classifier to detect NO_RESULTS from exception analysis
        mock_failure_context = Mock()
        mock_failure_context.failure_type = FailureType.NO_RESULTS
        mock_failure_context.confidence = confidence
        mock_failure_context.details = {"exception_analysis": True, "no_results_indicated": True}

        with patch.object(
            executor.failure_classifier, "classify_exception", return_value=mock_failure_context
        ):
            with patch.object(executor.failure_analytics, "record_failure") as mock_record_failure:
                # Mock adaptive retry strategy to prevent retries
                mock_config = Mock()
                mock_config.max_retries = max_retries
                with patch.object(
                    executor.adaptive_retry_strategy,
                    "get_adaptive_config",
                    return_value=mock_config,
                ):
                    # Make extract_single fail with an exception that should be classified as NO_RESULTS
                    mock_browser.driver.find_element.side_effect = Exception(
                        "No products found matching your search criteria"
                    )

                    step = WorkflowStep(
                        action="extract_single",
                        params={"field": "product_name", "selector": "product_name"},
                    )

                    with pytest.raises(WorkflowExecutionError):
                        executor._execute_step(step)

                    # Verify NO_RESULTS was detected and recorded
                    mock_record_failure.assert_called_once()
                    call_args = mock_record_failure.call_args
                    assert call_args[1]["failure_type"] == FailureType.NO_RESULTS
                    assert call_args[1]["context"]["failure_details"]["exception_analysis"] is True
                    assert (
                        call_args[1]["context"]["failure_details"]["no_results_indicated"] is True
                    )
