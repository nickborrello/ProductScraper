"""
CAPTCHA solving service integration for anti-detection manager.
Supports multiple CAPTCHA solving services including 2Captcha, Anti-Captcha, etc.
"""

import logging
import time
from enum import Enum
from typing import Any, cast

import requests  # type: ignore
from selenium.webdriver.common.by import By

logger = logging.getLogger(__name__)


class CaptchaType(Enum):
    """Supported CAPTCHA types."""

    RECAPTCHA_V2 = "recaptcha_v2"
    RECAPTCHA_V3 = "recaptcha_v3"
    HCAPTCHA = "hcaptcha"
    UNKNOWN = "unknown"


class CaptchaService(Enum):
    """Supported CAPTCHA solving services."""

    TWOCAPTCHA = "2captcha"
    ANTICAPTCHA = "anti-captcha"
    CAPSOLVER = "capsolver"


class CaptchaSolverConfig:
    """Configuration for CAPTCHA solving services."""

    def __init__(
        self,
        enabled: bool = False,
        service: str = "2captcha",
        api_key: str = "",
        timeout: int = 120,
        polling_interval: float = 5.0,
        max_retries: int = 3,
    ):
        self.enabled = enabled
        self.service = CaptchaService(service.lower())
        self.api_key = api_key
        self.timeout = timeout
        self.polling_interval = polling_interval
        self.max_retries = max_retries


class CaptchaSolver:
    """
    Handles CAPTCHA solving using external services.

    Supports multiple CAPTCHA types and solving services with automatic
    detection, submission, and solution application.
    """

    def __init__(self, config: CaptchaSolverConfig):
        self.config = config
        self.session = requests.Session()

        # Service endpoints
        self.endpoints = {
            CaptchaService.TWOCAPTCHA: {
                "submit": "http://2captcha.com/in.php",
                "retrieve": "http://2captcha.com/res.php",
            },
            CaptchaService.ANTICAPTCHA: {
                "submit": "https://api.anti-captcha.com/createTask",
                "retrieve": "https://api.anti-captcha.com/getTaskResult",
            },
            CaptchaService.CAPSOLVER: {
                "submit": "https://api.capsolver.com/createTask",
                "retrieve": "https://api.capsolver.com/getTaskResult",
            },
        }

    def solve_captcha(self, driver, url: str) -> bool:
        """
        Main method to solve CAPTCHA on current page.

        Args:
            driver: Selenium WebDriver instance
            url: Current page URL

        Returns:
            True if CAPTCHA was solved successfully, False otherwise
        """
        if not self.config.enabled or not self.config.api_key:
            logger.warning("CAPTCHA solver not configured or disabled")
            return False

        try:
            # Detect CAPTCHA type and extract parameters
            captcha_type, params = self._detect_captcha(driver, url)
            if captcha_type == CaptchaType.UNKNOWN:
                logger.warning("Unknown CAPTCHA type detected")
                return False

            # Submit to solving service
            task_id = self._submit_captcha(captcha_type, params, url)
            if not task_id:
                logger.error("Failed to submit CAPTCHA to solving service")
                return False

            # Wait for and retrieve solution
            solution = self._wait_for_solution(task_id)
            if not solution:
                logger.error("Failed to get CAPTCHA solution")
                return False

            # Apply solution to page
            return self._apply_solution(driver, captcha_type, solution, params)

        except Exception as e:
            logger.error(f"CAPTCHA solving failed: {e}")
            return False

    def _detect_captcha(self, driver, url: str) -> tuple[CaptchaType, dict[str, Any]]:
        """
        Detect CAPTCHA type and extract required parameters.

        Returns:
            Tuple of (captcha_type, parameters_dict)
        """
        try:
            # Check for reCAPTCHA v2
            recaptcha_v2_selectors = [
                ".g-recaptcha",
                "[data-sitekey]",
                ".recaptcha-checkbox",
            ]

            for selector in recaptcha_v2_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        element = elements[0]
                        site_key = element.get_attribute("data-sitekey") or driver.execute_script(
                            """
                                var recaptcha = document.querySelector('.g-recaptcha');
                                if (recaptcha) {
                                    return recaptcha.getAttribute('data-sitekey');
                                }
                                return null;
                            """
                        )
                        if site_key:
                            return CaptchaType.RECAPTCHA_V2, {
                                "site_key": site_key,
                                "element": element,
                            }
                except Exception:
                    continue

            # Check for reCAPTCHA v3
            try:
                recaptcha_v3_script = driver.find_elements(
                    By.CSS_SELECTOR, "script[src*='recaptcha/api.js']"
                )
                if recaptcha_v3_script:
                    # Look for site key in script or global variables
                    site_key = driver.execute_script("""
                        if (window.grecaptcha && window.grecaptcha.render) {
                            // Try to find site key from rendered widgets
                            var widgets = document.querySelectorAll('[data-sitekey]');
                            if (widgets.length > 0) {
                                return widgets[0].getAttribute('data-sitekey');
                            }
                        }
                        return null;
                    """)
                    if site_key:
                        return CaptchaType.RECAPTCHA_V3, {
                            "site_key": site_key,
                        }
            except Exception:
                pass

            # Check for hCaptcha
            hcaptcha_selectors = [
                ".h-captcha",
                "[data-sitekey]",
                ".hcaptcha-checkbox",
            ]

            for selector in hcaptcha_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        element = elements[0]
                        site_key = element.get_attribute("data-sitekey")
                        if site_key:
                            return CaptchaType.HCAPTCHA, {
                                "site_key": site_key,
                                "element": element,
                            }
                except Exception:
                    continue

            return CaptchaType.UNKNOWN, {}

        except Exception as e:
            logger.error(f"CAPTCHA detection failed: {e}")
            return CaptchaType.UNKNOWN, {}

    def _submit_captcha(
        self, captcha_type: CaptchaType, params: dict[str, Any], url: str
    ) -> str | None:
        """
        Submit CAPTCHA to solving service.

        Returns:
            Task ID if successful, None otherwise
        """
        try:
            if self.config.service == CaptchaService.TWOCAPTCHA:
                return self._submit_2captcha(captcha_type, params, url)
            elif self.config.service == CaptchaService.ANTICAPTCHA:
                return self._submit_anti_captcha(captcha_type, params, url)
            elif self.config.service == CaptchaService.CAPSOLVER:
                return self._submit_capsolver(captcha_type, params, url)
            else:
                logger.error(f"Unsupported CAPTCHA service: {self.config.service}")
                return None

        except Exception as e:
            logger.error(f"CAPTCHA submission failed: {e}")
            return None

    def _submit_2captcha(
        self, captcha_type: CaptchaType, params: dict[str, Any], url: str
    ) -> str | None:
        """Submit CAPTCHA to 2Captcha service."""
        data = {
            "key": self.config.api_key,
            "method": "userrecaptcha",
            "googlekey": params["site_key"],
            "pageurl": url,
            "json": 1,
        }

        if captcha_type == CaptchaType.RECAPTCHA_V3:
            data["version"] = "v3"
            data["action"] = "verify"  # Default action
        elif captcha_type == CaptchaType.HCAPTCHA:
            data["method"] = "hcaptcha"
            data["sitekey"] = params["site_key"]

        response = self.session.post(self.endpoints[CaptchaService.TWOCAPTCHA]["submit"], data=data)
        result = response.json()

        if result.get("status") == 1:
            return cast(str, result.get("request"))
        else:
            logger.error(f"2Captcha submission failed: {result}")
            return None

    def _submit_anti_captcha(
        self, captcha_type: CaptchaType, params: dict[str, Any], url: str
    ) -> str | None:
        """Submit CAPTCHA to Anti-Captcha service."""
        task_data = {
            "type": "RecaptchaV2TaskProxyless",
            "websiteURL": url,
            "websiteKey": params["site_key"],
        }

        if captcha_type == CaptchaType.RECAPTCHA_V3:
            task_data["type"] = "RecaptchaV3TaskProxyless"
            task_data["pageAction"] = "verify"
        elif captcha_type == CaptchaType.HCAPTCHA:
            task_data["type"] = "HCaptchaTaskProxyless"

        data = {
            "clientKey": self.config.api_key,
            "task": task_data,
        }

        response = self.session.post(
            self.endpoints[CaptchaService.ANTICAPTCHA]["submit"], json=data
        )
        result = response.json()

        if result.get("errorId") == 0:
            return str(result["taskId"])
        else:
            logger.error(f"Anti-Captcha submission failed: {result}")
            return None

    def _submit_capsolver(
        self, captcha_type: CaptchaType, params: dict[str, Any], url: str
    ) -> str | None:
        """Submit CAPTCHA to CapSolver service."""
        task_data = {
            "type": "ReCaptchaV2TaskProxyLess",
            "websiteURL": url,
            "websiteKey": params["site_key"],
        }

        if captcha_type == CaptchaType.RECAPTCHA_V3:
            task_data["type"] = "ReCaptchaV3TaskProxyLess"
            task_data["pageAction"] = "verify"
        elif captcha_type == CaptchaType.HCAPTCHA:
            task_data["type"] = "HCaptchaTaskProxyLess"

        data = {
            "clientKey": self.config.api_key,
            "appId": "appId",  # CapSolver specific
            "task": task_data,
        }

        response = self.session.post(self.endpoints[CaptchaService.CAPSOLVER]["submit"], json=data)
        result = response.json()

        if result.get("errorId") == 0:
            return cast(str, result["taskId"])
        else:
            logger.error(f"CapSolver submission failed: {result}")
            return None

    def _wait_for_solution(self, task_id: str) -> str | None:
        """
        Wait for CAPTCHA solution from service.

        Returns:
            Solution token if successful, None otherwise
        """
        start_time = time.time()

        while time.time() - start_time < self.config.timeout:
            try:
                solution = self._retrieve_solution(task_id)
                if solution:
                    return solution

                time.sleep(self.config.polling_interval)

            except Exception as e:
                logger.error(f"Solution retrieval failed: {e}")
                time.sleep(self.config.polling_interval)

        logger.error("CAPTCHA solution timeout")
        return None

    def _retrieve_solution(self, task_id: str) -> str | None:
        """Retrieve solution from solving service."""
        try:
            if self.config.service == CaptchaService.TWOCAPTCHA:
                return self._retrieve_2captcha(task_id)
            elif self.config.service == CaptchaService.ANTICAPTCHA:
                return self._retrieve_anti_captcha(task_id)
            elif self.config.service == CaptchaService.CAPSOLVER:
                return self._retrieve_capsolver(task_id)
            else:
                logger.error(f"Unsupported CAPTCHA service: {self.config.service}")
                return None

        except Exception as e:
            logger.error(f"Solution retrieval failed: {e}")
            return None

    def _retrieve_2captcha(self, task_id: str) -> str | None:
        """Retrieve solution from 2Captcha."""
        params = {
            "key": self.config.api_key,
            "action": "get",
            "id": task_id,
            "json": 1,
        }

        response = self.session.get(
            self.endpoints[CaptchaService.TWOCAPTCHA]["retrieve"],
            params=params,  # type: ignore
        )
        result = response.json()

        if result.get("status") == 1:
            return cast(str, result.get("request"))
        elif result.get("request") == "CAPCHA_NOT_READY":
            return None  # Still processing
        else:
            logger.error(f"2Captcha retrieval failed: {result}")
            return None

    def _retrieve_anti_captcha(self, task_id: str) -> str | None:
        """Retrieve solution from Anti-Captcha."""
        data = {
            "clientKey": self.config.api_key,
            "taskId": int(task_id),
        }

        response = self.session.post(
            self.endpoints[CaptchaService.ANTICAPTCHA]["retrieve"], json=data
        )
        result = response.json()

        if result.get("errorId") == 0:
            status = result.get("status")
            if status == "ready":
                return cast(str, result["solution"]["gRecaptchaResponse"])
            elif status == "processing":
                return None  # Still processing
            else:
                logger.error(f"Anti-Captcha unexpected status: {status}")
                return None
        else:
            logger.error(f"Anti-Captcha retrieval failed: {result}")
            return None

    def _retrieve_capsolver(self, task_id: str) -> str | None:
        """Retrieve solution from CapSolver."""
        data = {
            "clientKey": self.config.api_key,
            "taskId": task_id,
        }

        response = self.session.post(
            self.endpoints[CaptchaService.CAPSOLVER]["retrieve"], json=data
        )
        result = response.json()

        if result.get("errorId") == 0:
            status = result.get("status")
            if status == "ready":
                return cast(str, result["solution"]["gRecaptchaResponse"])
            elif status == "processing":
                return None  # Still processing
            else:
                logger.error(f"CapSolver unexpected status: {status}")
                return None
        else:
            logger.error(f"CapSolver retrieval failed: {result}")
            return None

    def _apply_solution(
        self, driver, captcha_type: CaptchaType, solution: str, params: dict[str, Any]
    ) -> bool:
        """
        Apply CAPTCHA solution to the page.

        Returns:
            True if solution applied successfully
        """
        try:
            if captcha_type in [CaptchaType.RECAPTCHA_V2, CaptchaType.HCAPTCHA]:
                # Inject the solution into the textarea
                script = f"""
                    var textarea = document.querySelector('textarea[name="g-recaptcha-response"]');
                    if (!textarea) {{
                        textarea = document.createElement('textarea');
                        textarea.name = 'g-recaptcha-response';
                        textarea.style.display = 'none';
                        document.body.appendChild(textarea);
                    }}
                    textarea.value = '{solution}';

                    // Trigger callback if it exists
                    if (window.grecaptchaCallback) {{
                        window.grecaptchaCallback('{solution}');
                    }}

                    // Mark as completed
                    var badge = document.querySelector('.g-recaptcha-badge');
                    if (badge) {{
                        badge.style.display = 'none';
                    }}
                """
                driver.execute_script(script)

            elif captcha_type == CaptchaType.RECAPTCHA_V3:
                # For v3, the token is usually submitted with forms
                # Store it for later use
                driver.execute_script(f"window.recaptchaV3Token = '{solution}';")

            logger.info(f"CAPTCHA solution applied for type: {captcha_type.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to apply CAPTCHA solution: {e}")
            return False
