"""
Workflow executor for scraper automation using Selenium WebDriver.
"""

import logging
import random
import re
import time
from typing import Any, Dict, List, Optional, Union, cast

from selenium.common.exceptions import (NoSuchElementException,
                                        TimeoutException, WebDriverException)
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.anti_detection_manager import (AntiDetectionConfig,
                                                AntiDetectionManager)
from src.core.adaptive_retry_strategy import AdaptiveRetryStrategy
from src.core.failure_analytics import FailureAnalytics
from src.core.failure_classifier import FailureClassifier, FailureType, FailureContext
from src.core.settings_manager import SettingsManager
from src.scrapers.models.config import (ScraperConfig, SelectorConfig,
                                        WorkflowStep)
from src.utils.scraping.browser import ScraperBrowser, create_browser

logger = logging.getLogger(__name__)


class WorkflowExecutionError(Exception):
    """Exception raised when workflow execution fails."""

    pass


class WorkflowExecutor:
    """
    Executes scraper workflows defined in YAML configurations using Selenium WebDriver.

    Supports actions like navigate, wait_for, extract_single, extract_multiple, input_text, click.
    Includes error handling, timeouts, and result collection.
    """

    def __init__(
        self,
        config: ScraperConfig,
        headless: bool = True,
        timeout: Optional[int] = None,
    ):
        """
        Initialize the workflow executor.

        Args:
            config: ScraperConfig instance with workflow definition
            headless: Whether to run browser in headless mode
            timeout: Default timeout in seconds (overrides config timeout)
        """
        self.config = config
        self.timeout = timeout or config.timeout
        self.browser: ScraperBrowser
        self.results = {}
        self.selectors = {selector.name: selector for selector in config.selectors}
        self.anti_detection_manager: Optional[AntiDetectionManager] = None
        self.adaptive_retry_strategy = AdaptiveRetryStrategy(
            history_file=f"data/retry_history_{config.name}.json"
        )
        self.failure_classifier = FailureClassifier(
            site_specific_no_results_selectors=self.config.validation.no_results_selectors,
            site_specific_no_results_text_patterns=self.config.validation.no_results_text_patterns,
        )
        self.failure_analytics = FailureAnalytics()
        self.settings = SettingsManager()

        # Log environment details for debugging
        import os
        self.is_ci = os.getenv('CI') == 'true'

        # Adjust timeout for CI environment (headless browsers need more time)
        if self.is_ci and self.timeout < 60:
            self.timeout = 60
            logger.info(f"Adjusted timeout for CI environment: {self.timeout}s")

        logger.info(f"Initializing workflow executor - CI: {self.is_ci}, Headless: {headless}, Timeout: {self.timeout}")

        # Initialize browser
        try:
            self.browser = create_browser(
                site_name=self.config.name,
                headless=headless,
                profile_suffix=f"workflow_{int(time.time())}",
            )
            logger.info(f"Browser initialized for scraper: {self.config.name}")

            # Log browser capabilities for debugging
            try:
                capabilities = self.browser.driver.capabilities
                browser_version = capabilities.get('browserVersion', 'unknown')
                chrome_version = capabilities.get('chrome', {}).get('chromedriverVersion', 'unknown')
                logger.info(f"Browser capabilities - Chrome: {browser_version}, ChromeDriver: {chrome_version}")
            except Exception as cap_e:
                logger.debug(f"Could not get browser capabilities: {cap_e}")

        except Exception as e:
            logger.error(f"Failed to initialize browser: {e}")
            raise WorkflowExecutionError(f"Failed to initialize browser: {e}")

        # Initialize anti-detection manager if configured
        if config.anti_detection:
            try:
                self.anti_detection_manager = AntiDetectionManager(
                    self.browser, config.anti_detection, config.name
                )
                logger.info(
                    f"Anti-detection manager initialized for scraper: {self.config.name}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize anti-detection manager: {e}")
                self.anti_detection_manager = None

        # Track if we've performed the first navigation to avoid rate limiting false positives
        self.first_navigation_done = False
        self.workflow_stopped = False

    def execute_workflow(self, test_skus: Optional[List[str]] = None, quit_browser: bool = True) -> Dict[str, Any]:
        """
        Execute the complete workflow defined in the configuration.

        Args:
            test_skus: List of SKUs to test with (optional)
            quit_browser: Whether to quit the browser after execution

        Returns:
            Dict containing execution results and extracted data

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        try:
            logger.info(f"Starting workflow execution for: {self.config.name}")

            for step in self.config.workflows:
                if self.workflow_stopped:
                    logger.info(f"Workflow stopped due to condition, skipping remaining steps.")
                    break
                self._execute_step(step)

            logger.info(f"Workflow execution completed for: {self.config.name}")
            return {
                "success": True,
                "results": self.results,
                "config_name": self.config.name,
                "steps_executed": len(self.config.workflows),
            }

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise WorkflowExecutionError(f"Workflow execution failed: {e}")
        finally:
            if quit_browser and self.browser:
                self.browser.quit()

    def execute_steps(self, steps: List[Any]) -> Dict[str, Any]:
        """
        Execute specific workflow steps.

        Args:
            steps: List of WorkflowStep objects to execute

        Returns:
            Dict containing execution results and extracted data

        Raises:
            WorkflowExecutionError: If step execution fails
        """
        try:
            logger.info(f"Starting step execution for: {self.config.name}")

            for step in steps:
                if self.workflow_stopped:
                    logger.info(f"Workflow stopped due to condition, skipping remaining steps.")
                    break
                self._execute_step(step)

            logger.info(f"Step execution completed for: {self.config.name}")
            return {
                "success": True,
                "results": self.results,
                "config_name": self.config.name,
                "steps_executed": len(steps),
            }

        except Exception as e:
            logger.error(f"Step execution failed: {e}")
            raise WorkflowExecutionError(f"Step execution failed: {e}")

    def _execute_step(self, step: WorkflowStep):
        """
        Execute a single workflow step.

        Args:
            step: WorkflowStep to execute

        Raises:
            WorkflowExecutionError: If step execution fails
        """
        action = step.action.lower()
        params = step.params or {}
        start_time = time.time()
        params["start_time"] = start_time  # Track for analytics

        logger.debug(f"Executing step: {action} with params: {params}")

        # Pre-action anti-detection hook
        if self.anti_detection_manager:
            # Skip rate limiting detection for the first navigation to avoid false positives
            skip_rate_limit_check = (action == "navigate" and not self.first_navigation_done)
            if not self.anti_detection_manager.pre_action_hook(action, params, skip_rate_limit_check=skip_rate_limit_check):
                raise WorkflowExecutionError(
                    f"Pre-action anti-detection check failed for '{action}'"
                )

        success = False
        try:
            if action == "navigate":
                self._action_navigate(params)
            elif action == "wait_for":
                self._action_wait_for(params)
            elif action == "extract_single":
                self._action_extract_single(params)
            elif action == "extract_multiple":
                self._action_extract_multiple(params)
            elif action == "input_text":
                self._action_input_text(params)
            elif action == "click":
                self._action_click(params)
            elif action == "wait":
                self._action_wait(params)
            elif action == "extract":
                self._action_extract(params)
            elif action == "login":
                self._action_login(params)
            elif action == "detect_captcha":
                self._action_detect_captcha(params)
            elif action == "handle_blocking":
                self._action_handle_blocking(params)
            elif action == "rate_limit":
                self._action_rate_limit(params)
            elif action == "simulate_human":
                self._action_simulate_human(params)
            elif action == "rotate_session":
                self._action_rotate_session(params)
            elif action == "validate_http_status":
                self._action_validate_http_status(params)
            elif action == "check_no_results":
                self._action_check_no_results(params)
            elif action == "conditional_skip":
                self._action_conditional_skip(params)
            else:
                raise WorkflowExecutionError(f"Unknown action: {action}")

            success = True

            # Record success for analytics
            start_time = time.time()
            duration = start_time - (params.get("start_time", start_time))
            self.failure_analytics.record_success(
                site_name=self.config.name,
                duration=duration,
                action=action,
                session_id=getattr(self.browser, 'session_id', None)
            )

            # Record success for learning
            retry_count = params.get("retry_count", 0)
            if retry_count > 0:
                # This was a successful retry
                self.adaptive_retry_strategy.record_failure(
                    failure_type=FailureType.NETWORK_ERROR,  # Default, will be updated with actual type
                    site_name=self.config.name,
                    action=action,
                    retry_count=retry_count,
                    context={"params": params},
                    success_after_retry=True,
                    final_success=True
                )

        except Exception as e:
            # Classify the failure to determine retry strategy
            try:
                failure_context = self.failure_classifier.classify_exception(e, {"action": action})
                logger.debug(f"Failure classified: {failure_context.failure_type.value} "
                            f"(confidence: {failure_context.confidence})")

                # For wait_for timeouts, check if page indicates no results
                if action == "wait_for" and isinstance(e, TimeoutException):
                    try:
                        page_context = {"action": action}
                        if "http_status" in self.results:
                            page_context["status_code"] = self.results["http_status"]
                        page_failure_context = self.failure_classifier.classify_page_content(
                            self.browser.driver, page_context
                        )
                        if (page_failure_context.failure_type == FailureType.NO_RESULTS and
                            page_failure_context.confidence > failure_context.confidence):
                            logger.debug(f"Reclassified failure from {failure_context.failure_type.value} "
                                       f"to {page_failure_context.failure_type.value} based on page content")
                            failure_context = page_failure_context
                    except Exception as page_classify_e:
                        logger.debug(f"Could not classify page content: {page_classify_e}")

            except Exception as classify_e:
                logger.debug(f"Could not classify failure: {classify_e}")
                # Default to network error
                failure_context = FailureContext(
                    failure_type=FailureType.NETWORK_ERROR,
                    confidence=0.5,
                    details={"classification_error": str(classify_e)},
                    recovery_strategy="retry"
                )

            # Get adaptive retry configuration
            retry_count = params.get("retry_count", 0)
            adaptive_config = self.adaptive_retry_strategy.get_adaptive_config(
                failure_context.failure_type,
                self.config.name,
                retry_count
            )

            # Check if we should retry
            should_retry = (
                retry_count < adaptive_config.max_retries and
                failure_context.failure_type != FailureType.PAGE_NOT_FOUND and
                failure_context.failure_type != FailureType.NO_RESULTS
            )

            if should_retry:
                # Calculate delay using adaptive strategy
                delay = self.adaptive_retry_strategy.calculate_delay(adaptive_config, retry_count)
                logger.info(
                    f"Adaptive retry for '{action}' - failure: {failure_context.failure_type.value}, "
                    f"retry {retry_count + 1}/{adaptive_config.max_retries}, delay: {delay:.1f}s"
                )

                # Apply the delay
                time.sleep(delay)

                # Try anti-detection error handling as fallback
                if self.anti_detection_manager:
                    if self.anti_detection_manager.handle_error(e, action, retry_count):
                        logger.info(f"Anti-detection error handling succeeded for '{action}', retrying...")
                    else:
                        logger.debug(f"Anti-detection error handling failed for '{action}'")

                # Record the failure for analytics
                duration = time.time() - start_time
                self.failure_analytics.record_failure(
                    site_name=self.config.name,
                    failure_type=failure_context.failure_type,
                    duration=duration,
                    action=action,
                    retry_count=retry_count,
                    context={
                        "exception": str(e),
                        "params": params,
                        "failure_details": failure_context.details,
                        "confidence": failure_context.confidence
                    },
                    success_after_retry=False,
                    final_success=False,
                    session_id=getattr(self.browser, 'session_id', None),
                    user_agent=getattr(self.browser, 'user_agent', None)
                )

                # Record the failure for learning
                self.adaptive_retry_strategy.record_failure(
                    failure_type=failure_context.failure_type,
                    site_name=self.config.name,
                    action=action,
                    retry_count=retry_count,
                    context={
                        "exception": str(e),
                        "params": params,
                        "failure_details": failure_context.details,
                        "confidence": failure_context.confidence
                    },
                    success_after_retry=False,  # Will be updated if retry succeeds
                    final_success=False
                )

                # Increment retry count and retry
                params["retry_count"] = retry_count + 1
                return self._execute_step(step)

            # No more retries or not retryable - record final failure
            duration = time.time() - start_time
            self.failure_analytics.record_failure(
                site_name=self.config.name,
                failure_type=failure_context.failure_type,
                duration=duration,
                action=action,
                retry_count=retry_count,
                context={
                    "exception": str(e),
                    "params": params,
                    "failure_details": failure_context.details,
                    "confidence": failure_context.confidence
                },
                success_after_retry=False,
                final_success=False,
                session_id=getattr(self.browser, 'session_id', None),
                user_agent=getattr(self.browser, 'user_agent', None)
            )

            self.adaptive_retry_strategy.record_failure(
                failure_type=failure_context.failure_type,
                site_name=self.config.name,
                action=action,
                retry_count=retry_count,
                context={
                    "exception": str(e),
                    "params": params,
                    "failure_details": failure_context.details,
                    "confidence": failure_context.confidence
                },
                success_after_retry=False,
                final_success=False
            )

            # Store failure context in results for debugging/analysis
            self.results["failure_context"] = {
                "type": failure_context.failure_type.value,
                "confidence": failure_context.confidence,
                "details": failure_context.details,
                "recovery_strategy": failure_context.recovery_strategy,
                "retries_attempted": retry_count
            }

            raise WorkflowExecutionError(f"Failed to execute step '{action}': {e}")
        finally:
            # Post-action anti-detection hook
            if self.anti_detection_manager:
                self.anti_detection_manager.post_action_hook(action, params, success)

    def _action_navigate(self, params: Dict[str, Any]):
        """Navigate to a URL."""
        url = params.get("url")
        if not url:
            raise WorkflowExecutionError("Navigate action requires 'url' parameter")

        logger.info(f"Navigating to: {url}")
        self.browser.get(url)

        # Check HTTP status if monitoring is enabled
        if self.config.http_status and self.config.http_status.enabled:
            self._check_http_status_after_navigation(url, params)

        # Optional wait after navigation
        wait_time = params.get("wait_after", 0)
        if wait_time > 0:
            time.sleep(wait_time)

        # Mark that first navigation is done
        self.first_navigation_done = True

    def _check_http_status_after_navigation(self, url: str, params: Dict[str, Any]):
        """Check HTTP status after navigation and handle errors."""
        if not self.config.http_status:
            return

        # Give the page a moment to load
        time.sleep(0.5)

        status_code = self.browser.check_http_status()
        if status_code is None:
            logger.debug(f"Could not determine HTTP status for {url}")
            return

        logger.debug(f"HTTP status for {url}: {status_code}")

        # Store status in results for later use
        self.results["http_status"] = status_code
        self.results["http_status_url"] = url

        # Check if status indicates an error
        if self.config.http_status.fail_on_error_status:
            error_codes = self.config.http_status.error_status_codes
            if status_code in error_codes:
                logger.error(f"HTTP error status {status_code} detected for {url}")
                raise WorkflowExecutionError(
                    f"HTTP {status_code} error encountered while navigating to {url}"
                )

        # Log warnings for redirect status codes
        warning_codes = self.config.http_status.warning_status_codes
        if status_code in warning_codes:
            logger.warning(f"HTTP redirect status {status_code} detected for {url}")

    def _action_wait_for(self, params: Dict[str, Any]):
        """Wait for an element to be present."""
        selector = params.get("selector")
        timeout = params.get("timeout", self.timeout)

        if not selector:
            raise WorkflowExecutionError(
                "Wait_for action requires 'selector' parameter"
            )

        logger.debug(f"Waiting for element: {selector} (timeout: {timeout}s, CI: {self.is_ci})")

        start_time = time.time()
        try:
            WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            wait_duration = time.time() - start_time
            logger.info(f"✅ Element found after {wait_duration:.2f}s: {selector}")
        except TimeoutException:
            wait_duration = time.time() - start_time
            logger.warning(f"⏰ TIMEOUT: Element not found within {timeout}s (waited {wait_duration:.2f}s): {selector}")
            logger.debug(f"Current page URL: {self.browser.driver.current_url}")
            logger.debug(f"Page title: {self.browser.driver.title}")

            # Try to log some page content for debugging
            try:
                body_text = self.browser.driver.find_element(By.TAG_NAME, "body").text[:500]
                logger.debug(f"Page body preview: {body_text}...")
            except Exception as e:
                logger.debug(f"Could not get page body: {e}")

            # Log available elements for debugging
            try:
                all_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "*")
                logger.debug(f"Total elements on page: {len(all_elements)}")

                # Try to find similar selectors
                if "." in selector or "#" in selector:
                    similar_selectors = []
                    for el in all_elements[:50]:  # Check first 50 elements
                        try:
                            el_classes = el.get_attribute("class") or ""
                            el_id = el.get_attribute("id") or ""
                            if selector.startswith(".") and selector[1:] in el_classes.split():
                                similar_selectors.append(f".{selector[1:]}")
                            elif selector.startswith("#") and selector[1:] == el_id:
                                similar_selectors.append(selector)
                        except:
                            pass
                    if similar_selectors:
                        logger.debug(f"Found similar elements: {similar_selectors[:5]}")
            except Exception as debug_e:
                logger.debug(f"Could not analyze page elements: {debug_e}")

            raise WorkflowExecutionError(
                f"Element not found within {timeout}s: {selector}"
            )

    def _action_wait(self, params: Dict[str, Any]):
        """Simple wait/delay."""
        seconds = params.get("seconds", params.get("timeout", 1))
        logger.debug(f"Waiting for {seconds} seconds")
        time.sleep(seconds)

    def _action_extract_single(self, params: Dict[str, Any]):
        """Extract a single value using a selector."""
        field_name = params.get("field")
        selector_name = params.get("selector")

        if not field_name or not selector_name:
            raise WorkflowExecutionError(
                "Extract_single requires 'field' and 'selector' parameters"
            )

        selector_config = self.selectors.get(selector_name)
        if not selector_config:
            raise WorkflowExecutionError(
                f"Selector '{selector_name}' not found in config"
            )

        try:
            element = self.browser.driver.find_element(
                By.CSS_SELECTOR, selector_config.selector
            )
            value = self._extract_value_from_element(element, selector_config.attribute)
            if field_name == "Brand" and value:
                match = re.match(r"Visit (?:the )?(.+?) Store", value)
                if match:
                    value = match.group(1)
            elif field_name == "Weight" and value:
                # Process weight: extract number and convert ounces to pounds
                weight_match = re.search(r"(\d+(?:\.\d+)?)", value)
                if weight_match:
                    weight_num = float(weight_match.group(1))
                    if "ounce" in value.lower():
                        # Convert ounces to pounds (1 oz = 0.0625 lbs)
                        weight_num = weight_num / 16
                    value = f"{weight_num:.2f} lbs"
                else:
                    value = None
            self.results[field_name] = value
            logger.debug(f"Extracted {field_name}: {value}")
        except NoSuchElementException:
            logger.warning(f"Element not found for field: {field_name}")
            self.results[field_name] = None

    def _action_extract_multiple(self, params: Dict[str, Any]):
        """Extract multiple values using a selector."""
        field_name = params.get("field")
        selector_name = params.get("selector")

        if not field_name or not selector_name:
            raise WorkflowExecutionError(
                "Extract_multiple requires 'field' and 'selector' parameters"
            )

        selector_config = self.selectors.get(selector_name)
        if not selector_config:
            raise WorkflowExecutionError(
                f"Selector '{selector_name}' not found in config"
            )

        try:
            elements = self.browser.driver.find_elements(
                By.CSS_SELECTOR, selector_config.selector
            )
            values = []
            for element in elements:
                value = self._extract_value_from_element(
                    element, selector_config.attribute
                )
                if value:
                    values.append(value)

            if field_name == "Brand":
                cleaned_values = []
                for v in values:
                    if v:
                        match = re.match(r"Visit (?:the )?(.+?) Store", v)
                        if match:
                            cleaned_values.append(match.group(1))
                        else:
                            cleaned_values.append(v)
                values = cleaned_values
            elif field_name == "Weight":
                # Process weight values: extract number and convert ounces to pounds
                processed_values = []
                for v in values:
                    if v:
                        weight_match = re.search(r"(\d+(?:\.\d+)?)", v)
                        if weight_match:
                            weight_num = float(weight_match.group(1))
                            if "ounce" in v.lower():
                                # Convert ounces to pounds (1 oz = 0.0625 lbs)
                                weight_num = weight_num / 16
                            processed_values.append(f"{weight_num:.2f} lbs")
                values = processed_values
            self.results[field_name] = values
            logger.debug(f"Extracted {len(values)} items for {field_name}")
        except Exception as e:
            logger.warning(f"Failed to extract multiple values for {field_name}: {e}")
            self.results[field_name] = []

    def _get_locator_type(self, selector: str):
        """Determine locator type based on selector format."""
        if selector.startswith("//") or selector.startswith(".//"):
            return By.XPATH
        else:
            return By.CSS_SELECTOR

    def _action_extract(self, params: Dict[str, Any]):
        """Extract multiple fields at once (legacy compatibility)."""
        fields = params.get("fields", [])
        logger.debug(f"Starting extract action for fields: {fields}")
        for field_name in fields:
            selector_config = self.selectors.get(field_name)
            if not selector_config:
                logger.warning(f"Selector '{field_name}' not found in config")
                continue

            try:
                locator_type = self._get_locator_type(selector_config.selector)
                if selector_config.multiple:
                    elements = self.browser.driver.find_elements(
                        locator_type, selector_config.selector
                    )
                    values = []
                    for element in elements:
                        value = self._extract_value_from_element(
                            element, selector_config.attribute
                        )
                        if value:
                            values.append(value)
                    if field_name == "Brand":
                        cleaned_values = []
                        for v in values:
                            if v:
                                match = re.match(r"Visit (?:the )?(.+?) Store", v)
                                if match:
                                    cleaned_values.append(match.group(1))
                                else:
                                    cleaned_values.append(v)
                        values = cleaned_values
                    self.results[field_name] = values
                else:
                    element = self.browser.driver.find_element(
                        locator_type, selector_config.selector
                    )
                    value = self._extract_value_from_element(
                        element, selector_config.attribute
                    )
                    if field_name == "Brand" and value:
                        match = re.match(r"Visit (?:the )?(.+?) Store", value)
                        if match:
                            value = match.group(1)
                    self.results[field_name] = value
                logger.debug(f"Extracted {field_name}: {self.results[field_name]}")
            except NoSuchElementException:
                logger.warning(f"Element not found for field: {field_name}")
                self.results[field_name] = [] if selector_config.multiple else None
        logger.debug(f"Extract action completed. Results: {self.results}")

    def _action_input_text(self, params: Dict[str, Any]):
        """Input text into a form field."""
        selector = params.get("selector")
        text = params.get("text")
        clear_first = params.get("clear_first", True)

        if not selector or text is None:
            raise WorkflowExecutionError(
                "Input_text requires 'selector' and 'text' parameters"
            )

        try:
            element = self.browser.driver.find_element(By.CSS_SELECTOR, selector)
            if clear_first:
                element.clear()
            element.send_keys(str(text))
            logger.debug(f"Input text into {selector}: {text}")
        except NoSuchElementException:
            raise WorkflowExecutionError(f"Input element not found: {selector}")

    def _action_click(self, params: Dict[str, Any]):
        """Click on an element with proper WebDriverWait and retry logic."""
        selector = params.get("selector")

        if not selector:
            raise WorkflowExecutionError("Click action requires 'selector' parameter")

        locator_type = self._get_locator_type(selector)
        max_retries = params.get("max_retries", 3 if self.is_ci else 1)  # More retries in CI

        logger.debug(f"Attempting to click element: {selector} (locator: {locator_type}, CI: {self.is_ci}, max_retries: {max_retries})")

        # Initial wait for element to be clickable
        try:
            WebDriverWait(self.browser.driver, self.timeout).until(
                EC.element_to_be_clickable((locator_type, selector))
            )
            logger.debug("Element is clickable, proceeding to click")
        except TimeoutException:
            logger.debug("Initial wait for clickable element failed, entering retry loop")
            # Retry logic with proper waiting
            for attempt in range(max_retries):
                try:
                    # Use progressively shorter timeout for retries
                    retry_timeout = max(self.timeout // (2 ** (attempt + 1)), 1)
                    WebDriverWait(self.browser.driver, retry_timeout).until(
                        EC.element_to_be_clickable((locator_type, selector))
                    )
                    logger.debug(f"Element became clickable on retry {attempt + 1}")
                    break
                except TimeoutException:
                    if attempt == max_retries - 1:
                        # Debug logging for failed clicks
                        logger.error(f"Click element not clickable after {max_retries} retries: {selector}")
                        logger.debug(f"Current page URL: {self.browser.driver.current_url}")
                        logger.debug(f"Page title: {self.browser.driver.title}")

                        # Try to log some page content for debugging
                        try:
                            body_text = self.browser.driver.find_element(By.TAG_NAME, "body").text[:500]
                            logger.debug(f"Page body preview: {body_text}...")
                        except Exception as debug_e:
                            logger.debug(f"Could not get page body: {debug_e}")

                        # Log available elements for debugging
                        try:
                            all_elements = self.browser.driver.find_elements(By.CSS_SELECTOR, "*")
                            logger.debug(f"Total elements on page: {len(all_elements)}")

                            # Try to find similar selectors
                            if "." in selector or "#" in selector:
                                similar_selectors = []
                                for el in all_elements[:100]:  # Check first 100 elements
                                    try:
                                        el_classes = el.get_attribute("class") or ""
                                        el_id = el.get_attribute("id") or ""
                                        if selector.startswith(".") and selector[1:] in el_classes.split():
                                            similar_selectors.append(f".{selector[1:]}")
                                        elif selector.startswith("#") and selector[1:] == el_id:
                                            similar_selectors.append(selector)
                                    except:
                                        pass
                                if similar_selectors:
                                    logger.debug(f"Found similar elements: {similar_selectors[:10]}")
                                else:
                                    logger.debug("No similar elements found on page")
                        except Exception as debug_e:
                            logger.debug(f"Could not analyze page elements: {debug_e}")

                        raise WorkflowExecutionError(f"Element not clickable after {max_retries} retries: {selector}")
                    logger.debug(f"Retry {attempt + 1} failed, trying again")

        # Now perform the click
        try:
            element = self.browser.driver.find_element(locator_type, selector)

            # Scroll element into view if needed
            try:
                self.browser.driver.execute_script("arguments[0].scrollIntoView({block: 'center', inline: 'center'});", element)
                time.sleep(0.5)  # Brief pause after scrolling
            except Exception as scroll_e:
                logger.debug(f"Could not scroll element into view: {scroll_e}")

            # Attempt click
            element.click()
            logger.debug(f"Successfully clicked element: {selector}")

            # Optional wait after click
            wait_time = params.get("wait_after", 0)
            if wait_time > 0:
                logger.debug(f"Waiting {wait_time}s after click")
                time.sleep(wait_time)

        except Exception as e:
            raise WorkflowExecutionError(f"Failed to click element after waiting: {e}")

    def _action_login(self, params: Dict[str, Any]):
        """Execute login workflow with credentials."""
        # Merge login details from config into params
        if self.config.login:
            params.update(self.config.login.dict())

        # Get credentials from settings manager
        scraper_name = self.config.name
        if scraper_name == "phillips":
            username, password = self.settings.phillips_credentials
            params["username"] = username
            params["password"] = password
        elif scraper_name == "orgill":
            username, password = self.settings.orgill_credentials
            params["username"] = username
            params["password"] = password
        elif scraper_name == "petfoodex":
            username, password = self.settings.petfoodex_credentials
            params["username"] = username
            params["password"] = password

        username = params.get("username")
        password = params.get("password")
        login_url = params.get("url")
        username_field = params.get("username_field")
        password_field = params.get("password_field")
        submit_button = params.get("submit_button")
        success_indicator = params.get("success_indicator")

        # Debug logging for credentials
        logger.debug(f"Login params for {scraper_name}: username={'***' if username else 'None'}, password={'***' if password else 'None'}, url={login_url}")
        logger.debug(f"Login fields: username_field={username_field}, password_field={password_field}, submit_button={submit_button}")

        if not all(
            [
                username,
                password,
                login_url,
                username_field,
                password_field,
                submit_button,
            ]
        ):
            logger.error(f"Missing login parameters for {scraper_name}: username={bool(username)}, password={bool(password)}, url={bool(login_url)}, username_field={bool(username_field)}, password_field={bool(password_field)}, submit_button={bool(submit_button)}")
            raise WorkflowExecutionError(
                "Login action requires username, password, url, username_field, password_field, and submit_button parameters"
            )

        logger.info("Executing login workflow")

        # Navigate to login page
        self.browser.get(login_url)
        time.sleep(1)  # Brief wait for page load

        # Input username
        try:
            username_element = self.browser.driver.find_element(
                By.CSS_SELECTOR, username_field
            )
            username_element.clear()
            username_element.send_keys(str(username))
            logger.debug("Entered username")
        except NoSuchElementException:
            raise WorkflowExecutionError(f"Username field not found: {username_field}")

        # Input password
        try:
            password_element = self.browser.driver.find_element(
                By.CSS_SELECTOR, password_field
            )
            password_element.clear()
            password_element.send_keys(str(password))
            logger.debug("Entered password")
        except NoSuchElementException:
            raise WorkflowExecutionError(f"Password field not found: {password_field}")

        # Click submit button
        try:
            submit_element = self.browser.driver.find_element(
                By.CSS_SELECTOR, submit_button
            )
            submit_element.click()
            logger.debug("Clicked submit button")
        except NoSuchElementException:
            raise WorkflowExecutionError(f"Submit button not found: {submit_button}")

        # Wait for success indicator if provided
        if success_indicator:
            try:
                WebDriverWait(self.browser.driver, self.timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, success_indicator))
                )
                logger.info("Login successful - success indicator found")
            except TimeoutException:
                raise WorkflowExecutionError(
                    f"Login failed - success indicator not found within {self.timeout}s: {success_indicator}"
                )
        else:
            # If no success indicator, wait a bit for login to process
            time.sleep(3)
            logger.info("Login submitted (no success indicator configured)")

        # Check for login failure indicators if configured
        failure_indicators = params.get("failure_indicators")
        if failure_indicators:
            logger.debug("Checking for login failure indicators")
            # Include HTTP status if available
            context = {"action": "login"}
            if "http_status" in self.results:
                context["status_code"] = self.results["http_status"]
            failure_context = self.failure_classifier.classify_page_content(
                self.browser.driver, context
            )

            # Check if failure was detected with sufficient confidence
            if failure_context.failure_type.value == "login_failed" and failure_context.confidence > 0.5:
                logger.error(f"Login failure detected: {failure_context.details}")
                raise WorkflowExecutionError(
                    f"Login failed - detected failure indicators: {failure_context.details}"
                )
            elif failure_context.confidence > 0.3:
                logger.warning(f"Potential login failure detected (confidence: {failure_context.confidence}): {failure_context.details}")

    def _action_detect_captcha(self, params: Dict[str, Any]):
        """Detect CAPTCHA presence on current page."""
        if (
            not self.anti_detection_manager
            or not self.anti_detection_manager.captcha_detector
        ):
            logger.warning("CAPTCHA detection not enabled")
            return

        detected = self.anti_detection_manager.captcha_detector.detect_captcha(
            self.browser.driver
        )
        self.results["captcha_detected"] = detected

        if detected:
            logger.info("CAPTCHA detected on current page")
            # Store detection result
            self.results["captcha_details"] = {
                "detected": True,
                "timestamp": time.time(),
            }
        else:
            logger.debug("No CAPTCHA detected on current page")

    def _action_handle_blocking(self, params: Dict[str, Any]):
        """Handle blocking pages."""
        if (
            not self.anti_detection_manager
            or not self.anti_detection_manager.blocking_handler
        ):
            logger.warning("Blocking handling not enabled")
            return

        handled = self.anti_detection_manager.blocking_handler.handle_blocking(
            self.browser.driver
        )
        self.results["blocking_handled"] = handled

        if handled:
            logger.info("Blocking page handled successfully")
        else:
            logger.warning("Failed to handle blocking page")

    def _action_rate_limit(self, params: Dict[str, Any]):
        """Apply rate limiting delay."""
        if (
            not self.anti_detection_manager
            or not self.anti_detection_manager.rate_limiter
        ):
            logger.warning("Rate limiting not enabled")
            return

        delay = params.get("delay", None)
        if delay:
            # Custom delay
            time.sleep(delay)
            logger.debug(f"Applied custom rate limit delay: {delay}s")
        else:
            # Use rate limiter's intelligent delay
            self.anti_detection_manager.rate_limiter.apply_delay()
            logger.debug("Applied intelligent rate limiting")

    def _action_simulate_human(self, params: Dict[str, Any]):
        """Simulate human-like behavior."""
        if (
            not self.anti_detection_manager
            or not self.anti_detection_manager.human_simulator
        ):
            logger.warning("Human behavior simulation not enabled")
            return

        behavior_type = params.get("behavior", "random")
        duration = params.get("duration", 2.0)

        if behavior_type == "reading":
            time.sleep(duration)
            logger.debug(f"Simulated reading behavior for {duration}s")
        elif behavior_type == "typing":
            # Simulate typing delay
            time.sleep(duration * 0.1)  # Shorter for typing
            logger.debug(f"Simulated typing behavior for {duration * 0.1}s")
        elif behavior_type == "navigation":
            time.sleep(duration)
            logger.debug(f"Simulated navigation pause for {duration}s")
        else:
            # Random human-like pause
            time.sleep(random.uniform(1, duration))
            logger.debug(
                f"Simulated random human behavior for {random.uniform(1, duration):.2f}s"
            )

    def _action_rotate_session(self, params: Dict[str, Any]):
        """Force session rotation."""
        if (
            not self.anti_detection_manager
            or not self.anti_detection_manager.session_manager
        ):
            logger.warning("Session rotation not enabled")
            return

        rotated = self.anti_detection_manager.session_manager.rotate_session(
            self.anti_detection_manager
        )
        self.results["session_rotated"] = rotated

        if rotated:
            logger.info("Session rotated successfully")
        else:
            logger.warning("Failed to rotate session")

    def _action_validate_http_status(self, params: Dict[str, Any]):
        """Validate HTTP status of current page."""
        expected_status = params.get("expected_status")
        fail_on_error = params.get("fail_on_error", True)
        error_codes = params.get("error_codes", [400, 401, 403, 404, 500, 502, 503, 504])

        status_code = self.browser.check_http_status()
        current_url = self.browser.driver.current_url

        if status_code is None:
            if fail_on_error:
                logger.error(f"Could not determine HTTP status for {current_url}")
                raise WorkflowExecutionError(f"Failed to determine HTTP status for {current_url}")
            else:
                logger.warning(f"Could not determine HTTP status for {current_url}")
                return

        logger.debug(f"Validated HTTP status for {current_url}: {status_code}")

        # Store status in results
        self.results["validated_http_status"] = status_code
        self.results["validated_http_url"] = current_url

        # Check expected status if specified
        if expected_status is not None:
            if status_code != expected_status:
                error_msg = f"HTTP status mismatch: expected {expected_status}, got {status_code} for {current_url}"
                if fail_on_error:
                    logger.error(error_msg)
                    raise WorkflowExecutionError(error_msg)
                else:
                    logger.warning(error_msg)

        # Check for error status codes
        if status_code in error_codes:
            error_msg = f"HTTP error status {status_code} detected for {current_url}"
            if fail_on_error:
                logger.error(error_msg)
                raise WorkflowExecutionError(error_msg)
            else:
                logger.warning(error_msg)

    def _action_check_no_results(self, params: Dict[str, Any]):
        """
        Explicitly check if the current page indicates a 'no results' scenario.
        Sets 'no_results_found' in self.results to True if detected.
        Uses both config validation patterns and failure classifier.
        """
        logger.info("Performing explicit 'check_no_results' action.")
        min_confidence = params.get("min_confidence", 0.5)  # Lower threshold for explicit check

        # First, check using config validation patterns if available
        config_no_results = getattr(self.config, 'validation', {}).get('no_results_selectors', [])
        config_text_patterns = getattr(self.config, 'validation', {}).get('no_results_text_patterns', [])

        try:
            page_source = self.browser.driver.page_source.lower()
            page_title = self.browser.driver.title.lower()

            # Check config selectors
            for selector in config_no_results:
                try:
                    elements = self.browser.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"✅ No results detected via config selector: {selector}")
                        self.results["no_results_found"] = True
                        return
                except Exception as e:
                    logger.debug(f"Error checking selector {selector}: {e}")

            # Check config text patterns
            for pattern in config_text_patterns:
                if pattern.lower() in page_source or pattern.lower() in page_title:
                    logger.info(f"✅ No results detected via config text pattern: {pattern}")
                    self.results["no_results_found"] = True
                    return

        except Exception as e:
            logger.debug(f"Error during config-based no-results check: {e}")

        # Fallback to failure classifier
        classification_context = {"action": "check_no_results"}
        if "http_status" in self.results:
            classification_context["status_code"] = self.results["http_status"]

        failure_context = self.failure_classifier.classify_page_content(
            self.browser.driver, classification_context
        )

        if (
            failure_context.failure_type == FailureType.NO_RESULTS
            and failure_context.confidence >= min_confidence
        ):
            self.results["no_results_found"] = True
            logger.info(
                f"✅ 'No results' detected via classifier with confidence "
                f"{failure_context.confidence:.2f}."
            )
        else:
            self.results["no_results_found"] = False
            logger.debug(
                f"No 'no results' detected (Type: {failure_context.failure_type.value}, "
                f"Confidence: {failure_context.confidence:.2f})."
            )

    def _action_conditional_skip(self, params: Dict[str, Any]):
        """
        Conditionally skip the rest of the workflow based on a flag in self.results.
        """
        if_flag = params.get("if_flag")
        if not if_flag:
            raise WorkflowExecutionError(
                "conditional_skip action requires 'if_flag' parameter"
            )

        if self.results.get(if_flag):
            logger.info(
                f"Condition '{if_flag}' is true, stopping workflow execution."
            )
            self.workflow_stopped = True

    def _extract_value_from_element(
        self, element, attribute: Optional[str]
    ) -> Optional[str]:
        """
        Extract value from a web element based on attribute.

        Args:
            element: Selenium WebElement
            attribute: Attribute to extract ('text', 'href', 'src', etc.) or None for text

        Returns:
            Extracted value or None
        """
        try:
            if attribute == "text" or attribute is None:
                return element.text.strip()
            elif attribute in ["href", "src", "alt", "title", "value"]:
                return element.get_attribute(attribute)
            else:
                return element.get_attribute(attribute)
        except Exception as e:
            logger.warning(f"Failed to extract value from element: {e}")
            return None

    def get_results(self) -> Dict[str, Any]:
        """Get the current execution results."""
        return self.results.copy()
