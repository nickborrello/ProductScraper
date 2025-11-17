"""
Anti-detection manager for web scraping operations.
Provides comprehensive anti-detection capabilities including CAPTCHA detection,
rate limiting, human behavior simulation, and session management.
"""

import logging
import random
import time
from typing import Any, Callable, Dict, List, Optional

from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.utils.scraping.browser import ScraperBrowser

logger = logging.getLogger(__name__)


class AntiDetectionConfig:
    """Configuration for anti-detection modules."""

    def __init__(
        self,
        enable_captcha_detection: bool = True,
        enable_rate_limiting: bool = True,
        enable_human_simulation: bool = True,
        enable_session_rotation: bool = True,
        enable_blocking_handling: bool = True,
        captcha_selectors: Optional[List[str]] = None,
        blocking_selectors: Optional[List[str]] = None,
        rate_limit_min_delay: float = 1.0,
        rate_limit_max_delay: float = 5.0,
        human_simulation_enabled: bool = True,
        session_rotation_interval: int = 100,
        max_retries_on_detection: int = 3,
    ):
        self.enable_captcha_detection = enable_captcha_detection
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_human_simulation = human_simulation_enabled
        self.enable_session_rotation = enable_session_rotation
        self.enable_blocking_handling = enable_blocking_handling
        self.captcha_selectors = captcha_selectors or [
            "[class*='captcha']",
            "[id*='captcha']",
            "[class*='recaptcha']",
            "[id*='recaptcha']",
            ".g-recaptcha",
            "#captcha-container",
        ]
        self.blocking_selectors = blocking_selectors or [
            "[class*='blocked']",
            "[id*='blocked']",
            "[class*='banned']",
            "[id*='banned']",
            "[class*='access-denied']",
            "[id*='access-denied']",
        ]
        self.rate_limit_min_delay = rate_limit_min_delay
        self.rate_limit_max_delay = rate_limit_max_delay
        self.session_rotation_interval = session_rotation_interval
        self.max_retries_on_detection = max_retries_on_detection


class AntiDetectionManager:
    """
    Manages anti-detection measures for web scraping operations.

    Provides integrated anti-detection capabilities including:
    - CAPTCHA detection and handling
    - Rate limiting with intelligent delays
    - Human behavior simulation
    - Session rotation
    - Blocking page detection
    """

    def __init__(self, browser: ScraperBrowser, config: AntiDetectionConfig):
        """
        Initialize the anti-detection manager.

        Args:
            browser: ScraperBrowser instance
            config: AntiDetectionConfig with module settings
        """
        self.browser = browser
        self.config = config
        self.request_count = 0
        self.last_request_time = 0
        self.session_start_time = time.time()

        # Initialize modules
        self.captcha_detector = (
            CaptchaDetector(self.config) if config.enable_captcha_detection else None
        )
        self.rate_limiter = (
            RateLimiter(self.config) if config.enable_rate_limiting else None
        )
        self.human_simulator = (
            HumanBehaviorSimulator(self.config)
            if config.enable_human_simulation
            else None
        )
        self.session_manager = (
            SessionManager(self.config) if config.enable_session_rotation else None
        )
        self.blocking_handler = (
            BlockingHandler(self.config) if config.enable_blocking_handling else None
        )

        logger.info(
            "AntiDetectionManager initialized with enabled modules: %s",
            [
                module
                for module in [
                    "captcha",
                    "rate_limit",
                    "human_sim",
                    "session",
                    "blocking",
                ]
                if getattr(
                    self,
                    (
                        f"{module}_detector"
                        if module == "captcha"
                        else (
                            f"{module}_handler"
                            if module == "blocking"
                            else (
                                f"{module}_manager"
                                if module == "session"
                                else (
                                    f"{module}_simulator"
                                    if module == "human"
                                    else f"{module}_limiter"
                                )
                            )
                        )
                    ),
                    None,
                )
                is not None
            ],
        )

    def pre_action_hook(self, action: str, params: Dict[str, Any]) -> bool:
        """
        Execute pre-action anti-detection measures.

        Args:
            action: The workflow action being executed
            params: Action parameters

        Returns:
            True if action should proceed, False if blocked
        """
        try:
            # Apply rate limiting
            if self.rate_limiter:
                self.rate_limiter.apply_delay()

            # Simulate human behavior before action
            if self.human_simulator:
                self.human_simulator.simulate_pre_action(action, params)

            # Check for blocking before proceeding
            if self.blocking_handler and self._should_check_blocking(action):
                if self.blocking_handler.detect_blocking(self.browser.driver):
                    logger.warning("Blocking page detected, attempting recovery")
                    return self.blocking_handler.handle_blocking(self.browser.driver)

            # Check for CAPTCHA before proceeding
            if self.captcha_detector and self._should_check_captcha(action):
                if self.captcha_detector.detect_captcha(self.browser.driver):
                    logger.warning("CAPTCHA detected, attempting resolution")
                    return self.captcha_detector.handle_captcha(self.browser.driver)

            # Check session rotation
            if self.session_manager:
                self.session_manager.check_session_rotation(self)

            self.request_count += 1
            return True

        except Exception as e:
            logger.error(f"Pre-action hook failed: {e}")
            return False

    def post_action_hook(
        self, action: str, params: Dict[str, Any], success: bool
    ) -> None:
        """
        Execute post-action anti-detection measures.

        Args:
            action: The workflow action that was executed
            params: Action parameters
            success: Whether the action succeeded
        """
        try:
            # Simulate human behavior after action
            if self.human_simulator:
                self.human_simulator.simulate_post_action(action, params, success)

            # Update rate limiter with action result
            if self.rate_limiter:
                self.rate_limiter.update_after_action(success)

        except Exception as e:
            logger.error(f"Post-action hook failed: {e}")

    def handle_error(self, error: Exception, action: str, retry_count: int = 0) -> bool:
        """
        Handle errors with anti-detection recovery strategies.

        Args:
            error: The exception that occurred
            action: The action that failed
            retry_count: Current retry count

        Returns:
            True if error was handled and can retry, False otherwise
        """
        if retry_count >= self.config.max_retries_on_detection:
            logger.warning(
                f"Max retries ({self.config.max_retries_on_detection}) exceeded for action: {action}"
            )
            return False

        try:
            # Check if it's a detection-related error
            error_str = str(error).lower()

            if "captcha" in error_str and self.captcha_detector:
                logger.info("CAPTCHA-related error detected, attempting recovery")
                return self.captcha_detector.handle_captcha(self.browser.driver)

            elif (
                any(
                    term in error_str for term in ["blocked", "banned", "access denied"]
                )
                and self.blocking_handler
            ):
                logger.info("Blocking-related error detected, attempting recovery")
                return self.blocking_handler.handle_blocking(self.browser.driver)

            elif "timeout" in error_str and self.rate_limiter:
                logger.info("Timeout error detected, applying rate limiting")
                self.rate_limiter.apply_backoff_delay()
                return True

            # Default session rotation on persistent failures
            if self.session_manager and retry_count > 1:
                logger.info("Persistent failures detected, rotating session")
                return self.session_manager.rotate_session(self)

        except Exception as e:
            logger.error(f"Error handling failed: {e}")

        return False

    def _should_check_captcha(self, action: str) -> bool:
        """Determine if CAPTCHA check should be performed for this action."""
        return action in ["navigate", "click", "input_text", "login"]

    def _should_check_blocking(self, action: str) -> bool:
        """Determine if blocking check should be performed for this action."""
        return action in ["navigate", "click"]


class CaptchaDetector:
    """Handles CAPTCHA detection and resolution."""

    def __init__(self, config: AntiDetectionConfig):
        self.config = config

    def detect_captcha(self, driver) -> bool:
        """Detect if a CAPTCHA is present on the page."""
        try:
            for selector in self.config.captcha_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"CAPTCHA detected using selector: {selector}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            logger.error(f"CAPTCHA detection failed: {e}")
            return False

    def handle_captcha(self, driver) -> bool:
        """Attempt to handle CAPTCHA (basic implementation)."""
        try:
            # For now, just wait and retry - in production, integrate with CAPTCHA solving service
            logger.info("Attempting CAPTCHA resolution (waiting strategy)")
            time.sleep(random.uniform(5, 10))
            return True  # Assume resolution successful for now
        except Exception as e:
            logger.error(f"CAPTCHA handling failed: {e}")
            return False


class RateLimiter:
    """Manages rate limiting with intelligent delays."""

    def __init__(self, config: AntiDetectionConfig):
        self.config = config
        self.last_request_time = 0
        self.consecutive_failures = 0

    def apply_delay(self) -> None:
        """Apply appropriate delay before next request."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time

        min_delay = self.config.rate_limit_min_delay
        max_delay = self.config.rate_limit_max_delay

        # Increase delay based on consecutive failures
        if self.consecutive_failures > 0:
            max_delay *= 2**self.consecutive_failures

        required_delay = random.uniform(min_delay, max_delay)

        if time_since_last < required_delay:
            delay = required_delay - time_since_last
            logger.debug(f"Applying rate limit delay: {delay:.2f}s")
            time.sleep(delay)

        self.last_request_time = time.time()

    def apply_backoff_delay(self) -> None:
        """Apply exponential backoff delay."""
        self.consecutive_failures += 1
        delay = self.config.rate_limit_max_delay * (2**self.consecutive_failures)
        logger.info(
            f"Applying backoff delay: {delay:.2f}s (failure #{self.consecutive_failures})"
        )
        time.sleep(delay)

    def update_after_action(self, success: bool) -> None:
        """Update rate limiting state based on action result."""
        if success:
            self.consecutive_failures = max(0, self.consecutive_failures - 1)
        else:
            self.consecutive_failures += 1


class HumanBehaviorSimulator:
    """Simulates human-like browsing behavior."""

    def __init__(self, config: AntiDetectionConfig):
        self.config = config

    def simulate_pre_action(self, action: str, params: Dict[str, Any]) -> None:
        """Simulate human behavior before an action."""
        if action == "click":
            # Random mouse movement before click
            time.sleep(random.uniform(0.1, 0.5))
        elif action == "input_text":
            # Typing delay
            time.sleep(random.uniform(0.05, 0.2))
        elif action == "navigate":
            # Page reading time
            time.sleep(random.uniform(1, 3))

    def simulate_post_action(
        self, action: str, params: Dict[str, Any], success: bool
    ) -> None:
        """Simulate human behavior after an action."""
        if action == "navigate" and success:
            # Simulate reading time
            time.sleep(random.uniform(2, 5))
        elif action == "click" and success:
            # Post-click pause
            time.sleep(random.uniform(0.5, 2))


class SessionManager:
    """Manages browser session rotation."""

    def __init__(self, config: AntiDetectionConfig):
        self.config = config
        self.request_count = 0

    def check_session_rotation(self, manager: "AntiDetectionManager") -> None:
        """Check if session should be rotated."""
        self.request_count += 1
        if self.request_count >= self.config.session_rotation_interval:
            logger.info(
                f"Session rotation triggered after {self.request_count} requests"
            )
            self.rotate_session(manager)

    def rotate_session(self, manager: "AntiDetectionManager") -> bool:
        """Rotate the browser session."""
        try:
            # Close current browser
            if manager.browser:
                manager.browser.quit()

            # Create new browser instance
            from src.utils.scraping.browser import create_browser

            manager.browser = create_browser(
                site_name="rotated_session",
                headless=True,  # Assume headless for now
                profile_suffix=f"rotated_{int(time.time())}",
            )

            # Reset counters
            self.request_count = 0
            manager.request_count = 0
            manager.session_start_time = time.time()

            logger.info("Session rotated successfully")
            return True

        except Exception as e:
            logger.error(f"Session rotation failed: {e}")
            return False


class BlockingHandler:
    """Handles blocking page detection and recovery."""

    def __init__(self, config: AntiDetectionConfig):
        self.config = config

    def detect_blocking(self, driver) -> bool:
        """Detect if current page is a blocking page."""
        try:
            for selector in self.config.blocking_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(
                            f"Blocking page detected using selector: {selector}"
                        )
                        return True
                except:
                    continue

            # Check page title/content for blocking indicators
            title = driver.title.lower()
            if any(
                term in title
                for term in ["blocked", "banned", "access denied", "forbidden"]
            ):
                logger.info("Blocking page detected in page title")
                return True

            return False

        except Exception as e:
            logger.error(f"Blocking detection failed: {e}")
            return False

    def handle_blocking(self, driver) -> bool:
        """Attempt to handle blocking page."""
        try:
            # For now, just wait and retry - in production, implement proxy rotation, etc.
            logger.info("Attempting blocking page recovery (waiting strategy)")
            time.sleep(random.uniform(30, 60))  # Longer wait for blocking
            return True
        except Exception as e:
            logger.error(f"Blocking handling failed: {e}")
            return False
