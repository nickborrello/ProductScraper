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
        self.settings = SettingsManager()

        # Initialize browser
        try:
            self.browser = create_browser(
                site_name=self.config.name,
                headless=headless,
                profile_suffix=f"workflow_{int(time.time())}",
            )
            logger.info(f"Browser initialized for scraper: {self.config.name}")
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to initialize browser: {e}")

        # Initialize anti-detection manager if configured
        if config.anti_detection:
            try:
                self.anti_detection_manager = AntiDetectionManager(
                    self.browser, config.anti_detection
                )
                logger.info(
                    f"Anti-detection manager initialized for scraper: {self.config.name}"
                )
            except Exception as e:
                logger.warning(f"Failed to initialize anti-detection manager: {e}")
                self.anti_detection_manager = None

    def execute_workflow(self, quit_browser: bool = True) -> Dict[str, Any]:
        """
        Execute the complete workflow defined in the configuration.

        Args:
            quit_browser: Whether to quit the browser after execution

        Returns:
            Dict containing execution results and extracted data

        Raises:
            WorkflowExecutionError: If workflow execution fails
        """
        try:
            logger.info(f"Starting workflow execution for: {self.config.name}")

            for step in self.config.workflows:
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

        logger.debug(f"Executing step: {action} with params: {params}")

        # Pre-action anti-detection hook
        if self.anti_detection_manager:
            if not self.anti_detection_manager.pre_action_hook(action, params):
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
            else:
                raise WorkflowExecutionError(f"Unknown action: {action}")

            success = True

        except Exception as e:
            # Try anti-detection error handling
            if self.anti_detection_manager:
                retry_count = params.get("retry_count", 0)
                if self.anti_detection_manager.handle_error(e, action, retry_count):
                    logger.info(
                        f"Anti-detection error handling succeeded for '{action}', retrying..."
                    )
                    # Increment retry count and retry
                    params["retry_count"] = retry_count + 1
                    return self._execute_step(step)

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

        # Optional wait after navigation
        wait_time = params.get("wait_after", 0)
        if wait_time > 0:
            time.sleep(wait_time)

    def _action_wait_for(self, params: Dict[str, Any]):
        """Wait for an element to be present."""
        selector = params.get("selector")
        timeout = params.get("timeout", self.timeout)

        if not selector:
            raise WorkflowExecutionError(
                "Wait_for action requires 'selector' parameter"
            )

        logger.debug(f"Waiting for element: {selector}")
        try:
            WebDriverWait(self.browser.driver, timeout).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
        except TimeoutException:
            logger.error(f"Wait_for element not found within {timeout}s: {selector}")
            logger.debug(f"Current page URL: {self.browser.driver.current_url}")
            logger.debug(f"Page title: {self.browser.driver.title}")
            # Try to log some page content for debugging
            try:
                body_text = self.browser.driver.find_element(By.TAG_NAME, "body").text[:500]
                logger.debug(f"Page body preview: {body_text}...")
            except Exception as e:
                logger.debug(f"Could not get page body: {e}")
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
        """Click on an element."""
        selector = params.get("selector")

        if not selector:
            raise WorkflowExecutionError("Click action requires 'selector' parameter")

        try:
            locator_type = self._get_locator_type(selector)
            element = self.browser.driver.find_element(locator_type, selector)
            element.click()
            logger.debug(f"Clicked element: {selector}")

            # Optional wait after click
            wait_time = params.get("wait_after", 0)
            if wait_time > 0:
                time.sleep(wait_time)
        except NoSuchElementException:
            # Debug logging for failed clicks
            logger.error(f"Click element not found: {selector}")
            logger.debug(f"Current page URL: {self.browser.driver.current_url}")
            logger.debug(f"Page title: {self.browser.driver.title}")
            # Try to log some page content for debugging
            try:
                body_text = self.browser.driver.find_element(By.TAG_NAME, "body").text[:500]
                logger.debug(f"Page body preview: {body_text}...")
            except Exception as e:
                logger.debug(f"Could not get page body: {e}")
            raise WorkflowExecutionError(f"Click element not found: {selector}")

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
